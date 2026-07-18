#!/usr/bin/env python3
"""Regressions for the spec/test governance guard.

These pin the exact violation shapes the guard must catch — the ones the parked
`parked_edits` branch (D20-R3) walked through: an in-place numbered-spec edit, a
flipped conformance expected verdict, a regenerated oracle digest, and a rewritten
reference test. Additions must stay free.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import spec_guard

ROOT = Path(__file__).resolve().parents[1]


def base() -> dict:
    return {
        "kernel_specs": {"spec/kernel-spec-v0.6.md": "aaaa"},
        "conformance": {"own1-neg-x": "c1", "rule:META-1": "c2"},
        "oracles": {"tools/codegen_parity.py": ["deadbeef"]},
        "tests": {"prototype/checker/test_checker.py": {"Negative.test_x": "t1"}},
    }


def check(name: str, condition: bool) -> None:
    if not condition:
        print(f"FAIL: {name}", file=sys.stderr)
        raise SystemExit(1)
    print(f"ok: {name}")


def test_compliant_tree_has_no_violations() -> None:
    check("identical surface -> no violations", diff_is_empty(base(), base()))


def diff_is_empty(baseline: dict, live: dict) -> bool:
    return spec_guard.diff_surface(baseline, live) == []


def test_in_place_spec_edit_is_caught() -> None:
    live = base()
    live["kernel_specs"] = {"spec/kernel-spec-v0.6.md": "bbbb"}  # hash changed, same file
    violations = spec_guard.diff_surface(base(), live)
    check("in-place spec edit flagged", any("in place" in v for v in violations))


def test_spec_removed_or_added_is_caught() -> None:
    removed = spec_guard.diff_surface(base(), {**base(), "kernel_specs": {}})
    check("spec removal flagged", any("removed" in v for v in removed))
    added = spec_guard.diff_surface(
        base(),
        {**base(), "kernel_specs": {"spec/kernel-spec-v0.6.md": "aaaa",
                                    "spec/kernel-spec-v0.7.md": "zzzz"}},
    )
    check("new spec without approval flagged", any("new numbered kernel spec" in v for v in added))


def test_flipped_conformance_verdict_is_caught() -> None:
    live = base()
    live["conformance"] = {"own1-neg-x": "CHANGED", "rule:META-1": "c2"}
    violations = spec_guard.diff_surface(base(), live)
    check("changed conformance verdict flagged",
          any("own1-neg-x" in v and "changed" in v for v in violations))


def test_removed_conformance_case_is_caught() -> None:
    live = base()
    live["conformance"] = {"rule:META-1": "c2"}  # own1-neg-x gone
    violations = spec_guard.diff_surface(base(), live)
    check("removed conformance case flagged",
          any("own1-neg-x" in v and "removed" in v for v in violations))


def test_added_conformance_case_is_free() -> None:
    live = base()
    live["conformance"] = {**base()["conformance"], "own1-pos-new": "brand-new"}
    check("added conformance case is allowed", diff_is_empty(base(), live))


def test_regenerated_oracle_digest_is_caught() -> None:
    live = base()
    live["oracles"] = {"tools/codegen_parity.py": ["0000new"]}  # old digest gone
    violations = spec_guard.diff_surface(base(), live)
    check("regenerated oracle digest flagged", any("oracle digest" in v for v in violations))


def test_added_oracle_digest_is_free() -> None:
    live = base()
    live["oracles"] = {"tools/codegen_parity.py": ["deadbeef", "0000new"]}
    check("added oracle digest is allowed", diff_is_empty(base(), live))


def test_rewritten_or_removed_test_is_caught() -> None:
    rewritten = base()
    rewritten["tests"] = {"prototype/checker/test_checker.py": {"Negative.test_x": "CHANGED"}}
    check("rewritten reference test flagged",
          any("rewritten" in v for v in spec_guard.diff_surface(base(), rewritten)))
    removed = base()
    removed["tests"] = {"prototype/checker/test_checker.py": {}}
    check("removed reference test flagged",
          any("removed" in v for v in spec_guard.diff_surface(base(), removed)))


def test_added_test_is_free() -> None:
    live = base()
    live["tests"] = {
        "prototype/checker/test_checker.py": {"Negative.test_x": "t1", "Negative.test_new": "t2"}
    }
    check("added reference test is allowed", diff_is_empty(base(), live))


def test_working_tree_passes_check() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "spec_guard.py"), "--check"],
        capture_output=True,
        text=True,
    )
    check("committed working tree passes --check", result.returncode == 0)


def main() -> int:
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("spec-guard regressions: all green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
