"""Ordered-ledger model for successor resolver diagnostic evidence."""

from __future__ import annotations

from bisect import bisect_left
from typing import Any

from schema import validate_case


_PROFILE_ORDER = (
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


_DECL_DOMAINS = {
    "struct": ("nominal", "constructor"),
    "enum": ("nominal",),
    "variant": ("constructor",),
    "contract": ("contract",),
    "function": ("value",),
    "type_parameter": ("nominal",),
    "const_parameter": ("value",),
    "parameter": ("value",),
    "local": ("value",),
    "requires_local": ("value",),
    "match_binder": ("value",),
    "constant": ("value",),
    "region_parameter": ("region",),
    "region": ("region",),
    "label": ("label",),
}

_USE_ROWS = {
    "type_argument": ("nominal", ("struct", "enum", "type_parameter"), "TYPE-5"),
    "numeric_identity_type": ("nominal", ("type_parameter",), "FORM-5"),
    "construct": ("constructor", ("struct", "variant"), "TYPE-6"),
    "arm_constructor": ("constructor", ("variant",), "TYPE-6"),
    "contract": ("contract", ("contract",), "FN-3"),
    "callee_ident": ("value", ("function",), "OP-1"),
    "callee_opname": ("operation", (), "OP-1"),
    "pbase": (
        "value",
        ("parameter", "local", "requires_local", "match_binder", "constant"),
        "TYPE-5",
    ),
    "const_use": ("value", ("const_parameter", "constant"), "CONST-1"),
    "cvalue": ("value", ("constant",), "CONST-2"),
    "fn_bind_right": ("value", ("function",), "FN-4"),
    "signature_region": ("region", ("region_parameter", "region"), "OWN-3"),
    "region": ("region", ("region_parameter", "region"), "OWN-3"),
    "label": ("label", ("label",), "TYPE-6"),
}

_DEFERRED_ROWS = {
    "match_field_name": "GRAM-10",
    "match_field_order": "GRAM-10",
    "match_variant_relation": "TYPE-6",
    "construct_field_name": "GRAM-8",
    "call_argument_name": "GRAM-11",
    "contract_member": "FN-3",
    "law_role": "FN-4",
}

_DOMAIN_ORDER = {
    "value": 0,
    "nominal": 1,
    "constructor": 2,
    "contract": 3,
    "region": 4,
    "label": 5,
}

_CLASS_ORDER = (
    "function",
    "struct",
    "enum",
    "variant",
    "contract",
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

_DECLARATION_CLASS = {
    "function": "function",
    "constant": "named-const",
    "const_parameter": "const-generic",
    "parameter": "value",
    "local": "value",
    "requires_local": "value",
    "match_binder": "value",
    "type_parameter": "generic-type",
    "struct": "nominal-type",
    "enum": "nominal-type",
    "variant": "enum-variant",
    "contract": "contract",
    "region_parameter": "region",
    "region": "region",
    "label": "label",
}

_PAYLOAD_CLASS_ORDER = (
    "function",
    "named-const",
    "const-generic",
    "value",
    "generic-type",
    "nominal-type",
    "struct-constructor",
    "enum-variant",
    "contract",
    "region",
    "label",
    "operation-family",
)

_GLOBAL_KINDS = {
    "struct",
    "enum",
    "variant",
    "contract",
    "function",
    "constant",
}

_STORAGE_ORDER = (
    "declarations",
    "scopes",
    "declaration_events",
    "lexical_uses",
    "deferred_uses",
    "lookup_entries",
    "coverage_records",
    "ordering_scratch",
    "diagnostic_issue_data",
)


def _binding_class(binding: dict[str, Any]) -> str:
    if binding["decl_kind"] == "struct" and binding["domain"] == "constructor":
        return "struct-constructor"
    return _DECLARATION_CLASS[binding["decl_kind"]]


def _admissible_classes(domain: str, kinds: tuple[str, ...]) -> list[str]:
    classes = {
        (
            "struct-constructor"
            if kind == "struct" and domain == "constructor"
            else _DECLARATION_CLASS[kind]
        )
        for kind in kinds
    }
    return [name for name in _PAYLOAD_CLASS_ORDER if name in classes]


def _key(item: dict[str, Any]) -> tuple[Any, ...]:
    key = item["key"]
    return (
        key["source"],
        key["start"],
        key["end"],
        tuple(key["path"]),
        key["role"],
        key["subtoken"],
    )


def _event_key(item: dict[str, Any]) -> dict[str, Any]:
    key = item["key"]
    return {
        "source": key["source"],
        "start": key["start"],
        "end": key["end"],
        "path": list(key["path"]),
        "role": key["role"],
        "subtoken": key["subtoken"],
    }


def _resource(
    kind: str,
    counts: dict[str, int],
    **details: Any,
) -> dict[str, Any]:
    return {"status": "resource_failure", "kind": kind, **details, "resources": counts}


def _payload_origin_groups(
    issue: dict[str, Any],
) -> list[tuple[bool, list[dict[str, Any]]]]:
    """Return fixed slots and abstract matched ranges in payload order."""

    groups: list[tuple[bool, list[dict[str, Any]]]] = []
    conflicts = [
        conflict["conflicting_origin"] for conflict in issue.get("conflicts", [])
    ]
    if conflicts:
        groups.append((True, conflicts))
    gram10 = issue.get("gram10")
    if gram10 is not None:
        if gram10["earlier_binder_origin"] is not None:
            groups.append((False, [gram10["earlier_binder_origin"]]))
        if gram10["arm_entry_live_origins"]:
            groups.append((True, list(gram10["arm_entry_live_origins"])))
    if issue.get("prior_origin") is not None:
        groups.append((False, [issue["prior_origin"]]))
    if issue.get("invisible_origins"):
        groups.append((True, list(issue["invisible_origins"])))
    if issue.get("label_origins"):
        groups.append((True, list(issue["label_origins"])))
    return groups


def _walk_payload_origins(
    issue: dict[str, Any],
    spend: Any,
    phase: str,
    *,
    write_descriptors: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Run the evidence subset's fixed-origin/range iterator once."""

    emitted: list[dict[str, Any]] = []
    for is_range, values in _payload_origin_groups(issue):
        if not is_range:
            for origin in values:
                failure = spend(1, phase)  # accepted fixed origin
                if failure:
                    return [], failure
                if write_descriptors:
                    failure = spend(1, phase)
                    if failure:
                        return [], failure
                emitted.append(origin)
            continue

        # The bounded evidence schema collapses each payload group to at most
        # one PRE-1 range and one source range.  This still exercises every
        # charged iterator action without pretending to cover all production
        # partition/class heads.
        ranges = [
            [origin for origin in values if origin["kind"] == "pre1"],
            [origin for origin in values if origin["kind"] == "source"],
        ]
        cursors = [0, 0]
        while any(cursors[index] < len(ranges[index]) for index in (0, 1)):
            active = [
                index for index in (0, 1) if cursors[index] < len(ranges[index])
            ]
            if len(active) == 2:
                failure = spend(1, phase)  # reached fixed-head comparison
                if failure:
                    return [], failure
            selected = active[0]  # PRE-1 range is normatively first
            origin = ranges[selected][cursors[selected]]
            cursors[selected] += 1
            for _action in ("range_entry", "self_exclusion", "accepted_origin"):
                failure = spend(1, phase)
                if failure:
                    return [], failure
            if write_descriptors:
                failure = spend(1, phase)
                if failure:
                    return [], failure
            emitted.append(origin)
    return emitted, None


def _depths(scopes: dict[str, dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for scope_id in scopes:
        depth = 0
        cursor = scopes[scope_id]
        while cursor["parent"] is not None:
            depth += 1
            cursor = scopes[cursor["parent"]]
        result[scope_id] = depth
    return result


def _ancestors(scope_id: str, scopes: dict[str, dict[str, Any]]) -> list[str]:
    result = [scope_id]
    while scopes[result[-1]]["parent"] is not None:
        result.append(scopes[result[-1]]["parent"])
    return result


def _expanded(
    item: dict[str, Any], builtin: bool, builtin_ordinal: int | None = None
) -> list[dict[str, Any]]:
    return [
        {
            "decl_id": item["decl_id"],
            "decl_kind": item["decl_kind"],
            "spelling": item["spelling"],
            "domain": domain,
            "scope": "unit" if builtin else item["visibility_scope"],
            "key": None if builtin else _key(item),
            "builtin": builtin,
            "whole_unit": builtin or item["decl_kind"] == "function",
            "arm_id": None if builtin else item["arm_id"],
            "field_spelling": None if builtin else item["field_spelling"],
            "owner_path": () if builtin else tuple(
                (component["kind"], component["id"])
                for component in item["owner_path"]
            ),
            "event": None if builtin else item,
            "builtin_ordinal": builtin_ordinal,
            "visible_from": None if builtin or item["decl_kind"] == "function" else (
                item["visible_from"]["source"],
                item["visible_from"]["start"],
                item["visible_from"]["end"],
                tuple(item["visible_from"]["path"]),
                item["visible_from"]["role"],
                item["visible_from"]["subtoken"],
            ),
            "loop_id": None if builtin else item["loop_id"],
        }
        for domain in _DECL_DOMAINS[item["decl_kind"]]
    ]


def _origin(binding: dict[str, Any]) -> dict[str, Any]:
    if binding["builtin"]:
        return {
            "kind": "pre1",
            "declaration_ordinal": binding["builtin_ordinal"],
            "decl_id": binding["decl_id"],
            "decl_kind": binding["decl_kind"],
        }
    return {
        "kind": "source",
        "event_id": binding["event"]["event_id"],
        "event_key": _event_key(binding["event"]),
    }


def _visible(
    binding: dict[str, Any],
    use: dict[str, Any],
    ancestors: list[str],
    scopes: dict[str, dict[str, Any]],
) -> bool:
    if not _owner_accessible(binding, use):
        return False
    if binding["scope"] not in ancestors:
        return False
    if not binding["whole_unit"] and binding["visible_from"] > _key(use):
        return False
    close = scopes[binding["scope"]]["close"]
    close_key = (
        close["source"],
        close["start"],
        close["end"],
        tuple(close["path"]),
        close["role"],
        close["subtoken"],
    )
    return _key(use) < close_key


def _event_owner(item: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(
        (component["kind"], component["id"])
        for component in item["owner_path"]
    )


def _is_prefix(
    prefix: tuple[tuple[str, str], ...],
    complete: tuple[tuple[str, str], ...],
) -> bool:
    return complete[: len(prefix)] == prefix


def _owner_accessible(binding: dict[str, Any], event: dict[str, Any]) -> bool:
    return (
        binding["builtin"]
        or binding["decl_kind"] in _GLOBAL_KINDS
        or _is_prefix(binding["owner_path"], _event_owner(event))
    )


def _prior_can_conflict(
    prior: dict[str, Any], candidate: dict[str, Any]
) -> bool:
    if prior["builtin"] or prior["decl_kind"] in _GLOBAL_KINDS:
        return True
    if candidate["decl_kind"] in _GLOBAL_KINDS:
        return False
    return _is_prefix(prior["owner_path"], candidate["owner_path"])


def _function_identity(owner: tuple[tuple[str, str], ...]) -> str | None:
    for kind, identity in owner:
        if kind == "function":
            return identity
    return None


_EVIDENCE_DOMAIN_ORDER = {
    "value": 0,
    "nominal": 1,
    "constructor": 2,
    "contract": 3,
    "region": 4,
    "label": 5,
    "operation": 6,
}


def _dense_ids(values: list[Any]) -> dict[Any, int]:
    return {value: index + 1 for index, value in enumerate(sorted(set(values)))}


def _lookup_work_rows(
    case: dict[str, Any],
    declarations: list[dict[str, Any]],
    event_ordinals: dict[str, int],
    event_positions: list[tuple[Any, ...]],
) -> list[dict[str, Any]]:
    owners = [
        tuple((item["kind"], item["id"]) for item in declaration["owner_path"])
        for declaration in declarations
    ]
    owner_ids = _dense_ids(owners)
    scope_ids = _dense_ids([declaration["visibility_scope"] for declaration in declarations])
    arm_ids = _dense_ids(
        [declaration["arm_id"] for declaration in declarations if declaration["arm_id"]]
    )
    rows: list[dict[str, Any]] = []
    for builtin in case["builtins"]:
        for carried_ordinal, domain in enumerate(_DECL_DOMAINS[builtin["decl_kind"]]):
            rows.append(
                {
                    "source": False,
                    "decl_kind": builtin["decl_kind"],
                    "domain": _EVIDENCE_DOMAIN_ORDER[domain],
                    "spelling": builtin["spelling"].encode("utf-8"),
                    "partition_kind": 0,
                    "partition_id": 0,
                    "owner_key": (),
                    "function_id": None,
                    "scope_id": 0,
                    "owner_id": 0,
                    "arm_id": 0,
                    "event": builtin["declaration_ordinal"],
                    "carried_ordinal": carried_ordinal,
                    "origin_kind": 0,
                    "class": _PAYLOAD_CLASS_ORDER.index(
                        _binding_class({"decl_kind": builtin["decl_kind"], "domain": domain})
                    ),
                    "visibility_start": 0,
                    "origin_order": builtin["declaration_ordinal"],
                }
            )
    for operation in case["operations"]:
        rows.append(
            {
                "source": False,
                "decl_kind": "operation",
                "domain": _EVIDENCE_DOMAIN_ORDER["operation"],
                "spelling": operation["spelling"].encode("utf-8"),
                "partition_kind": 0,
                "partition_id": 0,
                "owner_key": (),
                "function_id": None,
                "scope_id": 0,
                "owner_id": 0,
                "arm_id": 0,
                "event": operation["ordinal"],
                "carried_ordinal": 0,
                "origin_kind": 1,
                "class": _PAYLOAD_CLASS_ORDER.index("operation-family"),
                "visibility_start": 0,
                "origin_order": operation["ordinal"],
            }
        )
    for declaration in declarations:
        owner = tuple(
            (item["kind"], item["id"]) for item in declaration["owner_path"]
        )
        function_id = _function_identity(owner)
        for carried_ordinal, domain in enumerate(_DECL_DOMAINS[declaration["decl_kind"]]):
            if domain == "label":
                partition_kind = 2
                partition_id = owner_ids.get((('function', function_id),), 0)
            elif owner:
                partition_kind = 1
                partition_id = owner_ids[owner]
            else:
                partition_kind = 0
                partition_id = 0
            event = event_ordinals[declaration["event_id"]]
            rows.append(
                {
                    "source": True,
                    "decl_kind": declaration["decl_kind"],
                    "domain": _EVIDENCE_DOMAIN_ORDER[domain],
                    "spelling": declaration["spelling"].encode("utf-8"),
                    "partition_kind": partition_kind,
                    "partition_id": partition_id,
                    "owner_key": owner,
                    "function_id": function_id,
                    "scope_id": scope_ids[declaration["visibility_scope"]],
                    "owner_id": owner_ids[owner],
                    "arm_id": arm_ids.get(declaration["arm_id"], 0),
                    "event": event,
                    "carried_ordinal": carried_ordinal,
                    "origin_kind": 2,
                    "class": _PAYLOAD_CLASS_ORDER.index(
                        _binding_class({"decl_kind": declaration["decl_kind"], "domain": domain})
                    ),
                    "visibility_start": (
                        0
                        if declaration["decl_kind"] == "function"
                        else bisect_left(
                            event_positions,
                            (
                                declaration["visible_from"]["source"],
                                declaration["visible_from"]["start"],
                                declaration["visible_from"]["end"],
                                tuple(declaration["visible_from"]["path"]),
                                declaration["visible_from"]["role"],
                                declaration["visible_from"]["subtoken"],
                            ),
                        )
                    ),
                    "origin_order": event,
                }
            )
    return rows


def _sort_key(row: dict[str, Any], ordering: str, *, prefix: bool = False) -> tuple[Any, ...]:
    if ordering == "same_scope":
        key = (
            0 if row["source"] else 1,
            row["partition_id"],
            row["scope_id"],
            row["domain"],
            row["spelling"],
            row["event"],
            row["carried_ordinal"],
        )
        return key[:5] if prefix else key
    if ordering == "region_owner":
        key = (
            0 if row["source"] and row["domain"] == 4 else 1,
            row["owner_id"],
            row["spelling"],
            row["event"],
        )
        return key[:3] if prefix else key
    if ordering == "arm_binder":
        key = (
            0 if row["source"] and row["decl_kind"] == "match_binder" else 1,
            row["arm_id"],
            row["spelling"],
            row["event"],
        )
        return key[:3] if prefix else key
    return (
        row["partition_kind"],
        row["partition_id"],
        row["domain"],
        row["spelling"],
        row["origin_kind"],
        row["class"],
        row["visibility_start"],
        row["origin_order"],
    )


def _charged_compare(
    left: tuple[Any, ...], right: tuple[Any, ...], spend: Any, phase: str
) -> tuple[int, dict[str, Any] | None]:
    for left_part, right_part in zip(left, right):
        if isinstance(left_part, bytes):
            shorter = min(len(left_part), len(right_part))
            for index in range(shorter):
                failure = spend(1, phase)
                if failure:
                    return 0, failure
                if left_part[index] != right_part[index]:
                    return (-1 if left_part[index] < right_part[index] else 1), None
            failure = spend(1, phase)
            if failure:
                return 0, failure
            if len(left_part) != len(right_part):
                return (-1 if len(left_part) < len(right_part) else 1), None
        else:
            failure = spend(1, phase)
            if failure:
                return 0, failure
            if left_part != right_part:
                return (-1 if left_part < right_part else 1), None
    return 0, None


def _stable_lookup_sort(
    rows: list[dict[str, Any]], ordering: str, spend: Any
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    scratch: list[dict[str, Any]] = []
    for row in rows:
        failure = spend(1, f"{ordering}_scratch_copy")
        if failure:
            return [], failure
        scratch.append(row)
    source = scratch
    width = 1
    passes = 0
    while width < len(source):
        destination: list[dict[str, Any]] = []
        for start in range(0, len(source), 2 * width):
            left = start
            split = min(start + width, len(source))
            right = split
            end = min(start + 2 * width, len(source))
            while left < split and right < end:
                comparison, failure = _charged_compare(
                    _sort_key(source[left], ordering),
                    _sort_key(source[right], ordering),
                    spend,
                    f"{ordering}_comparison",
                )
                if failure:
                    return [], failure
                selected = source[left] if comparison <= 0 else source[right]
                left += int(comparison <= 0)
                right += int(comparison > 0)
                failure = spend(1, f"{ordering}_write")
                if failure:
                    return [], failure
                destination.append(selected)
            for cursor in list(range(left, split)) + list(range(right, end)):
                failure = spend(1, f"{ordering}_write")
                if failure:
                    return [], failure
                destination.append(source[cursor])
        source = destination
        width = min(width * 2, len(source))
        passes += 1
    if passes > 0 and passes % 2 == 0:
        for _row in source:
            failure = spend(1, f"{ordering}_final_copy")
            if failure:
                return [], failure
    return source, None


def _run_lookup_orderings(
    rows: list[dict[str, Any]], spend: Any
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    current = list(rows)
    for _row in current:
        failure = spend(1, "lookup_append")
        if failure:
            return [], failure
    for ordering in ("same_scope", "region_owner", "arm_binder", "lookup"):
        current, failure = _stable_lookup_sort(current, ordering, spend)
        if failure:
            return [], failure
        if ordering == "lookup":
            continue
        for index in range(1, len(current)):
            comparison, failure = _charged_compare(
                _sort_key(current[index - 1], ordering, prefix=True),
                _sort_key(current[index], ordering, prefix=True),
                spend,
                f"{ordering}_prefix",
            )
            if failure:
                return [], failure
            if comparison == 0 and _sort_key(current[index], ordering)[0] == 0:
                failure = spend(1, f"{ordering}_predecessor_write")
                if failure:
                    return [], failure
    return current, None


def _query_domains(role: str) -> tuple[int, ...]:
    if role == "callee_ident":
        return (6, 0)
    if role == "callee_opname":
        return (6,)
    return (_EVIDENCE_DOMAIN_ORDER[_USE_ROWS[role][0]],)


def _charge_lookup_query(
    rows: list[dict[str, Any]],
    use: dict[str, Any],
    use_ordinal: int,
    spend: Any,
) -> dict[str, Any] | None:
    spelling = use["spelling"].encode("utf-8")
    use_owner = tuple((item["kind"], item["id"]) for item in use["owner_path"])
    if use["role_kind"] == "label":
        function_id = _function_identity(use_owner)
        applicable = {
            (row["partition_kind"], row["partition_id"])
            for row in rows
            if row["partition_kind"] == 2 and row["function_id"] == function_id
        }
    else:
        applicable = {(0, 0)}
        applicable.update(
            (row["partition_kind"], row["partition_id"])
            for row in rows
            if row["partition_kind"] == 1
            and use_owner[: len(row["owner_key"])] == row["owner_key"]
        )
    partition_ranges: list[tuple[int, int]] = []
    start = 0
    while start < len(rows):
        partition = (rows[start]["partition_kind"], rows[start]["partition_id"])
        end = start + 1
        while end < len(rows) and (
            rows[end]["partition_kind"], rows[end]["partition_id"]
        ) == partition:
            end += 1
        if partition in applicable:
            partition_ranges.append((start, end))
        start = end
    for domain in _query_domains(use["role_kind"]):
        for partition_start, partition_end in partition_ranges:
            for upper in (False, True):
                lo, hi = partition_start, partition_end
                while lo < hi:
                    mid = lo + (hi - lo) // 2
                    failure = spend(1, "lookup_probe")
                    if failure:
                        return failure
                    comparison, failure = _charged_compare(
                        (rows[mid]["domain"], rows[mid]["spelling"]),
                        (domain, spelling),
                        spend,
                        "lookup_key_comparison",
                    )
                    if failure:
                        return failure
                    if comparison < 0 or (upper and comparison == 0):
                        lo = mid + 1
                    else:
                        hi = mid
                if not upper:
                    lower = lo
                else:
                    upper_bound = lo
            if lower < upper_bound:
                lo, hi = lower, upper_bound
                while lo < hi:
                    mid = lo + (hi - lo) // 2
                    failure = spend(1, "visibility_probe")
                    if failure:
                        return failure
                    failure = spend(1, "visibility_start_comparison")
                    if failure:
                        return failure
                    if rows[mid]["visibility_start"] <= use_ordinal:
                        lo = mid + 1
                    else:
                        hi = mid
    return None


def run(raw_case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one validated abstract role stream."""

    case = validate_case(raw_case)
    scopes = {scope["id"]: scope for scope in case["scopes"]}
    depths = _depths(scopes)
    rejected_blocks = {
        block["block_id"]
        for block in case["requires_blocks"]
        if block["issue_kind"] is not None
    }
    semantic_events = [
        event
        for event in case["events"]
        if event["requires_block"] not in rejected_blocks
    ]
    ordered_events = sorted(semantic_events, key=_key)
    declarations = [event for event in ordered_events if event["kind"] == "declare"]
    uses = [event for event in ordered_events if event["kind"] == "use"]
    event_ordinals = {
        event["event_id"]: ordinal for ordinal, event in enumerate(ordered_events)
    }
    event_positions = [_key(event) for event in ordered_events]
    lexical = [event for event in uses if event["role_kind"] in _USE_ROWS]
    deferred = [event for event in uses if event["role_kind"] in _DEFERRED_ROWS]
    source_bindings = sum(len(_DECL_DOMAINS[event["decl_kind"]]) for event in declarations)
    builtin_bindings = sum(len(_DECL_DOMAINS[item["decl_kind"]]) for item in case["builtins"])
    role_events = declarations + uses
    measured_counts = {
        "declarations": len(case["builtins"]) + len(declarations),
        "scopes": len(scopes),
        "scope_depth": max(depths.values()),
        "declaration_events": len(declarations),
        "lexical_uses": len(lexical),
        "deferred_uses": len(deferred),
        "spelling_bytes": sum(len(item["spelling"].encode("utf-8")) for item in case["builtins"])
        + sum(len(operation["spelling"].encode("utf-8")) for operation in case["operations"])
        + sum(len(item["spelling"].encode("utf-8")) for item in case["reservations"])
        + sum(len(item["spelling"].encode("utf-8")) for item in role_events),
        "lookup_entries": builtin_bindings + source_bindings + len(case["operations"]),
        "ancestry_steps": max(0, len(scopes) - 1),
        "node_path_depth": max(
            [len(event["key"]["path"]) for event in role_events]
            + [
                len((block["issue_key"] or block["block_key"])["path"])
                for block in case["requires_blocks"]
            ]
            + [0]
        ),
        "diagnostic_origins": 0,
        "diagnostic_paths": 0,
        "diagnostic_path_components": 0,
        "coverage_records": len(role_events),
        "work": 0,
    }

    counts = {name: 0 for name in _PROFILE_ORDER}

    def spend(amount: int, phase: str) -> dict[str, Any] | None:
        maximum = case["limits"]["work"]
        if counts["work"] + amount > maximum:
            counts["work"] = maximum + 1
            return _resource(
                "limit_exceeded",
                counts,
                limit="work",
                maximum=maximum,
                actual=counts["work"],
                phase=phase,
            )
        counts["work"] += amount
        return None

    def publish_issue(issue: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        stop = spend(1, "diagnostic_count")
        if stop:
            return stop
        origins, stop = _walk_payload_origins(
            issue, spend, "diagnostic_count", write_descriptors=False
        )
        if stop:
            return stop
        source_origins = [origin for origin in origins if origin["kind"] == "source"]
        paths = [event["key"]["path"]] + [
            origin["event_key"]["path"] for origin in source_origins
        ]
        counts["node_path_depth"] = max(
            counts["node_path_depth"], max((len(path) for path in paths), default=0)
        )
        counts["diagnostic_origins"] = len(origins)
        counts["diagnostic_paths"] = len(paths)
        counts["diagnostic_path_components"] = sum(len(path) for path in paths)
        for family in (
            "node_path_depth",
            "diagnostic_origins",
            "diagnostic_paths",
            "diagnostic_path_components",
        ):
            if counts[family] > case["limits"][family]:
                return _resource(
                    "limit_exceeded",
                    counts,
                    limit=family,
                    maximum=case["limits"][family],
                    actual=counts[family],
                    phase="diagnostic_count",
                )
        derived_fault = next(
            (
                fault
                for fault in case["faults"]
                if fault["kind"] == "count_unrepresentable"
                and fault["family"] == "diagnostic_issue_elements"
            ),
            None,
        )
        element_count = 0
        for addition, amount in enumerate(
            (
                1 + counts["diagnostic_origins"],
                counts["diagnostic_paths"],
                counts["diagnostic_path_components"],
            ),
            start=1,
        ):
            if derived_fault is not None and derived_fault["addition"] == addition:
                return _resource(
                    "count_unrepresentable",
                    counts,
                    family="diagnostic_issue_elements",
                )
            element_count += amount
        diagnostic_faults = [
            fault
            for fault in case["faults"]
            if fault.get("storage") == "diagnostic_issue_data"
        ]
        if diagnostic_faults:
            address_faults = [
                fault
                for fault in diagnostic_faults
                if fault["kind"] == "address_space_exceeded"
            ]
            fault = (address_faults or diagnostic_faults)[0]
            return _resource(
                fault["kind"],
                counts,
                storage="diagnostic_issue_data",
                requested_elements=element_count,
            )
        stop = spend(1, "diagnostic_materialization")
        if stop:
            return stop
        descriptors, stop = _walk_payload_origins(
            issue, spend, "diagnostic_materialization", write_descriptors=True
        )
        if stop:
            return stop
        stop = spend(1 + len(event["key"]["path"]), "diagnostic_materialization")
        if stop:
            return stop
        for descriptor in descriptors:
            stop = spend(1, "diagnostic_materialization")
            if stop:
                return stop
            if descriptor["kind"] == "source":
                stop = spend(
                    1 + len(descriptor["event_key"]["path"]),
                    "diagnostic_materialization",
                )
                if stop:
                    return stop
        return issue

    stop = spend(len(case["requires_blocks"]), "structural_admission")
    if stop:
        return stop
    structural_issues = [
        block for block in case["requires_blocks"] if block["issue_kind"] is not None
    ]
    if structural_issues:
        block = min(
            structural_issues,
            key=lambda item: (
                item["issue_key"]["source"],
                item["issue_key"]["start"],
                item["issue_key"]["end"],
                tuple(item["issue_key"]["path"]),
            ),
        )
        event = {"key": block["issue_key"]}
        return publish_issue(
            {
                "status": "source_issue",
                "phase": "structural_admission",
                "rule": "FN-8",
                "reason": block["issue_kind"],
                "event_id": block["block_id"],
                "event_key": _event_key(event),
                "conflicts": [],
                "gram10": None,
                "prior_origin": None,
                "invisible_origins": [],
                "label_origins": [],
                "resources": counts,
            },
            event,
        )

    admission_work = counts["work"]
    counts = measured_counts
    counts["work"] = admission_work

    preflight_work = (
        counts["work"]
        + counts["scopes"]
        + counts["declarations"]
        + len(role_events)
        + counts["lookup_entries"]
    )
    count_faults = sorted(
        (
            fault
            for fault in case["faults"]
            if fault["kind"] == "count_unrepresentable"
            and fault["family"] != "diagnostic_issue_elements"
        ),
        key=lambda fault: (fault["detection_work"], _PROFILE_ORDER.index(fault["family"])),
    )
    if count_faults and count_faults[0]["detection_work"] <= preflight_work:
        fault = count_faults[0]
        if case["limits"]["work"] < fault["detection_work"]:
            counts["work"] = case["limits"]["work"] + 1
            return _resource(
                "limit_exceeded",
                counts,
                limit="work",
                maximum=case["limits"]["work"],
                actual=counts["work"],
                phase="preflight",
            )
        counts["work"] = fault["detection_work"]
        return _resource(
            "count_unrepresentable",
            counts,
            family=fault["family"],
        )
    if preflight_work > case["limits"]["work"]:
        counts["work"] = case["limits"]["work"] + 1
        return _resource(
            "limit_exceeded",
            counts,
            limit="work",
            maximum=case["limits"]["work"],
            actual=counts["work"],
            phase="preflight",
        )
    counts["work"] = preflight_work
    for name in _PROFILE_ORDER:
        if name in (
            "diagnostic_origins",
            "diagnostic_paths",
            "diagnostic_path_components",
            "work",
        ):
            continue
        if counts[name] > case["limits"][name]:
            return _resource(
                "limit_exceeded",
                counts,
                limit=name,
                maximum=case["limits"][name],
                actual=counts[name],
                phase="preflight",
            )
    capacities = {
        "declarations": counts["declarations"],
        "scopes": counts["scopes"],
        "declaration_events": counts["declaration_events"],
        "lexical_uses": counts["lexical_uses"],
        "deferred_uses": counts["deferred_uses"],
        "lookup_entries": counts["lookup_entries"],
        "coverage_records": counts["coverage_records"],
        "ordering_scratch": counts["lookup_entries"],
    }
    pre_diagnostic_faults = [
        fault
        for fault in case["faults"]
        if fault["kind"] != "count_unrepresentable"
        and fault["storage"] != "diagnostic_issue_data"
        and capacities[fault["storage"]] > 0
    ]
    address_faults = [
        fault for fault in pre_diagnostic_faults
        if fault["kind"] == "address_space_exceeded"
    ]
    allocation_faults = [
        fault for fault in pre_diagnostic_faults
        if fault["kind"] == "allocation_failure"
    ]
    if address_faults or allocation_faults:
        fault = min(
            address_faults or allocation_faults,
            key=lambda item: _STORAGE_ORDER.index(item["storage"]),
        )
        return _resource(
            fault["kind"],
            counts,
            storage=fault["storage"],
            requested_elements=capacities[fault["storage"]],
        )

    lookup_work_rows = _lookup_work_rows(
        case, declarations, event_ordinals, event_positions
    )
    if len(lookup_work_rows) != counts["lookup_entries"]:
        raise AssertionError("lookup work projection disagrees with preflight count")
    lookup_work_rows, ordering_failure = _run_lookup_orderings(
        lookup_work_rows, spend
    )
    if ordering_failure:
        return ordering_failure

    stop = spend(len(case["operations"]) + len(case["reservations"]), "inventory")
    if stop:
        return stop

    builtin_entries: list[dict[str, Any]] = []
    for item in case["builtins"]:
        stop = spend(1 + len(_DECL_DOMAINS[item["decl_kind"]]), "inventory")
        if stop:
            return stop
        builtin_entries.extend(
            _expanded(item, True, item["declaration_ordinal"])
        )

    entries: list[dict[str, Any]] = []
    whole_unit_functions = [
        binding
        for declaration in declarations
        if declaration["decl_kind"] == "function"
        for binding in _expanded(declaration, False)
    ]
    for declaration in declarations:
        stop = spend(1 + len(_DECL_DOMAINS[declaration["decl_kind"]]), "inventory")
        if stop:
            return stop
    for declaration in declarations:
        domains = _DECL_DOMAINS[declaration["decl_kind"]]
        current = _expanded(declaration, False)
        issues: list[tuple[int, int, str, str, dict[str, Any] | None]] = []
        ancestors = _ancestors(declaration["scope"], scopes)
        for binding in current:
            normalized = (
                binding["spelling"][1:]
                if binding["decl_kind"] in ("region", "region_parameter")
                and binding["spelling"].startswith("'")
                else binding["spelling"]
            )
            reservation_applies = binding["decl_kind"] in (
                "function",
                "parameter",
                "local",
                "requires_local",
                "match_binder",
                "constant",
                "region_parameter",
                "region",
            )
            reservations = [
                reservation
                for reservation in case["reservations"]
                if reservation_applies and reservation["spelling"] == normalized
            ]
            for reservation in reservations:
                issues.append((0, _DOMAIN_ORDER[binding["domain"]], "reserved_name", binding["domain"], reservation))
            if (
                binding["decl_kind"] == "match_binder"
                and binding["spelling"] == binding["field_spelling"]
            ):
                issues.append(
                    (2, _DOMAIN_ORDER[binding["domain"]], "binder_equals_written_field", binding["domain"], None)
                )
            for prior in builtin_entries:
                if prior["domain"] == binding["domain"] and prior["spelling"] == binding["spelling"]:
                    issues.append((3, _DOMAIN_ORDER[binding["domain"]], "reserved_collision", binding["domain"], prior))
            if binding["scope"] != "unit" and binding["decl_kind"] != "function":
                for function in whole_unit_functions:
                    if (
                        function["decl_id"] != binding["decl_id"]
                        and function["domain"] == binding["domain"]
                        and function["spelling"] == binding["spelling"]
                    ):
                        if binding["decl_kind"] == "match_binder":
                            issues.append(
                                (2, _DOMAIN_ORDER[binding["domain"]], "binder_collides_arm_entry", binding["domain"], function)
                            )
                        elif function["key"] > binding["key"]:
                            issues.append(
                                (5, _DOMAIN_ORDER[binding["domain"]], "shadow_live_name", binding["domain"], function)
                            )
            for prior in entries:
                if prior["domain"] != binding["domain"] or prior["spelling"] != binding["spelling"]:
                    continue
                if binding["domain"] == "region":
                    if prior["owner_path"] == binding["owner_path"]:
                        issues.append(
                            (1, _DOMAIN_ORDER[binding["domain"]], "repeated_region", binding["domain"], prior)
                    )
                    continue
                if not _prior_can_conflict(prior, binding):
                    continue
                if (
                    prior["decl_kind"] == "match_binder"
                    and binding["decl_kind"] == "match_binder"
                    and prior["arm_id"] == binding["arm_id"]
                ):
                    reason = "duplicate_match_binder"
                elif binding["decl_kind"] == "match_binder" and (
                    prior["scope"] == binding["scope"]
                    or prior["whole_unit"]
                    or prior["scope"] in ancestors
                ):
                    reason = "binder_collides_arm_entry"
                elif prior["scope"] == binding["scope"]:
                    reason = "duplicate_binding"
                elif prior["whole_unit"]:
                    reason = "shadow_live_name"
                elif prior["scope"] in ancestors and prior["key"] < binding["key"]:
                    reason = "shadow_live_name"
                else:
                    continue
                if reason in ("duplicate_match_binder", "binder_collides_arm_entry"):
                    rank = 2
                elif reason == "duplicate_binding":
                    rank = 4
                else:
                    rank = 5
                issues.append((rank, _DOMAIN_ORDER[binding["domain"]], reason, binding["domain"], prior))
        if issues:
            rank, _, reason, domain, prior = min(
                issues, key=lambda issue: (issue[0], issue[1])
            )
            if reason == "reserved_name":
                rule = "FORM-3"
            elif reason == "repeated_region":
                rule = "OWN-3"
            elif declaration["decl_kind"] == "match_binder":
                rule = "GRAM-10"
            else:
                rule = "TYPE-6"
            conflicts = []
            if rank in (3, 4, 5) and rule == "TYPE-6":
                conflicts = [
                    {
                        "domain": issue[3],
                        "declaration_class": _binding_class(issue[4]),
                        "conflicting_origin": _origin(issue[4]),
                    }
                    for issue in sorted(
                        issues,
                        key=lambda issue: (
                            issue[1],
                            (-1, issue[4]["builtin_ordinal"])
                            if issue[4] is not None and issue[4]["builtin"]
                            else issue[4]["key"] if issue[4] is not None else (),
                        ),
                    )
                    if issue[0] == rank and issue[4] is not None
                ]
            reservation_payload = None
            if reason == "reserved_name" and prior is not None:
                reservation_payload = {
                    "spelling": normalized,
                    "declaration_role": declaration["decl_kind"],
                    "reserved_class": prior["reserved_class"],
                    "inventory_ordinal": prior["inventory_ordinal"],
                }
            gram10_payload = None
            if rule == "GRAM-10":
                earlier_binders = sorted(
                    (
                        binding
                        for binding in entries
                        if binding["decl_kind"] == "match_binder"
                        and binding["arm_id"] == declaration["arm_id"]
                        and binding["spelling"] == declaration["spelling"]
                    ),
                    key=lambda binding: binding["key"],
                )
                live_by_declaration = {
                    binding["decl_id"]: binding
                    for binding in entries + whole_unit_functions
                    if binding["domain"] == "value"
                    and not (
                        binding["decl_kind"] == "match_binder"
                        and binding["arm_id"] == declaration["arm_id"]
                    )
                    and binding["spelling"] == declaration["spelling"]
                    and _visible(binding, declaration, ancestors, scopes)
                }
                arm_entry_live = sorted(
                    live_by_declaration.values(), key=lambda binding: binding["key"]
                )
                gram10_payload = {
                    "binder_spelling": declaration["spelling"],
                    "paired_field_spelling": declaration["field_spelling"],
                    "earlier_binder_origin": (
                        _origin(earlier_binders[0]) if earlier_binders else None
                    ),
                    "arm_entry_live_origins": [
                        _origin(binding) for binding in arm_entry_live
                    ],
                }
            return publish_issue({
                "status": "source_issue",
                "phase": "inventory",
                "rule": rule,
                "reason": reason,
                "event_id": declaration["event_id"],
                "event_key": _event_key(declaration),
                "spelling": declaration["spelling"],
                "domain": domain,
                "conflicts": conflicts,
                "gram10": gram10_payload,
                "prior_origin": _origin(prior) if reason == "repeated_region" and prior else None,
                "reservation": reservation_payload,
                "invisible_origins": [],
                "label_origins": [],
                "resources": counts,
            }, declaration)
        entries.extend(current)

    all_entries = builtin_entries + entries
    by_scope: dict[str, list[dict[str, Any]]] = {scope_id: [] for scope_id in scopes}
    for binding in all_entries:
        by_scope[binding["scope"]].append(binding)
    resolutions: list[dict[str, Any]] = []
    deferred_records: list[dict[str, Any]] = []
    for use in uses:
        stop = spend(1, "resolution")
        if stop:
            return stop
        role = use["role_kind"]
        if role in _DEFERRED_ROWS:
            stop = spend(1, "resolution")
            if stop:
                return stop
            deferred_records.append(
                {
                    "event_id": use["event_id"],
                    "event_key": _event_key(use),
                    "role_kind": role,
                    "spelling": use["spelling"],
                    "surface": use["surface"],
                    "rule": _DEFERRED_ROWS[role],
                }
            )
            continue
        stop = _charge_lookup_query(
            lookup_work_rows, use, event_ordinals[use["event_id"]], spend
        )
        if stop:
            return stop
        if role in ("callee_ident", "callee_opname"):
            token_class = "ident" if role == "callee_ident" else "opname"
            operation = next(
                (
                    operation
                    for operation in case["operations"]
                    if operation["spelling"] == use["spelling"]
                    and operation["token_class"] == token_class
                ),
                None,
            )
            if operation is not None:
                stop = spend(1, "resolution")
                if stop:
                    return stop
                resolutions.append(
                    {
                        "event_id": use["event_id"],
                        "event_key": _event_key(use),
                        "role_kind": role,
                        "spelling": use["spelling"],
                        "surface": use["surface"],
                        "domain": "operation",
                        "target_decl_id": f"operation:{operation['ordinal']}",
                        "target_kind": "operation",
                    }
                )
                continue
        domain, allowed_kinds, failure_rule = _USE_ROWS[role]
        if role == "label":
            function_identity = _function_identity(_event_owner(use))
            label_candidates = sorted(
                (
                    binding
                    for binding in all_entries
                    if binding["domain"] == "label"
                    and binding["spelling"] == use["spelling"]
                    and _function_identity(binding["owner_path"]) == function_identity
                    and function_identity is not None
                ),
                key=lambda binding: binding["key"],
            )
            enclosing = [
                binding
                for binding in label_candidates
                if binding["loop_id"] in use["enclosing_loops"]
            ]
            if enclosing:
                if len(enclosing) != 1:
                    raise AssertionError("validated label topology has multiple enclosing targets")
                target = enclosing[0]
                stop = spend(1, "resolution")
                if stop:
                    return stop
                resolutions.append(
                    {
                        "event_id": use["event_id"],
                        "event_key": _event_key(use),
                        "role_kind": role,
                        "spelling": use["spelling"],
                        "surface": use["surface"],
                        "domain": domain,
                        "target_decl_id": target["decl_id"],
                        "target_kind": target["decl_kind"],
                    }
                )
                continue
            return publish_issue(
                {
                    "status": "source_issue",
                    "phase": "resolution",
                    "rule": "TYPE-6",
                    "reason": (
                        "non_enclosing_label" if label_candidates else "absent_binding"
                    ),
                    "event_id": use["event_id"],
                    "event_key": _event_key(use),
                    "spelling": use["spelling"],
                    "domain": domain,
                    "lookup_rank": 2 if label_candidates else 3,
                    "lexical_use_role": role,
                    "admissible_classes": ["label"],
                    "available_classes": [],
                    "invisible_origins": [],
                    "label_origins": [_origin(binding) for binding in label_candidates],
                    "conflicts": [],
                    "gram10": None,
                    "prior_origin": None,
                    "resources": counts,
                },
                use,
            )
        ancestors = _ancestors(use["scope"], scopes)
        target = None
        for scope_id in ancestors:
            candidates = [
                binding
                for binding in by_scope[scope_id]
                if binding["domain"] == domain
                and binding["spelling"] == use["spelling"]
                and binding["decl_kind"] in allowed_kinds
                and _owner_accessible(binding, use)
                and _visible(binding, use, ancestors, scopes)
            ]
            if candidates:
                target = candidates[0]
                break
        if target is None:
            domain_candidates = [
                binding
                for binding in all_entries
                if binding["domain"] == domain and binding["spelling"] == use["spelling"]
                and _owner_accessible(binding, use)
            ]
            visible_wrong_class = [
                binding
                for binding in domain_candidates
                if binding["decl_kind"] not in allowed_kinds
                and _visible(binding, use, ancestors, scopes)
            ]
            admissible = [
                binding
                for binding in all_entries
                if binding["domain"] == domain
                and binding["spelling"] == use["spelling"]
                and binding["decl_kind"] in allowed_kinds
                and _owner_accessible(binding, use)
            ]
            known_admissible = bool(admissible)
            invisible_origins = [
                _origin(binding)
                for binding in sorted(
                    admissible,
                    key=lambda binding: (
                        (-1,) if binding["builtin"] else binding["key"],
                        binding["decl_id"],
                    ),
                )
            ]
            available_class_set = {
                _binding_class(binding) for binding in visible_wrong_class
            }
            available_classes = [
                name for name in _PAYLOAD_CLASS_ORDER if name in available_class_set
            ]
            return publish_issue({
                "status": "source_issue",
                "phase": "resolution",
                "rule": failure_rule,
                "reason": "outside_visibility" if known_admissible else (
                    "inadmissible_declaration_class"
                    if visible_wrong_class
                    else "absent_binding"
                ),
                "event_id": use["event_id"],
                "event_key": _event_key(use),
                "spelling": use["spelling"],
                "domain": domain,
                "lookup_rank": 1 if known_admissible else 3,
                "lexical_use_role": role,
                "admissible_classes": _admissible_classes(domain, allowed_kinds),
                "available_classes": [] if known_admissible else available_classes,
                "invisible_origins": invisible_origins if known_admissible else [],
                "label_origins": [],
                "conflicts": [],
                "gram10": None,
                "prior_origin": None,
                "resources": counts,
            }, use)
        stop = spend(1, "resolution")
        if stop:
            return stop
        resolutions.append(
            {
                "event_id": use["event_id"],
                "event_key": _event_key(use),
                "role_kind": role,
                "spelling": use["spelling"],
                "surface": use["surface"],
                "domain": domain,
                "target_decl_id": target["decl_id"],
                "target_kind": target["decl_kind"],
            }
        )

    return {
        "status": "complete",
        "bindings": [
            {
                "decl_id": item["decl_id"],
                "decl_kind": item["decl_kind"],
                "spelling": item["spelling"],
                "domain": item["domain"],
                "builtin": item["builtin"],
            }
            for item in sorted(
                all_entries,
                key=lambda item: (
                    item["spelling"],
                    _DOMAIN_ORDER[item["domain"]],
                    item["decl_id"],
                ),
            )
        ],
        "resolutions": resolutions,
        "deferred": deferred_records,
        "resources": counts,
    }
