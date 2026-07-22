#!/usr/bin/env python3
"""Create or verify the raw-DEFLATE generation-input manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE / "generation-inputs.json"
PYTHON = Path(
    "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/"
    "Python3.framework/Versions/3.9/bin/python3.9"
)
CLANG = Path(
    "/Applications/Xcode.app/Contents/Developer/Toolchains/"
    "XcodeDefault.xctoolchain/usr/bin/clang"
)
SDK_SETTINGS = Path(
    "/Applications/Xcode.app/Contents/Developer/Platforms/"
    "MacOSX.platform/Developer/SDKs/MacOSX.sdk/SDKSettings.json"
)
CODEX = Path("/opt/homebrew/bin/codex")
CODEX_JAVASCRIPT = Path(
    "/opt/homebrew/lib/node_modules/@openai/codex/bin/codex.js"
)
CODEX_NATIVE = Path(
    "/opt/homebrew/lib/node_modules/@openai/codex/node_modules/"
    "@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex"
)
NODE = Path("/opt/homebrew/Cellar/node/25.9.0_2/bin/node")
SYSTEM_PROFILER = Path("/usr/sbin/system_profiler")
SW_VERS = Path("/usr/bin/sw_vers")
PMSET = Path("/usr/bin/pmset")
LAUNCHER_RELATIVE = "experiments/raw-deflate-default-shape/run_generation.py"
LAUNCHER_HASH_PATTERN = re.compile(
    rb'(?m)^INPUT_MANIFEST_SHA256 = "[0-9a-f]*"$'
)
LAUNCHER_HASH_REPLACEMENT = (
    b'INPUT_MANIFEST_SHA256 = "' + (b"0" * 64) + b'"'
)
EXPECTED_HOST = {
    "architecture": "arm64",
    "build_version": "25F80",
    "chip_type": "Apple M4",
    "low_power_mode": 0,
    "machine_model": "Mac16,12",
    "number_processors": "proc 10:4:6:0",
    "physical_memory": "16 GB",
    "power_source": "AC Power",
    "product_version": "26.5.1",
    "thermal_probe": "unavailable",
}


INPUT_PATHS = (
    "PATTERNS.md",
    "experiments/default-floor/PROTOCOL.md",
    "experiments/default-floor/README.md",
    "experiments/default-floor/codex_model_adapter.py",
    "experiments/default-floor/generate.py",
    "experiments/default-floor/tests/__init__.py",
    "experiments/default-floor/tests/mock_codex_cli.py",
    "experiments/default-floor/tests/mock_evaluator.py",
    "experiments/default-floor/tests/mock_model.py",
    "experiments/default-floor/tests/test_codex_model.py",
    "experiments/default-floor/tests/test_generate.py",
    "experiments/raw-deflate-default-shape/.gitignore",
    "experiments/raw-deflate-default-shape/PROTOCOL.md",
    "experiments/raw-deflate-default-shape/README.md",
    "experiments/raw-deflate-default-shape/analyze.py",
    "experiments/raw-deflate-default-shape/assemble_prompt.py",
    "experiments/raw-deflate-default-shape/base-prompt.txt",
    "experiments/raw-deflate-default-shape/benchmark.py",
    "experiments/raw-deflate-default-shape/corpus.py",
    "experiments/raw-deflate-default-shape/correctness-corpus.json",
    "experiments/raw-deflate-default-shape/input_manifest.py",
    "experiments/raw-deflate-default-shape/oracle.py",
    "experiments/raw-deflate-default-shape/prepare_scoring.py",
    "experiments/raw-deflate-default-shape/reference.c",
    "experiments/raw-deflate-default-shape/reference.py",
    LAUNCHER_RELATIVE,
    "experiments/raw-deflate-default-shape/scoring-manifest.json",
    "experiments/raw-deflate-default-shape/stock_zlib.c",
    "experiments/raw-deflate-default-shape/stock_zlib.py",
    "experiments/raw-deflate-default-shape/task.md",
    "experiments/raw-deflate-default-shape/teaching-pack.md",
    "experiments/raw-deflate-default-shape/test_oracle.py",
    "experiments/raw-deflate-default-shape/verify.py",
    "prototype/checker/checker.py",
    "prototype/democ/democ.py",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def input_sha256(relative: str, path: Path) -> str:
    if relative != LAUNCHER_RELATIVE:
        return sha256_file(path)
    normalized, replacements = LAUNCHER_HASH_PATTERN.subn(
        LAUNCHER_HASH_REPLACEMENT, path.read_bytes()
    )
    if replacements != 1:
        raise RuntimeError("generation launcher has no unique manifest-hash binding")
    return hashlib.sha256(normalized).hexdigest()


def checked_output(command: Sequence[str]) -> str:
    process = subprocess.run(
        list(command),
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip()
        raise RuntimeError(f"tool identity command failed: {command[0]}: {detail}")
    return process.stdout.strip()


def observe_host() -> dict[str, Any]:
    hardware = json.loads(
        checked_output([str(SYSTEM_PROFILER), "SPHardwareDataType", "-json"])
    )
    records = hardware.get("SPHardwareDataType")
    if not isinstance(records, list) or len(records) != 1 or not isinstance(records[0], dict):
        raise RuntimeError("system_profiler returned an unexpected hardware record")
    record = records[0]
    battery = checked_output([str(PMSET), "-g", "batt"]).splitlines()
    if not battery:
        raise RuntimeError("pmset did not report a power source")
    power_match = re.fullmatch(r"Now drawing from '([^']+)'", battery[0])
    if power_match is None:
        raise RuntimeError("pmset reported an unexpected power-source line")
    custom = checked_output([str(PMSET), "-g", "custom"])
    ac_section = custom.rsplit("AC Power:", 1)
    if len(ac_section) != 2:
        raise RuntimeError("pmset did not report AC power settings")
    low_power_match = re.search(
        r"(?m)^\s*lowpowermode\s+(\d+)\s*$", ac_section[1]
    )
    if low_power_match is None:
        raise RuntimeError("pmset did not report AC low-power mode")
    observed = {
        "architecture": platform.machine(),
        "build_version": checked_output([str(SW_VERS), "-buildVersion"]),
        "chip_type": record.get("chip_type"),
        "low_power_mode": int(low_power_match.group(1)),
        "machine_model": record.get("machine_model"),
        "number_processors": record.get("number_processors"),
        "physical_memory": record.get("physical_memory"),
        "power_source": power_match.group(1),
        "product_version": checked_output([str(SW_VERS), "-productVersion"]),
        "thermal_probe": "unavailable",
    }
    if observed != EXPECTED_HOST:
        raise RuntimeError(f"execution host differs from preregistration: {observed}")
    return observed


def tool(
    path: Path,
    version_argv: Sequence[str],
) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"tool input is missing or symlinked: {path}")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "version_argv": list(version_argv),
        "version_stdout": checked_output(version_argv),
    }


def build_manifest() -> dict[str, Any]:
    files: dict[str, str] = {}
    for relative in INPUT_PATHS:
        path = ROOT / relative
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"generation input is missing or symlinked: {relative}")
        files[relative] = input_sha256(relative, path)

    sdk_probe = [
        str(PYTHON),
        "-c",
        (
            "import json; p=json.load(open(" + repr(str(SDK_SETTINGS)) + ")); "
            "print(p['CanonicalName'] + '|' + p['Version'])"
        ),
    ]
    tools = {
        "clang": tool(CLANG, [str(CLANG), "--version"]),
        "codex_javascript": tool(
            CODEX_JAVASCRIPT, [str(CODEX), "--version"]
        ),
        "codex_native": tool(CODEX_NATIVE, [str(CODEX_NATIVE), "--version"]),
        "macos_sdk_settings": tool(SDK_SETTINGS, sdk_probe),
        "node": tool(NODE, [str(NODE), "--version"]),
        "python": tool(PYTHON, [str(PYTHON), "--version"]),
    }
    return {
        "schema": "whitefoot.raw-deflate.generation-inputs.v1",
        "files": files,
        "host": observe_host(),
        "tools": tools,
        "trajectory": {
            "model": "gpt-5.6-terra",
            "reasoning_effort": "medium",
            "repair_budget": 3,
            "service_tier": "default",
            "source_name": "inflate_raw.wf",
        },
    }


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--create", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        expected = canonical_json(build_manifest())
        if args.create:
            with OUTPUT.open("xb") as destination:
                destination.write(expected)
        elif OUTPUT.read_bytes() != expected:
            raise RuntimeError("generation-input manifest is stale")
    except (OSError, RuntimeError, KeyError, json.JSONDecodeError) as error:
        print(f"generation-input manifest failed: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "files": len(INPUT_PATHS),
                "manifest_sha256": hashlib.sha256(expected).hexdigest(),
                "tools": 6,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
