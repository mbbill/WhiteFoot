"""Tests for both independent diagnostic-order evidence models."""

from __future__ import annotations

import ast
import unittest
from unittest import mock
from pathlib import Path

import model_ledger
import model_relational
import run as evidence_run
from cases import (
    all_cases,
    case as evidence_case,
    clone,
    invalid_child_scope_case,
    resource_case,
)
from report import reports_equal, semantic_projection
from schema import SchemaError, validate_case


_EXPECTED_PROFILE_ORDER = (
    "declarations",
    "scopes",
    "scope_depth",
    "declaration_events",
    "lexical_uses",
    "deferred_uses",
    "spelling_bytes",
    "lookup_entries",
    "ancestry_steps",
    "node_path_depth",
    "diagnostic_origins",
    "diagnostic_paths",
    "diagnostic_path_components",
    "coverage_records",
    "work",
)


class EvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cases = {item["name"]: item for item in all_cases()}

    def reports(self, name: str) -> tuple[dict, dict]:
        case = self.cases[name]
        return model_ledger.run(case), model_relational.run(case)

    def agreed(self, name: str) -> dict:
        left, right = self.reports(name)
        self.assertTrue(reports_equal(left, right), name)
        return left

    def test_every_named_case_agrees(self) -> None:
        for name in self.cases:
            with self.subTest(name=name):
                self.agreed(name)

    def test_every_work_boundary_has_the_same_complete_report(self) -> None:
        for name, base in self.cases.items():
            baseline = model_ledger.run(base)
            for maximum in range(baseline["resources"]["work"] + 1):
                with self.subTest(name=name, maximum=maximum):
                    constrained = clone(base)
                    constrained["limits"]["work"] = maximum
                    left = model_ledger.run(constrained)
                    right = model_relational.run(constrained)
                    self.assertTrue(reports_equal(left, right))

    def test_canonical_report_matches_the_commit_bound_freeze(self) -> None:
        case_count, digest = evidence_run.agreed_report_digest()
        self.assertEqual(case_count, 77)
        self.assertEqual(digest, evidence_run.FROZEN_REPORT_SHA256)

    def test_models_do_not_import_each_other_or_case_semantics(self) -> None:
        root = Path(__file__).parent
        for filename in ("model_ledger.py", "model_relational.py"):
            tree = ast.parse((root / filename).read_text(encoding="utf-8"))
            imports = {
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            }
            imports.update(
                node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
            )
            self.assertFalse({"model_ledger", "model_relational", "cases", "report"} & imports)

    def test_pre1_same_spelling_cross_domain_is_accepted(self) -> None:
        report = self.agreed("pre1_cross_domain")
        self.assertEqual(report["status"], "complete")
        overflow = [item["domain"] for item in report["bindings"] if item["spelling"] == "Overflow"]
        narrow = [item["domain"] for item in report["bindings"] if item["spelling"] == "NarrowError"]
        self.assertEqual(overflow, ["nominal", "constructor"])
        self.assertEqual(narrow, ["nominal", "constructor"])

    def test_struct_is_one_declaration_with_two_binding_entries(self) -> None:
        report = self.agreed("struct_dual_entry")
        pair = [item for item in report["bindings"] if item["decl_id"] == "pair"]
        self.assertEqual([item["domain"] for item in pair], ["nominal", "constructor"])
        targets = {item["domain"]: item["target_decl_id"] for item in report["resolutions"]}
        self.assertEqual(targets, {"nominal": "pair", "constructor": "pair"})

    def test_inventory_outranks_earlier_resolution_failure(self) -> None:
        report = self.agreed("inventory_before_resolution")
        self.assertEqual(
            (report["status"], report["phase"], report["rule"], report["event_id"], report["domain"]),
            ("source_issue", "inventory", "TYPE-6", "d_box_variant", "constructor"),
        )

    def test_fn8_admission_precedes_and_suppresses_child_roles(self) -> None:
        report = self.agreed("fn8_structural_issue_suppresses_child_roles")
        self.assertEqual(
            (
                report["status"],
                report["phase"],
                report["rule"],
                report["reason"],
                report["event_id"],
                report["event_key"],
            ),
            (
                "source_issue",
                "structural_admission",
                "FN-8",
                "invalid_entry",
                "requires-bad",
                {
                    "source": 0,
                    "start": 20,
                    "end": 21,
                    "path": [0, 0],
                    "role": 0,
                    "subtoken": 0,
                },
            ),
        )
        self.assertEqual(
            {
                name: report["resources"][name]
                for name in (
                    "declarations",
                    "declaration_events",
                    "lexical_uses",
                    "deferred_uses",
                    "coverage_records",
                )
            },
            {
                "declarations": 0,
                "declaration_events": 0,
                "lexical_uses": 0,
                "deferred_uses": 0,
                "coverage_records": 0,
            },
        )

    def test_visibility_start_end_and_whole_unit_function(self) -> None:
        before = self.agreed("constructor_before_visibility_start")
        self.assertEqual((before["rule"], before["reason"]), ("TYPE-6", "outside_visibility"))
        after = self.agreed("scope_end_is_exclusive")
        self.assertEqual((after["rule"], after["reason"]), ("TYPE-5", "outside_visibility"))
        whole = self.agreed("whole_unit_function_visibility")
        self.assertEqual(whole["status"], "complete")
        self.assertEqual(whole["resolutions"][0]["target_decl_id"], "function_f")

    def test_lookup_requires_an_admissible_declaration_class(self) -> None:
        local = self.agreed("local_is_not_function")
        self.assertEqual(
            (local["rule"], local["reason"], local["available_classes"]),
            ("OP-1", "inadmissible_declaration_class", ["value"]),
        )
        constant = self.agreed("constant_is_not_function")
        self.assertEqual(
            (constant["rule"], constant["reason"], constant["available_classes"]),
            ("OP-1", "inadmissible_declaration_class", ["named-const"]),
        )
        numeric = self.agreed("nominal_is_not_numeric_identity_parameter")
        self.assertEqual(
            (numeric["rule"], numeric["reason"], numeric["available_classes"]),
            ("FORM-5", "inadmissible_declaration_class", ["nominal-type"]),
        )
        arm = self.agreed("struct_is_not_arm_constructor")
        self.assertEqual(
            (arm["rule"], arm["reason"], arm["available_classes"]),
            ("TYPE-6", "inadmissible_declaration_class", ["struct-constructor"]),
        )

    def test_canonical_key_orders_source_path_role_and_subtoken(self) -> None:
        cross = self.agreed("cross_source_order")
        self.assertEqual(cross["event_id"], "u_source_zero")
        path = self.agreed("node_path_prefix_order")
        self.assertEqual(path["event_id"], "u_short_path")
        role = self.agreed("role_and_subtoken_order")
        self.assertEqual(role["event_id"], "u_subtoken_zero")

    def test_generic_zero_retains_embedded_type_subtoken(self) -> None:
        report = self.agreed("generic_zero_subtoken")
        resolution = report["resolutions"][0]
        self.assertEqual(resolution["surface"], "0_T")
        self.assertEqual((resolution["event_key"]["start"], resolution["event_key"]["end"]), (32, 33))
        self.assertEqual(resolution["event_key"]["subtoken"], 1)
        self.assertEqual(resolution["target_decl_id"], "type_t")
        overlap = self.agreed("law_zero_role_overlap")
        self.assertEqual(overlap["deferred"][0]["event_key"]["subtoken"], 0)
        self.assertEqual(
            (overlap["deferred"][0]["event_key"]["start"], overlap["deferred"][0]["event_key"]["end"]),
            (30, 33),
        )
        self.assertEqual(overlap["resolutions"][0]["event_key"]["subtoken"], 1)
        self.assertEqual(
            (overlap["resolutions"][0]["event_key"]["start"], overlap["resolutions"][0]["event_key"]["end"]),
            (32, 33),
        )

    def test_u18_resolution_does_not_check_the_numeric_bound(self) -> None:
        unbound = self.agreed("u18_unbound_type_parameter")
        self.assertEqual(unbound["status"], "complete")
        self.assertEqual(unbound["resolutions"][0]["target_decl_id"], "unbound_t")

        wrong_bound = self.agreed("u18_wrong_bound_type_parameter")
        self.assertEqual(wrong_bound["status"], "complete")
        self.assertEqual(wrong_bound["resolutions"][-1]["target_decl_id"], "display_t")
        declaration = next(
            event
            for event in self.cases["u18_wrong_bound_type_parameter"]["events"]
            if event.get("decl_id") == "display_t"
        )
        self.assertEqual(declaration["type_bound"], "Display")

    def test_protected_rule_attribution_is_role_specific(self) -> None:
        own3 = self.agreed("own3_signature_region")
        self.assertEqual((own3["rule"], own3["event_id"]), ("OWN-3", "u_missing_region"))
        type5 = self.agreed("type5_requires_local_outside")
        self.assertEqual((type5["rule"], type5["event_id"]), ("TYPE-5", "u_req_after"))
        gram10 = self.agreed("gram10_deferred_roles")
        self.assertEqual([item["rule"] for item in gram10["deferred"]], ["GRAM-10"] * 2)
        freshness = self.agreed("gram10_binder_freshness_inventory")
        self.assertEqual(
            (freshness["phase"], freshness["rule"], freshness["reason"], freshness["event_id"]),
            ("inventory", "GRAM-10", "binder_collides_arm_entry", "d_match_binder"),
        )
        equals_field = self.agreed("gram10_binder_equals_field")
        self.assertEqual(
            (equals_field["rule"], equals_field["reason"], equals_field["event_id"]),
            ("GRAM-10", "binder_equals_written_field", "d_equal_binder"),
        )
        duplicate = self.agreed("gram10_duplicate_binder_in_arm")
        self.assertEqual(
            (duplicate["rule"], duplicate["reason"], duplicate["event_id"]),
            ("GRAM-10", "duplicate_match_binder", "d_later_binder"),
        )
        reserved = self.agreed("form3_reserved_binder_precedence")
        self.assertEqual(
            (reserved["rule"], reserved["reason"], reserved["event_id"]),
            ("FORM-3", "reserved_name", "d_reserved_binder"),
        )

    def test_foreign_variant_constructor_resolves_before_typed_relation(self) -> None:
        report = self.agreed("foreign_variant_relation_deferred")
        self.assertEqual(report["resolutions"][0]["target_decl_id"], "variant_b")
        self.assertEqual(report["deferred"][0]["rule"], "TYPE-6")

    def test_operations_and_structured_reservations_are_distinct(self) -> None:
        operations = self.agreed("operation_targets")
        self.assertEqual(
            [(item["target_decl_id"], item["target_kind"]) for item in operations["resolutions"]],
            [("operation:39", "operation"), ("operation:3", "operation")],
        )
        self.assertEqual(operations["resources"]["lookup_entries"], 2)
        mode = self.agreed("mode_word_is_not_operation")
        self.assertEqual((mode["rule"], mode["reason"]), ("OP-1", "absent_binding"))
        region = self.agreed("normalized_region_reservation")
        self.assertEqual(
            region["reservation"],
            {
                "spelling": "len",
                "declaration_role": "region",
                "reserved_class": "dotless_operation",
                "inventory_ordinal": 39,
            },
        )
        binder = self.agreed("form3_reserved_binder_precedence")
        self.assertEqual(binder["reservation"]["reserved_class"], "dotless_operation")

    def test_pre1_struct_collision_retains_both_domain_origins(self) -> None:
        report = self.agreed("pre1_struct_dual_conflict")
        self.assertEqual(report["rule"], "TYPE-6")
        self.assertEqual(
            [item["domain"] for item in report["conflicts"]],
            ["nominal", "constructor"],
        )
        self.assertEqual(
            [item["conflicting_origin"]["decl_id"] for item in report["conflicts"]],
            ["prelude_overflow_type", "prelude_overflow_variant"],
        )
        self.assertEqual(report["resources"]["diagnostic_paths"], 1)
        self.assertEqual(report["resources"]["diagnostic_origins"], 2)

    def test_whole_unit_function_shadow_and_root_duplicate_order(self) -> None:
        expected = {
            "nested_before_later_function_shadow": ("d_nested_g", "shadow_live_name"),
            "later_nested_after_function_shadow": ("d_nested_h", "shadow_live_name"),
            "root_const_then_function_duplicate": ("d_root_k_fn", "duplicate_binding"),
            "root_function_then_const_duplicate": ("d_root_m_const", "duplicate_binding"),
        }
        for name, selected in expected.items():
            with self.subTest(name=name):
                report = self.agreed(name)
                self.assertEqual((report["event_id"], report["reason"]), selected)

    def test_own3_region_uniqueness_ignores_lexical_expiry(self) -> None:
        disjoint = self.agreed("repeated_region_disjoint_scopes")
        self.assertEqual(
            (disjoint["rule"], disjoint["event_id"], disjoint["prior_origin"]["event_id"]),
            ("OWN-3", "d_right_r", "d_left_r"),
        )
        mixed = self.agreed("region_parameter_local_repeat")
        self.assertEqual(
            (mixed["rule"], mixed["event_id"], mixed["prior_origin"]["event_id"]),
            ("OWN-3", "d_local_r", "d_param_r"),
        )
        self.assertEqual(self.agreed("region_reuse_different_owners")["status"], "complete")

    def test_topology_visibility_boundaries_are_explicit(self) -> None:
        expected = {
            "let_initializer_visibility_boundary": "TYPE-5",
            "const_completion_visibility_boundary": "CONST-2",
            "parameter_completion_visibility_boundary": "TYPE-5",
            "match_list_completion_visibility_boundary": "TYPE-5",
        }
        for name, rule in expected.items():
            with self.subTest(name=name):
                report = self.agreed(name)
                self.assertEqual((report["rule"], report["reason"]), (rule, "outside_visibility"))

    def test_scope_interval_must_be_strictly_nested(self) -> None:
        with self.assertRaisesRegex(SchemaError, "strictly contained"):
            validate_case(invalid_child_scope_case())

    def test_builtin_operation_and_reservation_ordinals_are_absolute(self) -> None:
        wrong_builtin = clone(self.cases["pre1_cross_domain"])
        wrong_builtin["builtins"][0]["declaration_ordinal"] = 0
        with self.assertRaisesRegex(SchemaError, "exact PRE-1 declaration ordinal"):
            validate_case(wrong_builtin)

        wrong_operation = evidence_case("wrong_operation_ordinal", events=[])
        wrong_operation["operations"][0]["ordinal"] = 0
        with self.assertRaisesRegex(SchemaError, "exact OP-1 family ordinal"):
            validate_case(wrong_operation)

        wrong_reservation = evidence_case("wrong_reservation_ordinal", events=[])
        wrong_reservation["reservations"][0]["inventory_ordinal"] = 0
        with self.assertRaisesRegex(SchemaError, "wrong absolute OP-1 ordinal"):
            validate_case(wrong_reservation)

    def test_lookup_rank_and_role_attribution_table(self) -> None:
        label = self.agreed("non_enclosing_label")
        self.assertEqual((label["rule"], label["reason"]), ("TYPE-6", "non_enclosing_label"))
        self.assertEqual(
            [origin["event_id"] for origin in label["label_origins"]],
            ["d_loop_label", "d_sibling_label"],
        )
        ranked = self.agreed("invisible_admissible_precedes_wrong_class")
        self.assertEqual((ranked["rule"], ranked["reason"]), ("CONST-1", "outside_visibility"))
        self.assertEqual(ranked["available_classes"], [])
        self.assertEqual(ranked["invisible_origins"][0]["event_id"], "d_const_param_n")
        for name, rule in (
            ("missing_contract_attribution", "FN-3"),
            ("missing_const_attribution", "CONST-1"),
            ("missing_cvalue_attribution", "CONST-2"),
            ("missing_fn_bind_attribution", "FN-4"),
        ):
            with self.subTest(name=name):
                self.assertEqual(self.agreed(name)["rule"], rule)

    def test_label_inventory_is_current_function_and_enclosing_loop_scoped(self) -> None:
        enclosing = self.agreed("enclosing_label_resolves")
        self.assertEqual(enclosing["status"], "complete")
        self.assertEqual(enclosing["resolutions"][0]["target_decl_id"], "enclosing_label")

        later = self.agreed("later_label_same_function")
        self.assertEqual((later["reason"], later["rule"]), ("non_enclosing_label", "TYPE-6"))
        self.assertEqual([item["event_id"] for item in later["label_origins"]], ["d_later_label"])

        repeated = self.agreed("disjoint_repeated_label")
        self.assertEqual(repeated["status"], "complete")
        self.assertEqual(repeated["resolutions"][0]["target_decl_id"], "label_b")

        foreign = self.agreed("other_function_label_absent")
        self.assertEqual((foreign["reason"], foreign["label_origins"]), ("absent_binding", []))

    def test_unrelated_declaration_owners_do_not_enter_rank1(self) -> None:
        expected_rules = {
            "cross_function_local_nonleakage": "TYPE-5",
            "cross_function_type_generic_nonleakage": "TYPE-5",
            "cross_function_const_generic_nonleakage": "CONST-1",
            "cross_function_u18_nonleakage": "FORM-5",
            "cross_function_region_nonleakage": "OWN-3",
            "cross_top_level_owner_generic_nonleakage": "TYPE-5",
            "cross_signature_owner_region_nonleakage": "OWN-3",
        }
        for name, rule in expected_rules.items():
            with self.subTest(name=name):
                report = self.agreed(name)
                self.assertEqual((report["rule"], report["reason"]), (rule, "absent_binding"))
                self.assertEqual(report["invisible_origins"], [])

    def test_same_owner_expired_candidates_enter_rank1(self) -> None:
        values = self.agreed("same_function_sibling_values_rank1")
        self.assertEqual((values["rule"], values["reason"]), ("TYPE-5", "outside_visibility"))
        self.assertEqual(
            [item["event_id"] for item in values["invisible_origins"]],
            ["d_left_x", "d_middle_x"],
        )

        region = self.agreed("same_function_expired_region_rank1")
        self.assertEqual((region["rule"], region["reason"]), ("OWN-3", "outside_visibility"))
        self.assertEqual(
            [item["event_id"] for item in region["invisible_origins"]],
            ["d_left_region"],
        )

    def test_diagnostic_paths_include_primary_and_source_payload_origins(self) -> None:
        source_issue = clone(self.cases["same_function_sibling_values_rank1"])
        source_issue["events"][0]["key"]["path"] = [1]
        source_issue["events"][1]["key"]["path"] = [2, 3]
        source_issue["events"][2]["key"]["path"] = [4, 5, 6]
        left = model_ledger.run(source_issue)
        right = model_relational.run(source_issue)
        self.assertTrue(reports_equal(left, right))
        self.assertEqual(
            (
                left["status"],
                left["resources"]["diagnostic_paths"],
                left["resources"]["diagnostic_path_components"],
                left["resources"]["node_path_depth"],
            ),
            ("source_issue", 3, 6, 3),
        )

    def test_every_limit_is_exact_and_one_over_is_closed(self) -> None:
        complete_case = resource_case()
        issue_case = clone(self.cases["diagnostic_issue_data_allocation_failure"])
        issue_case["faults"] = []
        witnesses = {
            "diagnostic_origins": clone(self.cases["same_function_sibling_values_rank1"]),
            "diagnostic_paths": issue_case,
            "diagnostic_path_components": issue_case,
        }

        for limit_name in _EXPECTED_PROFILE_ORDER:
            base = witnesses.get(limit_name, complete_case)
            baseline_left = model_ledger.run(base)
            baseline_right = model_relational.run(base)
            self.assertTrue(reports_equal(baseline_left, baseline_right), limit_name)
            count = baseline_left["resources"][limit_name]
            self.assertGreater(count, 0, limit_name)

            exact = clone(base)
            exact["limits"] = dict(baseline_left["resources"])
            exact_left = model_ledger.run(exact)
            exact_right = model_relational.run(exact)
            self.assertTrue(reports_equal(exact_left, exact_right), limit_name)
            self.assertEqual(exact_left["status"], baseline_left["status"], limit_name)

            constrained = clone(base)
            constrained["limits"][limit_name] = count - 1
            left = model_ledger.run(constrained)
            right = model_relational.run(constrained)
            self.assertTrue(reports_equal(left, right), limit_name)
            self.assertEqual(left["status"], "resource_failure", limit_name)
            self.assertEqual((left["kind"], left["limit"]), ("limit_exceeded", limit_name))

    def test_preflight_limit_precedence_and_wrong_order_mutant(self) -> None:
        constrained = resource_case()
        constrained["limits"]["declarations"] = 0
        constrained["limits"]["scopes"] = 0

        expected = model_relational.run(constrained)
        self.assertEqual(
            (expected["kind"], expected["limit"], expected["phase"]),
            ("limit_exceeded", "declarations", "preflight"),
        )
        self.assertTrue(reports_equal(expected, model_ledger.run(constrained)))

        reversed_order = tuple(reversed(model_ledger._PROFILE_ORDER))
        with mock.patch.object(model_ledger, "_PROFILE_ORDER", reversed_order):
            mutant = model_ledger.run(constrained)
        self.assertEqual(mutant["limit"], "scopes")
        self.assertFalse(reports_equal(expected, mutant))

    def test_preflight_work_precedes_unfinished_structural_counts(self) -> None:
        constrained = resource_case()
        constrained["limits"]["work"] = 0
        constrained["limits"]["declarations"] = 0
        left = model_ledger.run(constrained)
        right = model_relational.run(constrained)
        self.assertTrue(reports_equal(left, right))
        self.assertEqual(
            (left["kind"], left["limit"], left["phase"]),
            ("limit_exceeded", "work", "preflight"),
        )

    def test_count_detection_obeys_work_precedence(self) -> None:
        constrained = clone(self.cases["count_unrepresentable_failure"])
        constrained["faults"][0]["detection_work"] = 3
        constrained["limits"]["work"] = 2
        left = model_ledger.run(constrained)
        right = model_relational.run(constrained)
        self.assertTrue(reports_equal(left, right))
        self.assertEqual((left["kind"], left["limit"]), ("limit_exceeded", "work"))

        constrained["limits"]["work"] = 3
        left = model_ledger.run(constrained)
        right = model_relational.run(constrained)
        self.assertTrue(reports_equal(left, right))
        self.assertEqual(
            (left["kind"], left["family"]),
            ("count_unrepresentable", "lookup_entries"),
        )

    def test_storage_precedence_is_closed_and_input_order_independent(self) -> None:
        constrained = resource_case()
        constrained["faults"] = [
            {
                "kind": "allocation_failure",
                "storage": "declarations",
            },
            {
                "kind": "address_space_exceeded",
                "storage": "ordering_scratch",
            },
            {
                "kind": "address_space_exceeded",
                "storage": "lookup_entries",
            },
        ]
        left = model_ledger.run(constrained)
        right = model_relational.run(constrained)
        self.assertTrue(reports_equal(left, right))
        self.assertEqual(
            (left["kind"], left["storage"]),
            ("address_space_exceeded", "lookup_entries"),
        )

        permuted = clone(constrained)
        permuted["faults"].reverse()
        permuted["events"].reverse()
        permuted["scopes"].reverse()
        self.assertTrue(reports_equal(left, model_ledger.run(permuted)))
        self.assertTrue(reports_equal(left, model_relational.run(permuted)))

    def test_ordering_scratch_allocation_failure_is_representable(self) -> None:
        constrained = resource_case()
        constrained["faults"] = [
            {
                "kind": "allocation_failure",
                "storage": "ordering_scratch",
            }
        ]
        left = model_ledger.run(constrained)
        right = model_relational.run(constrained)
        self.assertTrue(reports_equal(left, right))
        self.assertEqual(
            (left["kind"], left["storage"]),
            ("allocation_failure", "ordering_scratch"),
        )
        self.assertEqual(
            left["requested_elements"],
            left["resources"]["lookup_entries"],
        )

    def test_ancestry_is_counted_and_limited_in_post_pass(self) -> None:
        constrained = resource_case()
        constrained["limits"]["ancestry_steps"] = 0
        left = model_ledger.run(constrained)
        right = model_relational.run(constrained)
        self.assertTrue(reports_equal(left, right))
        self.assertEqual(
            (left["kind"], left["limit"], left["phase"]),
            ("limit_exceeded", "ancestry_steps", "preflight"),
        )
        self.assertEqual(left["resources"]["ancestry_steps"], 1)

    def test_fn8_short_circuits_all_ordinary_resource_paths(self) -> None:
        ordinary = set(_EXPECTED_PROFILE_ORDER) - {
            "node_path_depth",
            "diagnostic_origins",
            "diagnostic_paths",
            "diagnostic_path_components",
            "work",
        }
        for name in (
            "fn8_ordinary_zero_limit_dormant",
            "fn8_ordinary_count_fault_dormant",
            "fn8_ordinary_storage_fault_dormant",
        ):
            with self.subTest(name=name):
                report = self.agreed(name)
                self.assertEqual((report["status"], report["rule"]), ("source_issue", "FN-8"))
                self.assertTrue(all(report["resources"][field] == 0 for field in ordinary))

    def test_lookup_sort_schedule_and_common_prefix_work_are_bounded(self) -> None:
        common = self.cases["common_prefix_lookup_sort_work"]
        seen: list[str] = []
        original = model_ledger._stable_lookup_sort

        def recording_sort(rows, ordering, spend):
            seen.append(ordering)
            return original(rows, ordering, spend)

        with mock.patch.object(model_ledger, "_stable_lookup_sort", recording_sort):
            common_report = model_ledger.run(common)
        self.assertEqual(seen, ["same_scope", "region_owner", "arm_binder", "lookup"])
        self.assertEqual(common_report["status"], "complete")

        early_difference = clone(common)
        early_difference["events"][0]["spelling"] = "BaaaaaaaX"
        early_difference["events"][1]["spelling"] = "CaaaaaaaY"
        shorter = model_ledger.run(early_difference)
        self.assertGreater(common_report["resources"]["work"], shorter["resources"]["work"])

        boundary = clone(common)
        boundary["limits"]["work"] = shorter["resources"]["work"]
        failure = model_ledger.run(boundary)
        self.assertEqual((failure["kind"], failure["limit"]), ("limit_exceeded", "work"))

    def test_lookup_visibility_search_uses_the_dense_direct_use_ordinal(self) -> None:
        case = self.cases["lookup_visibility_uses_dense_direct_event_ordinal"]
        report = self.agreed("lookup_visibility_uses_dense_direct_event_ordinal")
        self.assertEqual(
            (report["status"], report["rule"], report["reason"]),
            ("source_issue", "TYPE-5", "outside_visibility"),
        )

        second_probe = clone(case)
        second_probe["limits"]["work"] = 81
        failure = model_ledger.run(second_probe)
        self.assertTrue(reports_equal(failure, model_relational.run(second_probe)))
        self.assertEqual(
            (failure["phase"], failure["resources"]["work"]),
            ("visibility_probe", 82),
        )

        second_comparison = clone(case)
        second_comparison["limits"]["work"] = 82
        failure = model_ledger.run(second_comparison)
        self.assertTrue(reports_equal(failure, model_relational.run(second_comparison)))
        self.assertEqual(
            (failure["phase"], failure["resources"]["work"]),
            ("visibility_start_comparison", 83),
        )
        self.assertIn("comparison", failure["phase"])

    def test_deep_successful_uses_do_not_multiply_ancestry(self) -> None:
        repeated = self.agreed("deep_scopes_repeated_successful_uses")
        single_case = clone(self.cases["deep_scopes_repeated_successful_uses"])
        single_case["events"] = single_case["events"][:2]
        left = model_ledger.run(single_case)
        right = model_relational.run(single_case)
        self.assertTrue(reports_equal(left, right))
        self.assertEqual(
            (repeated["resources"]["ancestry_steps"], left["resources"]["ancestry_steps"]),
            (4, 4),
        )

    def test_diagnostic_descriptors_and_issue_element_count_are_exact(self) -> None:
        pre1 = self.agreed("pre1_struct_dual_conflict")
        self.assertEqual(
            (pre1["resources"]["diagnostic_origins"], pre1["resources"]["diagnostic_paths"]),
            (2, 1),
        )

        rank2 = self.agreed("non_enclosing_label")
        self.assertEqual(
            (rank2["lookup_rank"], rank2["resources"]["diagnostic_origins"], rank2["resources"]["diagnostic_paths"]),
            (2, 2, 3),
        )

        allocation = self.agreed("diagnostic_issue_data_allocation_failure")
        resources = allocation["resources"]
        self.assertEqual(
            allocation["requested_elements"],
            1
            + resources["diagnostic_origins"]
            + resources["diagnostic_paths"]
            + resources["diagnostic_path_components"],
        )

    def test_issue_data_layout_and_derived_count_precedence(self) -> None:
        address = self.agreed("diagnostic_issue_data_address_precedes_allocation")
        self.assertEqual(
            (address["kind"], address["storage"]),
            ("address_space_exceeded", "diagnostic_issue_data"),
        )
        derived = self.agreed("diagnostic_issue_elements_unrepresentable")
        self.assertEqual(
            (derived["kind"], derived["family"]),
            ("count_unrepresentable", "diagnostic_issue_elements"),
        )

    def test_zero_element_reservation_fault_is_dormant(self) -> None:
        empty = evidence_case("zero_reserve_fault", events=[], operations=[], reservations=[])
        empty["faults"] = [
            {"kind": "allocation_failure", "storage": "coverage_records"}
        ]
        left = model_ledger.run(empty)
        right = model_relational.run(empty)
        self.assertTrue(reports_equal(left, right))
        self.assertEqual(left["status"], "complete")

    def test_selected_reason_payload_and_gram10_live_origins_are_exact(self) -> None:
        reserved = self.agreed("form3_reserved_binder_suppresses_gram10_origins")
        self.assertEqual(
            (
                reserved["rule"],
                reserved["gram10"],
                reserved["resources"]["diagnostic_origins"],
                reserved["resources"]["diagnostic_paths"],
            ),
            ("FORM-3", None, 0, 1),
        )

        for name, event_id, origin_id in (
            ("gram10_binder_before_later_function", "d_early_binder_f", "d_later_function_f"),
            ("gram10_nested_arm_outer_binder_live", "d_inner_arm_x", "d_outer_arm_x"),
        ):
            with self.subTest(name=name):
                report = self.agreed(name)
                self.assertEqual(
                    (report["rule"], report["reason"], report["event_id"]),
                    ("GRAM-10", "binder_collides_arm_entry", event_id),
                )
                self.assertEqual(
                    [origin["event_id"] for origin in report["gram10"]["arm_entry_live_origins"]],
                    [origin_id],
                )
                self.assertEqual(
                    (report["resources"]["diagnostic_origins"], report["resources"]["diagnostic_paths"]),
                    (1, 2),
                )

    def test_diagnostic_count_work_precedes_its_layout_and_reserve_boundary(self) -> None:
        constrained = clone(self.cases["diagnostic_issue_data_allocation_failure"])
        allocation_left = model_ledger.run(constrained)
        allocation_right = model_relational.run(constrained)
        self.assertTrue(reports_equal(allocation_left, allocation_right))
        self.assertEqual(
            (allocation_left["kind"], allocation_left["storage"]),
            ("allocation_failure", "diagnostic_issue_data"),
        )
        constrained["limits"]["work"] = allocation_left["resources"]["work"] - 1
        left = model_ledger.run(constrained)
        right = model_relational.run(constrained)
        self.assertTrue(reports_equal(left, right))
        self.assertEqual(
            (left["kind"], left["limit"], left["phase"]),
            ("limit_exceeded", "work", "diagnostic_count"),
        )

    def test_zero_limits_admit_exactly_zero_counts(self) -> None:
        empty = evidence_case(
            "zero_count_families",
            events=[],
            operations=[],
            reservations=[],
        )
        empty["limits"].update(
            {
                "declarations": 0,
                "scope_depth": 0,
                "declaration_events": 0,
                "lexical_uses": 0,
                "deferred_uses": 0,
                "spelling_bytes": 0,
                "lookup_entries": 0,
                "ancestry_steps": 0,
                "node_path_depth": 0,
                "diagnostic_origins": 0,
                "diagnostic_paths": 0,
                "diagnostic_path_components": 0,
                "coverage_records": 0,
                "scopes": 1,
                "work": 1,
            }
        )
        left = model_ledger.run(empty)
        right = model_relational.run(empty)
        self.assertTrue(reports_equal(left, right))
        self.assertEqual(left["status"], "complete")

        constrained = clone(empty)
        constrained["limits"]["scopes"] = 0
        left = model_ledger.run(constrained)
        right = model_relational.run(constrained)
        self.assertTrue(reports_equal(left, right))
        self.assertEqual((left["kind"], left["limit"]), ("limit_exceeded", "scopes"))

    def test_sufficient_limits_and_input_permutation_do_not_change_semantics(self) -> None:
        base = resource_case()
        permuted = clone(base)
        permuted["events"].reverse()
        permuted["scopes"].reverse()
        left = model_ledger.run(base)
        right = model_ledger.run(permuted)
        self.assertEqual(semantic_projection(left), semantic_projection(right))
        self.assertTrue(reports_equal(right, model_relational.run(permuted)))

    def test_closed_nonlimit_resource_failures(self) -> None:
        address = self.agreed("address_space_failure")
        count = self.agreed("count_unrepresentable_failure")
        storage = self.agreed("storage_failure")
        diagnostic = self.agreed("diagnostic_issue_data_allocation_failure")
        unused = self.agreed("unused_diagnostic_issue_data_fault")
        self.assertEqual(address["kind"], "address_space_exceeded")
        self.assertEqual(
            (count["kind"], count["family"]),
            ("count_unrepresentable", "lookup_entries"),
        )
        self.assertEqual(storage["kind"], "allocation_failure")
        self.assertEqual(
            (diagnostic["kind"], diagnostic["storage"]),
            ("allocation_failure", "diagnostic_issue_data"),
        )
        self.assertEqual(unused["status"], "complete")


if __name__ == "__main__":
    unittest.main()
