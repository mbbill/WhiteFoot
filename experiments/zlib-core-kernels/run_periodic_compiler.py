#!/usr/bin/env python3
"""Measure opt-in compiler-recognized periodic copy against the ordinary loop."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import statistics


HERE = Path(__file__).resolve().parent
BASE_SPEC = importlib.util.spec_from_file_location("match_copy_base_run", HERE / "run.py")
BASE = importlib.util.module_from_spec(BASE_SPEC)
assert BASE_SPEC.loader is not None
BASE_SPEC.loader.exec_module(BASE)

BUILD = HERE / "build" / "periodic-compiler"
RESULTS = HERE / "periodic-compiler-results.json"
HELPER = HERE / "periodic_copy_helper.c"
SOURCE_SHA256 = "cd4962c29f6725141d2c555a22986c585f1da8e46274cd776bfee48e270239d7"
VARIANTS = ("baseline", "periodic", "zng")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_variant(name: str, periodic: bool) -> Path:
    source_dir = BUILD / name
    source_dir.mkdir(parents=True, exist_ok=True)
    copied = source_dir / BASE.SOURCE.name
    shutil.copyfile(BASE.SOURCE, copied)
    if sha256(copied) != SOURCE_SHA256:
        raise SystemExit("copied match_copy.wf does not match the pinned source")

    command = [str(BASE.PYTHON), str(BASE.DEMOC), str(copied)]
    if periodic:
        command.append("--periodic-copy-experiment")
    BASE.run(command, capture=True)
    llvm = copied.with_suffix(".ll")
    lowered = "call i64 @__wf_periodic_copy_u8_repeated" in llvm.read_text(
        encoding="utf-8"
    )
    if lowered != periodic:
        raise SystemExit(
            f"periodic-copy lowering mismatch for {name}: expected {periodic}, got {lowered}"
        )

    obj = source_dir / "match_copy.o"
    exe = source_dir / "bench"
    common = [
        str(BASE.CLANG),
        "--no-default-config",
        "-O3",
        "-DNDEBUG",
        "-isysroot",
        str(BASE.SDK),
    ]
    BASE.run(common + ["-c", str(llvm), "-o", str(obj)], capture=True)
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
    sources = [str(HERE / "bench.c"), str(HERE / "zng_kernel.c")]
    if periodic:
        sources.append(str(HELPER))
    BASE.run(
        common
        + [
            "-march=armv8-a+simd",
            *zng_defines,
            "-I",
            str(BASE.ZNG_BUILD),
            "-I",
            str(BASE.ZNG_SOURCE),
            *sources,
            str(obj),
            "-o",
            str(exe),
        ],
        capture=True,
    )
    return exe


def main() -> int:
    if sha256(BASE.SOURCE) != SOURCE_SHA256:
        raise SystemExit("match_copy.wf changed from the pinned experiment source")
    BASE.verify_zng_checkout()
    BUILD.mkdir(parents=True, exist_ok=True)
    executables = {
        "baseline": build_variant("baseline", False),
        "periodic": build_variant("periodic", True),
    }
    for executable in executables.values():
        print(BASE.run([str(executable), "check"], capture=True).stdout.strip())
        BASE.verify_contract(executable)
    print(
        "contract: "
        f"{len(BASE.CONTRACT_SUCCESSES) + len(BASE.CONTRACT_TRAPS)} cases passed "
        "for baseline and periodic"
    )

    rows: list[dict[str, object]] = []
    for distance, match_len in BASE.CASES:
        for sample in range(BASE.SAMPLES):
            order = VARIANTS[sample % 3 :] + VARIANTS[: sample % 3]
            for variant in order:
                executable = executables[
                    "periodic" if variant == "periodic" else "baseline"
                ]
                selected = "zng" if variant == "zng" else "wf"
                completed = BASE.run(
                    [
                        str(executable),
                        "run",
                        selected,
                        str(distance),
                        str(match_len),
                        str(BASE.OUTPUT_BYTES),
                        str(BASE.PASSES),
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
                row["gib_per_s"]
                for row in case_rows
                if row["variant"] == variant
            )
            for variant in VARIANTS
        }
        print(
            f"distance={distance:5d} length={match_len:3d} "
            f"baseline={medians['baseline']:7.3f} GiB/s "
            f"periodic={medians['periodic']:7.3f} GiB/s "
            f"zng={medians['zng']:7.3f} GiB/s "
            f"periodic/zng={medians['periodic'] / medians['zng']:.3f}"
        )

    result = {
        "schema": "whitefoot.zlib-core.periodic-compiler.v1",
        "output_bytes": BASE.OUTPUT_BYTES,
        "passes": BASE.PASSES,
        "samples": BASE.SAMPLES,
        "source_sha256": SOURCE_SHA256,
        "helper_sha256": sha256(HELPER),
        "zlib_ng_commit": BASE.ZNG_COMMIT,
        "rows": rows,
    }
    RESULTS.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
