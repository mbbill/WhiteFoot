#!/usr/bin/env python3
"""Focused regressions for the Phase-5 successor protected-surface census."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import census_support as support
import protected_surface_census as census
import source_surface_scan as source_scan


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REPORT = HERE / census.REPORT_NAME


class CensusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = census.build_report(ROOT)

    def test_exact_protected_counts(self) -> None:
        conformance = self.report["conformance"]
        self.assertEqual(conformance["manifest_records"], 307)
        self.assertEqual(conformance["protected_source_files"], 293)
        self.assertEqual(conformance["rejects"], 152)
        self.assertEqual(conformance["frontend_only_rejects"], 21)
        self.assertEqual(conformance["semantic_rejects_requiring_unchanged_replay"], 131)

    def test_corrected_namespaces_preserve_required_prelude_equalities(self) -> None:
        r01 = self.report["r01"]
        self.assertEqual(
            r01["prelude_cross_namespace_equalities_required"],
            ["NarrowError", "Overflow"],
        )
        self.assertIn("Overflow", r01["prelude_by_namespace"]["nominal"])
        self.assertIn("Overflow", r01["prelude_by_namespace"]["constructor"])
        self.assertEqual(r01["protected_source_prelude_collisions"], [])
        self.assertEqual(
            r01["source_namespace_collisions"],
            [
                {
                    "declarations": [
                        {"kind": "enum-variant", "line": 2},
                        {"kind": "enum-variant", "line": 6},
                    ],
                    "namespace": "constructor",
                    "path": "conformance/cases/type6-neg-dup-variant.wf",
                    "spelling": "Dup",
                }
            ],
        )

    def test_r02_exact_difference_and_zero_bindings(self) -> None:
        r02 = self.report["r02"]
        self.assertEqual(r02["table_dotless_count"], 51)
        self.assertEqual(r02["listed_dotless_count"], 20)
        self.assertEqual(r02["table_only_count"], 31)
        self.assertEqual(r02["conformance_declaration_bindings"], [])
        self.assertEqual(r02["codegen_declaration_bindings"], [])
        self.assertEqual(
            r02["table_only_use_case_ids"], sorted(census.EXPECTED_TABLE_ONLY_USE_CASES)
        )
        reference = r02["protected_reference_semantic_surface"]
        self.assertEqual(
            reference["ProgramLayer.test_form3_every_op1_reserved_identifier_rejected"][
                "binding_shapes"
            ],
            ["function"],
        )
        self.assertEqual(
            reference["ProgramLayer.test_form3_reservation_covers_every_binding_shape"][
                "binding_shapes"
            ],
            list(census.REFERENCE_RESERVATION_BINDING_SHAPES),
        )

    def test_protected_intersections_are_exact(self) -> None:
        protected = self.report["protected_intersections"]
        self.assertEqual(protected["oracle_digest_entries"], 3)
        self.assertEqual(len(protected["oracle_files"]), 2)
        self.assertEqual(len(protected["reference_methods"]), 8)

    def test_scanner_keeps_typeid_namespaces_separate(self) -> None:
        source = b"""enum Overflow {
  Overflow();
}
struct Point {
  x: i32;
}
contract Point {
}
fn poly<T, const n: u64>(x: own T) -> own T pure {
  return x;
}
"""
        items, generics = source_scan.declarations(
            source_scan.scan_tokens(source, "fixture")
        )
        by_namespace = {
            namespace: {item.spelling for item in items if item.namespace == namespace}
            for namespace in ("nominal", "constructor", "contract")
        }
        self.assertEqual(by_namespace["nominal"], {"Overflow", "Point"})
        self.assertEqual(by_namespace["constructor"], {"Overflow", "Point"})
        self.assertEqual(by_namespace["contract"], {"Point"})
        self.assertEqual([generic.spelling for generic in generics], ["T"])
        self.assertEqual(source_scan.find_collisions("fixture.wf", items), [])

    def test_generic_shadow_scan_checks_live_nominal_and_redeclaration(self) -> None:
        source = b"""enum T {
  One();
}
fn poly<T, T>(x: own T) -> own T pure {
  return x;
}
"""
        items, generics = source_scan.declarations(
            source_scan.scan_tokens(source, "fixture")
        )
        collisions = source_scan.generic_shadow_collisions(
            "fixture.wf", items, generics, frozenset()
        )
        self.assertEqual(len(collisions), 2)
        self.assertEqual(
            collisions[0]["reasons"], ["live-source-nominal-shadow"]
        )
        self.assertEqual(
            collisions[1]["reasons"],
            ["same-generic-list-redeclaration", "live-source-nominal-shadow"],
        )

        later_nominal = b"""fn poly<T>(x: own T) -> own T pure {
  return x;
}
enum T {
  One();
}
"""
        later_items, later_generics = source_scan.declarations(
            source_scan.scan_tokens(later_nominal, "later-fixture")
        )
        self.assertEqual(
            source_scan.generic_shadow_collisions(
                "later-fixture.wf", later_items, later_generics, frozenset()
            ),
            [],
        )

    def test_r01_scans_codegen_as_well_as_conformance(self) -> None:
        r01 = self.report["r01"]
        self.assertEqual(r01["codegen_namespace_collisions"], [])
        self.assertEqual(r01["codegen_prelude_collisions"], [])
        self.assertEqual(r01["codegen_generic_shadow_collisions"], [])
        self.assertEqual(
            self.report["inputs"]["codegen_source_inventory"]["source_files"], 95
        )
        self.assertEqual(
            self.report["inputs"]["codegen_source_inventory"][
                "r01_r02_scanned_files"
            ],
            95,
        )

    def test_scan_coverage_rejects_one_skipped_codegen_path(self) -> None:
        expected = ["codegen-corpus/a.wf", "codegen-corpus/b.wf"]
        census.require_scan_coverage(expected, expected, "fixture")
        with self.assertRaisesRegex(census.CensusError, "scan coverage drift"):
            census.require_scan_coverage(expected[:-1], expected, "fixture")

    def test_scanner_ignores_documentation_strings(self) -> None:
        source = b'''fn main() -> own unit pure {
  doc "fn iand(x: own u64) and enum Fake { Fake(); }";
  return unit;
}
'''
        tokens = source_scan.scan_tokens(source, "fixture")
        items, _ = source_scan.declarations(tokens)
        self.assertEqual([(item.kind, item.spelling) for item in items], [])
        self.assertEqual(
            source_scan.table_only_bindings("fixture.wf", tokens, frozenset({"iand"})),
            [],
        )

    def test_binding_scan_covers_ident_and_region_shapes(self) -> None:
        source = b"""fn iand(x: own u64) -> own unit pure {
  region 'fneg {
    let buffer_new: own u64 = x;
  }
  return unit;
}
"""
        hits = source_scan.table_only_bindings(
            "fixture.wf",
            source_scan.scan_tokens(source, "fixture"),
            frozenset({"iand", "fneg", "buffer_new"}),
        )
        self.assertEqual({hit["spelling"] for hit in hits}, {"iand", "fneg", "buffer_new"})

    def test_strict_json_rejects_duplicate_keys_and_nonfinite_values(self) -> None:
        with self.assertRaisesRegex(support.CensusError, "duplicate JSON key"):
            support.strict_json(b'{"x":1,"x":2}', "fixture")
        with self.assertRaisesRegex(support.CensusError, "non-finite"):
            support.strict_json(b'{"x":NaN}', "fixture")
        with self.assertRaisesRegex(support.CensusError, "floats"):
            support.strict_json(b'{"x":1.5}', "fixture")
        with self.assertRaisesRegex(support.CensusError, "UTF-8"):
            support.strict_json(b"\xff", "fixture")

    def test_exact_identity_drift_fails_closed(self) -> None:
        with self.assertRaisesRegex(support.CensusError, "identity drift"):
            support.require_digest(b"changed", "0" * 64, "fixture")

    def test_census_binds_exact_proposal_and_candidate_transition(self) -> None:
        specification = (ROOT / census.SPEC_REL).read_bytes()
        proposal = (ROOT / census.PROPOSAL_REL).read_bytes()
        candidate = (ROOT / census.CANDIDATE_REL).read_bytes()
        census.validate_candidate_transition(specification, proposal, candidate)
        with self.assertRaisesRegex(support.CensusError, "identity drift"):
            census.validate_candidate_transition(
                specification, proposal + b"\n", candidate
            )
        with self.assertRaisesRegex(support.CensusError, "identity drift"):
            census.validate_candidate_transition(
                specification, proposal, candidate[:-1] + b"X"
            )

    def test_guarded_manifest_digest_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case_root = root / census.CONFORMANCE_REL
            case_root.mkdir(parents=True)
            (case_root / "case.wf").write_text("fn main() {}\n", encoding="utf-8")
            manifest = b'{"id":"case","rules":[],"expect":{"kind":"accept"},"status":"pending"}\n'
            with self.assertRaisesRegex(support.CensusError, "guarded conformance record drift"):
                support.load_manifest(
                    root,
                    census.CONFORMANCE_REL,
                    manifest,
                    {"case": "0" * 64},
                )

    def test_inventory_digest_changes_with_source_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "case.wf"
            path.write_bytes(b"one\n")
            before = support.inventory_digest(root, [path])
            path.write_bytes(b"two\n")
            after = support.inventory_digest(root, [path])
            self.assertNotEqual(before, after)

    def test_checked_in_report_is_canonical_and_current(self) -> None:
        expected = support.canonical_bytes(self.report)
        self.assertEqual(REPORT.read_bytes(), expected)
        self.assertEqual(json.loads(expected), self.report)

    def test_cli_check(self) -> None:
        result = subprocess.run(
            [sys.executable, str(HERE / "protected_surface_census.py"), "--check"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
