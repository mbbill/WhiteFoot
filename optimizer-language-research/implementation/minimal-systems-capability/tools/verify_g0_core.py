#!/usr/bin/env python3
"""Verify the complete G0-Core research artifact set."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parents[2]
TOOLS = ROOT / "tools"
MANIFEST = ROOT / "G0-CORE-ARTIFACT-MANIFEST.json"

EXPECTED_ROWS = {
    "CAPABILITY-OBLIGATION-REGISTRY.tsv": 49,
    "RUST-1.97.0-API-INVENTORY.tsv": 16432,
    "RUST-1.97.0-MODULE-ACCOUNTING.tsv": 290,
    "RUST-1.97.0-DOMAIN-CLASSIFICATION.tsv": 5369,
    "RUST-1.97.0-MODULE-DOMAIN-MAP.tsv": 290,
    "RUST-DATA-CONTRACT-CENSUS.tsv": 258,
    "RUST-DATA-SURFACE-MAP.tsv": 545,
    "RUST-D10-SURFACE-MAP.tsv": 150,
    "DERIVATION-MATRIX.tsv": 258,
}

AUTHORED_TEXT = [
    "G0-CORE-CHARTER.md",
    "RUST-CENSUS-NOTES.md",
    "DOMAIN-CLASSIFICATION-RULES.tsv",
    "RUST-1.97.0-DOMAIN-CLASSIFICATION.tsv",
    "RUST-1.97.0-DOMAIN-SUMMARY.tsv",
    "RUST-1.97.0-MODULE-DOMAIN-MAP.tsv",
    "SYSTEMS-DOMAIN-LEDGER.md",
    "RUST-DATA-CONTRACT-CENSUS.md",
    "RUST-DATA-CONTRACT-CENSUS.tsv",
    "RUST-DATA-SURFACE-MAP.tsv",
    "RUST-D10-SURFACE-MAP.tsv",
    "CAPABILITY-OBLIGATION-REGISTRY.tsv",
    "SEMANTIC-OBLIGATION-REGISTRY.md",
    "DERIVATION-MATRIX.tsv",
    "WITNESS-REGISTRY.md",
    "E01-TRACEABILITY.md",
    "FAMILY-LOCK-A-TEMPLATE.md",
    "G0-CORE-REPORT.md",
    "tools/extract_rust_api.py",
    "tools/verify_rust_census.py",
    "tools/classify_rust_api.py",
    "tools/verify_rust_data_contract_census.py",
    "tools/build_d10_surface_map.py",
    "tools/verify_derivation_matrix.py",
    "tools/verify_g0_core.py",
    "tools/build_g0_manifest.py",
]


def fail(message: str) -> None:
    raise SystemExit(f"G0-Core verification failed: {message}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_tsv(relative: str) -> tuple[list[str], list[dict[str, str]]]:
    path = ROOT / relative
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    if any(None in row for row in rows):
        fail(f"extra TSV columns in {relative}")
    if any(any("\r" in value or "\n" in value for value in row.values()) for row in rows):
        fail(f"embedded newline in {relative}")
    return fields, rows


def run_verifier(script: str) -> None:
    result = subprocess.run(
        [sys.executable, "-B", str(TOOLS / script)],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        fail(f"{script} returned {result.returncode}")
    print(result.stdout, end="")


def verify_generated_classifier() -> None:
    generated = [
        ROOT / "RUST-1.97.0-DOMAIN-CLASSIFICATION.tsv",
        ROOT / "RUST-1.97.0-DOMAIN-SUMMARY.tsv",
        ROOT / "RUST-1.97.0-MODULE-DOMAIN-MAP.tsv",
    ]
    before = {path: sha256(path) for path in generated}
    run_verifier("classify_rust_api.py")
    after = {path: sha256(path) for path in generated}
    if before != after:
        fail("generated domain outputs were stale before verification")


def verify_row_counts() -> None:
    for relative, expected in EXPECTED_ROWS.items():
        _, rows = read_tsv(relative)
        if len(rows) != expected:
            fail(f"{relative} has {len(rows)} rows, expected {expected}")


def verify_domain_routes() -> None:
    fields, declarations = read_tsv("RUST-1.97.0-DOMAIN-CLASSIFICATION.tsv")
    expected_fields = [
        "canonical_key",
        "representative_path",
        "item_kind",
        "member_kind",
        "member_name",
        "caller_safety",
        "surface_evidence_status",
        "surface_evidence_reason",
        "rule_id",
        "domain_id",
        "domain",
        "canonical_contract_id",
        "need_route_kind",
        "need_route_id",
        "need_route_reason",
        "required_frame_ids",
        "safe_displacement_id",
        "ng_authority_reason",
        "canonical_route_or_blocked_claim",
    ]
    if fields != expected_fields:
        fail(f"unexpected declaration-route schema: {fields}")
    keys = [row["canonical_key"] for row in declarations]
    if len(keys) != len(set(keys)):
        fail("duplicate canonical declaration domain route")
    safety = Counter(row["caller_safety"] for row in declarations)
    if safety != {"safe": 5096, "unsafe": 273}:
        fail(f"unexpected domain safety counts: {dict(safety)}")
    evidence_counts = Counter(row["surface_evidence_status"] for row in declarations)
    if evidence_counts != {
        "safe_contract_anchor": 4609,
        "safe_boundary_evidence": 170,
        "unsafe_boundary_evidence": 273,
        "rust_surface_only": 317,
    }:
        fail(f"unexpected surface evidence counts: {dict(evidence_counts)}")
    route_counts = Counter(row["need_route_kind"] for row in declarations)
    if route_counts != {
        "G0_CONTRACT": 1033,
        "LIB_CONTRACT": 302,
        "LATER_FAMILY": 3765,
        "FRAME": 7,
        "REDUNDANT": 43,
        "NO_INDEPENDENT_NEED": 217,
        "NG": 2,
    }:
        fail(f"unexpected need-route counts: {dict(route_counts)}")

    valid_evidence = {
        "safe_contract_anchor",
        "safe_boundary_evidence",
        "unsafe_boundary_evidence",
        "rust_surface_only",
    }
    valid_routes = {
        "G0_CONTRACT",
        "LIB_CONTRACT",
        "LATER_FAMILY",
        "FRAME",
        "REDUNDANT",
        "NG",
        "NO_INDEPENDENT_NEED",
    }
    valid_frames = {
        "F-MEM",
        "F-ALLOC",
        "F-TRAP",
        "F-BUILD",
        "F-IO",
        "F-FS",
        "F-PROC",
        "F-ABI",
        "F-NET",
        "F-CLOCK",
        "F-THREAD",
        "F-SYNC",
        "F-ASYNC",
        "F-TARGET",
        "F-MMIO",
    }
    _, contracts = read_tsv("RUST-DATA-CONTRACT-CENSUS.tsv")
    contract_ids = {row["contract_id"] for row in contracts}
    _, capabilities = read_tsv("CAPABILITY-OBLIGATION-REGISTRY.tsv")
    capability_ids = {row["capability_id"] for row in capabilities}

    for row in declarations:
        key = row["canonical_key"]
        evidence = row["surface_evidence_status"]
        route = row["need_route_kind"]
        if evidence not in valid_evidence:
            fail(f"invalid surface evidence status for {key}: {evidence}")
        if route not in valid_routes:
            fail(f"invalid need route kind for {key}: {route}")
        if not row["surface_evidence_reason"]:
            fail(f"missing surface evidence reason for {key}")
        if not row["need_route_id"] or not row["need_route_reason"]:
            fail(f"missing need route identity or reason for {key}")
        if row["caller_safety"] == "unsafe" and evidence != "unsafe_boundary_evidence":
            fail(f"Rust-unsafe declaration is not boundary evidence: {key}")
        if evidence == "unsafe_boundary_evidence" and row["caller_safety"] != "unsafe":
            fail(f"unsafe boundary evidence has a safe Rust caller: {key}")
        if evidence == "safe_boundary_evidence" and row["caller_safety"] != "safe":
            fail(f"safe boundary evidence has an unsafe Rust caller: {key}")
        boundary = evidence in {"safe_boundary_evidence", "unsafe_boundary_evidence"}
        if boundary and not row["safe_displacement_id"]:
            fail(f"boundary evidence lacks a safe displacement: {key}")
        if row["safe_displacement_id"].startswith(("RAW-", "NG:")):
            fail(f"safe displacement names raw or non-goal evidence: {key}")
        if not boundary and route != "NG" and row["safe_displacement_id"]:
            fail(f"non-boundary non-NG row has a spurious safe displacement: {key}")
        if route == "NG":
            if not row["ng_authority_reason"]:
                fail(f"NG route lacks owner authority and reason: {key}")
            if not re.search(
                r"(?:CONSTITUTION|owner directive D[0-9]+|EFF-[0-9]+)",
                row["ng_authority_reason"],
            ):
                fail(f"NG route lacks a recognizable authority citation: {key}")
            if not row["safe_displacement_id"]:
                fail(f"NG route lacks a safe displacement: {key}")
        elif row["ng_authority_reason"]:
            fail(f"non-NG route carries an NG authority reason: {key}")

        frames = row["required_frame_ids"].split(";") if row["required_frame_ids"] else []
        if len(frames) != len(set(frames)) or any(frame not in valid_frames for frame in frames):
            fail(f"invalid required frame set for {key}: {frames}")
        if route == "FRAME":
            if not frames or not row["need_route_id"].startswith("FRAME:"):
                fail(f"terminal frame route is not an exact boundary service: {key}")
        elif row["need_route_id"].startswith("FRAME:"):
            fail(f"non-frame route uses a frame route ID: {key}")
        if row["domain_id"] in {"D15", "D16", "D17", "D18", "D19", "D20", "D21", "D22", "D23", "D24"} and route == "FRAME":
            fail(f"OS/FFI/concurrency/target declaration incorrectly terminates at FRAME: {key}")

        if route == "G0_CONTRACT":
            route_id = row["need_route_id"]
            known = route_id in contract_ids
            known = known or (
                route_id.startswith("CAP:") and route_id[4:] in capability_ids
            )
            known = known or bool(re.fullmatch(r"SPEC:[A-Z]+-[0-9]+", route_id))
            if not known:
                fail(f"G0 route lacks a stable contract, obligation, or spec ID: {key}")
        if row["canonical_contract_id"] and row["canonical_contract_id"] not in contract_ids:
            fail(f"unknown canonical contract ID for {key}")
        if not re.fullmatch(r"D(?:0[1-9]|1[0-9]|2[0-5])", row["domain_id"]):
            fail(f"invalid public domain ID {row['domain_id']}")

    ng_keys = {
        row["canonical_key"] for row in declarations if row["need_route_kind"] == "NG"
    }
    if ng_keys != {
        "src/std/panic.rs.html#358|item|catch_unwind",
        "src/std/panic.rs.html#390|item|resume_unwind",
    }:
        fail(f"unexpected true non-goal declarations: {sorted(ng_keys)}")

    _, surface_map = read_tsv("RUST-DATA-SURFACE-MAP.tsv")
    mapped_contracts = {
        row["canonical_key"]: row["primary_contract_id"] for row in surface_map
    }
    iteration_map_path = ROOT / "RUST-D10-SURFACE-MAP.tsv"
    if iteration_map_path.is_file():
        iteration_fields, iteration_rows = read_tsv("RUST-D10-SURFACE-MAP.tsv")
        if iteration_fields != [
            "canonical_key",
            "representative_path",
            "member_name",
            "route_kind",
            "route_id",
            "route_reason",
        ]:
            fail("unexpected iteration surface-map schema")
        iteration_keys = [row["canonical_key"] for row in iteration_rows]
        if len(iteration_keys) != len(set(iteration_keys)):
            fail("duplicate canonical declaration in the iteration crosswalk")
        for row in iteration_rows:
            if row["route_kind"] not in {"contract", "redundant_surface"}:
                fail(f"invalid iteration crosswalk route kind for {row['canonical_key']}")
            if row["route_id"] not in contract_ids:
                fail(f"unknown iteration crosswalk contract for {row['canonical_key']}")
            previous = mapped_contracts.get(row["canonical_key"])
            if previous is not None and previous != row["route_id"]:
                fail(f"conflicting data and iteration crosswalk for {row['canonical_key']}")
            mapped_contracts[row["canonical_key"]] = row["route_id"]
    classified_contracts = {
        row["canonical_key"]: row["canonical_contract_id"]
        for row in declarations
        if row["canonical_contract_id"]
    }
    if classified_contracts != mapped_contracts:
        fail("detailed declaration-to-contract routes disagree with the surface map")

    def require_canary(
        path: str, member: str, expected: dict[str, str], minimum: int = 1
    ) -> None:
        matches = [
            row
            for row in declarations
            if row["representative_path"] == path and row["member_name"] == member
        ]
        if len(matches) < minimum:
            fail(f"missing semantic route canary {(path, member)}")
        for row in matches:
            actual = {field: row[field] for field in expected}
            if actual != expected:
                fail(
                    f"semantic route canary {(path, member)} is {actual}, expected {expected}"
                )

    require_canary(
        "alloc::vec::Vec",
        "spare_capacity_mut",
        {
            "surface_evidence_status": "safe_boundary_evidence",
            "domain_id": "D09",
            "need_route_kind": "G0_CONTRACT",
            "need_route_id": "RAW-SAFE-SPARE-01",
            "safe_displacement_id": "CAP:OW-INIT",
        },
    )
    require_canary(
        "core::mem::MaybeUninit",
        "assume_init",
        {
            "surface_evidence_status": "unsafe_boundary_evidence",
            "domain_id": "D04",
            "need_route_kind": "G0_CONTRACT",
            "need_route_id": "CAP:OW-INIT",
            "required_frame_ids": "F-MEM",
            "safe_displacement_id": "CAP:OW-INIT",
        },
    )
    require_canary(
        "core::slice",
        "get_unchecked",
        {
            "surface_evidence_status": "unsafe_boundary_evidence",
            "domain_id": "D09",
            "need_route_kind": "G0_CONTRACT",
            "need_route_id": "CAP:BR-PROV",
            "safe_displacement_id": "CAP:BR-PROV",
        },
    )
    require_canary(
        "core::sync::atomic::Atomic",
        "from_ptr",
        {
            "surface_evidence_status": "unsafe_boundary_evidence",
            "domain_id": "D22",
            "need_route_kind": "LATER_FAMILY",
            "need_route_id": "FAMILY:D22:CHECKED-ATOMIC-ADDRESSING",
            "required_frame_ids": "F-SYNC",
            "safe_displacement_id": "FAMILY:D22:CHECKED-ATOMIC-ADDRESSING",
        },
    )
    require_canary(
        "core::sync::atomic::AtomicPtr",
        "AtomicPtr",
        {
            "surface_evidence_status": "safe_boundary_evidence",
            "domain_id": "D22",
            "need_route_kind": "LATER_FAMILY",
            "need_route_id": "FAMILY:D22:ATOMICS-AND-SYNCHRONIZATION",
            "required_frame_ids": "F-SYNC",
            "safe_displacement_id": "FAMILY:D22:ATOMICS-AND-SYNCHRONIZATION",
        },
    )
    require_canary(
        "alloc::vec::Vec",
        "into_raw_parts",
        {
            "surface_evidence_status": "safe_boundary_evidence",
            "domain_id": "D04",
            "need_route_kind": "LATER_FAMILY",
            "need_route_id": "RAW-SAFE-OWNERSHIP-01",
            "required_frame_ids": "F-MEM",
            "safe_displacement_id": "FAMILY:D04:CHECKED-OWNERSHIP-TRANSFER",
        },
    )
    require_canary(
        "core::mem::forget",
        "forget",
        {
            "surface_evidence_status": "safe_boundary_evidence",
            "domain_id": "D04",
            "need_route_kind": "LATER_FAMILY",
            "need_route_id": "FAMILY:D04:EXPLICIT-RESOURCE-ABANDONMENT",
            "safe_displacement_id": "FAMILY:D04:EXPLICIT-RESOURCE-ABANDONMENT",
        },
    )
    require_canary(
        "alloc::boxed::Box",
        "downcast",
        {
            "domain_id": "D13",
            "need_route_kind": "LATER_FAMILY",
            "need_route_id": "BOX-DOWNCAST-01",
        },
        minimum=3,
    )
    require_canary(
        "alloc::boxed::Box",
        "into_pin",
        {
            "domain_id": "D23",
            "need_route_kind": "LATER_FAMILY",
            "need_route_id": "BOX-PIN-01",
        },
    )
    require_canary(
        "core::pointer",
        "read_volatile",
        {
            "surface_evidence_status": "unsafe_boundary_evidence",
            "domain_id": "D24",
            "need_route_kind": "LATER_FAMILY",
            "need_route_id": "FAMILY:D24:CHECKED-VOLATILE-MMIO",
            "required_frame_ids": "F-MMIO",
            "safe_displacement_id": "FAMILY:D24:CHECKED-VOLATILE-MMIO",
        },
        minimum=2,
    )
    require_canary(
        "std::os::unix::fs::FileExt",
        "read_at",
        {
            "domain_id": "D16",
            "need_route_kind": "LATER_FAMILY",
            "need_route_id": "FAMILY:D16:FILESYSTEMS",
            "required_frame_ids": "F-FS",
        },
    )
    require_canary(
        "std::os::unix::process::CommandExt",
        "exec",
        {
            "domain_id": "D17",
            "need_route_kind": "LATER_FAMILY",
            "need_route_id": "FAMILY:D17:PROCESS-ENVIRONMENT",
            "required_frame_ids": "F-PROC",
        },
    )
    require_canary(
        "core::mem::swap",
        "swap",
        {
            "domain_id": "D04",
            "need_route_kind": "G0_CONTRACT",
            "need_route_id": "CAP:OW-SWAP",
        },
    )
    require_canary(
        "std::is_x86_feature_detected",
        "is_x86_feature_detected",
        {
            "surface_evidence_status": "rust_surface_only",
            "domain_id": "D24",
            "need_route_kind": "LATER_FAMILY",
            "need_route_id": "FAMILY:D24:TARGET-FEATURE-DETECTION",
            "required_frame_ids": "F-TARGET",
        },
    )

    module_fields, modules = read_tsv("RUST-1.97.0-MODULE-DOMAIN-MAP.tsv")
    if module_fields != [
        "crate",
        "module_path",
        "mode",
        "rule_id",
        "domain_id",
        "domain",
        "module_route_kind",
        "module_route_id",
        "entry_digest",
    ]:
        fail(f"unexpected module-route schema: {module_fields}")
    module_paths = [row["module_path"] for row in modules]
    if len(module_paths) != len(set(module_paths)):
        fail("duplicate reachable module domain route")
    if any(
        row["module_route_kind"] != "NO_INDEPENDENT_NEED"
        or not row["module_route_id"].startswith("NAMESPACE:")
        for row in modules
    ):
        fail("module namespace incorrectly claims an independent need")
    domain_ids = {row["domain_id"] for row in declarations + modules}
    expected_ids = {f"D{index:02d}" for index in range(1, 27)}
    if domain_ids != expected_ids:
        fail(f"domain ledger coverage differs: {sorted(domain_ids)}")
    holding = [
        row["module_path"]
        for row in modules
        if row["rule_id"] == "DOM-UNSTABLE-RUNTIME-HOLDING"
    ]
    if holding != ["core::panicking"]:
        fail(f"unexpected unresolved D26 module holding routes: {holding}")


def verify_witness_budgets() -> None:
    witness = (ROOT / "WITNESS-REGISTRY.md").read_text(encoding="utf-8")
    if re.search(r"\b(?:ST|OW|EX|BR|FL|ID|AB|IT|FT|FAM)-\*", witness):
        fail("witness dependency budget contains a wildcard")

    _, capabilities = read_tsv("CAPABILITY-OBLIGATION-REGISTRY.tsv")
    _, contracts = read_tsv("RUST-DATA-CONTRACT-CENSUS.tsv")
    known_ids = {row["capability_id"] for row in capabilities}
    known_ids.update(row["contract_id"] for row in contracts)
    known_ids.update(
        {
            "K-SCALAR",
            "FAM-DENSE",
            "FAM-UMAP",
            "F-MEM",
            "F-ALLOC",
            "F-TRAP",
            "F-BUILD",
            "F-IO",
            "F-FS",
            "F-PROC",
            "F-ABI",
            "F-NET",
            "F-CLOCK",
            "F-THREAD",
            "F-SYNC",
            "F-ASYNC",
            "F-TARGET",
            "F-MMIO",
        }
    )
    known_ids.update(re.findall(r"^\| ((?:B|W)-[A-Z0-9-]+) \|", witness, re.MULTILINE))
    known_ids.update(re.findall(r"^### ((?:H|O)-[A-Z0-9-]+)\b", witness, re.MULTILINE))
    known_ids.update(re.findall(r"^- \*\*((?:O)-[A-Z0-9-]+):", witness, re.MULTILINE))

    identifier = re.compile(
        r"\b(?:ST|OW|EX|BR|FL|ID|AB|IT|FT|BOX|K|FAM|B|W|H|O|F)-[A-Z0-9-]+\b"
    )
    unresolved = sorted(set(identifier.findall(witness)) - known_ids)
    if unresolved:
        fail(f"witness registry contains unresolved dependency IDs: {unresolved}")

    for line in witness.splitlines():
        if not line.startswith("| W-"):
            continue
        columns = line.split("|")
        if len(columns) != 7:
            fail(f"malformed visible witness row: {line[:80]}")
        budget_ids = identifier.findall(columns[-2])
        if not budget_ids or len(budget_ids) != len(set(budget_ids)):
            fail(f"empty or duplicate visible witness dependency budget: {columns[1].strip()}")

    required_fragments = {
        "closed frame privilege rule": "A frame token likewise grants only its reviewed public checked",
        "arena borrow-safe reset": "reset/destroy is rejected until every phase borrow ends",
        "arena no address-family dependency": "without importing the deferred address-stability family",
        "pool exhaustion policy": "insertion returns `IdentityExhausted`",
        "LRU unique lookup": "lookup takes unique cache access",
        "IPQ held-out heap implementation": "the held-out itself\nimplements heap order",
        "store exhaustive allowlist": "The allowlist above is exhaustive",
    }
    for subject, fragment in required_fragments.items():
        if fragment not in witness:
            fail(f"witness registry lost the {subject}")
    arena_row = next(line for line in witness.splitlines() if line.startswith("| W-ARENA "))
    if "ID-ADDRESS" in arena_row:
        fail("W-ARENA imports the deferred physical-address capability")
    if "FAM-HEAP" in witness:
        fail("H-IPQ imports a finished heap instead of testing reverse-index repair")


def verify_template_markers() -> None:
    template = (ROOT / "FAMILY-LOCK-A-TEMPLATE.md").read_text(encoding="utf-8")
    markers = re.findall(r"<[^>]+>", template)
    required_prefix = "<required" + ": "
    if not markers or any(not marker.startswith(required_prefix) for marker in markers):
        fail("Family Lock template has an invalid field marker")
    for relative in AUTHORED_TEXT:
        if relative == "FAMILY-LOCK-A-TEMPLATE.md":
            continue
        if ("<required" + ":") in (ROOT / relative).read_text(encoding="utf-8"):
            fail(f"unresolved template marker outside Family Lock template: {relative}")


def verify_repository_language_rule() -> None:
    han = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
    forbidden_marker = re.compile(r"\b(?:TODO|TBD|FIXME)\b", re.IGNORECASE)
    for relative in AUTHORED_TEXT:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        if han.search(text):
            fail(f"CJK prose marker in authored artifact {relative}")
        marker_text = text
        if relative == "DOMAIN-CLASSIFICATION-RULES.tsv":
            _, rows = read_tsv(relative)
            marker_text = "\n".join(
                row["canonical_route_or_blocked_claim"] + "\t" + row["rationale"]
                for row in rows
            )
        elif relative == "RUST-1.97.0-DOMAIN-CLASSIFICATION.tsv":
            _, rows = read_tsv(relative)
            prose_fields = [
                "surface_evidence_reason",
                "domain",
                "need_route_reason",
                "ng_authority_reason",
                "canonical_route_or_blocked_claim",
            ]
            marker_text = "\n".join(
                "\t".join(row[field] for field in prose_fields) for row in rows
            )
        marker_text = re.sub(r"`[^`\n]*`", "", marker_text)
        if not relative.startswith("tools/") and forbidden_marker.search(marker_text):
            fail(f"unfinished-work marker in authored artifact {relative}")
        if any(line.rstrip() != line for line in text.splitlines()):
            fail(f"trailing whitespace in authored artifact {relative}")
    if (REPO / "AGENTS.md").read_bytes() != (REPO / "CLAUDE.md").read_bytes():
        fail("AGENTS.md and CLAUDE.md are not byte-identical")


def verify_manifest() -> None:
    if not MANIFEST.is_file():
        fail("missing G0-CORE-ARTIFACT-MANIFEST.json")
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if payload.get("schema") != "xlang-g0-core-artifact-manifest-v1":
        fail("unexpected exact-artifact manifest schema")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or payload.get("artifact_count") != len(artifacts):
        fail("exact-artifact manifest count mismatch")
    for entry in artifacts:
        relative = entry.get("path")
        if not isinstance(relative, str):
            fail("manifest artifact path is not a string")
        path = ROOT / relative
        if not path.is_file():
            fail(f"manifest artifact is missing: {relative}")
        if entry.get("sha256") != sha256(path):
            fail(f"manifest hash mismatch: {relative}")
        if entry.get("bytes") != path.stat().st_size:
            fail(f"manifest byte count mismatch: {relative}")
        if path.suffix == ".tsv":
            _, rows = read_tsv(relative)
            if entry.get("data_rows") != len(rows):
                fail(f"manifest row count mismatch: {relative}")


def main() -> None:
    run_verifier("verify_rust_census.py")
    verify_generated_classifier()
    run_verifier("verify_rust_data_contract_census.py")
    run_verifier("verify_derivation_matrix.py")
    verify_row_counts()
    verify_domain_routes()
    verify_witness_budgets()
    verify_template_markers()
    verify_repository_language_rule()
    verify_manifest()
    print(
        "G0-Core verification: PASS — exact census, domains, contracts, "
        "derivations, template, language rule, and manifest are consistent"
    )


if __name__ == "__main__":
    main()
