#!/usr/bin/env python3
"""Verify the completed bounded Candidate B cross-project design status."""

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
        "Candidate B's bounded cross-project design research stopped",
        "Design Gate with `B-REVISE`",
        "`B-FORMS` has 14 open",
        "`B-STRATA` has six closed and eight open",
        "`B-GRAPHS` has six\n  closed and eight open",
        "policy-neutral\n  quiescence",
        "authorization is exhausted",
        "D-2/P-1 fail-closed.",
    )
    require(ROOT / "AGENTS.md", status_phrases)
    require(
        ROOT / "THE-PLAN.md",
        (
            "CANDIDATE B\n   DESIGN GATE COMPLETE: `B-REVISE`",
            "There is no evidence-\n   backed winner.",
            "complete across fourteen\n   operations and four pinned source revisions",
            "`B-STRATA` six closed and eight open rows",
            "`B-GRAPHS` six closed and\n   eight open rows",
            "CANDIDATE-B-ELEGANT-DESIGN-PLAN.md",
            "Sparse Repair Gate selects `SR-PROFILE`",
            "authorization is exhausted at the\n   `B-REVISE` Design Gate",
        ),
    )
    require(
        ROOT / "HANDOVER.md",
        (
            "The performance-first owner packet is complete",
            "There is no evidence-backed production winner.",
            "Candidate B's bounded cross-project comparison is now complete.",
            "CANDIDATE-B-ELEGANT-DESIGN-PLAN.md",
            "exact fourteen-operation, 42-route result",
            "`B-STRATA`: six closed and eight open",
            "The gate is `B-REVISE`.",
            "Sparse Repair Gate selects `SR-PROFILE`",
        ),
    )
    plan_text = (ROOT / "THE-PLAN.md").read_text(encoding="utf-8")
    agents_text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    handover_text = (ROOT / "HANDOVER.md").read_text(encoding="utf-8")
    for stale in ("CANDIDATE COMPARISON PENDING", "candidate comparison pending"):
        if stale in plan_text:
            fail(f"THE-PLAN.md retains stale status {stale!r}")
    if "Performance-first minimal-capability research is the active design track" in agents_text:
        fail("agent instructions retain stale active-design-track status")
    for stale in (
        "Candidate B's bounded cross-project design research is active",
        "CANDIDATE B\n   CROSS-PROJECT DESIGN ACTIVE",
        "The active work has now moved to Candidate B.",
    ):
        if stale in agents_text or stale in plan_text or stale in handover_text:
            fail(f"status documents retain stale Candidate B status {stale!r}")
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
        / "CANDIDATE-B-ELEGANT-DESIGN.md",
        (
            "Candidate B Design Gate disposition: `B-REVISE`.",
            "`B-STRATA` has six closed and eight open rows.",
            "`B-GRAPHS` has six closed and eight open rows.",
            "Work stops at\nthis gate.",
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
    print("performance research status: Candidate B Design Gate complete at B-REVISE")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"performance research status verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
