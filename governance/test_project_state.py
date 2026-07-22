#!/usr/bin/env python3
"""Tests for the single-roadmap repository invariant."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from project_state import verify


INSTRUCTIONS = """# Agents

`THE-PLAN.md` is the sole source for current status, execution order, and gates.
"""

ROADMAP = "\n".join(
    ["# THE PLAN", "", "Status: CANONICAL ROADMAP"]
    + [f"\n## Phase {phase}: test" for phase in range(1, 8)]
)


def make_root(path: Path) -> None:
    (path / "AGENTS.md").write_text(INSTRUCTIONS, encoding="utf-8")
    (path / "CLAUDE.md").write_text(INSTRUCTIONS, encoding="utf-8")
    (path / "THE-PLAN.md").write_text(ROADMAP, encoding="utf-8")
class ProjectStateTests(unittest.TestCase):
    def test_minimal_valid_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_root(root)
            self.assertEqual(verify(root), [])

    def test_second_marker_is_rejected_under_neutral_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_root(root)
            (root / "STATUS.md").write_text(
                "# Status\n\nStatus: CANONICAL ROADMAP\n", encoding="utf-8"
            )
            self.assertTrue(
                any("STATUS.md" in error for error in verify(root)),
                verify(root),
            )

    def test_plan_name_and_duplicate_focus_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_root(root)
            (root / "NEXT-PLAN.md").write_text("# Queue\n", encoding="utf-8")
            changed = INSTRUCTIONS + "\n## Current focus\n"
            (root / "AGENTS.md").write_text(changed, encoding="utf-8")
            (root / "CLAUDE.md").write_text(changed, encoding="utf-8")
            errors = verify(root)
            self.assertTrue(any("NEXT-PLAN.md" in error for error in errors), errors)
            self.assertTrue(any("Current focus" in error for error in errors), errors)

    def test_archive_and_rejected_alternative_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_root(root)
            archive = root / "archive"
            archive.mkdir()
            (archive / "ROADMAP.md").write_text("historical\n", encoding="utf-8")
            alternative = root / "mcts_mem" / "toolchain.alt"
            alternative.mkdir(parents=True)
            (alternative / "old-plan.md").write_text("rejected\n", encoding="utf-8")
            self.assertEqual(verify(root), [])


if __name__ == "__main__":
    unittest.main()
