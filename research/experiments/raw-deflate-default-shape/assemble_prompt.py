#!/usr/bin/env python3
"""Assemble the hash-locked raw-DEFLATE writer prompt byte-for-byte."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TASK = HERE / "task.md"
TEACHING = HERE / "teaching-pack.md"
PATTERNS = ROOT / "PATTERNS.md"
SEPARATOR = b"\n===== BEGIN COMPLETE WHITEFOOT WRITER'S PACK =====\n\n"
PATTERN_SEPARATOR = (
    b"\n===== BEGIN COMPLETE WHITEFOOT PATTERN DOCTRINE =====\n\n"
    b"The following is the project's complete architecture guidance. It does not "
    b"add syntax: only forms admitted by the preceding stage-0 writer's pack are "
    b"available for this task.\n\n"
)
EXPECTED = {
    "task.md": "cf241974c39ecb2bbb1311f43b4cd0c7f5b71f2f032f60b433f76986432083c7",
    "teaching-pack.md": "466325804fd934665e41e2d9552bb1941f22ff542fb401f614d1879b1ea9cd98",
    "PATTERNS.md": "69213a146c84911f0675ca11f9be70c7515ea74a4a2d15788a2ce280550e51f4",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def assemble() -> tuple[bytes, dict[str, object]]:
    task = TASK.read_bytes()
    teaching = TEACHING.read_bytes()
    patterns = PATTERNS.read_bytes()
    observed = {
        "task.md": sha256(task),
        "teaching-pack.md": sha256(teaching),
        "PATTERNS.md": sha256(patterns),
    }
    if observed != EXPECTED:
        raise RuntimeError(f"prompt component hash mismatch: {observed}")
    prompt = task + SEPARATOR + teaching + PATTERN_SEPARATOR + patterns
    manifest: dict[str, object] = {
        "components": observed,
        "separator_utf8": SEPARATOR.decode("utf-8"),
        "pattern_separator_utf8": PATTERN_SEPARATOR.decode("utf-8"),
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
