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
        "Candidate C bounded validation is active",
        "CANDIDATE-C-BOUNDED-VALIDATION-PLAN.md",
        "Stage 1's five-operation Hashbrown paper calibration",
        "mandatory stop at Gate 1",
        "No Stage 2",
        "exact D-2/P-1 fail-",
    )
    require(ROOT / "AGENTS.md", status_phrases)
    require(
        ROOT / "THE-PLAN.md",
        (
            "CANDIDATE C\n   BOUNDED VALIDATION ACTIVE",
            "There is no evidence-\n   backed winner.",
            "C as the first bounded validation",
            "CANDIDATE-C-BOUNDED-VALIDATION-PLAN.md",
            "mandatory stop at Gate 1",
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
            "stop at Gate 1",
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
    print("performance research status: Candidate C bounded validation, Stages 0/1 only")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"performance research status verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
