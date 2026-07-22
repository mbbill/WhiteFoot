#!/usr/bin/env python3
"""Build and measure the Whitefoot DEFLATE match-copy kernel."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUILD = HERE / "build"
PYTHON = Path(
    "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/"
    "Python3.framework/Versions/3.9/bin/python3.9"
)
CLANG = Path(
    "/Applications/Xcode.app/Contents/Developer/Toolchains/"
    "XcodeDefault.xctoolchain/usr/bin/clang"
)
SDK = Path(
    "/Applications/Xcode.app/Contents/Developer/Platforms/"
    "MacOSX.platform/Developer/SDKs/MacOSX.sdk"
)
DEMOC = ROOT / "prototype" / "democ" / "democ.py"
ZNG_ROOT = Path(
    os.environ.get(
        "WHITEFOOT_ZNG_ROOT", "/private/tmp/whitefoot-zlib-research.wpK9iq"
    )
)
ZNG_BUILD = ZNG_ROOT / "build-zng-dispatch"
ZNG_SOURCE = ZNG_ROOT / "zlib-ng"
ZNG_COMMIT = "12731092979c6d07f42da27da673a9f6c7b13586"
SOURCE = HERE / "match_copy.wf"
CASES = (
    (1, 3),
    (1, 258),
    (2, 258),
    (3, 8),
    (3, 258),
    (4, 258),
    (8, 32),
    (8, 258),
    (16, 258),
    (31, 64),
    (31, 258),
    (64, 258),
    (257, 258),
    (32768, 258),
)
VARIANTS = ("facts", "nofacts", "zng")
OUTPUT_BYTES = 32 * 1024 * 1024
PASSES = 4
SAMPLES = 9
CONTRACT_SUCCESSES = ("zero-repeats", "exact-capacity")
CONTRACT_TRAPS = (
    "length-below",
    "length-above",
    "distance-zero",
    "distance-above",
    "distance-history",
    "product-overflow",
    "sum-overflow",
    "capacity-short",
)


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def verify_contract(executable: Path) -> None:
    for case in CONTRACT_SUCCESSES:
        completed = subprocess.run(
            [str(executable), "contract", case],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode != 0:
            raise SystemExit(
                f"match-copy contract success case {case!r} returned "
                f"{completed.returncode}: {completed.stderr.strip()}"
            )
    for case in CONTRACT_TRAPS:
        completed = subprocess.run(
            [str(executable), "contract", case],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode >= 0:
            raise SystemExit(
                f"match-copy contract trap case {case!r} did not signal; "
                f"return code {completed.returncode}"
            )


def verify_zng_checkout() -> None:
    if not (ZNG_SOURCE / "arch/arm/chunkset_neon.c").is_file():
        raise SystemExit("pinned zlib-ng NEON source is missing")
    head = run(
        ["git", "-C", str(ZNG_SOURCE), "rev-parse", "HEAD"], capture=True
    ).stdout.strip()
    if head != ZNG_COMMIT:
        raise SystemExit(f"zlib-ng commit mismatch: expected {ZNG_COMMIT}, got {head}")
    tracked_changes = run(
        [
            "git",
            "-C",
            str(ZNG_SOURCE),
            "status",
            "--short",
            "--untracked-files=no",
        ],
        capture=True,
    ).stdout.strip()
    if tracked_changes:
        raise SystemExit("pinned zlib-ng checkout has tracked modifications")


def build_variant(name: str, no_facts: bool) -> Path:
    source_dir = BUILD / name
    source_dir.mkdir(parents=True, exist_ok=True)
    copied = source_dir / SOURCE.name
    shutil.copyfile(SOURCE, copied)
    command = [str(PYTHON), str(DEMOC), str(copied)]
    if no_facts:
        command.append("--no-facts")
    run(command, capture=True)
    llvm = copied.with_suffix(".ll")
    obj = source_dir / "match_copy.o"
    exe = source_dir / "bench"
    common = [
        str(CLANG),
        "--no-default-config",
        "-O3",
        "-DNDEBUG",
        "-isysroot",
        str(SDK),
    ]
    run(common + ["-c", str(llvm), "-o", str(obj)], capture=True)
    zng_defines = [
        "-DARM_CRC32",
        "-DARM_CRC32_INTRIN",
        "-DARM_FEATURES",
        "-DARM_NEON",
        "-DARM_NEON_HASLD4",
        "-DHAVE_ARM_ACLE_H",
        "-DHAVE_ATTRIBUTE_ALIGNED",
        "-DHAVE_BUILTIN_ASSUME_ALIGNED",
        "-DHAVE_BUILTIN_CTZ",
        "-DHAVE_BUILTIN_CTZLL",
        "-DHAVE_SYS_SDT_H",
        "-DHAVE_VISIBILITY_HIDDEN",
        "-DHAVE_VISIBILITY_INTERNAL",
        "-DWITH_ALL_FALLBACKS",
        "-DWITH_GZFILEOP",
        "-DWITH_OPTIM",
        "-DZLIBNG_NATIVE_API",
    ]
    run(
        common
        + [
            "-march=armv8-a+simd",
            *zng_defines,
            "-I",
            str(ZNG_BUILD),
            "-I",
            str(ZNG_SOURCE),
            str(HERE / "bench.c"),
            str(HERE / "zng_kernel.c"),
            str(obj),
            "-o",
            str(exe),
        ],
        capture=True,
    )
    return exe


def main() -> int:
    verify_zng_checkout()
    BUILD.mkdir(exist_ok=True)
    executables = {
        "facts": build_variant("facts", False),
        "nofacts": build_variant("nofacts", True),
    }
    for executable in executables.values():
        print(run([str(executable), "check"], capture=True).stdout.strip())
        verify_contract(executable)
    print(
        "contract: "
        f"{len(CONTRACT_SUCCESSES) + len(CONTRACT_TRAPS)} cases passed "
        "for facts and nofacts"
    )

    rows: list[dict[str, object]] = []
    for distance, match_len in CASES:
        for sample in range(SAMPLES):
            order = VARIANTS[sample % 3 :] + VARIANTS[: sample % 3]
            for variant in order:
                executable = executables["nofacts" if variant == "nofacts" else "facts"]
                selected = "zng" if variant == "zng" else "wf"
                completed = run(
                    [
                        str(executable),
                        "run",
                        selected,
                        str(distance),
                        str(match_len),
                        str(OUTPUT_BYTES),
                        str(PASSES),
                    ],
                    capture=True,
                )
                row = json.loads(completed.stdout)
                row["variant"] = variant
                row["sample"] = sample
                row["bytes"] = row["produced_per_pass"] * row["passes"]
                row["gib_per_s"] = (
                    row["bytes"] / (1024.0**3) / (row["elapsed_ns"] / 1e9)
                )
                rows.append(row)
        case_rows = [
            row
            for row in rows
            if row["distance"] == distance and row["match_len"] == match_len
        ]
        medians = {
            variant: statistics.median(
                row["gib_per_s"] for row in case_rows if row["variant"] == variant
            )
            for variant in VARIANTS
        }
        print(
            f"distance={distance:5d} length={match_len:3d} "
            f"facts={medians['facts']:7.3f} GiB/s "
            f"nofacts={medians['nofacts']:7.3f} GiB/s "
            f"zng={medians['zng']:7.3f} GiB/s "
            f"facts/zng={medians['facts'] / medians['zng']:.3f}"
        )

    result = {
        "schema": "whitefoot.zlib-core.match-copy.v1",
        "output_bytes": OUTPUT_BYTES,
        "passes": PASSES,
        "samples": SAMPLES,
        "zlib_ng_commit": ZNG_COMMIT,
        "rows": rows,
    }
    (HERE / "results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
