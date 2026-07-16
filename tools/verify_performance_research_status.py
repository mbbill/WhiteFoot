#!/usr/bin/env python3
"""Verify the active bounded Candidate C validation status."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise ValueError(message)


def require(path: Path, phrases: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    for phrase in phrases:
        if phrase not in text:
            fail(f"{path.relative_to(ROOT)} omits {phrase!r}")


def main() -> int:
    agents = (ROOT / "AGENTS.md").read_bytes()
    claude = (ROOT / "CLAUDE.md").read_bytes()
    if agents != claude:
        fail("AGENTS.md and CLAUDE.md are not byte-identical")

    status_phrases = (
        "Candidate C sparse paper repair is active",
        "CANDIDATE-C-SPARSE-REPAIR-PLAN.md",
        "Stage 1 are complete",
        "`C-REVISE`",
        "stops at the Sparse Repair Gate",
        "No Stage 2",
        "exact D-2/P-1 fail-",
    )
    require(ROOT / "AGENTS.md", status_phrases)
    require(
        ROOT / "THE-PLAN.md",
        (
            "CANDIDATE C\n   SPARSE PAPER REPAIR ACTIVE",
            "There is no evidence-\n   backed winner.",
            "C as the first bounded validation",
            "CANDIDATE-C-BOUNDED-VALIDATION-PLAN.md",
            "mandatory Sparse Repair Gate stop",
            "No Stage 2",
        ),
    )
    require(
        ROOT / "HANDOVER.md",
        (
            "The performance-first owner packet is complete",
            "There is no evidence-backed production winner.",
            "C as the first bounded validation hypothesis",
            "CANDIDATE-C-BOUNDED-VALIDATION-PLAN.md",
            "route 1: a bounded paper repair",
            "mandatory Sparse Repair Gate stop",
        ),
    )
    plan_text = (ROOT / "THE-PLAN.md").read_text(encoding="utf-8")
    agents_text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for stale in ("CANDIDATE COMPARISON PENDING", "candidate comparison pending"):
        if stale in plan_text:
            fail(f"THE-PLAN.md retains stale status {stale!r}")
    if "Performance-first minimal-capability research is the active design track" in agents_text:
        fail("agent instructions retain stale active-design-track status")
    require(
        ROOT
        / "optimizer-language-research"
        / "implementation"
        / "minimal-systems-capability"
        / "CANDIDATE-C-BOUNDED-VALIDATION-PLAN.md",
        (
            "controlling research contract",
            "Work must stop at Gate 1",
            "Stage 0 — freeze Candidate C v0 and the rubric",
            "Stage 1 — bounded Hashbrown calibration",
            "Later stages — not authorized",
            "`UNKNOWN` is unresolved, never a pass",
        ),
    )
    require(
        ROOT
        / "optimizer-language-research"
        / "implementation"
        / "minimal-systems-capability"
        / "CANDIDATE-C-SPARSE-REPAIR-PLAN.md",
        (
            "controlling paper-repair contract",
            "Derive exactly three alternatives",
            "Exactly three alternatives and fifteen candidate-operation rows.",
            "Sparse Repair Gate",
            "The gate authorizes no implementation or further audit.",
        ),
    )
    require(
        ROOT
        / "optimizer-language-research"
        / "implementation"
        / "minimal-systems-capability"
        / "CANDIDATE-C-HASHBROWN-AUDIT.md",
        (
            "Gate 1 disposition: `C-REVISE`.",
            "Stage 2 is not authorized.",
        ),
    )
    print("performance research status: Candidate C sparse paper repair active")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"performance research status verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
