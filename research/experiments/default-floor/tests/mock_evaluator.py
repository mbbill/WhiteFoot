#!/usr/bin/env python3
"""Mock path-last evaluator used by the protocol tests."""

import json
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) < 3:
        return 80
    mode = sys.argv[1]
    candidate = Path(sys.argv[-1])
    if not candidate.is_absolute() or not candidate.is_file():
        return 81
    source = candidate.read_text(encoding="utf-8")
    passed = "GOOD" in source
    if mode == "normal":
        feedback = {
            "compile": {"passed": True, "diagnostics": []},
            "correctness": {
                "passed": passed,
                "diagnostics": [] if passed else [{"code": "MOCK_WRONG", "message": "candidate is not good"}],
            },
            "proof": {"status": "reported", "sites": []},
        }
    elif mode == "forbidden-perf":
        feedback = {
            "compile": {"passed": True},
            "correctness": {"passed": True},
            "proof": {"status": "reported", "benchmark_ns": 12},
        }
    elif mode == "forbidden-wall-ns":
        feedback = {
            "compile": {"passed": True},
            "correctness": {"passed": False, "diagnostics": []},
            "proof": {"status": "reported", "metrics": {"wall_ns": 12}},
        }
    elif mode == "forbidden-perf-text":
        feedback = {
            "compile": {"passed": True},
            "correctness": {
                "passed": False,
                "diagnostics": [{"code": "MOCK_WRONG", "message": "latency was 12 ns"}],
            },
        }
    else:
        return 82
    sys.stdout.write(json.dumps(feedback))
    return 0


if __name__ == "__main__":
    sys.exit(main())
