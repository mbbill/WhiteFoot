# Minimal reborrow relaxation — proposed rule (DRAFT, not yet a spec change)

Status: DRAFT proposal for the narrow-relaxation direction (owner-selected 2026-07-18).
This is the anchor artifact the model-check, the Featherweight-Rust (FR) reconciliation,
and the hostile no-alias review verify against. It is NOT a spec edit; the kernel spec is
owner-gated and changes only after the evidence is in and the owner approves the exact
delta (see `governance/APPROVALS.md`).

Design intent: admit exactly the fragment of reborrowing that wfc uses — a transient,
non-escaping child borrow passed as a call argument — and nothing more. Every harder form
(bound children, returned/given children, result-carrying children, uniq→shared downgrade,
loan-after-holder-move) is DEFERRED, so the open obligation and the checker surface stay
small. See `DOSSIER.md` for why this fragment is the recommendation.

## 1. Scope — what is admitted

A **statement-scoped child reborrow** is the written expression

    &uniq 'c deref(h)[suffix]        (uniq child)
    &'c   deref(h)[suffix]           (shared child)

that appears **only as a call argument**, where `h` is a live borrow holder (`&uniq` or
`&`), `'c` is a region that cannot outlive the enclosing statement, and `[suffix]` is a
possibly-empty place projection (fields / literal or variable indices).

Admitted iff ALL hold:

1. The reborrow expression is an **unbound call argument** — it is not bound by `let`, not
   the initializer of a `set`, not `return`ed, not `give`n, and not the whole call result.
2. A **uniq** child requires a **uniq** parent (`h` must be `&uniq`). A shared child is
   allowed from either.
3. Sibling children created in the same statement are compatible under OWN-5/OWN-7 on
   resolved places: any overlapping pair **containing a uniq child is rejected**; shared
   siblings may overlap; disjoint places (distinct fields, or index places that are not
   both non-literal and not both equal literals) are legal.

## 2. Effect on the holder — suspension

Creating a child reborrow of `h` **suspends** `h` and every transitive ancestor of `h`
(if `h` is itself a child) for the duration of the enclosing statement. While a place is
suspended:

- no read, write, move, copy, or call-transfer through it is permitted; the sole allowed
  operation is creating a further sibling child in the same statement (judged per §1.3);
- `h` **resumes** at the end of the enclosing statement, after its last child's borrow
  ends. There is no earlier resumption, because the child cannot be bound and therefore
  cannot end before the statement.

`resolved(child) = resolved(h) ++ suffix`. All OWN-5/OWN-7 judgments continue to use
resolved places. Singleton provenance (T-A) is retained: the child has one immutable
resolved root; lineage branches but is never retargeted, merged, or reassigned.

## 3. What is forbidden — and why each is load-bearing for `noalias`

The no-alias fact F001 requires: **at most one usable mutable path to any place at any
instant.** Each forbiddance below closes a way that invariant could break.

| Forbidden | Rule that rejects it | Why it would break `noalias` |
|---|---|---|
| Two overlapping `uniq` siblings | §1.3 overlap bar | Two usable `&uniq` to the same place at once |
| `uniq` child from a `shared` parent | §1.2 | A shared alias would coexist with a fresh `uniq` write path |
| Any access through a suspended parent | §2 suspension | Parent + child = two usable mutable paths |
| A child bound / returned / given / stored | §1.1 unbound-argument | Child would outlive the parent's suspension; two live paths |
| Resumption before the last child ends | §2 resume-at-statement-end | Parent would become usable while a child path is live |

Because the child is an unbound argument, it structurally cannot escape: functions return
`own` only (never a borrow), structs hold values not borrows, and there is no binding to
carry it past the statement. This is the property the map phase verified holds for 100% of
wfc's ~1,062 reborrow sites.

## 4. `noalias` re-derivation (the fact-channel claim to be reviewed)

Old premise (v0.6): `noalias(x)` because `x`'s provenance is a singleton **with no
lineage**.

New premise (this rule): `noalias(child)` because the root is singleton **and** every
ancestor is suspended (no usable path through them) **and** every overlapping `uniq`
sibling is rejected. During the child's life the child is the sole usable mutable path to
its resolved place; after statement end the child is gone and the parent resumes as the
sole path. Authority moves *down* the ownership tree and back up, never forks.

This re-derivation is a strictly more complex predicate than the old one and MUST pass the
hostile fact-channel review (step 3 of the program) before any spec change. A green checker
is not that review.

## 5. Decidability / checker cost

The admitted fragment is syntactic and local:

- recognize the written form `&uniq 'c deref(h)[suffix]` / `&'c deref(h)[suffix]` in call
  argument position;
- set a suspend flag on `h` (and its ancestors) for the statement;
- reuse the existing OWN-5/OWN-7 resolved-place overlap check for sibling compatibility;
- clear the flag at statement end.

No dataflow fixpoint, no path-set typing, no inference. This is far smaller than the parked
branch's full design (which also carried OWN-14 result-transfer, downgrade, and
loan-after-move); those are deferred here.

## 6. Deferred (re-entry triggers recorded)

Not admitted by this rule; each returns for its own owner-gated review when a real writer
need is demonstrated:

- **Bound children** (`let c = &uniq 'r deref(h)...`) — needs child liveness beyond one
  statement.
- **Result-carrying children / reference-result provenance** (the parked branch's OWN-14) —
  a function returning a borrow derived from a borrow argument. wfc uses zero of these.
- **uniq→shared downgrade** and **loan-after-holder-move** — the parked branch's harder
  clauses; wfc exercises none.

## 7. Obligation discharge plan (what turns this draft into an approvable delta)

- **Model-check (OBL-4 item 1):** extend the soundness model-checker to generate the
  statement-scoped child-reborrow form and confirm no accepted program yields two
  simultaneously-usable overlapping mutable paths. The existing 10k-model clean run covered
  the pre-reborrow core only; this widened run is what actually discharges the fragment.
- **FR reconciliation:** reconcile against Featherweight Rust's `*w` reborrow restricted to
  singleton-rooted child lineages, showing the checker stays singleton-rooted (no lval-set
  retyping).
- **Pinned census:** fix one authoritative occurrence-aware count of the reborrow sites
  (the 989 `&uniq` + 73 shared enumeration is complete) so the evidence is not a moving
  number (GOV-2).
- **Hostile fact-channel review:** re-derive `noalias` under §4; attack the §3 escape
  clauses directly in the sequential setting (do not assume safe by analogy to the parked
  branch); recommend encoding the suspension invariant structurally (e.g. a checker
  assertion that no two live `uniq` borrows have overlapping resolved places unless one
  derives from the other).

## 8. Eventual spec delta shape (owner-gated; drafted only, not applied)

If the evidence holds and the owner approves: bump `kernel-spec-v0.6.md` → `v0.7`, rename
the file, update the title and all live references in one change. The delta is confined to
OWN-5 (a child-creation exception), OWN-6 (the suspension clause and the statement-scoped
child definition), and PATTERNS P4 (no-reborrow → bounded-statement-scoped-reborrow). **No
new numbered rule** (no OWN-14). Record the approval and the evidence pointer in
`governance/APPROVALS.md` and `decision-gates.md`.
