#!/usr/bin/env python3
"""Tests for the isolated successor-candidate generator."""

from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

import generate_candidate as generator


class CandidateGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = generator.DEFAULT_BASE.read_bytes()
        cls.proposal = generator.DEFAULT_PROPOSAL.read_bytes()

    def test_pinned_base_hash(self) -> None:
        self.assertEqual(generator.sha256(self.base), generator.BASE_SHA256)

    def test_pinned_full_candidate_identity(self) -> None:
        candidate, _ = generator.build_candidate(self.base, self.proposal)
        self.assertEqual(len(candidate), generator.EXPECTED_CANDIDATE_BYTES)
        self.assertEqual(
            generator.sha256(candidate), generator.EXPECTED_CANDIDATE_SHA256
        )

    def test_candidate_blocks_and_source_anchors_are_unique(self) -> None:
        proposal = self.proposal.decode("utf-8")
        for name in ("HEADER", "TYPE_6", "OP_1_NAMES", "DIAG_1_TAIL"):
            block = generator.candidate_block(proposal, name)
            self.assertTrue(block.strip())
        candidate, edits = generator.build_candidate(self.base, self.proposal)
        self.assertEqual(
            [edit.name for edit in edits],
            [
                "HEADER",
                "TYPE_6",
                "OP_1_NAMES",
                "DIAG_1_TAIL",
                "FN4_VERSION_1",
                "FN4_VERSION_2",
                "FN4_VERSION_3",
            ],
        )
        self.assertIn(b"# Kernel Specification v0.10\n", candidate)

    def test_only_declared_blocks_change(self) -> None:
        candidate, edits = generator.build_candidate(self.base, self.proposal)
        self.assertEqual(generator.reverse_allowed_edits(candidate, edits), self.base)

    def test_output_is_deterministic(self) -> None:
        first, first_edits = generator.build_candidate(self.base, self.proposal)
        second, second_edits = generator.build_candidate(self.base, self.proposal)
        self.assertEqual(first, second)
        self.assertEqual(first_edits, second_edits)
        self.assertEqual(generator.sha256(first), generator.sha256(second))

    def test_changed_base_is_rejected_before_editing(self) -> None:
        changed = self.base + b"\n"
        with self.assertRaisesRegex(generator.CandidateError, "base SHA-256 mismatch"):
            generator.build_candidate(changed, self.proposal)

    def test_duplicate_anchor_is_rejected(self) -> None:
        with self.assertRaisesRegex(generator.CandidateError, "expected one anchor"):
            generator.replace_unique("x x", "x", "y", "duplicate")

    def test_write_and_check_modes_agree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "candidate.md"
            common = [
                "--base",
                str(generator.DEFAULT_BASE),
                "--proposal",
                str(generator.DEFAULT_PROPOSAL),
                "--output",
                str(output),
            ]
            self.assertEqual(generator.main(common), 0)
            first = output.read_bytes()
            self.assertEqual(generator.main([*common, "--check"]), 0)
            self.assertEqual(output.read_bytes(), first)

    def test_protected_operation_table_is_byte_identical(self) -> None:
        candidate, _ = generator.build_candidate(self.base, self.proposal)
        base_text = self.base.decode("utf-8")
        candidate_text = candidate.decode("utf-8")
        table_start = "| op | domain | signature | effects |"
        paragraph = "An operation name is an OPNAME"
        base_table = base_text[base_text.index(table_start):base_text.index(paragraph)]
        candidate_end = candidate_text.index("Let `DotlessOperationNames`")
        candidate_table = candidate_text[candidate_text.index(table_start):candidate_end]
        self.assertEqual(candidate_table, base_table)

    def test_hostile_language_corrections_are_pinned(self) -> None:
        candidate, _ = generator.build_candidate(self.base, self.proposal)
        text = candidate.decode("utf-8")
        required = (
            "one declaration event that adds one nominal-type entry and one constructor entry",
            "`cvalue` IDENT admits only an earlier named const",
            "an earlier binder in the same arm list",
            "citing exactly FORM-3",
            "subtoken_ordinal",
            "| REGIONID use | OWN-3 |",
            "foreign-variant relation cites TYPE-6",
            "OWN-3 requires every REGIONID declaration to be unique",
            "An OWN-3 repeated-region payload is `(spelling, conflicting_region_origin)`",
            "The dependent-declaration carriers are exactly",
            "none enters a resolver lookup inventory",
            "this X09/U18 pair is the only same-token overlap",
            "the leading TYPEID of `arm` admits only enum-variant",
            "PRE-1 contributes exactly twenty-four declaration records",
            "semantic diagnostic selection first runs the early FN-8 structural-admission pass",
            "the two `cvt` rows therefore belong to one `cvt` family",
            "not an external terminal predicate such as `literal`",
            "only entries belonging to its declaration-owner chain",
            "FN-3 and FORM-5, not lexical resolution, later require its numeric bound",
        )
        for clause in required:
            self.assertIn(clause, text)
        self.assertNotIn("Decision 7", text)
        self.assertNotIn("U05", text)
        self.assertNotIn("a LABEL is visible but its loop does not lexically enclose", text)
        self.assertNotIn("explicit GRAM-10 exception", text)

    def test_resource_reconciliation_is_pinned(self) -> None:
        proposal = self.proposal.decode("utf-8")
        required = (
            "15. `max_work`",
            "11. `max_diagnostic_origins`",
            "12. `max_diagnostic_paths`",
            "13. `max_diagnostic_path_components`",
            "twenty-four PRE-1 declaration records",
            "contributes exactly eighteen lookup records",
            "eighty-three distinct operation-family spellings",
            "fifty-six reservation records",
            "exact `OrderingScratch` capacity is the already represented",
            "one fixed bottom-up stable merge engine",
            "`AllocationFailure { storage, requested_elements }`",
            "`Layout::array::<Element>(count)`",
            "`try_reserve_exact(count)`",
            "`Layout::array::<DiagnosticIssueElement>(count)`",
            "is invocation identity, built-in identity",
        )
        for clause in required:
            self.assertIn(clause, proposal)
        self.assertNotIn("`StorageUnavailable { storage, requested }`", proposal)

    def test_final_fn8_and_resource_contract_closures_are_pinned(self) -> None:
        candidate, _ = generator.build_candidate(self.base, self.proposal)
        candidate_text = candidate.decode("utf-8")
        proposal = self.proposal.decode("utf-8")
        candidate_required = (
            "complete checked half-open source extent",
            "An empty or all-let block missing its final check uses `SourceNode`",
            "No declaration or use role inside an inadmissible block is classified or counted",
            "Only complete unit-wide FN-8 admission permits role classification",
        )
        proposal_required = (
            "The read-only structural preflight has two fixed subpasses",
            "the resolver skips\nthe counting subpass",
            "one preflight syntax element is exactly one",
            "checked-add one to the current `u64` work count",
            "The resolver lookup inventory is one flat vector in lookup-key order",
            "appends complete entries to the already reserved `LookupEntries` vector",
            "The grammar bounds that chain at two",
            "greatest visibility start not\nafter the use",
            "`O((D + U) log(D + 1) + B + Q)`",
            "insertion sort is permitted",
            "Before the final lookup-key ordering",
            "Declaration inventory then processes declaration events directly",
            "whole-\nunit source function",
            "one work unit\nbefore every byte pair examined",
            "a final admitted\nordinary let selects the block",
            "compiled immutable flat vector already sorted",
            "order `Prelude`, `Operations`, `Reservations`",
            "One derived-only member follows: `DiagnosticIssueElements`",
            "SourceIssue(ResolutionRejectedUnit)",
            "one fixed `IssueHeader`; one `OriginDescriptor`",
            "`FinalizeStorage::MixedElements`",
            "`Layout::array::<MixedElement>(count)`",
            "`AllocationFailure { storage: MixedElements, requested_elements }`",
            "length to `u64` is `NodePathDepth`; every checked origin",
            "`max_scope_depth` is the maximum",
            "`max_ancestry_steps` counts exactly one",
            "does not scan a matched entry",
            "the origin iterator runs exactly twice",
        )
        for clause in candidate_required:
            self.assertIn(clause, candidate_text)
        for clause in proposal_required:
            self.assertIn(clause, proposal)
        self.assertNotIn(
            "Production-node coverage records are counted even\ninside an inadmissible block",
            proposal,
        )
        self.assertNotIn("inventories are flat\nvectors sorted by the same", proposal)
        self.assertNotIn("`M = max(N, lookup_entries)`", proposal)
        self.assertNotIn("checked `2 * M`", proposal)
        self.assertNotIn("Scope walking separately", proposal)
        self.assertNotIn("the sole first-\nfailure payload scan", proposal)
        self.assertNotIn("and exact origin counts", proposal)


if __name__ == "__main__":
    unittest.main()
