#!/usr/bin/env python3
"""Small, disposable real-project frequency pilot.

The input is either a directory whose immediate children are projects, a JSON
list, or ``{"crates": [...]}``.  A JSON item may be a directory string or an
object with these useful fields::

    {"name": "foo", "path": "foo-1.0.0/"}
    {"name": "foo", "archive": "foo.crate", "sha256": "..."}
    {"name": "foo", "url": "https://...", "sha256": "..."}

Raw crates.io API rows are also accepted.  Their ``name`` and
``max_stable_version`` fields determine the static.crates.io archive URL.
Input order is ranking order.  Repository duplicates retain the first row.

This intentionally is not a general Rust analysis framework.  It inventories
authored-looking Rust source, optionally runs two external scanners, and emits
one compact JSON document.  An examined failure remains ``unknown`` in the
ledger; it is never silently discarded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence

try:
    import tomllib
except ImportError:  # pragma: no cover - Python 3.11+ is expected.
    tomllib = None


HERE = Path(__file__).resolve().parent
SCHEMA = 1
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_EXTRACTED_BYTES = 2 * 1024 * 1024 * 1024
MAX_MEMBERS = 200_000
SKIP_DIRS = {".git", "target"}
SOURCE_SKIP_DIRS = {
    ".git",
    "benches",
    "examples",
    "generated",
    "node_modules",
    "target",
    "tests",
    "vendor",
}
HEX_256 = re.compile(r"^[0-9a-fA-F]{64}$")


class PilotError(Exception):
    """Expected input or assessment failure."""


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_id(value: str) -> str:
    readable = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")[:60]
    readable = readable or "project"
    suffix = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{readable}-{suffix}"


def _resolve_input_path(value: str, base: Path) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return str(path.resolve(strict=False))


def _normal_repository(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().lower()
    if text.endswith(".git"):
        text = text[:-4]
    return text.rstrip("/")


def _normalize_entry(raw: Any, ordinal: int, base: Path) -> dict[str, Any]:
    if isinstance(raw, str):
        path = _resolve_input_path(raw, base)
        name = Path(path).name
        return {"id": name, "name": name, "path": path}
    if not isinstance(raw, dict):
        raise PilotError(f"entry {ordinal} is not an object or path string")

    entry: dict[str, Any] = {}
    name = raw.get("name") or raw.get("crate") or raw.get("id")
    if not isinstance(name, str) or not name:
        name = f"project-{ordinal:05d}"
    project_id = raw.get("id") or name
    if not isinstance(project_id, (str, int)):
        raise PilotError(f"entry {ordinal} has an invalid id")
    entry["id"] = str(project_id)
    entry["name"] = name

    version = raw.get("version") or raw.get("max_stable_version")
    if isinstance(version, str) and version:
        entry["version"] = version
    repository = raw.get("repository")
    if isinstance(repository, str) and repository:
        entry["repository"] = repository

    for key in ("path", "archive", "reassociation_jsonl", "source_signals_json"):
        if isinstance(raw.get(key), str) and raw[key]:
            entry[key] = _resolve_input_path(raw[key], base)

    url = raw.get("url") or raw.get("download_url")
    if not url and isinstance(version, str) and version and raw.get("max_stable_version"):
        quoted_name = urllib.parse.quote(name, safe="")
        quoted_file = urllib.parse.quote(f"{name}-{version}.crate", safe="")
        url = f"https://static.crates.io/crates/{quoted_name}/{quoted_file}"
    if isinstance(url, str) and url:
        entry["url"] = url

    checksum = raw.get("sha256") or raw.get("checksum")
    if isinstance(checksum, str) and checksum:
        entry["sha256"] = checksum.lower()
    return entry


def load_entries(source: Path) -> list[dict[str, Any]]:
    source = source.expanduser().resolve()
    if source.is_dir():
        if (source / "Cargo.toml").is_file():
            return [{"id": source.name, "name": source.name, "path": str(source)}]
        children = [
            child
            for child in source.iterdir()
            if child.name not in SKIP_DIRS and not child.name.startswith(".")
            and (child.is_dir() or child.is_symlink())
        ]
        children.sort(key=lambda child: os.fsencode(child.name))
        if not children:
            return [{"id": source.name, "name": source.name, "path": str(source)}]
        return [{"id": child.name, "name": child.name, "path": str(child)} for child in children]

    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PilotError(f"cannot read crate list {source}: {error}") from error
    rows = document.get("crates") if isinstance(document, dict) else document
    if not isinstance(rows, list):
        raise PilotError("crate list must be a JSON list or an object with a crates list")

    entries: list[dict[str, Any]] = []
    repositories: set[str] = set()
    ids: Counter[str] = Counter()
    for ordinal, raw in enumerate(rows, 1):
        entry = _normalize_entry(raw, ordinal, source.parent)
        repository = _normal_repository(entry.get("repository"))
        if repository is not None:
            if repository in repositories:
                continue
            repositories.add(repository)
        ids[entry["id"]] += 1
        if ids[entry["id"]] > 1:
            entry["id"] = f"{entry['id']}#{ids[entry['id']]}"
        entries.append(entry)
    return entries


def _archive_parts(name: str) -> tuple[str, ...]:
    if not name or "\x00" in name or "\\" in name:
        raise PilotError(f"unsafe archive path {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise PilotError(f"unsafe archive path {name!r}")
    parts = tuple(part for part in path.parts if part not in ("", "."))
    if parts and (":" in parts[0] or parts[0] in ("/", "..")):
        raise PilotError(f"unsafe archive path {name!r}")
    return parts


def _prepare_extract_destination(destination: Path) -> None:
    if destination.is_symlink():
        raise PilotError(f"extraction destination is a symlink: {destination}")
    if destination.exists() and any(destination.iterdir()):
        raise PilotError(f"extraction destination is not empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)


def _extract_tar(archive: Path, destination: Path) -> None:
    seen: set[tuple[str, ...]] = set()
    total = 0
    with tarfile.open(archive, mode="r:*") as bundle:
        members = bundle.getmembers()
        if len(members) > MAX_MEMBERS:
            raise PilotError("archive has too many members")
        for member in members:
            parts = _archive_parts(member.name)
            if not parts:
                continue
            if parts in seen:
                raise PilotError(f"duplicate archive path {member.name!r}")
            seen.add(parts)
            target = destination.joinpath(*parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise PilotError(f"archive contains a link or special file: {member.name!r}")
            total += member.size
            if total > MAX_EXTRACTED_BYTES:
                raise PilotError("archive expands beyond the size limit")
            target.parent.mkdir(parents=True, exist_ok=True)
            source = bundle.extractfile(member)
            if source is None:
                raise PilotError(f"cannot read archive member {member.name!r}")
            with source, target.open("xb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            target.chmod(member.mode & 0o777)


def _extract_zip(archive: Path, destination: Path) -> None:
    seen: set[tuple[str, ...]] = set()
    total = 0
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        if len(members) > MAX_MEMBERS:
            raise PilotError("archive has too many members")
        for member in members:
            parts = _archive_parts(member.filename)
            if not parts:
                continue
            if parts in seen:
                raise PilotError(f"duplicate archive path {member.filename!r}")
            seen.add(parts)
            mode = member.external_attr >> 16
            kind = stat.S_IFMT(mode)
            is_dir = member.is_dir()
            if kind == stat.S_IFLNK or (kind not in (0, stat.S_IFREG, stat.S_IFDIR)):
                raise PilotError(f"archive contains a link or special file: {member.filename!r}")
            if member.flag_bits & 1:
                raise PilotError(f"archive member is encrypted: {member.filename!r}")
            target = destination.joinpath(*parts)
            if is_dir:
                target.mkdir(parents=True, exist_ok=True)
                continue
            total += member.file_size
            if total > MAX_EXTRACTED_BYTES:
                raise PilotError("archive expands beyond the size limit")
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            if mode:
                target.chmod(mode & 0o777)


def safe_extract_archive(archive: Path, destination: Path) -> None:
    archive = archive.resolve()
    _prepare_extract_destination(destination)
    try:
        if zipfile.is_zipfile(archive):
            _extract_zip(archive, destination)
        elif tarfile.is_tarfile(archive):
            _extract_tar(archive, destination)
        else:
            raise PilotError(f"unsupported archive format: {archive}")
    except Exception:
        if destination.exists() and not destination.is_symlink():
            shutil.rmtree(destination)
        raise


def _validate_checksum(value: Any) -> str:
    if not isinstance(value, str) or not HEX_256.fullmatch(value):
        raise PilotError("archive source requires a 64-digit sha256/checksum")
    return value.lower()


def _download(url: str, destination: Path) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("https", "file"):
        raise PilotError("only https and local file URLs are accepted")
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "whitefoot-frequency-pilot/1"})
    size = 0
    try:
        with urllib.request.urlopen(request, timeout=30) as response, destination.open("xb") as output:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_ARCHIVE_BYTES:
                    raise PilotError("download exceeds the archive size limit")
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def _find_project_root(extracted: Path) -> Path:
    if (extracted / "Cargo.toml").is_file():
        return extracted
    children = sorted(extracted.iterdir(), key=lambda path: os.fsencode(path.name))
    if len(children) == 1 and children[0].is_dir() and not children[0].is_symlink():
        if (children[0] / "Cargo.toml").is_file():
            return children[0]
    manifests = [path for path in extracted.rglob("Cargo.toml") if path.is_file()]
    if len(manifests) == 1:
        return manifests[0].parent
    return extracted


def _is_static_crates_io(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname == "static.crates.io"
        and parsed.port is None
        and parsed.username is None
        and parsed.password is None
    )


def materialize(
    entry: dict[str, Any], work_dir: Path, fetch: bool, trust_crates_io: bool = False
) -> tuple[Path, dict[str, Any]]:
    raw_path = entry.get("archive") or entry.get("path")
    if raw_path:
        source = Path(raw_path)
        if source.is_symlink():
            raise PilotError(f"source is a symlink: {source}")
        if source.is_dir():
            return source.resolve(), {"kind": "directory", "path": str(source)}
        if not source.is_file():
            raise PilotError(f"source does not exist: {source}")
        archive = source.resolve()
    elif entry.get("url"):
        if not fetch:
            raise PilotError("source requires --fetch")
        if entry.get("sha256"):
            checksum = _validate_checksum(entry.get("sha256"))
            archive = work_dir / "downloads" / f"{checksum}.archive"
            if archive.exists() and sha256_file(archive) != checksum:
                archive.unlink()
            if not archive.exists():
                _download(entry["url"], archive)
        else:
            if not trust_crates_io or not _is_static_crates_io(entry["url"]):
                raise PilotError(
                    "download has no checksum; only static.crates.io is allowed with --trust-crates-io"
                )
            url_key = hashlib.sha256(entry["url"].encode("utf-8")).hexdigest()
            temporary = work_dir / "downloads" / f"untrusted-{url_key}.archive"
            temporary.unlink(missing_ok=True)
            _download(entry["url"], temporary)
            checksum = sha256_file(temporary)
            archive = work_dir / "downloads" / f"{checksum}.archive"
            archive.parent.mkdir(parents=True, exist_ok=True)
            if archive.exists():
                temporary.unlink()
            else:
                temporary.replace(archive)
    else:
        raise PilotError("entry has no path, archive, or URL")

    checksum = checksum if entry.get("url") and not entry.get("sha256") else _validate_checksum(entry.get("sha256"))
    actual = sha256_file(archive)
    if actual != checksum:
        raise PilotError(f"archive checksum mismatch: expected {checksum}, got {actual}")
    destination = work_dir / "projects" / _safe_id(entry["id"])
    if destination.exists():
        if destination.is_symlink():
            raise PilotError(f"project destination is a symlink: {destination}")
        shutil.rmtree(destination)
    safe_extract_archive(archive, destination)
    return _find_project_root(destination), {
        "kind": "archive",
        "sha256": checksum,
        "url": entry.get("url"),
    }


def rust_inventory(root: Path) -> dict[str, Any]:
    if root.is_symlink() or not root.is_dir():
        raise PilotError(f"project root is not a real directory: {root}")
    files: list[Path] = []

    def onerror(error: OSError) -> None:
        raise error

    for current, directories, names in os.walk(root, topdown=True, followlinks=False, onerror=onerror):
        current_path = Path(current)
        kept: list[str] = []
        for name in sorted(directories, key=os.fsencode):
            if name in SOURCE_SKIP_DIRS:
                continue
            child = current_path / name
            if child.is_symlink():
                raise PilotError(f"project contains a directory symlink: {child.relative_to(root)}")
            kept.append(name)
        directories[:] = kept
        for name in sorted(names, key=os.fsencode):
            child = current_path / name
            if child.is_symlink():
                raise PilotError(f"project contains a file symlink: {child.relative_to(root)}")
            relative_parent = current_path.relative_to(root)
            in_production_src = root.name == "src" or "src" in relative_parent.parts
            if child.suffix == ".rs" and in_production_src:
                files.append(child)

    nonblank = 0
    for path in files:
        try:
            with path.open("r", encoding="utf-8") as source:
                nonblank += sum(1 for line in source if line.strip())
        except (OSError, UnicodeError) as error:
            raise PilotError(f"cannot read {path.relative_to(root)}: {error}") from error
    return {"files": len(files), "nonblank_loc": nonblank, "status": "ok"}


def has_binary_target(root: Path) -> bool:
    manifest = root / "Cargo.toml"
    if not manifest.is_file():
        return False
    if (root / "src" / "main.rs").is_file():
        if tomllib is None:
            return True
        try:
            package = tomllib.loads(manifest.read_text(encoding="utf-8")).get("package", {})
        except (OSError, UnicodeError, tomllib.TOMLDecodeError):
            return False
        if package.get("autobins", True) is not False:
            return True
    if tomllib is None:
        return "[[bin]]" in manifest.read_text(encoding="utf-8", errors="ignore")
    try:
        document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError):
        return False
    return bool(document.get("bin"))


def _read_json_records(text: str, label: str) -> list[dict[str, Any]]:
    stripped = text.strip()
    if not stripped:
        return []
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        records: list[Any] = []
        for line_number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise PilotError(f"{label} has invalid JSON on line {line_number}: {error}") from error
    else:
        records = value if isinstance(value, list) else [value]
    if not all(isinstance(record, dict) for record in records):
        raise PilotError(f"{label} must contain JSON objects")
    return records


def _run_scanner(command: Sequence[str], root: Path, timeout: float, label: str) -> list[dict[str, Any]]:
    argv = [part.replace("{project}", str(root)) for part in command]
    if not any("{project}" in part for part in command):
        argv.append(str(root))
    try:
        result = subprocess.run(
            argv,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as error:
        raise PilotError(f"{label} failed: {error}") from error
    if result.returncode != 0:
        stderr = result.stderr.strip().replace("\n", " ")[:1000]
        raise PilotError(f"{label} exited {result.returncode}: {stderr}")
    return _read_json_records(result.stdout, label)


def _reassociation_result(records: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    dispositions = Counter(str(record.get("disposition", "unresolved")) for record in records)
    classes = Counter(str(record.get("class", "unknown")) for record in records)
    return {
        "by_class": dict(sorted(classes.items())),
        "candidates": dispositions["candidate"],
        "mode": mode,
        "records": records,
        "record_count": len(records),
        "status": "ok",
        "unresolved": dispositions["unresolved"],
    }


def _unknown(error: Exception | str) -> dict[str, Any]:
    return {"reason": str(error), "status": "unknown"}


def assess_reassociation(
    entry: dict[str, Any],
    root: Path,
    jsonl_dir: Path | None,
    command: Sequence[str] | None,
    timeout: float,
) -> dict[str, Any]:
    supplied = entry.get("reassociation_jsonl")
    candidate = Path(supplied) if supplied else None
    if candidate is None and jsonl_dir is not None:
        candidate = jsonl_dir / f"{_safe_id(entry['id'])}.jsonl"
    try:
        if candidate is not None and candidate.is_file():
            records = _read_json_records(candidate.read_text(encoding="utf-8"), "reassociation JSONL")
            return _reassociation_result(records, "ingested")
        if candidate is not None and command is None:
            return _unknown(f"reassociation JSONL is missing: {candidate}")
        if command is not None:
            return _reassociation_result(_run_scanner(command, root, timeout, "reassociation scanner"), "command")
        auto = [
            HERE / "reassociation" / "target" / "release" / "reassociation-source-miner",
            HERE / "reassociation" / "target" / "debug" / "reassociation-source-miner",
        ]
        binary = next((path for path in auto if path.is_file() and os.access(path, os.X_OK)), None)
        if binary is not None:
            return _reassociation_result(_run_scanner([str(binary)], root, timeout, "reassociation scanner"), "command")
        return {"status": "not_run"}
    except (OSError, UnicodeError, PilotError) as error:
        return _unknown(error)


def assess_source_signals(
    entry: dict[str, Any], root: Path, command: Sequence[str] | None, timeout: float
) -> dict[str, Any]:
    def result(records: list[dict[str, Any]], mode: str) -> dict[str, Any]:
        if len(records) == 1 and isinstance(records[0].get("records"), list):
            document = records[0]
            findings = document["records"]
            if not all(isinstance(finding, dict) for finding in findings):
                raise PilotError("source-signal records must be JSON objects")
            return {
                "candidate_count": document.get("candidate_count", len(findings)),
                "counts_by_class": document.get("counts_by_class", {}),
                "mode": mode,
                "record_count": len(findings),
                "records": findings,
                "report": document,
                "status": "ok",
            }
        return {
            "mode": mode,
            "record_count": len(records),
            "records": records,
            "status": "ok",
        }

    supplied = entry.get("source_signals_json")
    try:
        if supplied:
            records = _read_json_records(Path(supplied).read_text(encoding="utf-8"), "source signals")
            return result(records, "ingested")
        if command is None:
            auto = [
                HERE / "pilot_signals.py",
                HERE / "source_signal.py",
                HERE / "source-signals" / "scan.py",
            ]
            scanner = next((path for path in auto if path.is_file()), None)
            if scanner is not None:
                command = [sys.executable, str(scanner)]
        if command is None:
            return {"status": "not_run"}
        records = _run_scanner(command, root, timeout, "source-signal scanner")
        return result(records, "command")
    except (OSError, UnicodeError, PilotError) as error:
        return _unknown(error)


def _source_description(entry: dict[str, Any]) -> dict[str, Any]:
    if entry.get("url"):
        return {"kind": "url", "sha256": entry.get("sha256"), "url": entry["url"]}
    value = entry.get("archive") or entry.get("path")
    return {"kind": "local", "path": value}


def assess_project(
    entry: dict[str, Any],
    ordinal: int,
    work_dir: Path,
    fetch: bool,
    min_loc: int,
    require_bin: bool,
    reassociation_jsonl_dir: Path | None,
    reassociation_command: Sequence[str] | None,
    source_signal_command: Sequence[str] | None,
    timeout: float,
    trust_crates_io: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": entry["id"],
        "name": entry["name"],
        "ordinal": ordinal,
        "source": _source_description(entry),
    }
    if entry.get("repository"):
        result["repository"] = entry["repository"]
    if entry.get("version"):
        result["version"] = entry["version"]
    try:
        root, materialized = materialize(entry, work_dir, fetch, trust_crates_io)
        inventory = rust_inventory(root)
    except (OSError, PilotError, tarfile.TarError, zipfile.BadZipFile) as error:
        result.update(
            {
                "eligibility": "unknown",
                "reassociation": {"status": "not_run"},
                "rust": _unknown(error),
                "source_signals": {"status": "not_run"},
                "status": "unknown",
                "unknown_reasons": [str(error)],
            }
        )
        return result

    result["materialized_source"] = materialized
    result["rust"] = inventory
    ineligible_reasons: list[str] = []
    if inventory["nonblank_loc"] < min_loc:
        ineligible_reasons.append(f"nonblank Rust LOC is below {min_loc}")
    binary = has_binary_target(root)
    result["has_binary_target"] = binary
    if require_bin and not binary:
        ineligible_reasons.append("no binary target")
    if ineligible_reasons:
        result.update(
            {
                "eligibility": "ineligible",
                "ineligible_reasons": ineligible_reasons,
                "reassociation": {"status": "not_run"},
                "source_signals": {"status": "not_run"},
                "status": "ineligible",
            }
        )
        return result

    result["eligibility"] = "eligible"
    reassociation = assess_reassociation(
        entry, root, reassociation_jsonl_dir, reassociation_command, timeout
    )
    source_signals = assess_source_signals(entry, root, source_signal_command, timeout)
    result["reassociation"] = reassociation
    result["source_signals"] = source_signals
    failures = [
        section["reason"]
        for section in (reassociation, source_signals)
        if section.get("status") == "unknown"
    ]
    result["status"] = "unknown" if failures else "ok"
    if failures:
        result["unknown_reasons"] = failures
    return result


def summarize(projects: list[dict[str, Any]], eligible_limit: int) -> dict[str, Any]:
    eligible = [project for project in projects if project.get("eligibility") == "eligible"]
    known_rust = [project["rust"] for project in projects if project["rust"].get("status") == "ok"]
    reassessed = [project["reassociation"] for project in eligible if project["reassociation"].get("status") == "ok"]
    signaled = [project["source_signals"] for project in eligible if project["source_signals"].get("status") == "ok"]
    reassociation_classes: Counter[str] = Counter()
    signal_classes: Counter[str] = Counter()
    for item in reassessed:
        reassociation_classes.update(item["by_class"])
    for item in signaled:
        signal_classes.update(
            str(record.get("class", "unknown")) for record in item.get("records", [])
        )
    return {
        "eligible_limit": eligible_limit,
        "eligible_projects": len(eligible),
        "examined_projects": len(projects),
        "ineligible_projects": sum(project.get("eligibility") == "ineligible" for project in projects),
        "nonblank_rust_loc_examined": sum(item["nonblank_loc"] for item in known_rust),
        "reassociation": {
            "assessed_projects": len(reassessed),
            "by_class": dict(sorted(reassociation_classes.items())),
            "candidate_projects": sum(item["candidates"] > 0 for item in reassessed),
            "candidates": sum(item["candidates"] for item in reassessed),
            "records": sum(item["record_count"] for item in reassessed),
            "unknown_projects": sum(project["reassociation"].get("status") == "unknown" for project in eligible),
        },
        "rust_files_examined": sum(item["files"] for item in known_rust),
        "source_signals": {
            "assessed_projects": len(signaled),
            "by_class": dict(sorted(signal_classes.items())),
            "records": sum(item["record_count"] for item in signaled),
            "unknown_projects": sum(project["source_signals"].get("status") == "unknown" for project in eligible),
        },
        "unknown_projects": sum(project.get("status") == "unknown" for project in projects),
    }


def run_pilot(
    source: Path,
    *,
    limit: int,
    work_dir: Path,
    fetch: bool = False,
    min_loc: int = 1000,
    require_bin: bool = False,
    reassociation_jsonl_dir: Path | None = None,
    reassociation_command: Sequence[str] | None = None,
    source_signal_command: Sequence[str] | None = None,
    timeout: float = 120.0,
    trust_crates_io: bool = False,
) -> dict[str, Any]:
    if limit < 1:
        raise PilotError("limit must be positive")
    if min_loc < 0:
        raise PilotError("min-loc cannot be negative")
    entries = load_entries(source)
    work_dir.mkdir(parents=True, exist_ok=True)
    projects: list[dict[str, Any]] = []
    eligible = 0
    for ordinal, entry in enumerate(entries, 1):
        if eligible >= limit:
            break
        project = assess_project(
            entry,
            ordinal,
            work_dir,
            fetch,
            min_loc,
            require_bin,
            reassociation_jsonl_dir,
            reassociation_command,
            source_signal_command,
            timeout,
            trust_crates_io,
        )
        projects.append(project)
        if project.get("eligibility") == "eligible":
            eligible += 1
    return {
        "config": {"eligible_limit": limit, "min_nonblank_loc": min_loc, "require_bin": require_bin},
        "projects": projects,
        "schema": SCHEMA,
        "summary": summarize(projects, limit),
    }


def _command(value: str | None) -> list[str] | None:
    if value is None:
        return None
    argv = shlex.split(value)
    if not argv:
        raise argparse.ArgumentTypeError("scanner command cannot be empty")
    return argv


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="crate-list JSON or directory of projects")
    parser.add_argument("--limit", type=int, default=30, help="eligible projects to collect (default: 30)")
    parser.add_argument("--min-loc", type=int, default=1000, help="minimum nonblank Rust LOC (default: 1000)")
    parser.add_argument("--require-bin", action="store_true", help="require a Cargo binary target")
    parser.add_argument("--fetch", action="store_true", help="allow checksum-verified HTTPS/file downloads")
    parser.add_argument(
        "--trust-crates-io",
        action="store_true",
        help="allow checksum-less static.crates.io downloads and record their computed SHA-256",
    )
    parser.add_argument("--work-dir", type=Path, default=HERE / "work" / "pilot")
    parser.add_argument("--output", type=Path, help="write canonical JSON here instead of stdout")
    parser.add_argument("--reassociation-jsonl-dir", type=Path)
    parser.add_argument("--reassociation-command", help="shell-free command; project path is appended")
    parser.add_argument("--source-signal-command", help="shell-free command; project path is appended")
    parser.add_argument("--timeout", type=float, default=120.0, help="per-scanner timeout in seconds")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = run_pilot(
            args.source,
            limit=args.limit,
            work_dir=args.work_dir,
            fetch=args.fetch,
            min_loc=args.min_loc,
            require_bin=args.require_bin,
            reassociation_jsonl_dir=args.reassociation_jsonl_dir,
            reassociation_command=_command(args.reassociation_command),
            source_signal_command=_command(args.source_signal_command),
            timeout=args.timeout,
            trust_crates_io=args.trust_crates_io,
        )
        encoded = canonical_json_bytes(result)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(encoded)
        else:
            sys.stdout.buffer.write(encoded)
        return 0
    except (OSError, PilotError, argparse.ArgumentTypeError) as error:
        print(f"pilot: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
