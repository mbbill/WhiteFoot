#!/usr/bin/env python3
"""Frozen, fail-closed coverage authorities for dense Family Lock A.

This module is deliberately independent of ``build_dense_lock.py``.  It reads
every G0 input through ``git show`` at the reviewed closing commit, expands
selector parents without discarding helper identities, and emits exact
target, member/outcome, payload-overlay, role, and capability bindings.  It
contains no candidate implementation and performs no scoring.

The public ``build_authorities`` and ``validate_authorities`` functions are
intended for import by the lock builder and hostile verifier.  Running this
file writes only the new ``*-AUTHORITY.tsv`` files named in ``OUTPUT_FIELDS``;
``--check`` compares the expected bytes without writing.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from dense_lock_model import CLUSTER_MEMBERS, EXCLUDED_MEMBERS


FAMILY_ID = "F-DENSE"
G0_CLOSING_COMMIT = "a4de0eb70c345dcd198b11f435a5538ccc863113"
G0_MANIFEST_SHA256 = "f0eced756688affef1732a133c43fb39ab6fc672334dca27b26129ddb5123719"
HERE = Path(__file__).resolve().parent
CAPABILITY_ROOT = HERE.parent
REPO = CAPABILITY_ROOT.parents[2]
CAPABILITY_PREFIX = (
    "optimizer-language-research/implementation/"
    "minimal-systems-capability"
)

G0_INPUTS = (
    "G0-CORE-ARTIFACT-MANIFEST.json",
    "G0-COVERAGE-EVIDENCE-UNIVERSE.tsv",
    "G0-CLUSTER-FAMILY-ROUTING.tsv",
    "G0-TRAIT-IMPL-TOPOLOGY-ROUTING.tsv",
    "RUST-1.97.0-TRAIT-IMPL-CROSSWALK.tsv",
    "RUST-DATA-SURFACE-MAP.tsv",
    "RUST-D10-SURFACE-MAP.tsv",
    "RUST-DATA-UNSAFE-EVIDENCE-MAP.tsv",
    "PAYLOAD-SCOPE-CLASSIFICATION.tsv",
    "PAYLOAD-SCOPE-OVERLAY.tsv",
    "G0-FAMILY-REQUIREMENT-REGISTRY.tsv",
    "CAPABILITY-OBLIGATION-REGISTRY.tsv",
)

SELECTOR_KINDS = {
    "CLUSTER_RUST_SURFACES_SELECTOR",
    "CLUSTER_IMPLEMENTATION_PRIVILEGE_SELECTOR",
    "CLUSTER_SOURCE_REFS_SELECTOR",
}
LEGAL_TERMINALS = {
    "REFINED_IN_LOCK",
    "PREDECESSOR_PROVED",
    "EXCLUDED_BLOCKS_CLAIM",
}
NO_FUZZY_MARKERS = ("FUZZY", "DEFAULT", "SUBSTRING", "FALLBACK")


OUTPUT_FIELDS: Mapping[str, tuple[str, ...]] = {
    "DENSE-FROZEN-G0-INPUT-AUTHORITY.tsv": (
        "source_path",
        "git_commit",
        "git_blob_oid",
        "byte_count",
        "sha256",
        "access_method",
        "consumer",
    ),
    "DENSE-SELECTOR-EXPANSION-AUTHORITY.tsv": (
        "parent_evidence_identity",
        "cluster_id",
        "selector_kind",
        "parent_value_sha256",
        "child_ordinal",
        "child_identity",
        "child_kind",
        "child_value",
        "child_value_sha256",
        "anchored_evidence_identity_ids",
        "applicable_target_ids",
        "f_dense_member_contract_ids",
        "target_authority",
        "member_authority",
        "expansion_grammar",
    ),
    "DENSE-EVIDENCE-TARGET-AUTHORITY.tsv": (
        "subject_kind",
        "subject_identity",
        "parent_evidence_identity",
        "cluster_id",
        "evidence_kind",
        "target_id",
        "target_ordinal",
        "terminal_disposition",
        "member_contract_ids",
        "required_predecessor_family_ids",
        "required_predecessor_gate_stage_ids",
        "blocked_claims",
        "target_authority",
        "member_authority",
    ),
    "DENSE-EVIDENCE-MEMBER-AUTHORITY.tsv": (
        "subject_kind",
        "subject_identity",
        "parent_evidence_identity",
        "cluster_id",
        "target_id",
        "member_contract_id",
        "outcome_id",
        "unit_status",
        "mapping_authority",
        "outcome_binding_authority",
    ),
    "DENSE-OVERLAY-BRANCH-AUTHORITY.tsv": (
        "cluster_id",
        "overlay_branch_id",
        "role",
        "member_contract_id",
        "outcome_id",
        "binding_state",
        "base_capability_ids",
        "conditional_capability_ids",
        "effective_capability_ids",
        "source_disposition",
        "reopening_trigger_sha256",
        "binding_authority",
    ),
    "DENSE-ROLE-UNIT-AUTHORITY.tsv": (
        "obligation_id",
        "record_kind",
        "role",
        "workload_or_operation",
        "closure_owner_or_gate_stage",
        "owner_lock_disposition",
        "implicated_rebind_disposition",
        "binding_kind",
        "member_contract_id",
        "outcome_id",
        "control_or_witness_id",
        "primary_canary_id",
        "crosscut_canary_ids",
        "canary_source_sha256",
        "binding_authority",
    ),
    "DENSE-CAPABILITY-UNIT-AUTHORITY.tsv": (
        "capability_id",
        "dimension",
        "applicability",
        "binding_kind",
        "member_contract_id",
        "outcome_id",
        "overlay_branch_id",
        "control_id",
        "binding_authority",
    ),
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def ordered_digest(values: Iterable[str]) -> str:
    material = "".join(f"{value}\n" for value in values)
    return sha256_text(material)


def csv_ids(value: str) -> tuple[str, ...]:
    if not value or value == "NONE":
        return ()
    values = tuple(part.strip() for part in value.split(",") if part.strip())
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate comma-separated identity: {value}")
    return values


def ordered_union(order: Sequence[str], *groups: Iterable[str]) -> tuple[str, ...]:
    selected = {item for group in groups for item in group}
    unknown = selected - set(order)
    if unknown:
        raise ValueError(f"unknown ordered identity: {sorted(unknown)}")
    return tuple(item for item in order if item in selected)


def tsv_bytes(fields: Sequence[str], rows: Sequence[Mapping[str, object]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for source in rows:
        row = {field: str(source.get(field, "")) for field in fields}
        if any(any(mark in value for mark in ("\t", "\r", "\n")) for value in row.values()):
            raise ValueError("authority TSV value contains a control character")
        writer.writerow(row)
    return stream.getvalue().encode("utf-8")


def parse_tsv(data: bytes, source: str) -> list[dict[str, str]]:
    text = data.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter="\t")
    if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError(f"invalid or duplicate TSV header in {source}")
    result = list(reader)
    if any(None in row for row in result):
        raise ValueError(f"over-wide TSV row in {source}")
    return result


@dataclass(frozen=True)
class FrozenFile:
    relative: str
    repo_relative: str
    blob_oid: str
    data: bytes

    @property
    def sha256(self) -> str:
        return sha256_bytes(self.data)


class FrozenG0Snapshot:
    """Read-only access to one reviewed Git commit, never the worktree."""

    def __init__(
        self,
        repo: Path = REPO,
        commit: str = G0_CLOSING_COMMIT,
        capability_prefix: str = CAPABILITY_PREFIX,
    ) -> None:
        self.repo = repo
        self.commit = self._git("rev-parse", f"{commit}^{{commit}}").decode().strip()
        if self.commit != G0_CLOSING_COMMIT:
            raise ValueError(
                f"G0 commit mismatch: expected {G0_CLOSING_COMMIT}, got {self.commit}"
            )
        self.capability_prefix = capability_prefix
        self._cache: dict[str, FrozenFile] = {}

    def _git(self, *arguments: str) -> bytes:
        return subprocess.check_output(
            ["git", *arguments], cwd=self.repo, stderr=subprocess.PIPE
        )

    def file(self, relative: str) -> FrozenFile:
        if relative not in G0_INPUTS:
            raise KeyError(f"unregistered frozen G0 input: {relative}")
        if relative not in self._cache:
            repo_relative = f"{self.capability_prefix}/{relative}"
            blob_oid = self._git("rev-parse", f"{self.commit}:{repo_relative}").decode().strip()
            data = self._git("show", f"{self.commit}:{repo_relative}")
            self._cache[relative] = FrozenFile(relative, repo_relative, blob_oid, data)
        return self._cache[relative]

    def rows(self, relative: str) -> list[dict[str, str]]:
        return parse_tsv(self.file(relative).data, relative)

    def input_authority(self) -> list[dict[str, object]]:
        result = []
        for relative in G0_INPUTS:
            frozen = self.file(relative)
            result.append(
                {
                    "source_path": frozen.repo_relative,
                    "git_commit": self.commit,
                    "git_blob_oid": frozen.blob_oid,
                    "byte_count": len(frozen.data),
                    "sha256": frozen.sha256,
                    "access_method": "GIT_SHOW_COMMIT_PATH_ONLY",
                    "consumer": "dense_coverage_authority.py",
                }
            )
        return result


def split_top_level(value: str, delimiter: str = ";") -> list[str]:
    depth = 0
    start = 0
    result: list[str] = []
    for index, character in enumerate(value):
        if character in "{([":
            depth += 1
        elif character in "})]":
            depth -= 1
            if depth < 0:
                raise ValueError(f"unbalanced selector: {value}")
        elif character == delimiter and depth == 0:
            token = value[start:index].strip()
            if not token:
                raise ValueError(f"empty selector clause: {value}")
            result.append(token)
            start = index + 1
    if depth:
        raise ValueError(f"unbalanced selector: {value}")
    token = value[start:].strip()
    if not token:
        raise ValueError(f"empty selector tail: {value}")
    result.append(token)
    return result


def expand_braces(value: str) -> list[str]:
    start = value.find("{")
    if start < 0:
        return [value]
    depth = 0
    end = -1
    for index in range(start, len(value)):
        if value[index] == "{":
            depth += 1
        elif value[index] == "}":
            depth -= 1
            if depth == 0:
                end = index
                break
    if end < 0:
        raise ValueError(f"unbalanced selector brace: {value}")
    alternatives = split_top_level(value[start + 1 : end], ",")
    result: list[str] = []
    for alternative in alternatives:
        result.extend(expand_braces(value[:start] + alternative + value[end + 1 :]))
    return result


CANARY_LIST_RE = re.compile(
    r"compiled temporary (?P<names>[a-z0-9_, ]+(?:and [a-z0-9_]+)?) canaries$"
)
OWNING_HELPER_RE = re.compile(
    r"^(?:.*; )?owning helpers=(?P<namespace>"
    r"array|vec|vec_deque|linked_list|binary_heap|btree_map|btree_set|hash_map|hash_set"
    r")::IntoIter$"
)


def grammar_children(selector_kind: str, selected_value: str) -> list[tuple[str, str]]:
    """Expand all frozen clauses and separately name helper identities."""
    if selector_kind not in SELECTOR_KINDS:
        raise ValueError(f"unknown selector kind: {selector_kind}")
    clauses: list[str] = []
    for clause in split_top_level(selected_value):
        if selector_kind == "CLUSTER_RUST_SURFACES_SELECTOR":
            clauses.extend(expand_braces(clause))
        else:
            clauses.append(clause)
    result: list[tuple[str, str]] = []
    for clause in clauses:
        kind = "HELPER_TYPE" if OWNING_HELPER_RE.fullmatch(clause) else "SELECTOR_CLAUSE"
        result.append((kind, clause))
        match = CANARY_LIST_RE.search(clause)
        if match:
            normalized = match.group("names").replace(" and ", ",")
            names = [name.strip() for name in normalized.split(",") if name.strip()]
            if not names or len(names) != len(set(names)):
                raise ValueError(f"invalid helper canary list: {clause}")
            result.extend(("HELPER_CANARY", name) for name in names)
    if len(result) != len(set(result)):
        raise ValueError(f"duplicate selector grammar child: {selected_value}")
    return result


# Exact operation-to-member assignments.  A cluster with one frozen member is
# assigned by singleton equality; every multi-member direct surface must occur
# in this closed table.  There is no textual containment or fallback rule.
EXACT_OPERATION_MEMBERS: Mapping[tuple[str, str], tuple[str, ...]] = {
    ("VIEW-SORT-01", "sort"): ("DENSE-SORT-STABLE",),
    ("VIEW-SORT-01", "sort_by"): ("DENSE-SORT-STABLE",),
    ("VIEW-SORT-01", "sort_by_key"): ("DENSE-SORT-STABLE",),
    ("VIEW-SORT-01", "sort_by_cached_key"): ("DENSE-SORT-STABLE-CACHED-KEY",),
    ("VIEW-REORDER-01", "reverse"): ("DENSE-REVERSE",),
    ("VIEW-REORDER-01", "rotate_left"): ("DENSE-ROTATE",),
    ("VIEW-REORDER-01", "rotate_right"): ("DENSE-ROTATE",),
    ("VIEW-SWAP-01", "swap"): ("DENSE-SWAP",),
    ("VIEW-SWAP-01", "swap_with_slice"): ("DENSE-SWAP-WITH-VIEW",),
    ("VIEW-COPY-01", "copy_from_slice"): ("DENSE-COPY-FROM",),
    ("VIEW-COPY-01", "copy_within"): ("DENSE-COPY-WITHIN",),
    ("VIEW-FILL-01", "fill"): ("DENSE-FILL-CLONE",),
    ("VIEW-FILL-01", "fill_with"): ("DENSE-FILL-WITH",),
    ("VIEW-ALLOC-01", "to_vec"): ("DENSE-FRESH-CLONE",),
    ("VIEW-ALLOC-01", "into_vec"): ("DENSE-INTO-OWNER",),
    ("VIEW-CONCAT-01", "concat"): ("DENSE-CONCAT",),
    ("VIEW-CONCAT-01", "join"): ("DENSE-JOIN",),
    ("VIEW-CONCAT-01", "connect"): ("DENSE-JOIN",),
    ("VIEW-CONCAT-01", "repeat"): ("DENSE-REPEAT",),
    ("INIT-WRITE-01", "write_copy_of_slice"): ("DENSE-INIT-COPY",),
    ("INIT-WRITE-01", "write_clone_of_slice"): ("DENSE-INIT-CLONE",),
    ("SEQ-META-01", "new"): ("DENSE-NEW",),
    ("SEQ-META-01", "with_capacity"): ("DENSE-WITH-CAPACITY",),
    ("SEQ-META-01", "capacity"): ("DENSE-META",),
    ("SEQ-META-01", "len"): ("DENSE-META",),
    ("SEQ-META-01", "is_empty"): ("DENSE-META",),
    ("SEQ-RESERVE-01", "reserve"): ("DENSE-RESERVE",),
    ("SEQ-RESERVE-01", "reserve_exact"): ("DENSE-RESERVE-EXACT",),
    ("SEQ-TRY-RESERVE-01", "try_reserve"): ("DENSE-TRY-RESERVE",),
    ("SEQ-TRY-RESERVE-01", "try_reserve_exact"): ("DENSE-TRY-RESERVE-EXACT",),
    ("SEQ-SHRINK-01", "shrink_to"): ("DENSE-SHRINK-TO",),
    ("SEQ-SHRINK-01", "shrink_to_fit"): ("DENSE-SHRINK-TO-FIT",),
    ("SEQ-PUSH-01", "push"): ("DENSE-PUSH",),
    ("SEQ-PUSH-01", "push_mut"): ("DENSE-PUSH-UNIQ",),
    ("SEQ-INSERT-01", "insert"): ("DENSE-INSERT",),
    ("SEQ-INSERT-01", "insert_mut"): ("DENSE-INSERT-UNIQ",),
    ("SEQ-POP-01", "pop"): ("DENSE-POP",),
    ("SEQ-POP-01", "pop_if"): ("DENSE-POP-IF",),
    ("SEQ-REMOVE-01", "remove"): ("DENSE-REMOVE",),
    ("SEQ-REMOVE-01", "swap_remove"): ("DENSE-SWAP-REMOVE",),
    ("SEQ-EXTEND-COPY-01", "extend_from_slice"): ("DENSE-EXTEND-CLONE",),
    ("SEQ-EXTEND-COPY-01", "extend_from_within"): ("DENSE-EXTEND-WITHIN",),
    ("SEQ-RESIZE-01", "resize"): ("DENSE-RESIZE-CLONE",),
    ("SEQ-RESIZE-01", "resize_with"): ("DENSE-RESIZE-WITH",),
    ("SEQ-TRUNCATE-01", "truncate"): ("DENSE-TRUNCATE",),
    ("SEQ-TRUNCATE-01", "clear"): ("DENSE-CLEAR",),
    ("SEQ-RETAIN-01", "retain"): ("DENSE-RETAIN",),
    ("SEQ-RETAIN-01", "retain_mut"): ("DENSE-RETAIN-MUT",),
    ("SEQ-DEDUP-01", "dedup"): ("DENSE-DEDUP",),
    ("SEQ-DEDUP-01", "dedup_by"): ("DENSE-DEDUP-BY",),
    ("SEQ-DEDUP-01", "dedup_by_key"): ("DENSE-DEDUP-BY-KEY",),
    ("SEQ-EXTRACT-01", "extract_if"): ("DENSE-LAZY-EXTRACT-EVIDENCE",),
    ("SEQ-SPLICE-01", "splice"): ("DENSE-LAZY-SPLICE-EVIDENCE",),
    ("SEQ-CONVERT-01", "into_boxed_slice"): ("DENSE-INTO-BOXED",),
    ("SEQ-CONVERT-01", "into_flattened"): ("DENSE-INTO-FLATTENED",),
}


def members_of_clusters(*cluster_ids: str) -> set[str]:
    unknown = set(cluster_ids) - set(CLUSTER_MEMBERS)
    if unknown:
        raise ValueError(f"unknown cluster in member group: {sorted(unknown)}")
    return {member for cluster in cluster_ids for member in CLUSTER_MEMBERS[cluster]}


ALL_MEMBERS = {member for members in CLUSTER_MEMBERS.values() for member in members}
INCLUDED_MEMBERS = ALL_MEMBERS - set(EXCLUDED_MEMBERS)


def direct_operation_members(cluster_id: str, member_name: str) -> tuple[str, ...]:
    members = tuple(CLUSTER_MEMBERS[cluster_id])
    if len(members) == 1:
        return members
    key = (cluster_id, member_name)
    if key not in EXACT_OPERATION_MEMBERS:
        raise ValueError(f"missing exact operation/member assignment: {key}")
    result = EXACT_OPERATION_MEMBERS[key]
    if not set(result) <= set(members):
        raise ValueError(f"operation/member assignment escapes cluster: {key}")
    return result


def unique_index(
    rows: Sequence[dict[str, str]], field: str, source: str
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        key = row[field]
        if not key or key in result:
            raise ValueError(f"missing or duplicate {field} in {source}: {key!r}")
        result[key] = row
    return result


@dataclass
class AuthorityContext:
    snapshot: FrozenG0Snapshot
    route_rows: list[dict[str, str]]
    route_by_cluster: dict[str, dict[str, str]]
    audit_clusters: tuple[str, ...]
    evidence_rows: list[dict[str, str]]
    evidence_by_cluster: dict[str, list[dict[str, str]]]
    evidence_by_identity: dict[str, dict[str, str]]
    topology_by_impl: dict[str, dict[str, str]]
    crosswalk_by_impl: dict[str, dict[str, str]]
    safe_by_key: dict[str, dict[str, str]]
    d10_by_key: dict[str, dict[str, str]]
    unsafe_by_key: dict[str, dict[str, str]]
    overlay_rows: list[dict[str, str]]
    requirement_rows: list[dict[str, str]]
    capability_rows: list[dict[str, str]]


def load_context(snapshot: FrozenG0Snapshot | None = None) -> AuthorityContext:
    snapshot = snapshot or FrozenG0Snapshot()
    route_rows = snapshot.rows("G0-CLUSTER-FAMILY-ROUTING.tsv")
    route_by_cluster = unique_index(route_rows, "cluster_id", "cluster routing")
    audit_clusters = tuple(
        row["cluster_id"]
        for row in route_rows
        if FAMILY_ID
        in (
            csv_ids(row["primary_refinement_owner_or_gate_stage"])
            + csv_ids(row["implicated_or_reopening_family_ids"])
        )
    )
    if set(audit_clusters) != set(CLUSTER_MEMBERS):
        raise ValueError(
            "dense cluster model does not equal the immutable routed audit domain: "
            f"missing={sorted(set(audit_clusters) - set(CLUSTER_MEMBERS))}, "
            f"extra={sorted(set(CLUSTER_MEMBERS) - set(audit_clusters))}"
        )
    all_evidence = snapshot.rows("G0-COVERAGE-EVIDENCE-UNIVERSE.tsv")
    evidence_rows = [row for row in all_evidence if row["cluster_id"] in audit_clusters]
    evidence_by_identity = unique_index(evidence_rows, "evidence_identity", "evidence universe")
    evidence_by_cluster: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in evidence_rows:
        evidence_by_cluster[row["cluster_id"]].append(row)
    for cluster_id in audit_clusters:
        expected = int(route_by_cluster[cluster_id]["evidence_child_count"])
        if len(evidence_by_cluster[cluster_id]) != expected:
            raise ValueError(f"immutable evidence count mismatch for {cluster_id}")
    return AuthorityContext(
        snapshot=snapshot,
        route_rows=route_rows,
        route_by_cluster=route_by_cluster,
        audit_clusters=audit_clusters,
        evidence_rows=evidence_rows,
        evidence_by_cluster=dict(evidence_by_cluster),
        evidence_by_identity=evidence_by_identity,
        topology_by_impl=unique_index(
            snapshot.rows("G0-TRAIT-IMPL-TOPOLOGY-ROUTING.tsv"),
            "impl_key",
            "topology routing",
        ),
        crosswalk_by_impl=unique_index(
            snapshot.rows("RUST-1.97.0-TRAIT-IMPL-CROSSWALK.tsv"),
            "impl_key",
            "trait implementation crosswalk",
        ),
        safe_by_key=unique_index(
            snapshot.rows("RUST-DATA-SURFACE-MAP.tsv"),
            "canonical_key",
            "safe surface map",
        ),
        d10_by_key=unique_index(
            snapshot.rows("RUST-D10-SURFACE-MAP.tsv"),
            "canonical_key",
            "D10 surface map",
        ),
        unsafe_by_key=unique_index(
            snapshot.rows("RUST-DATA-UNSAFE-EVIDENCE-MAP.tsv"),
            "canonical_key",
            "unsafe evidence map",
        ),
        overlay_rows=[
            row
            for row in snapshot.rows("PAYLOAD-SCOPE-OVERLAY.tsv")
            if row["contract_id"] in audit_clusters
        ],
        requirement_rows=snapshot.rows("G0-FAMILY-REQUIREMENT-REGISTRY.tsv"),
        capability_rows=snapshot.rows("CAPABILITY-OBLIGATION-REGISTRY.tsv"),
    )


@dataclass(frozen=True)
class SubjectAuthority:
    subject_kind: str
    subject_identity: str
    parent_evidence_identity: str
    cluster_id: str
    evidence_kind: str
    targets: tuple[str, ...]
    members: tuple[str, ...]
    target_authority: str
    member_authority: str
    predecessor_families: Mapping[str, tuple[str, ...]]
    predecessor_gates: Mapping[str, tuple[str, ...]]


ACTIVE_SOURCE_TARGET_BY_ITEM_PATH: Mapping[str, str] = {
    "std::array": "F-DENSE",
    "std::slice": "F-DENSE",
    "alloc::vec::Vec": "F-DENSE",
    "alloc::boxed::Box": "F-RECURSIVE",
}


def concrete_members(crosswalk: Mapping[str, str], cluster_id: str) -> tuple[str, ...]:
    if cluster_id == "TRAIT-INTOITER-01":
        implementer = crosswalk["implementer"]
        if re.fullmatch(r"&'a mut .+", implementer):
            return ("DENSE-ITER-UNIQ",)
        if re.fullmatch(r"&'a .+", implementer):
            return ("DENSE-ITER-SHARED",)
        if implementer.startswith("&"):
            raise ValueError(f"unrecognized IntoIterator reference grammar: {implementer}")
        return ("DENSE-ITER-OWN",)
    if cluster_id == "TRAIT-INDEX-01":
        trait_path = crosswalk["trait_path"]
        terminal = trait_path.rsplit("::", 1)[-1]
        if terminal == "Index":
            return ("DENSE-INDEX-SHARED",)
        if terminal == "IndexMut":
            return ("DENSE-INDEX-UNIQ",)
        raise ValueError(f"unrecognized index trait path: {trait_path}")
    if cluster_id == "TRAIT-CMP-01":
        terminal = crosswalk["trait_path"].rsplit("::", 1)[-1]
        if terminal == "Hash":
            return ("DENSE-HASH-TRAVERSAL",)
        if terminal in {"PartialEq", "Eq", "PartialOrd", "Ord"}:
            return ("DENSE-COMPARE",)
        raise ValueError(f"unrecognized comparison/hash trait: {terminal}")
    fixed = {
        "TRAIT-EXTEND-01": ("DENSE-EXTEND-ITER",),
        "TRAIT-COLLECT-01": ("DENSE-COLLECT",),
        "TRAIT-DEREF-01": ("DENSE-OWNER-VIEW",),
        "TRAIT-BORROW-01": ("DENSE-OWNER-VIEW",),
        "TRAIT-CONVERT-01": ("DENSE-CONVERT",),
        "TRAIT-CLONE-01": ("DENSE-FRESH-CLONE", "DENSE-CLONE-FROM"),
        "TRAIT-DEFAULT-01": ("DENSE-DEFAULT",),
        "TRAIT-DROP-01": ("DENSE-DROP",),
    }
    if cluster_id not in fixed:
        raise ValueError(f"concrete implementation in unsupported cluster: {cluster_id}")
    return fixed[cluster_id]


def direct_subject(context: AuthorityContext, evidence: dict[str, str]) -> SubjectAuthority:
    kind = evidence["evidence_kind"]
    if kind in SELECTOR_KINDS:
        raise ValueError("selector parent is not a direct subject")
    cluster_id = evidence["cluster_id"]
    route = context.route_by_cluster[cluster_id]
    predecessors_f: dict[str, tuple[str, ...]] = {}
    predecessors_g: dict[str, tuple[str, ...]] = {}
    members: tuple[str, ...] = ()

    if kind == "CONCRETE_TRAIT_IMPL":
        key = evidence["evidence_key"]
        topology = context.topology_by_impl[key]
        crosswalk = context.crosswalk_by_impl[key]
        primary = topology["primary_refinement_family_or_gate"]
        if primary != evidence["applicability_primary_refinement_family_or_gate"]:
            raise ValueError(f"concrete primary target mismatch: {key}")
        targets = list(csv_ids(primary))
        additional = csv_ids(evidence["applicability_additional_operation_gate_stage_ids"])
        for target in additional:
            if target not in targets:
                targets.append(target)
        if FAMILY_ID in targets:
            members = concrete_members(crosswalk, cluster_id)
        predecessors_f[primary] = csv_ids(topology["required_predecessor_family_ids"])
        predecessors_g[primary] = csv_ids(topology["required_predecessor_gate_stage_ids"])
        for target in additional:
            immediate = csv_ids(
                evidence[
                    "applicability_additional_operation_gate_child_specific_immediate_predecessor_family_or_gate_ids"
                ]
            )
            route_f = csv_ids(route["required_predecessor_family_ids"])
            route_g = csv_ids(route["required_predecessor_gate_stage_ids"])
            predecessors_f[target] = tuple(dict.fromkeys(route_f + tuple(x for x in immediate if x.startswith("F-"))))
            predecessors_g[target] = tuple(dict.fromkeys(route_g + tuple(x for x in immediate if x.startswith("GATE-"))))
        target_authority = "EXACT_IMPL_KEY_TO_FROZEN_TOPOLOGY_ROUTE_AND_OPERATION_GATE"
        member_authority = "EXACT_TRAIT_PATH_AND_IMPLEMENTER_GRAMMAR"
    else:
        primary = route["primary_refinement_owner_or_gate_stage"]
        if route["route_state"] == "BOUNDARY":
            targets = list(csv_ids(primary))
            target_authority = "EXACT_BOUNDARY_SOURCE_KEY_TO_FROZEN_REJECTION_GATE"
            member_authority = "NONE_NON_DENSE_BOUNDARY_TARGET"
        elif kind == "STABLE_SAFE_SURFACE":
            source = context.safe_by_key[evidence["evidence_key"]]
            item_path = source["item_path"]
            if item_path not in ACTIVE_SOURCE_TARGET_BY_ITEM_PATH:
                raise ValueError(f"unclassified exact safe item_path: {item_path}")
            target = ACTIVE_SOURCE_TARGET_BY_ITEM_PATH[item_path]
            if target != primary:
                raise ValueError(
                    f"exact source topology disagrees with route for {evidence['evidence_key']}: "
                    f"{target} != {primary}"
                )
            targets = [target]
            if target == FAMILY_ID:
                members = direct_operation_members(cluster_id, source["member_name"])
            target_authority = "EXACT_SAFE_KEY_ITEM_PATH_CLOSED_TOPOLOGY_ENUM"
            member_authority = "EXACT_SAFE_MEMBER_NAME_CLOSED_ASSIGNMENT"
        elif kind in {"D10_CONTRACT_ROUTE", "D10_REDUNDANT_SURFACE_ROUTE"}:
            source = context.d10_by_key[evidence["evidence_key"]]
            if source["route_id"] != cluster_id:
                raise ValueError(f"D10 route mismatch for {evidence['evidence_key']}")
            targets = list(csv_ids(primary))
            target_authority = "EXACT_D10_KEY_TO_FROZEN_ROUTE_OWNER"
            member_authority = "NONE_GENERIC_PROTOCOL_DECLARATION_TARGET"
        elif kind == "STABLE_UNSAFE_EVIDENCE":
            source = context.unsafe_by_key[evidence["evidence_key"]]
            if source["evidence_cluster_id"] != cluster_id:
                raise ValueError(f"unsafe route mismatch for {evidence['evidence_key']}")
            targets = list(csv_ids(primary))
            target_authority = "EXACT_UNSAFE_KEY_TO_FROZEN_REJECTION_GATE"
            member_authority = "NONE_NON_DENSE_BOUNDARY_TARGET"
        else:
            raise ValueError(f"unknown direct evidence kind: {kind}")
        for target in targets:
            predecessors_f[target] = csv_ids(route["required_predecessor_family_ids"])
            predecessors_g[target] = csv_ids(route["required_predecessor_gate_stage_ids"])

    if not targets or len(targets) != len(set(targets)):
        raise ValueError(f"missing or duplicate exact targets: {evidence['evidence_identity']}")
    if FAMILY_ID in targets and not members:
        raise ValueError(f"dense direct subject has no exact member: {evidence['evidence_identity']}")
    if not set(members) <= set(CLUSTER_MEMBERS[cluster_id]):
        raise ValueError(f"direct subject member escapes cluster: {evidence['evidence_identity']}")
    return SubjectAuthority(
        subject_kind="DIRECT_EVIDENCE",
        subject_identity=evidence["evidence_identity"],
        parent_evidence_identity="NONE",
        cluster_id=cluster_id,
        evidence_kind=kind,
        targets=tuple(targets),
        members=members,
        target_authority=target_authority,
        member_authority=member_authority,
        predecessor_families=predecessors_f,
        predecessor_gates=predecessors_g,
    )


HELPER_TARGETS: Mapping[str, str] = {
    "array": "F-DENSE",
    "vec": "F-DENSE",
    "vec_deque": "F-DEQUE",
    "linked_list": "GATE-LINKED-COMPOSITION",
    "binary_heap": "F-HEAP",
    "btree_map": "F-ORDERED",
    "btree_set": "F-ORDERED",
    "hash_map": "F-SPARSE",
    "hash_set": "F-SPARSE",
}


SURFACE_SELECTOR_NAMESPACE_BY_ITEM_PATH: Mapping[str, str] = {
    "alloc::boxed::Box": "Box",
    "alloc::rc::Rc": "Rc",
    "alloc::vec::Vec": "Vec",
    "core::slice": "slice",
    "std::array": "array",
    "std::collections::HashMap": "HashMap",
    "std::slice": "slice",
}
SURFACE_SELECTOR_CHILD_RE = re.compile(
    r"^(?P<namespace>array|slice|Vec|Box|Rc|HashMap|mem)::"
    r"(?P<member>[A-Za-z_][A-Za-z0-9_]*)"
)


def rust_selector_anchor_assignments(
    context: AuthorityContext,
    parent: Mapping[str, str],
    children: Sequence[tuple[str, str]],
) -> tuple[tuple[str, ...], ...]:
    """Bind direct evidence metadata to grammar children without making children.

    Safe and unsafe surfaces join by the exact closed namespace/member pair.
    Trait and D10 rows join to the one aggregate selector clause that declares
    the selected implementation set.  Every anchored row must resolve once;
    helper clauses without a direct G0 evidence identity remain explicitly
    unanchored.
    """
    parsed_children: list[tuple[str, str] | None] = []
    aggregate_children: list[int] = []
    for index, (child_kind, child_value) in enumerate(children):
        match = SURFACE_SELECTOR_CHILD_RE.match(child_value)
        parsed_children.append(
            (match.group("namespace"), match.group("member")) if match else None
        )
        if child_kind == "SELECTOR_CLAUSE" and match is None:
            aggregate_children.append(index)

    assigned: list[list[str]] = [[] for _ in children]
    anchored = [
        row
        for row in context.evidence_by_cluster[parent["cluster_id"]]
        if row["evidence_kind"] not in SELECTOR_KINDS
    ]
    for evidence in anchored:
        kind = evidence["evidence_kind"]
        if kind == "STABLE_SAFE_SURFACE":
            source = context.safe_by_key[evidence["evidence_key"]]
            item_path = source["item_path"]
            member_name = source["member_name"]
        elif kind == "STABLE_UNSAFE_EVIDENCE":
            source = context.unsafe_by_key[evidence["evidence_key"]]
            item_path = source["representative_item_path"]
            member_name = source["member_name"]
        elif kind in {"CONCRETE_TRAIT_IMPL", "D10_CONTRACT_ROUTE"}:
            if len(aggregate_children) != 1:
                raise ValueError(
                    "trait/D10 selector requires one exact aggregate grammar child: "
                    f"{parent['evidence_identity']}"
                )
            assigned[aggregate_children[0]].append(evidence["evidence_identity"])
            continue
        else:
            raise ValueError(
                f"unsupported Rust selector anchor kind: {kind} "
                f"for {parent['evidence_identity']}"
            )

        if item_path not in SURFACE_SELECTOR_NAMESPACE_BY_ITEM_PATH:
            raise ValueError(f"unclassified exact selector item path: {item_path}")
        exact_key = (SURFACE_SELECTOR_NAMESPACE_BY_ITEM_PATH[item_path], member_name)
        candidates = [
            index for index, parsed in enumerate(parsed_children) if parsed == exact_key
        ]
        if len(candidates) != 1:
            raise ValueError(
                "surface evidence does not resolve to one exact grammar child: "
                f"{parent['evidence_identity']} {evidence['evidence_identity']} "
                f"key={exact_key!r} candidates={candidates}"
            )
        assigned[candidates[0]].append(evidence["evidence_identity"])

    flattened = [identity for group in assigned for identity in group]
    if len(flattened) != len(set(flattened)) or set(flattened) != {
        row["evidence_identity"] for row in anchored
    }:
        raise ValueError(
            f"Rust selector anchor assignment is not exact: {parent['evidence_identity']}"
        )
    return tuple(tuple(group) for group in assigned)


def selector_children(
    context: AuthorityContext,
    direct: Mapping[str, SubjectAuthority],
) -> tuple[list[dict[str, object]], list[SubjectAuthority]]:
    expansion_rows: list[dict[str, object]] = []
    authorities: list[SubjectAuthority] = []
    for parent in (row for row in context.evidence_rows if row["evidence_kind"] in SELECTOR_KINDS):
        cluster_id = parent["cluster_id"]
        route = context.route_by_cluster[cluster_id]
        anchored = [
            row
            for row in context.evidence_by_cluster[cluster_id]
            if row["evidence_kind"] not in SELECTOR_KINDS
        ]
        children = grammar_children(
            parent["evidence_kind"], parent["selected_source_value"]
        )
        if len(children) != len(set(children)):
            raise ValueError(f"duplicate materialized selector child: {parent['evidence_identity']}")
        anchor_assignments = (
            rust_selector_anchor_assignments(context, parent, children)
            if parent["evidence_kind"] == "CLUSTER_RUST_SURFACES_SELECTOR"
            else tuple(() for _ in children)
        )

        anchored_authorities = [direct[row["evidence_identity"]] for row in anchored]
        anchored_targets = tuple(
            dict.fromkeys(target for authority in anchored_authorities for target in authority.targets)
        )
        anchored_dense_members = tuple(
            dict.fromkeys(member for authority in anchored_authorities for member in authority.members)
        )
        child_ids: list[str] = []
        for ordinal, ((child_kind, child_value), anchor_ids) in enumerate(
            zip(children, anchor_assignments), 1
        ):
            child_identity = sha256_text(
                f"{parent['evidence_identity']}\0{ordinal}\0{child_kind}\0{child_value}"
            )
            child_ids.append(child_identity)
            if anchor_ids:
                source_authorities = [direct[identity] for identity in anchor_ids]
                targets = tuple(
                    dict.fromkeys(
                        target
                        for source_authority in source_authorities
                        for target in source_authority.targets
                    )
                )
                members = tuple(
                    dict.fromkeys(
                        member
                        for source_authority in source_authorities
                        for member in source_authority.members
                    )
                )
                target_authority = (
                    "EXACT_GRAMMAR_CHILD_TO_DIRECT_EVIDENCE_IDENTITY_JOIN"
                )
                member_authority = (
                    "EXACT_UNION_OF_GRAMMAR_CHILD_ANCHORED_DIRECT_MEMBERS"
                    if members
                    else "NONE_ANCHORED_NON_DENSE_TARGETS"
                )
                predecessors_f = {
                    target: tuple(
                        dict.fromkeys(
                            predecessor
                            for source_authority in source_authorities
                            for predecessor in source_authority.predecessor_families.get(
                                target, ()
                            )
                        )
                    )
                    for target in targets
                }
                predecessors_g = {
                    target: tuple(
                        dict.fromkeys(
                            predecessor
                            for source_authority in source_authorities
                            for predecessor in source_authority.predecessor_gates.get(
                                target, ()
                            )
                        )
                    )
                    for target in targets
                }
            elif child_kind == "HELPER_TYPE":
                match = OWNING_HELPER_RE.fullmatch(child_value)
                if not match:
                    raise ValueError(f"helper type grammar mismatch: {child_value}")
                namespace = match.group("namespace")
                targets = (HELPER_TARGETS[namespace],)
                members = ("DENSE-ITER-OWN",) if targets == (FAMILY_ID,) else ()
                target_authority = "EXACT_OWNING_HELPER_NAMESPACE_CLOSED_ENUM"
                member_authority = (
                    "EXACT_OWNING_HELPER_TO_DENSE_OWNING_ITERATION"
                    if members
                    else "NONE_NON_DENSE_HELPER_TARGET"
                )
                predecessors_f = {targets[0]: ()}
                predecessors_g = {targets[0]: ()}
            else:
                if child_kind == "HELPER_CANARY" and child_value.startswith("xlang_buildhasher_"):
                    targets_list = ["F-SPARSE"]
                    primary = route["primary_refinement_owner_or_gate_stage"]
                    if primary.startswith("GATE-"):
                        targets_list.append(primary)
                    targets = tuple(targets_list)
                    members = ()
                    target_authority = "EXACT_HASHER_CANARY_NAME_TO_SPARSE_AND_OPERATION_GATE"
                    member_authority = "NONE_NON_DENSE_HASHER_CANARY"
                elif (
                    parent["evidence_kind"] == "CLUSTER_RUST_SURFACES_SELECTOR"
                    and (surface_match := SURFACE_SELECTOR_CHILD_RE.match(child_value))
                ):
                    targets = csv_ids(route["primary_refinement_owner_or_gate_stage"])
                    members = (
                        direct_operation_members(
                            cluster_id, surface_match.group("member")
                        )
                        if FAMILY_ID in targets
                        else ()
                    )
                    target_authority = "EXACT_UNANCHORED_SURFACE_TO_FROZEN_ROUTE_OWNER"
                    member_authority = (
                        "EXACT_UNANCHORED_SURFACE_MEMBER_CLOSED_ASSIGNMENT"
                        if members
                        else "NONE_NON_DENSE_UNANCHORED_SURFACE"
                    )
                else:
                    targets = anchored_targets or csv_ids(
                        route["primary_refinement_owner_or_gate_stage"]
                    )
                    members = anchored_dense_members if FAMILY_ID in targets else ()
                    if FAMILY_ID in targets and not members:
                        frozen_members = tuple(CLUSTER_MEMBERS[cluster_id])
                        if len(frozen_members) != 1:
                            raise ValueError(
                                "selector-only dense clause requires an explicit single member: "
                                f"{cluster_id} {child_value}"
                            )
                        members = frozen_members
                        member_authority = "EXACT_SELECTOR_ONLY_SINGLE_FROZEN_MEMBER"
                    else:
                        member_authority = (
                            "EXACT_UNION_OF_ANCHORED_DENSE_CHILD_MEMBERS"
                            if members
                            else "NONE_NON_DENSE_SELECTOR_SCOPE"
                        )
                    target_authority = (
                        "EXACT_SELECTOR_DECLARED_SCOPE_ANCHORED_TARGET_UNION"
                        if anchored_targets
                        else "EXACT_SELECTOR_ONLY_FROZEN_ROUTE_OWNER"
                    )
                predecessors_f = {
                    target: csv_ids(route["required_predecessor_family_ids"])
                    if target == route["primary_refinement_owner_or_gate_stage"]
                    else ()
                    for target in targets
                }
                predecessors_g = {
                    target: csv_ids(route["required_predecessor_gate_stage_ids"])
                    if target == route["primary_refinement_owner_or_gate_stage"]
                    else ()
                    for target in targets
                }
            if not targets:
                raise ValueError(f"selector child has no exact target: {child_identity}")
            if FAMILY_ID in targets and not members:
                raise ValueError(f"dense selector child has no exact member: {child_identity}")
            authority = SubjectAuthority(
                subject_kind="SELECTOR_CHILD",
                subject_identity=child_identity,
                parent_evidence_identity=parent["evidence_identity"],
                cluster_id=cluster_id,
                evidence_kind=parent["evidence_kind"],
                targets=tuple(targets),
                members=tuple(members),
                target_authority=target_authority,
                member_authority=member_authority,
                predecessor_families=predecessors_f,
                predecessor_gates=predecessors_g,
            )
            authorities.append(authority)
            expansion_rows.append(
                {
                    "parent_evidence_identity": parent["evidence_identity"],
                    "cluster_id": cluster_id,
                    "selector_kind": parent["evidence_kind"],
                    "parent_value_sha256": parent["selected_source_value_sha256"],
                    "child_ordinal": ordinal,
                    "child_identity": child_identity,
                    "child_kind": child_kind,
                    "child_value": child_value,
                    "child_value_sha256": sha256_text(child_value),
                    "anchored_evidence_identity_ids": ",".join(anchor_ids) or "NONE",
                    "applicable_target_ids": ",".join(targets),
                    "f_dense_member_contract_ids": ",".join(members) or "NONE",
                    "target_authority": target_authority,
                    "member_authority": member_authority,
                    "expansion_grammar": "DENSE-SELECTOR-EXPANSION-v3",
                }
            )
        if not child_ids:
            raise ValueError(f"selector parent has no children: {parent['evidence_identity']}")
    return expansion_rows, authorities


OUTCOME_BINDING = "BIND_FROM_DECLARATIVE_CONTRACT_REGISTRY"
CONTRACT_REGISTRY_JOIN_FIELDS = ("cluster_id", "member_contract_id")
EVIDENCE_OUTCOME_UNIQUE_FIELDS = (
    "subject_kind",
    "subject_identity",
    "target_id",
    "member_contract_id",
    "policy_variant_id",
    "outcome_id",
)


def terminal_for(authority: SubjectAuthority, target: str) -> tuple[str, str]:
    if target != FAMILY_ID:
        return (
            "EXCLUDED_BLOCKS_CLAIM",
            f"{target};CLUSTER:{authority.cluster_id};COMPLETE-SYSTEMS-FLOOR",
        )
    excluded = set(authority.members) & set(EXCLUDED_MEMBERS)
    included = set(authority.members) - set(EXCLUDED_MEMBERS)
    if excluded and included:
        raise ValueError(
            "one exact evidence child mixes refined and excluded members: "
            f"{authority.subject_identity}"
        )
    if excluded:
        return (
            "EXCLUDED_BLOCKS_CLAIM",
            f"{FAMILY_ID};CLUSTER:{authority.cluster_id};COMPLETE-SYSTEMS-FLOOR",
        )
    if not included:
        raise ValueError(f"dense target has no legal terminal member: {authority.subject_identity}")
    return "REFINED_IN_LOCK", "NONE"


def target_and_member_rows(
    authorities: Sequence[SubjectAuthority],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    target_rows: list[dict[str, object]] = []
    member_rows: list[dict[str, object]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for authority in authorities:
        for ordinal, target in enumerate(authority.targets, 1):
            pair = (authority.subject_identity, target)
            if pair in seen_pairs:
                raise ValueError(f"duplicate evidence/target pair: {pair}")
            seen_pairs.add(pair)
            terminal, blocked = terminal_for(authority, target)
            members = authority.members if target == FAMILY_ID else ()
            target_rows.append(
                {
                    "subject_kind": authority.subject_kind,
                    "subject_identity": authority.subject_identity,
                    "parent_evidence_identity": authority.parent_evidence_identity,
                    "cluster_id": authority.cluster_id,
                    "evidence_kind": authority.evidence_kind,
                    "target_id": target,
                    "target_ordinal": ordinal,
                    "terminal_disposition": terminal,
                    "member_contract_ids": ",".join(members) or "NONE",
                    "required_predecessor_family_ids": ",".join(
                        authority.predecessor_families.get(target, ())
                    )
                    or "NONE",
                    "required_predecessor_gate_stage_ids": ",".join(
                        authority.predecessor_gates.get(target, ())
                    )
                    or "NONE",
                    "blocked_claims": blocked,
                    "target_authority": authority.target_authority,
                    "member_authority": authority.member_authority,
                }
            )
            if terminal == "REFINED_IN_LOCK":
                for member in members:
                    member_rows.append(
                        {
                            "subject_kind": authority.subject_kind,
                            "subject_identity": authority.subject_identity,
                            "parent_evidence_identity": authority.parent_evidence_identity,
                            "cluster_id": authority.cluster_id,
                            "target_id": target,
                            "member_contract_id": member,
                            "outcome_id": OUTCOME_BINDING,
                            "unit_status": "MEMBER_EXACT_OUTCOME_BINDING_REQUIRED",
                            "mapping_authority": authority.member_authority,
                            "outcome_binding_authority": "DECLARATIVE_CONTRACT_REGISTRY_REQUIRED_BEFORE_LOCK_CLOSE",
                        }
                    )
    return target_rows, member_rows


# Exact member groups used by both capability and payload-overlay authorities.
# Group membership is expressed only through frozen cluster/member identities.
FIXED_MEMBERS = members_of_clusters("ARR-VIEW-01", "ARR-EACH-01", "ARR-MAP-01")
VIEW_MEMBERS = members_of_clusters(
    "VIEW-META-01",
    "VIEW-GET-01",
    "VIEW-GET-02",
    "VIEW-END-01",
    "VIEW-ARRAY-01",
    "VIEW-END-CHUNK-01",
    "VIEW-END-SPLIT-01",
    "VIEW-SPLIT-01",
    "VIEW-SPLIT-02",
    "VIEW-CONSUME-01",
    "VIEW-DISJOINT-01",
    "VIEW-ARRAY-CHUNKS-01",
    "VIEW-SORT-01",
    "VIEW-SORT-02",
    "VIEW-SELECT-01",
    "VIEW-REORDER-01",
    "VIEW-SWAP-01",
    "VIEW-COPY-01",
    "VIEW-CLONE-01",
    "VIEW-FILL-01",
    "VIEW-ALLOC-01",
    "VIEW-CONCAT-01",
)
SEQUENCE_MEMBERS = members_of_clusters(
    "SEQ-META-01",
    "SEQ-RESERVE-01",
    "SEQ-TRY-RESERVE-01",
    "SEQ-SHRINK-01",
    "SEQ-VIEW-01",
    "SEQ-PUSH-01",
    "SEQ-INSERT-01",
    "SEQ-POP-01",
    "SEQ-REMOVE-01",
    "SEQ-APPEND-01",
    "SEQ-EXTEND-COPY-01",
    "SEQ-RESIZE-01",
    "SEQ-TRUNCATE-01",
    "SEQ-RETAIN-01",
    "SEQ-DEDUP-01",
    "SEQ-DRAIN-01",
    "SEQ-EXTRACT-01",
    "SEQ-SPLICE-01",
    "SEQ-SPLIT-01",
    "SEQ-CONVERT-01",
)
TRAIT_MEMBERS = members_of_clusters(
    "TRAIT-INTOITER-01",
    "TRAIT-EXTEND-01",
    "TRAIT-COLLECT-01",
    "TRAIT-INDEX-01",
    "TRAIT-DEREF-01",
    "TRAIT-BORROW-01",
    "TRAIT-CONVERT-01",
    "TRAIT-CLONE-01",
    "TRAIT-DEFAULT-01",
    "TRAIT-CMP-01",
    "TRAIT-DROP-01",
)
STORAGE_MEMBERS = (FIXED_MEMBERS | VIEW_MEMBERS | SEQUENCE_MEMBERS | TRAIT_MEMBERS) & INCLUDED_MEMBERS

HOLE_MEMBERS = members_of_clusters(
    "ARR-MAP-01",
    "VIEW-SORT-01",
    "VIEW-SORT-02",
    "VIEW-SELECT-01",
    "VIEW-REORDER-01",
    "VIEW-SWAP-01",
    "VIEW-COPY-01",
    "VIEW-CLONE-01",
    "VIEW-FILL-01",
    "INIT-WRITE-01",
    "SEQ-PUSH-01",
    "SEQ-INSERT-01",
    "SEQ-POP-01",
    "SEQ-REMOVE-01",
    "SEQ-APPEND-01",
    "SEQ-EXTEND-COPY-01",
    "SEQ-RESIZE-01",
    "SEQ-TRUNCATE-01",
    "SEQ-RETAIN-01",
    "SEQ-DEDUP-01",
    "SEQ-EXTRACT-01",
    "SEQ-SPLICE-01",
    "TRAIT-EXTEND-01",
    "TRAIT-COLLECT-01",
    "TRAIT-CLONE-01",
    "TRAIT-DROP-01",
) & INCLUDED_MEMBERS

INIT_MEMBERS = members_of_clusters(
    "ARR-MAP-01",
    "INIT-WRITE-01",
    "SEQ-META-01",
    "SEQ-PUSH-01",
    "SEQ-INSERT-01",
    "SEQ-APPEND-01",
    "SEQ-EXTEND-COPY-01",
    "SEQ-RESIZE-01",
    "SEQ-SPLICE-01",
    "TRAIT-EXTEND-01",
    "TRAIT-COLLECT-01",
    "TRAIT-DEFAULT-01",
    "MEM-TAKE-01",
) & INCLUDED_MEMBERS
MOVEOUT_MEMBERS = members_of_clusters(
    "SEQ-POP-01",
    "SEQ-REMOVE-01",
    "SEQ-EXTRACT-01",
    "SEQ-SPLICE-01",
    "SEQ-SPLIT-01",
    "SEQ-CONVERT-01",
    "TRAIT-INTOITER-01",
    "TRAIT-CONVERT-01",
    "MEM-REPLACE-01",
    "MEM-TAKE-01",
) & INCLUDED_MEMBERS
REPLACE_MEMBERS = members_of_clusters(
    "VIEW-CLONE-01",
    "VIEW-FILL-01",
    "SEQ-RESIZE-01",
    "TRAIT-CLONE-01",
    "MEM-REPLACE-01",
    "MEM-TAKE-01",
) & INCLUDED_MEMBERS
SWAP_MEMBERS = members_of_clusters("VIEW-REORDER-01", "VIEW-SWAP-01") & INCLUDED_MEMBERS
RELOCATE_MEMBERS = members_of_clusters(
    "VIEW-SORT-01",
    "VIEW-SORT-02",
    "VIEW-SELECT-01",
    "VIEW-REORDER-01",
    "VIEW-SWAP-01",
    "VIEW-COPY-01",
    "SEQ-RESERVE-01",
    "SEQ-TRY-RESERVE-01",
    "SEQ-SHRINK-01",
    "SEQ-PUSH-01",
    "SEQ-INSERT-01",
    "SEQ-REMOVE-01",
    "SEQ-APPEND-01",
    "SEQ-EXTEND-COPY-01",
    "SEQ-RESIZE-01",
    "SEQ-RETAIN-01",
    "SEQ-DEDUP-01",
    "SEQ-EXTRACT-01",
    "SEQ-SPLICE-01",
    "SEQ-SPLIT-01",
) & INCLUDED_MEMBERS
CLONE_MEMBERS = members_of_clusters(
    "VIEW-CLONE-01",
    "VIEW-FILL-01",
    "VIEW-ALLOC-01",
    "VIEW-CONCAT-01",
    "INIT-WRITE-01",
    "SEQ-EXTEND-COPY-01",
    "SEQ-RESIZE-01",
    "TRAIT-CLONE-01",
) & INCLUDED_MEMBERS
DROP_MEMBERS = members_of_clusters(
    "ARR-MAP-01",
    "VIEW-FILL-01",
    "SEQ-POP-01",
    "SEQ-REMOVE-01",
    "SEQ-RESIZE-01",
    "SEQ-TRUNCATE-01",
    "SEQ-RETAIN-01",
    "SEQ-DEDUP-01",
    "SEQ-EXTRACT-01",
    "SEQ-SPLICE-01",
    "TRAIT-INTOITER-01",
    "TRAIT-DROP-01",
    "MEM-TAKE-01",
) & INCLUDED_MEMBERS
PROTOCOL_MEMBERS = members_of_clusters(
    "ARR-MAP-01",
    "VIEW-SORT-01",
    "VIEW-SORT-02",
    "VIEW-SELECT-01",
    "VIEW-FILL-01",
    "SEQ-RESERVE-01",
    "SEQ-TRY-RESERVE-01",
    "SEQ-PUSH-01",
    "SEQ-INSERT-01",
    "SEQ-APPEND-01",
    "SEQ-EXTEND-COPY-01",
    "SEQ-RESIZE-01",
    "SEQ-RETAIN-01",
    "SEQ-DEDUP-01",
    "SEQ-EXTRACT-01",
    "SEQ-SPLICE-01",
    "TRAIT-INTOITER-01",
    "TRAIT-EXTEND-01",
    "TRAIT-COLLECT-01",
    "TRAIT-CLONE-01",
) & INCLUDED_MEMBERS
BORROW_MEMBERS = members_of_clusters(
    "ARR-VIEW-01",
    "ARR-EACH-01",
    "VIEW-GET-01",
    "VIEW-GET-02",
    "VIEW-END-01",
    "VIEW-ARRAY-01",
    "VIEW-END-CHUNK-01",
    "VIEW-END-SPLIT-01",
    "VIEW-SPLIT-01",
    "VIEW-SPLIT-02",
    "VIEW-CONSUME-01",
    "VIEW-DISJOINT-01",
    "VIEW-ARRAY-CHUNKS-01",
    "SEQ-VIEW-01",
    "SEQ-PUSH-01",
    "SEQ-INSERT-01",
    "TRAIT-INTOITER-01",
    "TRAIT-INDEX-01",
    "TRAIT-DEREF-01",
    "TRAIT-BORROW-01",
) & INCLUDED_MEMBERS
RESULT_BORROW_MEMBERS = members_of_clusters(
    "VIEW-GET-01",
    "VIEW-GET-02",
    "VIEW-END-01",
    "VIEW-ARRAY-01",
    "VIEW-END-CHUNK-01",
    "VIEW-END-SPLIT-01",
    "VIEW-SPLIT-01",
    "VIEW-SPLIT-02",
    "VIEW-CONSUME-01",
    "VIEW-DISJOINT-01",
    "VIEW-ARRAY-CHUNKS-01",
    "SEQ-VIEW-01",
    "SEQ-PUSH-01",
    "SEQ-INSERT-01",
    "TRAIT-INTOITER-01",
    "TRAIT-INDEX-01",
    "TRAIT-DEREF-01",
    "TRAIT-BORROW-01",
) & INCLUDED_MEMBERS
DISJOINT_MEMBERS = members_of_clusters(
    "ARR-EACH-01",
    "VIEW-SPLIT-01",
    "VIEW-SPLIT-02",
    "VIEW-DISJOINT-01",
    "VIEW-SWAP-01",
) & INCLUDED_MEMBERS
CALLBACK_MEMBERS = members_of_clusters(
    "ARR-MAP-01",
    "VIEW-SORT-01",
    "VIEW-SORT-02",
    "VIEW-SELECT-01",
    "VIEW-FILL-01",
    "SEQ-POP-01",
    "SEQ-RESIZE-01",
    "SEQ-RETAIN-01",
    "SEQ-DEDUP-01",
    "SEQ-EXTRACT-01",
    "SEQ-SPLICE-01",
    "TRAIT-CMP-01",
    "TRAIT-CLONE-01",
) & INCLUDED_MEMBERS
CAPACITY_MEMBERS = members_of_clusters(
    "SEQ-META-01",
    "SEQ-RESERVE-01",
    "SEQ-TRY-RESERVE-01",
    "SEQ-SHRINK-01",
    "SEQ-PUSH-01",
    "SEQ-INSERT-01",
    "SEQ-APPEND-01",
    "SEQ-EXTEND-COPY-01",
    "SEQ-RESIZE-01",
    "SEQ-SPLICE-01",
    "SEQ-SPLIT-01",
    "TRAIT-EXTEND-01",
    "TRAIT-COLLECT-01",
) & INCLUDED_MEMBERS
ALLOC_MEMBERS = members_of_clusters(
    "VIEW-ALLOC-01",
    "VIEW-CONCAT-01",
    "SEQ-META-01",
    "SEQ-RESERVE-01",
    "SEQ-TRY-RESERVE-01",
    "SEQ-SHRINK-01",
    "SEQ-PUSH-01",
    "SEQ-INSERT-01",
    "SEQ-APPEND-01",
    "SEQ-EXTEND-COPY-01",
    "SEQ-RESIZE-01",
    "SEQ-SPLICE-01",
    "SEQ-SPLIT-01",
    "TRAIT-EXTEND-01",
    "TRAIT-COLLECT-01",
    "TRAIT-CLONE-01",
) & INCLUDED_MEMBERS


def capability_groups() -> dict[str, set[str]]:
    groups: dict[str, set[str]] = {
        "ST-AOS": (FIXED_MEMBERS | STORAGE_MEMBERS) & INCLUDED_MEMBERS,
        "ST-DENSE": (VIEW_MEMBERS | SEQUENCE_MEMBERS | TRAIT_MEMBERS) & INCLUDED_MEMBERS,
        "ST-HOLE": HOLE_MEMBERS,
        "OW-INIT": INIT_MEMBERS,
        "OW-MOVEOUT": MOVEOUT_MEMBERS,
        "OW-REPLACE": REPLACE_MEMBERS,
        "OW-SWAP": SWAP_MEMBERS,
        "OW-RELOCATE": RELOCATE_MEMBERS,
        "OW-CLONE": CLONE_MEMBERS,
        "OW-DROP": DROP_MEMBERS,
        "EX-NORMAL": set(INCLUDED_MEMBERS),
        "EX-ABANDON": PROTOCOL_MEMBERS,
        "EX-ABORT": set(INCLUDED_MEMBERS),
        "BR-PROV": BORROW_MEMBERS,
        "BR-REBORROW": BORROW_MEMBERS,
        "BR-RESULT": RESULT_BORROW_MEMBERS,
        "BR-DISJOINT": DISJOINT_MEMBERS,
        "BR-INVALIDATE": BORROW_MEMBERS | RELOCATE_MEMBERS | DROP_MEMBERS,
        "BR-CURSOR": members_of_clusters("TRAIT-INTOITER-01") & INCLUDED_MEMBERS,
        "FL-CAPACITY": CAPACITY_MEMBERS,
        "FL-ALLOC": ALLOC_MEMBERS,
        "FL-ATOMIC": ALLOC_MEMBERS | members_of_clusters("MEM-REPLACE-01"),
        "FL-CALLBACK": CALLBACK_MEMBERS,
        "AB-SEAL": set(INCLUDED_MEMBERS),
        "AB-BEHAVIOR": CALLBACK_MEMBERS | CLONE_MEMBERS,
        "AB-STATEFUL": CALLBACK_MEMBERS,
        "AB-GENERIC": set(INCLUDED_MEMBERS),
        "IT-SHARED": {"DENSE-ITER-SHARED"},
        "IT-UNIQ": {"DENSE-ITER-UNIQ"},
        "IT-OWN": {"DENSE-ITER-OWN"},
        "FT-STATE": STORAGE_MEMBERS | HOLE_MEMBERS,
    }
    for capability, members in groups.items():
        if not members <= ALL_MEMBERS:
            raise ValueError(f"capability group escapes member registry: {capability}")
    return groups


def member_capabilities(
    member: str, capability_order: Sequence[str], groups: Mapping[str, set[str]]
) -> tuple[str, ...]:
    if member not in ALL_MEMBERS:
        raise ValueError(f"unknown member for capability binding: {member}")
    return tuple(capability for capability in capability_order if member in groups.get(capability, set()))


OVERLAY_EXACT_OVERRIDES: Mapping[tuple[str, str], tuple[str, ...]] = {
    ("SEQ-META-01", "BORROW_BEARING_STORED_TRANSITION"): ("DENSE-META",),
    ("VIEW-SORT-01", "CACHED_KEY_BORROW_STATE"): ("DENSE-SORT-STABLE-CACHED-KEY",),
    ("VIEW-SORT-01", "KEY_RESULT_BORROW_STATE"): ("DENSE-SORT-STABLE",),
    ("VIEW-FILL-01", "CALLABLE_ENV_BORROW_STATE"): ("DENSE-FILL-WITH",),
    ("VIEW-FILL-01", "CLONE_FROM_BORROW_EFFECT"): ("DENSE-FILL-CLONE",),
    ("VIEW-FILL-01", "PRODUCER_RESULT_BORROW_STATE"): ("DENSE-FILL-WITH",),
    ("VIEW-COPY-01", "BORROW_BEARING_RANGE_DESCRIPTOR"): ("DENSE-COPY-WITHIN",),
    ("INIT-WRITE-01", "CLONE_RESULT_BORROW_STATE"): ("DENSE-INIT-CLONE",),
    ("SEQ-POP-01", "CALLABLE_ENV_BORROW_STATE"): ("DENSE-POP-IF",),
    ("SEQ-EXTEND-COPY-01", "BORROW_BEARING_RANGE_DESCRIPTOR"): ("DENSE-EXTEND-WITHIN",),
    ("SEQ-EXTEND-COPY-01", "CLONE_RESULT_BORROW_STATE"): ("DENSE-EXTEND-CLONE",),
    ("SEQ-RESIZE-01", "CALLABLE_ENV_BORROW_STATE"): ("DENSE-RESIZE-WITH",),
    ("SEQ-RESIZE-01", "CLONE_RESULT_BORROW_STATE"): ("DENSE-RESIZE-CLONE",),
    ("SEQ-RESIZE-01", "PRODUCER_RESULT_BORROW_STATE"): ("DENSE-RESIZE-WITH",),
    ("SEQ-DEDUP-01", "CALLABLE_ENV_BORROW_STATE"): ("DENSE-DEDUP-BY", "DENSE-DEDUP-BY-KEY"),
    ("SEQ-DEDUP-01", "KEY_RESULT_BORROW_STATE"): ("DENSE-DEDUP-BY-KEY",),
    ("TRAIT-INTOITER-01", "OWNING_ENTRANCE_BORROW_BEARING_RESULT"): ("DENSE-ITER-OWN",),
    ("TRAIT-INTOITER-01", "OWNING_HASH_BUILDER_DROP"): (),
    ("TRAIT-INDEX-01", "GENERATED_HASHER_BORROW_STATE"): (),
    ("TRAIT-INDEX-01", "STORED_HASH_BUILDER_BORROW_STATE"): (),
    ("TRAIT-CLONE-01", "CLONE_CACHED_BORROW_BEARING_STATE"): (),
    ("TRAIT-CLONE-01", "CLONE_FRESH_OWNED_PAYLOAD"): ("DENSE-FRESH-CLONE",),
    ("TRAIT-CLONE-01", "CLONE_FROM_OWNED_PAYLOAD"): ("DENSE-CLONE-FROM",),
    ("TRAIT-CLONE-01", "CLONE_SHARED_HANDLE_PAYLOAD"): (),
    ("TRAIT-CMP-01", "CALLER_HASHER_BORROW_STATE"): ("DENSE-HASH-TRAVERSAL",),
    ("TRAIT-CMP-01", "GENERATED_HASHER_BORROW_STATE"): (),
    ("TRAIT-CMP-01", "STORED_HASH_BUILDER_BORROW_STATE"): (),
    ("BOX-INIT-01", "WRITE_SEAL_BORROW_BEARING_RESULT"): (),
}

OVERLAY_ALL_MEMBER_BRANCHES = {
    "BORROW_BEARING_STORED_TRANSITION",
    "BORROW_BEARING_OWNED_RESULT",
    "CALLABLE_ENV_BORROW_STATE",
    "INPUT_ARRAY_BORROW_PAYLOAD",
    "OUTPUT_ARRAY_BORROW_PAYLOAD",
    "CLONE_FROM_BORROW_EFFECT",
    "CLONE_RESULT_BORROW_STATE",
    "KEY_RESULT_BORROW_STATE",
    "PRODUCER_RESULT_BORROW_STATE",
    "BORROW_BEARING_RANGE_DESCRIPTOR",
    "FROM_CLONED_BORROW_PAYLOAD",
    "FROM_OWNED_BORROW_PAYLOAD",
    "TRY_FROM_BORROW_PAYLOAD_ERROR",
    "TRY_FROM_OWNED_BORROW_PAYLOAD_OK",
    "DEFAULT_LIVE_BORROW_PAYLOAD",
    "INSTALLED_DEFAULT_RESULT_BORROW_STATE",
}


def overlay_members(cluster_id: str, branch_id: str) -> tuple[str, ...]:
    key = (cluster_id, branch_id)
    if key in OVERLAY_EXACT_OVERRIDES:
        members = OVERLAY_EXACT_OVERRIDES[key]
    elif branch_id in OVERLAY_ALL_MEMBER_BRANCHES:
        members = tuple(
            member for member in CLUSTER_MEMBERS[cluster_id] if member not in EXCLUDED_MEMBERS
        )
    else:
        raise ValueError(f"unbound exact overlay branch: {key}")
    if not set(members) <= set(CLUSTER_MEMBERS[cluster_id]):
        raise ValueError(f"overlay member escapes cluster: {key}")
    return members


def overlay_authority_rows(context: AuthorityContext) -> list[dict[str, object]]:
    capability_order = tuple(row["capability_id"] for row in context.capability_rows)
    groups = capability_groups()
    result: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for source in context.overlay_rows:
        key = (source["contract_id"], source["branch_id"])
        if key in seen:
            raise ValueError(f"duplicate frozen overlay branch: {key}")
        seen.add(key)
        members = overlay_members(*key)
        conditional = csv_ids(source["conditional_capability_ids"])
        if not set(conditional) <= set(capability_order):
            raise ValueError(f"overlay uses unknown capability: {key}")
        if not members:
            result.append(
                {
                    "cluster_id": key[0],
                    "overlay_branch_id": key[1],
                    "role": source["role"],
                    "member_contract_id": "NONE",
                    "outcome_id": "NONE_NON_APPLICABLE_TO_F_DENSE_UNIT",
                    "binding_state": "NO_F_DENSE_MEMBER_TARGET",
                    "base_capability_ids": "NONE",
                    "conditional_capability_ids": ",".join(conditional),
                    "effective_capability_ids": "NONE",
                    "source_disposition": source["disposition"],
                    "reopening_trigger_sha256": sha256_text(source["reopening_trigger"]),
                    "binding_authority": "EXACT_CROSS_TOPOLOGY_BRANCH_EXCLUSION",
                }
            )
            continue
        for member in members:
            base = member_capabilities(member, capability_order, groups)
            effective = ordered_union(capability_order, base, conditional)
            result.append(
                {
                    "cluster_id": key[0],
                    "overlay_branch_id": key[1],
                    "role": source["role"],
                    "member_contract_id": member,
                    "outcome_id": OUTCOME_BINDING,
                    "binding_state": "EXACT_MEMBER_OUTCOME_BINDING_REQUIRED",
                    "base_capability_ids": ",".join(base) or "NONE",
                    "conditional_capability_ids": ",".join(conditional),
                    "effective_capability_ids": ",".join(effective),
                    "source_disposition": source["disposition"],
                    "reopening_trigger_sha256": sha256_text(source["reopening_trigger"]),
                    "binding_authority": "EXACT_CLUSTER_BRANCH_TO_MEMBER_ASSIGNMENT",
                }
            )
    if seen != {(row["contract_id"], row["branch_id"]) for row in context.overlay_rows}:
        raise ValueError("overlay authority does not equal the frozen branch universe")
    return result


ROLE_MEMBER_BINDINGS: Mapping[str, tuple[str, ...]] = {
    "Fixed AoS record buffer": (
        "DENSE-FIXED-VIEW",
        "DENSE-FIXED-EACH",
        "DENSE-FIXED-MAP",
    ),
    "Unknown-length append": (
        "DENSE-PUSH",
        "DENSE-EXTEND-ITER",
        "DENSE-COLLECT",
    ),
    "Append affine value": ("DENSE-PUSH", "DENSE-APPEND-MOVE"),
    "Grow/shrink contiguous sequence": (
        "DENSE-RESERVE",
        "DENSE-RESERVE-EXACT",
        "DENSE-TRY-RESERVE",
        "DENSE-TRY-RESERVE-EXACT",
        "DENSE-SHRINK-TO",
        "DENSE-SHRINK-TO-FIT",
    ),
    "Pop affine value": ("DENSE-POP", "DENSE-POP-IF"),
    "Ordered insert/remove and unordered `swap_remove`": (
        "DENSE-INSERT",
        "DENSE-INSERT-UNIQ",
        "DENSE-REMOVE",
        "DENSE-SWAP-REMOVE",
    ),
    "Swap two dynamic elements": ("DENSE-SWAP", "DENSE-SWAP-WITH-VIEW"),
    "Clear/truncate": ("DENSE-CLEAR", "DENSE-TRUNCATE"),
    "Deep clone and bulk move-append": (
        "DENSE-FRESH-CLONE",
        "DENSE-CLONE-FROM",
        "DENSE-APPEND-MOVE",
        "DENSE-EXTEND-CLONE",
    ),
    "Stable retain and eager drain/splice": (
        "DENSE-RETAIN",
        "DENSE-RETAIN-MUT",
        "DENSE-EAGER-EXTRACT",
        "DENSE-EAGER-SPLICE",
    ),
    "Lazy drain cursor": ("DENSE-LAZY-DRAIN-EVIDENCE",),
    "Generic unstable and stable sort": (
        "DENSE-SORT-STABLE",
        "DENSE-SORT-STABLE-CACHED-KEY",
        "DENSE-SORT-UNSTABLE",
    ),
    "Stack adapter": ("DENSE-PUSH", "DENSE-POP"),
    "Inline-to-heap small sequence": (
        "DENSE-NEW",
        "DENSE-WITH-CAPACITY",
        "DENSE-META",
        "DENSE-PUSH",
        "DENSE-POP",
        "DENSE-INSERT",
        "DENSE-REMOVE",
        "DENSE-OWNER-VIEW",
        "DENSE-ITER-SHARED",
        "DENSE-DROP",
    ),
    "Borrowed, uniq, and owning iteration": (
        "DENSE-ITER-SHARED",
        "DENSE-ITER-UNIQ",
        "DENSE-ITER-OWN",
    ),
    "W-SMALL": (
        "DENSE-NEW",
        "DENSE-WITH-CAPACITY",
        "DENSE-META",
        "DENSE-PUSH",
        "DENSE-POP",
        "DENSE-INSERT",
        "DENSE-REMOVE",
        "DENSE-OWNER-VIEW",
        "DENSE-ITER-SHARED",
        "DENSE-DROP",
    ),
    "W-GAP": (
        "DENSE-NEW",
        "DENSE-WITH-CAPACITY",
        "DENSE-INSERT",
        "DENSE-REMOVE",
        "DENSE-EAGER-SPLICE",
        "DENSE-OWNER-VIEW",
        "DENSE-DROP",
    ),
    "H-FLATSET": (
        "DENSE-NEW",
        "DENSE-META",
        "DENSE-RESERVE",
        "DENSE-TRY-RESERVE",
        "DENSE-VIEW-GET-SHARED",
        "DENSE-INSERT",
        "DENSE-REMOVE",
        "DENSE-SORT-STABLE",
        "DENSE-ITER-SHARED",
        "DENSE-DROP",
    ),
    "O-LAZY-DRAIN": ("DENSE-LAZY-DRAIN-EVIDENCE",),
}


def applicable_requirement_rows(context: AuthorityContext) -> list[dict[str, str]]:
    result = []
    for row in context.requirement_rows:
        is_baseline = row["role"] == "B"
        is_owner = row["closure_owner_or_gate_stage"] == FAMILY_ID
        is_pipe_rebind = (
            row["linked_registry_ids"] == "W-PIPE"
            and FAMILY_ID in csv_ids(row["implicated_family_ids"])
        )
        if is_baseline or is_owner or is_pipe_rebind:
            result.append(row)
    return result


def role_authority_rows(context: AuthorityContext) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for source in applicable_requirement_rows(context):
        role = source["role"]
        is_baseline = role == "B"
        is_owner = source["closure_owner_or_gate_stage"] == FAMILY_ID
        is_pipe = source["linked_registry_ids"] == "W-PIPE" and not is_owner
        if is_baseline:
            owner_disposition = "PROTECTED_CONTROL"
            rebind_disposition = "PROTECTED_CONTROL"
            controls = tuple(
                identity
                for identity in csv_ids(source["linked_registry_ids"])
                if identity in {"B-FIX", "B-P2"}
            )
            if len(controls) != 1:
                raise ValueError(f"baseline role lacks one exact control: {source['obligation_id']}")
            units = [("CONTROL", "NONE", "NONE", controls[0])]
        elif is_pipe:
            owner_disposition = "NOT_APPLICABLE_IMPLICATED_REBIND"
            rebind_disposition = "EXCLUDED_BLOCKS_FAMILY_AND_FLOOR"
            units = [("CLAIM_BLOCKING_EXCLUSION", "NONE", "NONE", "W-PIPE")]
        elif role == "O":
            owner_disposition = "OPTIONAL_NOT_PROMOTED"
            rebind_disposition = "NOT_APPLICABLE_REOPENING_ONLY"
            members = ROLE_MEMBER_BINDINGS[source["workload_or_operation"]]
            units = [("EXCLUDED_MEMBER", member, OUTCOME_BINDING, "NONE") for member in members]
        else:
            owner_disposition = "REQUIRED_IN_LOCK"
            rebind_disposition = "NOT_APPLICABLE_REOPENING_ONLY"
            if source["workload_or_operation"] not in ROLE_MEMBER_BINDINGS:
                raise ValueError(
                    f"required role lacks exact member bindings: {source['workload_or_operation']}"
                )
            members = ROLE_MEMBER_BINDINGS[source["workload_or_operation"]]
            units = [("MEMBER", member, OUTCOME_BINDING, "NONE") for member in members]
        for binding_kind, member, outcome, control in units:
            if member != "NONE" and member not in ALL_MEMBERS:
                raise ValueError(f"role binds unknown member: {member}")
            result.append(
                {
                    "obligation_id": source["obligation_id"],
                    "record_kind": source["record_kind"],
                    "role": role,
                    "workload_or_operation": source["workload_or_operation"],
                    "closure_owner_or_gate_stage": source["closure_owner_or_gate_stage"],
                    "owner_lock_disposition": owner_disposition,
                    "implicated_rebind_disposition": rebind_disposition,
                    "binding_kind": binding_kind,
                    "member_contract_id": member,
                    "outcome_id": outcome,
                    "control_or_witness_id": control,
                    "primary_canary_id": source["primary_canary_id"],
                    "crosscut_canary_ids": source["required_crosscut_canary_ids"],
                    "canary_source_sha256": source["canary_source_sha256"],
                    "binding_authority": "EXACT_G0_ROLE_TO_DENSE_MEMBER_OR_CONTROL_ASSIGNMENT",
                }
            )
    return result


def capability_authority_rows(
    context: AuthorityContext,
    overlay_rows: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    capability_order = tuple(row["capability_id"] for row in context.capability_rows)
    groups = capability_groups()
    conditional_by_capability: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in overlay_rows:
        if row["member_contract_id"] == "NONE":
            continue
        for capability in csv_ids(str(row["conditional_capability_ids"])):
            conditional_by_capability[capability].append(row)
    protected = {
        "ST-FULL": "B-FIX",
        "NT-FIXED": "B-FIX",
        "NT-P2": "B-P2",
    }
    result: list[dict[str, object]] = []
    for source in context.capability_rows:
        capability = source["capability_id"]
        base_members = tuple(member for member in ALL_MEMBERS if member in groups.get(capability, set()))
        deferred = conditional_by_capability.get(capability, [])
        if capability in protected:
            applicability = "PROTECTED"
            bindings = [("CONTROL", "NONE", "NONE", "NONE", protected[capability])]
        elif base_members:
            applicability = "REQUIRED"
            bindings = [
                ("MEMBER", member, OUTCOME_BINDING, "NONE", "NONE")
                for member in sorted(base_members)
            ]
            bindings.extend(
                (
                    "DEFERRED_OVERLAY",
                    str(row["member_contract_id"]),
                    OUTCOME_BINDING,
                    str(row["overlay_branch_id"]),
                    "NONE",
                )
                for row in deferred
            )
        elif deferred:
            applicability = "DEFERRED-BLOCKS-CLAIM"
            bindings = [
                (
                    "DEFERRED_OVERLAY",
                    str(row["member_contract_id"]),
                    OUTCOME_BINDING,
                    str(row["overlay_branch_id"]),
                    "NONE",
                )
                for row in deferred
            ]
        else:
            applicability = "NOT-IMPLICATED"
            bindings = [("NONE", "NONE", "NONE", "NONE", "NONE")]
        for binding_kind, member, outcome, branch, control in bindings:
            result.append(
                {
                    "capability_id": capability,
                    "dimension": source["dimension"],
                    "applicability": applicability,
                    "binding_kind": binding_kind,
                    "member_contract_id": member,
                    "outcome_id": outcome,
                    "overlay_branch_id": branch,
                    "control_id": control,
                    "binding_authority": "EXACT_CAPABILITY_TO_MEMBER_CONTROL_OR_OVERLAY_ASSIGNMENT",
                }
            )
    if set(capability_order) != {row["capability_id"] for row in context.capability_rows}:
        raise ValueError("capability registry contains duplicates")
    return result


def build_authorities(
    snapshot: FrozenG0Snapshot | None = None,
) -> tuple[AuthorityContext, dict[str, list[dict[str, object]]]]:
    """Build every authority from the frozen G0 snapshot.

    No current worktree G0 file and no heuristic member/outcome ledger is an
    input.  Outcome columns remain explicitly unresolved for later expansion
    from the separately supplied declarative contract registry.
    """
    context = load_context(snapshot)
    direct: dict[str, SubjectAuthority] = {}
    for evidence in context.evidence_rows:
        if evidence["evidence_kind"] not in SELECTOR_KINDS:
            authority = direct_subject(context, evidence)
            direct[authority.subject_identity] = authority
    expansion, selector_authorities = selector_children(context, direct)
    target_rows, member_rows = target_and_member_rows(
        [*direct.values(), *selector_authorities]
    )
    overlay_rows = overlay_authority_rows(context)
    outputs: dict[str, list[dict[str, object]]] = {
        "DENSE-FROZEN-G0-INPUT-AUTHORITY.tsv": context.snapshot.input_authority(),
        "DENSE-SELECTOR-EXPANSION-AUTHORITY.tsv": expansion,
        "DENSE-EVIDENCE-TARGET-AUTHORITY.tsv": target_rows,
        "DENSE-EVIDENCE-MEMBER-AUTHORITY.tsv": member_rows,
        "DENSE-OVERLAY-BRANCH-AUTHORITY.tsv": overlay_rows,
        "DENSE-ROLE-UNIT-AUTHORITY.tsv": role_authority_rows(context),
        "DENSE-CAPABILITY-UNIT-AUTHORITY.tsv": capability_authority_rows(
            context, overlay_rows
        ),
    }
    validate_authorities(context, outputs)
    return context, outputs


def validate_selector_authority(
    context: AuthorityContext,
    rows: Sequence[Mapping[str, object]],
) -> None:
    parents = {
        row["evidence_identity"]: row
        for row in context.evidence_rows
        if row["evidence_kind"] in SELECTOR_KINDS
    }
    grouped: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    child_ids: set[str] = set()
    for row in rows:
        parent_id = str(row["parent_evidence_identity"])
        if parent_id not in parents:
            raise ValueError(f"selector expansion has unknown parent: {parent_id}")
        child_id = str(row["child_identity"])
        if child_id in child_ids:
            raise ValueError(f"duplicate selector child identity: {child_id}")
        child_ids.add(child_id)
        grouped[parent_id].append(row)
    if set(grouped) != set(parents):
        raise ValueError("selector expansion parent set is not exact")
    for parent_id, parent in parents.items():
        actual = sorted(grouped[parent_id], key=lambda row: int(str(row["child_ordinal"])))
        if [int(str(row["child_ordinal"])) for row in actual] != list(
            range(1, len(actual) + 1)
        ):
            raise ValueError(f"non-contiguous selector ordinals: {parent_id}")
        if any(
            row["parent_value_sha256"] != parent["selected_source_value_sha256"]
            for row in actual
        ):
            raise ValueError(f"selector parent hash mismatch: {parent_id}")
        grammar = grammar_children(
            parent["evidence_kind"], parent["selected_source_value"]
        )
        anchor_assignments = (
            rust_selector_anchor_assignments(context, parent, grammar)
            if parent["evidence_kind"] == "CLUSTER_RUST_SURFACES_SELECTOR"
            else tuple(() for _ in grammar)
        )
        expected = [
            (kind, value, ",".join(anchor_ids) or "NONE")
            for (kind, value), anchor_ids in zip(grammar, anchor_assignments)
        ]
        observed = [
            (
                str(row["child_kind"]),
                str(row["child_value"]),
                str(row["anchored_evidence_identity_ids"]),
            )
            for row in actual
        ]
        if observed != expected:
            raise ValueError(f"selector expansion is not exhaustive and ordered: {parent_id}")
        for row in actual:
            expected_identity = sha256_text(
                f"{parent_id}\0{row['child_ordinal']}\0{row['child_kind']}\0{row['child_value']}"
            )
            if row["child_identity"] != expected_identity:
                raise ValueError(f"selector child identity mismatch: {parent_id}")
            if row["child_value_sha256"] != sha256_text(str(row["child_value"])):
                raise ValueError(f"selector child value hash mismatch: {parent_id}")
    kinds = Counter(str(row["child_kind"]) for row in rows)
    if "ANCHORED_EVIDENCE" in kinds:
        raise ValueError("direct evidence was incorrectly materialized as a selector child")
    if kinds["HELPER_TYPE"] == 0 or kinds["HELPER_CANARY"] == 0:
        raise ValueError("selector expansion omitted independently named helper identities")


def validate_target_member_authority(
    context: AuthorityContext,
    expansion_rows: Sequence[Mapping[str, object]],
    target_rows: Sequence[Mapping[str, object]],
    member_rows: Sequence[Mapping[str, object]],
) -> None:
    expected_direct = {
        row["evidence_identity"]
        for row in context.evidence_rows
        if row["evidence_kind"] not in SELECTOR_KINDS
    }
    expected_children = {str(row["child_identity"]) for row in expansion_rows}
    actual_direct = {
        str(row["subject_identity"])
        for row in target_rows
        if row["subject_kind"] == "DIRECT_EVIDENCE"
    }
    actual_children = {
        str(row["subject_identity"])
        for row in target_rows
        if row["subject_kind"] == "SELECTOR_CHILD"
    }
    if actual_direct != expected_direct or actual_children != expected_children:
        raise ValueError("target authority subject universe is not exact")
    grouped: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    seen_pairs: set[tuple[str, str]] = set()
    for row in target_rows:
        pair = (str(row["subject_identity"]), str(row["target_id"]))
        if pair in seen_pairs:
            raise ValueError(f"duplicate subject/target terminal: {pair}")
        seen_pairs.add(pair)
        grouped[pair[0]].append(row)
        if row["terminal_disposition"] not in LEGAL_TERMINALS:
            raise ValueError(f"illegal target terminal: {pair}")
        for field in ("target_authority", "member_authority"):
            value = str(row[field])
            if any(marker in value for marker in NO_FUZZY_MARKERS):
                raise ValueError(f"non-exact target/member authority: {value}")
        if row["terminal_disposition"] == "EXCLUDED_BLOCKS_CLAIM" and row["blocked_claims"] == "NONE":
            raise ValueError(f"claim-blocking exclusion lacks exact claims: {pair}")
    for subject, rows_for_subject in grouped.items():
        ordered = sorted(rows_for_subject, key=lambda row: int(str(row["target_ordinal"])))
        if [int(str(row["target_ordinal"])) for row in ordered] != list(
            range(1, len(ordered) + 1)
        ):
            raise ValueError(f"non-contiguous target ordinals: {subject}")
    expansion_targets = {
        str(row["child_identity"]): csv_ids(str(row["applicable_target_ids"]))
        for row in expansion_rows
    }
    for subject, expected in expansion_targets.items():
        observed = tuple(
            str(row["target_id"])
            for row in sorted(grouped[subject], key=lambda row: int(str(row["target_ordinal"])))
        )
        if observed != expected:
            raise ValueError(f"selector child target rows differ from expansion: {subject}")

    # The known second-target population is exact in the immutable G0 input.
    second_gate_subjects = {
        row["evidence_identity"]
        for row in context.evidence_rows
        if row["evidence_kind"] == "CONCRETE_TRAIT_IMPL"
        and row["applicability_primary_refinement_family_or_gate"] == FAMILY_ID
        and row["applicability_additional_operation_gate_stage_ids"] != "NONE"
    }
    if len(second_gate_subjects) != 29:
        raise ValueError("immutable dense second-gate population is not 29")
    for subject in second_gate_subjects:
        rows_for_subject = grouped[subject]
        gate_rows = [
            row
            for row in rows_for_subject
            if str(row["target_id"]).startswith("GATE-")
        ]
        if len(gate_rows) != 1 or gate_rows[0]["terminal_disposition"] != "EXCLUDED_BLOCKS_CLAIM":
            raise ValueError(f"second gate lacks one legal terminal: {subject}")

    refined = {
        str(row["subject_identity"]): set(csv_ids(str(row["member_contract_ids"])))
        for row in target_rows
        if row["target_id"] == FAMILY_ID
        and row["terminal_disposition"] == "REFINED_IN_LOCK"
    }
    observed_members: dict[str, set[str]] = defaultdict(set)
    seen_member_rows: set[tuple[str, str]] = set()
    for row in member_rows:
        key = (str(row["subject_identity"]), str(row["member_contract_id"]))
        if key in seen_member_rows:
            raise ValueError(f"duplicate exact evidence/member binding: {key}")
        seen_member_rows.add(key)
        if row["target_id"] != FAMILY_ID or row["outcome_id"] != OUTCOME_BINDING:
            raise ValueError(f"member authority bypasses declarative outcome binding: {key}")
        if row["member_contract_id"] not in ALL_MEMBERS:
            raise ValueError(f"member authority uses unknown member: {key}")
        observed_members[key[0]].add(key[1])
    if dict(observed_members) != refined:
        raise ValueError("refined evidence/member authority is not exact")


def validate_overlay_authority(
    context: AuthorityContext,
    rows: Sequence[Mapping[str, object]],
) -> None:
    frozen = {(row["contract_id"], row["branch_id"]): row for row in context.overlay_rows}
    grouped: dict[tuple[str, str], list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        key = (str(row["cluster_id"]), str(row["overlay_branch_id"]))
        if key not in frozen:
            raise ValueError(f"overlay authority has unknown branch: {key}")
        grouped[key].append(row)
    if set(grouped) != set(frozen):
        raise ValueError("overlay authority omits a frozen branch")
    capability_order = tuple(row["capability_id"] for row in context.capability_rows)
    for key, source in frozen.items():
        expected_members = set(overlay_members(*key))
        actual = grouped[key]
        actual_members = {
            str(row["member_contract_id"])
            for row in actual
            if row["member_contract_id"] != "NONE"
        }
        if actual_members != expected_members:
            raise ValueError(f"overlay/member binding differs from exact authority: {key}")
        if len(actual_members) != len([row for row in actual if row["member_contract_id"] != "NONE"]):
            raise ValueError(f"overlay/member binding duplicates a unit: {key}")
        if not expected_members:
            if len(actual) != 1 or actual[0]["binding_state"] != "NO_F_DENSE_MEMBER_TARGET":
                raise ValueError(f"cross-topology overlay branch is not explicitly terminal: {key}")
            continue
        conditional = csv_ids(source["conditional_capability_ids"])
        for row in actual:
            if row["outcome_id"] != OUTCOME_BINDING:
                raise ValueError(f"overlay bypasses declarative outcome binding: {key}")
            if csv_ids(str(row["conditional_capability_ids"])) != conditional:
                raise ValueError(f"overlay conditional delta mismatch: {key}")
            expected_effective = ordered_union(
                capability_order,
                csv_ids(str(row["base_capability_ids"])),
                conditional,
            )
            if csv_ids(str(row["effective_capability_ids"])) != expected_effective:
                raise ValueError(f"overlay effective capability union mismatch: {key}")


def validate_role_capability_authority(
    context: AuthorityContext,
    role_rows: Sequence[Mapping[str, object]],
    capability_rows: Sequence[Mapping[str, object]],
) -> None:
    expected_roles = {row["obligation_id"] for row in applicable_requirement_rows(context)}
    actual_roles = {str(row["obligation_id"]) for row in role_rows}
    if actual_roles != expected_roles or len(expected_roles) != 24:
        raise ValueError("role authority is not the exact 24-row applicable obligation set")
    grouped_roles: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in role_rows:
        grouped_roles[str(row["obligation_id"])].append(row)
        if row["member_contract_id"] != "NONE" and row["outcome_id"] != OUTCOME_BINDING:
            raise ValueError("role member bypasses declarative outcome binding")
    for obligation, rows_for_obligation in grouped_roles.items():
        disposition = {str(row["owner_lock_disposition"]) for row in rows_for_obligation}
        if len(disposition) != 1:
            raise ValueError(f"role has inconsistent dispositions: {obligation}")
        if "REQUIRED_IN_LOCK" in disposition and not any(
            row["binding_kind"] == "MEMBER" for row in rows_for_obligation
        ):
            raise ValueError(f"required role has no exact member: {obligation}")

    expected_capabilities = {row["capability_id"] for row in context.capability_rows}
    actual_capabilities = {str(row["capability_id"]) for row in capability_rows}
    if actual_capabilities != expected_capabilities or len(expected_capabilities) != 49:
        raise ValueError("capability authority does not equal the 49-row registry")
    grouped_capabilities: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in capability_rows:
        grouped_capabilities[str(row["capability_id"])].append(row)
        if row["member_contract_id"] != "NONE" and row["outcome_id"] != OUTCOME_BINDING:
            raise ValueError("capability member bypasses declarative outcome binding")
    for capability, rows_for_capability in grouped_capabilities.items():
        applicability = {str(row["applicability"]) for row in rows_for_capability}
        if len(applicability) != 1:
            raise ValueError(f"capability has inconsistent applicability: {capability}")
        state = next(iter(applicability))
        if state == "REQUIRED" and not any(
            row["binding_kind"] == "MEMBER" for row in rows_for_capability
        ):
            raise ValueError(f"required capability has no exact member: {capability}")
        if state == "PROTECTED" and not any(
            row["binding_kind"] == "CONTROL" for row in rows_for_capability
        ):
            raise ValueError(f"protected capability has no control: {capability}")


def validate_authorities(
    context: AuthorityContext,
    outputs: Mapping[str, Sequence[Mapping[str, object]]],
) -> None:
    if set(outputs) != set(OUTPUT_FIELDS):
        raise ValueError("authority output file set is not exact")
    if context.snapshot.file("G0-CORE-ARTIFACT-MANIFEST.json").sha256 != G0_MANIFEST_SHA256:
        raise ValueError("frozen G0 manifest digest differs from the reviewed close")
    inputs = outputs["DENSE-FROZEN-G0-INPUT-AUTHORITY.tsv"]
    if len(inputs) != len(G0_INPUTS) or any(
        row["git_commit"] != G0_CLOSING_COMMIT
        or row["access_method"] != "GIT_SHOW_COMMIT_PATH_ONLY"
        for row in inputs
    ):
        raise ValueError("G0 inputs are not immutable git-show authorities")
    validate_selector_authority(
        context, outputs["DENSE-SELECTOR-EXPANSION-AUTHORITY.tsv"]
    )
    validate_target_member_authority(
        context,
        outputs["DENSE-SELECTOR-EXPANSION-AUTHORITY.tsv"],
        outputs["DENSE-EVIDENCE-TARGET-AUTHORITY.tsv"],
        outputs["DENSE-EVIDENCE-MEMBER-AUTHORITY.tsv"],
    )
    validate_overlay_authority(
        context, outputs["DENSE-OVERLAY-BRANCH-AUTHORITY.tsv"]
    )
    validate_role_capability_authority(
        context,
        outputs["DENSE-ROLE-UNIT-AUTHORITY.tsv"],
        outputs["DENSE-CAPABILITY-UNIT-AUTHORITY.tsv"],
    )
    for name, rows in outputs.items():
        tsv_bytes(OUTPUT_FIELDS[name], rows)


def bind_declarative_outcomes(
    rows: Sequence[Mapping[str, object]],
    outcomes_by_member: Mapping[str, Sequence[str]],
) -> list[dict[str, object]]:
    """Expand fail-closed member placeholders from a declarative registry.

    Root integration can use this helper for the evidence, overlay, role, and
    capability authority rows.  Missing, empty, duplicate, or unknown outcome
    lists fail rather than retaining a generic outcome name.
    """
    result: list[dict[str, object]] = []
    for source in rows:
        row = dict(source)
        if row.get("outcome_id") != OUTCOME_BINDING:
            result.append(row)
            continue
        member = str(row.get("member_contract_id", ""))
        if member not in outcomes_by_member:
            raise ValueError(f"declarative outcome registry omits member: {member}")
        outcomes = tuple(outcomes_by_member[member])
        if not outcomes or len(outcomes) != len(set(outcomes)) or any(
            not outcome or outcome == OUTCOME_BINDING for outcome in outcomes
        ):
            raise ValueError(f"invalid declarative outcome set for member: {member}")
        for outcome in outcomes:
            expanded = dict(row)
            expanded["outcome_id"] = outcome
            if "outcome_binding_authority" in expanded:
                expanded["outcome_binding_authority"] = "DECLARATIVE_CONTRACT_REGISTRY_EXACT_MEMBER_JOIN"
            result.append(expanded)
    return result


def resolve_evidence_outcomes(
    authority_rows: Sequence[Mapping[str, object]],
    contract_rows: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Resolve evidence/member placeholders against the exact contract registry.

    The relational join is ``(target_id='F-DENSE', cluster_id,
    member_contract_id)`` plus exact membership of ``subject_identity`` in the
    contract row's ``evidence_identity_ids``.  The returned unit key is
    ``(subject_kind, subject_identity, target_id, member_contract_id,
    policy_variant_id, outcome_id)``.  Zero matches, unknown members, duplicate
    contract identities, duplicate registry units, and duplicate resolved units
    all fail closed.

    The resolver adds ``contract_id``, ``policy_variant_id``, and
    ``contract_registry_status`` to each returned row.  It does not read or
    depend on a particular registry file, so root integration can pass the
    declarative generator's in-memory rows before any artifact is written.
    """
    required_contract_fields = {
        "contract_id",
        "member_contract_id",
        "outcome_id",
        "cluster_id",
        "policy_variant_id",
        "status",
        "evidence_identity_ids",
    }
    registry_by_join: dict[tuple[str, str], list[Mapping[str, object]]] = defaultdict(list)
    contract_ids: set[str] = set()
    registry_units: set[tuple[str, str, str, str]] = set()
    for row in contract_rows:
        missing = required_contract_fields - set(row)
        if missing:
            raise ValueError(
                f"declarative contract row lacks fields: {sorted(missing)}"
            )
        contract_id = str(row["contract_id"])
        cluster_id = str(row["cluster_id"])
        member = str(row["member_contract_id"])
        policy = str(row["policy_variant_id"])
        outcome = str(row["outcome_id"])
        if (
            not contract_id
            or contract_id in contract_ids
            or not cluster_id
            or not member
            or member not in ALL_MEMBERS
            or not policy
            or not outcome
            or outcome == OUTCOME_BINDING
        ):
            raise ValueError(f"invalid declarative contract row: {contract_id!r}")
        contract_ids.add(contract_id)
        registry_unit = (cluster_id, member, policy, outcome)
        if registry_unit in registry_units:
            raise ValueError(f"duplicate declarative member outcome: {registry_unit}")
        registry_units.add(registry_unit)
        registry_by_join[(cluster_id, member)].append(row)

    result: list[dict[str, object]] = []
    seen_authority_units: set[tuple[str, str, str, str]] = set()
    seen_resolved_units: set[tuple[str, str, str, str, str, str]] = set()
    authority_relations: set[tuple[str, str, str]] = set()
    for source in authority_rows:
        if source.get("target_id") != FAMILY_ID:
            raise ValueError("evidence/member authority target is not F-DENSE")
        if source.get("outcome_id") != OUTCOME_BINDING:
            raise ValueError("evidence/member authority is not fail-closed")
        subject_kind = str(source.get("subject_kind", ""))
        subject = str(source.get("subject_identity", ""))
        cluster_id = str(source.get("cluster_id", ""))
        member = str(source.get("member_contract_id", ""))
        authority_unit = (subject_kind, subject, cluster_id, member)
        if (
            not subject_kind
            or not subject
            or member not in ALL_MEMBERS
            or authority_unit in seen_authority_units
        ):
            raise ValueError(f"invalid or duplicate evidence/member authority: {authority_unit}")
        seen_authority_units.add(authority_unit)
        authority_relations.add((cluster_id, member, subject))
        matches = [
            row
            for row in registry_by_join.get((cluster_id, member), ())
            if subject in csv_ids(str(row["evidence_identity_ids"]))
        ]
        if not matches:
            raise ValueError(
                "declarative registry has zero exact outcome resolutions for "
                f"{authority_unit}"
            )
        matches.sort(
            key=lambda row: (
                str(row["policy_variant_id"]),
                str(row["outcome_id"]),
                str(row["contract_id"]),
            )
        )
        for contract in matches:
            policy = str(contract["policy_variant_id"])
            outcome = str(contract["outcome_id"])
            resolved_key = (
                subject_kind,
                subject,
                FAMILY_ID,
                member,
                policy,
                outcome,
            )
            if resolved_key in seen_resolved_units:
                raise ValueError(
                    f"duplicate evidence/member/outcome resolution: {resolved_key}"
                )
            seen_resolved_units.add(resolved_key)
            row = dict(source)
            row["outcome_id"] = outcome
            row["policy_variant_id"] = policy
            row["contract_id"] = str(contract["contract_id"])
            row["contract_registry_status"] = str(contract["status"])
            row["outcome_binding_authority"] = (
                "EXACT_CONTRACT_REGISTRY_CLUSTER_MEMBER_AND_EVIDENCE_JOIN"
            )
            result.append(row)
    if len(seen_authority_units) != len(authority_rows):
        raise ValueError("evidence/member authority resolution lost a source unit")
    for contract in contract_rows:
        cluster_id = str(contract["cluster_id"])
        member = str(contract["member_contract_id"])
        evidence_ids = csv_ids(str(contract["evidence_identity_ids"]))
        if not evidence_ids or len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError(
                "declarative contract has no exact or has duplicate evidence identities: "
                f"{contract['contract_id']}"
            )
        for evidence_identity in evidence_ids:
            if evidence_identity.startswith("SYNTHETIC:"):
                if evidence_identity != f"SYNTHETIC:{member}":
                    raise ValueError(
                        "declarative contract has an invalid synthetic evidence identity: "
                        f"{contract['contract_id']} {evidence_identity}"
                    )
                continue
            relation = (cluster_id, member, evidence_identity)
            if relation not in authority_relations:
                raise ValueError(
                    "declarative contract evidence does not resolve back to one "
                    f"coverage authority relation: {contract['contract_id']} {relation}"
                )
    return result


def assert_no_unresolved_outcomes(
    rows: Sequence[Mapping[str, object]],
) -> None:
    unresolved = [
        str(row.get("member_contract_id", "NONE"))
        for row in rows
        if row.get("outcome_id") == OUTCOME_BINDING
    ]
    if unresolved:
        raise ValueError(
            "declarative contract outcomes remain unresolved for members: "
            + ",".join(sorted(set(unresolved)))
        )


def write_or_check(
    outputs: Mapping[str, Sequence[Mapping[str, object]]], check: bool
) -> None:
    for name in OUTPUT_FIELDS:
        expected = tsv_bytes(OUTPUT_FIELDS[name], outputs[name])
        path = HERE / name
        if check:
            if not path.is_file() or path.read_bytes() != expected:
                raise SystemExit(f"authority artifact differs from frozen derivation: {name}")
        else:
            path.write_bytes(expected)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify generated authority bytes without writing",
    )
    arguments = parser.parse_args()
    context, outputs = build_authorities()
    write_or_check(outputs, arguments.check)
    counts = {
        "frozen_inputs": len(outputs["DENSE-FROZEN-G0-INPUT-AUTHORITY.tsv"]),
        "selector_children": len(outputs["DENSE-SELECTOR-EXPANSION-AUTHORITY.tsv"]),
        "target_terminals": len(outputs["DENSE-EVIDENCE-TARGET-AUTHORITY.tsv"]),
        "evidence_member_bindings": len(outputs["DENSE-EVIDENCE-MEMBER-AUTHORITY.tsv"]),
        "overlay_bindings": len(outputs["DENSE-OVERLAY-BRANCH-AUTHORITY.tsv"]),
        "role_bindings": len(outputs["DENSE-ROLE-UNIT-AUTHORITY.tsv"]),
        "capability_bindings": len(outputs["DENSE-CAPABILITY-UNIT-AUTHORITY.tsv"]),
        "audit_clusters": len(context.audit_clusters),
    }
    action = "verified" if arguments.check else "wrote"
    print(
        f"Dense coverage authority {action}: "
        + ", ".join(f"{name}={value}" for name, value in counts.items())
    )


if __name__ == "__main__":
    main()
