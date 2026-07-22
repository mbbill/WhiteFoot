#!/usr/bin/env python3
"""Build and run the frozen raw-DEFLATE default-shape benchmark.

``score`` is the preregistered 30-process campaign.  It refuses to run without
an explicit acknowledgement, a pristine committed preregistration, the exact
frozen generation run, and a new output directory.  ``smoke`` builds a public
zlib-ng-backed Whitefoot-ABI shim and exercises the same process, ABI, corpus,
and verification wiring with one corpus pass.  Smoke output is always marked
as non-scoring.

Proof reports are requested only while building a source that has already
frozen.  They are retained as attribution evidence and are never passed to the
generator or evaluator.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import datetime as dt
import gc
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT_FLOOR = HERE.parent / "default-floor"
ANALYZER = HERE / "analyze.py"
PROTOCOL = HERE / "PROTOCOL.md"
SCORING_MANIFEST = HERE / "scoring-manifest.json"
REFERENCE_HELPER = HERE / "reference.py"
REFERENCE_SOURCE = HERE / "reference.c"
VERIFY = HERE / "verify.py"
RUN_GENERATION = HERE / "run_generation.py"
GENERATION_INPUTS = HERE / "generation-inputs.json"
TARGET_RUN_DIR = (HERE / "runs" / "primary-terra-medium-preregistered").resolve()
TARGET_TRACE_MANIFEST = TARGET_RUN_DIR / "frozen" / "trace-manifest.json"
GENERATOR = DEFAULT_FLOOR / "generate.py"
MODEL_ADAPTER = DEFAULT_FLOOR / "codex_model_adapter.py"
PROMPT = HERE / "base-prompt.txt"
DEMOC = ROOT / "prototype" / "democ" / "democ.py"

PYTHON = Path(
    "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/"
    "Python3.framework/Versions/3.9/bin/python3.9"
)
CLANG = Path(
    "/Applications/Xcode.app/Contents/Developer/Toolchains/"
    "XcodeDefault.xctoolchain/usr/bin/clang"
)
MACOS_SDK = Path(
    "/Applications/Xcode.app/Contents/Developer/Platforms/"
    "MacOSX.platform/Developer/SDKs/MacOSX.sdk"
)
SDK_SETTINGS = MACOS_SDK / "SDKSettings.json"
PMSET = Path("/usr/bin/pmset")
SYSTEM_PROFILER = Path("/usr/sbin/system_profiler")
SW_VERS = Path("/usr/bin/sw_vers")

SCORE_PASSES = 4
SMOKE_PASSES = 1
MEMBER_COUNT = 12
SOURCE_BYTES_PER_PASS = 211_938_580
SCORE_DECODED_BYTES = 847_754_320
RAW_DEFLATE_BYTES = 68_220_415
WORK8_LENGTH = 65_536
WORK16_LENGTH = 4_096
WORK32_LENGTH = 4_096
ALIGNMENT = 64
ORDER_SEED = 0x5244464C41544531
MASK64 = (1 << 64) - 1
VARIANTS = ("F", "N", "Z")
ORDER_STRATA = (
    "F,N,Z",
    "F,Z,N",
    "N,F,Z",
    "N,Z,F",
    "Z,F,N",
    "Z,N,F",
)
CANONICAL_MEMBERS = (
    "dickens",
    "mozilla",
    "mr",
    "nci",
    "ooffice",
    "osdb",
    "reymont",
    "samba",
    "sao",
    "webster",
    "xml",
    "x-ray",
)
FORBIDDEN_BUILD_FLAGS = (
    "target-cpu=native",
    "-march=",
    "-mcpu=",
    "-mtune=",
    "-flto",
    "profile-generate",
    "profile-use",
)
EXPECTED_SCORE_HOST = {
    "machine_model": "Mac16,12",
    "chip_type": "Apple M4",
    "processor_description": "proc 10:4:6:0",
    "processor_core_count": 10,
    "physical_memory": "16 GB",
    "architecture": "arm64",
    "macos_product_version": "26.5.1",
    "macos_build_version": "25F80",
    "platform": "macOS-26.5.1-arm64-arm-64bit",
}


class CampaignFailure(RuntimeError):
    """The campaign is invalid or a locked input changed."""


class Buf8(ctypes.Structure):
    _fields_ = [("p", ctypes.POINTER(ctypes.c_uint8)), ("n", ctypes.c_int64)]


class Buf16(ctypes.Structure):
    _fields_ = [("p", ctypes.POINTER(ctypes.c_uint16)), ("n", ctypes.c_int64)]


class Buf32(ctypes.Structure):
    _fields_ = [("p", ctypes.POINTER(ctypes.c_uint32)), ("n", ctypes.c_int64)]


class InflateResult(ctypes.Structure):
    _fields_ = [("status", ctypes.c_uint64), ("produced", ctypes.c_uint64)]


class AlignedBuffer:
    """One reusable, explicitly aligned region with a fixed visible address."""

    def __init__(self, size: int, alignment: int = ALIGNMENT) -> None:
        if size < 0 or alignment <= 0 or alignment & (alignment - 1):
            raise CampaignFailure("invalid aligned-buffer request")
        self.size = size
        self.storage = (ctypes.c_uint8 * (max(1, size) + alignment - 1))()
        base = ctypes.addressof(self.storage)
        self.address = (base + alignment - 1) & ~(alignment - 1)
        self.pointer8 = ctypes.cast(
            ctypes.c_void_p(self.address), ctypes.POINTER(ctypes.c_uint8)
        )

    def pointer16(self) -> Any:
        return ctypes.cast(
            ctypes.c_void_p(self.address), ctypes.POINTER(ctypes.c_uint16)
        )

    def pointer32(self) -> Any:
        return ctypes.cast(
            ctypes.c_void_p(self.address), ctypes.POINTER(ctypes.c_uint32)
        )

    def set_bytes(self, value: bytes) -> None:
        if len(value) != self.size:
            raise CampaignFailure("aligned-buffer source length mismatch")
        if value:
            ctypes.memmove(self.address, value, len(value))

    def poison(self, byte: int) -> None:
        if self.size:
            # memset both initializes and prefaults every visible page.  It is
            # deliberately called before the timer for every decoder call.
            ctypes.memset(self.address, byte & 0xFF, self.size)

    def bytes(self) -> bytes:
        return ctypes.string_at(self.address, self.size)


class XorShift64Star:
    def __init__(self, seed: int) -> None:
        if not 0 < seed <= MASK64:
            raise ValueError("xorshift seed must be a nonzero u64")
        self.state = seed

    def next(self) -> int:
        self.state ^= self.state >> 12
        self.state ^= (self.state << 25) & MASK64
        self.state ^= self.state >> 27
        self.state &= MASK64
        return (self.state * 2_685_821_657_736_338_717) & MASK64


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise CampaignFailure("%s is not a lowercase SHA-256" % label)
    return value


def read_json_object(path: Path, label: str) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CampaignFailure("could not read %s at %s: %s" % (label, path, error))
    if not isinstance(value, dict):
        raise CampaignFailure("%s is not a JSON object: %s" % (label, path))
    return value


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def argv_sha256(argv: Sequence[str]) -> str:
    encoded = json.dumps(
        list(argv), separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def checked_capture(
    argv: Sequence[str],
    *,
    cwd: Path = ROOT,
    env: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = 120,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        list(argv),
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise CampaignFailure(
            "command failed (%d): %r\nstdout:\n%s\nstderr:\n%s"
            % (completed.returncode, list(argv), completed.stdout, completed.stderr)
        )
    return completed


def run_logged(
    argv: Sequence[str],
    log_path: Path,
    *,
    env: Optional[Dict[str, str]] = None,
    timeout: int = 600,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        list(argv),
        cwd=ROOT,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    log_path.write_text(
        "argv: "
        + json.dumps(list(argv))
        + "\n\nstdout:\n"
        + completed.stdout
        + "\n\nstderr:\n"
        + completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise CampaignFailure(
            "command failed (%d); see %s" % (completed.returncode, log_path)
        )
    return completed


def sanitized_environment() -> Tuple[Dict[str, str], List[str]]:
    environment = dict(os.environ)
    removed: List[str] = []
    exact = {
        "CC",
        "CFLAGS",
        "CPPFLAGS",
        "LDFLAGS",
        "CPATH",
        "C_INCLUDE_PATH",
        "CPLUS_INCLUDE_PATH",
        "OBJC_INCLUDE_PATH",
        "LIBRARY_PATH",
        "CCC_OVERRIDE_OPTIONS",
        "RC_DEBUG_OPTIONS",
        "SDKROOT",
        "MACOSX_DEPLOYMENT_TARGET",
        "PYTHONHOME",
        "PYTHONPATH",
        "LD_PRELOAD",
        "LD_LIBRARY_PATH",
    }
    for key in list(environment):
        upper = key.upper()
        if (
            upper in exact
            or upper.startswith("DYLD_")
            or upper.startswith("CLANG_CONFIG_FILE_")
        ):
            removed.append(key)
            del environment[key]
    environment["LC_ALL"] = "C"
    environment["LANG"] = "C"
    return environment, sorted(removed)


def git_output(argv: Sequence[str]) -> str:
    return checked_capture(["git", *argv], timeout=60).stdout.strip()


def preregistration_identity() -> Dict[str, Any]:
    protocol_text = PROTOCOL.read_text(encoding="utf-8")
    if "Status: **preregistered**." not in protocol_text:
        raise CampaignFailure("PROTOCOL.md is not preregistered")
    if "TBD" in protocol_text or "DRAFT" in protocol_text:
        raise CampaignFailure("PROTOCOL.md still contains a draft marker")
    status = git_output(["status", "--porcelain=v1", "--untracked-files=all"])
    if status:
        raise CampaignFailure(
            "score requires a pristine committed preregistration; git is dirty"
        )
    required = (
        PROTOCOL,
        Path(__file__).resolve(),
        ANALYZER,
        SCORING_MANIFEST,
        REFERENCE_HELPER,
        REFERENCE_SOURCE,
        VERIFY,
        RUN_GENERATION,
        GENERATION_INPUTS,
        GENERATOR,
        MODEL_ADAPTER,
        PROMPT,
        DEMOC,
    )
    labels = [str(path.resolve().relative_to(ROOT.resolve())) for path in required]
    tracked = set(git_output(["ls-files", "--", *labels]).splitlines())
    missing = sorted(set(labels) - tracked)
    if missing:
        raise CampaignFailure("preregistered scoring inputs are untracked: %s" % missing)
    return {
        "head": git_output(["rev-parse", "HEAD"]),
        "tree": git_output(["rev-parse", "HEAD^{tree}"]),
        "status_porcelain_v1": [],
        "tracked_inputs": labels,
    }


def resolve_repo_file(relative: Any, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise CampaignFailure("%s path is missing" % label)
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise CampaignFailure("%s escapes the repository" % label)
    path = (ROOT / Path(*pure.parts)).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as error:
        raise CampaignFailure("%s resolves outside the repository" % label) from error
    if path.is_symlink() or not path.is_file():
        raise CampaignFailure("%s is not a regular file: %s" % (label, path))
    return path


def resolve_run_artifact(run_dir: Path, relative: Any, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise CampaignFailure("%s.path is missing" % label)
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise CampaignFailure("%s path escapes the generation run" % label)
    path = (run_dir / raw).resolve()
    try:
        path.relative_to(run_dir)
    except ValueError as error:
        raise CampaignFailure("%s resolves outside the generation run" % label) from error
    if path.is_symlink() or not path.is_file():
        raise CampaignFailure("%s artifact is missing or symlinked: %s" % (label, path))
    return path


def verify_bound_artifact(
    run_dir: Path, specification: Any, label: str
) -> Tuple[Path, str]:
    if not isinstance(specification, dict):
        raise CampaignFailure("%s binding is not an object" % label)
    path = resolve_run_artifact(run_dir, specification.get("path"), label)
    expected = require_sha256(specification.get("sha256"), label + ".sha256")
    actual = sha256_file(path)
    if actual != expected:
        raise CampaignFailure("%s hash mismatch: expected %s, got %s" % (label, expected, actual))
    return path, expected


def canonical_generation_inputs() -> Tuple[Dict[str, Any], str]:
    value = read_json_object(GENERATION_INPUTS, "generation input manifest")
    canonical = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if GENERATION_INPUTS.read_bytes() != canonical:
        raise CampaignFailure("generation-inputs.json is not canonical JSON")
    if value.get("schema") != "whitefoot.raw-deflate.generation-inputs.v1":
        raise CampaignFailure("generation input manifest schema changed")
    files = value.get("files")
    if not isinstance(files, dict) or not files:
        raise CampaignFailure("generation input manifest has no file bindings")
    for relative, expected in files.items():
        path = resolve_repo_file(relative, "generation input %s" % relative)
        if sha256_file(path) != require_sha256(expected, "generation input " + relative):
            raise CampaignFailure("generation input changed after preregistration: %s" % relative)
    return value, sha256_file(GENERATION_INPUTS)


def validate_generation_config(
    config: Dict[str, Any], run_dir: Path, repository: Dict[str, Any]
) -> None:
    if run_dir != TARGET_RUN_DIR:
        raise CampaignFailure("generation run is not the preregistered run path")
    if (
        config.get("protocol_version") != 1
        or config.get("trajectory_count") != 1
        or config.get("repair_budget") != 3
        or config.get("max_rounds") != 4
        or config.get("source_name") != "inflate_raw.wf"
        or config.get("model_timeout_seconds") != 660
        or config.get("evaluator_timeout_seconds") != 1200
    ):
        raise CampaignFailure("generation configuration is not the preregistered trajectory")
    model_invocation = config.get("model_invocation")
    evaluator_invocation = config.get("evaluator_invocation")
    if not isinstance(model_invocation, dict) or not isinstance(evaluator_invocation, dict):
        raise CampaignFailure("generation invocation metadata is missing")
    codex = Path("/opt/homebrew/bin/codex")
    expected_model = [
        str(PYTHON),
        str(MODEL_ADAPTER),
        "--codex",
        str(codex),
        "--model",
        "gpt-5.6-terra",
        "--reasoning",
        "medium",
        "--service-tier",
        "default",
        "--timeout",
        "600",
    ]
    expected_evaluator = [str(PYTHON), str(VERIFY)]
    if (
        model_invocation.get("argv_sha256") != argv_sha256(expected_model)
        or model_invocation.get("argv_items") != len(expected_model)
        or evaluator_invocation.get("argv_without_candidate_sha256")
        != argv_sha256(expected_evaluator)
        or evaluator_invocation.get("argv_items_without_candidate")
        != len(expected_evaluator)
    ):
        raise CampaignFailure("generation invocation identity changed")
    model = model_invocation.get("public_metadata")
    evaluator = evaluator_invocation.get("public_metadata")
    if not isinstance(model, dict) or not isinstance(evaluator, dict):
        raise CampaignFailure("generation public metadata is missing")
    expected_model_fields = {
        "surface": "codex-cli",
        "model": "gpt-5.6-terra",
        "reasoning_effort": "medium",
        "service_tier": "default",
        "ephemeral": True,
        "sandbox": "read-only",
        "user_config": "ignored",
        "repository_rules": "ignored",
        "event_boundary": "exact-four-event-single-agent-message-no-tools",
    }
    expected_evaluator_fields = {
        "kind": "raw-deflate-compile-and-correctness",
        "proof_feedback": "disabled-before-freeze",
    }
    if any(model.get(key) != value for key, value in expected_model_fields.items()):
        raise CampaignFailure("generation model metadata changed")
    if any(evaluator.get(key) != value for key, value in expected_evaluator_fields.items()):
        raise CampaignFailure("generation evaluator metadata changed")
    for channel in (model, evaluator):
        if (
            channel.get("host_platform") != EXPECTED_SCORE_HOST["platform"]
            or channel.get("python") != "3.9.6"
        ):
            raise CampaignFailure("generation did not run on the frozen OS/Python host")
        if channel.get("repository_revision") != repository["head"]:
            raise CampaignFailure("generation did not run from the scoring preregistration commit")
        if channel.get("git_status_porcelain_v1") != []:
            raise CampaignFailure("generation was not launched from a pristine repository")

    input_manifest, input_manifest_sha = canonical_generation_inputs()
    expected_input_binding = {
        "path": str(GENERATION_INPUTS.relative_to(ROOT)),
        "sha256": input_manifest_sha,
    }
    if (
        model.get("generation_input_manifest") != expected_input_binding
        or evaluator.get("generation_input_manifest") != expected_input_binding
    ):
        raise CampaignFailure("generation input-manifest binding is stale")
    input_hashes = evaluator.get("input_hashes")
    if input_hashes != input_manifest.get("files"):
        raise CampaignFailure("generation evaluator input hashes are not canonical")
    expected_model_inputs = {
        str(path.relative_to(ROOT)): input_hashes[str(path.relative_to(ROOT))]
        for path in (MODEL_ADAPTER, GENERATOR, PROMPT)
    }
    if model.get("input_hashes") != expected_model_inputs:
        raise CampaignFailure("generation model input subset changed")
    corpus_binding = evaluator.get("corpus")
    corpus_key = str((HERE / "correctness-corpus.json").relative_to(ROOT))
    if not isinstance(corpus_binding, dict) or corpus_binding.get("sha256") != input_hashes.get(corpus_key):
        raise CampaignFailure("generation correctness-corpus binding changed")

    tools = input_manifest.get("tools")
    if not isinstance(tools, dict) or not tools:
        raise CampaignFailure("generation tool manifest is empty")
    observed_tools: Dict[str, Any] = {}
    for label, specification in tools.items():
        if not isinstance(specification, dict):
            raise CampaignFailure("malformed generation tool binding: %s" % label)
        path = Path(specification.get("path", ""))
        if path.is_symlink() or not path.is_file():
            raise CampaignFailure("generation tool is missing: %s" % label)
        actual_hash = sha256_file(path)
        if actual_hash != require_sha256(specification.get("sha256"), "tool " + label):
            raise CampaignFailure("generation tool hash changed: %s" % label)
        version_argv = specification.get("version_argv")
        if not isinstance(version_argv, list) or not version_argv:
            raise CampaignFailure("generation tool version command is malformed")
        version = checked_capture(version_argv, timeout=60).stdout.strip()
        if version != specification.get("version_stdout"):
            raise CampaignFailure("generation tool version changed: %s" % label)
        observed_tools[label] = {
            "path": str(path),
            "sha256": actual_hash,
            "version": version,
        }
    if model.get("tool_manifest") != observed_tools or evaluator.get("tool_manifest") != observed_tools:
        raise CampaignFailure("generation public tool manifest changed")


def validate_freeze_manifest(
    manifest_argument: Path, repository: Dict[str, Any]
) -> Tuple[Dict[str, Any], Path, str]:
    manifest_path = manifest_argument.resolve()
    if manifest_path != TARGET_TRACE_MANIFEST:
        raise CampaignFailure("score requires the exact preregistered trace-manifest path")
    run_dir = manifest_path.parent.parent.resolve()
    manifest = read_json_object(manifest_path, "generation trace manifest")
    if manifest.get("protocol_version") != 1 or manifest.get("status") != "frozen":
        raise CampaignFailure("generation manifest is not a protocol-v1 frozen result")
    frozen_round = manifest.get("frozen_round")
    if type(frozen_round) is not int or not 0 <= frozen_round <= 3:
        raise CampaignFailure("generation manifest has an invalid frozen round")
    config_path, config_sha = verify_bound_artifact(run_dir, manifest.get("config"), "config")
    source_path, source_sha = verify_bound_artifact(run_dir, manifest.get("source"), "source")
    trace_spec = manifest.get("trace")
    trace_path, trace_sha = verify_bound_artifact(run_dir, trace_spec, "trace")
    if config_path != run_dir / "config.json" or trace_path != run_dir / "trace.jsonl":
        raise CampaignFailure("generation manifest does not bind canonical paths")
    config = read_json_object(config_path, "generation config")
    validate_generation_config(config, run_dir, repository)
    if source_path != run_dir / "frozen" / "inflate_raw.wf":
        raise CampaignFailure("frozen source path is not canonical")
    if not isinstance(trace_spec, dict):
        raise CampaignFailure("generation trace binding is malformed")
    manifest_rounds = trace_spec.get("rounds")
    if not isinstance(manifest_rounds, list) or len(manifest_rounds) != frozen_round + 1:
        raise CampaignFailure("generation trace does not end at the frozen round")
    trace_rounds: List[Any] = []
    for line_number, line in enumerate(trace_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            raise CampaignFailure("generation trace contains a blank line")
        try:
            trace_rounds.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise CampaignFailure("generation trace line %d is invalid" % line_number) from error
    if trace_rounds != manifest_rounds:
        raise CampaignFailure("trace.jsonl differs from its manifest copy")

    rounds_dir = run_dir / "rounds"
    if rounds_dir.is_symlink() or not rounds_dir.is_dir():
        raise CampaignFailure("generation rounds directory is missing or symlinked")
    observed_dirs = {
        entry.name
        for entry in os.scandir(rounds_dir)
        if entry.is_dir(follow_symlinks=False) and not entry.is_symlink()
    }
    expected_dirs = {"%03d" % index for index in range(frozen_round + 1)}
    if observed_dirs != expected_dirs or len(list(os.scandir(rounds_dir))) != len(expected_dirs):
        raise CampaignFailure("generation round directory set is not exact")

    artifacts_verified = 0
    for expected_round, record in enumerate(manifest_rounds):
        if not isinstance(record, dict):
            raise CampaignFailure("generation round record is malformed")
        if (
            record.get("protocol_version") != 1
            or record.get("round") != expected_round
            or type(record.get("correct")) is not bool
            or record["correct"] is not (expected_round == frozen_round)
        ):
            raise CampaignFailure("generation round freeze state is inconsistent")
        prefix = "rounds/%03d" % expected_round
        record_path = run_dir / prefix / "record.json"
        if record_path.is_symlink() or read_json_object(record_path, "round record") != record:
            raise CampaignFailure("generation record.json differs from the trace")
        expected_paths = {
            "prompt": prefix + "/prompt.txt",
            "raw": prefix + "/model.raw.txt",
            "source": prefix + "/inflate_raw.wf",
            "model_stderr": prefix + "/model.stderr.txt",
            "model_process": prefix + "/model-process.json",
            "evaluator_raw": prefix + "/evaluator.raw.txt",
            "evaluator_stderr": prefix + "/evaluator.stderr.txt",
            "evaluator_process": prefix + "/evaluator-process.json",
            "evaluator": prefix + "/evaluator.json",
        }
        artifacts = record.get("artifacts")
        if not isinstance(artifacts, dict) or set(artifacts) != set(expected_paths):
            raise CampaignFailure("generation round artifact set is not canonical")
        paths: Dict[str, Path] = {}
        for name, relative in expected_paths.items():
            specification = artifacts[name]
            if not isinstance(specification, dict) or specification.get("path") != relative:
                raise CampaignFailure("generation artifact path changed: %s" % name)
            paths[name], _ = verify_bound_artifact(
                run_dir, specification, "round %d %s" % (expected_round, name)
            )
            artifacts_verified += 1
        if paths["raw"].read_bytes() != paths["source"].read_bytes():
            raise CampaignFailure("model.raw.txt differs from the extracted source")
        evaluator = read_json_object(paths["evaluator"], "round evaluator")
        if evaluator != record.get("evaluator"):
            raise CampaignFailure("round evaluator JSON differs from the trace")
        compile_channel = evaluator.get("compile")
        correctness_channel = evaluator.get("correctness")
        recomputed = (
            isinstance(compile_channel, dict)
            and isinstance(correctness_channel, dict)
            and compile_channel.get("passed") is True
            and correctness_channel.get("passed") is True
        )
        if recomputed is not record["correct"]:
            raise CampaignFailure("round correct flag was not recomputed from both gates")
        if read_json_object(paths["model_process"], "model process") != {
            "returncode": 0,
            "process_failure": None,
        }:
            raise CampaignFailure("generation model process was not clean")
        if read_json_object(paths["evaluator_process"], "evaluator process") != {
            "returncode": 0,
            "process_failure": None,
            "candidate_was_last_argument": True,
        }:
            raise CampaignFailure("generation evaluator process was not clean")
    _, last_source_sha = verify_bound_artifact(
        run_dir, manifest_rounds[-1]["artifacts"]["source"], "frozen round source"
    )
    if last_source_sha != source_sha:
        raise CampaignFailure("frozen source differs from the correctness-green source")
    source_hash_path = run_dir / "frozen" / "source.sha256"
    if source_hash_path.read_bytes() != (source_sha + "  inflate_raw.wf\n").encode("ascii"):
        raise CampaignFailure("frozen source.sha256 is not canonical")
    result_path = run_dir / "result.json"
    result = read_json_object(result_path, "generation result")
    if (
        result.get("status") != "frozen"
        or result.get("round") != frozen_round
        or result.get("sha256") != source_sha
        or Path(result.get("source", "")).resolve() != source_path
        or Path(result.get("manifest", "")).resolve() != manifest_path
    ):
        raise CampaignFailure("generation result does not bind the frozen source")
    binding = {
        "status": "verified-frozen",
        "run_dir": str(run_dir),
        "frozen_round": frozen_round,
        "artifacts_verified": artifacts_verified,
        "manifest": {"path": str(manifest_path), "sha256": sha256_file(manifest_path)},
        "config": {"path": str(config_path), "sha256": config_sha},
        "trace": {"path": str(trace_path), "sha256": trace_sha},
        "source": {"path": str(source_path), "sha256": source_sha},
        "source_sha256_file": {
            "path": str(source_hash_path),
            "sha256": sha256_file(source_hash_path),
        },
        "result": {"path": str(result_path), "sha256": sha256_file(result_path)},
    }
    return binding, source_path, source_sha


def strict_tree_manifest(root: Path) -> Dict[str, str]:
    if root.is_symlink() or not root.is_dir():
        raise CampaignFailure("tree root is missing or symlinked: %s" % root)
    files: Dict[str, str] = {}
    for directory, names, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        for name in names:
            child = directory_path / name
            if child.is_symlink():
                raise CampaignFailure("tree contains a symlink: %s" % child)
        for name in filenames:
            child = directory_path / name
            if child.is_symlink() or not child.is_file():
                raise CampaignFailure("tree contains a non-regular file: %s" % child)
            files[child.relative_to(root).as_posix()] = sha256_file(child)
    return dict(sorted(files.items()))


def archive_generation(output: Path, binding: Dict[str, Any]) -> Dict[str, Any]:
    source = Path(binding["run_dir"])
    before = strict_tree_manifest(source)
    destination = output / "generation-freeze"
    shutil.copytree(source, destination, symlinks=False)
    after = strict_tree_manifest(source)
    copied = strict_tree_manifest(destination)
    if before != after or before != copied:
        raise CampaignFailure("generation run changed while it was archived")
    return {
        "source": str(source),
        "path": str(destination),
        "file_count": len(copied),
        "files_sha256": copied,
    }


def resolve_scoring_file(relative: Any, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise CampaignFailure("%s path is missing" % label)
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise CampaignFailure("%s path escapes the experiment" % label)
    path = (HERE / Path(*pure.parts)).resolve()
    try:
        path.relative_to(HERE.resolve())
    except ValueError as error:
        raise CampaignFailure("%s resolves outside the experiment" % label) from error
    if path.is_symlink() or not path.is_file():
        raise CampaignFailure("%s is missing or symlinked: %s" % (label, path))
    return path


def load_reference_module() -> Any:
    specification = importlib.util.spec_from_file_location(
        "whitefoot_raw_deflate_reference", REFERENCE_HELPER
    )
    if specification is None or specification.loader is None:
        raise CampaignFailure("could not import reference.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def validate_scoring_manifest(
    *, verify_reference: bool, exercise_reference: bool
) -> Dict[str, Any]:
    if exercise_reference and not verify_reference:
        raise CampaignFailure("reference execution requires provenance validation")
    manifest = read_json_object(SCORING_MANIFEST, "scoring manifest")
    if manifest.get("schema") != "whitefoot.raw-deflate.scoring-corpus.v1":
        raise CampaignFailure("scoring manifest schema changed")
    members = manifest.get("members")
    if not isinstance(members, list) or len(members) != MEMBER_COUNT:
        raise CampaignFailure("scoring manifest must contain exactly twelve members")
    validated_members: List[Dict[str, Any]] = []
    total_source = 0
    total_compressed = 0
    for index, (name, member) in enumerate(zip(CANONICAL_MEMBERS, members)):
        if not isinstance(member, dict) or member.get("name") != name or member.get("order") != index:
            raise CampaignFailure("scoring member order or name changed at index %d" % index)
        record: Dict[str, Any] = {"name": name, "order": index}
        for role in ("raw_deflate", "source"):
            value = member.get(role)
            if not isinstance(value, dict):
                raise CampaignFailure("scoring member %s lacks %s" % (name, role))
            path = resolve_scoring_file(value.get("file"), "%s %s" % (name, role))
            size = value.get("size")
            expected = require_sha256(value.get("sha256"), "%s %s" % (name, role))
            if type(size) is not int or size < 0 or path.stat().st_size != size:
                raise CampaignFailure("scoring member size changed: %s %s" % (name, role))
            actual = sha256_file(path)
            if actual != expected:
                raise CampaignFailure("scoring member hash changed: %s %s" % (name, role))
            record[role] = {
                "path": str(path),
                "relative": value["file"],
                "size": size,
                "sha256": actual,
            }
        total_source += record["source"]["size"]
        total_compressed += record["raw_deflate"]["size"]
        validated_members.append(record)
    aggregate = manifest.get("aggregate")
    if (
        not isinstance(aggregate, dict)
        or aggregate.get("member_count") != MEMBER_COUNT
        or aggregate.get("source_bytes") != SOURCE_BYTES_PER_PASS
        or aggregate.get("raw_deflate_bytes") != RAW_DEFLATE_BYTES
        or total_source != SOURCE_BYTES_PER_PASS
        or total_compressed != RAW_DEFLATE_BYTES
    ):
        raise CampaignFailure("scoring manifest aggregate is inconsistent")

    toolchain = manifest.get("toolchain")
    if not isinstance(toolchain, dict):
        raise CampaignFailure("scoring manifest toolchain is missing")
    build = toolchain.get("adapter_build")
    if (
        not isinstance(build, dict)
        or build.get("compiler_argv")
        != [str(CLANG), "--no-default-config", "-isysroot", str(MACOS_SDK)]
        or sha256_file(CLANG) != build.get("compiler_sha256")
    ):
        raise CampaignFailure("locked Clang identity changed")
    reference_binding = toolchain.get("zlib_ng_reference_decoder")
    if not isinstance(reference_binding, dict) or reference_binding.get("public_api_only") is not True:
        raise CampaignFailure("zlib-ng reference binding is not public-API-only")
    adapter_binding = reference_binding.get("adapter")
    library_binding = reference_binding.get("library")
    if not isinstance(adapter_binding, dict) or not isinstance(library_binding, dict):
        raise CampaignFailure("zlib-ng adapter or library binding is missing")
    bound_files = (
        (adapter_binding.get("artifact_file"), adapter_binding.get("artifact_sha256"), "reference adapter"),
        (adapter_binding.get("helper_file"), adapter_binding.get("helper_sha256"), "reference helper"),
        (adapter_binding.get("source_file"), adapter_binding.get("source_sha256"), "reference source"),
    )
    reference_files: Dict[str, Dict[str, str]] = {}
    for relative, expected_raw, label in bound_files:
        path = resolve_scoring_file(relative, label)
        expected = require_sha256(expected_raw, label)
        actual = sha256_file(path)
        if actual != expected:
            raise CampaignFailure("%s hash changed" % label)
        reference_files[label] = {"path": str(path), "sha256": actual}
    adapter_path = Path(reference_files["reference adapter"]["path"])
    reference_validation: Optional[Dict[str, Any]] = None
    if verify_reference:
        reference = load_reference_module()
        research_root = reference.DEFAULT_RESEARCH_ROOT
        checkout = research_root / "zlib-ng"
        build_dir = research_root / "build-zng-dispatch"
        library = reference.find_library(build_dir)
        provenance = reference.verify_provenance(checkout, build_dir, library)
        expected_provenance = {
            "version": library_binding.get("version"),
            "commit": library_binding.get("commit"),
            "tree": library_binding.get("tree"),
            "build_configuration": library_binding.get("build_configuration"),
            "generated_header_sha256": library_binding.get("generated_header_sha256"),
            "shared_library_sha256": library_binding.get("shared_library_sha256"),
        }
        for key, expected in expected_provenance.items():
            if provenance.get(key) != expected:
                raise CampaignFailure("zlib-ng provenance mismatch for %s" % key)
        cache_path = build_dir / "CMakeCache.txt"
        if sha256_file(cache_path) != library_binding.get("cmake_cache_sha256"):
            raise CampaignFailure("zlib-ng CMake cache hash changed")
        adapter = reference.load_adapter(adapter_path)
        status_cases = (
            reference.verify_status_contract(adapter) if exercise_reference else None
        )
        reference_validation = {
            "provenance": provenance,
            "cmake_cache": {
                "path": str(cache_path),
                "sha256": sha256_file(cache_path),
            },
            "status_contract_cases": status_cases,
            "decoder_calls_executed": exercise_reference,
        }
    return {
        "schema": manifest["schema"],
        "manifest": {"path": str(SCORING_MANIFEST), "sha256": sha256_file(SCORING_MANIFEST)},
        "members": validated_members,
        "aggregate": {
            "member_count": MEMBER_COUNT,
            "source_bytes": total_source,
            "raw_deflate_bytes": total_compressed,
        },
        "reference_adapter": {
            **reference_files["reference adapter"],
            "binding": adapter_binding,
        },
        "reference_files": reference_files,
        "reference_validation": reference_validation,
    }


LLVM_FUNCTION = re.compile(
    r"^define\b[^\n@]*@([A-Za-z_.$][A-Za-z0-9_.$-]*)\(", re.MULTILINE
)


def namespace_module(ir: str, namespace: str, entry: str) -> str:
    definitions = set(LLVM_FUNCTION.findall(ir))
    if "inflate_raw" not in definitions:
        raise CampaignFailure("compiled source lacks inflate_raw")
    replacements = {
        name: entry if name == "inflate_raw" else "xlang_%s_%s" % (namespace, name)
        for name in definitions
    }
    names = "|".join(re.escape(name) for name in sorted(definitions, key=len, reverse=True))
    transformed = re.sub(
        r"@(%s)(?=\()" % names,
        lambda match: "@" + replacements[match.group(1)],
        ir,
    )
    remaining = set(LLVM_FUNCTION.findall(transformed))
    expected = set(replacements.values())
    if remaining != expected:
        raise CampaignFailure("LLVM definition namespacing was incomplete")
    return transformed


def validate_proof_report(report: List[Dict[str, Any]], label: str) -> None:
    for site in report:
        if not isinstance(site, dict):
            raise CampaignFailure("%s proof report contains a non-object" % label)
        if site.get("status") not in ("proved", "retained", "ceiling"):
            raise CampaignFailure("%s proof report contains an unknown status" % label)
        if not isinstance(site.get("function"), str) or type(site.get("site")) is not int:
            raise CampaignFailure("%s proof report contains a malformed site" % label)


def proof_report_summary(path: Path, report: List[Dict[str, Any]]) -> Dict[str, Any]:
    statuses: Dict[str, int] = {}
    proofs: Dict[str, int] = {}
    for site in report:
        status = str(site.get("status"))
        proof = str(site.get("proof"))
        statuses[status] = statuses.get(status, 0) + 1
        proofs[proof] = proofs.get(proof, 0) + 1
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "site_count": len(report),
        "status_counts": dict(sorted(statuses.items())),
        "proof_counts": dict(sorted(proofs.items())),
        "ir_byte_identical_with_and_without_report": True,
        "collected_post_freeze": True,
    }


def compile_whitefoot(source_path: Path, source_sha: str, build: Path) -> Dict[str, Any]:
    expected_bytes = source_path.read_bytes()
    if hashlib.sha256(expected_bytes).hexdigest() != source_sha:
        raise CampaignFailure("frozen source changed before compilation")
    source = expected_bytes.decode("utf-8")
    sys.path.insert(0, str(DEMOC.parent))
    import democ  # type: ignore  # noqa: PLC0415

    verify_spec = importlib.util.spec_from_file_location(
        "whitefoot_raw_deflate_verify_for_benchmark", VERIFY
    )
    if verify_spec is None or verify_spec.loader is None:
        raise CampaignFailure("could not import verify.py for ABI validation")
    verify_module = importlib.util.module_from_spec(verify_spec)
    sys.modules[verify_spec.name] = verify_module
    verify_spec.loader.exec_module(verify_module)
    diagnostics = io.StringIO()
    try:
        with contextlib.redirect_stdout(diagnostics), contextlib.redirect_stderr(diagnostics):
            structs, _enums, functions, _contracts, _conforms, _consts = democ.parse_program(source)
            mismatch = verify_module.public_api_mismatch(source, structs, functions)
            if mismatch is not None:
                raise CampaignFailure("frozen source public API mismatch: " + mismatch)
            facts_ir = democ.compile_program(source, alias=True)
            nofacts_ir = democ.compile_program(source, alias=False)
            facts_report: List[Dict[str, Any]] = []
            nofacts_report: List[Dict[str, Any]] = []
            facts_report_ir = democ.compile_program(source, alias=True, proof_report=facts_report)
            nofacts_report_ir = democ.compile_program(source, alias=False, proof_report=nofacts_report)
    except CampaignFailure:
        raise
    except BaseException as error:
        detail = diagnostics.getvalue() or str(error) or type(error).__name__
        raise CampaignFailure("frozen source did not compile: " + detail) from error
    if source_path.read_bytes() != expected_bytes:
        raise CampaignFailure("frozen source changed during compilation")
    if facts_report_ir != facts_ir or nofacts_report_ir != nofacts_ir:
        raise CampaignFailure("requesting a proof report changed generated LLVM IR")
    validate_proof_report(facts_report, "facts-on")
    validate_proof_report(nofacts_report, "facts-off")
    facts_ll = build / "facts.ll"
    nofacts_ll = build / "nofacts.ll"
    facts_report_path = build / "facts-proof-report.json"
    nofacts_report_path = build / "nofacts-proof-report.json"
    facts_ll.write_text(
        namespace_module(facts_ir, "inflate_facts", "xlang_inflate_facts"),
        encoding="utf-8",
    )
    nofacts_ll.write_text(
        namespace_module(nofacts_ir, "inflate_nofacts", "xlang_inflate_nofacts"),
        encoding="utf-8",
    )
    facts_report_path.write_text(
        json.dumps(facts_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    nofacts_report_path.write_text(
        json.dumps(nofacts_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (build / "democ-output.txt").write_text(diagnostics.getvalue(), encoding="utf-8")
    return {
        "facts_ll": facts_ll,
        "nofacts_ll": nofacts_ll,
        "proof_reports": {
            "F": proof_report_summary(facts_report_path, facts_report),
            "N": proof_report_summary(nofacts_report_path, nofacts_report),
        },
        "source_sha256": source_sha,
        "identical_source_bytes": True,
        "only_compiler_toggle": "democ.compile_program(alias=True/False)",
    }


def assert_generic_command(command: Sequence[str]) -> None:
    lowered = " ".join(command).lower()
    found = [flag for flag in FORBIDDEN_BUILD_FLAGS if flag in lowered]
    if found:
        raise CampaignFailure("native build command contains forbidden flag(s): %s" % found)
    if list(command[:4]) != [str(CLANG), "--no-default-config", "-isysroot", str(MACOS_SDK)]:
        raise CampaignFailure("native build is not sealed to absolute Xcode Clang and SDK")


def build_candidate(
    mode: str,
    output: Path,
    scoring: Dict[str, Any],
    source_path: Optional[Path],
    source_sha: Optional[str],
) -> Tuple[Path, Dict[str, Any]]:
    build = output / "build"
    build.mkdir()
    environment, removed = sanitized_environment()
    commands: List[List[str]] = []
    proof_reports: Optional[Dict[str, Any]] = None
    if mode == "score":
        if source_path is None or source_sha is None:
            raise CampaignFailure("score build lost its frozen source")
        compiled = compile_whitefoot(source_path, source_sha, build)
        proof_reports = compiled["proof_reports"]
        facts_obj = build / "facts.o"
        nofacts_obj = build / "nofacts.o"
        for ll_path, obj_path, label in (
            (compiled["facts_ll"], facts_obj, "facts"),
            (compiled["nofacts_ll"], nofacts_obj, "nofacts"),
        ):
            command = [
                str(CLANG),
                "--no-default-config",
                "-isysroot",
                str(MACOS_SDK),
                "-O3",
                "-c",
                str(ll_path),
                "-o",
                str(obj_path),
            ]
            assert_generic_command(command)
            commands.append(command)
            run_logged(command, build / ("clang-%s.log" % label), env=environment)
        candidate = build / "libwhitefoot_raw_candidate.dylib"
        link = [
            str(CLANG),
            "--no-default-config",
            "-isysroot",
            str(MACOS_SDK),
            "-O3",
            "-dynamiclib",
            str(facts_obj),
            str(nofacts_obj),
            "-o",
            str(candidate),
        ]
    else:
        # This source is generated only inside a non-scoring output directory.
        # It forwards both Whitefoot ABI entries to the already-pinned public
        # comparator adapter, allowing ABI and worker validation without a model.
        smoke_source = build / "smoke-shim.c"
        smoke_source.write_text(
            "#include <stddef.h>\n#include <stdint.h>\n\n"
            "typedef struct { uint8_t *p; int64_t n; } Buf8;\n"
            "typedef struct { uint16_t *p; int64_t n; } Buf16;\n"
            "typedef struct { uint32_t *p; int64_t n; } Buf32;\n"
            "typedef struct { uint64_t status; uint64_t produced; } InflateResult;\n"
            "extern size_t wf_zng_raw_state_size(void);\n"
            "extern size_t wf_zng_raw_state_alignment(void);\n"
            "extern int32_t wf_zng_raw_prepare(void *, size_t, uint8_t *, size_t, const uint8_t *, size_t);\n"
            "extern int32_t wf_zng_raw_inflate_prepared(void *, size_t *);\n"
            "extern int32_t wf_zng_raw_end(void *);\n"
            "static void forward(Buf8 src, Buf8 out, InflateResult *result, Buf8 work8, Buf16 work16, Buf32 work32) {\n"
            "  size_t state_size = wf_zng_raw_state_size();\n"
            "  size_t state_alignment = wf_zng_raw_state_alignment();\n"
            "  uint8_t raw_state[state_size + state_alignment - 1];\n"
            "  uintptr_t aligned = ((uintptr_t)raw_state + state_alignment - 1) & ~(uintptr_t)(state_alignment - 1);\n"
            "  void *state = (void *)aligned;\n"
            "  size_t produced = 0;\n"
            "  int32_t status;\n"
            "  (void)work8; (void)work16; (void)work32;\n"
            "  status = wf_zng_raw_prepare(state, state_size, out.p, (size_t)out.n, src.p, (size_t)src.n);\n"
            "  if (status == 0) { status = wf_zng_raw_inflate_prepared(state, &produced); }\n"
            "  if (wf_zng_raw_end(state) != 0) { status = 2; }\n"
            "  result->status = (uint64_t)(uint32_t)status;\n"
            "  result->produced = (uint64_t)produced;\n"
            "}\n"
            "__attribute__((visibility(\"default\"))) void xlang_inflate_facts(Buf8 src, Buf8 out, InflateResult *result, Buf8 work8, Buf16 work16, Buf32 work32) { forward(src, out, result, work8, work16, work32); }\n"
            "__attribute__((visibility(\"default\"))) void xlang_inflate_nofacts(Buf8 src, Buf8 out, InflateResult *result, Buf8 work8, Buf16 work16, Buf32 work32) { forward(src, out, result, work8, work16, work32); }\n",
            encoding="utf-8",
        )
        candidate = build / "libwhitefoot_raw_smoke.dylib"
        adapter = Path(scoring["reference_adapter"]["path"])
        link = [
            str(CLANG),
            "--no-default-config",
            "-isysroot",
            str(MACOS_SDK),
            "-O3",
            "-std=c11",
            "-dynamiclib",
            str(smoke_source),
            str(adapter),
            "-Wl,-rpath," + str(adapter.parent),
            "-o",
            str(candidate),
        ]
    assert_generic_command(link)
    commands.append(link)
    run_logged(link, build / "clang-link.log", env=environment)
    if not candidate.is_file():
        raise CampaignFailure("native candidate library was not produced")
    artifacts: Dict[str, str] = {}
    for path in sorted(build.iterdir()):
        if path.is_file():
            artifacts[path.name] = sha256_file(path)
    return candidate, {
        "commands": commands,
        "sanitized_environment_removed": removed,
        "compiler": {
            "path": str(CLANG),
            "sha256": sha256_file(CLANG),
            "version": checked_capture([str(CLANG), "--version"]).stdout.strip(),
        },
        "sdk": {
            "path": str(MACOS_SDK),
            "settings_path": str(SDK_SETTINGS),
            "settings_sha256": sha256_file(SDK_SETTINGS),
        },
        "optimization": "-O3",
        "target": "generic/default (no native CPU flags)",
        "proof_reports": proof_reports,
        "artifacts_sha256": artifacts,
        "candidate": {"path": str(candidate), "sha256": sha256_file(candidate)},
    }


def check_abi_layout() -> None:
    if (
        ctypes.sizeof(Buf8) != 16
        or ctypes.sizeof(Buf16) != 16
        or ctypes.sizeof(Buf32) != 16
        or ctypes.sizeof(InflateResult) != 16
        or InflateResult.status.offset != 0
        or InflateResult.produced.offset != 8
    ):
        raise CampaignFailure("host ABI does not match the Whitefoot boundary")


def resolve_candidate_function(library: Any, symbol: str) -> Any:
    try:
        function = getattr(library, symbol)
    except AttributeError as error:
        raise CampaignFailure("candidate library lacks %s" % symbol) from error
    function.argtypes = [
        Buf8,
        Buf8,
        ctypes.POINTER(InflateResult),
        Buf8,
        Buf16,
        Buf32,
    ]
    function.restype = None
    return function


def first_mismatch(left: bytes, right: bytes) -> Optional[int]:
    if len(left) != len(right):
        return min(len(left), len(right))
    for index, (a, b) in enumerate(zip(left, right)):
        if a != b:
            return index
    return None


def expected_output_digest(members: Sequence[Dict[str, Any]], passes: int) -> str:
    digest = hashlib.sha256()
    for _ in range(passes):
        for member in members:
            with Path(member["source"]["path"]).open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
    return digest.hexdigest()


def run_worker(args: argparse.Namespace) -> int:
    check_abi_layout()
    mode = args.mode
    expected_passes = SCORE_PASSES if mode == "score" else SMOKE_PASSES
    if args.passes != expected_passes:
        raise CampaignFailure("worker pass count does not match its mode")
    if args.order not in ORDER_STRATA:
        raise CampaignFailure("worker order is not a frozen stratum")
    scoring = validate_scoring_manifest(
        verify_reference=True, exercise_reference=False
    )
    if scoring["manifest"]["sha256"] != args.manifest_sha256:
        raise CampaignFailure("scoring manifest changed before worker start")
    candidate_path = args.candidate.resolve()
    if sha256_file(candidate_path) != args.candidate_sha256:
        raise CampaignFailure("candidate library changed before worker start")
    reference_path = Path(scoring["reference_adapter"]["path"])
    if sha256_file(reference_path) != args.reference_sha256:
        raise CampaignFailure("reference adapter changed before worker start")
    reference = load_reference_module()
    adapter = reference.load_adapter(reference_path)
    comparator_state_size = int(adapter.wf_zng_raw_state_size())
    comparator_state_alignment = int(adapter.wf_zng_raw_state_alignment())
    if (
        comparator_state_size <= 0
        or comparator_state_alignment <= 0
        or comparator_state_alignment & (comparator_state_alignment - 1)
    ):
        raise CampaignFailure("reference adapter reported an invalid state layout")
    candidate_library = ctypes.CDLL(str(candidate_path))
    functions = {
        "F": resolve_candidate_function(candidate_library, "xlang_inflate_facts"),
        "N": resolve_candidate_function(candidate_library, "xlang_inflate_nofacts"),
    }

    loaded: List[Dict[str, Any]] = []
    for member in scoring["members"]:
        compressed = Path(member["raw_deflate"]["path"]).read_bytes()
        expected = Path(member["source"]["path"]).read_bytes()
        source_storage = AlignedBuffer(len(compressed))
        source_storage.set_bytes(compressed)
        loaded.append(
            {
                "name": member["name"],
                "compressed": compressed,
                "expected": expected,
                "source_storage": source_storage,
                "compressed_sha256": member["raw_deflate"]["sha256"],
                "source_sha256": member["source"]["sha256"],
            }
        )
    maximum_output = max(len(item["expected"]) for item in loaded)
    output = AlignedBuffer(maximum_output)
    work8 = AlignedBuffer(WORK8_LENGTH)
    work16 = AlignedBuffer(WORK16_LENGTH * 2)
    work32 = AlignedBuffer(WORK32_LENGTH * 4)
    result = InflateResult()
    result_pointer = ctypes.pointer(result)
    comparator_produced = ctypes.c_size_t()
    comparator_states = [
        AlignedBuffer(
            comparator_state_size,
            max(ALIGNMENT, comparator_state_alignment),
        )
        for _ in range(args.passes * MEMBER_COUNT)
    ]
    if any(
        state.address % comparator_state_alignment != 0
        for state in comparator_states
    ):
        raise CampaignFailure("reference state storage is incorrectly aligned")
    expected_digest = expected_output_digest(scoring["members"], args.passes)
    samples: List[Dict[str, Any]] = []
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        for ordinal, variant in enumerate(args.order.split(",")):
            digest = hashlib.sha256()
            elapsed_ns = 0
            call_count = 0
            for pass_index in range(args.passes):
                for member_index, item in enumerate(loaded):
                    expected = item["expected"]
                    capacity = len(expected)
                    poison = (0xA5 ^ (ordinal * 29) ^ (pass_index * 17) ^ member_index) & 0xFF
                    output.poison(poison)
                    if variant in ("F", "N"):
                        work8.poison(poison ^ 0x33)
                        work16.poison(poison ^ 0x55)
                        work32.poison(poison ^ 0x77)
                        result.status = 0xD3D3D3D3D3D3D3D3 ^ call_count
                        result.produced = 0xE4E4E4E4E4E4E4E4 ^ call_count
                        arguments = (
                            Buf8(item["source_storage"].pointer8, len(item["compressed"])),
                            Buf8(output.pointer8, capacity),
                            result_pointer,
                            Buf8(work8.pointer8, WORK8_LENGTH),
                            Buf16(work16.pointer16(), WORK16_LENGTH),
                            Buf32(work32.pointer32(), WORK32_LENGTH),
                        )
                        started = time.perf_counter_ns()
                        functions[variant](*arguments)
                        finished = time.perf_counter_ns()
                        status = int(result.status)
                        produced = int(result.produced)
                    else:
                        state = comparator_states[call_count]
                        state.poison(poison ^ 0x99)
                        comparator_produced.value = ctypes.c_size_t(-1).value
                        prepared = int(
                            adapter.wf_zng_raw_prepare(
                                ctypes.c_void_p(state.address),
                                comparator_state_size,
                                output.pointer8,
                                capacity,
                                item["source_storage"].pointer8,
                                len(item["compressed"]),
                            )
                        )
                        if prepared != 0:
                            raise CampaignFailure(
                                "Z %s prepare returned status=%d"
                                % (item["name"], prepared)
                            )
                        started = time.perf_counter_ns()
                        raw_status = adapter.wf_zng_raw_inflate_prepared(
                            ctypes.c_void_p(state.address),
                            ctypes.byref(comparator_produced),
                        )
                        finished = time.perf_counter_ns()
                        status = int(raw_status)
                        ended = int(
                            adapter.wf_zng_raw_end(ctypes.c_void_p(state.address))
                        )
                        if ended != 0:
                            raise CampaignFailure(
                                "Z %s end returned status=%d"
                                % (item["name"], ended)
                            )
                        produced = int(comparator_produced.value)
                    elapsed = finished - started
                    if elapsed <= 0:
                        raise CampaignFailure("monotonic timer did not advance")
                    elapsed_ns += elapsed
                    call_count += 1
                    if status != 0 or produced != capacity:
                        raise CampaignFailure(
                            "%s %s returned status=%d produced=%d expected=%d"
                            % (variant, item["name"], status, produced, capacity)
                        )
                    actual = ctypes.string_at(output.address, capacity)
                    if actual != expected:
                        raise CampaignFailure(
                            "%s %s output mismatch at byte %s"
                            % (variant, item["name"], first_mismatch(actual, expected))
                        )
                    digest.update(actual)
            output_sha = digest.hexdigest()
            if output_sha != expected_digest:
                raise CampaignFailure("%s aggregate output digest changed" % variant)
            samples.append(
                {
                    "variant": variant,
                    "ordinal": ordinal,
                    "decoded_bytes": SOURCE_BYTES_PER_PASS * args.passes,
                    "elapsed_ns": elapsed_ns,
                    "call_count": call_count,
                    "passes": args.passes,
                    "member_count": MEMBER_COUNT,
                    "output_sha256": output_sha,
                }
            )
    finally:
        if gc_was_enabled:
            gc.enable()

    # Re-read every input through the exact addresses supplied to all variants.
    # This full identity check is after all timed calls.
    for item in loaded:
        if hashlib.sha256(item["source_storage"].bytes()).hexdigest() != item["compressed_sha256"]:
            raise CampaignFailure("decoder changed scoring input: %s" % item["name"])
    if sha256_file(candidate_path) != args.candidate_sha256:
        raise CampaignFailure("candidate library changed during worker execution")
    if sha256_file(reference_path) != args.reference_sha256:
        raise CampaignFailure("reference adapter changed during worker execution")
    final_scoring = validate_scoring_manifest(
        verify_reference=False, exercise_reference=False
    )
    if final_scoring["manifest"]["sha256"] != args.manifest_sha256:
        raise CampaignFailure("scoring artifacts changed during worker execution")
    record = {
        "schema_version": 1,
        "kind": "raw-deflate-benchmark-block",
        "mode": mode,
        "not_a_score": mode == "smoke",
        "block_index": args.block_index,
        "order": args.order,
        "order_stratum": args.order,
        "worker_pid": os.getpid(),
        "passes": args.passes,
        "member_count": MEMBER_COUNT,
        "decoded_bytes_per_variant": SOURCE_BYTES_PER_PASS * args.passes,
        "expected_output_sha256": expected_digest,
        "samples": samples,
        "alignment": {
            "bytes": ALIGNMENT,
            "all_input_modulo": sorted(
                {item["source_storage"].address % ALIGNMENT for item in loaded}
            ),
            "output_modulo": output.address % ALIGNMENT,
            "result_modulo": ctypes.addressof(result) % ctypes.alignment(InflateResult),
            "same_input_pointer_for_all_variants": True,
            "same_output_pointer_for_all_variants": True,
            "same_result_pointer_for_F_and_N": True,
            "comparator_state_size": comparator_state_size,
            "comparator_state_alignment": comparator_state_alignment,
            "all_comparator_state_modulo": sorted(
                {
                    state.address % comparator_state_alignment
                    for state in comparator_states
                }
            ),
            "fresh_comparator_state_per_call": True,
        },
        "timing_boundary": {
            "F_and_N": "perf_counter_ns immediately around exactly one Whitefoot decoder call",
            "Z": "perf_counter_ns immediately around exactly one wf_zng_raw_inflate_prepared call",
        },
        "comparator_lifecycle": {
            "prepare": "wf_zng_raw_prepare outside timing; status checked",
            "decode": "wf_zng_raw_inflate_prepared inside timing; status and output checked",
            "end": "wf_zng_raw_end outside timing; status checked",
            "one_shot_used_for_measurement": False,
        },
        "warmup_policy": {
            "candidate_decoder_calls_before_samples": 0,
            "comparator_decoder_calls_before_samples": 0,
            "reference_validation_in_worker": "hash/provenance/load-only",
        },
        "preparation_outside_timing": [
            "allocation",
            "prefault-by-memset",
            "output poison",
            "result poison",
            "scratch poison",
            "all hashing and byte verification",
            "zlib-ng public prepare and end",
        ],
        "identities": {
            "candidate_sha256": args.candidate_sha256,
            "reference_adapter_sha256": args.reference_sha256,
            "scoring_manifest_sha256": args.manifest_sha256,
        },
    }
    print(json.dumps(record, sort_keys=True, separators=(",", ":")))
    return 0


def schedule(repetitions: int) -> List[str]:
    orders = list(ORDER_STRATA) * repetitions
    rng = XorShift64Star(ORDER_SEED)
    for index in range(len(orders) - 1, 0, -1):
        swap = rng.next() % (index + 1)
        orders[index], orders[swap] = orders[swap], orders[index]
    validate_schedule(orders, repetitions)
    return orders


def validate_schedule(orders: Sequence[str], repetitions: int) -> None:
    if len(orders) != len(ORDER_STRATA) * repetitions:
        raise CampaignFailure("schedule length is wrong")
    for stratum in ORDER_STRATA:
        if orders.count(stratum) != repetitions:
            raise CampaignFailure("schedule stratum is not balanced")
    for variant in VARIANTS:
        for ordinal in range(3):
            if sum(order.split(",")[ordinal] == variant for order in orders) != 2 * repetitions:
                raise CampaignFailure("schedule ordinal positions are not balanced")


def command_observation(argv: Sequence[str]) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            list(argv),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        return {
            "argv": list(argv),
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except (OSError, subprocess.SubprocessError) as error:
        return {"argv": list(argv), "unavailable": True, "error": str(error)}


def exact_host_snapshot() -> Dict[str, Any]:
    hardware_argv = [str(SYSTEM_PROFILER), "SPHardwareDataType", "-json"]
    hardware_raw = checked_capture(hardware_argv, timeout=120).stdout
    try:
        hardware_value = json.loads(hardware_raw)
        rows = hardware_value["SPHardwareDataType"]
        hardware = rows[0]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise CampaignFailure("system_profiler returned an unexpected hardware record") from error
    processor_description = hardware.get("number_processors")
    match = re.fullmatch(r"proc ([0-9]+):[0-9]+:[0-9]+:[0-9]+", str(processor_description))
    if match is None:
        raise CampaignFailure("system_profiler returned an unknown processor description")
    product_argv = [str(SW_VERS), "-productVersion"]
    build_argv = [str(SW_VERS), "-buildVersion"]
    snapshot = {
        "machine_model": hardware.get("machine_model"),
        "chip_type": hardware.get("chip_type"),
        "processor_description": processor_description,
        "processor_core_count": int(match.group(1)),
        "physical_memory": hardware.get("physical_memory"),
        "architecture": platform.machine(),
        "macos_product_version": checked_capture(product_argv, timeout=30).stdout.strip(),
        "macos_build_version": checked_capture(build_argv, timeout=30).stdout.strip(),
        "platform": platform.platform(),
    }
    # Retain only the non-identifying fields used by the frozen host gate.  The
    # raw hardware record also contains serial and device identifiers and must
    # not be copied into campaign artifacts.
    return {
        **snapshot,
        "commands": {
            "hardware": hardware_argv,
            "product_version": product_argv,
            "build_version": build_argv,
        },
        "raw_hardware_record_retained": False,
        "matches_frozen_score_host": snapshot == EXPECTED_SCORE_HOST,
    }


def parse_ac_low_power_mode(custom: Dict[str, Any]) -> Optional[int]:
    if custom.get("returncode") != 0:
        return None
    section: Optional[str] = None
    for raw_line in custom.get("stdout", "").splitlines():
        line = raw_line.strip()
        if line.endswith(":"):
            section = line[:-1]
            continue
        if section == "AC Power":
            parts = line.split()
            if len(parts) == 2 and parts[0] == "lowpowermode":
                try:
                    return int(parts[1])
                except ValueError:
                    return None
    return None


def power_snapshot() -> Dict[str, Any]:
    battery = command_observation([str(PMSET), "-g", "batt"])
    first_line = battery.get("stdout", "").splitlines()[:1]
    match = re.search(r"Now drawing from '([^']+)'", first_line[0] if first_line else "")
    thermal = command_observation([str(PMSET), "-g", "therm"])
    thermal_stdout = thermal.get("stdout", "")
    thermal_available = (
        thermal.get("returncode") == 0
        and bool(thermal_stdout.strip())
        and "error:" not in thermal_stdout.lower()
    )
    custom = command_observation([str(PMSET), "-g", "custom"])
    low_power_mode = parse_ac_low_power_mode(custom)
    return {
        "captured_at": utc_now(),
        "power_source": match.group(1) if match else None,
        "power_source_available": match is not None,
        "power_probe": battery,
        "ac_low_power_mode": low_power_mode,
        "ac_low_power_mode_available": low_power_mode is not None,
        "power_policy_probe": custom,
        "thermal": {
            "available": thermal_available,
            "stdout": thermal_stdout,
            "returncode": thermal.get("returncode"),
            "stderr": thermal.get("stderr", ""),
        },
    }


def enforce_score_environment(host: Dict[str, Any], power: Dict[str, Any]) -> None:
    selected_host = {key: host.get(key) for key in EXPECTED_SCORE_HOST}
    if selected_host != EXPECTED_SCORE_HOST or host.get("matches_frozen_score_host") is not True:
        raise CampaignFailure(
            "score host differs from the frozen Mac16,12 / 10-core Apple M4 / 16 GB / macOS 26.5.1 (25F80) host"
        )
    if not power.get("power_source_available") or power.get("power_source") != "AC Power":
        raise CampaignFailure("score requires AC Power")
    if (
        power.get("ac_low_power_mode_available") is not True
        or power.get("ac_low_power_mode") != 0
    ):
        raise CampaignFailure("score requires AC lowpowermode=0")
    if power.get("thermal", {}).get("available") is not False:
        raise CampaignFailure(
            "score protocol freezes pmset thermal monitoring as unavailable on this host"
        )


def power_transition(before: Dict[str, Any], after: Dict[str, Any]) -> Optional[str]:
    if before["power_source_available"] != after["power_source_available"]:
        return "power-source availability changed"
    if before["power_source_available"] and before["power_source"] != after["power_source"]:
        return "power source changed from %s to %s" % (
            before["power_source"],
            after["power_source"],
        )
    if before["ac_low_power_mode_available"] != after["ac_low_power_mode_available"]:
        return "AC low-power-mode availability changed"
    if (
        before["ac_low_power_mode_available"]
        and before["ac_low_power_mode"] != after["ac_low_power_mode"]
    ):
        return "AC lowpowermode changed from %s to %s" % (
            before["ac_low_power_mode"],
            after["ac_low_power_mode"],
        )
    before_thermal = before["thermal"]
    after_thermal = after["thermal"]
    if before_thermal["available"] != after_thermal["available"]:
        return "thermal-state availability changed"
    if before_thermal["available"] and before_thermal["stdout"] != after_thermal["stdout"]:
        return "pmset thermal state changed"
    return None


def parse_single_json(stdout: str, label: str) -> Dict[str, Any]:
    lines = [line for line in stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise CampaignFailure("%s emitted %d nonempty stdout lines" % (label, len(lines)))
    try:
        value = json.loads(lines[0])
    except json.JSONDecodeError as error:
        raise CampaignFailure("%s emitted invalid JSON" % label) from error
    if not isinstance(value, dict):
        raise CampaignFailure("%s JSON is not an object" % label)
    return value


def validate_block_record(
    record: Dict[str, Any],
    mode: str,
    block_index: int,
    order: str,
    passes: int,
    expected_output_sha: str,
    candidate_sha: str,
    reference_sha: str,
    manifest_sha: str,
) -> None:
    expected_bytes = SOURCE_BYTES_PER_PASS * passes
    if (
        record.get("kind") != "raw-deflate-benchmark-block"
        or record.get("mode") != mode
        or record.get("not_a_score") is not (mode == "smoke")
        or record.get("block_index") != block_index
        or record.get("order") != order
        or record.get("order_stratum") != order
        or record.get("passes") != passes
        or record.get("member_count") != MEMBER_COUNT
        or record.get("decoded_bytes_per_variant") != expected_bytes
        or record.get("expected_output_sha256") != expected_output_sha
    ):
        raise CampaignFailure("benchmark worker returned the wrong block identity")
    samples = record.get("samples")
    if not isinstance(samples, list) or len(samples) != 3:
        raise CampaignFailure("benchmark worker did not return exactly three samples")
    for ordinal, (variant, sample) in enumerate(zip(order.split(","), samples)):
        if (
            not isinstance(sample, dict)
            or sample.get("variant") != variant
            or sample.get("ordinal") != ordinal
            or sample.get("decoded_bytes") != expected_bytes
            or sample.get("passes") != passes
            or sample.get("member_count") != MEMBER_COUNT
            or sample.get("call_count") != passes * MEMBER_COUNT
            or type(sample.get("elapsed_ns")) is not int
            or sample["elapsed_ns"] <= 0
            or sample.get("output_sha256") != expected_output_sha
        ):
            raise CampaignFailure("benchmark worker returned a malformed sample")
    alignment = record.get("alignment", {})
    state_alignment = alignment.get("comparator_state_alignment")
    if (
        alignment.get("all_input_modulo") != [0]
        or alignment.get("output_modulo") != 0
        or type(alignment.get("comparator_state_size")) is not int
        or alignment["comparator_state_size"] <= 0
        or type(state_alignment) is not int
        or state_alignment <= 0
        or state_alignment & (state_alignment - 1)
        or alignment.get("all_comparator_state_modulo") != [0]
        or alignment.get("fresh_comparator_state_per_call") is not True
    ):
        raise CampaignFailure("benchmark worker did not preserve locked pointer alignment")
    if record.get("comparator_lifecycle", {}).get("one_shot_used_for_measurement") is not False:
        raise CampaignFailure("benchmark worker used the comparator one-shot timing path")
    if record.get("warmup_policy") != {
        "candidate_decoder_calls_before_samples": 0,
        "comparator_decoder_calls_before_samples": 0,
        "reference_validation_in_worker": "hash/provenance/load-only",
    }:
        raise CampaignFailure("benchmark worker performed an asymmetric warmup")
    if record.get("identities") != {
        "candidate_sha256": candidate_sha,
        "reference_adapter_sha256": reference_sha,
        "scoring_manifest_sha256": manifest_sha,
    }:
        raise CampaignFailure("benchmark worker returned stale artifact identities")


INTERRUPTED = False


def note_signal(signum: int, _frame: Any) -> None:
    global INTERRUPTED
    INTERRUPTED = True
    raise KeyboardInterrupt("received signal %d" % signum)


def campaign_source_hashes() -> Dict[str, str]:
    paths = (
        Path(__file__).resolve(),
        ANALYZER,
        PROTOCOL,
        SCORING_MANIFEST,
        REFERENCE_HELPER,
        REFERENCE_SOURCE,
        VERIFY,
        RUN_GENERATION,
        GENERATION_INPUTS,
        DEMOC,
    )
    return {str(path): sha256_file(path) for path in paths if path.is_file()}


def run_campaign(args: argparse.Namespace) -> int:
    mode = args.command
    if args.out_dir.exists():
        raise CampaignFailure("refusing to reuse output directory %s" % args.out_dir.resolve())
    if mode == "score" and not args.acknowledge_preregistered_score:
        raise CampaignFailure(
            "score requires --acknowledge-preregistered-score; use smoke for validation"
        )
    if Path(sys.executable).resolve() != PYTHON.resolve():
        raise CampaignFailure("campaign must run under locked Python %s" % PYTHON)
    host_before_preparation = exact_host_snapshot()
    power_before_preparation = power_snapshot()
    if mode == "score":
        enforce_score_environment(host_before_preparation, power_before_preparation)

    repository: Optional[Dict[str, Any]] = None
    freeze: Optional[Dict[str, Any]] = None
    source_path: Optional[Path] = None
    source_sha: Optional[str] = None
    if mode == "score":
        repository = preregistration_identity()
        freeze, source_path, source_sha = validate_freeze_manifest(
            args.trace_manifest, repository
        )
    scoring = validate_scoring_manifest(
        verify_reference=True, exercise_reference=True
    )
    output = args.out_dir.resolve()
    output.mkdir(parents=True)
    passes = SCORE_PASSES if mode == "score" else SMOKE_PASSES
    repetitions = 5 if mode == "score" else 1
    metadata: Dict[str, Any] = {
        "schema_version": 1,
        "kind": "raw-deflate-campaign",
        "mode": mode,
        "not_a_score": mode == "smoke",
        "status": "preparing",
        "created_at": utc_now(),
        "repository": repository,
        "protocol_sha256": sha256_file(PROTOCOL),
        "generation_freeze": freeze,
        "frozen_source": (
            {"path": str(source_path), "sha256": source_sha}
            if source_path is not None
            else None
        ),
        "scoring": scoring,
        "source_and_tool_sha256": campaign_source_hashes(),
        "host": {
            **host_before_preparation,
            "python": platform.python_version(),
            "python_executable": str(Path(sys.executable).resolve()),
            "python_sha256": sha256_file(Path(sys.executable).resolve()),
        },
        "clock": "Python time.perf_counter_ns immediately around one ctypes call",
        "timings_or_results_exposed_to_generation_or_evaluator": False,
        "proof_reports_exposed_to_generation_or_evaluator": False,
        "warmup_policy": {
            "candidate_warmup_calls_per_worker": 0,
            "comparator_warmup_calls_per_worker": 0,
            "reference_status_contract_exercised_only_in_parent_before_workers": True,
        },
        "power_before_preparation": power_before_preparation,
        "thermal_monitoring": {
            "available": False,
            "enforced": False,
            "probe": "pmset -g therm",
            "limitation": (
                "The host does not expose thermal warning/performance state through "
                "pmset. No thermal-stability claim is made."
            ),
            "mitigation": (
                "All six F/N/Z orders are balanced and repeated five times under "
                "the frozen deterministic shuffle."
            ),
        },
    }
    metadata_path = output / "metadata.json"
    atomic_json(metadata_path, metadata)
    try:
        if freeze is not None:
            metadata["generation_archive"] = archive_generation(output, freeze)
        candidate, build = build_candidate(
            mode, output, scoring, source_path, source_sha
        )
        candidate_sha = sha256_file(candidate)
        reference_sha = scoring["reference_adapter"]["sha256"]
        manifest_sha = scoring["manifest"]["sha256"]
        expected_output_sha = expected_output_digest(scoring["members"], passes)
        orders = schedule(repetitions)
        schedule_value = {
            "schema_version": 1,
            "mode": mode,
            "not_a_score": mode == "smoke",
            "variants": list(VARIANTS),
            "variant_meanings": {
                "F": "frozen Whitefoot facts-on",
                "N": "identical frozen Whitefoot facts-off",
                "Z": "zlib-ng 2.3.3 public prepared raw inflate kernel",
            },
            "strata_order": list(ORDER_STRATA),
            "repetitions_per_stratum": repetitions,
            "seed_hex": "0x%016x" % ORDER_SEED,
            "shuffle": "descending Fisher-Yates; i=n-1..1, j=next()%(i+1)",
            "orders": [
                {"block_index": index, "order": order}
                for index, order in enumerate(orders)
            ],
        }
        schedule_path = output / "schedule.json"
        atomic_json(schedule_path, schedule_value)
        environment, measurement_removed = sanitized_environment()
        host_before_measurement = exact_host_snapshot()
        power_before_measurement = power_snapshot()
        if mode == "score":
            enforce_score_environment(host_before_measurement, power_before_measurement)
        metadata.update(
            {
                "status": "running",
                "prepared_at": utc_now(),
                "passes_per_sample": passes,
                "decoded_bytes_per_variant": SOURCE_BYTES_PER_PASS * passes,
                "calls_per_variant": MEMBER_COUNT * passes,
                "blocks_expected": len(orders),
                "fresh_child_process_per_block": True,
                "build": build,
                "candidate": {"path": str(candidate), "sha256": candidate_sha},
                "expected_output_sequence_sha256": expected_output_sha,
                "schedule_sha256": sha256_file(schedule_path),
                "measurement_environment": {
                    "removed_override_variable_names": measurement_removed,
                    "dynamic_loader_injection_scrubbed": True,
                },
                "host_before_measurement": host_before_measurement,
                "power_before_measurement": power_before_measurement,
            }
        )
        atomic_json(metadata_path, metadata)

        raw_path = output / "raw.jsonl"
        previous_power = metadata["power_before_measurement"]
        with raw_path.open("x", encoding="utf-8") as raw:
            for block_index, order in enumerate(orders):
                if INTERRUPTED:
                    raise KeyboardInterrupt("campaign interrupted")
                if sha256_file(candidate) != candidate_sha:
                    raise CampaignFailure("candidate changed before block %d" % block_index)
                before = power_snapshot()
                gap_transition = power_transition(previous_power, before)
                if gap_transition is not None:
                    raise CampaignFailure(
                        "campaign invalidated before block %d: %s"
                        % (block_index, gap_transition)
                    )
                command = [
                    str(Path(sys.executable).resolve()),
                    str(Path(__file__).resolve()),
                    "_worker",
                    "--mode",
                    mode,
                    "--candidate",
                    str(candidate),
                    "--candidate-sha256",
                    candidate_sha,
                    "--reference-sha256",
                    reference_sha,
                    "--manifest-sha256",
                    manifest_sha,
                    "--block-index",
                    str(block_index),
                    "--order",
                    order,
                    "--passes",
                    str(passes),
                ]
                started_at = utc_now()
                completed = subprocess.run(
                    command,
                    cwd=ROOT,
                    env=environment,
                    check=False,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=args.block_timeout,
                )
                finished_at = utc_now()
                after = power_snapshot()
                log_path = output / ("block-%02d.log" % block_index)
                log_path.write_text(
                    "argv: "
                    + json.dumps(command)
                    + "\n\nstdout:\n"
                    + completed.stdout
                    + "\n\nstderr:\n"
                    + completed.stderr,
                    encoding="utf-8",
                )
                if completed.returncode != 0:
                    raise CampaignFailure(
                        "block %d crashed or failed (%d); see %s"
                        % (block_index, completed.returncode, log_path)
                    )
                record = parse_single_json(completed.stdout, "block %d" % block_index)
                validate_block_record(
                    record,
                    mode,
                    block_index,
                    order,
                    passes,
                    expected_output_sha,
                    candidate_sha,
                    reference_sha,
                    manifest_sha,
                )
                transition = power_transition(before, after)
                record.update(
                    {
                        "process_command": command,
                        "started_at": started_at,
                        "finished_at": finished_at,
                        "power_before": before,
                        "power_after": after,
                        "power_policy_transition": transition,
                        "child_stderr": completed.stderr,
                    }
                )
                raw.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
                raw.flush()
                os.fsync(raw.fileno())
                if transition is not None:
                    raise CampaignFailure(
                        "block %d invalidated by %s" % (block_index, transition)
                    )
                previous_power = after

        final_power = power_snapshot()
        final_host = exact_host_snapshot()
        if mode == "score":
            enforce_score_environment(final_host, final_power)
        transition = power_transition(previous_power, final_power)
        if transition is not None:
            raise CampaignFailure("campaign invalidated after final block: " + transition)
        if sha256_file(candidate) != candidate_sha:
            raise CampaignFailure("candidate changed during the campaign")
        if campaign_source_hashes() != metadata["source_and_tool_sha256"]:
            raise CampaignFailure("campaign source or compiler changed during measurement")
        final_scoring = validate_scoring_manifest(
            verify_reference=True, exercise_reference=True
        )
        if final_scoring["manifest"]["sha256"] != manifest_sha:
            raise CampaignFailure("scoring manifest changed during measurement")
        if mode == "score":
            assert repository is not None and freeze is not None
            if preregistration_identity() != repository:
                raise CampaignFailure("preregistration repository identity changed")
            final_freeze, final_source, final_source_sha = validate_freeze_manifest(
                args.trace_manifest, repository
            )
            if final_freeze != freeze or final_source != source_path or final_source_sha != source_sha:
                raise CampaignFailure("frozen generation identity changed")
            if strict_tree_manifest(Path(metadata["generation_archive"]["path"])) != metadata["generation_archive"]["files_sha256"]:
                raise CampaignFailure("archived generation freeze changed")
        metadata.update(
            {
                "status": "complete",
                "completed_at": utc_now(),
                "blocks_completed": len(orders),
                "raw_sha256": sha256_file(raw_path),
                "power_after_measurement": final_power,
                "host_after_measurement": final_host,
            }
        )
        atomic_json(metadata_path, metadata)
        if mode == "score":
            analysis_command = [str(PYTHON), str(ANALYZER), str(output)]
            analysis = run_logged(
                analysis_command, output / "analysis.log", env=environment, timeout=300
            )
            parse_single_json(analysis.stdout, "analysis")
            metadata["analysis"] = {
                "path": str(output / "analysis.json"),
                "sha256": sha256_file(output / "analysis.json"),
                "command": analysis_command,
            }
            atomic_json(metadata_path, metadata)
        else:
            atomic_json(
                output / "SMOKE_ONLY.json",
                {
                    "schema_version": 1,
                    "mode": "smoke",
                    "not_a_score": True,
                    "validation_passed": True,
                    "passes_per_sample": SMOKE_PASSES,
                    "message": (
                        "Harness validation only. F and N used a zlib-ng-backed "
                        "Whitefoot-ABI shim; these timings are not a score."
                    ),
                },
            )
        print(
            json.dumps(
                {
                    "status": "complete",
                    "mode": mode,
                    "not_a_score": mode == "smoke",
                    "output": str(output),
                },
                sort_keys=True,
            )
        )
        return 0
    except BaseException as error:
        metadata.update(
            {
                "status": "invalid",
                "invalidated_at": utc_now(),
                "invalidation_reason": str(error) or type(error).__name__,
                "interrupted": isinstance(error, KeyboardInterrupt) or INTERRUPTED,
            }
        )
        atomic_json(metadata_path, metadata)
        raise


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    score = subparsers.add_parser("score", help="run the preregistered score")
    score.add_argument("--out-dir", type=Path, required=True)
    score.add_argument(
        "--trace-manifest", type=Path, default=TARGET_TRACE_MANIFEST
    )
    score.add_argument("--acknowledge-preregistered-score", action="store_true")
    score.add_argument("--block-timeout", type=int, default=3600)
    smoke = subparsers.add_parser("smoke", help="run non-scoring harness validation")
    smoke.add_argument("--out-dir", type=Path, required=True)
    smoke.add_argument("--block-timeout", type=int, default=1800)
    worker = subparsers.add_parser("_worker", help=argparse.SUPPRESS)
    worker.add_argument("--mode", choices=("score", "smoke"), required=True)
    worker.add_argument("--candidate", type=Path, required=True)
    worker.add_argument("--candidate-sha256", required=True)
    worker.add_argument("--reference-sha256", required=True)
    worker.add_argument("--manifest-sha256", required=True)
    worker.add_argument("--block-index", type=int, required=True)
    worker.add_argument("--order", required=True)
    worker.add_argument("--passes", type=int, required=True)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args.command == "_worker":
        return run_worker(args)
    previous: Dict[int, Any] = {}
    for signum in (signal.SIGINT, signal.SIGTERM):
        previous[signum] = signal.signal(signum, note_signal)
    try:
        return run_campaign(args)
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CampaignFailure, OSError, UnicodeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print("benchmark failed: %s" % error, file=sys.stderr)
        raise SystemExit(2)
