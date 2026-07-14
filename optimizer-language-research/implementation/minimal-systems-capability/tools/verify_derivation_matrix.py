#!/usr/bin/env python3
"""Verify exact coverage and semantic coherence in DERIVATION-MATRIX.tsv."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


EXPECTED_HEADER = [
    "contract_id",
    "capability_ids",
    "current_route",
    "status_code",
    "ordinary_library_derivation_sketch",
    "ownership_exit_drop_argument",
    "asymptotic_argument",
    "structural_costs_and_pathology",
    "fact_channels_and_invalidators",
    "negative_canaries",
    "family_lock_or_deferral",
    "evidence_refs",
]

VALID_STATUSES = {"E", "P", "U", "X", "FRAME", "DEFERRED", "BOUNDARY", "NG"}
FORBIDDEN_PLACEHOLDERS = {"todo", "tbd", "placeholder", "n/a", "unknown"}

STATUS_LEGEND = {
    "E": "established direct route covering the complete normalized contract",
    "P": "proved blessed pattern with correctness and performance evidence",
    "U": "unproved workaround or current subset lacking a complete proof or cost result",
    "X": "current semantic, soundness, asymptotic, or structural gap",
    "FRAME": "named trusted-boundary contract requiring a reviewed dossier; not authorization",
    "DEFERRED": "outside the current G0 domain; no G0 derivation is claimed",
    "BOUNDARY": "Rust boundary evidence whose unchecked or raw spelling is inadmissible while the underlying checked need remains routed",
    "NG": "owner-ratified writer-visible non-goal with any safe displacement tracked separately",
}

E_INCOMPATIBLE_REGISTRY_STATUSES = {
    "deferred_domain",
    "gap",
    "gap_or_scoped",
    "selected_unimplemented",
}

STATIC_ONLY_BEHAVIOR_CONTRACTS = {
    "ARR-VIEW-01",
    "VIEW-GET-01",
    "VIEW-GET-02",
    "OMAP-END-01",
    "OMAP-ITER-01",
    "BOX-DOWNCAST-01",
    "RC-DOWNCAST-01",
}

NON_ATOMIC_CONTRACTS = {"TRAIT-EXTEND-01", "TRAIT-COLLECT-01"}
INTERNAL_ONLY_DISJOINTNESS_CONTRACTS = {
    "ARR-VIEW-01",
    "VIEW-GET-01",
    "VIEW-GET-02",
    "VIEW-SORT-01",
    "VIEW-SORT-02",
    "VIEW-REORDER-01",
}

FACT_PHRASES = {
    "FT-STATE": "live/occupancy facts",
    "FT-REFINE": "refinement facts",
    "FT-IDENTITY": "identity facts",
    "FT-BORROW": "dynamic-borrow facts",
    "FT-SHARED": "shared-lifecycle facts",
}

CANARY_PHRASES = {
    "OW-DROP": "verify exact live-value drops",
    "BR-DISJOINT": "duplicate/overlapping mutable outputs",
    "FL-ALLOC": "inject allocation/capacity failure",
    "FL-CALLBACK": "trap/fail the invoked behavior",
    "FT-STATE": "recorded live-state invalidator",
    "FT-REFINE": "reject invalid refinement",
    "FT-BORROW": "borrow-count overflow",
    "FT-SHARED": "last-strong",
}

EFF4_CLAUSE = "Under xlang [EFF-4], an invoked-behavior trap aborts immediately"
EFF4_REFERENCE = "spec/kernel-spec-v0.6.md [EFF-4]"

COMPOSITION_FAMILIES = {
    "iteration_protocol",
    "iteration_producer",
    "iteration_adapter",
    "iteration_consumer",
    "range_iteration",
    "bulk_construction_protocol",
}

D10_PROTOCOL_CONTRACTS = {
    "TRAIT-INTOITER-01",
    "TRAIT-ITER-01",
    "TRAIT-DOUBLE-01",
    "TRAIT-EXACT-01",
    "TRAIT-EXTEND-01",
    "TRAIT-COLLECT-01",
    "TRAIT-FUSED-01",
}


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{path}: missing header")
        rows = list(reader)
        return reader.fieldnames, rows


def duplicate_values(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count != 1)


def census_implicates_allocation_failure(row: dict[str, str]) -> bool:
    text = row.get("failure_drop_abandonment", "").lower()
    terms = ("allocation", "allocator", "oom", "capacity", "growth", "reallocate")
    return row.get("contract_id", "").startswith("ALLOC-") or any(
        term in text for term in terms
    ) or "reserve" in row.get("rust_surfaces", "").lower()


def census_implicates_disjointness(row: dict[str, str]) -> bool:
    text = " ".join(
        row.get(field, "")
        for field in (
            "post_state_result",
            "invalidation",
            "required_obligations",
            "implementation_privilege_evidence",
        )
    ).lower()
    contract_id = row.get("contract_id", "")
    return (
        "disjoint" in text
        or "partition" in text
        or "SWAP" in contract_id
        or contract_id == "RAW-UNSAFE-ACCESS-01"
    )


def verify(root: Path) -> list[str]:
    errors: list[str] = []
    census_path = root / "RUST-DATA-CONTRACT-CENSUS.tsv"
    registry_path = root / "CAPABILITY-OBLIGATION-REGISTRY.tsv"
    matrix_path = root / "DERIVATION-MATRIX.tsv"

    census_header, census_rows = read_tsv(census_path)
    registry_header, registry_rows = read_tsv(registry_path)
    matrix_header, matrix_rows = read_tsv(matrix_path)

    if "contract_id" not in census_header:
        errors.append(f"{census_path}: missing contract_id column")
    if "capability_id" not in registry_header:
        errors.append(f"{registry_path}: missing capability_id column")
    if matrix_header != EXPECTED_HEADER:
        errors.append(
            f"{matrix_path}: header mismatch: expected {EXPECTED_HEADER!r}, "
            f"found {matrix_header!r}"
        )

    census_ids = [row.get("contract_id", "").strip() for row in census_rows]
    registry_ids = [row.get("capability_id", "").strip() for row in registry_rows]
    matrix_ids = [row.get("contract_id", "").strip() for row in matrix_rows]

    for label, values in (
        ("census contract", census_ids),
        ("registry capability", registry_ids),
        ("matrix contract", matrix_ids),
    ):
        duplicates = duplicate_values(values)
        if duplicates:
            errors.append(f"duplicate or empty {label} IDs: {duplicates}")

    census_set = set(census_ids)
    matrix_set = set(matrix_ids)
    if census_set != matrix_set:
        missing = sorted(census_set - matrix_set)
        extra = sorted(matrix_set - census_set)
        if missing:
            errors.append(f"matrix is missing contracts: {missing}")
        if extra:
            errors.append(f"matrix has unknown contracts: {extra}")

    if matrix_ids != census_ids:
        errors.append("matrix contract order differs from the canonical census order")

    registry_set = set(registry_ids)
    registry_rank = {capability_id: index for index, capability_id in enumerate(registry_ids)}
    registry_status = {
        row.get("capability_id", "").strip(): row.get("current_xlang_status", "").strip()
        for row in registry_rows
    }
    census_by_id = {
        row.get("contract_id", "").strip(): row for row in census_rows
    }
    for line_number, row in enumerate(matrix_rows, start=2):
        contract_id = row.get("contract_id", "").strip() or f"line {line_number}"

        for field in EXPECTED_HEADER:
            value = row.get(field)
            if value is None or not value.strip():
                errors.append(f"{contract_id}: empty field {field}")
                continue
            if "\n" in value or "\r" in value:
                errors.append(f"{contract_id}: embedded newline in {field}")
            if value.strip().lower() in FORBIDDEN_PLACEHOLDERS:
                errors.append(f"{contract_id}: placeholder value in {field}: {value!r}")

        status = row.get("status_code", "").strip()
        if status not in VALID_STATUSES:
            errors.append(f"{contract_id}: invalid status_code {status!r}")

        raw_capabilities = row.get("capability_ids", "")
        capability_ids = [part.strip() for part in raw_capabilities.split(",")]
        if any(not capability_id for capability_id in capability_ids):
            errors.append(f"{contract_id}: malformed comma-separated capability_ids")
        if any("*" in capability_id for capability_id in capability_ids):
            errors.append(f"{contract_id}: capability wildcard was not expanded")
        capability_duplicates = duplicate_values(capability_ids)
        if capability_duplicates:
            errors.append(
                f"{contract_id}: duplicate capability IDs: {capability_duplicates}"
            )
        unknown_capabilities = sorted(set(capability_ids) - registry_set)
        if unknown_capabilities:
            errors.append(
                f"{contract_id}: unknown capability IDs: {unknown_capabilities}"
            )

        known_capabilities = [
            capability_id
            for capability_id in capability_ids
            if capability_id in registry_rank
        ]
        if known_capabilities != sorted(known_capabilities, key=registry_rank.get):
            errors.append(f"{contract_id}: capability IDs are not in registry order")

        capabilities = set(capability_ids)
        census_row = census_by_id.get(contract_id, {})
        canaries = row.get("negative_canaries", "")
        facts = row.get("fact_channels_and_invalidators", "")
        ownership = row.get("ownership_exit_drop_argument", "")
        evidence = row.get("evidence_refs", "")
        sketch = row.get("ordinary_library_derivation_sketch", "")
        structural = row.get("structural_costs_and_pathology", "")

        if census_row.get("family", "") in COMPOSITION_FAMILIES:
            if "IT-COMPOSE" not in capabilities:
                errors.append(f"{contract_id}: composable iterator contract lacks IT-COMPOSE")
            if "without intermediate materialization" not in f"{sketch} {structural}":
                errors.append(
                    f"{contract_id}: composition route does not forbid intermediate materialization"
                )

        is_d10_contract = (
            contract_id.startswith(("ITER-", "RANGE-"))
            or contract_id in D10_PROTOCOL_CONTRACTS
        )
        if is_d10_contract and "BR-STORED" in capabilities:
            errors.append(
                f"{contract_id}: D10 contract stores no borrow that survives its owner boundary"
            )
        if contract_id.startswith("RANGE-ITER-"):
            if not {"OW-CLONE", "IT-OWN", "IT-COMPOSE"} <= capabilities:
                errors.append(
                    f"{contract_id}: independent owning range cursor lacks clone/own/compose obligations"
                )
        if contract_id in {"TRAIT-EXACT-01", "TRAIT-FUSED-01"}:
            if "FT-STATE" in capabilities:
                errors.append(
                    f"{contract_id}: stable metadata/marker contract is not a live-state fact channel"
                )

        if status == "E":
            incompatible = sorted(
                capability_id
                for capability_id in capabilities
                if registry_status.get(capability_id)
                in E_INCOMPATIBLE_REGISTRY_STATUSES
            )
            if incompatible:
                errors.append(
                    f"{contract_id}: E route depends on non-established capabilities: "
                    f"{incompatible}"
                )
            if not row.get("current_route", "").startswith(
                ("Direct current route:", "Derived current route:")
            ):
                errors.append(
                    f"{contract_id}: E current_route must identify a direct or derived route"
                )
        if status == "P" and "proved" not in row.get("current_route", "").lower():
            errors.append(f"{contract_id}: P current_route must identify the proved pattern")
        if status == "U" and "unproved" not in row.get("current_route", "").lower():
            errors.append(f"{contract_id}: U current_route must identify what is unproved")
        if status == "FRAME" and "boundary" not in row.get("current_route", "").lower():
            errors.append(f"{contract_id}: FRAME current_route must name a boundary")
        if status == "DEFERRED" and "later-domain" not in row.get("current_route", ""):
            errors.append(f"{contract_id}: DEFERRED current_route must identify a later-domain route")
        if status == "BOUNDARY":
            if "Boundary evidence" not in row.get("current_route", ""):
                errors.append(
                    f"{contract_id}: BOUNDARY current_route must identify boundary evidence"
                )
            if "boundary evidence" not in row.get("family_lock_or_deferral", ""):
                errors.append(
                    f"{contract_id}: BOUNDARY row must preserve the underlying checked need"
                )
        if status == "NG" and "non-goal" not in row.get("current_route", ""):
            errors.append(f"{contract_id}: NG current_route must identify the non-goal")

        behavior = census_row.get("behavior_parameter", "").lower()
        if "FL-CALLBACK" in capabilities:
            if (
                not behavior
                or behavior == "none"
                or "statically selected" in behavior
                or contract_id in STATIC_ONLY_BEHAVIOR_CONTRACTS
            ):
                errors.append(
                    f"{contract_id}: FL-CALLBACK has no runtime-invoked behavior"
                )
            if EFF4_CLAUSE not in ownership:
                errors.append(f"{contract_id}: callback route omits the EFF-4 trap translation")
            if EFF4_REFERENCE not in evidence:
                errors.append(f"{contract_id}: callback route omits the EFF-4 evidence reference")
            if "Rust failure evidence:" not in ownership:
                errors.append(
                    f"{contract_id}: callback route does not separate Rust failure evidence"
                )
        elif CANARY_PHRASES["FL-CALLBACK"] in canaries or "invoked-behavior containment" in sketch:
            errors.append(f"{contract_id}: callback prose appears without FL-CALLBACK")

        if (
            "AB-BEHAVIOR" in capabilities
            and contract_id in STATIC_ONLY_BEHAVIOR_CONTRACTS
        ):
            errors.append(
                f"{contract_id}: static/type-only context is misclassified as callable behavior"
            )

        if "FL-ALLOC" in capabilities and not census_implicates_allocation_failure(census_row):
            errors.append(
                f"{contract_id}: FL-ALLOC is present without a census allocation-failure edge"
            )
        if "FL-ALLOC" not in capabilities and (
            CANARY_PHRASES["FL-ALLOC"] in canaries
            or "explicit allocation-failure policy" in sketch
        ):
            errors.append(f"{contract_id}: allocation-failure prose appears without FL-ALLOC")

        if "FL-ATOMIC" in capabilities and contract_id in NON_ATOMIC_CONTRACTS:
            errors.append(
                f"{contract_id}: FL-ATOMIC contradicts the census partial-progress contract"
            )
        if "FL-ATOMIC" not in capabilities and "recoverable failure atomicity" in sketch:
            errors.append(f"{contract_id}: atomicity prose appears without FL-ATOMIC")

        if "BR-DISJOINT" in capabilities:
            if contract_id in INTERNAL_ONLY_DISJOINTNESS_CONTRACTS:
                errors.append(
                    f"{contract_id}: BR-DISJOINT is not an exposed/runtime contract"
                )
            if not census_implicates_disjointness(census_row):
                errors.append(
                    f"{contract_id}: BR-DISJOINT lacks a census disjointness obligation"
                )
        elif (
            CANARY_PHRASES["BR-DISJOINT"] in canaries
            or "disjointness facts" in facts
            or "checked multi-place disjointness" in sketch
        ):
            errors.append(f"{contract_id}: disjointness prose appears without BR-DISJOINT")

        if "FT-STATE" in capabilities and not (
            capabilities & {"ST-DENSE", "ST-RING", "ST-SPARSE", "ST-DEPENDENT", "ST-HOLE"}
            or contract_id == "TRAIT-DROP-01"
        ):
            errors.append(f"{contract_id}: FT-STATE has no partial/live-set topology")
        if "FT-REFINE" in capabilities and "ST-REFINE" not in capabilities:
            errors.append(f"{contract_id}: FT-REFINE has no refinement-sealed source")
        if "FT-IDENTITY" in capabilities and not (
            capabilities & {"ID-LOGICAL", "ID-POOL"}
        ):
            errors.append(f"{contract_id}: FT-IDENTITY has no pool/logical identity")
        if "FT-BORROW" in capabilities and not (
            "borrow" in census_row.get("family", "")
            or contract_id in {"TRAIT-DROP-01", "RAW-UNSAFE-BORROW-01"}
        ):
            errors.append(f"{contract_id}: FT-BORROW has no dynamic-borrow contract")
        if "FT-SHARED" in capabilities and not (
            "ID-SHARED" in capabilities or contract_id == "TRAIT-DROP-01"
        ):
            errors.append(f"{contract_id}: FT-SHARED has no shared-lifecycle contract")

        for capability_id, fact_phrase in FACT_PHRASES.items():
            if (capability_id in capabilities) != (fact_phrase in facts):
                errors.append(
                    f"{contract_id}: {capability_id} and its fact-channel prose disagree"
                )
        for capability_id, canary_phrase in CANARY_PHRASES.items():
            if capability_id in capabilities and canary_phrase not in canaries:
                errors.append(
                    f"{contract_id}: {capability_id} lacks its negative canary"
                )
            if (
                capability_id not in capabilities
                and canary_phrase in canaries
                and capability_id != "FT-SHARED"
            ):
                errors.append(
                    f"{contract_id}: {canary_phrase!r} canary lacks {capability_id}"
                )

        registry_marker = "; CAPABILITY-OBLIGATION-REGISTRY.tsv:"
        if evidence.count(registry_marker) != 1:
            errors.append(f"{contract_id}: evidence must contain one registry capability list")
        else:
            evidence_capabilities = evidence.split(registry_marker, 1)[1].split(",")
            if evidence_capabilities != capability_ids:
                errors.append(
                    f"{contract_id}: evidence capability list differs from capability_ids"
                )
        census_reference = f"RUST-DATA-CONTRACT-CENSUS.tsv:{contract_id}"
        if census_reference not in evidence:
            errors.append(f"{contract_id}: missing exact census evidence reference")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="minimal-systems-capability artifact directory",
    )
    args = parser.parse_args()

    errors = verify(args.root.resolve())
    if errors:
        for error in errors:
            print(f"derivation matrix: FAIL: {error}")
        return 1

    _, census_rows = read_tsv(args.root / "RUST-DATA-CONTRACT-CENSUS.tsv")
    _, registry_rows = read_tsv(args.root / "CAPABILITY-OBLIGATION-REGISTRY.tsv")
    print(
        "derivation matrix: PASS — "
        f"{len(census_rows)} contracts mapped exactly once against "
        f"{len(registry_rows)} registered capabilities"
    )
    print(
        "status legend: "
        + "; ".join(f"{code}={meaning}" for code, meaning in STATUS_LEGEND.items())
    )
    print(
        "status note: E is direct; P is an evidence-backed derived pattern; "
        "current_route records the exact route. Redundant Rust aliases were removed "
        "during contract clustering and therefore have no matrix status row."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
