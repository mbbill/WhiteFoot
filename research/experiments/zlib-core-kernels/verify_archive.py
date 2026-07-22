#!/usr/bin/env python3
"""Verify the durable zlib core-kernel archive without rebuilding native code."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE_HASHES = {
    "match_copy.wf": "cd4962c29f6725141d2c555a22986c585f1da8e46274cd776bfee48e270239d7",
    "huffman_literals.wf": "de44aca1c03a889834a56f15138c4ebb924feaedabece766633f45fd73974847",
}
RESULT_SCHEMAS = {
    "results.json": "whitefoot.zlib-core.match-copy.v1",
    "huffman-results.json": "whitefoot.zlib-core.huffman-literals.v1",
    "periodic-compiler-results.json": "whitefoot.zlib-core.periodic-compiler.v1",
    "huffman-guarded-results.json": "whitefoot.zlib-core.huffman-guarded-compiler.v1",
    "manual-lowering-ceiling/periodic-results.json": "whitefoot.zlib-core.match-copy.v1",
    "manual-lowering-ceiling/huffman-results.json": "whitefoot.zlib-core.huffman-literals.v1",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest() -> int:
    checked = 0
    for line in (HERE / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        actual = digest(HERE / relative)
        if actual != expected:
            raise SystemExit(
                f"SHA-256 mismatch for {relative}: expected {expected}, got {actual}"
            )
        checked += 1
    return checked


def main() -> int:
    for relative, expected in SOURCE_HASHES.items():
        actual = digest(HERE / relative)
        if actual != expected:
            raise SystemExit(
                f"source identity mismatch for {relative}: expected {expected}, got {actual}"
            )

    for relative, expected in RESULT_SCHEMAS.items():
        data = json.loads((HERE / relative).read_text(encoding="utf-8"))
        if data.get("schema") != expected:
            raise SystemExit(
                f"schema mismatch for {relative}: expected {expected}, got {data.get('schema')}"
            )

    for relative in (
        "bounds-elision-ceiling/match-results.json",
        "bounds-elision-ceiling/huffman-results.json",
    ):
        json.loads((HERE / relative).read_text(encoding="utf-8"))

    markers = {
        "assembly/match-ordinary.aarch64.asm.txt": ("ldrb", "strb"),
        "assembly/match-periodic-helper.aarch64.asm.txt": ("tbl.16b", "str\tq"),
        "assembly/huffman-guarded.aarch64.asm.txt": ("ldr\tx", "ldrh"),
        "compiler-prototypes/periodic/democ.patch": (
            "periodic-copy-experiment",
            "__wf_periodic_copy_u8_repeated",
        ),
        "compiler-prototypes/guarded-bit-window/democ.patch": (
            "experimental-guarded-bit-window",
            "EXPERIMENTAL guarded-bit-window certificate",
        ),
    }
    for relative, required in markers.items():
        text = (HERE / relative).read_text(encoding="utf-8")
        for marker in required:
            if marker not in text:
                raise SystemExit(f"missing marker {marker!r} in {relative}")

    checked = verify_manifest()
    print(
        "zlib core-kernel archive: "
        f"{checked} manifest files, 2 pinned sources, and 8 JSON results verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
