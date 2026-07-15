#!/usr/bin/env python3
"""Verify the final active status for performance-first capability research."""

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
        "complete for owner review",
        "there is no evidence-backed winner",
        "VR-0",
        "No repair, model, prototype",
        "exact D-2/P-1 fail-closed",
    )
    require(ROOT / "AGENTS.md", status_phrases)
    require(
        ROOT / "THE-PLAN.md",
        (
            "OWNER REVIEW",
            "There is no evidence-\n   backed winner.",
            "not a complete selectable set",
            "PERFORMANCE-FIRST-OWNER-DECISION-PACKET.md",
            "VR-0 exact paper repair",
        ),
    )
    require(
        ROOT / "HANDOVER.md",
        (
            "The performance-first owner packet is complete",
            "There is no evidence-backed winner.",
            "B is not selectable",
            "VR-0 paper repair only",
        ),
    )
    plan_text = (ROOT / "THE-PLAN.md").read_text(encoding="utf-8")
    agents_text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for stale in ("CANDIDATE COMPARISON PENDING", "candidate comparison pending"):
        if stale in plan_text:
            fail(f"THE-PLAN.md retains stale status {stale!r}")
    if "Performance-first minimal-capability research is the active design track" in agents_text:
        fail("agent instructions retain stale active-design-track status")
    print("performance research status: owner review pending, no winner, VR-0 only recommended")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"performance research status verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
