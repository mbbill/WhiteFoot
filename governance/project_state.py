#!/usr/bin/env python3
"""Verify the repository's single-plan and design-package invariants."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROADMAP = Path("docs/roadmap.md")

RETIRED_ACTIVE_PATHS = (
    Path("HANDOVER.md"),
    Path("compiler/PLAN.md"),
    Path("compiler/sources.txt"),
    Path("prototype/democ/democ.py"),
    Path("optimizer-language-research/implementation/validation-harness-plan.md"),
    Path("tools/verify_performance_research_status.py"),
    Path(
        "optimizer-language-research/implementation/"
        "systems-performance-coverage/FOLLOW-UPS.md"
    ),
)


def roadmap_name(filename: str) -> bool:
    """Return whether a Markdown filename declares itself a plan or roadmap."""
    path = Path(filename)
    if path.suffix.lower() != ".md":
        return False
    tokens = re.split(r"[^a-z0-9]+", path.stem.lower())
    return "plan" in tokens or "roadmap" in tokens


def live_roadmaps(root: Path) -> list[Path]:
    """Find roadmap-shaped files without traversing historical evidence."""
    found: list[Path] = []
    for directory, child_directories, filenames in os.walk(root):
        relative_directory = Path(directory).relative_to(root)
        child_directories[:] = [
            child
            for child in child_directories
            if child not in {".git", "archive"} and not child.endswith(".alt")
        ]
        if any(part.endswith(".alt") for part in relative_directory.parts):
            child_directories.clear()
            continue
        for filename in filenames:
            relative_path = relative_directory / filename
            full_path = root / relative_path
            marked_canonical = False
            if full_path.suffix.lower() == ".md":
                marked_canonical = (
                    "Status: CANONICAL ROADMAP"
                    in full_path.read_text(encoding="utf-8")
                )
            if roadmap_name(filename) or marked_canonical:
                found.append(relative_path)
    return sorted(found)


def verify(root: Path) -> list[str]:
    errors: list[str] = []

    agents = root / "AGENTS.md"
    claude = root / "CLAUDE.md"
    if not agents.is_file():
        errors.append("missing AGENTS.md")
    if not claude.is_file():
        errors.append("missing CLAUDE.md")
    if (
        agents.is_file()
        and claude.is_file()
        and agents.read_bytes() != claude.read_bytes()
    ):
        errors.append("AGENTS.md and CLAUDE.md are not byte-identical")
    if agents.is_file():
        instructions = agents.read_text(encoding="utf-8")
        if "## Current focus" in instructions:
            errors.append("AGENTS.md retains a duplicate Current focus section")
        if "`docs/roadmap.md` is the sole source" not in instructions:
            errors.append("AGENTS.md omits the sole-roadmap authority statement")

    if not (root / CANONICAL_ROADMAP).is_file():
        errors.append(f"missing canonical roadmap {CANONICAL_ROADMAP}")
    else:
        roadmap = (root / CANONICAL_ROADMAP).read_text(encoding="utf-8")
        if "Status: CANONICAL ROADMAP" not in roadmap:
            errors.append("docs/roadmap.md omits its canonical-roadmap status")
        for phase in range(1, 8):
            if f"## Phase {phase}:" not in roadmap:
                errors.append(f"docs/roadmap.md omits authorized phase {phase}")

    extra_roadmaps = [
        path for path in live_roadmaps(root) if path != CANONICAL_ROADMAP
    ]
    if extra_roadmaps:
        rendered = ", ".join(str(path) for path in extra_roadmaps)
        errors.append(f"docs/roadmap.md is not the sole active roadmap: {rendered}")

    for path in RETIRED_ACTIVE_PATHS:
        if (root / path).exists():
            errors.append(f"retired active path still exists: {path}")

    return errors


def main() -> int:
    errors = verify(ROOT)
    if errors:
        print("project state verification failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        "project state: docs/roadmap.md is the sole active roadmap; "
        "agent instructions and retired-toolchain paths verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
