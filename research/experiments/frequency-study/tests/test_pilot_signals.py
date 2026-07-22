#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import pilot_signals as ps


class PilotSignalTests(unittest.TestCase):
    def classes(self, source: str) -> list[str]:
        return [record["class"] for record in ps.analyze_source(source, "src/lib.rs")]

    def test_finds_candidate_and_expert_shapes(self) -> None:
        source = """
fn encode(out: &mut [u8], src: &[u8]) {
    for i in 0..src.len() {
        out[i] = src[i];
    }

    let mut total = 0u64;
    for &x in src {
        total = total.saturating_add(x as u64);
    }

    for (chunk, dst) in src.chunks_exact(3).zip(out.chunks_exact_mut(4)) {
        unsafe { *dst.get_unchecked_mut(0) = *chunk.get_unchecked(0); }
    }
}
"""
        records = ps.analyze_source(source, "src/lib.rs")
        classes = [record["class"] for record in records]
        self.assertEqual(classes.count(ps.INDEX_LOOP), 1)
        self.assertEqual(classes.count(ps.SCOPED_ALIAS), 1)
        self.assertEqual(classes.count(ps.SATURATING_RECURRENCE), 1)
        self.assertEqual(classes.count(ps.CHUNKS_EXACT), 2)
        self.assertEqual(classes.count(ps.ITERATOR_ZIP), 1)
        self.assertEqual(classes.count(ps.GET_UNCHECKED), 2)
        for record in records:
            self.assertEqual(record["file"], "src/lib.rs")
            self.assertIsInstance(record["line"], int)
            self.assertTrue(record["snippet"])
            self.assertTrue(record["reason"])
            self.assertEqual(record["label"], ps.LABEL)
            self.assertIs(record["proven_speedup"], False)

    def test_comments_and_strings_cannot_create_signals(self) -> None:
        source = r'''
// for i in 0..x.len() { y[i] = x[i]; }
/* fn fake(a: &[u8], b: &mut [u8]) {
     loop { acc = acc.saturating_add(1); }
   }
   /* .chunks_exact(4).zip(x).get_unchecked(0) */
*/
const NORMAL: &str = "for i in 0..x.len() { y[i] = x[i]; }";
const RAW: &str = r###"loop { acc = acc.saturating_add(1); }
    x.chunks_exact(4).zip(y).get_unchecked(0)"###;
const BYTE: &[u8] = b".chunks_exact(4)";
const C_STRING: &core::ffi::CStr = c".zip(";
'''
        self.assertEqual(ps.analyze_source(source, "src/lib.rs"), [])

    def test_index_guard_requires_index_access_in_same_loop(self) -> None:
        source = """
fn probes(x: &[u8]) {
    for i in 0..x.len() { consume(x); }
    consume(x[0]);
    let mut j = 0;
    while j < x.len() { consume(x[j]); j += 1; }
    let mut k = 0;
    while x.len() > k { consume(x[k]); k += 1; }
}
"""
        self.assertEqual(self.classes(source).count(ps.INDEX_LOOP), 2)

    def test_scoped_alias_needs_two_direct_slice_parameters_and_loop(self) -> None:
        source = """
fn one(a: &[u8]) { for x in a { consume(x); } }
fn no_loop(a: &[u8], b: &mut [u8]) { consume((a, b)); }
fn candidate<'a>(a: &'a [u8], b: &mut [u8]) {
    while ready() { consume((a, b)); }
}
"""
        self.assertEqual(self.classes(source).count(ps.SCOPED_ALIAS), 1)

    def test_saturating_add_must_be_loop_carried_assignment(self) -> None:
        source = """
fn probe(xs: &[u64]) {
    let mut acc = 0u64;
    acc = acc.saturating_add(1);
    for &x in xs {
        let acc = acc.saturating_add(x);
        consume(acc);
    }
    for &x in xs {
        acc = other.saturating_add(x);
    }
    for &x in xs {
        acc = acc.saturating_add(x);
    }
}
"""
        self.assertEqual(self.classes(source).count(ps.SATURATING_RECURRENCE), 1)

    def test_trait_impl_for_is_not_mistaken_for_a_loop(self) -> None:
        source = """
impl AddOne for Counter {
    fn add_one(&mut self) {
        let mut acc = self.value;
        acc = acc.saturating_add(1);
        self.value = acc;
    }
}
"""
        self.assertNotIn(ps.SATURATING_RECURRENCE, self.classes(source))

    def test_masking_preserves_real_source_location(self) -> None:
        source = '''/* decoy
for i in 0..x.len() { y[i] = x[i]; }
*/
const DECOY: &str = "acc = acc.saturating_add(x)";
fn actual(x: &[u8], y: &mut [u8]) {
    for i in 0..x.len() { y[i] = x[i]; }
}
'''
        records = ps.analyze_source(source, "src/lib.rs")
        index = next(record for record in records if record["class"] == ps.INDEX_LOOP)
        self.assertEqual(index["line"], 6)
        self.assertIn("for i", index["snippet"])

    def test_directory_scope_and_order_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src/z.rs").write_text("fn z() {}\n", encoding="utf-8")
            (root / "src/a.rs").write_text(
                "fn a(x: &[u8]) { for i in 0..x.len() { consume(x[i]); } }\n",
                encoding="utf-8",
            )
            for excluded in ("tests", "examples", "benches", "generated", "vendor", "target"):
                path = root / excluded
                path.mkdir()
                (path / "decoy.rs").write_text(
                    "fn x(a: &[u8], b: &[u8]) { loop {} }\n", encoding="utf-8"
                )
            member = root / "member/src"
            member.mkdir(parents=True)
            (member / "lib.rs").write_text(
                "fn m(xs: &[u64]) { let mut a=0; loop { a = a.saturating_add(xs[0]); } }\n",
                encoding="utf-8",
            )

            first = ps.scan_project(root)
            second = ps.scan_project(root)
            self.assertEqual(first, second)
            self.assertEqual(first["rust_file_count"], 3)
            self.assertEqual(
                [record["file"] for record in first["records"]],
                ["member/src/lib.rs", "src/a.rs"],
            )
            self.assertIn("production src/**/*.rs", first["scan_scope"]["included"])
            self.assertFalse(first["interpretation"]["proven_speedups"])

    def test_single_rust_file_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "standalone.rs"
            path.write_text("fn main() {}\n", encoding="utf-8")
            result = ps.scan_project(path)
            self.assertEqual(result["rust_file_count"], 1)
            self.assertEqual(result["candidate_count"], 0)

    def test_invalid_or_unsafe_input_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            invalid = root / "src/lib.rs"
            invalid.write_bytes(b"\xff")
            with self.assertRaises(ps.ScanError):
                ps.scan_project(root)

        with self.assertRaises(ps.ScanError):
            ps.scan_project("/definitely/not/a/real/pilot/path")
        with self.assertRaises(ps.ScanError):
            ps.analyze_source("/* never closed", "src/lib.rs")
        with self.assertRaises(ps.ScanError):
            ps.analyze_source('const X: &str = "never closed', "src/lib.rs")

    def test_cli_json_is_stable_and_errors_emit_no_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "probe.rs"
            path.write_text("fn main() {}\n", encoding="utf-8")
            outputs = []
            for _ in range(2):
                stdout = StringIO()
                stderr = StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    status = ps.main([str(path)])
                self.assertEqual(status, 0)
                self.assertEqual(stderr.getvalue(), "")
                json.loads(stdout.getvalue())
                outputs.append(stdout.getvalue())
            self.assertEqual(outputs[0], outputs[1])

            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = ps.main([str(path.with_name("missing.rs"))])
            self.assertEqual(status, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("error", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
