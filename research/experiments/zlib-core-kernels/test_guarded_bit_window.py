#!/usr/bin/env python3
"""Focused tests for the compiler-triggered guarded bit-window experiment."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import re
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = HERE / "huffman_literals.wf"
DEMOC_PATH = ROOT / "prototype/democ/democ.py"
SOURCE_SHA256 = "de44aca1c03a889834a56f15138c4ebb924feaedabece766633f45fd73974847"

SPEC = importlib.util.spec_from_file_location("guarded_bit_window_democ", DEMOC_PATH)
assert SPEC is not None and SPEC.loader is not None
DEMOC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEMOC)


class GuardedBitWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE.read_text(encoding="utf-8")

    def test_source_is_unchanged(self) -> None:
        self.assertEqual(
            hashlib.sha256(SOURCE.read_bytes()).hexdigest(), SOURCE_SHA256
        )

    def test_flag_selects_certified_lowering_only(self) -> None:
        ordinary = DEMOC.compile_program(self.source)
        guarded = DEMOC.compile_program(
            self.source, experimental_guarded_bit_window=True
        )
        self.assertNotIn("EXPERIMENTAL guarded-bit-window certificate", ordinary)
        self.assertIn("EXPERIMENTAL guarded-bit-window certificate", guarded)
        self.assertIn("%bw_has_word = icmp uge i64 %bw_src_available, 8", guarded)
        self.assertIn("%bw_next_produced = add i64 %bw_produced, 6", guarded)
        self.assertIn("bw_tail_header:", guarded)

    def test_alpha_renamed_shape_is_certified(self) -> None:
        renamed = self.source
        for old, new in (
            ("symbol_count", "decoded_symbols"),
            ("input_pos", "source_cursor"),
            ("output_pos", "destination_cursor"),
            ("fixed_lencode", "literal_decode_table"),
        ):
            renamed = re.sub(rf"\b{old}\b", new, renamed)
        guarded = DEMOC.compile_program(
            renamed, experimental_guarded_bit_window=True
        )
        self.assertIn("EXPERIMENTAL guarded-bit-window certificate", guarded)
        self.assertIn("@__const_literal_decode_table", guarded)

    def assert_shape_rejected(self, source: str) -> None:
        with self.assertRaises(DEMOC.CheckError) as caught:
            DEMOC.compile_program(
                source, experimental_guarded_bit_window=True
            )
        self.assertEqual(caught.exception.rule, "EXPERIMENT-BIT-WINDOW")

    def test_mask_drift_fails_closed(self) -> None:
        self.assert_shape_rejected(self.source.replace("511_u64", "510_u64", 1))

    def test_refill_threshold_drift_fails_closed(self) -> None:
        old = "ige<u32>(bits, 9_u32)"
        self.assertIn(old, self.source)
        self.assert_shape_rejected(self.source.replace(old, "ige<u32>(bits, 8_u32)", 1))

    def test_literal_table_range_drift_fails_closed(self) -> None:
        # Packed {op=0,bits=8,val=256}: the source remains well-typed, but the
        # compiler may no longer remove the checked u32-to-u8 conversion arm.
        self.assert_shape_rejected(
            self.source.replace("5244928_u32", "16779264_u32", 1)
        )

    def test_literal_table_used_width_drift_fails_closed(self) -> None:
        # Packed {op=0,bits=0,val=80}: a zero drop would invalidate progress.
        self.assert_shape_rejected(
            self.source.replace("5244928_u32", "5242880_u32", 1)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
