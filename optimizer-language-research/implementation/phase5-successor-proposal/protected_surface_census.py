#!/usr/bin/env python3
"""Reproduce the protected-surface census for the Phase-5 successor proposal.

This is proposal evidence, not language or compiler authority.  It reads the
exact guarded v0.9 inputs, rejects any identity or inventory drift, and emits a
deterministic report.  It never edits a protected input.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Sequence

from generate_candidate import (
    CandidateError,
    EXPECTED_CANDIDATE_BYTES,
    EXPECTED_CANDIDATE_SHA256,
    build_candidate,
)

from census_support import (
    CensusError,
    canonical_bytes,
    inventory_digest,
    load_manifest,
    read_regular,
    require_digest,
    sha256,
    strict_json,
    validate_case_inventory,
)
from source_surface_scan import (
    LOWER_NAME,
    declarations,
    find_collisions,
    generic_shadow_collisions,
    scan_tokens,
    table_only_bindings,
)


FORMAT = "whitefoot-phase5-successor-protected-surface-census-v1"
SPEC_REL = Path("spec/kernel-spec-v0.9.md")
PROPOSAL_REL = Path(
    "optimizer-language-research/implementation/phase5-successor-proposal/PROPOSAL.md"
)
CANDIDATE_REL = Path(
    "optimizer-language-research/implementation/phase5-successor-proposal/"
    "kernel-spec-v0.10-candidate.md"
)
SOURCE_INDEX_REL = Path("facets/v0.9/source.json")
GUARD_REL = Path("governance/guard-baseline.json")
MANIFEST_REL = Path("conformance/manifest.jsonl")
CONFORMANCE_REL = Path("conformance/cases")
CODEGEN_REL = Path("codegen-corpus")
REPORT_NAME = "protected-surface-census.json"

SPEC_SHA256 = "bdfb461d1901f610633c5cbcd2477d24df3c77ca90599b9580c8289e50b82b68"
PROPOSAL_SHA256 = "7fc48cc30f94d25be5be1106e3265d92c1b0cdf2bfea5a7a17759a12f3cf092d"
SOURCE_INDEX_SHA256 = "cc9aa86de0d59b9288d1f8fd7a6bde6f94fff26da139d73f91bcbcf71219d663"
GUARD_SHA256 = "bb7ce5ea5b3b2a169b259bcffc7add3234e89b50aa689d5f9df5a93a91325622"
MANIFEST_SHA256 = "0eff27bfb87ca14086f31f4b171d72c9eb1a49072aa4563a3f7c937d0b8bb90c"
CONFORMANCE_INVENTORY_SHA256 = (
    "d6fc88b4f65beb638cebb128a32f2834d1b12e0fcbb273960bbc0923ce753efb"
)
CODEGEN_INVENTORY_SHA256 = (
    "53f2d81b06a12df1198fd9d9354dfa2d0eea77ba03d763b63dead5fd4bf80095"
)

EXPECTED_MANIFEST_RECORDS = 307
EXPECTED_CASE_RECORDS = 292
EXPECTED_COVERAGE_RECORDS = 15
EXPECTED_PROTECTED_SOURCES = 293
EXPECTED_CODEGEN_SOURCES = 95
EXPECTED_REJECTIONS = 152
EXPECTED_FRONTEND_REJECTIONS = 21
EXPECTED_NOMINAL_FILES = 87
EXPECTED_CONTRACT_FILES = 9
EXPECTED_TYPE_GENERIC_FILES = 1

FRONTEND_ONLY_RULES = frozenset(
    {"FORM-1", "FORM-2", "FORM-3", "FORM-4", "FORM-5", "FORM-7", "GRAM-9"}
)

EXPECTED_FRONTEND_CASES = (
    "form1-neg-unknown-construct",
    "form2-neg-noncanonical-ws",
    "form3-neg-opname-bad-suffix",
    "form3-neg-typeid-fn-name",
    "form4-neg-comment",
    "form5-neg-missing-suffix",
    "form7-neg-out-of-range",
    "form7-neg-leading-zero",
    "gram9-neg-nested-call",
    "x-gram-nested-op-in-construct-field",
    "x-gram-nested-ucall-in-call-arg",
    "x-form-form2-tab-indent",
    "x-form-form3-enum-name-ident",
    "x-form-form4-block-comment",
    "x-form-form5-op-arg-missing-suffix",
    "x-form-form7-i32-max-plus-one",
    "form3-neg-requires-binding",
    "form3-neg-reserved-mode-field",
    "gram9-neg-constructor-in-call-argument",
    "gram9-neg-constructor-in-constructor-field",
    "form3-neg-region-param-missing-apostrophe",
)

EXPECTED_TABLE_ONLY_USE_CASES = (
    "const1-neg-noninteger",
    "const1-pos-array-size",
    "op3-neg-exact-dotted",
    "op4-trap-index-oob",
    "op8-neg-rotate-trap",
    "op8-pos-iand",
    "op9-pos-buffer-new",
    "own1-neg-bare-affine-call",
    "own1-neg-index-atom-after-move",
    "own1-neg-index-move-copy-offset",
    "own1-pos-explicit-affine-call",
    "own1-pos-match-projected-copy",
    "pending-op9-buffer-new",
    "type2-pos-buffer-tagonly",
    "type5-neg-index-offset-type",
    "type7-neg-index-reference-holder",
)

EXPECTED_TYPE6_CASES = (
    "type6-pos-distinct-names",
    "type6-neg-dup-variant",
    "type6-neg-shadow",
    "x-typ-match-foreign-variant",
    "x-typ-let-shadows-param",
    "x-enum-multiwidth-dispatch",
    "fn8-pos-requires-name-reuse",
    "type5-neg-match-non-enum",
)

EXPECTED_PRELUDE_SPELLING_CASES = (
    "eff2-neg-try-hidden-trap",
    "eff2-pos-try-declared-trap",
    "err3-neg-try-different-error-type",
    "err3-pos-try-propagation",
    "err4-pos-contract-trap",
    "err4-pos-recoverable-value",
    "op6-pos-cvt-checked",
    "x-arith-iadd-checked-overflow-err-arm-runs",
)

REFERENCE_METHODS = (
    "ProgramLayer.test_form3_every_op1_reserved_identifier_rejected",
    "ProgramLayer.test_form3_reservation_covers_every_binding_shape",
    "ProgramLayer.test_gram10_binder_not_fresh",
    "ProgramLayer.test_type5_context_free_option_constructor",
    "ProgramLayer.test_type5_context_free_result_constructor",
    "ProgramLayer.test_type6_duplicate_variant",
    "ProgramLayer.test_type6_type_namespace_rejects_user_and_prelude_collisions",
    "ProgramLayer.test_type6_unknown_constructor",
)

REFERENCE_RESERVATION_BINDING_SHAPES = (
    "named constant",
    "let binder",
    "try binder",
    "match binder",
    "struct field",
    "variant field",
    "parameter",
    "region parameter",
    "local region",
)

def _expect_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise CensusError(f"{label} drift: expected {expected!r}, got {actual!r}")


def require_scan_coverage(
    scanned: Sequence[str], expected: Sequence[str], label: str
) -> None:
    if list(scanned) != list(expected):
        raise CensusError(f"{label} scan coverage drift")


def validate_candidate_transition(
    specification: bytes, proposal: bytes, candidate: bytes
) -> None:
    require_digest(proposal, PROPOSAL_SHA256, PROPOSAL_REL.as_posix())
    require_digest(candidate, EXPECTED_CANDIDATE_SHA256, CANDIDATE_REL.as_posix())
    if len(candidate) != EXPECTED_CANDIDATE_BYTES:
        raise CensusError(
            f"candidate byte-length drift: expected {EXPECTED_CANDIDATE_BYTES}, "
            f"got {len(candidate)}"
        )
    try:
        generated, _ = build_candidate(specification, proposal)
    except CandidateError as error:
        raise CensusError(f"candidate transition is invalid: {error}") from error
    if generated != candidate:
        raise CensusError("checked-in candidate differs from the exact proposal transition")


def build_report(root: Path) -> dict[str, Any]:
    spec_raw = read_regular(root / SPEC_REL, SPEC_REL.as_posix())
    proposal_raw = read_regular(root / PROPOSAL_REL, PROPOSAL_REL.as_posix())
    candidate_raw = read_regular(root / CANDIDATE_REL, CANDIDATE_REL.as_posix())
    source_index_raw = read_regular(root / SOURCE_INDEX_REL, SOURCE_INDEX_REL.as_posix())
    guard_raw = read_regular(root / GUARD_REL, GUARD_REL.as_posix())
    manifest_raw = read_regular(root / MANIFEST_REL, MANIFEST_REL.as_posix())
    require_digest(spec_raw, SPEC_SHA256, SPEC_REL.as_posix())
    validate_candidate_transition(spec_raw, proposal_raw, candidate_raw)
    require_digest(source_index_raw, SOURCE_INDEX_SHA256, SOURCE_INDEX_REL.as_posix())
    require_digest(guard_raw, GUARD_SHA256, GUARD_REL.as_posix())
    require_digest(manifest_raw, MANIFEST_SHA256, MANIFEST_REL.as_posix())

    guard = strict_json(guard_raw, GUARD_REL.as_posix())
    source_index = strict_json(source_index_raw, SOURCE_INDEX_REL.as_posix())
    if not isinstance(guard, dict) or not isinstance(source_index, dict):
        raise CensusError("guard baseline and source index must be objects")
    if guard.get("kernel_specs", {}).get(SPEC_REL.as_posix()) != SPEC_SHA256:
        raise CensusError("guard baseline does not bind exact kernel specification v0.9")
    if source_index.get("specification", {}).get("sha256") != SPEC_SHA256:
        raise CensusError("source index does not bind exact kernel specification v0.9")

    case_paths, conformance_inventory = validate_case_inventory(
        root,
        CONFORMANCE_REL,
        guard,
        CONFORMANCE_INVENTORY_SHA256,
    )
    protected_manifest = guard.get("conformance")
    if not isinstance(protected_manifest, dict):
        raise CensusError("guard baseline conformance inventory is malformed")
    cases, annotations = load_manifest(
        root,
        CONFORMANCE_REL,
        manifest_raw,
        protected_manifest,
    )

    codegen_paths = sorted((root / CODEGEN_REL).rglob("*.wf"))
    codegen_inventory = inventory_digest(root, codegen_paths)
    if codegen_inventory != CODEGEN_INVENTORY_SHA256:
        raise CensusError(
            "codegen source inventory drift: "
            f"expected {CODEGEN_INVENTORY_SHA256}, got {codegen_inventory}"
        )

    _expect_equal(len(protected_manifest), EXPECTED_MANIFEST_RECORDS, "manifest record count")
    _expect_equal(len(cases), EXPECTED_CASE_RECORDS, "case record count")
    _expect_equal(len(annotations), EXPECTED_COVERAGE_RECORDS, "coverage record count")
    _expect_equal(len(case_paths), EXPECTED_PROTECTED_SOURCES, "protected source count")
    _expect_equal(len(codegen_paths), EXPECTED_CODEGEN_SOURCES, "codegen source count")

    operation_sets = source_index.get("operation_name_sets")
    if not isinstance(operation_sets, dict):
        raise CensusError("source index operation-name sets are missing")
    table_dotless = operation_sets.get("table_dotless_identifiers")
    listed_dotless = operation_sets.get("listed_dotless_identifiers")
    if not isinstance(table_dotless, list) or not isinstance(listed_dotless, list):
        raise CensusError("source index operation-name sets are malformed")
    if not all(isinstance(value, str) and LOWER_NAME.fullmatch(value) for value in table_dotless):
        raise CensusError("table dotless set contains a non-IDENT")
    if not all(isinstance(value, str) and LOWER_NAME.fullmatch(value) for value in listed_dotless):
        raise CensusError("listed dotless set contains a non-IDENT")
    table_only = tuple(sorted(set(table_dotless) - set(listed_dotless)))
    _expect_equal(len(table_dotless), 51, "table dotless count")
    _expect_equal(len(listed_dotless), 20, "listed dotless count")
    _expect_equal(len(table_only), 31, "table-only dotless count")
    _expect_equal(table_only, tuple(operation_sets.get("table_only_identifiers", ())), "table-only set")
    table_only_set = frozenset(table_only)

    prelude_start = spec_raw.rfind(b"\n[PRE-1]")
    if prelude_start >= 0:
        prelude_start += 1
    prelude_end = spec_raw.find(b"## 16.", prelude_start)
    if prelude_start < 0 or prelude_end < 0:
        raise CensusError("cannot isolate exact PRE-1 source")
    prelude_declarations, _ = declarations(
        scan_tokens(spec_raw[prelude_start:prelude_end], "PRE-1 source")
    )
    prelude_by_namespace = {
        namespace: sorted(
            {item.spelling for item in prelude_declarations if item.namespace == namespace}
        )
        for namespace in ("nominal", "constructor", "contract")
    }
    cross_namespace = sorted(
        set(prelude_by_namespace["nominal"])
        & set(prelude_by_namespace["constructor"])
    )
    _expect_equal(cross_namespace, ["NarrowError", "Overflow"], "PRE-1 cross-namespace equality")

    source_generics: dict[str, list[str]] = {}
    nominal_files: set[str] = set()
    contract_files: set[str] = set()
    generic_files: set[str] = set()
    source_collisions: list[dict[str, Any]] = []
    source_generic_collisions: list[dict[str, Any]] = []
    prelude_collisions: list[dict[str, Any]] = []
    table_only_uses: list[str] = []
    conformance_binding_hits: list[dict[str, Any]] = []
    prelude_spelling_cases: list[str] = []
    for path in case_paths:
        relative = path.relative_to(root).as_posix()
        case_id = path.stem
        raw = read_regular(path, relative)
        tokens = scan_tokens(raw, relative)
        items, generics = declarations(tokens)
        source_generics[relative] = [generic.spelling for generic in generics]
        if any(item.namespace == "nominal" for item in items):
            nominal_files.add(relative)
        if any(item.namespace == "contract" for item in items):
            contract_files.add(relative)
        if generics:
            generic_files.add(relative)
        source_collisions.extend(find_collisions(relative, items))
        source_generic_collisions.extend(
            generic_shadow_collisions(
                relative,
                items,
                generics,
                frozenset(prelude_by_namespace["nominal"]),
            )
        )
        for item in items:
            if item.spelling in prelude_by_namespace[item.namespace]:
                prelude_collisions.append(
                    {
                        "kind": item.kind,
                        "line": item.line,
                        "namespace": item.namespace,
                        "path": relative,
                        "spelling": item.spelling,
                    }
                )
        conformance_binding_hits.extend(
            table_only_bindings(relative, tokens, table_only_set)
        )
        if any(
            token.kind in {"word", "region"}
            and (token.text[1:] if token.kind == "region" else token.text) in table_only_set
            for token in tokens
        ):
            table_only_uses.append(case_id)
        text = raw.decode("utf-8")
        if re.search(r"\b(?:Overflow|NarrowError)\b", text):
            prelude_spelling_cases.append(case_id)

    _expect_equal(len(nominal_files), EXPECTED_NOMINAL_FILES, "nominal declaration file count")
    _expect_equal(len(contract_files), EXPECTED_CONTRACT_FILES, "contract declaration file count")
    _expect_equal(len(generic_files), EXPECTED_TYPE_GENERIC_FILES, "type generic file count")
    _expect_equal(sorted(table_only_uses), sorted(EXPECTED_TABLE_ONLY_USE_CASES), "table-only use cases")
    _expect_equal(sorted(prelude_spelling_cases), sorted(EXPECTED_PRELUDE_SPELLING_CASES), "prelude spelling cases")
    if prelude_collisions:
        raise CensusError(f"unexpected protected-source/prelude collision: {prelude_collisions}")
    expected_collision = [
        {
            "declarations": [
                {"kind": "enum-variant", "line": 2},
                {"kind": "enum-variant", "line": 6},
            ],
            "namespace": "constructor",
            "path": "conformance/cases/type6-neg-dup-variant.wf",
            "spelling": "Dup",
        }
    ]
    _expect_equal(source_collisions, expected_collision, "source namespace collisions")
    _expect_equal(source_generic_collisions, [], "source generic shadow collisions")

    codegen_binding_hits: list[dict[str, Any]] = []
    codegen_namespace_collisions: list[dict[str, Any]] = []
    codegen_prelude_collisions: list[dict[str, Any]] = []
    codegen_generic_collisions: list[dict[str, Any]] = []
    codegen_generics: dict[str, list[str]] = {}
    scanned_codegen_paths: list[str] = []
    for path in codegen_paths:
        relative = path.relative_to(root).as_posix()
        tokens = scan_tokens(read_regular(path, relative), relative)
        items, generics = declarations(tokens)
        if generics:
            codegen_generics[relative] = [generic.spelling for generic in generics]
        codegen_namespace_collisions.extend(find_collisions(relative, items))
        codegen_generic_collisions.extend(
            generic_shadow_collisions(
                relative,
                items,
                generics,
                frozenset(prelude_by_namespace["nominal"]),
            )
        )
        for item in items:
            if item.spelling in prelude_by_namespace[item.namespace]:
                codegen_prelude_collisions.append(
                    {
                        "kind": item.kind,
                        "line": item.line,
                        "namespace": item.namespace,
                        "path": relative,
                        "spelling": item.spelling,
                    }
                )
        codegen_binding_hits.extend(
            table_only_bindings(
                relative,
                tokens,
                table_only_set,
            )
        )
        scanned_codegen_paths.append(relative)
    expected_codegen_paths = [path.relative_to(root).as_posix() for path in codegen_paths]
    require_scan_coverage(scanned_codegen_paths, expected_codegen_paths, "codegen R-01/R-02")
    codegen_scan_transcript = "\n".join(scanned_codegen_paths).encode("utf-8")
    _expect_equal(codegen_namespace_collisions, [], "codegen namespace collisions")
    _expect_equal(codegen_prelude_collisions, [], "codegen/prelude collisions")
    _expect_equal(codegen_generic_collisions, [], "codegen generic shadow collisions")
    if conformance_binding_hits or codegen_binding_hits:
        raise CensusError(
            "table-only declaration binding found: "
            f"conformance={conformance_binding_hits}, codegen={codegen_binding_hits}"
        )

    rejects = [record for record in cases if record.get("expect", {}).get("kind") == "reject"]
    frontend_cases = [
        record["id"]
        for record in rejects
        if record.get("expect", {}).get("rule") in FRONTEND_ONLY_RULES
    ]
    _expect_equal(len(rejects), EXPECTED_REJECTIONS, "reject count")
    _expect_equal(frontend_cases, list(EXPECTED_FRONTEND_CASES), "frontend-only reject cases")
    type6_cases = [record["id"] for record in cases if "TYPE-6" in record.get("rules", [])]
    _expect_equal(type6_cases, list(EXPECTED_TYPE6_CASES), "TYPE-6 case set")

    oracles = guard.get("oracles")
    tests = guard.get("tests", {}).get("prototype/checker/test_checker.py")
    if not isinstance(oracles, dict) or not isinstance(tests, dict):
        raise CensusError("protected oracle or reference-test inventory is malformed")
    oracle_files: list[dict[str, Any]] = []
    for path, digests in sorted(oracles.items()):
        if not isinstance(path, str) or not isinstance(digests, list) or not all(
            isinstance(digest, str) for digest in digests
        ):
            raise CensusError("protected oracle inventory is malformed")
        oracle_files.append({"digests": digests, "path": path})
    oracle_digest_entries = sum(len(item["digests"]) for item in oracle_files)
    _expect_equal(oracle_digest_entries, 3, "protected oracle digest-entry count")

    reference_methods: list[dict[str, str]] = []
    for name in REFERENCE_METHODS:
        digest = tests.get(name)
        if not isinstance(digest, str):
            raise CensusError(f"protected reference method is absent: {name}")
        reference_methods.append({"qualified_name": name, "sha256": digest})

    generic_summary = [
        {"names": source_generics[path], "path": path} for path in sorted(generic_files)
    ]
    return {
        "conformance": {
            "case_records": len(cases),
            "coverage_records": len(annotations),
            "frontend_only_reject_case_ids": frontend_cases,
            "frontend_only_rejects": len(frontend_cases),
            "manifest_records": len(protected_manifest),
            "protected_source_files": len(case_paths),
            "rejects": len(rejects),
            "semantic_rejects_requiring_unchanged_replay": len(rejects) - len(frontend_cases),
        },
        "format": FORMAT,
        "inputs": {
            "candidate": {
                "bytes": EXPECTED_CANDIDATE_BYTES,
                "path": CANDIDATE_REL.as_posix(),
                "sha256": EXPECTED_CANDIDATE_SHA256,
            },
            "codegen_source_inventory": {
                "r01_r02_scanned_files": len(scanned_codegen_paths),
                "r01_r02_scan_path_sha256": sha256(codegen_scan_transcript),
                "sha256": codegen_inventory,
                "source_files": len(codegen_paths),
            },
            "conformance_source_inventory": {
                "sha256": conformance_inventory,
                "source_files": len(case_paths),
            },
            "guard_baseline": {"path": GUARD_REL.as_posix(), "sha256": GUARD_SHA256},
            "manifest": {"path": MANIFEST_REL.as_posix(), "sha256": MANIFEST_SHA256},
            "proposal": {
                "path": PROPOSAL_REL.as_posix(),
                "sha256": PROPOSAL_SHA256,
            },
            "source_index": {
                "path": SOURCE_INDEX_REL.as_posix(),
                "sha256": SOURCE_INDEX_SHA256,
            },
            "specification": {
                "path": SPEC_REL.as_posix(),
                "sha256": SPEC_SHA256,
                "version": "0.9",
            },
        },
        "protected_intersections": {
            "oracle_digest_entries": oracle_digest_entries,
            "oracle_disposition": "unchanged; no regeneration",
            "oracle_files": oracle_files,
            "reference_disposition": "existing protected bodies and expectations remain unchanged",
            "reference_methods": reference_methods,
        },
        "r01": {
            "contract_declaration_files": len(contract_files),
            "corrected_namespaces": {
                "constructor": "struct constructors, enum variants, and prelude constructors",
                "contract": "source contracts and built-in contracts",
                "nominal": "struct names, enum names, prelude nominal types, and lexical type parameters",
            },
            "direct_type6_case_ids": type6_cases,
            "generic_declarations": generic_summary,
            "generic_shadow_collisions": source_generic_collisions,
            "nominal_declaration_files": len(nominal_files),
            "prelude_by_namespace": prelude_by_namespace,
            "prelude_cross_namespace_equalities_required": cross_namespace,
            "protected_cases_mentioning_same_spelling_prelude_types": sorted(prelude_spelling_cases),
            "protected_source_prelude_collisions": prelude_collisions,
            "source_namespace_collisions": source_collisions,
            "type_generic_declaration_files": len(generic_files),
            "codegen_generic_declarations": [
                {"names": codegen_generics[path], "path": path}
                for path in sorted(codegen_generics)
            ],
            "codegen_generic_shadow_collisions": codegen_generic_collisions,
            "codegen_namespace_collisions": codegen_namespace_collisions,
            "codegen_prelude_collisions": codegen_prelude_collisions,
        },
        "r02": {
            "codegen_declaration_bindings": codegen_binding_hits,
            "conformance_declaration_bindings": conformance_binding_hits,
            "listed_dotless_count": len(listed_dotless),
            "table_dotless_count": len(table_dotless),
            "table_only_count": len(table_only),
            "table_only_identifiers": list(table_only),
            "table_only_use_case_ids": sorted(table_only_uses),
            "protected_reference_semantic_surface": {
                "ProgramLayer.test_form3_every_op1_reserved_identifier_rejected": {
                    "binding_shapes": ["function"],
                    "covered_dotless_identifiers": len(table_dotless),
                    "existing_expected_rule": "FORM-3",
                },
                "ProgramLayer.test_form3_reservation_covers_every_binding_shape": {
                    "binding_shapes": list(REFERENCE_RESERVATION_BINDING_SHAPES),
                    "representative_spelling": "trap",
                    "existing_expected_rule": "FORM-3",
                },
                "disposition": (
                    "semantic intersection recorded; existing protected bodies and "
                    "expectations remain unchanged"
                ),
            },
        },
        "r03": {
            "frontend_only_rule_ids": sorted(FRONTEND_ONLY_RULES),
            "protected_reject_expectations": len(rejects),
            "semantic_reject_expectations_requiring_unchanged_replay": (
                len(rejects) - len(frontend_cases)
            ),
        },
        "result": {
            "claim_scope": (
                "static R-01 namespace/generic and R-02 declaration-reservation "
                "intersections over the pinned conformance and codegen source inventories"
            ),
            "direct_protected_source_edits_for_scanned_intersections": 0,
            "not_proved": [
                "complete successor semantic replay of protected expectations",
                "zero expected-rule or diagnostic-location changes",
                "zero protected verdict changes",
            ],
            "proposal_constraint": "nominal, constructor, and contract TYPEID namespaces remain separate",
            "status": "reproduced",
        },
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="compare the checked-in report")
    mode.add_argument("--write", action="store_true", help="regenerate the report")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = Path(__file__).resolve().parents[3]
    report_path = Path(__file__).resolve().parent / REPORT_NAME
    try:
        encoded = canonical_bytes(build_report(root))
        if args.write:
            report_path.write_bytes(encoded)
            print(f"wrote {report_path.relative_to(root)} ({sha256(encoded)})")
            return 0
        existing = read_regular(report_path, report_path.relative_to(root).as_posix())
        if existing != encoded:
            raise CensusError(
                f"generated report drift: run {Path(__file__).name} --write and review the delta"
            )
        print(
            "phase5 successor protected-surface census: PASS "
            f"({sha256(encoded)})"
        )
        return 0
    except (CensusError, MemoryError, OSError) as error:
        print(f"phase5 successor protected-surface census: FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
