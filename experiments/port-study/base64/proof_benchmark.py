#!/usr/bin/env python3
"""Rebuild and median-benchmark base64 no-facts, PROOF-2, and ceiling variants."""

from __future__ import annotations

import re
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "prototype/democ"))
import democ  # noqa: E402


RESULT = re.compile(r"encode: ([0-9.]+) GB/s \(([0-9.]+) ms/pass")
VARIANTS = (
    ("no-facts", {"alias": False}),
    ("PROOF-2", {}),
    ("ceiling", {"elide_bounds": True}),
)


def build(build_dir: Path, name: str, options: dict[str, bool]) -> Path:
    source = (HERE / "b64.xl").read_text()
    ir = democ.compile_program(source, **options)
    ll = build_dir / f"{name}.ll"
    exe = build_dir / name
    ll.write_text(ir)
    subprocess.run(
        ["/usr/bin/clang", "-O3", str(ll), str(HERE / "bench.c"), "-o", str(exe)],
        check=True,
    )
    return exe


def measure(executable: Path, size: int, samples: int) -> tuple[float, float]:
    throughput, milliseconds = [], []
    for _ in range(samples):
        output = subprocess.check_output([str(executable), str(size)], text=True)
        match = RESULT.search(output)
        if not match:
            raise RuntimeError(output)
        throughput.append(float(match.group(1)))
        milliseconds.append(float(match.group(2)))
    return statistics.median(throughput), statistics.median(milliseconds)


def main() -> None:
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 384_000_000
    samples = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    if len(sys.argv) > 3:
        raise SystemExit(f"usage: {sys.argv[0]} [BYTES] [SAMPLES]")
    print("| variant | throughput | time/pass |")
    print("|---|---:|---:|")
    with tempfile.TemporaryDirectory(prefix="whitefoot-base64-proof-") as temporary:
        build_dir = Path(temporary)
        for name, options in VARIANTS:
            executable = build(build_dir, name, options)
            gbps, ms = measure(executable, size, samples)
            print(f"| {name} | {gbps:.3f} GB/s | {ms:.1f} ms |")


if __name__ == "__main__":
    main()
