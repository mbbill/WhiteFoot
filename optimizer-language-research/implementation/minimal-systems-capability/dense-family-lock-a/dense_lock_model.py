#!/usr/bin/env python3
"""Authoritative declarative model for the dense Family Lock A draft."""

from __future__ import annotations


FAMILY_ID = "F-DENSE"
LOCK_ID = "F-DENSE-LOCK-A-R1"
LOCK_STATUS = "OWNER_REVIEW_DRAFT"
G0_CLOSING_COMMIT = "a4de0eb70c345dcd198b11f435a5538ccc863113"
AUTHORIZATION_COMMIT = "c4ca5437fc90f3ce833fb026f2e794f4f758d011"


# A cluster may split into several exact caller contracts. The source selector
# and exact evidence key choose the narrowest matching member. The first member
# is the fail-closed fallback only when the cluster has one member.
CLUSTER_MEMBERS = {
    "ARR-VIEW-01": ["DENSE-FIXED-VIEW"],
    "ARR-EACH-01": ["DENSE-FIXED-EACH"],
    "ARR-MAP-01": ["DENSE-FIXED-MAP"],
    "VIEW-META-01": ["DENSE-VIEW-META"],
    "VIEW-GET-01": ["DENSE-VIEW-GET-SHARED"],
    "VIEW-GET-02": ["DENSE-VIEW-GET-UNIQ"],
    "VIEW-END-01": ["DENSE-VIEW-END"],
    "VIEW-ARRAY-01": ["DENSE-VIEW-AS-FIXED"],
    "VIEW-END-CHUNK-01": ["DENSE-VIEW-END-CHUNK"],
    "VIEW-END-SPLIT-01": ["DENSE-VIEW-END-SPLIT"],
    "VIEW-SPLIT-01": ["DENSE-VIEW-SPLIT-TRAP"],
    "VIEW-SPLIT-02": ["DENSE-VIEW-SPLIT-CHECKED"],
    "VIEW-CONSUME-01": ["DENSE-VIEW-CONSUME-SPLIT"],
    "VIEW-DISJOINT-01": ["DENSE-VIEW-DISJOINT-UNIQ"],
    "VIEW-ARRAY-CHUNKS-01": ["DENSE-VIEW-ARRAY-CHUNKS"],
    "VIEW-SORT-01": ["DENSE-SORT-STABLE", "DENSE-SORT-STABLE-CACHED-KEY"],
    "VIEW-SORT-02": ["DENSE-SORT-UNSTABLE"],
    "VIEW-SELECT-01": ["DENSE-SELECT-UNSTABLE"],
    "VIEW-REORDER-01": ["DENSE-REVERSE", "DENSE-ROTATE"],
    "VIEW-SWAP-01": ["DENSE-SWAP", "DENSE-SWAP-WITH-VIEW"],
    "VIEW-COPY-01": ["DENSE-COPY-FROM", "DENSE-COPY-WITHIN"],
    "VIEW-CLONE-01": ["DENSE-CLONE-FROM"],
    "VIEW-FILL-01": ["DENSE-FILL-CLONE", "DENSE-FILL-WITH"],
    "VIEW-ALLOC-01": ["DENSE-FRESH-CLONE", "DENSE-INTO-OWNER"],
    "VIEW-CONCAT-01": ["DENSE-CONCAT", "DENSE-JOIN", "DENSE-REPEAT"],
    "INIT-WRITE-01": ["DENSE-INIT-COPY", "DENSE-INIT-CLONE"],
    "BOX-INIT-01": ["DENSE-BOX-INIT-EVIDENCE"],
    "SEQ-META-01": ["DENSE-NEW", "DENSE-WITH-CAPACITY", "DENSE-META"],
    "SEQ-RESERVE-01": ["DENSE-RESERVE", "DENSE-RESERVE-EXACT"],
    "SEQ-TRY-RESERVE-01": ["DENSE-TRY-RESERVE", "DENSE-TRY-RESERVE-EXACT"],
    "SEQ-SHRINK-01": ["DENSE-SHRINK-TO", "DENSE-SHRINK-TO-FIT"],
    "SEQ-VIEW-01": ["DENSE-OWNER-VIEW"],
    "SEQ-PUSH-01": ["DENSE-PUSH", "DENSE-PUSH-UNIQ"],
    "SEQ-INSERT-01": ["DENSE-INSERT", "DENSE-INSERT-UNIQ"],
    "SEQ-POP-01": ["DENSE-POP", "DENSE-POP-IF"],
    "SEQ-REMOVE-01": ["DENSE-REMOVE", "DENSE-SWAP-REMOVE"],
    "SEQ-APPEND-01": ["DENSE-APPEND-MOVE"],
    "SEQ-EXTEND-COPY-01": ["DENSE-EXTEND-CLONE", "DENSE-EXTEND-WITHIN"],
    "SEQ-RESIZE-01": ["DENSE-RESIZE-CLONE", "DENSE-RESIZE-WITH"],
    "SEQ-TRUNCATE-01": ["DENSE-TRUNCATE", "DENSE-CLEAR"],
    "SEQ-RETAIN-01": ["DENSE-RETAIN", "DENSE-RETAIN-MUT"],
    "SEQ-DEDUP-01": ["DENSE-DEDUP", "DENSE-DEDUP-BY", "DENSE-DEDUP-BY-KEY"],
    "SEQ-DRAIN-01": ["DENSE-LAZY-DRAIN-EVIDENCE"],
    "SEQ-EXTRACT-01": ["DENSE-EAGER-EXTRACT", "DENSE-LAZY-EXTRACT-EVIDENCE"],
    "SEQ-SPLICE-01": ["DENSE-EAGER-SPLICE", "DENSE-LAZY-SPLICE-EVIDENCE"],
    "SEQ-SPLIT-01": ["DENSE-SPLIT-OFF"],
    "SEQ-CONVERT-01": ["DENSE-INTO-BOXED", "DENSE-INTO-FLATTENED"],
    "TRAIT-INTOITER-01": ["DENSE-ITER-SHARED", "DENSE-ITER-UNIQ", "DENSE-ITER-OWN"],
    "TRAIT-EXTEND-01": ["DENSE-EXTEND-ITER"],
    "TRAIT-COLLECT-01": ["DENSE-COLLECT"],
    "TRAIT-INDEX-01": ["DENSE-INDEX-SHARED", "DENSE-INDEX-UNIQ"],
    "TRAIT-DEREF-01": ["DENSE-OWNER-VIEW"],
    "TRAIT-BORROW-01": ["DENSE-OWNER-VIEW"],
    "TRAIT-CONVERT-01": ["DENSE-CONVERT"],
    "TRAIT-CLONE-01": ["DENSE-FRESH-CLONE", "DENSE-CLONE-FROM"],
    "TRAIT-DEFAULT-01": ["DENSE-DEFAULT"],
    "TRAIT-CMP-01": ["DENSE-COMPARE", "DENSE-HASH-TRAVERSAL"],
    "TRAIT-DROP-01": ["DENSE-DROP"],
    "MEM-REPLACE-01": ["DENSE-REPLACE"],
    "MEM-TAKE-01": ["DENSE-TAKE-WITH-DEFAULT"],
    "RAW-SAFE-SPARE-01": ["DENSE-RAW-SPARE-REJECTED"],
    "RAW-UNSAFE-ACCESS-01": ["DENSE-UNCHECKED-ACCESS-EVIDENCE"],
    "RAW-UNSAFE-ALIGN-01": ["DENSE-ALIGN-EVIDENCE"],
    "RAW-UNSAFE-INIT-01": ["DENSE-INIT-AUTHORITY-EVIDENCE"],
    "RAW-UNSAFE-LEN-01": ["DENSE-LEN-AUTHORITY-EVIDENCE"],
}


SPECIAL_MEMBER_MATCHES = {
    "sort_by_cached_key": "DENSE-SORT-STABLE-CACHED-KEY",
    "rotate_": "DENSE-ROTATE",
    "swap_with_slice": "DENSE-SWAP-WITH-VIEW",
    "copy_within": "DENSE-COPY-WITHIN",
    "copy_from_slice": "DENSE-COPY-FROM",
    "fill_with": "DENSE-FILL-WITH",
    "fill": "DENSE-FILL-CLONE",
    "into_vec": "DENSE-INTO-OWNER",
    "to_vec": "DENSE-FRESH-CLONE",
    "connect": "DENSE-JOIN",
    "join": "DENSE-JOIN",
    "repeat": "DENSE-REPEAT",
    "concat": "DENSE-CONCAT",
    "write_copy": "DENSE-INIT-COPY",
    "write_clone": "DENSE-INIT-CLONE",
    "with_capacity": "DENSE-WITH-CAPACITY",
    "capacity": "DENSE-META",
    "is_empty": "DENSE-META",
    "len": "DENSE-META",
    "new": "DENSE-NEW",
    "try_reserve_exact": "DENSE-TRY-RESERVE-EXACT",
    "try_reserve": "DENSE-TRY-RESERVE",
    "reserve_exact": "DENSE-RESERVE-EXACT",
    "reserve": "DENSE-RESERVE",
    "shrink_to_fit": "DENSE-SHRINK-TO-FIT",
    "shrink_to": "DENSE-SHRINK-TO",
    "push_mut": "DENSE-PUSH-UNIQ",
    "push": "DENSE-PUSH",
    "insert_mut": "DENSE-INSERT-UNIQ",
    "insert": "DENSE-INSERT",
    "pop_if": "DENSE-POP-IF",
    "pop": "DENSE-POP",
    "swap_remove": "DENSE-SWAP-REMOVE",
    "remove": "DENSE-REMOVE",
    "extend_from_within": "DENSE-EXTEND-WITHIN",
    "extend_from_slice": "DENSE-EXTEND-CLONE",
    "resize_with": "DENSE-RESIZE-WITH",
    "resize": "DENSE-RESIZE-CLONE",
    "clear": "DENSE-CLEAR",
    "truncate": "DENSE-TRUNCATE",
    "retain_mut": "DENSE-RETAIN-MUT",
    "retain": "DENSE-RETAIN",
    "dedup_by_key": "DENSE-DEDUP-BY-KEY",
    "dedup_by": "DENSE-DEDUP-BY",
    "dedup": "DENSE-DEDUP",
    "extract_if": "DENSE-LAZY-EXTRACT-EVIDENCE",
    "splice": "DENSE-LAZY-SPLICE-EVIDENCE",
    "drain": "DENSE-LAZY-DRAIN-EVIDENCE",
    "into_flattened": "DENSE-INTO-FLATTENED",
    "into_boxed_slice": "DENSE-INTO-BOXED",
    "clone_from": "DENSE-CLONE-FROM",
}


EXCLUDED_MEMBERS = {
    "DENSE-LAZY-DRAIN-EVIDENCE": "O-LAZY-DRAIN is not promoted; eager range removal is mandatory instead.",
    "DENSE-LAZY-EXTRACT-EVIDENCE": "A lazy repair-bearing cursor is excluded; eager stable extraction remains mandatory.",
    "DENSE-LAZY-SPLICE-EVIDENCE": "A lazy repair-bearing cursor is excluded; eager splice remains mandatory.",
    "DENSE-RAW-SPARE-REJECTED": "Writer-visible spare-capacity initialization state is constitutionally inadmissible.",
    "DENSE-UNCHECKED-ACCESS-EVIDENCE": "Unchecked caller access is evidence only and never an xlang surface.",
    "DENSE-ALIGN-EVIDENCE": "Unchecked type-punning is evidence only and outside the dense claim.",
    "DENSE-INIT-AUTHORITY-EVIDENCE": "Writer-forgeable initialization authority is evidence only.",
    "DENSE-LEN-AUTHORITY-EVIDENCE": "Writer-forgeable live-length authority is evidence only.",
    "DENSE-BOX-INIT-EVIDENCE": "Box-specific recursive ownership is deferred to F-RECURSIVE; only shared initialization obligations are evidence here.",
}


MEMBER_OVERRIDES = {
    "DENSE-EAGER-EXTRACT": {
        "pre": "A valid dense owner and a finite index interval or predicate are supplied; no incompatible borrow is live.",
        "result": "Returns a valid dense owner plus an owning dense sequence of removed values, preserving retained order.",
        "complexity": "O(n) predicate calls and O(n) relocations in the worst case; one pass; no per-element allocation.",
        "behavior": "The predicate is invoked exactly once for every visited original element, in increasing index order, and may mutate its current element.",
    },
    "DENSE-EAGER-SPLICE": {
        "pre": "A valid dense owner, checked finite range, and finite replacement producer are supplied; no incompatible borrow is live.",
        "result": "Returns a valid dense owner plus an owning dense sequence of removed values; replacements occupy the range in producer order.",
        "complexity": "O(n + r) moves and O(r) production; at most one growth allocation; no per-element allocation.",
        "behavior": "Replacement production is ordered and each produced affine value is consumed exactly once.",
    },
    "DENSE-PUSH": {
        "pre": "A valid dense owner and one affine value are supplied with no incompatible borrow.",
        "result": "Success returns the valid owner with the value moved once to old len; recoverable precommit failure returns both original owner and offered value unchanged.",
        "complexity": "O(1) amortized, O(n) only on growth; at most one allocation per growth.",
    },
    "DENSE-INSERT": {
        "pre": "A valid dense owner, affine value, and index in 0..=len are supplied with no incompatible borrow.",
        "result": "Success shifts the suffix right by direct relocation and moves the offered value once; precommit failure returns owner and value unchanged.",
        "complexity": "O(n-index) relocations plus at most one O(n) growth relocation.",
    },
    "DENSE-REMOVE": {
        "pre": "A valid dense owner and index in 0..len are supplied with no incompatible borrow.",
        "result": "Returns the removed affine value and a valid owner; the suffix is relocated left once and order is preserved.",
        "complexity": "O(n-index) relocations, no allocation.",
    },
    "DENSE-SWAP-REMOVE": {
        "pre": "A valid dense owner and index in 0..len are supplied with no incompatible borrow.",
        "result": "Returns the removed affine value; if nonlast, the last value relocates once into the hole; order is not preserved.",
        "complexity": "O(1), no allocation.",
    },
    "DENSE-POP": {
        "pre": "A valid dense owner is supplied with no incompatible borrow.",
        "result": "Empty returns None and the unchanged owner; nonempty marks the last slot dead before returning its sole affine value.",
        "complexity": "O(1), no allocation.",
    },
    "DENSE-REPLACE": {
        "pre": "A live place and one affine replacement are supplied through unique authority.",
        "result": "Atomically returns the former owner and installs the replacement; no placeholder, clone, or double-live state is observable.",
        "complexity": "O(1) plus payload move size, no allocation.",
    },
    "DENSE-SWAP": {
        "pre": "Two checked dynamic indices into one live dense prefix are supplied through unique authority.",
        "result": "Equal indices are a checked no-op; unequal indices exchange the two sole owners without cloning or destruction.",
        "complexity": "O(1), no allocation.",
    },
    "DENSE-RESERVE": {
        "pre": "A valid dense owner and additional element count are supplied with no live payload borrow.",
        "result": "Success returns capacity >= len+additional; a current OOM aborts; checked overflow traps before mutation.",
        "complexity": "O(n) only when growth relocates; at most one allocation.",
    },
    "DENSE-TRY-RESERVE": {
        "pre": "A valid dense owner and additional element count are supplied with no live payload borrow.",
        "result": "Success returns sufficient capacity; recoverable allocation failure returns the byte-identical logical owner and allocation; checked arithmetic error is a distinct error.",
        "complexity": "O(n) only on successful relocating growth; at most one allocation attempt.",
    },
    "DENSE-DROP": {
        "pre": "Sole destruction authority for a valid dense owner is supplied.",
        "result": "Destroys exactly slots [0,len), never spare capacity, then releases the allocation exactly once.",
        "complexity": "O(len) payload destructions and one allocation release.",
    },
    "DENSE-ITER-OWN": {
        "pre": "A valid dense owner is consumed.",
        "result": "The cursor solely owns the allocation and a live interval [front,back); each yield kills one endpoint before returning its value; consuming close destroys the remainder and releases once.",
        "complexity": "O(1) per yield and O(remaining) close, no allocation.",
    },
}


# Mechanisms are descriptions only. No syntax, compiler implementation, or
# production selection is authorized by this file.
CANDIDATES = [
    {
        "id": "C-ATOMIC-TRANSITIONS",
        "mechanism": "A sealed generic storage owner exposes a lexical range-transition region plus checked initialize, move-out, replace, swap, overlap-safe relocate, destroy, allocate-transfer, and release events. The region may span loops and effectful callbacks, but no hole-bearing state is observable outside it and every normal escape is checked to close to one valid owner.",
        "trusted_delta": "A generic loop-capable range-transition region, storage-state kernel, and verifier rules for transition preconditions, callbacks, exits, and postconditions; no container-specific recognition.",
        "strength": "Eliminates abandonment repair by construction and keeps steady-state ptr/len/cap representation available.",
        "risk": "The transition algebra may grow into a container-shaped kernel; without a loop-capable region it cannot implement O(n), O(1)-scratch retain after the first hole and is rejected before construction.",
        "hypothesis": "Best checker simplicity and code shape for common operations; possible code-size and expressiveness loss on complex compaction.",
    },
    {
        "id": "C-LINEAR-REBUILD",
        "mechanism": "A generic rebuild scope owns source, destination, live-set proof, allocation authority, and every moved value. Its protocol value is exact-use rather than affine: every normal control-flow edge must consume it into one valid owner or an explicit failure result.",
        "trusted_delta": "A new exact-use mode, flow checking across fallthrough/return/break/give/try, and generic state-indexed storage transitions.",
        "strength": "Small generic mechanism with direct one-way relocation and strong ordinary-library generativity.",
        "risk": "Adds a second ownership mode and substantial flow/diagnostic surface; exact-use may infect helpers or callbacks.",
        "hypothesis": "Lowest compulsory payload traffic; no steady-state metadata; compile-time and source-shape cost may be highest.",
    },
    {
        "id": "C-DERIVED-REPAIR",
        "mechanism": "A sealed affine transition scope may hold a transient hole, but the compiler derives and emits a typed repair/destruction action on every normal abandonment edge. The elaborated artifact exposes each cleanup edge for review; traps still abort without cleanup.",
        "trusted_delta": "Compiler-derived normal-exit cleanup semantics, typed repair authority, elaboration visibility, and fact invalidation across cleanup edges.",
        "strength": "Expresses drain, compaction, sorting scratch, and failure paths without an exact-use source discipline.",
        "risk": "Introduces finalizer-like kernel behavior, implicit code paths, code-size/latency tax, and a larger soundness TCB.",
        "hypothesis": "Direct relocation performance with possible cold-path and code-size regression; protected paths must prove zero emitted cleanup.",
    },
    {
        "id": "C-PROOF-CARRYING-STATE",
        "mechanism": "A checked split transition shortens a base to an immediately valid prefix and returns owner-bound, state-indexed live-range owners for disjoint suffixes or hole-adjacent ranges in the same allocation. Every intermediate is structurally droppable; successful code consumes and rejoins ranges, while abandonment drops exactly each range without repairing a prior invariant.",
        "trusted_delta": "Split allocation ownership, range-rooted provenance, state-indexed live-range owners, compiler-derived range destruction, proof erasure, and checked rejoin rules.",
        "strength": "Keeps every intermediate valid without exact-use or repair cleanup and may generalize to later sparse/dependent states without per-slot metadata.",
        "risk": "Largest grammar/type-system and solver burden; proof terms may harm AI generation and reviewability.",
        "hypothesis": "Zero runtime metadata when proofs erase, but highest compile-time, code-size, and authoring risk.",
    },
    {
        "id": "C-RUNTIME-TOPOLOGY",
        "mechanism": "A sealed generic allocation owner stores compact O(1) topology metadata for Dense and one transient Hole or split-range state. Checked transitions update metadata and payload as one authority; per-slot tags or bitmaps are not part of this arm.",
        "trusted_delta": "A generic sealed topology owner, Dense/Hole state relation, live-range destruction, and trusted metadata-to-payload fact channel with hostile optimizer review.",
        "strength": "Simple local checking and broad generativity without exact-use or compiler cleanup semantics.",
        "risk": "Transient metadata, state branches, range drop, and fact-channel complexity may tax complex operations; steady-state prefix erasure must be proved rather than asserted.",
        "hypothesis": "O(1) topology state may match direct relocation while remaining easier to check; any persistent steady-state field or protected-path tax rejects it.",
    },
]


EXCLUDED_CANDIDATES = [
    ("Writer-visible raw or MaybeUninit storage plus set_len", "Violates the no-unsafe/no-uninitialized-read surface and makes metadata a forgeable fact channel."),
    ("Affine builder with an explicit finish convention", "Affinity prevents duplication but permits abandonment; normal exits can strand a hole or live values."),
    ("Fully initialize capacity with Default or a dummy T", "Silently narrows payloads and performs pathological initialization/drop work proportional to capacity."),
    ("Rebuild the entire sequence for each mutation", "Expressible but imposes O(n) allocation/traffic on O(1) append, pop, replace, and swap contracts."),
    ("One Option<T>, tag, or bitmap bit per slot as the canonical dense representation", "It violates the H-FLATSET no-per-slot-occupancy budget and adds avoidable initialization, scan, branch, or drop cost; it remains a structural rejection control, not C-RUNTIME-TOPOLOGY."),
    ("Standard-library-only privileged container", "Fails ordinary-library generativity and creates container-specific compiler recognition."),
    ("General user finalizers", "Far broader than the dense obligation and reintroduces implicit cleanup, ordering, and effect questions without a bounded proof advantage."),
]


SCENARIO_FAMILIES = [
    ("S-INIT-UNDERFILL", "construction", "Producer stops after each k in 0..capacity; only [0,k) may be live."),
    ("S-INIT-OVERFILL", "construction", "Producer offers capacity+1 values; no out-of-bounds write and every owner has one disposition."),
    ("S-INIT-REPEAT-CLOSE", "construction", "A completed protocol cannot complete again or mint authority."),
    ("S-PUSH-FAIL", "failure", "Inject arithmetic and allocation failure before commit; base and offered affine value return unchanged."),
    ("S-INSERT-SHIFT", "relocation", "Enumerate all indices for lengths 0..4 and prove right-shift direction and exact owners."),
    ("S-REMOVE-SHIFT", "relocation", "Enumerate all indices for lengths 1..4 and prove left-shift direction and exact returned owner."),
    ("S-SWAP-EQUAL", "alias", "Equal dynamic indices are a no-op without two unique accesses."),
    ("S-GROW-SAME-ADDRESS", "provenance", "Allocator reports same-address success; all old physical references still invalidate."),
    ("S-GROW-MOVED", "provenance", "Moved-address growth transfers allocation ownership and relocates every live value exactly once."),
    ("S-GROW-FAIL", "failure", "Each recoverable allocation failure leaves old allocation, order, len, cap, and owners unchanged."),
    ("S-TRUNCATE-DROP", "destruction", "Every removed live value drops once; spare capacity never drops."),
    ("S-OWNER-DROP", "destruction", "All and only live values drop, then the allocation releases once."),
    ("S-OWN-ITER", "cursor", "Unused, partial, alternating two-ended, exhausted, repeated terminal, and close states preserve a live interval."),
    ("S-EAGER-RETAIN", "behavior", "Predicate calls and mutations follow the frozen order; retained values compact once."),
    ("S-EAGER-SPLICE", "behavior", "Replacement underfill/overfill and injected producer error leave the frozen valid post-state."),
    ("S-ABANDON", "control-flow", "Every protocol is tested at fallthrough, return, break, give, try propagation, and callback stop."),
    ("S-BORROW-INVALIDATE", "borrow", "Growth, removal, clear, shrink, and destruction reject under live element/slice borrows."),
    ("S-FACT-STALE", "fact", "Remove, grow, clear, join, and branch mismatch invalidate old live-set/version facts."),
    ("S-SIMD-DEAD-LANE", "fact", "No optimized scalar or vector load touches a dead lane before masking."),
    ("S-ZST-AFFINE", "ownership", "Zero-byte payloads still preserve logical owner and destruction cardinality."),
    ("S-NESTED-OWNER", "ownership", "Payloads containing distinct nested owners move and drop exactly once."),
    ("S-RAW-SURFACE-NEGATIVE", "static-negative", "Unchecked access, set_len, raw spare initialization, and forged completion are unspellable."),
    ("S-PROTECTED-FIXED", "protected", "B-FIX receives no capacity, occupancy, cleanup, allocation, branch, or fact tax."),
    ("S-PROTECTED-P2", "protected", "B-P2 receives no generation, recycling, validity, cleanup, branch, or fact tax."),
]


PAYLOADS = [
    ("P-U8", 1, 1, "Copy scalar control"),
    ("P-U64", 8, 8, "Copy scalar control"),
    ("P-ROW24", 24, 8, "Three-field Copy record"),
    ("P-ROW56", 56, 8, "Seven-field Copy record"),
    ("P-AFFINE24", 24, 8, "Region-free borrow-free affine record with unique identity and drop counter"),
    ("P-AFFINE64", 64, 8, "Cache-line affine record with nested allocation owner"),
    ("P-AFFINE256", 256, 8, "Large inline affine record for relocation and cache traffic"),
    ("P-BEHAVIOR", 24, 8, "Affine record with counted Clone, comparison, and mutation behavior"),
    ("P-ZST-AFFINE", 0, 1, "Zero-sized affine value with logical drop counter"),
]


TRACES = [
    ("T-APPEND", "Start empty; push N values; black-box fold; drop."),
    ("T-STACK", "Push/pop bursts with geometric burst lengths and peak N."),
    ("T-RANDOM-EDIT", "Seeded mix: 35% push, 15% pop, 15% insert, 15% ordered remove, 10% swap-remove, 10% replace."),
    ("T-BULK", "Append two owners, clone/extend, split_off, clear, and reuse capacity."),
    ("T-COMPACT", "Retain alternating and seeded 10%, 50%, and 90% survivor patterns; eager extract and splice."),
    ("T-SORT", "Stable and unstable sort over random, sorted, reverse, organ-pipe, and 90%-duplicate keys."),
    ("T-GROW-FAIL", "Inject failure at every capacity arithmetic/allocation point and verify unchanged precommit state."),
    ("T-SMALL", "W-SMALL lengths 0..32 crossing inline/heap boundary."),
    ("T-GAP", "W-GAP cursor-local edits at front, middle, and back with one final materialization."),
]


SCALES = [0, 1, 4, 15, 16, 17, 64, 1024, 65536]


TARGETS = [
    {
        "id": "TARGET-AARCH64-DARWIN",
        "triple": "aarch64-apple-darwin",
        "data_layout": "Resolve from the exact candidate LLVM module and require equality across candidates before scoring.",
        "machine": "FVV39V0J1W; Darwin 25.5.0; arm64 T8132; macOS 26.5.1 build 25F80",
        "measurement": "TIMED_AND_STRUCTURAL",
    },
    {
        "id": "TARGET-X86_64-LINUX-PENDING",
        "triple": "x86_64-unknown-linux-gnu",
        "data_layout": "Must be frozen from the exact LLVM target and equal across candidate/reference modules before scoring.",
        "machine": "BLOCKED_PENDING_EXACT_MACHINE_KERNEL_LIBC_ALLOCATOR_IDENTITY",
        "measurement": "TIMED_REQUIRED_FOR_ARCHITECTURE_GENERAL_SELECTION",
    },
    {
        "id": "TARGET-I686-STRUCTURAL",
        "triple": "i686-unknown-linux-gnu",
        "data_layout": "Resolve from the pinned LLVM target and record pointer/index widths.",
        "machine": "No timing runner frozen; compile/layout/soundness boundary only.",
        "measurement": "STRUCTURAL_ONLY",
    },
]


META5_ROWS = [
    ("META-C-ATOMIC", "C-ATOMIC-TRANSITIONS", "generic checked storage-transition surface", "New state-transition and preservation rules; no exact-use or cleanup rule.", "Grammar additions depend on chosen surface and are frozen before candidate construction.", "Checker validates sealed transition preconditions and owner/live-set postconditions.", "Generic transition lowering; no container-specific recognition."),
    ("META-C-LINEAR", "C-LINEAR-REBUILD", "exact-use rebuild scope and proof-state surface", "New exact-use ownership mode and complete normal-exit consumption law.", "At least one exact-use binder/type marker and transition form; exact spelling remains an owner decision.", "Flow checker covers fallthrough, return, break, give, try, callbacks, joins, and helpers.", "Proofs erase; relocation lowers directly."),
    ("META-C-REPAIR", "C-DERIVED-REPAIR", "typed repair scope", "New compiler-derived normal-exit cleanup semantics and elaborated cleanup visibility.", "At least one repair-scope form; exact spelling remains an owner decision.", "Checker derives one repair/destruction action for every normal abandonment edge.", "Emit explicit cleanup blocks; no unwind cleanup."),
    ("META-C-PROOF", "C-PROOF-CARRYING-STATE", "state-indexed storage/proof surface", "New state-indexed type/proof rules and valid-owner boundary law.", "Proof binder, state proposition, and transition forms; exact spelling remains an owner decision.", "Type/proof checker establishes live-set arithmetic and complete-boundary propositions.", "Erase proofs; lower state transitions directly."),
    ("META-C-RUNTIME", "C-RUNTIME-TOPOLOGY", "sealed topology-owner surface", "New sealed Dense/Hole topology relation and fact-channel rules.", "Generic topology-owner and checked transition forms; exact spelling remains an owner decision.", "Checker prevents metadata/payload separation and validates owner-rooted range facts.", "Steady Dense state and proofs may erase only from machine-verified derivations."),
]


def members_for_text(cluster_id: str, text: str) -> list[str]:
    """Choose exact member adapters from an evidence or selector child string."""
    members = CLUSTER_MEMBERS[cluster_id]
    if len(members) == 1:
        return list(members)
    lowered = text.lower()
    matches = []
    for needle, member in SPECIAL_MEMBER_MATCHES.items():
        if member in members and needle in lowered and member not in matches:
            matches.append(member)
    return matches or list(members)
