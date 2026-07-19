#!/usr/bin/env python3
"""Build and exercise the pinned stock-zlib corpus-preparation adapter.

This module is deliberately outside the measurement path.  It verifies a
pristine zlib 1.3.2 checkout and its Release shared build, compiles the small
public-API adapter in ``stock_zlib.c``, and provides deterministic raw-DEFLATE
compression plus full-capacity inflate cross-checks for corpus construction.
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


EXPECTED_ZLIB_VERSION = "1.3.2"
EXPECTED_ZLIB_TAG = "v1.3.2"
EXPECTED_ZLIB_COMMIT = "da607da739fa6047df13e66a2af6b8bec7c2a498"
EXPECTED_ZLIB_TREE = "79b5a06f88838dd54f90f821e8650254abfedb7e"
DEFAULT_RESEARCH_ROOT = Path("/private/tmp/whitefoot-zlib-research.wpK9iq")

STOCK_DONE = 0
STOCK_NEED_OUTPUT = 1
STOCK_MALFORMED = 2
STOCK_ERROR = 3

Z_DEFAULT_STRATEGY = 0
Z_FILTERED = 1
Z_HUFFMAN_ONLY = 2
Z_RLE = 3
Z_FIXED = 4

LEVELS = (0, 1, 6, 9)
STRATEGY_NAMES = {
    Z_DEFAULT_STRATEGY: "Z_DEFAULT_STRATEGY",
    Z_FILTERED: "Z_FILTERED",
    Z_HUFFMAN_ONLY: "Z_HUFFMAN_ONLY",
    Z_RLE: "Z_RLE",
    Z_FIXED: "Z_FIXED",
}
STRATEGIES = tuple(STRATEGY_NAMES)

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


def find_library(build_dir: Path) -> Path:
    names = (
        "libz.1.3.2.dylib",
        "libz.so.1.3.2",
        "zlib1.dll",
    )
    for name in names:
        candidate = build_dir / name
        if candidate.is_file():
            return candidate
    raise RuntimeError(f"no zlib {EXPECTED_ZLIB_VERSION} shared library in {build_dir}")


def verify_provenance(checkout: Path, build_dir: Path, library: Path) -> dict[str, Any]:
    checkout = checkout.resolve()
    build_dir = build_dir.resolve()
    library = _require_file(library.resolve(), "stock-zlib shared library")
    source_header = _require_file(checkout / "zlib.h", "stock-zlib public header")
    generated_header = _require_file(build_dir / "zconf.h", "generated zconf header")
    cache_path = _require_file(build_dir / "CMakeCache.txt", "stock-zlib CMake cache")

    commit = _run_text(["git", "-C", str(checkout), "rev-parse", "HEAD"])
    tree = _run_text(["git", "-C", str(checkout), "rev-parse", "HEAD^{tree}"])
    tag_commit = _run_text(
        ["git", "-C", str(checkout), "rev-parse", f"refs/tags/{EXPECTED_ZLIB_TAG}^{{commit}}"]
    )
    tracked_status = _run_text(
        ["git", "-C", str(checkout), "status", "--porcelain", "--untracked-files=no"]
    )

    if commit != EXPECTED_ZLIB_COMMIT:
        raise RuntimeError(f"stock-zlib commit is {commit}, expected {EXPECTED_ZLIB_COMMIT}")
    if tree != EXPECTED_ZLIB_TREE:
        raise RuntimeError(f"stock-zlib tree is {tree}, expected {EXPECTED_ZLIB_TREE}")
    if tag_commit != EXPECTED_ZLIB_COMMIT:
        raise RuntimeError(
            f"stock-zlib tag {EXPECTED_ZLIB_TAG} does not resolve to the pinned commit"
        )
    if tracked_status:
        raise RuntimeError("stock-zlib checkout has tracked modifications")

    header_text = source_header.read_text(encoding="utf-8")
    version_match = re.search(
        r'^#define ZLIB_VERSION "([^"]+)"$', header_text, flags=re.MULTILINE
    )
    if version_match is None or version_match.group(1) != EXPECTED_ZLIB_VERSION:
        actual = version_match.group(1) if version_match is not None else "missing"
        raise RuntimeError(
            f"stock-zlib header version is {actual}, expected {EXPECTED_ZLIB_VERSION}"
        )

    cache_values = _cmake_cache_values(cache_path)
    expected_cache = {
        "BUILD_SHARED_LIBS": "ON",
        "CMAKE_BUILD_TYPE": "Release",
        "ZLIB_BUILD_SHARED": "ON",
    }
    mismatches = {
        key: {"actual": cache_values.get(key), "expected": expected}
        for key, expected in expected_cache.items()
        if cache_values.get(key) != expected
    }
    if mismatches:
        raise RuntimeError(f"stock-zlib build configuration mismatch: {mismatches}")
    cache_home_text = cache_values.get("CMAKE_HOME_DIRECTORY")
    if cache_home_text is None or Path(cache_home_text).resolve() != checkout:
        raise RuntimeError(
            "stock-zlib build directory was not configured from the pinned checkout: "
            f"{cache_home_text}"
        )

    return {
        "version": EXPECTED_ZLIB_VERSION,
        "tag": EXPECTED_ZLIB_TAG,
        "commit": commit,
        "tree": tree,
        "checkout": str(checkout),
        "checkout_tracked_clean": True,
        "build_dir": str(build_dir),
        "build_source_checkout": str(Path(cache_home_text).resolve()),
        "build_configuration": expected_cache,
        "source_header": str(source_header),
        "source_header_sha256": _sha256(source_header),
        "generated_header": str(generated_header),
        "generated_header_sha256": _sha256(generated_header),
        "cmake_cache_sha256": _sha256(cache_path),
        "shared_library": str(library),
        "shared_library_sha256": _sha256(library),
    }


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
        raise RuntimeError("the stock-zlib helper currently requires a Unix-style C compiler")
    if not compiler:
        raise RuntimeError("empty C compiler command")

    output.parent.mkdir(parents=True, exist_ok=True)
    link_mode = "-dynamiclib" if sys.platform == "darwin" else "-shared"
    command = [
        *compiler,
        "-std=c11",
        "-O2",
        "-fPIC",
        "-fvisibility=hidden",
        "-Wall",
        "-Wextra",
        "-Wpedantic",
        "-Wconversion",
        "-Wsign-conversion",
        "-Wshadow",
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
    _require_file(output, "compiled stock-zlib adapter")
    return command


def load_adapter(path: Path) -> ctypes.CDLL:
    adapter = ctypes.CDLL(str(path.resolve()))

    adapter.wf_stock_header_version.argtypes = []
    adapter.wf_stock_header_version.restype = ctypes.c_char_p
    adapter.wf_stock_runtime_version.argtypes = []
    adapter.wf_stock_runtime_version.restype = ctypes.c_char_p
    for symbol in (adapter.wf_stock_header_version, adapter.wf_stock_runtime_version):
        version_bytes = symbol()
        version = version_bytes.decode("ascii") if version_bytes is not None else "missing"
        if version != EXPECTED_ZLIB_VERSION:
            raise RuntimeError(
                f"loaded adapter reports zlib {version}, expected {EXPECTED_ZLIB_VERSION}"
            )

    adapter.wf_stock_raw_deflate_bound.argtypes = [
        ctypes.c_size_t,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    adapter.wf_stock_raw_deflate_bound.restype = ctypes.c_int32
    adapter.wf_stock_raw_deflate_once.argtypes = [
        _U8_POINTER,
        ctypes.c_size_t,
        _U8_POINTER,
        ctypes.c_size_t,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    adapter.wf_stock_raw_deflate_once.restype = ctypes.c_int32
    adapter.wf_stock_raw_inflate_full.argtypes = [
        _U8_POINTER,
        ctypes.c_size_t,
        _U8_POINTER,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    adapter.wf_stock_raw_inflate_full.restype = ctypes.c_int32
    return adapter


def _source_storage(data: bytes) -> tuple[Any, Any]:
    storage = (ctypes.c_uint8 * len(data)).from_buffer_copy(data) if data else None
    pointer = ctypes.cast(storage, _U8_POINTER) if storage is not None else None
    return storage, pointer


def _output_storage(capacity: int) -> tuple[Any, Any]:
    storage = (ctypes.c_uint8 * capacity)() if capacity else None
    pointer = ctypes.cast(storage, _U8_POINTER) if storage is not None else None
    return storage, pointer


def compress_raw(adapter: ctypes.CDLL, data: bytes, level: int, strategy: int) -> bytes:
    """Return a deterministic one-shot raw-DEFLATE stream for ``data``."""

    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    if level not in LEVELS:
        raise ValueError(f"level must be one of {LEVELS}")
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy must be one of {STRATEGIES}")

    bound = ctypes.c_size_t(0)
    bound_status = int(
        adapter.wf_stock_raw_deflate_bound(
            len(data), level, strategy, ctypes.byref(bound)
        )
    )
    if bound_status != STOCK_DONE:
        raise RuntimeError(f"stock-zlib deflateBound adapter failed with {bound_status}")

    source_storage, source_pointer = _source_storage(data)
    output_storage, output_pointer = _output_storage(bound.value)
    produced = ctypes.c_size_t(0)
    status = int(
        adapter.wf_stock_raw_deflate_once(
            output_pointer,
            bound.value,
            source_pointer,
            len(data),
            level,
            strategy,
            ctypes.byref(produced),
        )
    )
    del source_storage
    if status != STOCK_DONE:
        raise RuntimeError(f"stock-zlib raw deflate failed with adapter status {status}")
    if produced.value > bound.value or output_storage is None:
        raise RuntimeError("stock-zlib raw deflate reported an invalid output size")
    return bytes(output_storage[: produced.value])


def inflate_full(
    adapter: ctypes.CDLL, compressed: bytes, capacity: int
) -> tuple[int, bytes]:
    """Inflate once with ``capacity`` bytes and return adapter status and output."""

    if not isinstance(compressed, bytes):
        raise TypeError("compressed must be bytes")
    if capacity < 0:
        raise ValueError("capacity must be nonnegative")

    source_storage, source_pointer = _source_storage(compressed)
    output_storage, output_pointer = _output_storage(capacity)
    produced = ctypes.c_size_t(0)
    status = int(
        adapter.wf_stock_raw_inflate_full(
            output_pointer,
            capacity,
            source_pointer,
            len(compressed),
            ctypes.byref(produced),
        )
    )
    del source_storage
    if status == STOCK_ERROR:
        raise RuntimeError("stock-zlib raw inflate reported an adapter error")
    if status not in (STOCK_DONE, STOCK_NEED_OUTPUT, STOCK_MALFORMED):
        raise RuntimeError(f"stock-zlib raw inflate returned unknown status {status}")
    if produced.value > capacity:
        raise RuntimeError("stock-zlib raw inflate reported output beyond capacity")
    output = bytes(output_storage[: produced.value]) if output_storage is not None else b""
    return status, output


def verify_roundtrips(adapter: ctypes.CDLL) -> list[dict[str, Any]]:
    payloads = (
        b"",
        b"Whitefoot raw DEFLATE corpus preparation\n",
        bytes(range(256)) * 3,
        (b"overlap-pattern-" * 257) + bytes(range(64)),
    )
    results: list[dict[str, Any]] = []
    for level in LEVELS:
        for strategy in STRATEGIES:
            stream_hash = hashlib.sha256()
            compressed_size = 0
            for payload in payloads:
                first = compress_raw(adapter, payload, level, strategy)
                second = compress_raw(adapter, payload, level, strategy)
                if first != second:
                    raise RuntimeError(
                        f"nondeterministic output at level {level}, "
                        f"strategy {STRATEGY_NAMES[strategy]}"
                    )
                status, decoded = inflate_full(adapter, first, len(payload))
                if status != STOCK_DONE or decoded != payload:
                    raise RuntimeError(
                        f"roundtrip failed at level {level}, "
                        f"strategy {STRATEGY_NAMES[strategy]}"
                    )
                stream_hash.update(len(first).to_bytes(8, "little"))
                stream_hash.update(first)
                compressed_size += len(first)
            results.append(
                {
                    "level": level,
                    "strategy": STRATEGY_NAMES[strategy],
                    "payload_count": len(payloads),
                    "compressed_bytes": compressed_size,
                    "stream_set_sha256": stream_hash.hexdigest(),
                }
            )
    return results


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkout",
        type=Path,
        default=DEFAULT_RESEARCH_ROOT / "zlib",
        help="pinned stock-zlib source checkout",
    )
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=DEFAULT_RESEARCH_ROOT / "build-zlib",
        help="pinned stock-zlib Release shared build",
    )
    parser.add_argument(
        "--library",
        type=Path,
        help="exact stock-zlib shared library (normally discovered in --build-dir)",
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
    source = Path(__file__).with_name("stock_zlib.c").resolve()
    if args.output is None:
        output_dir = Path(tempfile.mkdtemp(prefix="whitefoot-stock-zlib-"))
        output = output_dir / f"libwhitefoot_stock_zlib{_adapter_suffix()}"
    else:
        output = args.output.resolve()

    provenance = verify_provenance(checkout, build_dir, library)
    compiler = shlex.split(args.cc)
    command = build_adapter(source, checkout, build_dir, library, output, compiler)
    adapter = load_adapter(output)
    roundtrips = verify_roundtrips(adapter)

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
            "DONE": STOCK_DONE,
            "NEED_OUTPUT": STOCK_NEED_OUTPUT,
            "MALFORMED": STOCK_MALFORMED,
            "ERROR": STOCK_ERROR,
        },
        "levels": list(LEVELS),
        "strategies": [STRATEGY_NAMES[strategy] for strategy in STRATEGIES],
        "roundtrips": roundtrips,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
