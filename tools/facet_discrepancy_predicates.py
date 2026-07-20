#!/usr/bin/env python3
"""Recompute the closed exact-v0.8 discrepancy predicate registry."""

from __future__ import annotations

import json
import re
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

try:
    import facet_discrepancy_inputs as inputs
except ModuleNotFoundError:  # Support import as ``tools.*``.
    from tools import facet_discrepancy_inputs as inputs  # type: ignore


DiscrepancyError = inputs.DiscrepancyError

MAX_MANIFEST_ENTRIES = 20_000
MAX_DECLARATIONS_PER_CASE = 4_096
MAX_DECLARATIONS_TOTAL = 100_000

IDENT = re.compile(rb"[a-z][a-z0-9_]*")
OP_NAME = re.compile(rb"`([a-z_]+(?:\.[a-z]+)?)`")
DOTLESS_LIST = re.compile(rb"or a dotless IDENT \(`([^`\r\n]+)`\); both")


@dataclass(frozen=True)
class ExactSource:
    """Exact bytes plus byte-to-line coordinates for evidence anchors."""

    path: str
    raw: bytes
    line_offsets: tuple[int, ...]

    @classmethod
    def from_bytes(cls, path: str, raw: bytes) -> "ExactSource":
        offsets = [0]
        for line in raw.splitlines(keepends=True):
            offsets.append(offsets[-1] + len(line))
        return cls(path, raw, tuple(offsets))

    def evidence(self, byte_start: int, byte_end: int) -> dict[str, Any]:
        if not 0 <= byte_start < byte_end <= len(self.raw):
            raise DiscrepancyError(
                f"invalid evidence span {self.path}:{byte_start}-{byte_end}"
            )
        return {
            "byte_end": byte_end,
            "byte_start": byte_start,
            "line_end": bisect_right(self.line_offsets, byte_end - 1),
            "line_start": bisect_right(self.line_offsets, byte_start),
            "path": self.path,
            "sha256": inputs.sha256(self.raw[byte_start:byte_end]),
        }

    def unique(self, fragment: bytes) -> tuple[int, int]:
        count = self.raw.count(fragment)
        if count != 1:
            raise DiscrepancyError(
                f"expected one exact fragment in {self.path}, found {count}: "
                f"{fragment!r}"
            )
        start = self.raw.index(fragment)
        return start, start + len(fragment)


@dataclass(frozen=True)
class Observation:
    """The recomputed truth value and exact evidence of one predicate."""

    is_open: bool
    evidence: dict[str, Any]


@dataclass(frozen=True)
class Registration:
    identifier: str
    discrepancy_class: str
    predicate_identifier: str
    affected_facet_ids: tuple[str, ...]
    resolution_authorities: tuple[str, ...]


REGISTRATIONS = (
    Registration(
        "discrepancy:v0.8/op1-dotless-reservation",
        "internal-specification-ambiguity",
        "predicate:op1-dotless-reservation-set-equality",
        ("facet:OP-1/dotless-operation-reservation",),
        ("successor-numbered-specification",),
    ),
    Registration(
        "discrepancy:v0.8/form2-protected-conformance-spacing",
        "specification-protected-surface-conflict",
        "predicate:form2-conformance-function-spacing",
        ("facet:FORM-2/no-space-before-open-paren",),
        (
            "owner-approved-protected-surface-change",
            "successor-numbered-specification",
        ),
    ),
    Registration(
        "discrepancy:v0.8/form4-doc-cross-reference",
        "internal-specification-inconsistency",
        "predicate:form4-doc-production-owner-consistency",
        ("facet:FORM-4/documentation-field-only",),
        ("successor-numbered-specification",),
    ),
    Registration(
        "discrepancy:v0.8/form5-form7-float-canonical-spelling",
        "internal-specification-inconsistency",
        "predicate:form5-form7-float-canonical-spelling-consistency",
        (
            "facet:FORM-1/noncanonical-input-rejected",
            "facet:FORM-1/one-byte-format",
            "facet:FORM-1/one-spelling-per-construct",
            "facet:FORM-1/toolchain-does-not-autoformat",
            "facet:FORM-5/float-lowercase-exponent",
            "facet:FORM-5/float-no-leading-zeros",
            "facet:FORM-5/float-required-integer-and-fraction-digits",
            "facet:FORM-5/float-shortest-rne-roundtrip",
            "facet:META-1/one-spelling-enforcement",
        ),
        ("successor-numbered-specification",),
    ),
    Registration(
        "discrepancy:v0.8/gram1-gram7-match-node-bijection",
        "internal-specification-inconsistency",
        "predicate:gram1-gram7-match-node-bijection-consistency",
        (
            "facet:GRAM-1/production-node-bijection",
            "facet:GRAM-7/shared-match-node-kind",
            "facet:META-1/production-node-bijection-enforcement",
        ),
        ("successor-numbered-specification",),
    ),
    Registration(
        "discrepancy:v0.8/fn7-main-return-spelling",
        "internal-specification-inconsistency",
        "predicate:fn7-main-return-spelling-consistency",
        ("facet:FN-7/main-return-spelling",),
        ("successor-numbered-specification",),
    ),
)


def _pin(actual: Any, expected: Any, label: str) -> None:
    if inputs.canonical_bytes(actual) != inputs.canonical_bytes(expected):
        raise DiscrepancyError(f"{label} no longer matches the pinned audit")


def observe_op1(specification: bytes, *, enforce_pins: bool = True) -> Observation:
    """Compare OP-1 table dotless names with its explicit listed set."""
    source = ExactSource.from_bytes("spec/kernel-spec-v0.8.md", specification)
    header = b"| op | domain | signature | effects |\n"
    table_start, _ = source.unique(header)
    table_end = specification.find(b"\n\n", table_start)
    if table_end < 0:
        raise DiscrepancyError("OP-1 table has no terminating blank line")
    table_end += 1
    lines = specification[table_start:table_end].splitlines(keepends=True)
    if len(lines) < 3 or lines[:2] != [
        header,
        b"|---|---|---|---|\n",
    ]:
        raise DiscrepancyError("OP-1 table header is not the audited shape")

    occurrences: list[str] = []
    for line in lines[2:]:
        cells = line.split(b"|")
        if len(cells) != 6 or cells[0] or cells[-1] != b"\n":
            raise DiscrepancyError("OP-1 table row is malformed")
        names = [match.decode("ascii") for match in OP_NAME.findall(cells[1])]
        if not names:
            raise DiscrepancyError("OP-1 table row has no operation name")
        occurrences.extend(names)

    table_dotless = list(dict.fromkeys(name for name in occurrences if "." not in name))
    listed_match = DOTLESS_LIST.search(specification, table_end)
    if listed_match is None:
        raise DiscrepancyError("OP-1 explicit dotless identifier list is missing")
    listed = listed_match.group(1).decode("ascii").split(" ")
    if len(listed) != len(set(listed)) or any(
        IDENT.fullmatch(name.encode("ascii")) is None for name in listed
    ):
        raise DiscrepancyError("OP-1 explicit dotless list is malformed or duplicated")
    table_set = set(table_dotless)
    listed_set = set(listed)
    table_only = [name for name in table_dotless if name not in listed_set]
    listed_only = [name for name in listed if name not in table_set]
    evidence = {
        "listed_distinct_dotless_count": len(listed),
        "listed_dotless_identifiers": listed,
        "listed_only_count": len(listed_only),
        "listed_only_identifiers": listed_only,
        "listed_source": source.evidence(listed_match.start(1), listed_match.end(1)),
        "operation_name_occurrence_count": len(occurrences),
        "operation_row_count": len(lines) - 2,
        "table_distinct_dotless_count": len(table_dotless),
        "table_dotless_identifiers": table_dotless,
        "table_only_count": len(table_only),
        "table_only_identifiers": table_only,
        "table_source": source.evidence(table_start, table_end),
    }
    if enforce_pins:
        _pin(
            {
                "listed_count": len(listed),
                "listed_sha256": evidence["listed_source"]["sha256"],
                "listed_only_count": len(listed_only),
                "occurrences": len(occurrences),
                "rows": len(lines) - 2,
                "table_count": len(table_dotless),
                "table_only_count": len(table_only),
                "table_sha256": evidence["table_source"]["sha256"],
                "unique_operations": len(set(occurrences)),
            },
            {
                "listed_count": 20,
                "listed_sha256": "bca1f3a8ad911092756f1f18a459de95cd91062991b837b792e9d9de78fd41fc",
                "listed_only_count": 0,
                "occurrences": 84,
                "rows": 44,
                "table_count": 51,
                "table_only_count": 31,
                "table_sha256": "415a65e25e5c070ccbb7a51ebfb0b3d4ff2a8c42f2f151d3a23720198c352297",
                "unique_operations": 83,
            },
            "OP-1 discrepancy evidence",
        )
    return Observation(table_set != listed_set, evidence)


def _manifest_entries(raw: bytes) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    entries: list[dict[str, Any]] = []
    cases: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(raw.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith(b"#"):
            continue
        if len(entries) >= MAX_MANIFEST_ENTRIES:
            raise DiscrepancyError(
                f"manifest exceeds {MAX_MANIFEST_ENTRIES} semantic entries"
            )
        value = inputs.strict_json_loads(
            line,
            max_bytes=inputs.MAX_MANIFEST_BYTES,
            label=f"manifest line {line_number}",
        )
        if not isinstance(value, dict):
            raise DiscrepancyError(f"manifest line {line_number} is not an object")
        entries.append(value)
        if "id" in value:
            identifier = value["id"]
            if not isinstance(identifier, str) or inputs.CASE_ID.fullmatch(identifier) is None:
                raise DiscrepancyError(f"invalid manifest case id at line {line_number}")
            if identifier in cases:
                raise DiscrepancyError(f"duplicate manifest case id: {identifier}")
            cases[identifier] = value
    return entries, cases


def _protected_surface(
    entries: Sequence[dict[str, Any]],
    manifest_cases: Mapping[str, dict[str, Any]],
    case_sources: Mapping[str, bytes],
    protected: Mapping[str, Any],
) -> tuple[str, ...]:
    """Recompute every baseline entry while ignoring additive entries."""
    live: dict[str, str] = {}
    for entry in entries:
        if "id" in entry and entry["id"] in protected:
            identifier = entry["id"]
            path = f"conformance/cases/{identifier}.wf"
            if path not in case_sources:
                raise DiscrepancyError(f"protected manifest case has no source: {path}")
            projection = {
                field: entry.get(field)
                for field in ("id", "rules", "expect", "status")
            }
            encoded = json.dumps(
                projection, ensure_ascii=True, sort_keys=True, separators=(",", ":")
            ).encode("ascii")
            key = identifier
            digest = inputs.sha256(encoded + b"\0" + case_sources[path])
        elif "rule" in entry and f"rule:{entry['rule']}" in protected:
            key = f"rule:{entry['rule']}"
            digest = inputs.sha256(
                json.dumps(
                    entry, ensure_ascii=True, sort_keys=True, separators=(",", ":")
                ).encode("ascii")
            )
        else:
            continue
        if key in live:
            raise DiscrepancyError(f"duplicate protected-surface key in manifest: {key}")
        live[key] = digest

    case_ids = []
    for key, expected_digest in protected.items():
        if not isinstance(key, str):
            raise DiscrepancyError("guard baseline conformance key must be a string")
        if not isinstance(expected_digest, str) or inputs.HEX_SHA256.fullmatch(
            expected_digest
        ) is None:
            raise DiscrepancyError(
                f"guard baseline conformance digest is invalid for {key!r}"
            )
        if key not in live:
            raise DiscrepancyError(f"protected conformance entry is missing: {key}")
        if live[key] != expected_digest:
            raise DiscrepancyError(f"protected conformance entry changed: {key}")
        if inputs.CASE_ID.fullmatch(key):
            if key not in manifest_cases:
                raise DiscrepancyError(f"protected manifest case is missing: {key}")
            case_ids.append(key)
    case_ids.sort(key=str.encode)
    return tuple(case_ids)


def _skip_horizontal(line: bytes, cursor: int) -> tuple[int, bytes]:
    start = cursor
    while cursor < len(line) and line[cursor] in (0x20, 0x09):
        cursor += 1
    return cursor, line[start:cursor]


def _scan_balanced(line: bytes, cursor: int, opening: int, closing: int) -> int | None:
    if cursor >= len(line) or line[cursor] != opening:
        return None
    depth = 0
    while cursor < len(line):
        byte = line[cursor]
        if byte == opening:
            depth += 1
        elif byte == closing:
            depth -= 1
            if depth == 0:
                return cursor + 1
        cursor += 1
    return None


def scan_direct_fn_head(line: bytes) -> tuple[bytes, str] | None:
    """Classify spacing before a direct fn_decl parameter opener in one pass."""
    if not line.startswith(b"fn "):
        return None
    cursor = 3
    name_start = cursor
    name_terminators = b" \t<[(\r\n"
    while cursor < len(line) and line[cursor] not in name_terminators:
        cursor += 1
    if cursor == name_start:
        return None
    name = line[name_start:cursor]
    cursor, final_gap = _skip_horizontal(line, cursor)
    if cursor < len(line) and line[cursor] == 0x3C:  # <...>
        balanced = _scan_balanced(line, cursor, 0x3C, 0x3E)
        if balanced is None:
            return None
        cursor, final_gap = _skip_horizontal(line, balanced)
    if cursor < len(line) and line[cursor] == 0x5B:  # [...]
        balanced = _scan_balanced(line, cursor, 0x5B, 0x5D)
        if balanced is None:
            return None
        cursor, final_gap = _skip_horizontal(line, balanced)
    if cursor >= len(line) or line[cursor] != 0x28:  # (
        return None
    spacing = (
        "attached"
        if final_gap == b""
        else "single-space"
        if final_gap == b" "
        else "other-whitespace"
    )
    return name, spacing


def scan_case_declarations(
    raw: bytes,
    path: str,
    *,
    declarations_before: int = 0,
) -> tuple[dict[str, Any], ...]:
    """Return capped exact records for direct declarations in one case."""
    declarations: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw.splitlines(keepends=True), 1):
        scanned = scan_direct_fn_head(line)
        if scanned is None:
            continue
        if len(declarations) >= MAX_DECLARATIONS_PER_CASE:
            raise DiscrepancyError(
                f"{path} exceeds {MAX_DECLARATIONS_PER_CASE} declarations"
            )
        if declarations_before + len(declarations) >= MAX_DECLARATIONS_TOTAL:
            raise DiscrepancyError(
                f"protected corpus exceeds {MAX_DECLARATIONS_TOTAL} declarations"
            )
        name, spacing = scanned
        declarations.append(
            {
                "line": line_number,
                "line_sha256": inputs.sha256(line),
                "name_bytes_hex": name.hex(),
                "spacing": spacing,
            }
        )
    return tuple(declarations)


def _protected_form2_sources(
    protected_case_ids: Sequence[str],
    manifest_cases: Mapping[str, dict[str, Any]],
    case_sources: Mapping[str, bytes],
    *,
    include_legacy_orphan: bool,
) -> tuple[tuple[str, dict[str, Any] | None], ...]:
    """Name every protected source and distinguish manifest-backed authority."""
    sources: list[tuple[str, dict[str, Any] | None]] = [
        (f"conformance/cases/{identifier}.wf", manifest_cases[identifier])
        for identifier in protected_case_ids
    ]
    if include_legacy_orphan:
        orphan = case_sources.get(inputs.LEGACY_ORPHAN_PATH)
        if orphan is None:
            raise DiscrepancyError("legacy protected orphan source is missing")
        actual = inputs.sha256(orphan)
        if actual != inputs.LEGACY_ORPHAN_SHA256:
            raise DiscrepancyError(
                "legacy protected orphan source changed: "
                f"{actual} != {inputs.LEGACY_ORPHAN_SHA256}"
            )
        if any(path == inputs.LEGACY_ORPHAN_PATH for path, _ in sources):
            raise DiscrepancyError(
                "legacy protected orphan unexpectedly has a manifest entry"
            )
        sources.append((inputs.LEGACY_ORPHAN_PATH, None))
    sources.sort(key=lambda item: item[0].encode("utf-8"))
    return tuple(sources)


def observe_form2(
    manifest: bytes,
    case_sources: Mapping[str, bytes],
    *,
    protected_surface: Mapping[str, Any] | None = None,
    enforce_pins: bool = True,
) -> Observation:
    """Audit protected fn_decl heads with capped linear line scans."""
    entries, manifest_cases = _manifest_entries(manifest)
    if protected_surface is None:
        if enforce_pins:
            raise DiscrepancyError(
                "FORM-2 pinned audit requires the protected baseline surface"
            )
        protected_case_ids = tuple(sorted(manifest_cases, key=str.encode))
    else:
        protected_case_ids = _protected_surface(
            entries, manifest_cases, case_sources, protected_surface
        )

    protected_sources = _protected_form2_sources(
        protected_case_ids,
        manifest_cases,
        case_sources,
        include_legacy_orphan=protected_surface is not None,
    )

    rows = []
    total_declarations = 0
    counts: Counter[str] = Counter()
    manifested_counts: Counter[str] = Counter()
    unmanifested_counts: Counter[str] = Counter()
    affected_rows = []
    affected_manifest_entries = []
    for path, manifest_entry in protected_sources:
        if path not in case_sources:
            raise DiscrepancyError(f"protected case source is missing: {path}")
        raw = case_sources[path]
        declarations = scan_case_declarations(
            raw,
            path,
            declarations_before=total_declarations,
        )
        for declaration in declarations:
            total_declarations += 1
            spacing = declaration["spacing"]
            counts[spacing] += 1
            if manifest_entry is None:
                unmanifested_counts[spacing] += 1
            else:
                manifested_counts[spacing] += 1
        projection = None
        if manifest_entry is not None:
            projection = {
                field: manifest_entry.get(field)
                for field in ("id", "rules", "expect", "status")
            }
        row = {
            "direct_function_declarations": list(declarations),
            "manifest": projection,
            "path": path,
            "sha256": inputs.sha256(raw),
        }
        rows.append(row)
        if any(item["spacing"] == "single-space" for item in declarations):
            affected_rows.append(row)
            if manifest_entry is not None:
                affected_manifest_entries.append(manifest_entry)

    runnable = [
        entry
        for entry in affected_manifest_entries
        if entry.get("status") == "runnable"
    ]
    pending = [
        entry
        for entry in affected_manifest_entries
        if entry.get("status") == "pending"
    ]
    expected_rejections = [
        entry
        for entry in runnable
        if entry.get("expect") == {"kind": "reject", "rule": "FORM-2"}
    ]
    conflicting = len(runnable) - len(expected_rejections)
    manifested_rows = [row for row in rows if row["manifest"] is not None]
    unmanifested_rows = [row for row in rows if row["manifest"] is None]
    affected_manifested_rows = [
        row for row in affected_rows if row["manifest"] is not None
    ]
    affected_unmanifested_rows = [
        row for row in affected_rows if row["manifest"] is None
    ]
    inventory = [
        {
            "manifested": row["manifest"] is not None,
            "path": row["path"],
            "sha256": row["sha256"],
        }
        for row in rows
    ]
    positive = next(
        (
            row
            for row in rows
            if row["path"] == "conformance/cases/form2-pos-canonical-bytes.wf"
        ),
        None,
    )
    if positive is None and enforce_pins:
        raise DiscrepancyError("FORM-2 positive fixture is missing")
    evidence = {
        "attached_declaration_count": counts["attached"],
        "direct_function_declaration_count": total_declarations,
        "manifested_direct_function_declaration_count": sum(
            manifested_counts.values()
        ),
        "manifested_expected_form2_rejection_count": len(expected_rejections),
        "manifested_pending_source_files_with_single_space_count": len(pending),
        "manifested_runnable_other_expectation_count": conflicting,
        "manifested_runnable_source_files_with_single_space_count": len(runnable),
        "manifested_single_space_declaration_count": manifested_counts[
            "single-space"
        ],
        "other_whitespace_declaration_count": counts["other-whitespace"],
        "positive_fixture": positive,
        "protected_census_sha256": inputs.sha256(inputs.canonical_bytes(rows)),
        "protected_manifested_source_count": len(manifested_rows),
        "protected_manifested_source_files_with_single_space_count": len(
            affected_manifested_rows
        ),
        "protected_source_count": len(rows),
        "protected_source_files_with_single_space_count": len(affected_rows),
        "protected_source_inventory_sha256": inputs.sha256(
            inputs.canonical_bytes(inventory)
        ),
        "protected_surface_sha256": inputs.sha256(
            inputs.canonical_bytes(protected_surface)
        ),
        "protected_unmanifested_source_count": len(unmanifested_rows),
        "protected_unmanifested_source_files_with_single_space_count": len(
            affected_unmanifested_rows
        ),
        "single_space_declaration_count": counts["single-space"],
        "unmanifested_direct_function_declaration_count": sum(
            unmanifested_counts.values()
        ),
        "unmanifested_protected_sources": unmanifested_rows,
        "unmanifested_single_space_declaration_count": unmanifested_counts[
            "single-space"
        ],
    }
    if enforce_pins:
        assert positive is not None
        _pin(
            {
                key: evidence[key]
                for key in (
                    "attached_declaration_count",
                    "direct_function_declaration_count",
                    "manifested_direct_function_declaration_count",
                    "manifested_expected_form2_rejection_count",
                    "manifested_pending_source_files_with_single_space_count",
                    "manifested_runnable_other_expectation_count",
                    "manifested_runnable_source_files_with_single_space_count",
                    "manifested_single_space_declaration_count",
                    "other_whitespace_declaration_count",
                    "protected_census_sha256",
                    "protected_manifested_source_count",
                    "protected_manifested_source_files_with_single_space_count",
                    "protected_source_count",
                    "protected_source_files_with_single_space_count",
                    "protected_source_inventory_sha256",
                    "protected_unmanifested_source_count",
                    "protected_unmanifested_source_files_with_single_space_count",
                    "single_space_declaration_count",
                    "unmanifested_direct_function_declaration_count",
                    "unmanifested_single_space_declaration_count",
                )
            },
            {
                "attached_declaration_count": 2,
                "direct_function_declaration_count": 400,
                "manifested_direct_function_declaration_count": 399,
                "manifested_expected_form2_rejection_count": 2,
                "manifested_pending_source_files_with_single_space_count": 14,
                "manifested_runnable_other_expectation_count": 274,
                "manifested_runnable_source_files_with_single_space_count": 276,
                "manifested_single_space_declaration_count": 397,
                "other_whitespace_declaration_count": 0,
                "protected_census_sha256": (
                    "61fe48b74371fd2ea476cc901db8d30ce"
                    "07921ffa4ce30ba9c32577a6394beb5"
                ),
                "protected_manifested_source_count": 292,
                "protected_manifested_source_files_with_single_space_count": 290,
                "protected_source_count": 293,
                "protected_source_files_with_single_space_count": 291,
                "protected_source_inventory_sha256": (
                    "944773a3012e40d529f33b1bfe4d9069"
                    "a11eb0c365ae938e27d58977830c9700"
                ),
                "protected_unmanifested_source_count": 1,
                "protected_unmanifested_source_files_with_single_space_count": 1,
                "single_space_declaration_count": 398,
                "unmanifested_direct_function_declaration_count": 1,
                "unmanifested_single_space_declaration_count": 1,
            },
            "FORM-2 protected-surface evidence",
        )
        _pin(
            evidence["unmanifested_protected_sources"],
            [
                {
                    "direct_function_declarations": [
                        {
                            "line": 3,
                            "line_sha256": (
                                "e58d474de015a09840860e8f233684239"
                                "005a29ace4a3ba58c17903fdd13326e"
                            ),
                            "name_bytes_hex": "6d61696e",
                            "spacing": "single-space",
                        }
                    ],
                    "manifest": None,
                    "path": inputs.LEGACY_ORPHAN_PATH,
                    "sha256": inputs.LEGACY_ORPHAN_SHA256,
                }
            ],
            "FORM-2 unmanifested protected-source evidence",
        )
        _pin(
            {
                "declarations": positive["direct_function_declarations"],
                "manifest": positive["manifest"],
                "sha256": positive["sha256"],
            },
            {
                "declarations": [
                    {
                        "line": 1,
                        "line_sha256": (
                            "01da3f7b8d2822839e71e050e99e46eb"
                            "38a794d3e4b8054e5d5f361a184ab29c"
                        ),
                        "name_bytes_hex": "6d61696e",
                        "spacing": "single-space",
                    }
                ],
                "manifest": {
                    "expect": {"exit": 0, "kind": "run"},
                    "id": "form2-pos-canonical-bytes",
                    "rules": ["FORM-2"],
                    "status": "runnable",
                },
                "sha256": "202d27f9d94e35c1a5d36eb04046e25774273f73783efb0609fb4e7e9e5c9218",
            },
            "FORM-2 positive-fixture evidence",
        )
    return Observation(conflicting > 0, evidence)


def observe_form4(
    specification: bytes,
    source_index: Mapping[str, Any],
    *,
    enforce_pins: bool = True,
) -> Observation:
    """Compare FORM-4's doc citation with the indexed doc production owner."""
    source = ExactSource.from_bytes("spec/kernel-spec-v0.8.md", specification)
    statement = b"Documentation is the `doc` field of declarations [GRAM-3]."
    statement_span = source.unique(statement)
    citation = re.search(rb"\[(GRAM-[0-9]+)\]", statement)
    if citation is None:
        raise DiscrepancyError("FORM-4 documentation citation is missing")
    cited_owner = citation.group(1).decode("ascii")

    productions = source_index.get("syntax_productions")
    if not isinstance(productions, list):
        raise DiscrepancyError("source index syntax_productions must be an array")
    matches = [
        item
        for item in productions
        if isinstance(item, dict) and item.get("id") == "production:GRAM-2:doc"
    ]
    if len(matches) != 1:
        raise DiscrepancyError(
            "source index must contain exactly one production:GRAM-2:doc"
        )
    production = matches[0]
    production_source = production.get("source")
    if production.get("lhs") != "doc" or not isinstance(production_source, dict):
        raise DiscrepancyError("indexed doc production has invalid content")
    owner = production.get("owner_rule")
    start = production_source.get("byte_start")
    end = production_source.get("byte_end")
    if not isinstance(owner, str) or isinstance(start, bool) or not isinstance(start, int):
        raise DiscrepancyError("indexed doc production has invalid owner or start")
    if isinstance(end, bool) or not isinstance(end, int):
        raise DiscrepancyError("indexed doc production has invalid end")
    indexed_evidence = source.evidence(start, end)
    source_fields = ("byte_end", "byte_start", "line_end", "line_start", "sha256")
    if {key: indexed_evidence[key] for key in source_fields} != {
        key: production_source.get(key) for key in source_fields
    }:
        raise DiscrepancyError("indexed doc production source span is stale")
    evidence = {
        "doc_production_id": production["id"],
        "doc_production_lhs": production["lhs"],
        "doc_production_owner": owner,
        "doc_production_source": indexed_evidence,
        "form4_cited_owner": cited_owner,
        "form4_citation_source": source.evidence(*statement_span),
    }
    if enforce_pins:
        _pin(
            {
                "doc_owner": owner,
                "doc_sha256": indexed_evidence["sha256"],
                "form4_owner": cited_owner,
                "form4_sha256": evidence["form4_citation_source"]["sha256"],
            },
            {
                "doc_owner": "GRAM-2",
                "doc_sha256": "62075dc6f83e384ce0bea4df8876944089e916f855f9e78b315d02c34e3fccb1",
                "form4_owner": "GRAM-3",
                "form4_sha256": "73ef840b5d5d7f45dcacb899e42f7d6a0be0af400a1cce8371da8721a1cd56d4",
            },
            "FORM-4 documentation cross-reference evidence",
        )
    return Observation(cited_owner != owner, evidence)


def observe_form5_form7(
    specification: bytes,
    *,
    enforce_pins: bool = True,
) -> Observation:
    """Record the normative-vs-deferred float-canonicality conflict."""
    source = ExactSource.from_bytes("spec/kernel-spec-v0.8.md", specification)
    form5_clause = (
        b"the canonical spelling is the unique shortest decimal digit string that "
        b"round-trips under round-to-nearest-even, with at least one integer and "
        b"one fraction digit, lowercase `e`, and no leading zeros; "
    )
    form7_clause = (
        b"The canonical decimal spelling of a float value is gated on the FORM-1 "
        b"reject-vs-canonicalize decision and DEFERRED.\n"
    )
    form5_span = source.unique(form5_clause)
    form7_span = source.unique(form7_clause)
    evidence = {
        "form5_disposition": "normative-unique-shortest-rne-roundtrip",
        "form5_source": source.evidence(*form5_span),
        "form7_disposition": "explicitly-deferred",
        "form7_source": source.evidence(*form7_span),
    }
    if enforce_pins:
        _pin(
            {
                "form5_span": [*form5_span],
                "form5_sha256": evidence["form5_source"]["sha256"],
                "form7_span": [*form7_span],
                "form7_sha256": evidence["form7_source"]["sha256"],
            },
            {
                "form5_span": [9125, 9325],
                "form5_sha256": "3b25dca20138b9ef5f797dae0565329818835c7190f04e1d1b83108800157c6a",
                "form7_span": [11240, 11357],
                "form7_sha256": "268dc6c19eacf8f247fad3a3402746692fee5ce709aeace0b3a1254f497f118e",
            },
            "FORM-5/FORM-7 float-canonicality evidence",
        )
    return Observation(True, evidence)


def observe_fn7(specification: bytes, *, enforce_pins: bool = True) -> Observation:
    """Compare FN-7's main return spelling with grammar and EX-1."""
    source = ExactSource.from_bytes("spec/kernel-spec-v0.8.md", specification)
    fn_decl = (
        b'fn_decl      := "fn" IDENT generics? region_params? "(" param_list? ")"\n'
        b'                "->" rtype effects requires_block? "{" doc? stmt* "}"\n'
    )
    rtype = b"rtype  := mode type\n"
    fn7_signature = b"fn main() -> unit"
    example_line = b"fn main() -> own unit traps {\n"
    fn_decl_span = source.unique(fn_decl)
    rtype_span = source.unique(rtype)
    fn7_span = source.unique(fn7_signature)
    example_span = source.unique(example_line)
    evidence = {
        "example_main_return_spelling": "own unit",
        "example_main_source": source.evidence(*example_span),
        "fn7_main_return_spelling": "unit",
        "fn7_main_source": source.evidence(*fn7_span),
        "fn_decl_return_nonterminal": "rtype",
        "fn_decl_source": source.evidence(*fn_decl_span),
        "rtype_shape": "mode type",
        "rtype_source": source.evidence(*rtype_span),
    }
    if enforce_pins:
        _pin(
            {
                key: evidence[key]["sha256"]
                for key in (
                    "example_main_source",
                    "fn7_main_source",
                    "fn_decl_source",
                    "rtype_source",
                )
            },
            {
                "example_main_source": (
                    "3c21e58f403384c5f0b6f119e1c6e64"
                    "e916b48bea8a58355724ec5a9f4642165"
                ),
                "fn7_main_source": (
                    "2687d72b3742432ba69de3203f96d293"
                    "08347ac8825558f829fa766f6a3b8fc8"
                ),
                "fn_decl_source": (
                    "7937beaad997465d1e80dcc0eae3573d"
                    "3de754bd5b7762a561760bf98adc9508"
                ),
                "rtype_source": "c9e5b6dead005a9feb5a7adb849ce60d0bc0dcd6051f3b64892a0f7c383eeac4",
            },
            "FN-7 discrepancy evidence",
        )
    return Observation(True, evidence)


def observe_gram1_gram7(
    specification: bytes,
    *,
    enforce_pins: bool = True,
) -> Observation:
    """Compare the global production bijection with GRAM-7's shared node."""
    source = ExactSource.from_bytes("spec/kernel-spec-v0.8.md", specification)
    gram1_clause = (
        b"Every production maps 1:1 to one core-tree node kind; there is no "
        b"desugaring."
    )
    gram7_clause = (
        b"appears in two disjoint productions sharing one core-tree node kind "
        b"[META-1]"
    )
    gram1_span = source.unique(gram1_clause)
    gram7_span = source.unique(gram7_clause)
    evidence = {
        "gram1_constraint": "one-production-to-one-node-kind-bijection",
        "gram1_source": source.evidence(*gram1_span),
        "gram7_constraint": "two-productions-share-one-match-node-kind",
        "gram7_source": source.evidence(*gram7_span),
    }
    if enforce_pins:
        _pin(
            {
                "gram1_span": [*gram1_span],
                "gram1_sha256": evidence["gram1_source"]["sha256"],
                "gram7_span": [*gram7_span],
                "gram7_sha256": evidence["gram7_source"]["sha256"],
            },
            {
                "gram1_span": [12268, 12345],
                "gram1_sha256": "0f10dd0af3c839004ed9fae81ee6118043a10ed9cf48476a0c406f6a3386cfe2",
                "gram7_span": [16129, 16205],
                "gram7_sha256": "d131bea381d9e91bac481198b82a0c931bbff919066db77073cd50a67d9fe414",
            },
            "GRAM-1/GRAM-7 node-bijection evidence",
        )
    return Observation(True, evidence)


def validate_registry(
    observations: Mapping[str, Observation],
) -> dict[str, Registration]:
    """Require a bijection between registrations and recomputed predicates."""
    registrations: dict[str, Registration] = {}
    predicate_ids: set[str] = set()
    for registration in REGISTRATIONS:
        if registration.identifier in registrations:
            raise DiscrepancyError(
                f"duplicate discrepancy registration: {registration.identifier}"
            )
        if registration.predicate_identifier in predicate_ids:
            raise DiscrepancyError(
                f"duplicate discrepancy predicate: {registration.predicate_identifier}"
            )
        if not registration.affected_facet_ids or list(
            registration.affected_facet_ids
        ) != sorted(set(registration.affected_facet_ids)):
            raise DiscrepancyError(
                f"affected facets are empty, duplicated, or unsorted: {registration.identifier}"
            )
        if not registration.resolution_authorities or list(
            registration.resolution_authorities
        ) != sorted(set(registration.resolution_authorities)):
            raise DiscrepancyError(
                "resolution authorities are empty, duplicated, or unsorted: "
                f"{registration.identifier}"
            )
        registrations[registration.identifier] = registration
        predicate_ids.add(registration.predicate_identifier)
    registered_ids = set(registrations)
    observed_ids = set(observations)
    if registered_ids != observed_ids:
        raise DiscrepancyError(
            "discrepancy registrations and predicate observations differ; "
            f"unobserved={sorted(registered_ids - observed_ids)}, "
            f"unregistered={sorted(observed_ids - registered_ids)}"
        )
    return registrations


def recompute(authorities: inputs.AuthorityInputs) -> dict[str, Observation]:
    """Recompute every registered predicate from one authority snapshot."""
    observations = {
        "discrepancy:v0.8/op1-dotless-reservation": observe_op1(
            authorities.specification
        ),
        "discrepancy:v0.8/form2-protected-conformance-spacing": observe_form2(
            authorities.manifest,
            authorities.case_sources,
            protected_surface=authorities.protected_conformance,
        ),
        "discrepancy:v0.8/form4-doc-cross-reference": observe_form4(
            authorities.specification, authorities.source_index
        ),
        "discrepancy:v0.8/form5-form7-float-canonical-spelling": observe_form5_form7(
            authorities.specification
        ),
        "discrepancy:v0.8/fn7-main-return-spelling": observe_fn7(
            authorities.specification
        ),
        "discrepancy:v0.8/gram1-gram7-match-node-bijection": observe_gram1_gram7(
            authorities.specification
        ),
    }
    validate_registry(observations)
    return observations
