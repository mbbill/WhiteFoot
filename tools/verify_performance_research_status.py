#!/usr/bin/env python3
"""Verify the active B-Strata decisive-research status."""

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
        "B-Strata is the sole active minimal systems-capability architecture",
        "CANDIDATE-B-STRATA-DECISIVE-PLAN.md",
        "outcome must be `STRATA-YES`",
        "or `STRATA-NO` with an irreducible reason",
        "Do not pivot\n  to Candidate C",
        "A paper YES is required before safety modeling",
        "model YES before the smallest preregistered prototypes",
        "No production language",
        "D-2/P-1 fail-closed.",
    )
    require(ROOT / "AGENTS.md", status_phrases)
    require(
        ROOT / "THE-PLAN.md",
        (
            "B-STRATA\n   DECISIVE TRACK ACTIVE",
            "`STRATA-YES` with a normalized closed core",
            "or `STRATA-NO` with the irreducible safety",
            "Candidate C is not a fallback",
            "complete across fourteen\n   operations and four pinned source revisions",
            "`B-STRATA` six closed and eight open rows",
            "`B-GRAPHS` six closed and\n   eight open rows",
            "CANDIDATE-B-ELEGANT-DESIGN-PLAN.md",
            "CANDIDATE-B-STRATA-DECISIVE-PLAN.md",
            "Phase 1 first normalizes the eight",
            "only a paper YES and model YES authorize",
            "Sparse Repair Gate selects `SR-PROFILE`",
            "Exact D-2/P-1 remain fail-closed",
        ),
    )
    require(
        ROOT / "HANDOVER.md",
        (
            "Current B-Strata-only decision",
            "B-Strata as the sole capability architecture",
            "work must end in `STRATA-YES`",
            "Another open-ended revision recommendation is not an allowed final result",
            "Paper closure precedes a hostile",
            "final `STRATA-YES` returns an exact landing proposal",
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
        "Candidate B's bounded cross-project design research stopped",
        "CANDIDATE B\n   CROSS-PROJECT DESIGN ACTIVE",
        "The active work has now moved to Candidate B.",
    ):
        if stale in agents_text or stale in plan_text or stale in handover_text:
            fail(f"status documents retain stale Candidate B status {stale!r}")
    if "## 0. Current correction — read this first" in handover_text:
        fail("HANDOVER.md retains a superseded second read-this-first section")
    require(
        ROOT
        / "optimizer-language-research"
        / "implementation"
        / "minimal-systems-capability"
        / "CANDIDATE-B-STRATA-DECISIVE-PLAN.md",
        (
            "controlling plan for the owner-selected B-Strata-only research track",
            "`STRATA-YES`",
            "`STRATA-NO`",
            "The existing eight strata are analytical jobs",
            "Every rule must preserve one common resource-conservation invariant",
            "`K1 ROOTED-PLACE`",
            "`K2 SEALED-STATE`",
            "`K3 LINEAR-STEP`",
            "authority-origin ledger with no cycles",
            "No leaf may directly mint `Quiescent`, `Stable`, `RepairComplete`",
            "Front-load four verdict-forcing definitions",
            "one semantic-repair budget",
            "The route matrix has exactly fourteen rows",
            "stable `outcome_id` rows",
            "general operational semantics",
            "Bounded execution and negative corpora\nsupport the general proofs but never substitute for them",
            "decisive cross-project vertical evidence",
            "The operation-to-entrypoint map is exact",
            "its own quantitative non-inferiority test passes",
            "The goal may not\nstop at unexplained evidence insufficiency.",
            "CANDIDATE-B-STRATA-PRODUCTION-LANDING-PROPOSAL.md",
            "Do not use a broad brainstorming or mind-expansion workflow.",
            "The work is complete only at `STRATA-YES` or `STRATA-NO`.",
        ),
    )
    require(
        ROOT / "optimizer-language-research" / "notes" / "user-directives.md",
        (
            "D14 B-Strata decisive ruling",
            "selected B-Strata as the sole architecture",
            "is exactly `STRATA-YES` or `STRATA-NO`",
        ),
    )
    require(
        ROOT / "mcts_mem" / "xlang.md",
        (
            "B-Strata is now the sole capability architecture under development",
            "forced `STRATA-YES` or `STRATA-NO` verdict",
            "Candidate C is not a fallback",
        ),
    )
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
    print("performance research status: B-Strata decisive track active at Phase 1")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"performance research status verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
