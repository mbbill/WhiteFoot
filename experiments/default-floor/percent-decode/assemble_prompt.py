#!/usr/bin/env python3
"""Assemble the hash-locked percent-decode base prompt without normalization."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
TASK = HERE / "task.md"
TEACHING = HERE / "teaching-pack.md"
SEPARATOR = b"\n===== BEGIN COMPLETE XLANG WRITER'S PACK =====\n\n"
EXPECTED = {
    "task.md": "5ee6fbf0def51248ccc7749855a11c9b6cb8f44a664ff74326d84f91285fc022",
    "teaching-pack.md": "a4ee1213415af5c56bdbbfa21697388b37f644bbc64a478ff7006fd03dcdfcd5",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def assemble() -> tuple[bytes, dict[str, object]]:
    task = TASK.read_bytes()
    teaching = TEACHING.read_bytes()
    observed = {"task.md": sha256(task), "teaching-pack.md": sha256(teaching)}
    if observed != EXPECTED:
        raise RuntimeError(f"prompt component hash mismatch: {observed}")
    prompt = task + SEPARATOR + teaching
    manifest: dict[str, object] = {
        "components": observed,
        "separator_utf8": SEPARATOR.decode("utf-8"),
        "base_prompt_sha256": sha256(prompt),
        "base_prompt_bytes": len(prompt),
    }
    return prompt, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        prompt, manifest = assemble()
        with args.output.open("xb") as stream:
            stream.write(prompt)
    except (OSError, RuntimeError) as error:
        print(f"prompt assembly failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
