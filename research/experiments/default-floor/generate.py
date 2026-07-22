#!/usr/bin/env python3
"""Run one benchmark-blind default-floor generation trajectory.

The model receives a prompt on stdin and must emit only candidate source on
stdout.  The evaluator receives the candidate path as its final argument and
must emit protocol JSON on stdout.  No shell is involved in either invocation.
"""

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


PROTOCOL_VERSION = 1
ALLOWED_EVALUATOR_CHANNELS = frozenset(("compile", "correctness", "proof"))
REQUIRED_EVALUATOR_CHANNELS = frozenset(("compile", "correctness"))
PERFORMANCE_TEXT = re.compile(
    r"(?i)(?:\bbenchmark\w*|\bperformance\b|\bperf\b|\blatenc\w*|\bthroughput\b|"
    r"\btiming\b|\belapsed\b|\bduration\b|\bwall[_ -]?time\b|\bcpu[_ -]?time\b|"
    r"\bcycles?\b|\bspeed\b|\bbandwidth\b|\bmbps\b|\bgbps\b|\bops[/_]s\b|"
    r"\bbytes[/_]s\b|\b(?:ns|us|ms)\b)"
)
PERFORMANCE_FIELD = re.compile(
    r"(?i)(?:benchmark|performance|(?:^|_)perf(?:_|$)|latency|throughput|timing|elapsed|"
    r"duration|(?:^|_)(?:wall|cpu)?_?time(?:_|$)|(?:^|_)(?:wall_?)?(?:ns|us|ms)(?:_|$)|"
    r"cycles?|speed|bandwidth|mbps|gbps|ops_per|bytes_per)"
)
DIAGNOSTIC_FIELDS = frozenset(("code", "message", "path", "line", "column", "end_line", "end_column"))
PROOF_FIELDS = frozenset(("passed", "status", "diagnostics", "sites"))
PROOF_SITE_FIELDS = frozenset(("id", "status", "detail", "rule", "path", "line", "column"))


class ProtocolError(RuntimeError):
    """The caller, model, or evaluator violated the frozen protocol."""


@dataclass(frozen=True)
class ProcessOutcome:
    returncode: Optional[int]
    stdout: bytes
    stderr: bytes
    failure: Optional[str] = None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def write_new_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def write_new_json(path: Path, value: Any) -> None:
    write_new_bytes(path, canonical_json_bytes(value))


def parse_argv_json(label: str, raw: str) -> List[str]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ProtocolError(f"{label} must be valid JSON: {error}") from error
    if not isinstance(value, list) or not value:
        raise ProtocolError(f"{label} must be a non-empty JSON array")
    if any(not isinstance(item, str) or not item for item in value):
        raise ProtocolError(f"every {label} item must be a non-empty string")
    return list(value)


def parse_metadata_json(label: str, raw: str) -> Dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ProtocolError(f"{label} must be valid JSON: {error}") from error
    if not isinstance(value, dict):
        raise ProtocolError(f"{label} must be a JSON object")
    return dict(value)


def argv_sha256(argv: Sequence[str]) -> str:
    encoded = json.dumps(list(argv), sort_keys=False, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(encoded)


def validate_source_name(name: str) -> str:
    if not name or Path(name).name != name or name in (".", ".."):
        raise ProtocolError("--source-name must be one plain file name")
    return name


def build_prompt(
    base_prompt: str,
    round_index: int,
    previous_source: Optional[str],
    previous_evaluator: Optional[Mapping[str, Any]],
) -> str:
    contract = (
        "\n\nDEFAULT-FLOOR OUTPUT CONTRACT\n"
        "Return only the complete candidate source on stdout. Do not use Markdown fences, "
        "explanations, benchmark results, timing data, or performance measurements.\n"
    )
    if round_index == 0:
        return base_prompt + contract
    if previous_source is None or previous_evaluator is None:
        raise AssertionError("repair rounds require the preceding candidate and evaluator feedback")
    feedback = json.dumps(previous_evaluator, sort_keys=True, indent=2, ensure_ascii=False)
    return (
        base_prompt
        + contract
        + f"\nREPAIR ROUND {round_index}\n"
        + "Repair the preceding candidate using only the machine feedback below.\n"
        + "\nPREVIOUS CANDIDATE\n<<<SOURCE\n"
        + previous_source
        + "\nSOURCE\n"
        + "\nMACHINE EVALUATOR FEEDBACK\n<<<JSON\n"
        + feedback
        + "\nJSON\n"
    )


def reject_performance_observations(value: Any, path: Tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ProtocolError("evaluator JSON object keys must be strings")
            if PERFORMANCE_FIELD.search(key) or PERFORMANCE_TEXT.search(key):
                location = ".".join(path + (key,))
                raise ProtocolError(f"evaluator emitted forbidden benchmark/performance field: {location}")
            reject_performance_observations(child, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_performance_observations(child, path + (str(index),))
    elif isinstance(value, str) and PERFORMANCE_TEXT.search(value):
        location = ".".join(path)
        raise ProtocolError(f"evaluator emitted forbidden benchmark/performance text: {location}")


def require_closed_object(label: str, value: Any, allowed: frozenset) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolError(f"{label} must be a JSON object")
    extra = set(value) - allowed
    if extra:
        raise ProtocolError(f"{label} has forbidden fields: {sorted(extra)}")
    return value


def validate_diagnostics(label: str, value: Any) -> None:
    if not isinstance(value, list):
        raise ProtocolError(f"{label} must be a JSON array")
    for index, diagnostic in enumerate(value):
        item_label = f"{label}[{index}]"
        item = require_closed_object(item_label, diagnostic, DIAGNOSTIC_FIELDS)
        if "code" not in item or "message" not in item:
            raise ProtocolError(f"{item_label} requires string fields 'code' and 'message'")
        for field in ("code", "message", "path"):
            if field in item and not isinstance(item[field], str):
                raise ProtocolError(f"{item_label}.{field} must be a string")
        for field in ("line", "column", "end_line", "end_column"):
            if field in item and (type(item[field]) is not int or item[field] < 0):
                raise ProtocolError(f"{item_label}.{field} must be a non-negative integer")


def validate_pass_channel(channel: str, value: Any) -> None:
    payload = require_closed_object(
        f"evaluator channel {channel!r}", value, frozenset(("passed", "diagnostics"))
    )
    if type(payload.get("passed")) is not bool:
        raise ProtocolError(f"evaluator channel {channel!r} must contain boolean field 'passed'")
    if "diagnostics" in payload:
        validate_diagnostics(f"{channel}.diagnostics", payload["diagnostics"])


def validate_proof_channel(value: Any) -> None:
    proof = require_closed_object("evaluator channel 'proof'", value, PROOF_FIELDS)
    if "passed" in proof and type(proof["passed"]) is not bool:
        raise ProtocolError("proof.passed must be boolean")
    if "status" in proof and not isinstance(proof["status"], str):
        raise ProtocolError("proof.status must be a string")
    if "diagnostics" in proof:
        validate_diagnostics("proof.diagnostics", proof["diagnostics"])
    if "sites" in proof:
        if not isinstance(proof["sites"], list):
            raise ProtocolError("proof.sites must be a JSON array")
        for index, raw_site in enumerate(proof["sites"]):
            site = require_closed_object(f"proof.sites[{index}]", raw_site, PROOF_SITE_FIELDS)
            if "id" not in site or "status" not in site:
                raise ProtocolError(f"proof.sites[{index}] requires string fields 'id' and 'status'")
            for field in ("id", "status", "detail", "rule", "path"):
                if field in site and not isinstance(site[field], str):
                    raise ProtocolError(f"proof.sites[{index}].{field} must be a string")
            for field in ("line", "column"):
                if field in site and (type(site[field]) is not int or site[field] < 0):
                    raise ProtocolError(f"proof.sites[{index}].{field} must be a non-negative integer")


def validate_evaluator_feedback(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolError("evaluator stdout must be one JSON object")
    keys = set(value)
    missing = REQUIRED_EVALUATOR_CHANNELS - keys
    extra = keys - ALLOWED_EVALUATOR_CHANNELS
    if missing:
        raise ProtocolError(f"evaluator JSON is missing channels: {sorted(missing)}")
    if extra:
        raise ProtocolError(f"evaluator JSON has forbidden channels: {sorted(extra)}")
    reject_performance_observations(value)
    for channel in ("compile", "correctness"):
        validate_pass_channel(channel, value[channel])
    if "proof" in value:
        validate_proof_channel(value["proof"])
    return dict(value)


def is_correct(feedback: Mapping[str, Any]) -> bool:
    return feedback["compile"]["passed"] is True and feedback["correctness"]["passed"] is True


def run_process(
    argv: Sequence[str],
    stdin: bytes,
    cwd: Optional[Path],
    timeout_seconds: float,
) -> ProcessOutcome:
    try:
        completed = subprocess.run(
            list(argv),
            input=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(cwd) if cwd is not None else None,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
        return ProcessOutcome(completed.returncode, completed.stdout, completed.stderr)
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout if isinstance(error.stdout, bytes) else (error.stdout or "").encode("utf-8")
        stderr = error.stderr if isinstance(error.stderr, bytes) else (error.stderr or "").encode("utf-8")
        return ProcessOutcome(None, stdout, stderr, "timeout")
    except OSError as error:
        return ProcessOutcome(None, b"", str(error).encode("utf-8", errors="replace"), "exec_error")


def relative_artifact(run_dir: Path, path: Path) -> str:
    return path.relative_to(run_dir).as_posix()


def round_record(
    run_dir: Path,
    round_index: int,
    prompt_path: Path,
    raw_path: Path,
    source_path: Path,
    model_stderr_path: Path,
    model_process_path: Path,
    evaluator_raw_path: Path,
    evaluator_stderr_path: Path,
    evaluator_process_path: Path,
    evaluator_path: Path,
    evaluator: Mapping[str, Any],
) -> Dict[str, Any]:
    artifacts = {}
    for label, path in (
        ("prompt", prompt_path),
        ("raw", raw_path),
        ("source", source_path),
        ("model_stderr", model_stderr_path),
        ("model_process", model_process_path),
        ("evaluator_raw", evaluator_raw_path),
        ("evaluator_stderr", evaluator_stderr_path),
        ("evaluator_process", evaluator_process_path),
        ("evaluator", evaluator_path),
    ):
        artifacts[label] = {
            "path": relative_artifact(run_dir, path),
            "sha256": sha256_file(path),
        }
    return {
        "protocol_version": PROTOCOL_VERSION,
        "round": round_index,
        "correct": is_correct(evaluator),
        "artifacts": artifacts,
        "evaluator": evaluator,
    }


def append_jsonl(path: Path, value: Any) -> None:
    with path.open("ab") as stream:
        stream.write(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
        stream.write(b"\n")


def archive_protocol_failure(
    run_dir: Path,
    trace_path: Path,
    round_dir: Path,
    round_index: int,
    phase: str,
    message: str,
    artifacts: Mapping[str, Path],
) -> None:
    artifact_records = {}
    for label, path in artifacts.items():
        if path.is_file():
            artifact_records[label] = {
                "path": relative_artifact(run_dir, path),
                "sha256": sha256_file(path),
            }
    record = {
        "protocol_version": PROTOCOL_VERSION,
        "round": round_index,
        "status": "protocol_error",
        "phase": phase,
        "error": message,
        "artifacts": artifact_records,
    }
    write_new_json(round_dir / "record.json", record)
    append_jsonl(trace_path, record)
    write_new_json(
        run_dir / "result.json",
        {"status": "protocol_error", "round": round_index, "phase": phase, "error": message},
    )


def freeze_success(
    run_dir: Path,
    source_path: Path,
    source_name: str,
    round_index: int,
    trace_path: Path,
    records: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    frozen_dir = run_dir / "frozen"
    frozen_dir.mkdir()
    frozen_source = frozen_dir / source_name
    shutil.copyfile(str(source_path), str(frozen_source))
    source_hash = sha256_file(frozen_source)
    write_new_bytes(frozen_dir / "source.sha256", f"{source_hash}  {source_name}\n".encode("ascii"))
    manifest = {
        "protocol_version": PROTOCOL_VERSION,
        "status": "frozen",
        "frozen_round": round_index,
        "config": {
            "path": "config.json",
            "sha256": sha256_file(run_dir / "config.json"),
        },
        "source": {
            "path": relative_artifact(run_dir, frozen_source),
            "sha256": source_hash,
        },
        "trace": {
            "path": relative_artifact(run_dir, trace_path),
            "sha256": sha256_file(trace_path),
            "rounds": list(records),
        },
    }
    manifest_path = frozen_dir / "trace-manifest.json"
    write_new_json(manifest_path, manifest)
    return {
        "status": "frozen",
        "round": round_index,
        "source": str(frozen_source),
        "sha256": source_hash,
        "manifest": str(manifest_path),
    }


def run_trajectory(
    run_dir: Path,
    base_prompt: str,
    model_argv: Sequence[str],
    evaluator_argv: Sequence[str],
    model_metadata: Mapping[str, Any],
    evaluator_metadata: Mapping[str, Any],
    repair_budget: int,
    source_name: str,
    model_timeout: float,
    evaluator_timeout: float,
) -> Tuple[int, Dict[str, Any]]:
    if run_dir.exists():
        raise ProtocolError(f"run directory already exists; refusing to overwrite: {run_dir}")
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        run_dir.mkdir()
    except FileExistsError as error:
        raise ProtocolError(f"run directory already exists; refusing to overwrite: {run_dir}") from error

    config = {
        "protocol_version": PROTOCOL_VERSION,
        "trajectory_count": 1,
        "repair_budget": repair_budget,
        "max_rounds": repair_budget + 1,
        "source_name": source_name,
        "model_invocation": {
            "argv_sha256": argv_sha256(model_argv),
            "argv_items": len(model_argv),
            "public_metadata": dict(model_metadata),
        },
        "evaluator_invocation": {
            "argv_without_candidate_sha256": argv_sha256(evaluator_argv),
            "argv_items_without_candidate": len(evaluator_argv),
            "public_metadata": dict(evaluator_metadata),
        },
        "model_timeout_seconds": model_timeout,
        "evaluator_timeout_seconds": evaluator_timeout,
    }
    write_new_json(run_dir / "config.json", config)
    rounds_dir = run_dir / "rounds"
    rounds_dir.mkdir()
    trace_path = run_dir / "trace.jsonl"
    trace_path.touch(exist_ok=False)

    previous_source: Optional[str] = None
    previous_evaluator: Optional[Mapping[str, Any]] = None
    records: List[Mapping[str, Any]] = []

    for round_index in range(repair_budget + 1):
        round_dir = rounds_dir / f"{round_index:03d}"
        round_dir.mkdir()
        prompt = build_prompt(base_prompt, round_index, previous_source, previous_evaluator)
        prompt_bytes = prompt.encode("utf-8")
        prompt_path = round_dir / "prompt.txt"
        write_new_bytes(prompt_path, prompt_bytes)

        with tempfile.TemporaryDirectory(prefix="default-floor-model-") as model_cwd_raw:
            model_cwd = Path(model_cwd_raw)
            if any(model_cwd.iterdir()):
                raise ProtocolError("model temporary working directory was not empty")
            model = run_process(model_argv, prompt_bytes, model_cwd, model_timeout)
        raw_path = round_dir / "model.raw.txt"
        write_new_bytes(raw_path, model.stdout)
        model_stderr_path = round_dir / "model.stderr.txt"
        model_process_path = round_dir / "model-process.json"
        source_path = round_dir / source_name
        write_new_bytes(model_stderr_path, model.stderr)
        write_new_json(
            model_process_path,
            {"returncode": model.returncode, "process_failure": model.failure},
        )
        write_new_bytes(source_path, model.stdout)
        model_failure = None
        if model.failure is not None:
            model_failure = f"model process failure in round {round_index}: {model.failure}"
        elif model.returncode != 0:
            model_failure = f"model failed in round {round_index} with exit code {model.returncode}"
        if model_failure is not None:
            archive_protocol_failure(
                run_dir,
                trace_path,
                round_dir,
                round_index,
                "model",
                model_failure,
                {
                    "prompt": prompt_path,
                    "raw": raw_path,
                    "source": source_path,
                    "model_stderr": model_stderr_path,
                    "model_process": model_process_path,
                },
            )
            raise ProtocolError(model_failure)
        try:
            source_text = model.stdout.decode("utf-8")
        except UnicodeDecodeError as error:
            message = f"model stdout in round {round_index} is not UTF-8 source"
            archive_protocol_failure(
                run_dir,
                trace_path,
                round_dir,
                round_index,
                "model_output",
                message,
                {
                    "prompt": prompt_path,
                    "raw": raw_path,
                    "source": source_path,
                    "model_stderr": model_stderr_path,
                    "model_process": model_process_path,
                },
            )
            raise ProtocolError(message) from error

        evaluator_call = list(evaluator_argv) + [str(source_path.resolve())]
        evaluator = run_process(evaluator_call, b"", None, evaluator_timeout)
        evaluator_raw_path = round_dir / "evaluator.raw.txt"
        evaluator_stderr_path = round_dir / "evaluator.stderr.txt"
        evaluator_process_path = round_dir / "evaluator-process.json"
        write_new_bytes(evaluator_raw_path, evaluator.stdout)
        write_new_bytes(evaluator_stderr_path, evaluator.stderr)
        write_new_json(
            evaluator_process_path,
            {
                "returncode": evaluator.returncode,
                "process_failure": evaluator.failure,
                "candidate_was_last_argument": True,
            },
        )
        evaluator_failure = None
        if evaluator.failure is not None:
            evaluator_failure = f"evaluator process failure in round {round_index}: {evaluator.failure}"
        elif evaluator.returncode != 0:
            evaluator_failure = f"evaluator failed in round {round_index} with exit code {evaluator.returncode}"
        failure_artifacts = {
            "prompt": prompt_path,
            "raw": raw_path,
            "source": source_path,
            "model_stderr": model_stderr_path,
            "model_process": model_process_path,
            "evaluator_raw": evaluator_raw_path,
            "evaluator_stderr": evaluator_stderr_path,
            "evaluator_process": evaluator_process_path,
        }
        if evaluator_failure is not None:
            archive_protocol_failure(
                run_dir,
                trace_path,
                round_dir,
                round_index,
                "evaluator",
                evaluator_failure,
                failure_artifacts,
            )
            raise ProtocolError(evaluator_failure)
        try:
            parsed = json.loads(evaluator.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            message = f"evaluator stdout in round {round_index} is not valid UTF-8 JSON"
            archive_protocol_failure(
                run_dir,
                trace_path,
                round_dir,
                round_index,
                "evaluator_output",
                message,
                failure_artifacts,
            )
            raise ProtocolError(message) from error
        try:
            feedback = validate_evaluator_feedback(parsed)
        except ProtocolError as error:
            archive_protocol_failure(
                run_dir,
                trace_path,
                round_dir,
                round_index,
                "evaluator_schema",
                str(error),
                failure_artifacts,
            )
            raise
        evaluator_path = round_dir / "evaluator.json"
        write_new_json(evaluator_path, feedback)

        record = round_record(
            run_dir,
            round_index,
            prompt_path,
            raw_path,
            source_path,
            model_stderr_path,
            model_process_path,
            evaluator_raw_path,
            evaluator_stderr_path,
            evaluator_process_path,
            evaluator_path,
            feedback,
        )
        write_new_json(round_dir / "record.json", record)
        append_jsonl(trace_path, record)
        records.append(record)

        if is_correct(feedback):
            result = freeze_success(
                run_dir,
                source_path,
                source_name,
                round_index,
                trace_path,
                records,
            )
            write_new_json(run_dir / "result.json", result)
            return 0, result

        previous_source = source_text
        previous_evaluator = feedback

    result = {
        "status": "repair_budget_exhausted",
        "rounds": repair_budget + 1,
        "repair_budget": repair_budget,
    }
    write_new_json(run_dir / "result.json", result)
    return 3, result


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--prompt-file", required=True, type=Path)
    parser.add_argument("--model-argv-json", required=True)
    parser.add_argument("--evaluator-argv-json", required=True)
    parser.add_argument("--public-model-metadata-json", default="{}")
    parser.add_argument("--public-evaluator-metadata-json", default="{}")
    parser.add_argument("--repair-budget", required=True, type=int)
    parser.add_argument("--source-name", default="source.xl")
    parser.add_argument("--model-timeout", type=float, default=300.0)
    parser.add_argument("--evaluator-timeout", type=float, default=300.0)
    return parser


def cli(argv: Optional[Sequence[str]] = None) -> int:
    args = build_argument_parser().parse_args(argv)
    try:
        if args.repair_budget < 0:
            raise ProtocolError("--repair-budget must be non-negative")
        if args.model_timeout <= 0 or args.evaluator_timeout <= 0:
            raise ProtocolError("timeouts must be positive")
        source_name = validate_source_name(args.source_name)
        model_argv = parse_argv_json("--model-argv-json", args.model_argv_json)
        evaluator_argv = parse_argv_json("--evaluator-argv-json", args.evaluator_argv_json)
        model_metadata = parse_metadata_json(
            "--public-model-metadata-json", args.public_model_metadata_json
        )
        evaluator_metadata = parse_metadata_json(
            "--public-evaluator-metadata-json", args.public_evaluator_metadata_json
        )
        try:
            base_prompt = args.prompt_file.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise ProtocolError(f"could not read prompt file {args.prompt_file}: {error}") from error
        code, result = run_trajectory(
            args.run_dir,
            base_prompt,
            model_argv,
            evaluator_argv,
            model_metadata,
            evaluator_metadata,
            args.repair_budget,
            source_name,
            args.model_timeout,
            args.evaluator_timeout,
        )
        print(json.dumps(result, sort_keys=True))
        return code
    except ProtocolError as error:
        print(f"default-floor protocol error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(cli())
