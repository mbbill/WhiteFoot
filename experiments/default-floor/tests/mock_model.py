#!/usr/bin/env python3
"""Mock source-only model used by the protocol tests."""

import json
import os
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 3:
        return 90
    mode = sys.argv[1]
    state_path = Path(sys.argv[2])
    if os.listdir("."):
        print("model cwd was not empty", file=sys.stderr)
        return 91
    prompt = sys.stdin.read()
    count = 0
    if state_path.exists():
        count = json.loads(state_path.read_text(encoding="utf-8"))["calls"]
    state_path.write_text(json.dumps({"calls": count + 1, "last_prompt": prompt}), encoding="utf-8")
    if mode == "first-shot":
        sys.stdout.write("GOOD first shot\n")
        return 0
    if mode == "repair":
        sys.stdout.write("BAD needs repair\n" if count == 0 else "GOOD repaired\n")
        return 0
    if mode == "fail":
        sys.stdout.write("PARTIAL source\n")
        print("mock model failure", file=sys.stderr)
        return 7
    print(f"unknown mock mode: {mode}", file=sys.stderr)
    return 92


if __name__ == "__main__":
    sys.exit(main())
