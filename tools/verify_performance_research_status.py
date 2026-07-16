#!/usr/bin/env python3
"""Verify the active bounded Candidate B cross-project design status."""

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
        "Candidate B's bounded cross-project design research is active",
        "CANDIDATE-B-ELEGANT-DESIGN-PLAN.md",
        "fourteen\n  frozen operations across Hashbrown, mimalloc, SQLite, and Crossbeam Epoch",
        "`B-FORMS`, `B-STRATA`, and `B-GRAPHS`",
        "then stop at the Candidate B Design Gate",
        "read-only paper research",
        "D-2/P-1 fail-closed.",
    )
    require(ROOT / "AGENTS.md", status_phrases)
    require(
        ROOT / "THE-PLAN.md",
        (
            "CANDIDATE B\n   CROSS-PROJECT DESIGN ACTIVE",
            "There is no evidence-\n   backed winner.",
            "fourteen operations across four\n   official source revisions",
            "exactly three B architectures",
            "exactly 42 fail-closed operation routes",
            "CANDIDATE-B-ELEGANT-DESIGN-PLAN.md",
            "Sparse Repair Gate selects `SR-PROFILE`",
            "No Stage 2, additional",
        ),
    )
    require(
        ROOT / "HANDOVER.md",
        (
            "The performance-first owner packet is complete",
            "There is no evidence-backed production winner.",
            "The active work has now moved to Candidate B.",
            "CANDIDATE-B-ELEGANT-DESIGN-PLAN.md",
            "Hashbrown, mimalloc, SQLite, and Crossbeam Epoch",
            "exactly 42 comparison rows",
            "Sparse Repair Gate selects `SR-PROFILE`",
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
        / "CANDIDATE-B-ELEGANT-DESIGN-PLAN.md",
        (
            "controlling bounded paper-design and source-audit contract",
            "Audit exactly fourteen operations.",
            "Derive exactly three alternatives before routing any operation",
            "Produce exactly 42 candidate-operation rows",
            "at least two independent projects",
            "Stop after the deliverables",
        ),
    )
    require(
        ROOT
        / "optimizer-language-research"
        / "implementation"
        / "minimal-systems-capability"
        / "CANDIDATE-C-SPARSE-REPAIR-CANDIDATES.md",
        (
            "Sparse Repair Gate disposition: `SPARSE-SELECT: SR-PROFILE`.",
            "Candidate C v0 is unchanged.",
            "Work stops at this gate.",
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
    print("performance research status: Candidate B cross-project design active")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"performance research status verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
