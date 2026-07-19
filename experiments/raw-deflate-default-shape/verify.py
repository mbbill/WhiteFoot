#!/usr/bin/env python3
"""Compile and correctness-check one raw-DEFLATE Whitefoot candidate.

The evaluator deliberately exposes only compile and correctness feedback.  It
does not request proof reports and has no comparator or timing dependency.
"""

from __future__ import annotations

import contextlib
import ctypes
from dataclasses import dataclass
import hashlib
import io
import json
import mmap
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CORPUS = HERE / "correctness-corpus.json"
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
DEMOC = ROOT / "prototype" / "democ" / "democ.py"
CHECKER = ROOT / "prototype" / "checker" / "checker.py"

sys.path.insert(0, str(DEMOC.parent))
import democ  # noqa: E402


class HarnessFailure(RuntimeError):
    """The evaluator failed independently of the candidate."""


SCHEMA = "whitefoot.raw-deflate.correctness-corpus.v1"
CORPUS_SEED = 2026071901
MAX_DIAGNOSTIC_CHARS = 65_536
MAX_FEEDBACK_INPUT_BYTES = 4_096
MAX_SOURCE_BYTES = 1_048_576
MAX_VISIBLE_LENGTH = (1 << 31) - 1
WORK8_LENGTH = 65_536
WORK16_LENGTH = 4_096
WORK32_LENGTH = 4_096
CALL_TIMEOUT_SECONDS = 2.0

EXPECTED_FILE_SHA256 = {
    CLANG: "7def90dd8829726686213a747fc5bff1583df933dae5edc55d755479e0bfe00a",
    PYTHON: "271143990bc83af0fb2404a255038f5faafb96df1584ed7f085e5018c0f33ffb",
    SDK_SETTINGS: "f8d005f09381389167f9e0aeaa169bc9e7dff162ef22ca2fd8e98df7ff1acafe",
    DEMOC: "65677c102521e9034f16690e00d2a861ce559ea8579785b1c6fa7729bd4c77ef",
    CHECKER: "cfa052e36869004cc68223664233eb7bc41a82012cde7a13a208251c20d4b106",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tool_identity() -> Dict[str, str]:
    observed: Dict[str, str] = {}
    for path, expected in EXPECTED_FILE_SHA256.items():
        if path.is_symlink() or not path.is_file():
            raise HarnessFailure("locked evaluator input is missing or not a regular file")
        actual = sha256_file(path)
        if actual != expected:
            raise HarnessFailure("locked evaluator input identity changed")
        observed[str(path)] = actual
    return observed


def sanitized_build_environment() -> Dict[str, str]:
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
    environment["LC_ALL"] = "C"
    environment["LANG"] = "C"
    return environment


def run(
    command: Sequence[str],
    *,
    env: Optional[Dict[str, str]] = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
        timeout=timeout,
        text=True,
    )


def diagnostic(code: str, message: str) -> Dict[str, str]:
    return {"code": code, "message": message[:MAX_DIAGNOSTIC_CHARS]}


def result(
    compile_passed: bool,
    compile_diagnostics: List[Dict[str, str]],
    correctness_passed: bool,
    correctness_diagnostics: List[Dict[str, str]],
) -> Dict[str, Any]:
    return {
        "compile": {
            "passed": compile_passed,
            "diagnostics": compile_diagnostics,
        },
        "correctness": {
            "passed": correctness_passed,
            "diagnostics": correctness_diagnostics,
        },
    }


LLVM_FUNCTION = re.compile(
    r"^define\b[^\n@]*@([A-Za-z_.$][A-Za-z0-9_.$-]*)\(", re.MULTILINE
)


def namespace_module(ir: str, namespace: str, entry: str) -> str:
    definitions = set(LLVM_FUNCTION.findall(ir))
    if "inflate_raw" not in definitions:
        raise HarnessFailure("compiled module lacks the required entry definition")
    replacements = {
        name: entry if name == "inflate_raw" else "xlang_%s_%s" % (namespace, name)
        for name in definitions
    }
    names = "|".join(
        re.escape(name) for name in sorted(definitions, key=len, reverse=True)
    )
    return re.sub(
        r"@(%s)(?=\()" % names,
        lambda match: "@" + replacements[match.group(1)],
        ir,
    )


EXPECTED_PARAMS = [
    {
        "name": "src",
        "mode": {"kind": "ref", "region": "s", "uniq": False},
        "ty": "buffer<u8>",
    },
    {
        "name": "out",
        "mode": {"kind": "ref", "region": "o", "uniq": True},
        "ty": "buffer<u8>",
    },
    {
        "name": "result",
        "mode": {"kind": "ref", "region": "r", "uniq": True},
        "ty": "InflateResult",
    },
    {"name": "work8", "mode": {"kind": "own"}, "ty": "buffer<u8>"},
    {"name": "work16", "mode": {"kind": "own"}, "ty": "buffer<u16>"},
    {"name": "work32", "mode": {"kind": "own"}, "ty": "buffer<u32>"},
]


def parse_effect_row(tokens: Sequence[str]) -> Optional[Dict[str, Any]]:
    groups: Dict[str, Any] = {}
    cursor = 0
    while cursor < len(tokens):
        name = tokens[cursor]
        cursor += 1
        if name == "traps":
            if name in groups:
                return None
            groups[name] = True
        elif name in ("reads", "writes", "allocates"):
            if name in groups or cursor >= len(tokens) or tokens[cursor] != "(":
                return None
            cursor += 1
            values = []
            while cursor < len(tokens) and tokens[cursor] != ")":
                values.append(tokens[cursor])
                cursor += 1
            if cursor >= len(tokens) or not values:
                return None
            cursor += 1
            groups[name] = values
        else:
            return None
        if cursor == len(tokens):
            break
        if tokens[cursor] != ",":
            return None
        cursor += 1
        if cursor == len(tokens):
            return None
    return groups


def contains_allocation(function: Dict[str, Any]) -> bool:
    if "allocates" in function.get("effects", []):
        return True

    def walk(value: Any) -> bool:
        if isinstance(value, dict):
            if value.get("op") in ("box_new", "arena_new", "buffer_new"):
                return True
            return any(walk(child) for child in value.values())
        if isinstance(value, list):
            return any(walk(child) for child in value)
        return False

    return walk(function.get("body", []))


def public_api_mismatch(
    source: str,
    structs: Dict[str, Any],
    functions: List[Dict[str, Any]],
) -> Optional[str]:
    tokens = democ.toks(source)
    declaration_count = sum(
        1
        for index in range(len(tokens) - 1)
        if tokens[index] == "struct" and tokens[index + 1] == "InflateResult"
    )
    if declaration_count != 1:
        return "the source must define exactly one struct named InflateResult"
    if structs.get("InflateResult") != [
        {"name": "status", "ty": "u64"},
        {"name": "produced", "ty": "u64"},
    ]:
        return "InflateResult fields must be exactly status: u64; produced: u64"
    if any(
        tokens[index] == "fn" and tokens[index + 1] == "main"
        for index in range(len(tokens) - 1)
    ):
        return "function main is forbidden for this candidate"
    entries = [
        function for function in functions if function.get("name") == "inflate_raw"
    ]
    if len(entries) != 1:
        return "the source must define exactly one function named inflate_raw"
    if any(contains_allocation(function) for function in functions):
        return "allocation is forbidden in every candidate function"

    entry = entries[0]
    if entry.get("requires") is not None:
        return "inflate_raw must not contain a requires block"
    if entry.get("regions") != ["s", "o", "r"]:
        return "inflate_raw regions must be exactly ['s', 'o', 'r']"
    if entry.get("params") != EXPECTED_PARAMS:
        return "inflate_raw parameters do not match the required six-parameter ABI"
    if entry.get("rmode") != {"kind": "own"} or entry.get("rty") != "unit":
        return "inflate_raw must return exactly own unit"
    effects = parse_effect_row(entry.get("effects", []))
    if effects is None:
        return "inflate_raw has a malformed effect row"
    reads = effects.get("reads")
    writes = effects.get("writes")
    if (
        set(effects) != {"reads", "writes", "traps"}
        or not isinstance(reads, list)
        or len(reads) != len(set(reads))
        or set(reads) not in (
            {"'s"},
            {"'s", "'o"},
            {"'s", "'r"},
            {"'s", "'o", "'r"},
        )
        or not isinstance(writes, list)
        or len(writes) != 2
        or set(writes) != {"'o", "'r"}
    ):
        return (
            "inflate_raw must read 's, write exactly 'o and 'r, include traps, "
            "and may additionally declare reads only for 'o or 'r"
        )
    return None


@dataclass(frozen=True)
class Fixture:
    identifier: str
    kind: str
    input_data: bytes
    oracle_output: bytes
    unit_boundaries: Tuple[int, ...]
    input_bits_consumed: int
    error: Optional[str]


@dataclass(frozen=True)
class Call:
    fixture: int
    capacity: int


@dataclass(frozen=True)
class CorpusData:
    fixtures: Tuple[Fixture, ...]
    calls: Tuple[Call, ...]
    sha256: str


def require_exact_keys(value: Dict[str, Any], expected: Iterable[str], label: str) -> None:
    expected_set = set(expected)
    if set(value) != expected_set:
        raise HarnessFailure("%s fields do not match the locked schema" % label)


def canonical_hex(value: Any, label: str) -> bytes:
    if not isinstance(value, str) or re.fullmatch(r"(?:[0-9a-f]{2})*", value) is None:
        raise HarnessFailure("%s is not canonical lowercase hexadecimal" % label)
    return bytes.fromhex(value)


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("ascii")


def require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise HarnessFailure("%s is not a lowercase SHA-256" % label)
    return value


def load_corpus(path: Path = CORPUS) -> CorpusData:
    if path.is_symlink() or not path.is_file():
        raise HarnessFailure("correctness corpus is missing or not a regular file")
    identity = sha256_file(path)
    try:
        encoded = path.read_bytes()
        raw = json.loads(encoded.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise HarnessFailure("correctness corpus is not valid UTF-8 JSON") from error
    if not isinstance(raw, dict):
        raise HarnessFailure("correctness corpus root is not an object")
    if encoded != canonical_json_bytes(raw):
        raise HarnessFailure("correctness corpus is not canonical JSON")
    require_exact_keys(
        raw, ("schema", "seed", "metadata", "counts", "fixtures", "calls"), "corpus"
    )
    if raw.get("schema") != SCHEMA:
        raise HarnessFailure("correctness corpus schema identity changed")
    if raw.get("seed") != CORPUS_SEED:
        raise HarnessFailure("correctness corpus seed is invalid")
    metadata = raw.get("metadata")
    counts = raw.get("counts")
    if not isinstance(metadata, dict) or not isinstance(counts, dict):
        raise HarnessFailure("correctness corpus metadata or counts is not an object")
    metadata_keys = (
        "generator_sha256",
        "oracle_sha256",
        "stock_adapter_source_sha256",
        "stock_helper_sha256",
        "zlib_ng_adapter_source_sha256",
        "zlib_ng_helper_sha256",
        "native_provenance",
        "cross_check",
        "coverage",
        "fixture_payload_sha256",
        "input_sequence_sha256",
        "capacity_policy",
    )
    require_exact_keys(metadata, metadata_keys, "corpus.metadata")
    for key in (
        "generator_sha256",
        "oracle_sha256",
        "stock_adapter_source_sha256",
        "stock_helper_sha256",
        "zlib_ng_adapter_source_sha256",
        "zlib_ng_helper_sha256",
        "fixture_payload_sha256",
        "input_sequence_sha256",
    ):
        require_sha256(metadata.get(key), "corpus.metadata.%s" % key)
    if (
        not isinstance(metadata.get("native_provenance"), dict)
        or not isinstance(metadata.get("cross_check"), dict)
        or not isinstance(metadata.get("coverage"), dict)
        or not isinstance(metadata.get("capacity_policy"), str)
        or not metadata["capacity_policy"]
    ):
        raise HarnessFailure("correctness corpus metadata has invalid field types")
    metadata_paths = {
        "generator_sha256": HERE / "corpus.py",
        "oracle_sha256": HERE / "oracle.py",
        "stock_adapter_source_sha256": HERE / "stock_zlib.c",
        "stock_helper_sha256": HERE / "stock_zlib.py",
        "zlib_ng_adapter_source_sha256": HERE / "reference.c",
        "zlib_ng_helper_sha256": HERE / "reference.py",
    }
    for key, source_path in metadata_paths.items():
        if source_path.is_symlink() or not source_path.is_file():
            raise HarnessFailure("a corpus source binding is missing")
        if metadata[key] != sha256_file(source_path):
            raise HarnessFailure("a corpus source binding is stale")
    require_exact_keys(
        counts,
        (
            "fixtures",
            "calls",
            "valid_fixtures",
            "malformed_fixtures",
            "input_bytes",
            "oracle_output_bytes",
        ),
        "corpus.counts",
    )
    if any(type(value) is not int or value < 0 for value in counts.values()):
        raise HarnessFailure("correctness corpus counts are invalid")
    raw_fixtures = raw.get("fixtures")
    raw_calls = raw.get("calls")
    if not isinstance(raw_fixtures, list) or not raw_fixtures:
        raise HarnessFailure("correctness corpus fixtures must be a nonempty array")
    if not isinstance(raw_calls, list) or not raw_calls:
        raise HarnessFailure("correctness corpus calls must be a nonempty array")

    fixtures: List[Fixture] = []
    identifiers = set()
    fixture_keys = (
        "id",
        "kind",
        "input_hex",
        "oracle_output_hex",
        "unit_boundaries",
        "input_bits_consumed",
        "error",
    )
    for index, item in enumerate(raw_fixtures):
        label = "fixtures[%d]" % index
        if not isinstance(item, dict):
            raise HarnessFailure("%s is not an object" % label)
        require_exact_keys(item, fixture_keys, label)
        identifier = item["id"]
        if (
            not isinstance(identifier, str)
            or re.fullmatch(r"[A-Za-z0-9._/-]{1,128}", identifier) is None
            or identifier in identifiers
        ):
            raise HarnessFailure("%s.id is invalid or duplicated" % label)
        identifiers.add(identifier)
        kind = item["kind"]
        if not isinstance(kind, str) or re.fullmatch(r"[a-z0-9-]+", kind) is None:
            raise HarnessFailure("%s.kind is invalid" % label)
        input_data = canonical_hex(item["input_hex"], label + ".input_hex")
        oracle_output = canonical_hex(
            item["oracle_output_hex"], label + ".oracle_output_hex"
        )
        raw_boundaries = item["unit_boundaries"]
        if not isinstance(raw_boundaries, list) or any(
            type(boundary) is not int for boundary in raw_boundaries
        ):
            raise HarnessFailure("%s.unit_boundaries is not an integer array" % label)
        boundaries = tuple(raw_boundaries)
        if any(boundary <= 0 for boundary in boundaries) or any(
            left >= right for left, right in zip(boundaries, boundaries[1:])
        ):
            raise HarnessFailure("%s.unit_boundaries is not strictly increasing" % label)
        if (not oracle_output and boundaries) or (
            oracle_output and (not boundaries or boundaries[-1] != len(oracle_output))
        ):
            raise HarnessFailure("%s.unit_boundaries does not cover the oracle prefix" % label)
        bits = item["input_bits_consumed"]
        if type(bits) is not int or bits < 0 or bits > len(input_data) * 8:
            raise HarnessFailure("%s.input_bits_consumed is out of range" % label)
        error = item["error"]
        if error is not None and (not isinstance(error, str) or not error):
            raise HarnessFailure("%s.error must be null or a nonempty string" % label)
        fixtures.append(
            Fixture(
                identifier,
                kind,
                input_data,
                oracle_output,
                boundaries,
                bits,
                error,
            )
        )

    fixture_by_id = {
        fixture.identifier: index for index, fixture in enumerate(fixtures)
    }
    calls: List[Call] = []
    seen_calls = set()
    referenced = set()
    for index, item in enumerate(raw_calls):
        label = "calls[%d]" % index
        if not isinstance(item, dict):
            raise HarnessFailure("%s is not an object" % label)
        require_exact_keys(item, ("fixture", "capacity"), label)
        fixture_id = item["fixture"]
        capacity = item["capacity"]
        if not isinstance(fixture_id, str) or fixture_id not in fixture_by_id:
            raise HarnessFailure("%s.fixture does not name a fixture" % label)
        fixture_index = fixture_by_id[fixture_id]
        if type(capacity) is not int or capacity < 0 or capacity > MAX_VISIBLE_LENGTH:
            raise HarnessFailure("%s.capacity is out of range" % label)
        key = (fixture_id, capacity)
        if key in seen_calls:
            raise HarnessFailure("%s duplicates an earlier call" % label)
        seen_calls.add(key)
        referenced.add(fixture_index)
        calls.append(Call(fixture_index, capacity))
    if referenced != set(range(len(fixtures))):
        raise HarnessFailure("correctness corpus contains an unreferenced fixture")
    expected_counts = {
        "fixtures": len(fixtures),
        "calls": len(calls),
        "valid_fixtures": sum(fixture.error is None for fixture in fixtures),
        "malformed_fixtures": sum(fixture.error is not None for fixture in fixtures),
        "input_bytes": sum(len(fixture.input_data) for fixture in fixtures),
        "oracle_output_bytes": sum(
            len(fixture.oracle_output) for fixture in fixtures
        ),
    }
    if counts != expected_counts:
        raise HarnessFailure("correctness corpus counts do not match its records")
    payload_hash = hashlib.sha256(
        canonical_json_bytes({"fixtures": raw_fixtures, "calls": raw_calls})
    ).hexdigest()
    if metadata["fixture_payload_sha256"] != payload_hash:
        raise HarnessFailure("correctness corpus payload hash is inconsistent")
    input_hash = hashlib.sha256()
    for fixture in fixtures:
        input_hash.update(len(fixture.input_data).to_bytes(8, "little"))
        input_hash.update(fixture.input_data)
    if metadata["input_sequence_sha256"] != input_hash.hexdigest():
        raise HarnessFailure("correctness corpus input-sequence hash is inconsistent")
    return CorpusData(tuple(fixtures), tuple(calls), identity)


class Buf8(ctypes.Structure):
    _fields_ = [("p", ctypes.POINTER(ctypes.c_uint8)), ("n", ctypes.c_int64)]


class Buf16(ctypes.Structure):
    _fields_ = [("p", ctypes.POINTER(ctypes.c_uint16)), ("n", ctypes.c_int64)]


class Buf32(ctypes.Structure):
    _fields_ = [("p", ctypes.POINTER(ctypes.c_uint32)), ("n", ctypes.c_int64)]


class InflateResult(ctypes.Structure):
    _fields_ = [("status", ctypes.c_uint64), ("produced", ctypes.c_uint64)]


InflateFunction = ctypes.CFUNCTYPE(
    None,
    Buf8,
    Buf8,
    ctypes.POINTER(InflateResult),
    Buf8,
    Buf16,
    Buf32,
)


def check_abi_layout() -> None:
    if (
        ctypes.sizeof(Buf8) != 16
        or ctypes.sizeof(Buf16) != 16
        or ctypes.sizeof(Buf32) != 16
        or ctypes.sizeof(InflateResult) != 16
        or InflateResult.status.offset != 0
        or InflateResult.produced.offset != 8
    ):
        raise HarnessFailure("host ABI does not match the locked candidate boundary")


LIBC = ctypes.CDLL(None, use_errno=True)
LIBC.mmap.restype = ctypes.c_void_p
LIBC.mmap.argtypes = [
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_long,
]
LIBC.mprotect.restype = ctypes.c_int
LIBC.mprotect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
LIBC.munmap.restype = ctypes.c_int
LIBC.munmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t]


class GuardedRegion:
    """Shared anonymous storage with inaccessible pages on both sides."""

    def __init__(self, visible_bytes: int, poison: int, align_right: bool) -> None:
        if visible_bytes < 0:
            raise HarnessFailure("negative guarded-region length")
        self.page_size = os.sysconf("SC_PAGE_SIZE")
        self.visible_size = visible_bytes
        body_need = max(1, visible_bytes)
        self.body_size = (
            (body_need + self.page_size - 1) // self.page_size * self.page_size
        )
        self.total_size = self.body_size + 2 * self.page_size
        flags = mmap.MAP_SHARED | mmap.MAP_ANON
        mapped = LIBC.mmap(None, self.total_size, 0, flags, -1, 0)
        failed = ctypes.c_void_p(-1).value
        if mapped is None or mapped == failed:
            raise HarnessFailure("guarded mmap failed")
        self.base = int(mapped)
        self.body = self.base + self.page_size
        if LIBC.mprotect(self.body, self.body_size, mmap.PROT_READ | mmap.PROT_WRITE):
            LIBC.munmap(self.base, self.total_size)
            raise HarnessFailure("guarded mprotect failed")
        ctypes.memset(self.body, poison, self.body_size)
        self.visible = (
            self.body + self.body_size - visible_bytes if align_right else self.body
        )
        self.closed = False

    def __enter__(self) -> "GuardedRegion":
        return self

    def __exit__(self, _kind: Any, _value: Any, _traceback: Any) -> None:
        self.close()

    def close(self) -> None:
        if not self.closed:
            if LIBC.munmap(self.base, self.total_size):
                raise HarnessFailure("guarded munmap failed")
            self.closed = True

    def body_bytes(self) -> bytes:
        return ctypes.string_at(self.body, self.body_size)

    def visible_bytes(self) -> bytes:
        if self.visible_size == 0:
            return b""
        return ctypes.string_at(self.visible, self.visible_size)

    def write_visible(self, value: bytes) -> None:
        if len(value) != self.visible_size:
            raise HarnessFailure("guarded-region initializer length mismatch")
        if value:
            ctypes.memmove(self.visible, value, len(value))

    def make_read_only(self) -> None:
        if LIBC.mprotect(self.body, self.body_size, mmap.PROT_READ):
            raise HarnessFailure("read-only mprotect failed")

    def outside_visible_unchanged(self, before: bytes) -> bool:
        after = self.body_bytes()
        offset = self.visible - self.body
        end = offset + self.visible_size
        return before[:offset] == after[:offset] and before[end:] == after[end:]


@dataclass(frozen=True)
class Observation:
    status: int
    produced: int
    output: bytes


def pointer(address: int, scalar: Any) -> Any:
    return ctypes.cast(ctypes.c_void_p(address), ctypes.POINTER(scalar))


def child_call(function: Any, arguments: Tuple[Any, ...]) -> Optional[str]:
    try:
        process = os.fork()
    except OSError as error:
        raise HarnessFailure("could not fork guarded candidate call") from error
    if process == 0:
        try:
            signal.signal(signal.SIGALRM, signal.SIG_DFL)
            signal.setitimer(signal.ITIMER_REAL, CALL_TIMEOUT_SECONDS)
            function(*arguments)
            os._exit(0)
        except BaseException:
            os._exit(125)
    try:
        waited, status = os.waitpid(process, 0)
    except BaseException:
        try:
            os.kill(process, signal.SIGKILL)
        except OSError:
            pass
        try:
            os.waitpid(process, 0)
        except OSError:
            pass
        raise
    if waited != process:
        raise HarnessFailure("waitpid returned the wrong guarded child")
    if os.WIFSIGNALED(status):
        number = os.WTERMSIG(status)
        if number == signal.SIGALRM:
            return "call did not return before the correctness limit"
        try:
            name = signal.Signals(number).name
        except ValueError:
            name = str(number)
        return "call terminated by signal %s" % name
    if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
        return "call did not return normally"
    return None


def first_changed(before: bytes, after: bytes, start: int = 0) -> Optional[int]:
    for index in range(start, min(len(before), len(after))):
        if before[index] != after[index]:
            return index
    if len(before) != len(after):
        return min(len(before), len(after))
    return None


def run_guarded_variant(
    function: Any,
    fixture: Fixture,
    capacity: int,
    call_index: int,
    align_right: bool,
) -> Tuple[Optional[Observation], Optional[str]]:
    poison = (0xA5 ^ ((call_index * 37) & 0xFF)) & 0xFF
    with contextlib.ExitStack() as stack:
        source = stack.enter_context(
            GuardedRegion(len(fixture.input_data), poison ^ 0x11, align_right)
        )
        output = stack.enter_context(GuardedRegion(capacity, poison, align_right))
        result_region = stack.enter_context(GuardedRegion(16, poison ^ 0x22, align_right))
        work8 = stack.enter_context(
            GuardedRegion(WORK8_LENGTH, poison ^ 0x33, align_right)
        )
        work16 = stack.enter_context(
            GuardedRegion(WORK16_LENGTH * 2, poison ^ 0x44, align_right)
        )
        work32 = stack.enter_context(
            GuardedRegion(WORK32_LENGTH * 4, poison ^ 0x55, align_right)
        )
        regions = (source, output, result_region, work8, work16, work32)
        spans = sorted((region.base, region.base + region.total_size) for region in regions)
        if any(left[1] > right[0] for left, right in zip(spans, spans[1:])):
            raise HarnessFailure("guarded argument mappings overlap")

        source.write_visible(fixture.input_data)
        source_before = source.body_bytes()
        output_before = output.body_bytes()
        result_before = result_region.body_bytes()
        work8_before = work8.body_bytes()
        work16_before = work16.body_bytes()
        work32_before = work32.body_bytes()

        result_pointer = ctypes.cast(
            ctypes.c_void_p(result_region.visible), ctypes.POINTER(InflateResult)
        )
        result_pointer.contents.status = 0xD3D3D3D3D3D3D3D3 ^ call_index
        result_pointer.contents.produced = 0xE4E4E4E4E4E4E4E4 ^ call_index
        # The result snapshot must include the field poison, not only the byte poison.
        result_before = result_region.body_bytes()
        source.make_read_only()

        arguments = (
            Buf8(pointer(source.visible, ctypes.c_uint8), len(fixture.input_data)),
            Buf8(pointer(output.visible, ctypes.c_uint8), capacity),
            result_pointer,
            Buf8(pointer(work8.visible, ctypes.c_uint8), WORK8_LENGTH),
            Buf16(pointer(work16.visible, ctypes.c_uint16), WORK16_LENGTH),
            Buf32(pointer(work32.visible, ctypes.c_uint32), WORK32_LENGTH),
        )
        failure = child_call(function, arguments)
        if failure is not None:
            return None, failure
        if source.body_bytes() != source_before:
            return None, "call changed the read-only source mapping"
        for label, region, before in (
            ("out", output, output_before),
            ("result", result_region, result_before),
            ("work8", work8, work8_before),
            ("work16", work16, work16_before),
            ("work32", work32, work32_before),
        ):
            if not region.outside_visible_unchanged(before):
                return None, "call changed storage outside visible %s" % label

        status = int(result_pointer.contents.status)
        produced = int(result_pointer.contents.produced)
        if status not in (0, 1, 2):
            return None, "result.status was not overwritten with a permitted value"
        if produced > capacity:
            return None, "result.produced exceeds output capacity"
        return Observation(status, produced, output.visible_bytes()), None


def semantic_failure(
    fixture: Fixture,
    capacity: int,
    observation: Observation,
    initial_output: bytes,
) -> Optional[str]:
    if fixture.error is None:
        if capacity >= len(fixture.oracle_output):
            expected_status = 0
            expected_produced = len(fixture.oracle_output)
        else:
            expected_status = 1
            expected_produced = max(
                (0,) + tuple(
                    boundary
                    for boundary in fixture.unit_boundaries
                    if boundary <= capacity
                )
            )
        if observation.status != expected_status:
            return "returned status %d instead of %d" % (
                observation.status,
                expected_status,
            )
        if observation.produced != expected_produced:
            return "returned produced=%d instead of %d" % (
                observation.produced,
                expected_produced,
            )
    else:
        if observation.status != 2:
            return "malformed input did not return Malformed"
        allowed = {0}
        allowed.update(
            boundary
            for boundary in fixture.unit_boundaries
            if boundary <= capacity
        )
        if observation.produced not in allowed:
            return "malformed input returned a non-unit-boundary produced value"

    expected_prefix = fixture.oracle_output[: observation.produced]
    actual_prefix = observation.output[: observation.produced]
    mismatch = first_changed(expected_prefix, actual_prefix)
    if mismatch is not None:
        return "decoded prefix first differs at output byte %d" % mismatch
    suffix = observation.output[observation.produced :]
    initial_suffix = initial_output[observation.produced :]
    changed = first_changed(initial_suffix, suffix)
    if changed is not None:
        return "output suffix first changed at byte %d" % (observation.produced + changed)
    return None


def observation_difference(left: Observation, right: Observation) -> Optional[str]:
    if left.status != right.status:
        return "compiled variants returned different statuses"
    if left.produced != right.produced:
        return "compiled variants returned different produced values"
    changed = first_changed(left.output, right.output)
    if changed is not None:
        return "compiled variants first differed at output byte %d" % changed
    return None


def failure_feedback(
    fixture: Fixture, capacity: int, call_ordinal: int, message: str
) -> str:
    shown = fixture.input_data[:MAX_FEEDBACK_INPUT_BYTES]
    omitted = len(fixture.input_data) - len(shown)
    input_description = shown.hex()
    if omitted:
        input_description += "...(%d input bytes omitted)" % omitted
    return (
        "call_ordinal=%d; classification=%s; capacity=%d; input_hex=%s; failure=%s"
        % (
            call_ordinal,
            "valid" if fixture.error is None else "malformed",
            capacity,
            input_description,
            message,
        )
    )


def resolve_function(library: Any, symbol: str) -> Any:
    try:
        function = getattr(library, symbol)
    except AttributeError as error:
        raise HarnessFailure("linked evaluator library lacks a required entry") from error
    function.argtypes = list(InflateFunction._argtypes_)
    function.restype = None
    return function


def checked_evaluator_result(
    value: Dict[str, Any], locked_tools: Dict[str, str], corpus: CorpusData
) -> Dict[str, Any]:
    if tool_identity() != locked_tools:
        raise HarnessFailure("locked evaluator inputs changed during evaluation")
    current_corpus = load_corpus()
    if current_corpus.sha256 != corpus.sha256:
        raise HarnessFailure("correctness corpus changed during evaluation")
    return value


def evaluate(candidate: Path) -> Dict[str, Any]:
    if Path(sys.executable).resolve() != PYTHON.resolve():
        raise HarnessFailure("evaluator is not running under the locked Python")
    locked_tools = tool_identity()
    check_abi_layout()
    corpus = load_corpus()
    try:
        if candidate.is_symlink() or not candidate.is_file():
            raise OSError("candidate is not a regular non-symlink file")
        if candidate.stat().st_size > MAX_SOURCE_BYTES:
            return checked_evaluator_result(
                result(
                    False,
                    [
                        diagnostic(
                            "SOURCE_SIZE", "candidate source exceeds 1,048,576 bytes"
                        )
                    ],
                    False,
                    [diagnostic("NOT_RUN", "compile failed")],
                ),
                locked_tools,
                corpus,
            )
        with candidate.open("r", encoding="utf-8", newline="") as stream:
            source = stream.read()
    except (OSError, UnicodeError) as error:
        return checked_evaluator_result(
            result(
                False,
                [diagnostic("SOURCE_READ", str(error))],
                False,
                [diagnostic("NOT_RUN", "compile failed")],
            ),
            locked_tools,
            corpus,
        )

    compiler_text = io.StringIO()
    try:
        with contextlib.redirect_stdout(compiler_text), contextlib.redirect_stderr(
            compiler_text
        ):
            structs, _enums, functions, _contracts, _conforms, _consts = (
                democ.parse_program(source)
            )
    except (MemoryError, KeyboardInterrupt, GeneratorExit) as error:
        raise HarnessFailure("unexpected source-parser failure") from error
    except (SystemExit, Exception) as error:
        message = compiler_text.getvalue() or str(error) or type(error).__name__
        return checked_evaluator_result(
            result(
                False,
                [diagnostic("WHITEFOOT_COMPILE", message)],
                False,
                [diagnostic("NOT_RUN", "compile failed")],
            ),
            locked_tools,
            corpus,
        )

    mismatch = public_api_mismatch(source, structs, functions)
    if mismatch is not None:
        return checked_evaluator_result(
            result(
                False,
                [diagnostic("WHITEFOOT_PUBLIC_API", mismatch)],
                False,
                [diagnostic("NOT_RUN", "compile failed")],
            ),
            locked_tools,
            corpus,
        )

    compiler_text.seek(0)
    compiler_text.truncate(0)
    try:
        with contextlib.redirect_stdout(compiler_text), contextlib.redirect_stderr(
            compiler_text
        ):
            # Proof reports are attribution evidence, not repair feedback.
            facts_ir = democ.compile_program(source, alias=True)
            nofacts_ir = democ.compile_program(source, alias=False)
        facts_ir = namespace_module(facts_ir, "inflate_facts", "xlang_inflate_facts")
        nofacts_ir = namespace_module(
            nofacts_ir, "inflate_nofacts", "xlang_inflate_nofacts"
        )
    except (democ.CheckError, SystemExit) as error:
        message = compiler_text.getvalue() or str(error) or type(error).__name__
        return checked_evaluator_result(
            result(
                False,
                [diagnostic("WHITEFOOT_COMPILE", message)],
                False,
                [diagnostic("NOT_RUN", "compile failed")],
            ),
            locked_tools,
            corpus,
        )
    except BaseException as error:
        raise HarnessFailure("unexpected compiler or namespacing failure") from error

    build_environment = sanitized_build_environment()
    with tempfile.TemporaryDirectory(prefix="whitefoot-raw-deflate-verify-") as raw_build:
        build = Path(raw_build)
        facts_ll = build / "facts.ll"
        nofacts_ll = build / "nofacts.ll"
        facts_obj = build / "facts.o"
        nofacts_obj = build / "nofacts.o"
        library_path = build / "candidate.dylib"
        facts_ll.write_text(facts_ir, encoding="utf-8")
        nofacts_ll.write_text(nofacts_ir, encoding="utf-8")
        for ll_path, object_path in (
            (facts_ll, facts_obj),
            (nofacts_ll, nofacts_obj),
        ):
            try:
                compiled = run(
                    [
                        str(CLANG),
                        "--no-default-config",
                        "-isysroot",
                        str(MACOS_SDK),
                        "-O3",
                        "-c",
                        str(ll_path),
                        "-o",
                        str(object_path),
                    ],
                    env=build_environment,
                )
            except subprocess.TimeoutExpired as error:
                raise HarnessFailure("locked native compilation timed out") from error
            if compiled.returncode != 0:
                raise HarnessFailure("compiler emitted a module Clang could not compile")
        try:
            linked = run(
                [
                    str(CLANG),
                    "--no-default-config",
                    "-isysroot",
                    str(MACOS_SDK),
                    "-dynamiclib",
                    str(facts_obj),
                    str(nofacts_obj),
                    "-o",
                    str(library_path),
                ],
                env=build_environment,
            )
        except subprocess.TimeoutExpired as error:
            raise HarnessFailure("locked evaluator link timed out") from error
        if linked.returncode != 0:
            raise HarnessFailure("locked evaluator link failed")
        try:
            library = ctypes.CDLL(str(library_path), mode=ctypes.RTLD_LOCAL)
        except OSError as error:
            raise HarnessFailure("could not load the linked evaluator library") from error
        facts = resolve_function(library, "xlang_inflate_facts")
        nofacts = resolve_function(library, "xlang_inflate_nofacts")

        for call_index, call in enumerate(corpus.calls):
            fixture = corpus.fixtures[call.fixture]
            poison = (0xA5 ^ ((call_index * 37) & 0xFF)) & 0xFF
            initial_output = bytes([poison]) * call.capacity
            observations: List[Observation] = []
            for function, align_right in (
                (facts, True),
                (facts, False),
                (nofacts, True),
                (nofacts, False),
            ):
                observation, failure = run_guarded_variant(
                    function, fixture, call.capacity, call_index, align_right
                )
                if failure is None and observation is not None:
                    failure = semantic_failure(
                        fixture, call.capacity, observation, initial_output
                    )
                if failure is None and observation is not None and observations:
                    failure = observation_difference(observations[0], observation)
                if failure is None and observation is not None:
                    observations.append(observation)
                    continue
                failure = failure or "candidate call failed"
                break
            if failure is not None:
                return checked_evaluator_result(
                    result(
                        True,
                        [],
                        False,
                        [
                            diagnostic(
                                "CORRECTNESS",
                                failure_feedback(
                                    fixture, call.capacity, call_index, failure
                                ),
                            )
                        ],
                    ),
                    locked_tools,
                    corpus,
                )

    return checked_evaluator_result(
        result(
            True,
            [],
            True,
            [
                diagnostic(
                    "CORPUS",
                    "correct calls=%d fixtures=%d"
                    % (len(corpus.calls), len(corpus.fixtures)),
                )
            ],
        ),
        locked_tools,
        corpus,
    )


def self_test() -> None:
    if Path(sys.executable).resolve() != PYTHON.resolve():
        raise HarnessFailure("self-test is not running under the locked Python")
    tool_identity()
    load_corpus()

    synthetic_ir = """define void @inflate_raw() { ret void }
define void @helper() { call void @inflate_raw(); ret void }
"""
    namespaced = namespace_module(synthetic_ir, "inflate_facts", "xlang_inflate_facts")
    if "@xlang_inflate_facts()" not in namespaced:
        raise HarnessFailure("namespacing self-test failed")
    if "@xlang_inflate_facts_helper()" not in namespaced:
        raise HarnessFailure("helper namespacing self-test failed")

    source = """struct InflateResult {
  status: u64;
  produced: u64;
}
fn inflate_raw ['s, 'o, 'r] (src: &'s buffer<u8>, out: &uniq 'o buffer<u8>, result: &uniq 'r InflateResult, work8: own buffer<u8>, work16: own buffer<u16>, work32: own buffer<u32>) -> own unit reads('s), writes('o 'r), traps {
}
"""
    structs, _enums, functions, _contracts, _conforms, _consts = democ.parse_program(source)
    if public_api_mismatch(source, structs, functions) is not None:
        raise HarnessFailure("public-API self-test failed")

    fixture = Fixture("self", "valid", b"", b"abc", (1, 3), 0, None)
    initial = b"\xA5" * 2
    observation = Observation(1, 1, b"a\xA5")
    if semantic_failure(fixture, 2, observation, initial) is not None:
        raise HarnessFailure("result-contract self-test failed")
    with GuardedRegion(3, 0xA5, True) as region:
        region.write_visible(b"abc")
        before = region.body_bytes()
        if region.visible_bytes() != b"abc" or not region.outside_visible_unchanged(before):
            raise HarnessFailure("guarded-region self-test failed")


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        try:
            self_test()
        except BaseException as error:
            print("raw-DEFLATE evaluator harness failure: %s" % error, file=sys.stderr)
            return 70
        print("self-test ok")
        return 0
    if len(sys.argv) != 2:
        print(
            json.dumps(
                result(
                    False,
                    [diagnostic("USAGE", "expected candidate path")],
                    False,
                    [diagnostic("NOT_RUN", "usage error")],
                ),
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    try:
        value = evaluate(Path(sys.argv[1]).resolve())
    except BaseException as error:
        print("raw-DEFLATE evaluator harness failure: %s" % error, file=sys.stderr)
        return 70
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
