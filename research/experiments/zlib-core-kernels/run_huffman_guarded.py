#!/usr/bin/env python3
"""Build and balance the compiler-triggered Huffman bit-window experiment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import shutil
import statistics

import run_huffman as baseline


HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
SOURCE = HERE / "huffman_literals.wf"
SOURCE_SHA256 = "de44aca1c03a889834a56f15138c4ebb924feaedabece766633f45fd73974847"
SYMBOLS = baseline.SYMBOLS
PASSES = baseline.PASSES
SAMPLES = baseline.SAMPLES
VARIANTS = ("baseline", "guarded", "zng")
TAIL_COUNTS = (
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13,
    17, 23, 31, 32, 33, 47, 63, 64, 65, 95, 127, 128, 129, 257,
)
EXPERIMENT_SUCCESS_CASES = (
    "exact-bulk",
    "exact-bulk-tail",
    "guard-page-bulk",
    "guard-page-bulk-tail",
    "nonliteral-bulk-prefix",
    "nonliteral-tail-prefix",
)


def source_digest() -> str:
    return hashlib.sha256(SOURCE.read_bytes()).hexdigest()


def build_variant(name: str, guarded: bool) -> tuple[Path, Path]:
    target = BUILD / f"huffman-compiler-{name}"
    target.mkdir(parents=True, exist_ok=True)
    copied = target / SOURCE.name
    shutil.copyfile(SOURCE, copied)
    command = [str(baseline.PYTHON), str(baseline.DEMOC), str(copied)]
    if guarded:
        command.append("--experimental-guarded-bit-window")
    baseline.run(command)
    ir = copied.with_suffix(".ll")
    ir_text = ir.read_text(encoding="utf-8")
    marker = "EXPERIMENTAL guarded-bit-window certificate"
    if guarded != (marker in ir_text):
        raise SystemExit(f"compiler selection audit failed for {name}")
    obj = target / "kernel.o"
    exe = target / "bench"
    common = [
        str(baseline.CLANG),
        "--no-default-config",
        "-O3",
        "-DNDEBUG",
        "-isysroot",
        str(baseline.SDK),
    ]
    baseline.run(common + ["-c", str(ir), "-o", str(obj)])
    baseline.run(
        common
        + [
            "-DZLIBNG_NATIVE_API",
            "-I",
            str(baseline.ZNG_BUILD),
            "-I",
            str(baseline.ZNG_SOURCE),
            str(HERE / "huffman_bench.c"),
            str(HERE / "zng_huffman_kernel.c"),
            str(obj),
            "-o",
            str(exe),
        ]
    )
    return exe, ir


def verify_tails(executable: Path) -> None:
    for count in TAIL_COUNTS:
        completed = baseline.run([str(executable), "run", "wf", str(count), "1"])
        result = json.loads(completed.stdout)
        if result["symbols"] != count:
            raise SystemExit(f"tail count mismatch: expected {count}")


def verify_exact_bulk_cases(executable: Path) -> None:
    for case in EXPERIMENT_SUCCESS_CASES:
        baseline.run([str(executable), "contract", case])


def paired_summary(
    rows: list[dict[str, object]], denominator: str
) -> dict[str, object]:
    speeds = {
        (int(row["sample"]), str(row["variant"])): float(
            row["million_symbols_per_s"]
        )
        for row in rows
    }
    ratios = [
        speeds[(sample, "guarded")] / speeds[(sample, denominator)]
        for sample in range(SAMPLES)
    ]
    rng = random.Random(20260719)
    resamples = sorted(
        statistics.median(
            ratios[rng.randrange(len(ratios))] for _ in range(len(ratios))
        )
        for _ in range(200_000)
    )
    return {
        "denominator": denominator,
        "ratios": ratios,
        "median": statistics.median(ratios),
        "bootstrap_seed": 20260719,
        "bootstrap_resamples": 200_000,
        "bootstrap_95": [resamples[5_000], resamples[194_999]],
    }


def main() -> int:
    if source_digest() != SOURCE_SHA256:
        raise SystemExit("Whitefoot Huffman source changed before the experiment")
    baseline.verify_zng_checkout()
    baseline.verify_fixed_table_identity()
    baseline.run(
        [str(baseline.PYTHON), str(HERE / "test_guarded_bit_window.py")]
    )
    BUILD.mkdir(exist_ok=True)
    baseline_exe, _baseline_ir = build_variant("baseline", False)
    guarded_exe, guarded_ir = build_variant("guarded", True)
    for executable in (baseline_exe, guarded_exe):
        baseline.verify_contract(executable)
        verify_exact_bulk_cases(executable)
        verify_tails(executable)
    if source_digest() != SOURCE_SHA256:
        raise SystemExit("Whitefoot Huffman source changed during compilation")
    print(
        "compiler: certified guarded lowering; "
        f"{len(baseline.CONTRACT_SUCCESSES) + len(baseline.CONTRACT_TRAPS) + len(EXPERIMENT_SUCCESS_CASES)} "
        f"contracts passed twice; {len(TAIL_COUNTS)} tails passed twice"
    )

    executables = {"baseline": baseline_exe, "guarded": guarded_exe}
    rows: list[dict[str, object]] = []
    for sample in range(SAMPLES):
        order = VARIANTS[sample % 3 :] + VARIANTS[: sample % 3]
        for variant in order:
            executable = executables.get(variant, baseline_exe)
            selected = "zng" if variant == "zng" else "wf"
            completed = baseline.run(
                [str(executable), "run", selected, str(SYMBOLS), str(PASSES)]
            )
            row = json.loads(completed.stdout)
            row["variant"] = variant
            row["sample"] = sample
            row["million_symbols_per_s"] = (
                row["symbols"] * row["passes"] / row["elapsed_ns"] * 1000.0
            )
            rows.append(row)
    medians = {
        variant: statistics.median(
            row["million_symbols_per_s"]
            for row in rows
            if row["variant"] == variant
        )
        for variant in VARIANTS
    }
    paired = {
        denominator: paired_summary(rows, denominator)
        for denominator in ("baseline", "zng")
    }
    print(
        f"baseline={medians['baseline']:.3f} Msyms/s "
        f"guarded={medians['guarded']:.3f} Msyms/s "
        f"zng={medians['zng']:.3f} Msyms/s "
        f"guarded/zng={medians['guarded'] / medians['zng']:.3f} "
        f"guarded/baseline={medians['guarded'] / medians['baseline']:.3f}"
    )
    print(
        "paired median guarded/baseline="
        f"{paired['baseline']['median']:.3f} "
        f"95%={paired['baseline']['bootstrap_95']} "
        "guarded/zng="
        f"{paired['zng']['median']:.3f} "
        f"95%={paired['zng']['bootstrap_95']}"
    )
    (HERE / "huffman-guarded-results.json").write_text(
        json.dumps(
            {
                "schema": "whitefoot.zlib-core.huffman-guarded-compiler.v1",
                "source_sha256": SOURCE_SHA256,
                "guarded_ir": str(guarded_ir.relative_to(HERE)),
                "symbols": SYMBOLS,
                "passes": PASSES,
                "samples": SAMPLES,
                "zlib_ng_commit": baseline.ZNG_COMMIT,
                "tail_counts": TAIL_COUNTS,
                "paired": paired,
                "rows": rows,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
