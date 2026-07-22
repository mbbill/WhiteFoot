"""Abstract role-stream cases; neither semantic model imports this module."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

Owner = tuple[tuple[str, str], ...]
FIXTURE_FUNCTION_OWNER: Owner = (("function", "fixture-function"),)

_PROFILE_FIELDS = (
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


def owner_path(owner: Owner) -> list[dict[str, str]]:
    return [{"kind": kind, "id": identity} for kind, identity in owner]


def key(
    source: int,
    start: int,
    *,
    end: int | None = None,
    path: tuple[int, ...] = (),
    role: int = 0,
    subtoken: int = 0,
) -> dict[str, Any]:
    return {
        "source": source,
        "start": start,
        "end": start + 1 if end is None else end,
        "path": list(path),
        "role": role,
        "subtoken": subtoken,
    }


def ample_limits() -> dict[str, int]:
    return {name: 100_000 for name in _PROFILE_FIELDS}


def unit_scope(last_source: int = 9) -> list[dict[str, Any]]:
    return [
        {
            "id": "unit",
            "parent": None,
            "open": key(0, 0, end=0),
            "close": key(last_source, 1_000_000, end=1_000_001),
        }
    ]


def two_function_scopes() -> list[dict[str, Any]]:
    return unit_scope() + [
        {"id": "fn_f", "parent": "unit", "open": key(0, 10), "close": key(0, 400)},
        {"id": "fn_g", "parent": "unit", "open": key(0, 500), "close": key(0, 900)},
    ]


def function_sibling_scopes() -> list[dict[str, Any]]:
    return unit_scope() + [
        {"id": "fn_f", "parent": "unit", "open": key(0, 10), "close": key(0, 900)},
        {"id": "left", "parent": "fn_f", "open": key(0, 100), "close": key(0, 250)},
        {"id": "middle", "parent": "fn_f", "open": key(0, 300), "close": key(0, 450)},
        {"id": "right", "parent": "fn_f", "open": key(0, 500), "close": key(0, 700)},
    ]


def label_scopes() -> list[dict[str, Any]]:
    return unit_scope() + [
        {"id": "fn_f", "parent": "unit", "open": key(0, 10), "close": key(0, 900)},
        {"id": "loop_a", "parent": "fn_f", "open": key(0, 100), "close": key(0, 300)},
        {"id": "loop_b", "parent": "fn_f", "open": key(0, 400), "close": key(0, 600)},
        {"id": "loop_c", "parent": "fn_f", "open": key(0, 650), "close": key(0, 800)},
    ]


def declaration(
    event_id: str,
    decl_id: str,
    decl_kind: str,
    spelling: str,
    position: dict[str, Any],
    scope: str = "unit",
    *,
    arm_id: str | None = None,
    field_spelling: str | None = None,
    visible_from: dict[str, Any] | None = None,
    visibility_scope: str | None = None,
    loop_id: str | None = None,
    owner: Owner | None = None,
    type_bound: str | None = None,
    requires_block: str | None = None,
) -> dict[str, Any]:
    if owner is None:
        owner = (
            FIXTURE_FUNCTION_OWNER
            if decl_kind
            in (
                "type_parameter",
                "const_parameter",
                "parameter",
                "local",
                "requires_local",
                "match_binder",
                "region_parameter",
                "region",
                "label",
            )
            else ()
        )
    return {
        "event_id": event_id,
        "kind": "declare",
        "decl_id": decl_id,
        "decl_kind": decl_kind,
        "spelling": spelling,
        "scope": scope,
        "key": position,
        "arm_id": arm_id,
        "field_spelling": field_spelling,
        "owner_path": owner_path(owner),
        "type_bound": type_bound,
        "visible_from": (
            None
            if decl_kind == "function"
            else deepcopy(position) if visible_from is None else visible_from
        ),
        "visibility_scope": scope if visibility_scope is None else visibility_scope,
        "loop_id": loop_id,
        "requires_block": requires_block,
    }


def use(
    event_id: str,
    role_kind: str,
    spelling: str,
    position: dict[str, Any],
    scope: str = "unit",
    surface: str | None = None,
    enclosing_loops: tuple[str, ...] = (),
    owner: Owner = FIXTURE_FUNCTION_OWNER,
    requires_block: str | None = None,
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "kind": "use",
        "role_kind": role_kind,
        "spelling": spelling,
        "scope": scope,
        "key": position,
        "surface": surface,
        "enclosing_loops": list(enclosing_loops),
        "owner_path": owner_path(owner),
        "requires_block": requires_block,
    }


def builtin(
    decl_id: str,
    decl_kind: str,
    spelling: str,
    declaration_ordinal: int,
) -> dict[str, Any]:
    return {
        "decl_id": decl_id,
        "decl_kind": decl_kind,
        "spelling": spelling,
        "owner_path": [],
        "type_bound": None,
        "declaration_ordinal": declaration_ordinal,
    }


def case(
    name: str,
    *,
    events: list[dict[str, Any]],
    builtins: list[dict[str, Any]] | None = None,
    scopes: list[dict[str, Any]] | None = None,
    fault: dict[str, Any] | None = None,
    operations: list[dict[str, Any]] | None = None,
    reservations: list[dict[str, Any]] | None = None,
    requires_blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "scopes": unit_scope() if scopes is None else scopes,
        "builtins": [] if builtins is None else builtins,
        "operations": (
            [
                {"spelling": "iadd.trap", "token_class": "opname", "ordinal": 3},
                {"spelling": "len", "token_class": "ident", "ordinal": 39},
            ]
            if operations is None
            else operations
        ),
        "reservations": (
            [
                {
                    "spelling": "len",
                    "reserved_class": "dotless_operation",
                    "inventory_ordinal": 39,
                },
                {
                    "spelling": "wrap",
                    "reserved_class": "mode_word",
                    "inventory_ordinal": 0,
                },
            ]
            if reservations is None
            else reservations
        ),
        "requires_blocks": [] if requires_blocks is None else requires_blocks,
        "events": events,
        "limits": ample_limits(),
        "faults": [] if fault is None else [fault],
    }


def all_cases() -> list[dict[str, Any]]:
    prelude = [
        builtin("prelude_overflow_type", "enum", "Overflow", 15),
        builtin("prelude_overflow_variant", "variant", "Overflow", 16),
        builtin("prelude_narrow_type", "enum", "NarrowError", 20),
        builtin("prelude_narrow_variant", "variant", "NarrowError", 21),
        builtin("prelude_int_contract", "contract", "Int", 22),
    ]
    nested_scopes = unit_scope() + [
        {
            "id": "inner",
            "parent": "unit",
            "open": key(0, 10, path=(0,)),
            "close": key(0, 50, path=(0,)),
        }
    ]
    cases = [
        case(
            "fn8_structural_issue_suppresses_child_roles",
            requires_blocks=[
                {
                    "block_id": "requires-bad",
                    "block_key": key(0, 10, path=(0,)),
                    "issue_kind": "invalid_entry",
                    "issue_key": key(0, 20, path=(0, 0)),
                }
            ],
            events=[
                declaration(
                    "d_suppressed_reserved",
                    "suppressed_reserved",
                    "requires_local",
                    "len",
                    key(0, 15, path=(0, 0, 0)),
                    requires_block="requires-bad",
                ),
                use(
                    "u_suppressed_missing",
                    "pbase",
                    "missing",
                    key(0, 16, path=(0, 0, 1)),
                    requires_block="requires-bad",
                ),
            ],
        ),
        case("pre1_cross_domain", events=[], builtins=prelude),
        case(
            "struct_dual_entry",
            events=[
                declaration("d_pair", "pair", "struct", "Pair", key(0, 10)),
                use("u_pair_type", "type_argument", "Pair", key(0, 20)),
                use("u_pair_ctor", "construct", "Pair", key(0, 30)),
            ],
        ),
        case(
            "inventory_before_resolution",
            events=[
                use("u_early_missing", "pbase", "missing", key(0, 1)),
                declaration("d_box", "box_struct", "struct", "Box", key(0, 10)),
                declaration("d_box_variant", "box_variant", "variant", "Box", key(0, 20)),
            ],
        ),
        case(
            "separate_contract_domain",
            builtins=[builtin("builtin_int_contract", "contract", "Int", 22)],
            events=[
                declaration("d_int", "source_int", "struct", "Int", key(0, 10)),
                use("u_int_type", "type_argument", "Int", key(0, 20)),
                use("u_int_ctor", "construct", "Int", key(0, 21)),
                use("u_int_contract", "contract", "Int", key(0, 22)),
            ],
        ),
        case(
            "constructor_before_visibility_start",
            events=[
                use("u_later", "construct", "Later", key(0, 10)),
                declaration("d_later", "later_variant", "variant", "Later", key(0, 20)),
            ],
        ),
        case(
            "struct_is_not_arm_constructor",
            events=[
                declaration("d_arm_struct", "arm_struct", "struct", "OnlyStruct", key(0, 10)),
                use("u_arm_struct", "arm_constructor", "OnlyStruct", key(0, 20)),
            ],
        ),
        case(
            "scope_end_is_exclusive",
            scopes=nested_scopes,
            events=[
                declaration("d_x", "inner_x", "local", "x", key(0, 20, path=(0, 0)), "inner"),
                use("u_x_after", "pbase", "x", key(0, 60)),
            ],
        ),
        case(
            "whole_unit_function_visibility",
            events=[
                use("u_f_early", "callee_ident", "f", key(0, 10)),
                declaration("d_f", "function_f", "function", "f", key(0, 20)),
            ],
        ),
        case(
            "local_is_not_function",
            scopes=nested_scopes,
            events=[
                declaration("d_local_f", "local_f", "local", "f", key(0, 20, path=(0, 0)), "inner"),
                use("u_local_f_call", "callee_ident", "f", key(0, 30, path=(0, 1)), "inner"),
            ],
        ),
        case(
            "constant_is_not_function",
            events=[
                declaration("d_const_f", "const_f", "constant", "f", key(0, 10)),
                use("u_const_f_call", "callee_ident", "f", key(0, 20)),
            ],
        ),
        case(
            "nominal_is_not_numeric_identity_parameter",
            events=[
                declaration("d_nominal_t", "enum_t", "enum", "T", key(0, 10)),
                use(
                    "u_wrong_zero_t",
                    "numeric_identity_type",
                    "T",
                    key(0, 22, end=23, subtoken=1),
                    surface="0_T",
                ),
            ],
        ),
        case(
            "cross_source_order",
            events=[
                use("u_source_one", "pbase", "a", key(1, 1)),
                use("u_source_zero", "pbase", "b", key(0, 100)),
            ],
        ),
        case(
            "node_path_prefix_order",
            events=[
                use("u_long_path", "pbase", "long", key(0, 10, path=(2, 0))),
                use("u_short_path", "pbase", "short", key(0, 10, path=(2,))),
            ],
        ),
        case(
            "role_and_subtoken_order",
            events=[
                use("u_subtoken_one", "pbase", "late", key(0, 10, path=(3,), role=1, subtoken=1)),
                use("u_subtoken_zero", "pbase", "first", key(0, 10, path=(3,), role=1, subtoken=0)),
                use("u_role_two", "pbase", "later_role", key(0, 10, path=(3,), role=2, subtoken=0)),
            ],
        ),
        case(
            "generic_zero_subtoken",
            scopes=nested_scopes,
            events=[
                declaration("d_t", "type_t", "type_parameter", "T", key(0, 20, path=(0, 0)), "inner"),
                use(
                    "u_zero_t",
                    "numeric_identity_type",
                    "T",
                    key(0, 32, end=33, path=(0, 1), subtoken=1),
                    "inner",
                    "0_T",
                ),
            ],
        ),
        case(
            "law_zero_role_overlap",
            scopes=nested_scopes,
            events=[
                declaration("d_law_t", "law_type_t", "type_parameter", "T", key(0, 20, path=(0, 0)), "inner"),
                use(
                    "u_law_zero_complete",
                    "law_role",
                    "0_T",
                    key(0, 30, end=33, path=(0, 1), role=0, subtoken=0),
                    "inner",
                    "0_T",
                ),
                use(
                    "u_law_zero_suffix",
                    "numeric_identity_type",
                    "T",
                    key(0, 32, end=33, path=(0, 1), role=0, subtoken=1),
                    "inner",
                    "0_T",
                ),
            ],
        ),
        case(
            "own3_signature_region",
            events=[use("u_missing_region", "signature_region", "'missing", key(0, 10))],
        ),
        case(
            "type5_requires_local_outside",
            scopes=nested_scopes,
            events=[
                declaration("d_req", "req_x", "requires_local", "x", key(0, 20, path=(0, 0)), "inner"),
                use("u_req_after", "pbase", "x", key(0, 60)),
            ],
        ),
        case(
            "gram10_deferred_roles",
            events=[
                use("u_field", "match_field_name", "value", key(0, 10, role=0)),
                use("u_order", "match_field_order", "error", key(0, 10, role=1)),
            ],
        ),
        case(
            "gram10_binder_freshness_inventory",
            scopes=nested_scopes,
            events=[
                declaration("d_live_name", "live_name", "constant", "value", key(0, 5)),
                declaration(
                    "d_match_binder",
                    "match_binder",
                    "match_binder",
                    "value",
                    key(0, 20, path=(0, 0)),
                    "inner",
                    arm_id="arm0",
                    field_spelling="field",
                ),
            ],
        ),
        case(
            "gram10_binder_equals_field",
            scopes=nested_scopes,
            events=[
                declaration(
                    "d_equal_binder",
                    "equal_binder",
                    "match_binder",
                    "payload",
                    key(0, 20, path=(0, 0)),
                    "inner",
                    arm_id="arm0",
                    field_spelling="payload",
                ),
            ],
        ),
        case(
            "gram10_duplicate_binder_in_arm",
            scopes=nested_scopes,
            events=[
                declaration(
                    "d_first_binder",
                    "first_binder",
                    "match_binder",
                    "x",
                    key(0, 20, path=(0, 0), role=0),
                    "inner",
                    arm_id="arm0",
                    field_spelling="left",
                ),
                declaration(
                    "d_later_binder",
                    "later_binder",
                    "match_binder",
                    "x",
                    key(0, 20, path=(0, 0), role=1),
                    "inner",
                    arm_id="arm0",
                    field_spelling="right",
                ),
            ],
        ),
        case(
            "form3_reserved_binder_precedence",
            scopes=nested_scopes,
            events=[
                declaration(
                    "d_reserved_binder",
                    "reserved_binder",
                    "match_binder",
                    "len",
                    key(0, 20, path=(0, 0)),
                    "inner",
                    arm_id="arm0",
                    field_spelling="len",
                ),
            ],
        ),
        case(
            "foreign_variant_relation_deferred",
            events=[
                declaration("d_a", "enum_a", "enum", "A", key(0, 10)),
                declaration("d_acase", "variant_a", "variant", "ACase", key(0, 11)),
                declaration("d_b", "enum_b", "enum", "B", key(0, 12)),
                declaration("d_bcase", "variant_b", "variant", "BCase", key(0, 13)),
                use("u_bcase", "arm_constructor", "BCase", key(0, 20, role=0)),
                use("u_relation", "match_variant_relation", "BCase", key(0, 20, role=1)),
            ],
        ),
        case(
            "operation_targets",
            events=[
                use("u_len", "callee_ident", "len", key(0, 10)),
                use("u_iadd_trap", "callee_opname", "iadd.trap", key(0, 20)),
            ],
        ),
        case(
            "mode_word_is_not_operation",
            events=[use("u_wrap", "callee_ident", "wrap", key(0, 10))],
        ),
        case(
            "normalized_region_reservation",
            events=[
                declaration(
                    "d_reserved_region",
                    "reserved_region",
                    "region",
                    "'len",
                    key(0, 10),
                )
            ],
        ),
        case(
            "pre1_struct_dual_conflict",
            builtins=[
                builtin("prelude_overflow_type", "enum", "Overflow", 15),
                builtin("prelude_overflow_variant", "variant", "Overflow", 16),
            ],
            events=[
                declaration(
                    "d_source_overflow",
                    "source_overflow",
                    "struct",
                    "Overflow",
                    key(0, 10),
                )
            ],
        ),
        case(
            "nested_before_later_function_shadow",
            scopes=nested_scopes,
            events=[
                declaration("d_nested_g", "nested_g", "local", "g", key(0, 20, path=(0, 0)), "inner"),
                declaration("d_later_g", "function_g", "function", "g", key(0, 80)),
            ],
        ),
        case(
            "later_nested_after_function_shadow",
            scopes=nested_scopes,
            events=[
                declaration("d_early_h", "function_h", "function", "h", key(0, 5)),
                declaration("d_nested_h", "nested_h", "parameter", "h", key(0, 20, path=(0, 0)), "inner"),
            ],
        ),
        case(
            "root_const_then_function_duplicate",
            events=[
                declaration("d_root_k_const", "root_k_const", "constant", "k", key(0, 10)),
                declaration("d_root_k_fn", "root_k_fn", "function", "k", key(0, 20)),
            ],
        ),
        case(
            "root_function_then_const_duplicate",
            events=[
                declaration("d_root_m_fn", "root_m_fn", "function", "m", key(0, 10)),
                declaration("d_root_m_const", "root_m_const", "constant", "m", key(0, 20)),
            ],
        ),
        case(
            "repeated_region_disjoint_scopes",
            scopes=unit_scope()
            + [
                {"id": "left", "parent": "unit", "open": key(0, 10), "close": key(0, 30)},
                {"id": "right", "parent": "unit", "open": key(0, 40), "close": key(0, 60)},
            ],
            events=[
                declaration("d_left_r", "left_r", "region", "'r", key(0, 20), "left"),
                declaration("d_right_r", "right_r", "region", "'r", key(0, 50), "right"),
            ],
        ),
        case(
            "region_parameter_local_repeat",
            scopes=nested_scopes,
            events=[
                declaration("d_param_r", "param_r", "region_parameter", "'r", key(0, 5)),
                declaration("d_local_r", "local_r", "region", "'r", key(0, 20, path=(0, 0)), "inner"),
            ],
        ),
        case(
            "region_reuse_different_owners",
            scopes=unit_scope()
            + [
                {"id": "left", "parent": "unit", "open": key(0, 10), "close": key(0, 30)},
                {"id": "right", "parent": "unit", "open": key(0, 40), "close": key(0, 60)},
            ],
            events=[
                declaration(
                    "d_f_r",
                    "f_r",
                    "region",
                    "'r",
                    key(0, 20),
                    "left",
                    owner=(("function", "f"),),
                ),
                declaration(
                    "d_g_r",
                    "g_r",
                    "region",
                    "'r",
                    key(0, 50),
                    "right",
                    owner=(("function", "g"),),
                ),
            ],
        ),
        case(
            "let_initializer_visibility_boundary",
            scopes=nested_scopes,
            events=[
                declaration(
                    "d_init_x",
                    "init_x",
                    "local",
                    "x",
                    key(0, 20, path=(0, 0)),
                    "inner",
                    visible_from=key(0, 40, path=(0, 0)),
                ),
                use("u_init_x", "pbase", "x", key(0, 30, path=(0, 1)), "inner"),
            ],
        ),
        case(
            "const_completion_visibility_boundary",
            events=[
                declaration(
                    "d_pending_const",
                    "pending_const",
                    "constant",
                    "c",
                    key(0, 10),
                    visible_from=key(0, 30),
                ),
                use("u_pending_const", "cvalue", "c", key(0, 20)),
            ],
        ),
        case(
            "parameter_completion_visibility_boundary",
            scopes=nested_scopes,
            events=[
                declaration(
                    "d_pending_param",
                    "pending_param",
                    "parameter",
                    "p",
                    key(0, 20, path=(0, 0)),
                    "inner",
                    visible_from=key(0, 40, path=(0, 0)),
                ),
                use("u_pending_param", "pbase", "p", key(0, 30, path=(0, 1)), "inner"),
            ],
        ),
        case(
            "match_list_completion_visibility_boundary",
            scopes=nested_scopes,
            events=[
                declaration(
                    "d_pending_binder",
                    "pending_binder",
                    "match_binder",
                    "bound",
                    key(0, 20, path=(0, 0)),
                    "inner",
                    arm_id="arm0",
                    field_spelling="field",
                    visible_from=key(0, 40, path=(0, 0)),
                ),
                use("u_pending_binder", "pbase", "bound", key(0, 30, path=(0, 1)), "inner"),
            ],
        ),
        case(
            "u18_unbound_type_parameter",
            scopes=nested_scopes,
            events=[
                declaration(
                    "d_unbound_t",
                    "unbound_t",
                    "type_parameter",
                    "T",
                    key(0, 20, path=(0, 0)),
                    "inner",
                    type_bound=None,
                ),
                use(
                    "u_unbound_zero_t",
                    "numeric_identity_type",
                    "T",
                    key(0, 32, end=33, path=(0, 1), subtoken=1),
                    "inner",
                    "0_T",
                ),
            ],
        ),
        case(
            "u18_wrong_bound_type_parameter",
            builtins=[],
            scopes=nested_scopes,
            events=[
                declaration(
                    "d_display_contract",
                    "display_contract",
                    "contract",
                    "Display",
                    key(0, 5),
                ),
                declaration(
                    "d_display_t",
                    "display_t",
                    "type_parameter",
                    "T",
                    key(0, 20, path=(0, 0)),
                    "inner",
                    type_bound="Display",
                ),
                use("u_display_bound", "contract", "Display", key(0, 24), "inner"),
                use(
                    "u_display_zero_t",
                    "numeric_identity_type",
                    "T",
                    key(0, 32, end=33, path=(0, 1), subtoken=1),
                    "inner",
                    "0_T",
                ),
            ],
        ),
        case(
            "non_enclosing_label",
            scopes=label_scopes(),
            events=[
                declaration(
                    "d_loop_label",
                    "loop_label",
                    "label",
                    "@outer",
                    key(0, 90),
                    "fn_f",
                    visible_from=key(0, 100),
                    visibility_scope="loop_a",
                    loop_id="loop-outer",
                    owner=(("function", "f"),),
                ),
                declaration(
                    "d_sibling_label",
                    "sibling_label",
                    "label",
                    "@outer",
                    key(0, 390),
                    "fn_f",
                    visible_from=key(0, 400),
                    visibility_scope="loop_b",
                    loop_id="loop-sibling",
                    owner=(("function", "f"),),
                ),
                use(
                    "u_bad_break",
                    "label",
                    "@outer",
                    key(0, 700),
                    "loop_c",
                    enclosing_loops=("loop-third",),
                    owner=(("function", "f"),),
                ),
            ],
        ),
        case(
            "enclosing_label_resolves",
            scopes=label_scopes(),
            events=[
                declaration(
                    "d_enclosing_label",
                    "enclosing_label",
                    "label",
                    "@again",
                    key(0, 90),
                    "fn_f",
                    visible_from=key(0, 100),
                    visibility_scope="loop_a",
                    loop_id="loop-a",
                    owner=(("function", "f"),),
                ),
                use(
                    "u_enclosing_break",
                    "label",
                    "@again",
                    key(0, 150),
                    "loop_a",
                    enclosing_loops=("loop-a",),
                    owner=(("function", "f"),),
                ),
            ],
        ),
        case(
            "later_label_same_function",
            scopes=label_scopes(),
            events=[
                use(
                    "u_before_loop",
                    "label",
                    "@later",
                    key(0, 50),
                    "fn_f",
                    owner=(("function", "f"),),
                ),
                declaration(
                    "d_later_label",
                    "later_label",
                    "label",
                    "@later",
                    key(0, 90),
                    "fn_f",
                    visible_from=key(0, 100),
                    visibility_scope="loop_a",
                    loop_id="loop-later",
                    owner=(("function", "f"),),
                ),
            ],
        ),
        case(
            "disjoint_repeated_label",
            scopes=label_scopes(),
            events=[
                declaration(
                    "d_label_a",
                    "label_a",
                    "label",
                    "@again",
                    key(0, 90),
                    "fn_f",
                    visible_from=key(0, 100),
                    visibility_scope="loop_a",
                    loop_id="loop-a",
                    owner=(("function", "f"),),
                ),
                declaration(
                    "d_label_b",
                    "label_b",
                    "label",
                    "@again",
                    key(0, 390),
                    "fn_f",
                    visible_from=key(0, 400),
                    visibility_scope="loop_b",
                    loop_id="loop-b",
                    owner=(("function", "f"),),
                ),
                use(
                    "u_label_b",
                    "label",
                    "@again",
                    key(0, 450),
                    "loop_b",
                    enclosing_loops=("loop-b",),
                    owner=(("function", "f"),),
                ),
            ],
        ),
        case(
            "other_function_label_absent",
            scopes=two_function_scopes()
            + [
                {"id": "f_loop", "parent": "fn_f", "open": key(0, 30), "close": key(0, 300)},
            ],
            events=[
                declaration(
                    "d_f_label",
                    "f_label",
                    "label",
                    "@foreign",
                    key(0, 20),
                    "fn_f",
                    visible_from=key(0, 30),
                    visibility_scope="f_loop",
                    loop_id="loop-f",
                    owner=(("function", "f"),),
                ),
                use(
                    "u_g_break",
                    "label",
                    "@foreign",
                    key(0, 550),
                    "fn_g",
                    owner=(("function", "g"),),
                ),
            ],
        ),
        case(
            "cross_function_local_nonleakage",
            scopes=two_function_scopes(),
            events=[
                declaration("d_f_x", "f_x", "local", "x", key(0, 20), "fn_f", owner=(("function", "f"),)),
                use("u_g_x", "pbase", "x", key(0, 550), "fn_g", owner=(("function", "g"),)),
            ],
        ),
        case(
            "cross_function_type_generic_nonleakage",
            scopes=two_function_scopes(),
            events=[
                declaration("d_f_t", "f_t", "type_parameter", "T", key(0, 20), "fn_f", owner=(("function", "f"),)),
                use("u_g_t", "type_argument", "T", key(0, 550), "fn_g", owner=(("function", "g"),)),
            ],
        ),
        case(
            "cross_function_const_generic_nonleakage",
            scopes=two_function_scopes(),
            events=[
                declaration("d_f_n", "f_n", "const_parameter", "n", key(0, 20), "fn_f", owner=(("function", "f"),)),
                use("u_g_n", "const_use", "n", key(0, 550), "fn_g", owner=(("function", "g"),)),
            ],
        ),
        case(
            "cross_function_u18_nonleakage",
            scopes=two_function_scopes(),
            events=[
                declaration("d_f_u18_t", "f_u18_t", "type_parameter", "T", key(0, 20), "fn_f", owner=(("function", "f"),)),
                use("u_g_zero_t", "numeric_identity_type", "T", key(0, 552, end=553, subtoken=1), "fn_g", "0_T", owner=(("function", "g"),)),
            ],
        ),
        case(
            "cross_function_region_nonleakage",
            scopes=two_function_scopes(),
            events=[
                declaration("d_f_region", "f_region", "region", "'r", key(0, 20), "fn_f", owner=(("function", "f"),)),
                use("u_g_region", "region", "'r", key(0, 550), "fn_g", owner=(("function", "g"),)),
            ],
        ),
        case(
            "cross_top_level_owner_generic_nonleakage",
            scopes=unit_scope()
            + [
                {"id": "struct_s", "parent": "unit", "open": key(0, 10), "close": key(0, 300)},
                {"id": "struct_t", "parent": "unit", "open": key(0, 400), "close": key(0, 700)},
            ],
            events=[
                declaration("d_s_t", "s_t", "type_parameter", "T", key(0, 20), "struct_s", owner=(("struct", "S"),)),
                use("u_t_t", "type_argument", "T", key(0, 450), "struct_t", owner=(("struct", "Other"),)),
            ],
        ),
        case(
            "cross_signature_owner_region_nonleakage",
            scopes=unit_scope()
            + [
                {"id": "contract_c", "parent": "unit", "open": key(0, 10), "close": key(0, 900)},
                {"id": "sig_a", "parent": "contract_c", "open": key(0, 100), "close": key(0, 300)},
                {"id": "sig_b", "parent": "contract_c", "open": key(0, 400), "close": key(0, 700)},
            ],
            events=[
                declaration(
                    "d_sig_a_r",
                    "sig_a_r",
                    "region_parameter",
                    "'r",
                    key(0, 150),
                    "sig_a",
                    owner=(("contract", "C"), ("contract_signature", "a")),
                ),
                use(
                    "u_sig_b_r",
                    "region",
                    "'r",
                    key(0, 450),
                    "sig_b",
                    owner=(("contract", "C"), ("contract_signature", "b")),
                ),
            ],
        ),
        case(
            "same_function_sibling_values_rank1",
            scopes=function_sibling_scopes(),
            events=[
                declaration("d_left_x", "left_x", "local", "x", key(0, 150), "left", owner=(("function", "f"),)),
                declaration("d_middle_x", "middle_x", "local", "x", key(0, 350), "middle", owner=(("function", "f"),)),
                use("u_right_x", "pbase", "x", key(0, 550), "right", owner=(("function", "f"),)),
            ],
        ),
        case(
            "same_function_expired_region_rank1",
            scopes=function_sibling_scopes(),
            events=[
                declaration("d_left_region", "left_region", "region", "'r", key(0, 150), "left", owner=(("function", "f"),)),
                use("u_right_region", "region", "'r", key(0, 550), "right", owner=(("function", "f"),)),
            ],
        ),
        case(
            "invisible_admissible_precedes_wrong_class",
            scopes=unit_scope()
            + [
                {"id": "left", "parent": "unit", "open": key(0, 10), "close": key(0, 30)},
                {"id": "right", "parent": "unit", "open": key(0, 40), "close": key(0, 80)},
            ],
            events=[
                declaration("d_const_param_n", "const_param_n", "const_parameter", "n", key(0, 20), "left"),
                declaration("d_local_n", "local_n", "local", "n", key(0, 50), "right"),
                use("u_const_n", "const_use", "n", key(0, 60), "right"),
            ],
        ),
        case(
            "missing_contract_attribution",
            events=[use("u_missing_contract", "contract", "Missing", key(0, 10))],
        ),
        case(
            "missing_const_attribution",
            events=[use("u_missing_const", "const_use", "missing", key(0, 10))],
        ),
        case(
            "missing_cvalue_attribution",
            events=[use("u_missing_cvalue", "cvalue", "missing", key(0, 10))],
        ),
        case(
            "missing_fn_bind_attribution",
            events=[use("u_missing_fn_bind", "fn_bind_right", "missing", key(0, 10))],
        ),
        case(
            "address_space_failure",
            events=[],
            fault={"kind": "address_space_exceeded", "storage": "lookup_entries"},
        ),
        case(
            "count_unrepresentable_failure",
            events=[],
            fault={
                "kind": "count_unrepresentable",
                "family": "lookup_entries",
                "detection_work": 1,
            },
        ),
        case(
            "storage_failure",
            events=[use("u_coverage", "match_field_name", "field", key(0, 10))],
            fault={"kind": "allocation_failure", "storage": "coverage_records"},
        ),
        case(
            "diagnostic_issue_data_allocation_failure",
            events=[
                use(
                    "u_path_failure",
                    "pbase",
                    "missing",
                    key(0, 10, path=(1, 2, 3)),
                )
            ],
            fault={
                "kind": "allocation_failure",
                "storage": "diagnostic_issue_data",
            },
        ),
        case(
            "unused_diagnostic_issue_data_fault",
            events=[],
            fault={
                "kind": "allocation_failure",
                "storage": "diagnostic_issue_data",
            },
        ),
    ]

    fn8_limit = case(
        "fn8_ordinary_zero_limit_dormant",
        builtins=[builtin("builtin_would_count", "contract", "Int", 22)],
        events=[declaration("d_would_count", "would_count", "struct", "S", key(0, 5))],
        requires_blocks=[
            {
                "block_id": "requires-limit",
                "block_key": key(0, 10, path=(0,)),
                "issue_kind": "invalid_entry",
                "issue_key": key(0, 20, path=(0, 0)),
            }
        ],
    )
    fn8_limit["limits"]["declarations"] = 0

    fn8_count = case(
        "fn8_ordinary_count_fault_dormant",
        events=[declaration("d_count", "counted", "struct", "S", key(0, 5))],
        requires_blocks=[
            {
                "block_id": "requires-count",
                "block_key": key(0, 10, path=(0,)),
                "issue_kind": "invalid_entry",
                "issue_key": key(0, 20, path=(0, 0)),
            }
        ],
        fault={
            "kind": "count_unrepresentable",
            "family": "lookup_entries",
            "detection_work": 1,
        },
    )

    fn8_storage = case(
        "fn8_ordinary_storage_fault_dormant",
        events=[declaration("d_storage", "stored", "struct", "S", key(0, 5))],
        requires_blocks=[
            {
                "block_id": "requires-storage",
                "block_key": key(0, 10, path=(0,)),
                "issue_kind": "invalid_entry",
                "issue_key": key(0, 20, path=(0, 0)),
            }
        ],
        fault={"kind": "allocation_failure", "storage": "coverage_records"},
    )

    deep_scopes = unit_scope() + [
        {"id": "deep1", "parent": "unit", "open": key(0, 10), "close": key(0, 900)},
        {"id": "deep2", "parent": "deep1", "open": key(0, 20), "close": key(0, 800)},
        {"id": "deep3", "parent": "deep2", "open": key(0, 30), "close": key(0, 700)},
        {"id": "deep4", "parent": "deep3", "open": key(0, 40), "close": key(0, 600)},
    ]
    deep_uses = case(
        "deep_scopes_repeated_successful_uses",
        scopes=deep_scopes,
        events=[
            declaration("d_deep_x", "deep_x", "local", "x", key(0, 50), "deep4"),
            use("u_deep_x_1", "pbase", "x", key(0, 60), "deep4"),
            use("u_deep_x_2", "pbase", "x", key(0, 61), "deep4"),
            use("u_deep_x_3", "pbase", "x", key(0, 62), "deep4"),
        ],
    )

    common_prefix = case(
        "common_prefix_lookup_sort_work",
        events=[
            declaration("d_prefix_x", "prefix_x", "struct", "AaaaaaaaX", key(0, 10)),
            declaration("d_prefix_y", "prefix_y", "struct", "AaaaaaaaY", key(0, 20)),
        ],
        operations=[],
        reservations=[],
    )

    dense_use_ordinal = case(
        "lookup_visibility_uses_dense_direct_event_ordinal",
        scopes=function_sibling_scopes(),
        events=[
            declaration(
                "d_left_dense_x",
                "left_dense_x",
                "local",
                "x",
                key(0, 150),
                "left",
            ),
            use("u_middle_dense_x", "pbase", "x", key(0, 350), "middle"),
            declaration(
                "d_right_dense_x",
                "right_dense_x",
                "local",
                "x",
                key(0, 550),
                "right",
            ),
        ],
        operations=[],
        reservations=[],
    )

    issue_data_address = case(
        "diagnostic_issue_data_address_precedes_allocation",
        events=[use("u_issue_layout", "pbase", "missing", key(0, 10, path=(1,)))],
        fault={"kind": "allocation_failure", "storage": "diagnostic_issue_data"},
    )
    issue_data_address["faults"].append(
        {"kind": "address_space_exceeded", "storage": "diagnostic_issue_data"}
    )

    derived_overflow = case(
        "diagnostic_issue_elements_unrepresentable",
        events=[use("u_issue_count", "pbase", "missing", key(0, 10))],
        fault={
            "kind": "count_unrepresentable",
            "family": "diagnostic_issue_elements",
            "addition": 2,
        },
    )

    suppressed_gram10 = case(
        "form3_reserved_binder_suppresses_gram10_origins",
        scopes=nested_scopes,
        events=[
            declaration(
                "d_live_len",
                "live_len",
                "const_parameter",
                "len",
                key(0, 5),
            ),
            declaration(
                "d_reserved_live_binder",
                "reserved_live_binder",
                "match_binder",
                "len",
                key(0, 20, path=(0, 0)),
                "inner",
                arm_id="arm-live",
                field_spelling="other",
            ),
        ],
    )

    binder_before_function = case(
        "gram10_binder_before_later_function",
        scopes=nested_scopes,
        events=[
            declaration(
                "d_early_binder_f",
                "early_binder_f",
                "match_binder",
                "f",
                key(0, 20, path=(0, 0)),
                "inner",
                arm_id="arm-f",
                field_spelling="field",
            ),
            declaration("d_later_function_f", "later_function_f", "function", "f", key(0, 80)),
        ],
    )

    nested_arm_binder = case(
        "gram10_nested_arm_outer_binder_live",
        scopes=unit_scope()
        + [
            {"id": "outer_arm", "parent": "unit", "open": key(0, 10), "close": key(0, 900)},
            {"id": "inner_arm", "parent": "outer_arm", "open": key(0, 30), "close": key(0, 800)},
        ],
        events=[
            declaration(
                "d_outer_arm_x",
                "outer_arm_x",
                "match_binder",
                "x",
                key(0, 20),
                "outer_arm",
                arm_id="outer-arm",
                field_spelling="outer-field",
            ),
            declaration(
                "d_inner_arm_x",
                "inner_arm_x",
                "match_binder",
                "x",
                key(0, 40),
                "inner_arm",
                arm_id="inner-arm",
                field_spelling="inner-field",
            ),
        ],
    )

    cases.extend(
        [
            fn8_limit,
            fn8_count,
            fn8_storage,
            deep_uses,
            common_prefix,
            dense_use_ordinal,
            issue_data_address,
            derived_overflow,
            suppressed_gram10,
            binder_before_function,
            nested_arm_binder,
        ]
    )
    return cases


def resource_case() -> dict[str, Any]:
    scopes = unit_scope() + [
        {
            "id": "inner",
            "parent": "unit",
            "open": key(0, 10, path=(0,)),
            "close": key(0, 90, path=(0,)),
        }
    ]
    return case(
        "resource_boundaries",
        builtins=[builtin("builtin_contract", "contract", "Int", 22)],
        scopes=scopes,
        events=[
            declaration("d_s", "struct_s", "struct", "S", key(0, 5)),
            declaration("d_x", "local_x", "local", "x", key(0, 20, path=(0, 0)), "inner"),
            use("u_s", "type_argument", "S", key(0, 30, path=(0, 1)), "inner"),
            use("u_x", "pbase", "x", key(0, 31, path=(0, 2)), "inner"),
            use("u_field", "match_field_name", "field", key(0, 32, path=(0, 3)), "inner"),
        ],
    )


def clone(value: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(value)


def invalid_child_scope_case() -> dict[str, Any]:
    invalid = case("invalid_child_scope", events=[])
    invalid["scopes"].append(
        {
            "id": "escaping_child",
            "parent": "unit",
            "open": key(0, 10),
            "close": key(9, 1_000_001, end=1_000_002),
        }
    )
    return invalid
