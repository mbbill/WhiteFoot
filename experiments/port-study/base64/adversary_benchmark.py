#!/usr/bin/env python3
"""Build and run isolated, balanced base64 adversary blocks."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import platform
import random
import statistics
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "prototype/democ"))
import democ  # noqa: E402


VARIANTS = (
    "whitefoot-proof",
    "rust-naive",
    "rust-assert",
    "rust-chunks-full",
    "rust-unsafe",
)
ORDER_SEED = 0xB64


def command_output(command: list[str]) -> str:
    return subprocess.check_output(command, text=True).rstrip()


def build(build_dir: Path) -> tuple[Path, dict[str, int]]:
    proof_report: list[dict] = []
    llvm_ir = democ.compile_program(
        (HERE / "b64.wf").read_text(), proof_report=proof_report
    )
    proof_summary = {
        "proved": sum(site["status"] == "proved" for site in proof_report),
        "retained": sum(site["status"] == "retained" for site in proof_report),
        "output_capacity_lockstep": sum(
            site["proof"] == "output-capacity-lockstep" for site in proof_report
        ),
    }
    if proof_summary != {
        "proved": 27,
        "retained": 0,
        "output_capacity_lockstep": 12,
    }:
        raise RuntimeError(f"whitefoot PROOF-2 accounting changed: {proof_summary}")
    ll = build_dir / "whitefoot-proof.ll"
    obj = build_dir / "whitefoot-proof.o"
    executable = build_dir / "paired-adversary"
    ll.write_text(llvm_ir)
    subprocess.run(
        ["/usr/bin/clang", "-O3", "-mcpu=native", "-c", str(ll), "-o", str(obj)],
        check=True,
    )
    subprocess.run(
        [
            "rustc",
            "--edition=2024",
            "-C",
            "opt-level=3",
            "-C",
            "target-cpu=native",
            "-C",
            "codegen-units=1",
            "-C",
            "panic=abort",
            str(HERE / "paired_adversary.rs"),
            "-C",
            f"link-arg={obj}",
            "-o",
            str(executable),
        ],
        check=True,
    )
    return executable, proof_summary


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def bootstrap_median_interval(values: list[float], seed: int) -> tuple[float, float]:
    rng = random.Random(seed)
    medians = []
    for _ in range(10_000):
        sample = [values[rng.randrange(len(values))] for _ in values]
        medians.append(statistics.median(sample))
    return percentile(medians, 0.025), percentile(medians, 0.975)


def parse_samples(output: str) -> list[dict[str, str]]:
    lines = output.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("sample,"))
    return list(csv.DictReader(io.StringIO("\n".join(lines[start:]))))


def run_blocks(executable: Path, size: int, cycles: int) -> list[dict[str, str]]:
    rng = random.Random(ORDER_SEED)
    rows: list[dict[str, str]] = []
    block = 0
    for cycle in range(cycles):
        order = list(range(10))
        rng.shuffle(order)
        for row_index in order:
            output = command_output([str(executable), str(size), str(row_index)])
            block_rows = parse_samples(output)
            if len(block_rows) != len(VARIANTS):
                raise RuntimeError(f"incomplete process block {block}")
            for row in block_rows:
                row["sample"] = str(len(rows) + int(row["sample"]))
                row["block"] = str(block)
                row["cycle"] = str(cycle)
                row["row"] = str(row_index)
            rows.extend(block_rows)
            block += 1
            print(f"completed isolated block {block}/{cycles * 10}", flush=True)
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize(rows: list[dict[str, str]], size: int) -> None:
    by_variant: dict[str, list[float]] = defaultdict(list)
    by_block: dict[int, dict[str, float]] = defaultdict(dict)
    positions: dict[str, list[int]] = defaultdict(list)
    block_positions: dict[int, dict[str, int]] = defaultdict(dict)
    block_cycles: dict[int, int] = {}
    for row in rows:
        variant = row["variant"]
        nanos = float(row["nanos"])
        block = int(row["block"])
        by_variant[variant].append(nanos)
        by_block[block][variant] = nanos
        positions[variant].append(int(row["position"]))
        block_positions[block][variant] = int(row["position"])
        block_cycles[block] = int(row["cycle"])

    if set(by_variant) != set(VARIANTS):
        raise RuntimeError(f"unexpected variants: {sorted(by_variant)}")
    if any(len(block) != len(VARIANTS) for block in by_block.values()):
        raise RuntimeError("incomplete balanced block")
    repeats_per_position = len(rows) // len(VARIANTS) ** 2
    expected_positions = [
        position
        for position in range(len(VARIANTS))
        for _ in range(repeats_per_position)
    ]
    for variant in VARIANTS:
        if sorted(positions[variant]) != expected_positions:
            raise RuntimeError(f"unbalanced positions for {variant}")

    whitefoot = "whitefoot-proof"
    print(
        "\n| variant | median | MAD/median | throughput | "
        "XL/variant process-block ratio (row-bootstrap 95% interval) |"
    )
    print("|---|---:|---:|---:|---:|")
    for index, variant in enumerate(VARIANTS):
        times = by_variant[variant]
        median_ns = statistics.median(times)
        mad_ns = statistics.median(abs(value - median_ns) for value in times)
        if variant == whitefoot:
            ratio_text = "1.000"
        else:
            # Same byte count: XL throughput / variant throughput = variant time / XL time.
            ratios = [block[variant] / block[whitefoot] for block in by_block.values()]
            ratio = statistics.median(ratios)
            low, high = bootstrap_median_interval(ratios, 0xB64 + index)
            ratio_text = f"{ratio:.3f} ({low:.3f}..{high:.3f})"
        print(
            f"| {variant} | {median_ns / 1e6:.3f} ms | "
            f"{100.0 * mad_ns / median_ns:.2f}% | {size / median_ns:.3f} GB/s | "
            f"{ratio_text} |"
        )

    block_ids = list(by_block)
    chunks_ratios = [
        by_block[block]["rust-chunks-full"] / by_block[block][whitefoot]
        for block in block_ids
    ]
    ratio = statistics.median(chunks_ratios)
    low, high = bootstrap_median_interval(chunks_ratios, 0xB640)
    if low >= 0.98 and high <= 1.02:
        verdict = "practical parity in this run (the row-bootstrap interval is inside ±2%)"
    elif high < 0.98:
        verdict = "Rust lead above the 2% equivalence margin"
    elif low > 1.02:
        verdict = "whitefoot lead above the 2% equivalence margin"
    else:
        verdict = "inconclusive against the predeclared ±2% equivalence margin"
    cycle_ratios = {
        cycle: statistics.median(
            value
            for block, value in zip(block_ids, chunks_ratios, strict=True)
            if block_cycles[block] == cycle
        )
        for cycle in sorted(set(block_cycles.values()))
    }
    xl_first = statistics.median(
        value
        for block, value in zip(block_ids, chunks_ratios, strict=True)
        if block_positions[block][whitefoot] < block_positions[block]["rust-chunks-full"]
    )
    rust_first = statistics.median(
        value
        for block, value in zip(block_ids, chunks_ratios, strict=True)
        if block_positions[block]["rust-chunks-full"] < block_positions[block][whitefoot]
    )
    print(
        f"\nPrimary comparison: XL/Rust-chunks = {ratio:.3f} "
        f"({low:.3f}..{high:.3f} row-bootstrap interval); {verdict}."
    )
    print(
        "Cycle medians: "
        + ", ".join(f"{cycle}={value:.3f}" for cycle, value in cycle_ratios.items())
    )
    print(f"Order sensitivity: XL-first={xl_first:.3f}, Rust-first={rust_first:.3f}.")


def write_evidence(
    raw_path: Path,
    rows: list[dict[str, str]],
    *,
    size: int,
    cycles: int,
    proof_summary: dict[str, int],
    git_commit: str,
    git_status: str,
    host: str,
    rustc_version: str,
    clang_version: str,
) -> Path:
    fields = (
        "sample",
        "block",
        "cycle",
        "row",
        "position",
        "variant",
        "nanos",
        "len",
        "checksum",
    )
    raw_path.write_text(
        ",".join(fields)
        + "\n"
        + "\n".join(",".join(row[field] for field in fields) for row in rows)
        + "\n"
    )
    sources = (
        HERE / "paired_adversary.rs",
        HERE / "adversary_benchmark.py",
        HERE / "b64.wf",
        ROOT / "prototype/democ/democ.py",
    )
    metadata = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "git_commit": git_commit,
        "git_status": git_status.splitlines(),
        "host": host,
        "toolchains": {"rustc": rustc_version, "clang": clang_version},
        "compile_flags": {
            "whitefoot_ir": "democ.compile_program(default facts; asserted 27 proved, 0 retained)",
            "clang": ["-O3", "-mcpu=native", "-c"],
            "rustc": [
                "--edition=2024",
                "-C opt-level=3",
                "-C target-cpu=native",
                "-C codegen-units=1",
                "-C panic=abort",
            ],
        },
        "proof_summary": proof_summary,
        "protocol": {
            "bytes": size,
            "cycles": cycles,
            "isolated_process_blocks": cycles * 10,
            "samples_per_variant": cycles * 10,
            "order_seed": ORDER_SEED,
            "bootstrap_resamples": 10_000,
            "practical_equivalence_margin": 0.02,
        },
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256_file(path) for path in sources
        },
        "raw_csv": raw_path.name,
        "raw_csv_sha256": sha256_file(raw_path),
    }
    metadata_path = raw_path.with_suffix(".metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return metadata_path


def main() -> None:
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 384_000_000
    cycles = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    raw_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    if len(sys.argv) > 4:
        raise SystemExit(f"usage: {sys.argv[0]} [BYTES] [CYCLES] [RAW_CSV]")
    if size <= 0 or cycles <= 0:
        raise SystemExit("BYTES and CYCLES must be positive")

    git_commit = command_output(["git", "rev-parse", "HEAD"])
    git_status = command_output(["git", "status", "--short"])
    host = f"{platform.platform()}; {platform.machine()}"
    rustc_version = command_output(["rustc", "-vV"]).replace(chr(10), "; ")
    clang_version = command_output(["/usr/bin/clang", "--version"]).splitlines()[0]
    print(f"git: {git_commit}")
    print(f"host: {host}")
    print(f"rustc: {rustc_version}")
    print(f"clang: {clang_version}")
    print(f"protocol: {size} bytes, {cycles * 10} isolated Williams-row processes")

    with tempfile.TemporaryDirectory(prefix="whitefoot-base64-adversary-") as temporary:
        executable, proof_summary = build(Path(temporary))
        rows = run_blocks(executable, size, cycles)
    if raw_path is not None:
        metadata_path = write_evidence(
            raw_path,
            rows,
            size=size,
            cycles=cycles,
            proof_summary=proof_summary,
            git_commit=git_commit,
            git_status=git_status,
            host=host,
            rustc_version=rustc_version,
            clang_version=clang_version,
        )
        print(f"raw samples: {raw_path}")
        print(f"metadata: {metadata_path}")
    summarize(rows, size)


if __name__ == "__main__":
    main()
