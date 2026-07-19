#!/usr/bin/env python3
"""Launch the single preregistered raw-DEFLATE generation trajectory."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT_FLOOR = HERE.parent / "default-floor"
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
CODEX = Path("/opt/homebrew/bin/codex")
ADAPTER = DEFAULT_FLOOR / "codex_model_adapter.py"
GENERATOR = DEFAULT_FLOOR / "generate.py"
EVALUATOR = HERE / "verify.py"
PROMPT = HERE / "base-prompt.txt"
INPUT_MANIFEST = HERE / "generation-inputs.json"
LAUNCHER_RELATIVE = "experiments/raw-deflate-default-shape/run_generation.py"
LAUNCHER_HASH_PATTERN = re.compile(
    rb'(?m)^INPUT_MANIFEST_SHA256 = "[0-9a-f]*"$'
)
LAUNCHER_HASH_REPLACEMENT = (
    b'INPUT_MANIFEST_SHA256 = "' + (b"0" * 64) + b'"'
)
RUN_DIR = HERE / "runs" / "primary-terra-medium-preregistered"
MODEL = "gpt-5.6-terra"
EXPECTED_HOST = {
    "architecture": "arm64",
    "build_version": "25F80",
    "chip_type": "Apple M4",
    "low_power_mode": 0,
    "machine_model": "Mac16,12",
    "number_processors": "proc 10:4:6:0",
    "physical_memory": "16 GB",
    "power_source": "AC Power",
    "product_version": "26.5.1",
    "thermal_probe": "unavailable",
}
PROMPT_SEPARATOR = b"\n===== BEGIN COMPLETE WHITEFOOT WRITER'S PACK =====\n\n"
PATTERN_SEPARATOR = (
    b"\n===== BEGIN COMPLETE WHITEFOOT PATTERN DOCTRINE =====\n\n"
    b"The following is the project's complete architecture guidance. It does not "
    b"add syntax: only forms admitted by the preceding stage-0 writer's pack are "
    b"available for this task.\n\n"
)

# Filled only after every preregistered input and measurement tool is final.
INPUT_MANIFEST_SHA256 = ""


class PreflightFailure(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def input_sha256(relative: str, path: Path) -> str:
    if relative != LAUNCHER_RELATIVE:
        return sha256_file(path)
    normalized, replacements = LAUNCHER_HASH_PATTERN.subn(
        LAUNCHER_HASH_REPLACEMENT, path.read_bytes()
    )
    if replacements != 1:
        raise PreflightFailure("generation launcher has no unique manifest-hash binding")
    return hashlib.sha256(normalized).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def run(
    command: Sequence[str],
    *,
    cwd: Path = ROOT,
    timeout: int = 300,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        env=env,
    )


def checked_output(command: Sequence[str], *, cwd: Path = ROOT) -> str:
    completed = run(command, cwd=cwd)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise PreflightFailure(f"metadata command failed: {command[0]}: {detail}")
    return completed.stdout.strip()


def resolve_repo_file(relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or not pure.parts or ".." in pure.parts:
        raise PreflightFailure(f"input manifest path escapes repository: {relative!r}")
    path = (ROOT / Path(*pure.parts)).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as error:
        raise PreflightFailure(f"input manifest path resolves outside repository: {relative}") from error
    if path.is_symlink() or not path.is_file():
        raise PreflightFailure(f"input manifest path is not a regular file: {relative}")
    return path


def load_input_manifest() -> tuple[dict[str, Any], dict[str, str]]:
    if not INPUT_MANIFEST_SHA256:
        raise PreflightFailure("generation launcher has no frozen input-manifest identity")
    if INPUT_MANIFEST.is_symlink() or not INPUT_MANIFEST.is_file():
        raise PreflightFailure("generation input manifest is missing")
    observed_hash = sha256_file(INPUT_MANIFEST)
    if observed_hash != INPUT_MANIFEST_SHA256:
        raise PreflightFailure("generation input manifest SHA-256 changed")
    try:
        value = json.loads(INPUT_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PreflightFailure("generation input manifest is not valid UTF-8 JSON") from error
    if canonical_json(value) != INPUT_MANIFEST.read_bytes():
        raise PreflightFailure("generation input manifest is not canonical JSON")
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "files",
        "host",
        "tools",
        "trajectory",
    }:
        raise PreflightFailure("generation input manifest has the wrong schema")
    if value["schema"] != "whitefoot.raw-deflate.generation-inputs.v1":
        raise PreflightFailure("generation input manifest schema changed")
    if value["host"] != EXPECTED_HOST:
        raise PreflightFailure("generation input manifest host binding changed")
    files = value["files"]
    if not isinstance(files, dict) or not files:
        raise PreflightFailure("generation input file map is empty")
    observed: dict[str, str] = {}
    for relative, expected in files.items():
        if (
            not isinstance(relative, str)
            or not isinstance(expected, str)
            or len(expected) != 64
        ):
            raise PreflightFailure("generation input file binding is malformed")
        path = resolve_repo_file(relative)
        actual = input_sha256(relative, path)
        if actual != expected:
            raise PreflightFailure(f"preregistered input changed: {relative}")
        observed[relative] = actual
    return value, observed


def require_committed_inputs(relative_files: Sequence[str]) -> None:
    labels = list(relative_files) + [
        str(INPUT_MANIFEST.relative_to(ROOT)),
        str(Path(__file__).resolve().relative_to(ROOT)),
    ]
    tracked = set(
        checked_output(["git", "ls-files", "--", *labels]).splitlines()
    )
    missing = sorted(set(labels) - tracked)
    if missing:
        raise PreflightFailure(f"preregistered inputs are not tracked: {missing}")
    dirty = checked_output(
        ["git", "status", "--porcelain=v1", "--untracked-files=all", "--", *labels]
    )
    if dirty:
        raise PreflightFailure(f"preregistered inputs differ from HEAD:\n{dirty}")


def verify_tools(tools: Any) -> dict[str, Any]:
    if not isinstance(tools, dict) or not tools:
        raise PreflightFailure("generation tool manifest is empty")
    observed: dict[str, Any] = {}
    for label, specification in tools.items():
        if not isinstance(specification, dict) or set(specification) != {
            "path",
            "sha256",
            "version_argv",
            "version_stdout",
        }:
            raise PreflightFailure(f"tool binding is malformed: {label}")
        path = Path(specification["path"])
        if path.is_symlink() or not path.is_file():
            raise PreflightFailure(f"locked tool is missing or symlinked: {label}")
        actual_hash = sha256_file(path)
        if actual_hash != specification["sha256"]:
            raise PreflightFailure(f"locked tool hash changed: {label}")
        argv = specification["version_argv"]
        if not isinstance(argv, list) or not argv or any(
            not isinstance(item, str) or not item for item in argv
        ):
            raise PreflightFailure(f"tool version command is malformed: {label}")
        actual_version = checked_output(argv)
        if actual_version != specification["version_stdout"]:
            raise PreflightFailure(f"locked tool version changed: {label}")
        observed[label] = {
            "path": str(path),
            "sha256": actual_hash,
            "version": actual_version,
        }
    return observed


def verify_prompt() -> None:
    assembled = (
        (HERE / "task.md").read_bytes()
        + PROMPT_SEPARATOR
        + (HERE / "teaching-pack.md").read_bytes()
        + PATTERN_SEPARATOR
        + (ROOT / "PATTERNS.md").read_bytes()
    )
    if PROMPT.read_bytes() != assembled:
        raise PreflightFailure("base prompt is not the exact component assembly")


def verify_protocol() -> None:
    text = (HERE / "PROTOCOL.md").read_text(encoding="utf-8")
    if "Status: **preregistered**." not in text:
        raise PreflightFailure("protocol has not entered preregistered status")
    if "TBD" in text or "DRAFT" in text:
        raise PreflightFailure("protocol still contains a draft marker")


def verify_scoring_artifacts() -> None:
    manifest = json.loads((HERE / "scoring-manifest.json").read_text(encoding="utf-8"))
    for member in manifest.get("members", []):
        for role in ("source", "raw_deflate"):
            specification = member[role]
            path = HERE / specification["file"]
            if not path.is_file() or path.stat().st_size != specification["size"]:
                raise PreflightFailure(f"scoring artifact is missing or has wrong size: {path}")
            if sha256_file(path) != specification["sha256"]:
                raise PreflightFailure(f"scoring artifact hash changed: {path}")
    adapters = (
        manifest["toolchain"]["stock_zlib_compressor_and_decoder"]["adapter"],
        manifest["toolchain"]["zlib_ng_reference_decoder"]["adapter"],
    )
    for specification in adapters:
        path = HERE / specification["artifact_file"]
        if not path.is_file() or sha256_file(path) != specification["artifact_sha256"]:
            raise PreflightFailure(f"scoring adapter identity changed: {path}")


def verify_local_gates() -> None:
    tests = (
        ([str(PYTHON), str(HERE / "input_manifest.py"), "--check"], 120),
        (
            [
                str(PYTHON),
                str(DEFAULT_FLOOR / "tests" / "test_generate.py"),
            ],
            120,
        ),
        (
            [
                str(PYTHON),
                str(DEFAULT_FLOOR / "tests" / "test_codex_model.py"),
            ],
            120,
        ),
        ([str(PYTHON), str(HERE / "test_oracle.py")], 120),
        (
            [
                str(PYTHON),
                str(HERE / "corpus.py"),
                "--check",
                "--cc",
                "%s --no-default-config -isysroot %s" % (CLANG, MACOS_SDK),
            ],
            300,
        ),
        ([str(PYTHON), str(HERE / "prepare_scoring.py"), "--check"], 600),
        ([str(PYTHON), str(EVALUATOR), "--self-test"], 120),
    )
    environment = sanitized_environment()
    for command, timeout in tests:
        completed = run(command, timeout=timeout, env=environment)
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise PreflightFailure(f"generation preflight gate failed: {command[1]}: {detail}")


def sanitized_environment() -> dict[str, str]:
    environment = dict(os.environ)
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
            del environment[key]
    environment["PATH"] = "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    environment["LC_ALL"] = "C"
    environment["LANG"] = "C"
    return environment


def main() -> int:
    try:
        if len(sys.argv) != 1:
            raise PreflightFailure("the preregistration launcher accepts no arguments")
        if Path(sys.executable).resolve() != PYTHON.resolve():
            raise PreflightFailure(f"launcher must run under locked Python {PYTHON}")
        if RUN_DIR.exists():
            raise PreflightFailure(f"preregistered run directory already exists: {RUN_DIR}")
        manifest, hashes = load_input_manifest()
        require_committed_inputs(tuple(hashes))
        tools = verify_tools(manifest["tools"])
        codex_script = Path(manifest["tools"]["codex_javascript"]["path"])
        if (
            not CODEX.is_symlink()
            or CODEX.resolve() != codex_script.resolve()
            or sha256_file(CODEX) != manifest["tools"]["codex_javascript"]["sha256"]
        ):
            raise PreflightFailure("Codex launcher symlink identity changed")
        path_node = Path("/opt/homebrew/bin/node")
        locked_node = Path(manifest["tools"]["node"]["path"])
        if not path_node.is_symlink() or path_node.resolve() != locked_node.resolve():
            raise PreflightFailure("PATH Node symlink identity changed")
        trajectory = manifest["trajectory"]
        if trajectory != {
            "model": MODEL,
            "reasoning_effort": "medium",
            "repair_budget": 3,
            "service_tier": "default",
            "source_name": "inflate_raw.wf",
        }:
            raise PreflightFailure("generation trajectory binding changed")
        verify_prompt()
        verify_protocol()
        verify_scoring_artifacts()
        verify_local_gates()
        revision = checked_output(["git", "rev-parse", "HEAD"])
        status = checked_output(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"]
        )
        if status:
            raise PreflightFailure("generation requires a pristine committed repository")
    except (OSError, UnicodeError, ValueError, KeyError, subprocess.TimeoutExpired, PreflightFailure) as error:
        print(f"generation preflight failed: {error}", file=sys.stderr)
        return 2

    model_argv = [
        str(PYTHON),
        str(ADAPTER),
        "--codex",
        str(CODEX),
        "--model",
        MODEL,
        "--reasoning",
        "medium",
        "--service-tier",
        "default",
        "--timeout",
        "600",
    ]
    evaluator_argv = [str(PYTHON), str(EVALUATOR)]
    common = {
        "host_platform": platform.platform(),
        "host_binding": manifest["host"],
        "python": platform.python_version(),
        "repository_revision": revision,
        "git_status_porcelain_v1": status.splitlines(),
        "generation_input_manifest": {
            "path": str(INPUT_MANIFEST.relative_to(ROOT)),
            "sha256": INPUT_MANIFEST_SHA256,
        },
    }
    model_metadata = {
        **common,
        "surface": "codex-cli",
        "model": MODEL,
        "reasoning_effort": "medium",
        "service_tier": "default",
        "ephemeral": True,
        "sandbox": "read-only",
        "user_config": "ignored",
        "repository_rules": "ignored",
        "event_boundary": "exact-four-event-single-agent-message-no-tools",
        "tool_manifest": tools,
        "input_hashes": {
            relative: hashes[relative]
            for relative in (
                str(ADAPTER.relative_to(ROOT)),
                str(GENERATOR.relative_to(ROOT)),
                str(PROMPT.relative_to(ROOT)),
            )
        },
    }
    evaluator_metadata = {
        **common,
        "kind": "raw-deflate-compile-and-correctness",
        "corpus": {
            "sha256": hashes[str((HERE / "correctness-corpus.json").relative_to(ROOT))],
        },
        "proof_feedback": "disabled-before-freeze",
        "tool_manifest": tools,
        "input_hashes": hashes,
    }
    argv = [
        str(PYTHON),
        str(GENERATOR),
        "--run-dir",
        str(RUN_DIR),
        "--prompt-file",
        str(PROMPT),
        "--model-argv-json",
        json.dumps(model_argv, separators=(",", ":")),
        "--evaluator-argv-json",
        json.dumps(evaluator_argv, separators=(",", ":")),
        "--public-model-metadata-json",
        json.dumps(model_metadata, sort_keys=True, separators=(",", ":")),
        "--public-evaluator-metadata-json",
        json.dumps(evaluator_metadata, sort_keys=True, separators=(",", ":")),
        "--repair-budget",
        "3",
        "--source-name",
        "inflate_raw.wf",
        "--model-timeout",
        "660",
        "--evaluator-timeout",
        "1200",
    ]
    os.execve(str(PYTHON), argv, sanitized_environment())
    return 127


if __name__ == "__main__":
    raise SystemExit(main())
