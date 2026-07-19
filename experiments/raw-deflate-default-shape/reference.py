#!/usr/bin/env python3
"""Build and correctness-check the pinned public zlib-ng reference adapter.

This helper does not benchmark.  It verifies the local zlib-ng source and
build provenance, compiles reference.c against the native public API, loads
the resulting adapter, and exercises the three experiment status outcomes
through both its one-shot validation path and its prepared timing path. The
independent oracle, not this module, defines candidate correctness at
capacity-limited unit boundaries.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
from typing import Any, Sequence


EXPECTED_ZLIB_NG_VERSION = "2.3.3"
EXPECTED_ZLIB_NG_COMMIT = "12731092979c6d07f42da27da673a9f6c7b13586"
EXPECTED_ZLIB_NG_TREE = "baa7e2050b51c3db4c88bc8f2daf93ca0ae88a98"
DEFAULT_RESEARCH_ROOT = Path("/private/tmp/whitefoot-zlib-research.wpK9iq")

WF_RAW_DONE = 0
WF_RAW_NEED_OUTPUT = 1
WF_RAW_MALFORMED = 2

_U8_POINTER = ctypes.POINTER(ctypes.c_uint8)


def _run_text(command: Sequence[str], *, cwd: Path | None = None) -> str:
    process = subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip()
        raise RuntimeError(f"command failed ({' '.join(command)}): {detail}")
    return process.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(path: Path, description: str) -> Path:
    if not path.is_file():
        raise RuntimeError(f"missing {description}: {path}")
    return path


def _cmake_cache_values(cache_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in cache_path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("//") or line.startswith("#") or "=" not in line:
            continue
        typed_key, value = line.split("=", 1)
        key = typed_key.split(":", 1)[0]
        values[key] = value
    return values


def verify_provenance(checkout: Path, build_dir: Path, library: Path) -> dict[str, Any]:
    checkout = checkout.resolve()
    build_dir = build_dir.resolve()
    library = _require_file(library.resolve(), "zlib-ng shared library")
    header = _require_file(build_dir / "zlib-ng.h", "generated zlib-ng header")
    cache_path = _require_file(build_dir / "CMakeCache.txt", "zlib-ng CMake cache")

    commit = _run_text(["git", "-C", str(checkout), "rev-parse", "HEAD"])
    tree = _run_text(["git", "-C", str(checkout), "rev-parse", "HEAD^{tree}"])
    tag_commit = _run_text(
        ["git", "-C", str(checkout), "rev-parse", "refs/tags/2.3.3^{commit}"]
    )
    tracked_status = _run_text(
        ["git", "-C", str(checkout), "status", "--porcelain", "--untracked-files=no"]
    )

    if commit != EXPECTED_ZLIB_NG_COMMIT:
        raise RuntimeError(f"zlib-ng commit is {commit}, expected {EXPECTED_ZLIB_NG_COMMIT}")
    if tree != EXPECTED_ZLIB_NG_TREE:
        raise RuntimeError(f"zlib-ng tree is {tree}, expected {EXPECTED_ZLIB_NG_TREE}")
    if tag_commit != EXPECTED_ZLIB_NG_COMMIT:
        raise RuntimeError("zlib-ng tag 2.3.3 does not resolve to the pinned commit")
    if tracked_status:
        raise RuntimeError("zlib-ng checkout has tracked modifications")

    header_text = header.read_text(encoding="utf-8")
    version_match = re.search(
        r'^#define ZLIBNG_VERSION "([^"]+)"$', header_text, flags=re.MULTILINE
    )
    if version_match is None or version_match.group(1) != EXPECTED_ZLIB_NG_VERSION:
        actual = version_match.group(1) if version_match is not None else "missing"
        raise RuntimeError(
            f"generated zlib-ng header version is {actual}, expected {EXPECTED_ZLIB_NG_VERSION}"
        )

    expected_cache = {
        "BUILD_SHARED_LIBS": "ON",
        "CMAKE_BUILD_TYPE": "Release",
        "WITH_ARMV8": "ON",
        "WITH_NATIVE_INSTRUCTIONS": "OFF",
        "WITH_NEON": "ON",
        "WITH_OPTIM": "ON",
        "WITH_RUNTIME_CPU_DETECTION": "ON",
        "ZLIB_COMPAT": "OFF",
    }
    cache_values = _cmake_cache_values(cache_path)
    mismatches = {
        key: {"actual": cache_values.get(key), "expected": expected}
        for key, expected in expected_cache.items()
        if cache_values.get(key) != expected
    }
    if mismatches:
        raise RuntimeError(f"zlib-ng build configuration mismatch: {mismatches}")
    cache_home_text = cache_values.get("CMAKE_HOME_DIRECTORY")
    if cache_home_text is None or Path(cache_home_text).resolve() != checkout:
        raise RuntimeError(
            "zlib-ng build directory was not configured from the pinned checkout: "
            f"{cache_home_text}"
        )

    return {
        "version": EXPECTED_ZLIB_NG_VERSION,
        "commit": commit,
        "tree": tree,
        "checkout": str(checkout),
        "checkout_tracked_clean": True,
        "build_dir": str(build_dir),
        "build_source_checkout": str(Path(cache_home_text).resolve()),
        "build_configuration": expected_cache,
        "generated_header": str(header),
        "generated_header_sha256": _sha256(header),
        "shared_library": str(library),
        "shared_library_sha256": _sha256(library),
    }


def find_library(build_dir: Path) -> Path:
    names = (
        "libz-ng.2.3.3.dylib",
        "libz-ng.so.2.3.3",
        "zlib-ng2.dll",
        "zlib-ng.dll",
    )
    for name in names:
        candidate = build_dir / name
        if candidate.is_file():
            return candidate
    raise RuntimeError(f"no zlib-ng {EXPECTED_ZLIB_NG_VERSION} shared library in {build_dir}")


def _adapter_suffix() -> str:
    if sys.platform == "darwin":
        return ".dylib"
    if os.name == "nt":
        return ".dll"
    return ".so"


def build_adapter(
    source: Path,
    checkout: Path,
    build_dir: Path,
    library: Path,
    output: Path,
    compiler: Sequence[str],
) -> list[str]:
    if os.name == "nt":
        raise RuntimeError("the verification helper currently requires a Unix-style C compiler")
    if not compiler:
        raise RuntimeError("empty C compiler command")

    output.parent.mkdir(parents=True, exist_ok=True)
    link_mode = "-dynamiclib" if sys.platform == "darwin" else "-shared"
    command = [
        *compiler,
        "-std=c11",
        "-O3",
        "-fPIC",
        "-fvisibility=hidden",
        "-Wall",
        "-Wextra",
        "-Werror",
        link_mode,
        "-I",
        str(build_dir),
        "-I",
        str(checkout),
        str(source),
        str(library),
        f"-Wl,-rpath,{library.parent}",
        "-o",
        str(output),
    ]
    _run_text(command)
    _require_file(output, "compiled reference adapter")
    return command


def load_adapter(path: Path) -> ctypes.CDLL:
    adapter = ctypes.CDLL(str(path.resolve()))

    adapter.wf_zng_header_version.argtypes = []
    adapter.wf_zng_header_version.restype = ctypes.c_char_p
    adapter.wf_zng_runtime_version.argtypes = []
    adapter.wf_zng_runtime_version.restype = ctypes.c_char_p

    for symbol in (adapter.wf_zng_header_version, adapter.wf_zng_runtime_version):
        version_bytes = symbol()
        version = version_bytes.decode("ascii") if version_bytes is not None else "missing"
        if version != EXPECTED_ZLIB_NG_VERSION:
            raise RuntimeError(
                f"loaded reference reports zlib-ng {version}, expected {EXPECTED_ZLIB_NG_VERSION}"
            )

    adapter.wf_zng_raw_inflate_once.argtypes = [
        _U8_POINTER,
        ctypes.c_size_t,
        _U8_POINTER,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    adapter.wf_zng_raw_inflate_once.restype = ctypes.c_int32
    adapter.wf_zng_raw_state_size.argtypes = []
    adapter.wf_zng_raw_state_size.restype = ctypes.c_size_t
    adapter.wf_zng_raw_state_alignment.argtypes = []
    adapter.wf_zng_raw_state_alignment.restype = ctypes.c_size_t
    adapter.wf_zng_raw_prepare.argtypes = [
        ctypes.c_void_p,
        ctypes.c_size_t,
        _U8_POINTER,
        ctypes.c_size_t,
        _U8_POINTER,
        ctypes.c_size_t,
    ]
    adapter.wf_zng_raw_prepare.restype = ctypes.c_int32
    adapter.wf_zng_raw_inflate_prepared.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    adapter.wf_zng_raw_inflate_prepared.restype = ctypes.c_int32
    adapter.wf_zng_raw_end.argtypes = [ctypes.c_void_p]
    adapter.wf_zng_raw_end.restype = ctypes.c_int32
    return adapter


def inflate_once(adapter: ctypes.CDLL, compressed: bytes, output_capacity: int) -> tuple[int, bytes]:
    if output_capacity < 0:
        raise ValueError("output capacity must be nonnegative")

    source_storage = (
        (ctypes.c_uint8 * len(compressed)).from_buffer_copy(compressed) if compressed else None
    )
    output_storage = (ctypes.c_uint8 * output_capacity)() if output_capacity else None
    source_pointer = (
        ctypes.cast(source_storage, _U8_POINTER) if source_storage is not None else None
    )
    output_pointer = (
        ctypes.cast(output_storage, _U8_POINTER) if output_storage is not None else None
    )
    produced = ctypes.c_size_t(0)
    status = int(
        adapter.wf_zng_raw_inflate_once(
            output_pointer,
            output_capacity,
            source_pointer,
            len(compressed),
            ctypes.byref(produced),
        )
    )
    if produced.value > output_capacity:
        raise RuntimeError("reference adapter reported output beyond its capacity")
    output = bytes(output_storage[: produced.value]) if output_storage is not None else b""
    return status, output


def inflate_prepared_once(
    adapter: ctypes.CDLL, compressed: bytes, output_capacity: int
) -> tuple[int, bytes]:
    if output_capacity < 0:
        raise ValueError("output capacity must be nonnegative")

    source_storage = (
        (ctypes.c_uint8 * len(compressed)).from_buffer_copy(compressed) if compressed else None
    )
    output_storage = (ctypes.c_uint8 * output_capacity)() if output_capacity else None
    source_pointer = (
        ctypes.cast(source_storage, _U8_POINTER) if source_storage is not None else None
    )
    output_pointer = (
        ctypes.cast(output_storage, _U8_POINTER) if output_storage is not None else None
    )
    state_size = int(adapter.wf_zng_raw_state_size())
    state_alignment = int(adapter.wf_zng_raw_state_alignment())
    if state_size <= 0 or state_alignment <= 0 or state_alignment & (state_alignment - 1):
        raise RuntimeError("reference adapter reported an invalid state layout")
    state_storage = (ctypes.c_uint8 * (state_size + state_alignment - 1))()
    state_address = (
        ctypes.addressof(state_storage) + state_alignment - 1
    ) & -state_alignment
    state_pointer = ctypes.c_void_p(state_address)
    prepared = int(
        adapter.wf_zng_raw_prepare(
            state_pointer,
            state_size,
            output_pointer,
            output_capacity,
            source_pointer,
            len(compressed),
        )
    )
    if prepared != WF_RAW_DONE:
        raise RuntimeError(f"reference adapter preparation failed with status {prepared}")
    produced = ctypes.c_size_t(0)
    status = int(
        adapter.wf_zng_raw_inflate_prepared(state_pointer, ctypes.byref(produced))
    )
    ended = int(adapter.wf_zng_raw_end(state_pointer))
    if ended != WF_RAW_DONE:
        raise RuntimeError(f"reference adapter teardown failed with status {ended}")
    if produced.value > output_capacity:
        raise RuntimeError("prepared reference adapter reported output beyond its capacity")
    output = bytes(output_storage[: produced.value]) if output_storage is not None else b""
    return status, output


def verify_status_contract(adapter: ctypes.CDLL) -> list[dict[str, Any]]:
    stored_hello = b"\x01\x05\x00\xfa\xffhello"
    cases = [
        ("complete", stored_hello, 5, WF_RAW_DONE, b"hello"),
        ("output-full", stored_hello, 4, WF_RAW_NEED_OUTPUT, b"hell"),
        ("output-zero", stored_hello, 0, WF_RAW_NEED_OUTPUT, b""),
        ("empty", b"\x03\x00", 0, WF_RAW_DONE, b""),
        ("reserved-block-type", b"\x07", 16, WF_RAW_MALFORMED, b""),
        ("truncated", stored_hello[:-1], 16, WF_RAW_MALFORMED, b"hell"),
    ]
    results: list[dict[str, Any]] = []
    for name, compressed, capacity, expected_status, expected_output in cases:
        status, output = inflate_once(adapter, compressed, capacity)
        if (status, output) != (expected_status, expected_output):
            raise RuntimeError(
                f"{name}: got status {status} and output {output!r}, "
                f"expected {expected_status} and {expected_output!r}"
            )
        prepared_status, prepared_output = inflate_prepared_once(
            adapter, compressed, capacity
        )
        if (prepared_status, prepared_output) != (status, output):
            raise RuntimeError(
                f"{name}: prepared path returned status {prepared_status} and output "
                f"{prepared_output!r}, one-shot path returned {status} and {output!r}"
            )
        results.append(
            {
                "case": name,
                "status": status,
                "produced": len(output),
                "output_hex": output.hex(),
            }
        )
    return results


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkout",
        type=Path,
        default=DEFAULT_RESEARCH_ROOT / "zlib-ng",
        help="pinned zlib-ng source checkout",
    )
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=DEFAULT_RESEARCH_ROOT / "build-zng-dispatch",
        help="pinned zlib-ng build directory",
    )
    parser.add_argument(
        "--library",
        type=Path,
        help="exact zlib-ng shared library (normally discovered in --build-dir)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="adapter output path (defaults to a new temporary directory)",
    )
    parser.add_argument(
        "--cc",
        default=os.environ.get("CC", "cc"),
        help="C compiler command (default: CC or cc)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    checkout = args.checkout.resolve()
    build_dir = args.build_dir.resolve()
    library = args.library.resolve() if args.library is not None else find_library(build_dir)
    source = Path(__file__).with_name("reference.c").resolve()
    if args.output is None:
        output_dir = Path(tempfile.mkdtemp(prefix="whitefoot-raw-deflate-reference-"))
        output = output_dir / f"libwhitefoot_raw_reference{_adapter_suffix()}"
    else:
        output = args.output.resolve()

    provenance = verify_provenance(checkout, build_dir, library)
    compiler = shlex.split(args.cc)
    command = build_adapter(source, checkout, build_dir, library, output, compiler)
    adapter = load_adapter(output)
    cases = verify_status_contract(adapter)

    report = {
        "provenance": provenance,
        "adapter": {
            "source": str(source),
            "source_sha256": _sha256(source),
            "output": str(output),
            "output_sha256": _sha256(output),
            "compile_command": command,
        },
        "status_contract": {
            "DONE": WF_RAW_DONE,
            "NEED_OUTPUT": WF_RAW_NEED_OUTPUT,
            "MALFORMED": WF_RAW_MALFORMED,
        },
        "correctness_cases": cases,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
