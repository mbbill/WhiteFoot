#!/usr/bin/env python3
"""Fail-closed tests for the opt-in periodic-copy lowering experiment."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "experiments" / "zlib-core-kernels" / "match_copy.wf"
DEMOC_PATH = Path(__file__).with_name("democ.py")
SPEC = importlib.util.spec_from_file_location("periodic_democ", DEMOC_PATH)
DEMOC = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(DEMOC)


def compile_experiment(source: str) -> str:
    return DEMOC.compile_program(source, periodic_copy_experiment=True)


class PeriodicCopyExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE.read_text(encoding="utf-8")

    def test_flag_is_required_and_checked_precondition_remains(self) -> None:
        ordinary = DEMOC.compile_program(self.source)
        experimental = compile_experiment(self.source)
        self.assertNotIn("@__wf_periodic_copy_u8_repeated", ordinary)
        self.assertEqual(
            experimental.count("@__wf_periodic_copy_u8_repeated"), 2
        )
        self.assertIn("store volatile i1", experimental)
        self.assertIn("call i64 @__wf_periodic_copy_u8_repeated", experimental)

    def test_alpha_renamed_canonical_source_is_recognized(self) -> None:
        names = set(re.findall(r"\blet\s+([A-Za-z_]\w*)", self.source))
        names.update(
            {
                "inflate_match_copy",
                "out",
                "seed_len",
                "distance",
                "match_len",
                "repeats",
                "matches",
                "bytes",
            }
        )
        renamed = self.source
        for index, name in enumerate(sorted(names, key=len, reverse=True)):
            renamed = re.sub(rf"\b{re.escape(name)}\b", f"alpha_{index}", renamed)
        llvm = compile_experiment(renamed)
        self.assertIn("call i64 @__wf_periodic_copy_u8_repeated", llvm)

    def test_changed_recurrence_is_not_recognized(self) -> None:
        changed = self.source.replace(
            "isub.wrap<u64>(out_pos, distance)",
            "isub.wrap<u64>(out_pos, seed_len)",
        )
        self.assertNotEqual(changed, self.source)
        llvm = compile_experiment(changed)
        self.assertNotIn("@__wf_periodic_copy_u8_repeated", llvm)

    def test_changed_precondition_is_not_recognized(self) -> None:
        changed = self.source.replace("32768_u64", "32767_u64", 1)
        self.assertNotEqual(changed, self.source)
        llvm = compile_experiment(changed)
        self.assertNotIn("@__wf_periodic_copy_u8_repeated", llvm)


if __name__ == "__main__":
    unittest.main()
