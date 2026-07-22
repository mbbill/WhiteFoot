"""Pairwise visibility-relation model for successor diagnostic evidence."""

from __future__ import annotations

from bisect import bisect_left
from typing import Any

from schema import validate_case


_LIMIT_SEQUENCE = (
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


def _position(record: dict[str, Any]) -> tuple[Any, ...]:
    value = record["key"]
    return (
        value["source"],
        value["start"],
        value["end"],
        tuple(value["path"]),
        value["role"],
        value["subtoken"],
    )


def _printed_position(record: dict[str, Any]) -> dict[str, Any]:
    value = record["key"]
    return {name: list(value[name]) if name == "path" else value[name] for name in (
        "source", "start", "end", "path", "role", "subtoken"
    )}


def _declaration_domains(kind: str) -> tuple[str, ...]:
    if kind == "struct":
        return ("nominal", "constructor")
    if kind in ("enum", "type_parameter"):
        return ("nominal",)
    if kind == "variant":
        return ("constructor",)
    if kind == "contract":
        return ("contract",)
    if kind in (
        "function",
        "const_parameter",
        "parameter",
        "local",
        "requires_local",
        "match_binder",
        "constant",
    ):
        return ("value",)
    if kind in ("region_parameter", "region"):
        return ("region",)
    if kind == "label":
        return ("label",)
    raise AssertionError(kind)


def _lookup_row(role: str) -> tuple[str, tuple[str, ...], str | None] | None:
    rows = {
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
    return rows.get(role)


def _deferred_rule(role: str) -> str | None:
    rows = {
        "match_field_name": "GRAM-10",
        "match_field_order": "GRAM-10",
        "match_variant_relation": "TYPE-6",
        "construct_field_name": "GRAM-8",
        "call_argument_name": "GRAM-11",
        "contract_member": "FN-3",
        "law_role": "FN-4",
    }
    return rows.get(role)


def _domain_rank(domain: str) -> int:
    return ("value", "nominal", "constructor", "contract", "region", "label").index(domain)


def _class_rank(kind: str) -> int:
    return (
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
    ).index(kind)


def _printed_class(binding: dict[str, Any]) -> str:
    if binding["decl_kind"] == "struct":
        return (
            "struct-constructor"
            if binding["domain"] == "constructor"
            else "nominal-type"
        )
    return {
        "function": "function",
        "constant": "named-const",
        "const_parameter": "const-generic",
        "parameter": "value",
        "local": "value",
        "requires_local": "value",
        "match_binder": "value",
        "type_parameter": "generic-type",
        "enum": "nominal-type",
        "variant": "enum-variant",
        "contract": "contract",
        "region_parameter": "region",
        "region": "region",
        "label": "label",
    }[binding["decl_kind"]]


def _closed_classes() -> tuple[str, ...]:
    return (
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


def _allowed_class_names(domain: str, kinds: tuple[str, ...]) -> list[str]:
    names = set()
    for kind in kinds:
        if kind == "struct":
            names.add("struct-constructor" if domain == "constructor" else "nominal-type")
        else:
            names.add(
                {
                    "function": "function",
                    "constant": "named-const",
                    "const_parameter": "const-generic",
                    "parameter": "value",
                    "local": "value",
                    "requires_local": "value",
                    "match_binder": "value",
                    "type_parameter": "generic-type",
                    "enum": "nominal-type",
                    "variant": "enum-variant",
                    "contract": "contract",
                    "region_parameter": "region",
                    "region": "region",
                    "label": "label",
                }[kind]
            )
    return [name for name in _closed_classes() if name in names]


def _owner(record: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(
        (component["kind"], component["id"])
        for component in record["owner_path"]
    )


def _global_class(kind: str) -> bool:
    return kind in (
        "struct",
        "enum",
        "variant",
        "contract",
        "function",
        "constant",
    )


def _owner_prefix(
    possible_prefix: tuple[tuple[str, str], ...],
    path: tuple[tuple[str, str], ...],
) -> bool:
    return len(possible_prefix) <= len(path) and all(
        possible_prefix[index] == path[index]
        for index in range(len(possible_prefix))
    )


def _candidate_belongs_to_use(
    binding: dict[str, Any], use: dict[str, Any]
) -> bool:
    return (
        binding["builtin"]
        or _global_class(binding["decl_kind"])
        or _owner_prefix(binding["owner_path"], _owner(use))
    )


def _prior_belongs_to_declaration(
    prior: dict[str, Any], candidate: dict[str, Any]
) -> bool:
    if prior["builtin"] or _global_class(prior["decl_kind"]):
        return True
    if _global_class(candidate["decl_kind"]):
        return False
    return _owner_prefix(prior["owner_path"], candidate["owner_path"])


def _function_from_owner(path: tuple[tuple[str, str], ...]) -> str | None:
    matches = [identity for kind, identity in path if kind == "function"]
    return matches[0] if matches else None


def _origin_segments(
    issue: dict[str, Any],
) -> tuple[tuple[str, tuple[dict[str, Any], ...]], ...]:
    """Describe fixed slots and bounded matched ranges in payload order."""

    segments: list[tuple[str, tuple[dict[str, Any], ...]]] = []
    conflicts = tuple(
        conflict["conflicting_origin"] for conflict in issue.get("conflicts", [])
    )
    if conflicts:
        segments.append(("range", conflicts))
    freshness = issue.get("gram10")
    if freshness:
        if freshness["earlier_binder_origin"] is not None:
            segments.append(("fixed", (freshness["earlier_binder_origin"],)))
        if freshness["arm_entry_live_origins"]:
            segments.append(("range", tuple(freshness["arm_entry_live_origins"])))
    if issue.get("prior_origin") is not None:
        segments.append(("fixed", (issue["prior_origin"],)))
    for field in ("invisible_origins", "label_origins"):
        if issue.get(field):
            segments.append(("range", tuple(issue[field])))
    return tuple(segments)


def _iterate_origins(
    issue: dict[str, Any],
    charge: Any,
    phase: str,
    *,
    emit_descriptors: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Independently execute one abstract origin iteration."""

    result: list[dict[str, Any]] = []
    for segment_kind, segment in _origin_segments(issue):
        if segment_kind == "fixed":
            for origin in segment:
                failure = charge(1, phase)
                if failure:
                    return [], failure
                if emit_descriptors:
                    failure = charge(1, phase)
                    if failure:
                        return [], failure
                result.append(origin)
            continue

        prelude = tuple(origin for origin in segment if origin["kind"] == "pre1")
        source = tuple(origin for origin in segment if origin["kind"] == "source")
        offsets = [0, 0]
        ranges = (prelude, source)
        while offsets[0] != len(prelude) or offsets[1] != len(source):
            ready = [index for index in range(2) if offsets[index] != len(ranges[index])]
            if len(ready) > 1:
                failure = charge(1, phase)
                if failure:
                    return [], failure
            chosen = ready[0]
            origin = ranges[chosen][offsets[chosen]]
            offsets[chosen] += 1
            failure = charge(3, phase)  # entry, self-exclusion, accepted origin
            if failure:
                return [], failure
            if emit_descriptors:
                failure = charge(1, phase)
                if failure:
                    return [], failure
            result.append(origin)
    return result, None


_LOOKUP_DOMAIN_ORDER = (
    "value",
    "nominal",
    "constructor",
    "contract",
    "region",
    "label",
    "operation",
)


def _lookup_domain_rank(domain: str) -> int:
    return _LOOKUP_DOMAIN_ORDER.index(domain)


def _compare_numeric(left: Any, right: Any, charge: Any, phase: str) -> tuple[int, dict[str, Any] | None]:
    failure = charge(1, phase)
    if failure:
        return 0, failure
    return (left > right) - (left < right), None


def _compare_spelling(left: str, right: str, charge: Any, phase: str) -> tuple[int, dict[str, Any] | None]:
    left_bytes = left.encode("utf-8")
    right_bytes = right.encode("utf-8")
    for left_byte, right_byte in zip(left_bytes, right_bytes):
        failure = charge(1, phase)
        if failure:
            return 0, failure
        if left_byte != right_byte:
            return (-1 if left_byte < right_byte else 1), None
    failure = charge(1, phase)
    if failure:
        return 0, failure
    return (len(left_bytes) > len(right_bytes)) - (len(left_bytes) < len(right_bytes)), None


def _compare_key(
    left: tuple[Any, ...],
    right: tuple[Any, ...],
    component_kinds: tuple[str, ...],
    charge: Any,
    phase: str,
) -> tuple[int, dict[str, Any] | None]:
    for left_value, right_value, kind in zip(left, right, component_kinds):
        if kind == "spelling":
            order, failure = _compare_spelling(
                left_value, right_value, charge, phase
            )
        else:
            order, failure = _compare_numeric(
                left_value, right_value, charge, phase
            )
        if failure or order:
            return order, failure
    return 0, None


def _stable_lookup_order(
    rows: list[dict[str, Any]],
    key_name: str,
    component_kinds: tuple[str, ...],
    prefix_length: int | None,
    charge: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    phase = f"{key_name}_comparison"
    failure = charge(len(rows), f"{key_name}_scratch_copy")
    if failure:
        return [], failure
    source = list(rows)
    width = 1
    passes = 0
    while width < len(source):
        destination: list[dict[str, Any]] = []
        for base in range(0, len(source), 2 * width):
            left = base
            middle = min(base + width, len(source))
            right = middle
            stop = min(base + 2 * width, len(source))
            while left < middle and right < stop:
                order, failure = _compare_key(
                    source[left][key_name],
                    source[right][key_name],
                    component_kinds,
                    charge,
                    phase,
                )
                if failure:
                    return [], failure
                take_left = order <= 0
                destination.append(source[left] if take_left else source[right])
                left += int(take_left)
                right += int(not take_left)
                failure = charge(1, f"{key_name}_write")
                if failure:
                    return [], failure
            while left < middle:
                destination.append(source[left])
                left += 1
                failure = charge(1, f"{key_name}_write")
                if failure:
                    return [], failure
            while right < stop:
                destination.append(source[right])
                right += 1
                failure = charge(1, f"{key_name}_write")
                if failure:
                    return [], failure
        source = destination
        width *= 2
        passes += 1
    if passes > 0 and passes % 2 == 0:
        failure = charge(len(source), f"{key_name}_final_copy")
        if failure:
            return [], failure

    if prefix_length is not None:
        prefix_kinds = component_kinds[:prefix_length]
        for prior, current in zip(source, source[1:]):
            order, failure = _compare_key(
                prior[key_name][:prefix_length],
                current[key_name][:prefix_length],
                prefix_kinds,
                charge,
                f"{key_name}_prefix",
            )
            if failure:
                return [], failure
            if order == 0 and current[key_name][0] == 0:
                failure = charge(1, f"{key_name}_predecessor_write")
                if failure:
                    return [], failure
    return source, None


def _storage_rank(storage: str) -> int:
    return (
        "declarations",
        "scopes",
        "declaration_events",
        "lexical_uses",
        "deferred_uses",
        "lookup_entries",
        "coverage_records",
        "ordering_scratch",
        "diagnostic_issue_data",
    ).index(storage)


def _scope_depth(scope_id: str, scopes: dict[str, dict[str, Any]]) -> int:
    count = 0
    cursor = scope_id
    while scopes[cursor]["parent"] is not None:
        count += 1
        cursor = scopes[cursor]["parent"]
    return count


def _lineage(scope_id: str, scopes: dict[str, dict[str, Any]]) -> tuple[str, ...]:
    chain = [scope_id]
    while scopes[chain[-1]]["parent"] is not None:
        chain.append(scopes[chain[-1]]["parent"])
    return tuple(chain)


def _binding(
    declaration: dict[str, Any],
    domain: str,
    builtin: bool,
) -> dict[str, Any]:
    return {
        "decl_id": declaration["decl_id"],
        "decl_kind": declaration["decl_kind"],
        "spelling": declaration["spelling"],
        "domain": domain,
        "scope": "unit" if builtin else declaration["visibility_scope"],
        "position": None if builtin else _position(declaration),
        "builtin": builtin,
        "whole_unit": builtin or declaration["decl_kind"] == "function",
        "event": None if builtin else declaration,
        "arm_id": None if builtin else declaration["arm_id"],
        "field_spelling": None if builtin else declaration["field_spelling"],
        "owner_path": () if builtin else _owner(declaration),
        "builtin_ordinal": declaration["declaration_ordinal"] if builtin else None,
        "visible_from": None if builtin or declaration["decl_kind"] == "function" else _position(
            {"key": declaration["visible_from"]}
        ),
        "loop_id": None if builtin else declaration["loop_id"],
    }


_SAME_SCOPE_KINDS = (
    "numeric", "numeric", "numeric", "numeric", "spelling", "numeric", "numeric"
)
_REGION_OWNER_KINDS = ("numeric", "numeric", "spelling", "numeric")
_ARM_BINDER_KINDS = ("numeric", "numeric", "spelling", "numeric")
_FINAL_LOOKUP_KINDS = (
    "numeric",
    "numeric",
    "numeric",
    "spelling",
    "numeric",
    "numeric",
    "numeric",
    "numeric",
)


def _dense_ids(values: list[Any]) -> dict[Any, int]:
    return {value: index + 1 for index, value in enumerate(sorted(set(values)))}


def _lookup_work_rows(
    case: dict[str, Any],
    builtin_bindings: list[dict[str, Any]],
    source_bindings: list[dict[str, Any]],
    event_ordinals: dict[str, int],
    event_positions: list[tuple[Any, ...]],
    charge: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    owner_ids = _dense_ids(
        [binding["owner_path"] for binding in source_bindings]
    )
    scope_ids = _dense_ids([binding["scope"] for binding in source_bindings])
    arm_ids = _dense_ids(
        [binding["arm_id"] for binding in source_bindings if binding["arm_id"]]
    )
    rows: list[dict[str, Any]] = []

    def append_binding(binding: dict[str, Any]) -> None:
        source = not binding["builtin"]
        owner_path = binding["owner_path"]
        function_id = _function_from_owner(owner_path)
        if binding["builtin"]:
            partition_kind, partition_id = 0, 0
            scope_id = owner_id = arm_id = 0
            event = binding["builtin_ordinal"]
        else:
            if binding["domain"] == "label":
                partition_kind = 2
                partition_id = owner_ids.get(
                    (("function", function_id),), 0
                )
            elif owner_path:
                partition_kind, partition_id = 1, owner_ids[owner_path]
            else:
                partition_kind, partition_id = 0, 0
            scope_id = scope_ids[binding["scope"]]
            owner_id = owner_ids[owner_path]
            arm_id = arm_ids.get(binding["arm_id"], 0)
            event = event_ordinals[binding["event"]["event_id"]]
        carried_ordinal = _declaration_domains(binding["decl_kind"]).index(
            binding["domain"]
        )
        rows.append(
            {
                "same_scope": (
                    0 if source else 1,
                    partition_id,
                    scope_id,
                    _lookup_domain_rank(binding["domain"]),
                    binding["spelling"],
                    event,
                    carried_ordinal,
                ),
                "region_owner": (
                    0 if source and binding["domain"] == "region" else 1,
                    owner_id,
                    binding["spelling"],
                    event,
                ),
                "arm_binder": (
                    0
                    if source and binding["decl_kind"] == "match_binder"
                    else 1,
                    arm_id,
                    binding["spelling"],
                    event,
                ),
                "lookup": (
                    partition_kind,
                    partition_id,
                    _lookup_domain_rank(binding["domain"]),
                    binding["spelling"],
                    2 if source else 0,
                    _closed_classes().index(_printed_class(binding)),
                    (
                        0
                        if binding["whole_unit"]
                        else bisect_left(event_positions, binding["visible_from"])
                    ),
                    event,
                ),
                "owner_path": owner_path,
                "function_id": function_id,
            }
        )

    for binding in builtin_bindings:
        append_binding(binding)
    for operation in case["operations"]:
        rows.append(
            {
                "same_scope": (
                    1, 0, 0, 6, operation["spelling"], operation["ordinal"], 0
                ),
                "region_owner": (1, 0, operation["spelling"], operation["ordinal"]),
                "arm_binder": (1, 0, operation["spelling"], operation["ordinal"]),
                "lookup": (
                    0,
                    0,
                    6,
                    operation["spelling"],
                    1,
                    _closed_classes().index("operation-family"),
                    0,
                    operation["ordinal"],
                ),
                "owner_path": (),
                "function_id": None,
            }
        )
    for binding in source_bindings:
        append_binding(binding)

    failure = charge(len(rows), "lookup_append")
    if failure:
        return [], failure
    for key_name, kinds, prefix_length in (
        ("same_scope", _SAME_SCOPE_KINDS, 5),
        ("region_owner", _REGION_OWNER_KINDS, 3),
        ("arm_binder", _ARM_BINDER_KINDS, 3),
        ("lookup", _FINAL_LOOKUP_KINDS, None),
    ):
        rows, failure = _stable_lookup_order(
            rows, key_name, kinds, prefix_length, charge
        )
        if failure:
            return [], failure
    return rows, None


def _query_domains(use: dict[str, Any]) -> tuple[str, ...]:
    if use["role_kind"] == "callee_ident":
        return ("operation", "value")
    if use["role_kind"] == "callee_opname":
        return ("operation",)
    row = _lookup_row(use["role_kind"])
    assert row is not None
    return (row[0],)


def _applicable_partitions(
    use: dict[str, Any], rows: list[dict[str, Any]]
) -> tuple[tuple[int, Any], ...]:
    if use["role_kind"] == "label":
        current_function = _function_from_owner(_owner(use))
        applicable = {
            (row["lookup"][0], row["lookup"][1])
            for row in rows
            if row["lookup"][0] == 2
            and row["function_id"] == current_function
        }
    else:
        applicable = {(0, 0)}
        use_owner = _owner(use)
        applicable.update(
            (row["lookup"][0], row["lookup"][1])
            for row in rows
            if row["lookup"][0] == 1
            and _owner_prefix(row["owner_path"], use_owner)
        )
    return tuple(sorted(applicable))


def _charge_lookup_query(
    use: dict[str, Any],
    rows: list[dict[str, Any]],
    use_ordinal: int,
    charge: Any,
) -> dict[str, Any] | None:
    partitions = _applicable_partitions(use, rows)
    for domain in _query_domains(use):
        for partition in partitions:
            partition_rows = [
                row
                for row in rows
                if (row["lookup"][0], row["lookup"][1]) == partition
            ]
            target = (_lookup_domain_rank(domain), use["spelling"])

            def compare(row: dict[str, Any]) -> tuple[int, dict[str, Any] | None]:
                failure = charge(1, "lookup_probe")
                if failure:
                    return 0, failure
                return _compare_key(
                    (row["lookup"][2], row["lookup"][3]),
                    target,
                    ("numeric", "spelling"),
                    charge,
                    "lookup_key_comparison",
                )

            lower_left = 0
            lower_right = len(partition_rows)
            while lower_left < lower_right:
                middle = lower_left + (lower_right - lower_left) // 2
                order, failure = compare(partition_rows[middle])
                if failure:
                    return failure
                if order < 0:
                    lower_left = middle + 1
                else:
                    lower_right = middle
            lower = lower_left

            upper_left = 0
            upper_right = len(partition_rows)
            while upper_left < upper_right:
                middle = upper_left + (upper_right - upper_left) // 2
                order, failure = compare(partition_rows[middle])
                if failure:
                    return failure
                if order <= 0:
                    upper_left = middle + 1
                else:
                    upper_right = middle
            upper = upper_left

            if lower < upper:
                left = lower
                right = upper
                while left < right:
                    middle = left + (right - left) // 2
                    failure = charge(1, "visibility_probe")
                    if failure:
                        return failure
                    order, failure = _compare_numeric(
                        partition_rows[middle]["lookup"][6],
                        use_ordinal,
                        charge,
                        "visibility_start_comparison",
                    )
                    if failure:
                        return failure
                    if order <= 0:
                        left = middle + 1
                    else:
                        right = middle
    return None


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
        "event_key": _printed_position(binding["event"]),
    }


def _limit_failure(counts: dict[str, int], name: str, maximum: int, phase: str) -> dict[str, Any]:
    return {
        "status": "resource_failure",
        "kind": "limit_exceeded",
        "limit": name,
        "maximum": maximum,
        "actual": counts[name],
        "phase": phase,
        "resources": counts,
    }


def run(raw_case: dict[str, Any]) -> dict[str, Any]:
    case = validate_case(raw_case)
    counts = {name: 0 for name in _LIMIT_SEQUENCE}

    def charge(amount: int, phase: str) -> dict[str, Any] | None:
        maximum = case["limits"]["work"]
        if counts["work"] + amount > maximum:
            counts["work"] = maximum + 1
            return _limit_failure(counts, "work", maximum, phase)
        counts["work"] += amount
        return None

    def publish_issue(issue: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        failure = charge(1, "diagnostic_count")
        if failure:
            return failure
        origins, failure = _iterate_origins(
            issue, charge, "diagnostic_count", emit_descriptors=False
        )
        if failure:
            return failure
        paths = [event["key"]["path"]] + [
            origin["event_key"]["path"]
            for origin in origins
            if origin["kind"] == "source"
        ]
        counts["node_path_depth"] = max(
            counts["node_path_depth"], max(map(len, paths), default=0)
        )
        counts["diagnostic_origins"] = len(origins)
        counts["diagnostic_paths"] = len(paths)
        counts["diagnostic_path_components"] = sum(map(len, paths))
        for name in (
            "node_path_depth",
            "diagnostic_origins",
            "diagnostic_paths",
            "diagnostic_path_components",
        ):
            if counts[name] > case["limits"][name]:
                return _limit_failure(
                    counts, name, case["limits"][name], "diagnostic_count"
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
        stream_elements = 0
        for addition, amount in enumerate(
            (
                1 + counts["diagnostic_origins"],
                counts["diagnostic_paths"],
                counts["diagnostic_path_components"],
            ),
            start=1,
        ):
            if derived_fault is not None and derived_fault["addition"] == addition:
                return {
                    "status": "resource_failure",
                    "kind": "count_unrepresentable",
                    "family": "diagnostic_issue_elements",
                    "resources": counts,
                }
            stream_elements += amount

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
            return {
                "status": "resource_failure",
                "kind": fault["kind"],
                "storage": "diagnostic_issue_data",
                "requested_elements": stream_elements,
                "resources": counts,
            }

        failure = charge(1, "diagnostic_materialization")
        if failure:
            return failure
        descriptors, failure = _iterate_origins(
            issue, charge, "diagnostic_materialization", emit_descriptors=True
        )
        if failure:
            return failure
        failure = charge(
            1 + len(event["key"]["path"]), "diagnostic_materialization"
        )
        if failure:
            return failure
        for descriptor in descriptors:
            failure = charge(1, "diagnostic_materialization")
            if failure:
                return failure
            if descriptor["kind"] == "source":
                failure = charge(
                    1 + len(descriptor["event_key"]["path"]),
                    "diagnostic_materialization",
                )
                if failure:
                    return failure
        return issue

    failure = charge(len(case["requires_blocks"]), "structural_admission")
    if failure:
        return failure
    admission_failures = [
        item for item in case["requires_blocks"] if item["issue_kind"] is not None
    ]
    if admission_failures:
        block = min(
            admission_failures,
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
                "event_key": _printed_position(event),
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
    scopes = {item["id"]: item for item in case["scopes"]}
    blocked_requires = {
        item["block_id"]
        for item in case["requires_blocks"]
        if item["issue_kind"] is not None
    }
    classified_events = [
        item
        for item in case["events"]
        if item["requires_block"] not in blocked_requires
    ]
    declarations = sorted(
        [item for item in classified_events if item["kind"] == "declare"], key=_position
    )
    use_events = sorted(
        [item for item in classified_events if item["kind"] == "use"], key=_position
    )
    lexical_events = [item for item in use_events if _lookup_row(item["role_kind"]) is not None]
    deferred_events = [item for item in use_events if _deferred_rule(item["role_kind"]) is not None]
    source_roles = declarations + use_events
    binding_count = sum(len(_declaration_domains(item["decl_kind"])) for item in case["builtins"] + declarations)
    depth_values = [_scope_depth(scope_id, scopes) for scope_id in scopes]
    counts = {
        "declarations": len(case["builtins"]) + len(declarations),
        "scopes": len(scopes),
        "scope_depth": max(depth_values),
        "declaration_events": len(declarations),
        "lexical_uses": len(lexical_events),
        "deferred_uses": len(deferred_events),
        "spelling_bytes": sum(len(item["spelling"].encode("utf-8")) for item in case["builtins"] + source_roles)
        + sum(len(operation["spelling"].encode("utf-8")) for operation in case["operations"])
        + sum(len(item["spelling"].encode("utf-8")) for item in case["reservations"]),
        "lookup_entries": binding_count + len(case["operations"]),
        "ancestry_steps": max(0, len(scopes) - 1),
        "node_path_depth": max(
            [len(item["key"]["path"]) for item in source_roles]
            + [
                len((block["issue_key"] or block["block_key"])["path"])
                for block in case["requires_blocks"]
            ]
            + [0]
        ),
        "diagnostic_origins": 0,
        "diagnostic_paths": 0,
        "diagnostic_path_components": 0,
        "coverage_records": len(source_roles),
        "work": admission_work,
    }
    required_preflight = (
        counts["work"]
        + counts["scopes"]
        + counts["declarations"]
        + len(source_roles)
        + counts["lookup_entries"]
    )
    count_faults = [
        fault
        for fault in case["faults"]
        if fault["kind"] == "count_unrepresentable"
        and fault["family"] != "diagnostic_issue_elements"
    ]
    count_faults.sort(
        key=lambda fault: (fault["detection_work"], _LIMIT_SEQUENCE.index(fault["family"]))
    )
    if count_faults and count_faults[0]["detection_work"] <= required_preflight:
        fault = count_faults[0]
        if case["limits"]["work"] < fault["detection_work"]:
            counts["work"] = case["limits"]["work"] + 1
            return _limit_failure(counts, "work", case["limits"]["work"], "preflight")
        counts["work"] = fault["detection_work"]
        return {
            "status": "resource_failure",
            "kind": "count_unrepresentable",
            "family": fault["family"],
            "resources": counts,
        }
    if required_preflight > case["limits"]["work"]:
        counts["work"] = case["limits"]["work"] + 1
        return _limit_failure(counts, "work", case["limits"]["work"], "preflight")
    counts["work"] = required_preflight
    for limit_name in _LIMIT_SEQUENCE:
        if limit_name not in (
            "diagnostic_origins",
            "diagnostic_paths",
            "diagnostic_path_components",
            "work",
        ) and counts[limit_name] > case["limits"][limit_name]:
            return _limit_failure(counts, limit_name, case["limits"][limit_name], "preflight")
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
    storage_faults = [
        fault
        for fault in case["faults"]
        if fault["kind"] != "count_unrepresentable"
        and fault["storage"] != "diagnostic_issue_data"
        and capacities[fault["storage"]] > 0
    ]
    if storage_faults:
        address_faults = [
            item for item in storage_faults
            if item["kind"] == "address_space_exceeded"
        ]
        fault = min(address_faults or storage_faults, key=lambda item: _storage_rank(item["storage"]))
        return {
            "status": "resource_failure",
            "kind": fault["kind"],
            "storage": fault["storage"],
            "requested_elements": capacities[fault["storage"]],
            "resources": counts,
        }

    ordered_events = sorted(classified_events, key=_position)
    declarations = [item for item in ordered_events if item["kind"] == "declare"]
    use_events = [item for item in ordered_events if item["kind"] == "use"]

    builtin_bindings = [
        _binding(declaration, domain, True)
        for declaration in case["builtins"]
        for domain in _declaration_domains(declaration["decl_kind"])
    ]
    source_bindings = [
        _binding(declaration, domain, False)
        for declaration in declarations
        for domain in _declaration_domains(declaration["decl_kind"])
    ]
    event_ordinals = {
        event["event_id"]: ordinal
        for ordinal, event in enumerate(ordered_events)
    }
    lookup_rows, failure = _lookup_work_rows(
        case,
        builtin_bindings,
        source_bindings,
        event_ordinals,
        [_position(event) for event in ordered_events],
        charge,
    )
    if failure:
        return failure

    failure = charge(len(case["operations"]) + len(case["reservations"]), "inventory")
    if failure:
        return failure
    for declaration in case["builtins"]:
        failure = charge(
            1 + len(_declaration_domains(declaration["decl_kind"])), "inventory"
        )
        if failure:
            return failure
    for declaration in declarations:
        failure = charge(
            1 + len(_declaration_domains(declaration["decl_kind"])), "inventory"
        )
        if failure:
            return failure

    conflicts: list[tuple[Any, ...]] = []
    for candidate in source_bindings:
        declaration = candidate["event"]
        normalized = (
            candidate["spelling"][1:]
            if candidate["decl_kind"] in ("region", "region_parameter")
            and candidate["spelling"].startswith("'")
            else candidate["spelling"]
        )
        reservation_applies = candidate["decl_kind"] in (
            "function",
            "parameter",
            "local",
            "requires_local",
            "match_binder",
            "constant",
            "region_parameter",
            "region",
        )
        for reservation in case["reservations"]:
            if reservation_applies and reservation["spelling"] == normalized:
                conflicts.append(
                    (
                        _position(declaration),
                        0,
                        _domain_rank(candidate["domain"]),
                        "reserved_name",
                        candidate,
                        reservation,
                    )
                )
        if (
            candidate["decl_kind"] == "match_binder"
            and candidate["spelling"] == candidate["field_spelling"]
        ):
            conflicts.append(
                (
                    _position(declaration),
                    2,
                    _domain_rank(candidate["domain"]),
                    "binder_equals_written_field",
                    candidate,
                    None,
                )
            )
        for builtin in builtin_bindings:
            if candidate["domain"] == builtin["domain"] and candidate["spelling"] == builtin["spelling"]:
                conflicts.append(
                    (
                        _position(declaration),
                        3,
                        _domain_rank(candidate["domain"]),
                        "reserved_collision",
                        candidate,
                        builtin,
                    )
                )
        for prior in source_bindings:
            if prior["position"] is None or prior["decl_id"] == candidate["decl_id"]:
                continue
            if prior["domain"] != candidate["domain"] or prior["spelling"] != candidate["spelling"]:
                continue
            if prior["position"] > candidate["position"]:
                if (
                    candidate["scope"] != "unit"
                    and candidate["decl_kind"] != "function"
                    and prior["decl_kind"] == "function"
                    and prior["whole_unit"]
                ):
                    violation = (
                        "binder_collides_arm_entry"
                        if candidate["decl_kind"] == "match_binder"
                        else "shadow_live_name"
                    )
                    conflicts.append(
                        (
                            _position(declaration),
                            2 if violation == "binder_collides_arm_entry" else 5,
                            _domain_rank(candidate["domain"]),
                            violation,
                            candidate,
                            prior,
                        )
                    )
                continue
            if candidate["domain"] == "region":
                if prior["owner_path"] == candidate["owner_path"]:
                    conflicts.append(
                        (
                            _position(declaration),
                            1,
                            _domain_rank(candidate["domain"]),
                            "repeated_region",
                            candidate,
                            prior,
                        )
                    )
                continue
            if not _prior_belongs_to_declaration(prior, candidate):
                continue
            lineage = _lineage(candidate["scope"], scopes)
            if (
                prior["decl_kind"] == "match_binder"
                and candidate["decl_kind"] == "match_binder"
                and prior["arm_id"] == candidate["arm_id"]
            ):
                violation = "duplicate_match_binder"
            elif candidate["decl_kind"] == "match_binder" and (
                prior["scope"] == candidate["scope"]
                or prior["whole_unit"]
                or prior["scope"] in lineage
            ):
                violation = "binder_collides_arm_entry"
            elif prior["scope"] == candidate["scope"]:
                violation = "duplicate_binding"
            elif prior["whole_unit"]:
                violation = "shadow_live_name"
            elif prior["scope"] in lineage:
                violation = "shadow_live_name"
            else:
                continue
            conflicts.append(
                (
                    _position(declaration),
                    (
                        2
                        if violation in ("duplicate_match_binder", "binder_collides_arm_entry")
                        else 4 if violation == "duplicate_binding" else 5
                    ),
                    _domain_rank(candidate["domain"]),
                    violation,
                    candidate,
                    prior,
                )
            )
    if conflicts:
        selected = min(conflicts, key=lambda item: item[:3])
        _, rank, _, reason, binding, prior = selected
        declaration = binding["event"]
        if reason == "reserved_name":
            rule = "FORM-3"
        elif reason == "repeated_region":
            rule = "OWN-3"
        elif declaration["decl_kind"] == "match_binder":
            rule = "GRAM-10"
        else:
            rule = "TYPE-6"
        collision_payload = []
        if rank in (3, 4, 5) and rule == "TYPE-6":
            matching = [
                item
                for item in conflicts
                if item[0] == selected[0] and item[1] == rank and item[5] is not None
            ]
            matching.sort(
                key=lambda item: (
                    item[2],
                    (0, item[5]["builtin_ordinal"])
                    if item[5]["builtin"]
                    else (1, item[5]["position"]),
                )
            )
            collision_payload = [
                {
                    "domain": item[4]["domain"],
                    "declaration_class": _printed_class(item[5]),
                    "conflicting_origin": _origin(item[5]),
                }
                for item in matching
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
            earlier = sorted(
                [
                    item
                    for item in source_bindings
                    if item["decl_kind"] == "match_binder"
                    and item["arm_id"] == declaration["arm_id"]
                    and item["spelling"] == declaration["spelling"]
                    and item["position"] < binding["position"]
                ],
                key=lambda item: item["position"],
            )
            lineage = _lineage(declaration["scope"], scopes)
            live = sorted(
                [
                    item
                    for item in source_bindings
                    if item["domain"] == "value"
                    and not (
                        item["decl_kind"] == "match_binder"
                        and item["arm_id"] == declaration["arm_id"]
                    )
                    and item["spelling"] == declaration["spelling"]
                    and item["scope"] in lineage
                    and (item["whole_unit"] or item["visible_from"] <= _position(declaration))
                ],
                key=lambda item: item["position"],
            )
            gram10_payload = {
                "binder_spelling": declaration["spelling"],
                "paired_field_spelling": declaration["field_spelling"],
                "earlier_binder_origin": _origin(earlier[0]) if earlier else None,
                "arm_entry_live_origins": [_origin(item) for item in live],
            }
        return publish_issue({
            "status": "source_issue",
            "phase": "inventory",
            "rule": rule,
            "reason": reason,
            "event_id": declaration["event_id"],
            "event_key": _printed_position(declaration),
            "spelling": declaration["spelling"],
            "domain": binding["domain"],
            "conflicts": collision_payload,
            "gram10": gram10_payload,
            "prior_origin": _origin(prior) if reason == "repeated_region" else None,
            "reservation": reservation_payload,
            "invisible_origins": [],
            "label_origins": [],
            "resources": counts,
        }, declaration)

    all_bindings = builtin_bindings + source_bindings
    resolutions: list[dict[str, Any]] = []
    deferred_records: list[dict[str, Any]] = []
    for use in use_events:
        failure = charge(1, "resolution")
        if failure:
            return failure
        deferred_rule = _deferred_rule(use["role_kind"])
        if deferred_rule is not None:
            failure = charge(1, "resolution")
            if failure:
                return failure
            deferred_records.append(
                {
                    "event_id": use["event_id"],
                    "event_key": _printed_position(use),
                    "role_kind": use["role_kind"],
                    "spelling": use["spelling"],
                    "surface": use["surface"],
                    "rule": deferred_rule,
                }
            )
            continue
        failure = _charge_lookup_query(
            use, lookup_rows, event_ordinals[use["event_id"]], charge
        )
        if failure:
            return failure
        row = _lookup_row(use["role_kind"])
        assert row is not None
        if use["role_kind"] in ("callee_ident", "callee_opname"):
            token_class = "ident" if use["role_kind"] == "callee_ident" else "opname"
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
                failure = charge(1, "resolution")
                if failure:
                    return failure
                resolutions.append(
                    {
                        "event_id": use["event_id"],
                        "event_key": _printed_position(use),
                        "role_kind": use["role_kind"],
                        "spelling": use["spelling"],
                        "surface": use["surface"],
                        "domain": "operation",
                        "target_decl_id": f"operation:{operation['ordinal']}",
                        "target_kind": "operation",
                    }
                )
                continue
        domain, allowed_kinds, attribution = row
        if use["role_kind"] == "label":
            current_function = _function_from_owner(_owner(use))
            same_function = sorted(
                [
                    binding
                    for binding in all_bindings
                    if binding["domain"] == "label"
                    and binding["spelling"] == use["spelling"]
                    and current_function is not None
                    and _function_from_owner(binding["owner_path"])
                    == current_function
                ],
                key=lambda binding: binding["position"],
            )
            enclosing = [
                binding
                for binding in same_function
                if binding["loop_id"] in use["enclosing_loops"]
            ]
            if enclosing:
                if len(enclosing) != 1:
                    raise AssertionError("validated label topology has multiple enclosing targets")
                target = enclosing[0]
                failure = charge(1, "resolution")
                if failure:
                    return failure
                resolutions.append(
                    {
                        "event_id": use["event_id"],
                        "event_key": _printed_position(use),
                        "role_kind": use["role_kind"],
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
                        "non_enclosing_label" if same_function else "absent_binding"
                    ),
                    "event_id": use["event_id"],
                    "event_key": _printed_position(use),
                    "spelling": use["spelling"],
                    "domain": domain,
                    "lookup_rank": 2 if same_function else 3,
                    "lexical_use_role": use["role_kind"],
                    "admissible_classes": ["label"],
                    "available_classes": [],
                    "invisible_origins": [],
                    "label_origins": [_origin(binding) for binding in same_function],
                    "conflicts": [],
                    "gram10": None,
                    "prior_origin": None,
                    "resources": counts,
                },
                use,
            )
        lineage = _lineage(use["scope"], scopes)
        eligible: list[tuple[int, dict[str, Any]]] = []
        for binding in all_bindings:
            if (
                binding["domain"] != domain
                or binding["spelling"] != use["spelling"]
                or binding["decl_kind"] not in allowed_kinds
                or not _candidate_belongs_to_use(binding, use)
            ):
                continue
            if binding["scope"] not in lineage:
                continue
            if not binding["whole_unit"] and binding["visible_from"] > _position(use):
                continue
            eligible.append((lineage.index(binding["scope"]), binding))
        if eligible:
            distance, target = min(eligible, key=lambda item: item[0])
        else:
            distance, target = len(lineage) - 1, None
        if target is None:
            same_domain = [
                binding
                for binding in all_bindings
                if binding["domain"] == domain and binding["spelling"] == use["spelling"]
                and _candidate_belongs_to_use(binding, use)
            ]
            visible_wrong_class = [
                binding
                for binding in same_domain
                if binding["decl_kind"] not in allowed_kinds
                and binding["scope"] in lineage
                and (binding["whole_unit"] or binding["visible_from"] <= _position(use))
            ]
            admissible = [
                binding
                for binding in all_bindings
                if binding["domain"] == domain
                and binding["spelling"] == use["spelling"]
                and binding["decl_kind"] in allowed_kinds
                and _candidate_belongs_to_use(binding, use)
            ]
            known_admissible = bool(admissible)
            invisible_origins = [
                _origin(binding)
                for binding in sorted(
                    admissible,
                    key=lambda binding: (
                        (-1,) if binding["builtin"] else binding["position"],
                        binding["decl_id"],
                    ),
                )
            ]
            available_names = {_printed_class(binding) for binding in visible_wrong_class}
            available_classes = [
                name for name in _closed_classes() if name in available_names
            ]
            return publish_issue({
                "status": "source_issue",
                "phase": "resolution",
                "rule": attribution,
                "reason": "outside_visibility" if known_admissible else (
                    "inadmissible_declaration_class"
                    if visible_wrong_class
                    else "absent_binding"
                ),
                "event_id": use["event_id"],
                "event_key": _printed_position(use),
                "spelling": use["spelling"],
                "domain": domain,
                "lookup_rank": 1 if known_admissible else 3,
                "lexical_use_role": use["role_kind"],
                "admissible_classes": _allowed_class_names(domain, allowed_kinds),
                "available_classes": [] if known_admissible else available_classes,
                "invisible_origins": invisible_origins if known_admissible else [],
                "label_origins": [],
                "conflicts": [],
                "gram10": None,
                "prior_origin": None,
                "resources": counts,
            }, use)
        failure = charge(1, "resolution")
        if failure:
            return failure
        resolutions.append(
            {
                "event_id": use["event_id"],
                "event_key": _printed_position(use),
                "role_kind": use["role_kind"],
                "spelling": use["spelling"],
                "surface": use["surface"],
                "domain": domain,
                "target_decl_id": target["decl_id"],
                "target_kind": target["decl_kind"],
            }
        )

    ordered_bindings = sorted(
        all_bindings,
        key=lambda item: (item["spelling"], _domain_rank(item["domain"]), item["decl_id"]),
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
            for item in ordered_bindings
        ],
        "resolutions": resolutions,
        "deferred": deferred_records,
        "resources": counts,
    }
