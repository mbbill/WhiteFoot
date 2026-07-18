#!/usr/bin/env python3
"""Deterministic PROOF-2 base64 correctness and checked-boundary gate."""

from __future__ import annotations

import base64
import random
import subprocess
import sys
import tempfile
from pathlib import Path


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "prototype/democ"))
import democ  # noqa: E402


def build(build_dir: Path, name: str, *, facts: bool) -> tuple[Path, list[dict]]:
    report: list[dict] = []
    ir = democ.compile_program(
        (HERE / "b64.xl").read_text(), alias=facts, proof_report=report
    )
    ll = build_dir / f"{name}.ll"
    exe = build_dir / name
    ll.write_text(ir)
    subprocess.run(
        ["/usr/bin/clang", "-O3", str(ll), str(HERE / "driver.c"), "-o", str(exe)],
        check=True,
        capture_output=True,
    )
    return exe, report


def corpus() -> list[bytes]:
    rng = random.Random(0x58364C414E47)
    sizes = set(range(0, 65))
    for k in range(1, 25):
        for delta in (-2, -1, 0, 1, 2):
            sizes.add(max(0, 3 * k + delta))
    while len(sizes) < 139:
        sizes.add(rng.randrange(0, 4097))
    return [bytes(rng.randrange(256) for _ in range(n)) for n in sorted(sizes)[:139]]


def verify_differential(build_dir: Path, facts: Path, nofacts: Path) -> None:
    input_path = build_dir / "input.bin"
    for ordinal, data in enumerate(corpus()):
        input_path.write_bytes(data)
        expected = base64.b64encode(data) + b"\n"
        got_facts = subprocess.check_output([str(facts), str(input_path)])
        got_nofacts = subprocess.check_output([str(nofacts), str(input_path)])
        if got_facts != expected or got_nofacts != expected:
            raise AssertionError(
                f"base64 differential failed at case {ordinal}, size {len(data)}"
            )


def verify_foreign_boundary(build_dir: Path) -> None:
    """A direct C call cannot bypass the retained callee-entry requirement."""
    report: list[dict] = []
    ir = democ.compile_program((HERE / "b64.xl").read_text(), proof_report=report)
    if len(report) != 27 or sum(s["proof"] == "output-capacity-lockstep" for s in report) != 12:
        raise AssertionError("PROOF-2 site accounting changed")
    encode = ir[ir.index("define i64 @encode"):]
    entry_guard = encode.find("  br i1")
    first_byte_store = encode.find("  store i8")
    if entry_guard < 0 or first_byte_store < 0 or entry_guard >= first_byte_store:
        raise AssertionError("requires guard no longer dominates the first body byte store")

    ll = build_dir / "boundary.ll"
    c = build_dir / "boundary.c"
    exe = build_dir / "boundary"
    ll.write_text(ir)
    c.write_text(
        """#include <stdint.h>
typedef struct { uint8_t *p; int64_t n; } Buf;
extern uint64_t encode(Buf out, Buf src);
int main(int argc, char **argv) {
  uint8_t src_data[3] = {97, 98, 99};
  uint8_t out_data[4] = {0, 0, 0, 0};
  Buf src = {src_data, 3};
  Buf out = {out_data, argc > 1 ? 3 : 4};
  uint64_t n = encode(out, src);
  return n == 4 && out_data[0] == 89 && out_data[1] == 87 &&
         out_data[2] == 74 && out_data[3] == 106 ? 0 : 7;
}
"""
    )
    subprocess.run(
        ["/usr/bin/clang", "-O3", str(ll), str(c), "-o", str(exe)],
        check=True,
        capture_output=True,
    )
    subprocess.run([str(exe)], check=True, capture_output=True)
    undersized = subprocess.run([str(exe), "undersized"], capture_output=True)
    if undersized.returncode == 0:
        raise AssertionError("direct C call bypassed the checked output-capacity boundary")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="whitefoot-base64-verify-") as temporary:
        build_dir = Path(temporary)
        facts, facts_report = build(build_dir, "facts", facts=True)
        nofacts, nofacts_report = build(build_dir, "nofacts", facts=False)
        if (sum(s["status"] == "proved" for s in facts_report),
                sum(s["status"] == "retained" for s in facts_report)) != (27, 0):
            raise AssertionError("facts proof partition changed")
        if (sum(s["status"] == "proved" for s in nofacts_report),
                sum(s["status"] == "retained" for s in nofacts_report)) != (0, 27):
            raise AssertionError("facts-off proof partition changed")
        verify_differential(build_dir, facts, nofacts)
        verify_foreign_boundary(build_dir)
    print("base64 PROOF-2: 139/139 facts/nofacts/reference differentials; checked C boundary OK")


if __name__ == "__main__":
    main()
