"""Bounded input, exact identity, and guarded-manifest support for the census."""

from __future__ import annotations

import hashlib
import json
import re
import stat
from pathlib import Path
from typing import Any, Iterable, Sequence


MAX_JSON_BYTES = 16_000_000
MAX_TEXT_BYTES = 16_000_000
CASE_ID = re.compile(r"[a-z0-9-]+\Z")


class CensusError(ValueError):
    """One bound input or a derived census invariant is invalid."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
    except (MemoryError, OverflowError, RecursionError, TypeError, ValueError) as error:
        raise CensusError(f"report is not canonical JSON: {error}") from error
    return (text + "\n").encode("ascii")


def _unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CensusError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise CensusError(f"non-finite JSON number is forbidden: {value}")


def _reject_json_float(value: str) -> None:
    raise CensusError(f"JSON floats are forbidden: {value}")


def strict_json(raw: bytes, label: str) -> Any:
    if not raw or len(raw) > MAX_JSON_BYTES:
        raise CensusError(f"{label} has an invalid byte length")
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
            parse_float=_reject_json_float,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise CensusError(f"{label} is not strict UTF-8 JSON: {error}") from error


def read_regular(path: Path, label: str, max_bytes: int = MAX_TEXT_BYTES) -> bytes:
    try:
        mode = path.lstat().st_mode
    except OSError as error:
        raise CensusError(f"cannot inspect {label}: {error}") from error
    if not stat.S_ISREG(mode) or path.is_symlink():
        raise CensusError(f"{label} is not a regular non-symlink file")
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise CensusError(f"cannot read {label}: {error}") from error
    if len(raw) > max_bytes:
        raise CensusError(f"{label} exceeds the {max_bytes}-byte limit")
    return raw


def require_digest(raw: bytes, expected: str, label: str) -> None:
    actual = sha256(raw)
    if actual != expected:
        raise CensusError(f"{label} identity drift: expected {expected}, got {actual}")


def inventory_digest(root: Path, paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        raw = read_regular(path, path.as_posix())
        try:
            relative = path.relative_to(root).as_posix().encode("utf-8")
        except ValueError as error:
            raise CensusError(f"inventory path escapes root: {path}") from error
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(hashlib.sha256(raw).digest())
    return digest.hexdigest()


def _manifest_key(record: dict[str, Any], raw_line: str) -> tuple[str, str]:
    if "id" in record:
        case_id = record["id"]
        if not isinstance(case_id, str) or not CASE_ID.fullmatch(case_id):
            raise CensusError(f"invalid conformance case id: {case_id!r}")
        canonical = json.dumps(
            {field: record.get(field) for field in ("id", "rules", "expect", "status")},
            sort_keys=True,
            separators=(",", ":"),
        )
        return case_id, canonical
    if "rule" not in record or not isinstance(record["rule"], str):
        raise CensusError(f"manifest annotation has no rule: {raw_line}")
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return f"rule:{record['rule']}", canonical


def load_manifest(
    root: Path,
    case_root_relative: Path,
    raw: bytes,
    protected: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CensusError(f"manifest is not UTF-8: {error}") from error
    cases: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        record = strict_json(stripped.encode("utf-8"), f"manifest line {line_number}")
        if not isinstance(record, dict):
            raise CensusError(f"manifest line {line_number} is not an object")
        key, canonical = _manifest_key(record, stripped)
        if key in seen:
            raise CensusError(f"duplicate manifest key: {key}")
        seen.add(key)
        if "id" in record:
            case_path = root / case_root_relative / f"{record['id']}.wf"
            case_raw = read_regular(case_path, case_path.as_posix())
            digest = sha256(canonical.encode("utf-8") + b"\0" + case_raw)
            cases.append(record)
        else:
            digest = sha256(canonical.encode("utf-8"))
            annotations.append(record)
        if protected.get(key) != digest:
            raise CensusError(f"guarded conformance record drift: {key}")
    if set(protected) != seen:
        missing = sorted(set(protected) - seen)
        extra = sorted(seen - set(protected))
        raise CensusError(f"guarded manifest inventory drift: missing={missing}, extra={extra}")
    return cases, annotations


def validate_case_inventory(
    root: Path,
    case_root_relative: Path,
    baseline: dict[str, Any],
    expected_digest: str,
) -> tuple[list[Path], str]:
    protected = baseline.get("conformance_case_files")
    if not isinstance(protected, dict) or not protected:
        raise CensusError("guard baseline has no conformance case-file inventory")
    paths = sorted((root / case_root_relative).rglob("*.wf"))
    actual: dict[str, str] = {}
    for path in paths:
        relative = path.relative_to(root).as_posix()
        actual[relative] = sha256(read_regular(path, relative))
    if actual != protected:
        raise CensusError("guarded conformance case-file inventory drift")
    digest = inventory_digest(root, paths)
    if digest != expected_digest:
        raise CensusError(
            "conformance inventory identity drift: "
            f"expected {expected_digest}, got {digest}"
        )
    return paths, digest
