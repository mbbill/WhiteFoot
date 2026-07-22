"""Neutral input validation for the Phase 5 diagnostic-order evidence.

The two models may share this wire schema.  This module deliberately contains
no namespace expansion, visibility, diagnostic, or resolution algorithm.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


LIMIT_NAMES = frozenset({
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
})

DERIVED_COUNT_FAMILY = "diagnostic_issue_elements"
COUNT_FAMILY_NAMES = LIMIT_NAMES | {DERIVED_COUNT_FAMILY}

PRE1_LOOKUP_DECLARATIONS = {
    0: ("enum", "Bool"),
    1: ("variant", "True"),
    2: ("variant", "False"),
    3: ("enum", "Option"),
    5: ("variant", "None"),
    6: ("variant", "Some"),
    8: ("enum", "Result"),
    11: ("variant", "Ok"),
    13: ("variant", "Err"),
    15: ("enum", "Overflow"),
    16: ("variant", "Overflow"),
    17: ("enum", "DivError"),
    18: ("variant", "DivideByZero"),
    19: ("variant", "DivOverflow"),
    20: ("enum", "NarrowError"),
    21: ("variant", "NarrowError"),
    22: ("contract", "Int"),
    23: ("contract", "Float"),
}

OPERATION_FAMILIES = (
    "iadd.wrap", "isub.wrap", "imul.wrap", "iadd.trap", "isub.trap",
    "imul.trap", "iadd.checked", "isub.checked", "imul.checked",
    "idiv.trap", "irem.trap", "idiv.checked", "irem.checked", "ineg.wrap",
    "ineg.trap", "ineg.checked", "ieq", "ine", "ilt", "ile", "igt",
    "ige", "eeq", "ene", "fadd.strict", "fsub.strict", "fmul.strict",
    "fdiv.strict", "feq", "flt", "fle", "fgt", "fge", "fne", "band",
    "bor", "bxor", "bnot", "cvt", "len", "slice_of", "box_new",
    "arena_new", "array_new", "buffer_new", "iand", "ior", "ixor",
    "inot", "ishl.wrap", "ishr.wrap", "ishl.trap", "ishr.trap", "irotl",
    "irotr", "ipopcount", "iclz", "ictz", "ibswap", "imulhi",
    "iadd.sat", "isub.sat", "imul.sat", "imin", "imax", "iabs.wrap",
    "iabs.trap", "iabs.checked", "reinterpret", "fneg", "fabs",
    "fcopysign", "fmin", "fmax", "ffloor", "fceil", "ftrunc",
    "froundeven", "frem", "fsqrt.strict", "ffma.strict", "finf", "fnan",
)

MODE_WORDS = ("wrap", "trap", "checked", "sat", "strict")

STORAGE_NAMES = frozenset({
    "declarations",
    "scopes",
    "declaration_events",
    "lexical_uses",
    "deferred_uses",
    "lookup_entries",
    "coverage_records",
    "ordering_scratch",
    "diagnostic_issue_data",
})

DECLARATION_KINDS = (
    "struct",
    "enum",
    "variant",
    "contract",
    "function",
    "type_parameter",
    "const_parameter",
    "parameter",
    "local",
    "requires_local",
    "match_binder",
    "constant",
    "region_parameter",
    "region",
    "label",
)

ROLE_KINDS = (
    "type_argument",
    "numeric_identity_type",
    "construct",
    "arm_constructor",
    "contract",
    "callee_ident",
    "callee_opname",
    "pbase",
    "const_use",
    "cvalue",
    "fn_bind_right",
    "signature_region",
    "region",
    "label",
    "match_field_name",
    "match_field_order",
    "match_variant_relation",
    "construct_field_name",
    "call_argument_name",
    "contract_member",
    "law_role",
)

OWNER_KINDS = (
    "function",
    "struct",
    "enum",
    "contract",
    "contract_signature",
)

_KEY_FIELDS = ("source", "start", "end", "path", "role", "subtoken")


class SchemaError(ValueError):
    """The evidence input is outside the closed abstract-role schema."""


def _require_mapping(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SchemaError(f"{where} must be an object")
    return value


def _require_exact_keys(value: dict[str, Any], keys: set[str], where: str) -> None:
    actual = set(value)
    if actual != keys:
        raise SchemaError(
            f"{where} keys differ: missing={sorted(keys - actual)!r}, "
            f"extra={sorted(actual - keys)!r}"
        )


def _validate_nonnegative(value: Any, where: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise SchemaError(f"{where} must be a nonnegative integer")


def validate_key(value: Any, where: str) -> None:
    key = _require_mapping(value, where)
    _require_exact_keys(key, set(_KEY_FIELDS), where)
    for field in ("source", "start", "end", "role", "subtoken"):
        _validate_nonnegative(key[field], f"{where}.{field}")
    if key["end"] < key["start"]:
        raise SchemaError(f"{where}.end precedes start")
    if not isinstance(key["path"], list):
        raise SchemaError(f"{where}.path must be an array")
    for index, component in enumerate(key["path"]):
        _validate_nonnegative(component, f"{where}.path[{index}]")


def _wire_key(value: dict[str, Any]) -> tuple[Any, ...]:
    """Compare only structural envelope positions during schema validation."""

    return (
        value["source"],
        value["start"],
        value["end"],
        tuple(value["path"]),
        value["role"],
        value["subtoken"],
    )


def _validate_owner_path(value: Any, where: str) -> None:
    if not isinstance(value, list):
        raise SchemaError(f"{where} must be an array")
    if len(value) > 2:
        raise SchemaError(f"{where} exceeds the closed owner depth")
    for index, component in enumerate(value):
        item = _require_mapping(component, f"{where}[{index}]")
        _require_exact_keys(item, {"kind", "id"}, f"{where}[{index}]")
        if item["kind"] not in OWNER_KINDS:
            raise SchemaError(f"{where}[{index}].kind is not closed")
        if not isinstance(item["id"], str) or not item["id"]:
            raise SchemaError(f"{where}[{index}].id must be a nonempty string")
    if len(value) == 2 and not (
        value[0]["kind"] == "contract"
        and value[1]["kind"] == "contract_signature"
    ):
        raise SchemaError(
            f"{where} depth two is reserved for a contract signature owner"
        )
    if len(value) == 1 and value[0]["kind"] == "contract_signature":
        raise SchemaError(f"{where} contract signature lacks its contract owner")


def _validate_scope(scope: Any, index: int) -> None:
    item = _require_mapping(scope, f"scopes[{index}]")
    _require_exact_keys(item, {"id", "parent", "open", "close"}, f"scopes[{index}]")
    if not isinstance(item["id"], str) or not item["id"]:
        raise SchemaError(f"scopes[{index}].id must be a nonempty string")
    if item["parent"] is not None and (
        not isinstance(item["parent"], str) or not item["parent"]
    ):
        raise SchemaError(f"scopes[{index}].parent must be null or a nonempty string")
    validate_key(item["open"], f"scopes[{index}].open")
    validate_key(item["close"], f"scopes[{index}].close")
    if _wire_key(item["open"]) >= _wire_key(item["close"]):
        raise SchemaError(f"scopes[{index}] must have a nonempty half-open interval")


def _validate_declaration(item: dict[str, Any], where: str, *, builtin: bool) -> None:
    required = {"decl_id", "decl_kind", "spelling", "owner_path", "type_bound"}
    if builtin:
        required.add("declaration_ordinal")
    if not builtin:
        required |= {
            "event_id",
            "kind",
            "scope",
            "key",
            "arm_id",
            "field_spelling",
            "visible_from",
            "visibility_scope",
            "loop_id",
            "requires_block",
        }
    _require_exact_keys(item, required, where)
    if not isinstance(item["decl_id"], str) or not item["decl_id"]:
        raise SchemaError(f"{where}.decl_id must be a nonempty string")
    if item["decl_kind"] not in DECLARATION_KINDS:
        raise SchemaError(f"{where}.decl_kind is not in the closed schema")
    if not isinstance(item["spelling"], str) or not item["spelling"]:
        raise SchemaError(f"{where}.spelling must be a nonempty string")
    _validate_owner_path(item["owner_path"], f"{where}.owner_path")
    if builtin and item["owner_path"]:
        raise SchemaError(f"{where}.owner_path must be the unit owner")
    if builtin:
        _validate_nonnegative(item["declaration_ordinal"], f"{where}.declaration_ordinal")
        expected = PRE1_LOOKUP_DECLARATIONS.get(item["declaration_ordinal"])
        if expected != (item["decl_kind"], item["spelling"]):
            raise SchemaError(f"{where} is not the exact PRE-1 declaration ordinal")
    if item["decl_kind"] == "type_parameter":
        if item["type_bound"] is not None and (
            not isinstance(item["type_bound"], str) or not item["type_bound"]
        ):
            raise SchemaError(f"{where}.type_bound must be null or a nonempty spelling")
    elif item["type_bound"] is not None:
        raise SchemaError(f"{where} carries a type-parameter-only bound")
    if not builtin:
        if item["kind"] != "declare":
            raise SchemaError(f"{where}.kind must be declare")
        validate_key(item["key"], f"{where}.key")
        if item["decl_kind"] == "function":
            if item["visible_from"] is not None:
                raise SchemaError(f"{where}.visible_from must be null for a whole-unit function")
        else:
            validate_key(item["visible_from"], f"{where}.visible_from")
        if item["decl_kind"] == "match_binder":
            if not isinstance(item["arm_id"], str) or not item["arm_id"]:
                raise SchemaError(f"{where}.arm_id must identify the owning match arm")
            if not isinstance(item["field_spelling"], str) or not item["field_spelling"]:
                raise SchemaError(f"{where}.field_spelling must be a nonempty string")
        elif item["arm_id"] is not None or item["field_spelling"] is not None:
            raise SchemaError(f"{where} carries match-binder-only fields")
        if item["decl_kind"] == "label":
            if not isinstance(item["loop_id"], str) or not item["loop_id"]:
                raise SchemaError(f"{where}.loop_id must identify the declaring loop")
        elif item["loop_id"] is not None:
            raise SchemaError(f"{where} carries a label-only loop id")
        if item["requires_block"] is not None and (
            not isinstance(item["requires_block"], str)
            or not item["requires_block"]
        ):
            raise SchemaError(f"{where}.requires_block must be null or a block id")


def _validate_use(item: dict[str, Any], where: str) -> None:
    _require_exact_keys(
        item,
        {
            "event_id",
            "kind",
            "role_kind",
            "spelling",
            "scope",
            "key",
            "surface",
            "enclosing_loops",
            "owner_path",
            "requires_block",
        },
        where,
    )
    if item["kind"] != "use":
        raise SchemaError(f"{where}.kind must be use")
    if item["role_kind"] not in ROLE_KINDS:
        raise SchemaError(f"{where}.role_kind is not in the closed schema")
    if not isinstance(item["spelling"], str) or not item["spelling"]:
        raise SchemaError(f"{where}.spelling must be a nonempty string")
    if item["surface"] is not None and not isinstance(item["surface"], str):
        raise SchemaError(f"{where}.surface must be null or a string")
    _validate_owner_path(item["owner_path"], f"{where}.owner_path")
    if item["requires_block"] is not None and (
        not isinstance(item["requires_block"], str) or not item["requires_block"]
    ):
        raise SchemaError(f"{where}.requires_block must be null or a block id")
    if not isinstance(item["enclosing_loops"], list) or any(
        not isinstance(loop, str) or not loop for loop in item["enclosing_loops"]
    ):
        raise SchemaError(f"{where}.enclosing_loops must be an array of loop ids")
    if len(set(item["enclosing_loops"])) != len(item["enclosing_loops"]):
        raise SchemaError(f"{where}.enclosing_loops must not repeat a loop")
    if item["role_kind"] != "label" and item["enclosing_loops"]:
        raise SchemaError(f"{where}.enclosing_loops is label-use-only topology")
    validate_key(item["key"], f"{where}.key")


def validate_case(value: Any) -> dict[str, Any]:
    """Return a defensive copy after validating the closed neutral schema."""

    case = deepcopy(_require_mapping(value, "case"))
    _require_exact_keys(
        case,
        {
            "name",
            "scopes",
            "builtins",
            "operations",
            "reservations",
            "requires_blocks",
            "events",
            "limits",
            "faults",
        },
        "case",
    )
    if not isinstance(case["name"], str) or not case["name"]:
        raise SchemaError("case.name must be a nonempty string")

    if not isinstance(case["scopes"], list) or not case["scopes"]:
        raise SchemaError("case.scopes must be a nonempty array")
    for index, scope in enumerate(case["scopes"]):
        _validate_scope(scope, index)
    scope_by_id = {scope["id"]: scope for scope in case["scopes"]}
    if len(scope_by_id) != len(case["scopes"]):
        raise SchemaError("scope ids must be unique")
    roots = [scope for scope in case["scopes"] if scope["parent"] is None]
    if len(roots) != 1 or roots[0]["id"] != "unit":
        raise SchemaError("the sole root scope must be named unit")
    for scope in case["scopes"]:
        parent = scope["parent"]
        if parent is not None and parent not in scope_by_id:
            raise SchemaError(f"scope {scope['id']!r} has an unknown parent")
        if parent is not None:
            parent_scope = scope_by_id[parent]
            if not (
                _wire_key(parent_scope["open"]) < _wire_key(scope["open"])
                and _wire_key(scope["close"]) < _wire_key(parent_scope["close"])
            ):
                raise SchemaError(
                    f"scope {scope['id']!r} is not strictly contained in its parent"
                )
        seen: set[str] = set()
        cursor = scope
        while cursor["parent"] is not None:
            if cursor["id"] in seen:
                raise SchemaError("scope parent graph contains a cycle")
            seen.add(cursor["id"])
            cursor = scope_by_id[cursor["parent"]]

    if not isinstance(case["builtins"], list):
        raise SchemaError("case.builtins must be an array")
    declaration_ids: set[str] = set()
    for index, builtin in enumerate(case["builtins"]):
        item = _require_mapping(builtin, f"builtins[{index}]")
        _validate_declaration(item, f"builtins[{index}]", builtin=True)
        if item["decl_id"] in declaration_ids:
            raise SchemaError("declaration ids must be unique")
        declaration_ids.add(item["decl_id"])
    builtin_ordinals = [item["declaration_ordinal"] for item in case["builtins"]]
    if builtin_ordinals != sorted(set(builtin_ordinals)):
        raise SchemaError("builtins must use unique increasing PRE-1 declaration ordinals")

    if not isinstance(case["operations"], list):
        raise SchemaError("case.operations must be an array")
    operation_spellings: set[str] = set()
    operation_ordinals: set[int] = set()
    for index, operation in enumerate(case["operations"]):
        item = _require_mapping(operation, f"operations[{index}]")
        _require_exact_keys(item, {"spelling", "token_class", "ordinal"}, f"operations[{index}]")
        if not isinstance(item["spelling"], str) or not item["spelling"]:
            raise SchemaError(f"operations[{index}].spelling must be nonempty")
        if item["token_class"] not in ("ident", "opname"):
            raise SchemaError(f"operations[{index}].token_class is not closed")
        _validate_nonnegative(item["ordinal"], f"operations[{index}].ordinal")
        if item["ordinal"] >= len(OPERATION_FAMILIES) or (
            OPERATION_FAMILIES[item["ordinal"]] != item["spelling"]
        ):
            raise SchemaError(f"operations[{index}] is not the exact OP-1 family ordinal")
        expected_token_class = "ident" if "." not in item["spelling"] else "opname"
        if item["token_class"] != expected_token_class:
            raise SchemaError(f"operations[{index}].token_class disagrees with OP-1 spelling")
        if item["spelling"] in operation_spellings or item["ordinal"] in operation_ordinals:
            raise SchemaError("operation spellings and ordinals must be unique")
        operation_spellings.add(item["spelling"])
        operation_ordinals.add(item["ordinal"])
    if [item["ordinal"] for item in case["operations"]] != sorted(operation_ordinals):
        raise SchemaError("operations must use increasing absolute OP-1 ordinals")

    if not isinstance(case["reservations"], list):
        raise SchemaError("case.reservations must be an array")
    reservation_spellings: set[str] = set()
    reservation_ordinals: set[tuple[str, int]] = set()
    for index, reservation in enumerate(case["reservations"]):
        item = _require_mapping(reservation, f"reservations[{index}]")
        _require_exact_keys(
            item,
            {"spelling", "reserved_class", "inventory_ordinal"},
            f"reservations[{index}]",
        )
        if not isinstance(item["spelling"], str) or not item["spelling"]:
            raise SchemaError(f"reservations[{index}].spelling must be nonempty")
        if item["reserved_class"] not in ("dotless_operation", "mode_word"):
            raise SchemaError(f"reservations[{index}].reserved_class is not closed")
        _validate_nonnegative(item["inventory_ordinal"], f"reservations[{index}].inventory_ordinal")
        if item["reserved_class"] == "dotless_operation":
            if (
                item["inventory_ordinal"] >= len(OPERATION_FAMILIES)
                or OPERATION_FAMILIES[item["inventory_ordinal"]] != item["spelling"]
                or "." in item["spelling"]
            ):
                raise SchemaError("dotless reservation has the wrong absolute OP-1 ordinal")
        elif (
            item["inventory_ordinal"] >= len(MODE_WORDS)
            or MODE_WORDS[item["inventory_ordinal"]] != item["spelling"]
        ):
            raise SchemaError("mode reservation has the wrong FORM-3 alternative ordinal")
        if item["spelling"] in reservation_spellings:
            raise SchemaError("reservation spellings must be disjoint and unique")
        reservation_spellings.add(item["spelling"])
        ordinal_key = (item["reserved_class"], item["inventory_ordinal"])
        if ordinal_key in reservation_ordinals:
            raise SchemaError("reservation ordinals must be unique within each class")
        reservation_ordinals.add(ordinal_key)
        if item["reserved_class"] == "dotless_operation" and not any(
            operation["spelling"] == item["spelling"]
            and operation["token_class"] == "ident"
            and operation["ordinal"] == item["inventory_ordinal"]
            for operation in case["operations"]
        ):
            raise SchemaError("dotless reservation must name its exact IDENT operation")
    reservation_order = [
        (
            item["spelling"],
            0 if item["reserved_class"] == "dotless_operation" else 1,
            item["inventory_ordinal"],
        )
        for item in case["reservations"]
    ]
    if reservation_order != sorted(reservation_order):
        raise SchemaError("reservations must use exact compiled inventory order")

    requires_blocks = case["requires_blocks"]
    if not isinstance(requires_blocks, list):
        raise SchemaError("case.requires_blocks must be an array")
    block_ids: set[str] = set()
    for index, block in enumerate(requires_blocks):
        item = _require_mapping(block, f"requires_blocks[{index}]")
        _require_exact_keys(
            item,
            {"block_id", "block_key", "issue_kind", "issue_key"},
            f"requires_blocks[{index}]",
        )
        if not isinstance(item["block_id"], str) or not item["block_id"]:
            raise SchemaError(f"requires_blocks[{index}].block_id must be nonempty")
        if item["block_id"] in block_ids:
            raise SchemaError("requires block ids must be unique")
        block_ids.add(item["block_id"])
        validate_key(item["block_key"], f"requires_blocks[{index}].block_key")
        if item["issue_kind"] is None:
            if item["issue_key"] is not None:
                raise SchemaError("admitted requires block cannot carry an issue key")
        else:
            if item["issue_kind"] not in ("invalid_entry", "missing_final_check"):
                raise SchemaError(f"requires_blocks[{index}].issue_kind is not closed")
            validate_key(item["issue_key"], f"requires_blocks[{index}].issue_key")

    if not isinstance(case["events"], list):
        raise SchemaError("case.events must be an array")
    event_ids: set[str] = set()
    keys: set[tuple[Any, ...]] = set()
    for index, event in enumerate(case["events"]):
        item = _require_mapping(event, f"events[{index}]")
        if item.get("kind") == "declare":
            _validate_declaration(item, f"events[{index}]", builtin=False)
            if item["decl_id"] in declaration_ids:
                raise SchemaError("declaration ids must be unique")
            declaration_ids.add(item["decl_id"])
        elif item.get("kind") == "use":
            _validate_use(item, f"events[{index}]")
        else:
            raise SchemaError(f"events[{index}].kind is not in the closed schema")
        if not isinstance(item["event_id"], str) or not item["event_id"]:
            raise SchemaError(f"events[{index}].event_id must be a nonempty string")
        if item["event_id"] in event_ids:
            raise SchemaError("event ids must be unique")
        event_ids.add(item["event_id"])
        if item["requires_block"] is not None and item["requires_block"] not in block_ids:
            raise SchemaError(f"events[{index}] names an unknown requires block")
        if item["scope"] not in scope_by_id:
            raise SchemaError(f"events[{index}] names an unknown scope")
        if item["kind"] == "declare" and item["visibility_scope"] not in scope_by_id:
            raise SchemaError(f"events[{index}] names an unknown visibility scope")
        key = _wire_key(item["key"])
        if key in keys:
            raise SchemaError("event keys must be unique")
        keys.add(key)
        scope = scope_by_id[item["scope"]]
        if not (_wire_key(scope["open"]) <= key < _wire_key(scope["close"])):
            raise SchemaError(f"events[{index}] lies outside its owning scope")
        if item["kind"] == "declare" and item["decl_kind"] != "function":
            visibility_scope = scope_by_id[item["visibility_scope"]]
            boundary = _wire_key(item["visible_from"])
            if not (
                _wire_key(visibility_scope["open"])
                <= boundary
                < _wire_key(visibility_scope["close"])
            ):
                raise SchemaError(
                    f"events[{index}].visible_from lies outside its visibility scope"
                )

    limits = _require_mapping(case["limits"], "case.limits")
    _require_exact_keys(limits, LIMIT_NAMES, "case.limits")
    for name in LIMIT_NAMES:
        _validate_nonnegative(limits[name], f"case.limits.{name}")

    faults = case["faults"]
    if not isinstance(faults, list):
        raise SchemaError("case.faults must be an array")
    fault_targets: set[tuple[str, str]] = set()
    for index, fault in enumerate(faults):
        item = _require_mapping(fault, f"case.faults[{index}]")
        if item.get("kind") == "count_unrepresentable":
            if item.get("family") == DERIVED_COUNT_FAMILY:
                _require_exact_keys(
                    item,
                    {"kind", "family", "addition"},
                    f"case.faults[{index}]",
                )
                if item["addition"] not in (1, 2, 3):
                    raise SchemaError(
                        f"case.faults[{index}].addition must be 1, 2, or 3"
                    )
            else:
                _require_exact_keys(
                    item,
                    {"kind", "family", "detection_work"},
                    f"case.faults[{index}]",
                )
                _validate_nonnegative(
                    item["detection_work"],
                    f"case.faults[{index}].detection_work",
                )
            if item["family"] not in COUNT_FAMILY_NAMES:
                raise SchemaError(f"case.faults[{index}].family is not closed")
            target = ("family", item["family"])
        else:
            _require_exact_keys(
                item,
                {"kind", "storage"},
                f"case.faults[{index}]",
            )
            if item["kind"] not in ("address_space_exceeded", "allocation_failure"):
                raise SchemaError(f"case.faults[{index}].kind is not closed")
            if item["storage"] not in STORAGE_NAMES:
                raise SchemaError(f"case.faults[{index}].storage is not closed")
            target = (item["kind"], item["storage"])
        if target in fault_targets:
            raise SchemaError("fault targets must be unique")
        fault_targets.add(target)

    return case
