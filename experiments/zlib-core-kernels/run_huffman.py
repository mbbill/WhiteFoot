#!/usr/bin/env python3
"""Build and measure the Whitefoot DEFLATE Huffman literal kernel."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess


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
DEMOC = ROOT / "prototype/democ/democ.py"
ZNG_ROOT = Path(
    os.environ.get(
        "WHITEFOOT_ZNG_ROOT", "/private/tmp/whitefoot-zlib-research.wpK9iq"
    )
)
ZNG_BUILD = ZNG_ROOT / "build-zng-dispatch"
ZNG_SOURCE = ZNG_ROOT / "zlib-ng"
ZNG_COMMIT = "12731092979c6d07f42da27da673a9f6c7b13586"
SOURCE = HERE / "huffman_literals.wf"
SYMBOLS = 32 * 1024 * 1024 - 2
PASSES = 4
SAMPLES = 12
VARIANTS = ("facts", "nofacts", "zng")
CONTRACT_SUCCESSES = ("zero", "exact-input")
CONTRACT_TRAPS = (
    "short-input",
    "short-output",
    "nonliteral",
    "count-overflow",
)


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def verify_fixed_table_identity() -> None:
    source_text = SOURCE.read_text(encoding="utf-8")
    wf_table_text = source_text.split("];")[0]
    wf_entries = [
        int(value) for value in re.findall(r"\b([0-9]+)_u32\b", wf_table_text)
    ]

    zng_header = (ZNG_SOURCE / "inffixed_tbl.h").read_text(encoding="utf-8")
    zng_table_text = zng_header.split("static const code lenfix[512] = {", 1)[1]
    zng_table_text = zng_table_text.split("};", 1)[0]
    zng_entries = [
        int(operation) | (int(bits) << 8) | (int(value) << 16)
        for operation, bits, value in re.findall(
            r"\{([0-9]+),([0-9]+),([0-9]+)\}", zng_table_text
        )
    ]
    if len(wf_entries) != 512 or len(zng_entries) != 512:
        raise SystemExit(
            "fixed Huffman table audit failed: "
            f"Whitefoot={len(wf_entries)} zlib-ng={len(zng_entries)} entries"
        )
    if wf_entries != zng_entries:
        mismatch = next(
            index
            for index, (wf_entry, zng_entry) in enumerate(
                zip(wf_entries, zng_entries)
            )
            if wf_entry != zng_entry
        )
        raise SystemExit(
            "fixed Huffman table audit failed at index "
            f"{mismatch}: Whitefoot={wf_entries[mismatch]} "
            f"zlib-ng={zng_entries[mismatch]}"
        )


def verify_zng_checkout() -> None:
    head = run(["git", "-C", str(ZNG_SOURCE), "rev-parse", "HEAD"]).stdout.strip()
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
        ]
    ).stdout.strip()
    if tracked_changes:
        raise SystemExit("pinned zlib-ng checkout has tracked modifications")


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
                f"Huffman contract success case {case!r} returned "
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
                f"Huffman contract trap case {case!r} did not signal; "
                f"return code {completed.returncode}"
            )


def build_variant(name: str, no_facts: bool) -> Path:
    target = BUILD / f"huffman-{name}"
    target.mkdir(parents=True, exist_ok=True)
    copied = target / SOURCE.name
    shutil.copyfile(SOURCE, copied)
    command = [str(PYTHON), str(DEMOC), str(copied)]
    if no_facts:
        command.append("--no-facts")
    run(command)
    obj = target / "kernel.o"
    exe = target / "bench"
    common = [
        str(CLANG),
        "--no-default-config",
        "-O3",
        "-DNDEBUG",
        "-isysroot",
        str(SDK),
    ]
    run(common + ["-c", str(copied.with_suffix(".ll")), "-o", str(obj)])
    run(
        common
        + [
            "-DZLIBNG_NATIVE_API",
            "-I",
            str(ZNG_BUILD),
            "-I",
            str(ZNG_SOURCE),
            str(HERE / "huffman_bench.c"),
            str(HERE / "zng_huffman_kernel.c"),
            str(obj),
            "-o",
            str(exe),
        ]
    )
    return exe


def main() -> int:
    verify_zng_checkout()
    verify_fixed_table_identity()
    BUILD.mkdir(exist_ok=True)
    executables = {
        "facts": build_variant("facts", False),
        "nofacts": build_variant("nofacts", True),
    }
    for executable in executables.values():
        verify_contract(executable)
    print(
        "contract: "
        f"{len(CONTRACT_SUCCESSES) + len(CONTRACT_TRAPS)} cases passed "
        "for facts and nofacts"
    )
    rows: list[dict[str, object]] = []
    for sample in range(SAMPLES):
        order = VARIANTS[sample % 3 :] + VARIANTS[: sample % 3]
        for variant in order:
            executable = executables["nofacts" if variant == "nofacts" else "facts"]
            selected = "zng" if variant == "zng" else "wf"
            completed = run(
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
    print(
        f"facts={medians['facts']:.3f} Msyms/s "
        f"nofacts={medians['nofacts']:.3f} Msyms/s "
        f"zng={medians['zng']:.3f} Msyms/s "
        f"facts/zng={medians['facts'] / medians['zng']:.3f}"
    )
    (HERE / "huffman-results.json").write_text(
        json.dumps(
            {
                "schema": "whitefoot.zlib-core.huffman-literals.v1",
                "symbols": SYMBOLS,
                "passes": PASSES,
                "samples": SAMPLES,
                "zlib_ng_commit": ZNG_COMMIT,
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
