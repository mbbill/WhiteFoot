# Kernel deltas — RESEARCH DRAFT (not production spec)

Status: RESEARCH DRAFT under D15/D16. This file drafts four kernel deltas in
kernel-spec voice from the D18-R3 flag list; it is NOT the production spec and
changes nothing in `kernel-spec-v0.6.md`, which remains untouchable pending the
owner's separate landing review. Rule IDs here are draft namespaces (`CONC-*`,
`TBLCLONE-1`, `LOAD-*`, `DOM-1`), not ratified kernel IDs. Every interaction
claim is checked against `kernel-spec-v0.6.md` and `../m1-loan-judgment/
RULES-RATIFIED.md` (the ratified 15 loan rules R1-R15). One numbered rule per
judgment. Each delta carries: rule text, admission rationale (D16), interactions,
checker cost, open questions, and a hostile-review flag.

D16 admission bar (used below): a sealed built-in is admitted only when ordinary
users cannot reach par performance from the language primitives and checked
libraries, AND a named 51-map consumer or corpus operation needs it.

---

## Delta 1 — CONCURRENCY BINDINGS (v3; rebuilt on the CONC-0 memory model)

> **HOSTILE-REVIEW FLAG (whole delta).** The v2 draft was ruled NOT ADOPTABLE by
> three reviews (`evidence/conc-review.json`): the shape (static capabilities, a
> closed set of sealed synchronization points, trap = abort) is right, but it was
> built on a memory model the kernel does not contain, and its checker-side rules
> admitted three data races the draft claimed closed. This v3 rebuild puts the
> memory model FIRST (CONC-0) and repairs every FATAL/MAJOR finding; each repair
> is marked [CONC-V3-n]. Nothing here ships without a fresh full re-attack on this
> text — every fix (spawn's capture-loan clause, the Shareable induction,
> guard_uniq's issue clause, the R15 concurrency schema) is itself new
> fact-channel surface. Rule IDs remain draft namespaces; the memory-model clauses
> MM-0..MM-10 and the amendments AMD-7/AMD-8 are PROPOSED kernel/ratified-rule
> additions requiring owner ratification (see Escalations).

### CONC-0 — The memory model (the foundation; a proposed kernel addition)

[CONC-V3-1] D1 ("data-race impossibility") is stated as a LAW (CAP-1) but the
kernel defines no data race, no happens-before, and no meaning for the
release/acquire CQ-6 asserts. Every sealed-form soundness argument therefore has
no reduction target, and even the flagship walks' "parent reads a child's writes
after join" correctness is unstatable. CONC-0 is the minimal happens-before
statement the kernel must add so D1 becomes CHECKABLE. It is the REDUCTION TARGET
every sealed-form R15 proof discharges to: a sealed author proves "my internals
establish these synchronizes-with edges," and CONC-0 turns those edges into the
absence of a data race. The eleven clauses:

- **MM-0 Definitions and the theorem.** A *location* is a range of bytes of a
  language-managed object. Two accesses *conflict* iff they touch overlapping
  locations and at least one is a write. *happens-before* (HB) is the transitive
  closure of program order within one thread plus the closed *synchronizes-with*
  edge list MM-1..MM-6. A *data race* is a conflicting pair of accesses on
  distinct threads not ordered by HB. **D1 restated as a theorem:** an accepted
  program has no data race on language-managed memory. The theorem is scoped by
  SCOPE-3: gated FFI frames, external writers of RO-mapped files, and TCB
  internals (allocator, scheduler, runtime) are excluded, and externally mappable
  bytes carry no optimizer facts (the member audit's map-row discipline).
- **MM-1 Spawn / publication edge.** Everything sequenced-before a `spawn['p]` in
  the parent happens-before the child body's first action; in particular every
  capture's initialization is published to the child. (Fixes the finding that
  capture publication had no normative basis.)
- **MM-2 Join edge.** Each child's last action happens-before the `scope 'p`
  exit that joins it (and before a `par` statement's return); an `Err`-returning
  spawn that never ran contributes the empty edge. This is what makes a parent's
  post-join read of a `&uniq 'p` split-view write, or of `got` after Walk 1,
  race-free.
- **MM-3 Mutex tenure order (the R15 O1-O4 schema).** Per mutex instance there is
  a total HB order of guard *tenures* (a tenure = `mtx_lock` return to the
  matching R7 unlock). **O1** process-wide tenure *exclusion*: at most one issued
  token is live per instance at every instant, thread-agnostic — a same-thread
  re-acquire must BLOCK or TRAP, never issue a second token (this outlaws a
  conforming recursive-lock implementation, the reviewers' aliased-`&uniq` race).
  **O2** `unlock`_i synchronizes-with `mtx_lock`-return_{i+1}. **O3** the interior
  address is stable across the whole tenure. **O4** a token is issued only on an
  acquiring path (`try`/`timeout` variants issue solely on their `Ok` arm).
- **MM-4 Queue publication.** `cq_send(v)` synchronizes-with the `cq_recv`
  returning that `v`; one release publish per batch covers all its items; the
  last-`cq_tx`-drop happens-before any `RecvClosed` observation; the last-`cq_rx`-
  drop happens-before any `QueueClosed(value)` ownership handback.
- **MM-5 Endpoint seriality (stated soundly).** All operations on one endpoint
  are HB-totally-ordered — derived from endpoint affinity, the `&uniq` receiver on
  every endpoint op, and the MM-1/2/3 edges on every legal transfer path
  (including migration through `mutex<cq_tx>`). `spsc` additionally has
  exactly-two-endpoint totality (the clone rows reject). **Sealed proofs may
  assume HB-seriality, NEVER thread identity** — this replaces CQ-3's literal
  "single-threaded by construction," which a `mutex<cq_tx>` serialized-send
  program (legal, see appendix) falsifies for any implementation keyed on thread
  id.
- **MM-6 Reclamation / epoch safety.** Every operation and drop on any endpoint
  happens-before the storage free performed in the last endpoint's drop; that free
  is unique (exact acq_rel reference counting — the `Arc`-drop shape); and the
  freeing thread's remaining-item drops observe every published item (MM-4). This
  is what makes CQ-5's cross-thread last-drop free not a double-free.
- **MM-7 Non-interference / effect opacity.** A sealed synchronization op is NEVER
  `pure`, and its effect on shared internal state is NON-ERASABLE: it survives
  region confinement (CAT-5a(ii) must not strike it). Concretely, a new EFF-1
  effect atom `sync` is introduced for exactly this; every sealed sync op
  (`mtx_lock`, `guard_uniq`, the guard/endpoint drops, and every `cq_*` op)
  carries `sync`, which no region-disjointness, CSE, DSE, code-motion, or purity
  fact may see through, and against which no reordering across the acquire/release
  direction is licensed. Requires-engine facts over shared-reachable state fail
  closed (generalizing CQ-6's no-occupancy-facts rule). (Fixes the derivable
  pure-rowed enqueue: an op whose only other effect `writes('e)` is confined by
  CAT-5a(ii) is still `sync`, so never pure.)
- **MM-8 Split views.** A `par`/`scope` split-unique slot and CONC-1's `&uniq 'p`
  captures partition their backing into byte-disjoint ranges; two split views of
  one place must not overlap (this is the loan-side disjointness the MM-2 join
  then makes readable).
- **MM-9 Trap ordering.** A trap happens-before any effect of the violating
  operation, and the abort path performs no language-visible write (the general
  SCOPE-4/EFF-4 clause CONC-4 needs, previously stated only per-op, e.g. OP-9).
  Surviving threads observe only pre-trap-valid in-process state during the
  bounded teardown window; external (persisted/peer) state receives power-loss-
  prefix semantics, gated by a MANDATORY abort-mid-scenario fault-injection
  battery. The no-user-signal-handler invariant (only the sealed sticky-flag
  handler runs; `signals_general` deferred) is a load-bearing premise.
- **MM-10 Target mapping.** `release`/`acquire`/`acq_rel` are pinned to the
  C11/LLVM memory orderings with a per-target lowering proof; arm64 is the honest
  stress bed (Chase-Lev / Vyukov fence audits run under that mapping — the member
  audit's deque note).

**The per-form obligation list the CONC hostile-review MODEL phase must discharge**
(attached by BEHAVIOR — "the body may access state reachable from another live
binding or thread" — not by loan class, so it reaches loan-NONE brand-carriers):
`mtx_new`, `mtx_lock`, `guard_uniq`, the guard drop; all ten `cq_*` rows, both
`cq_tx_clone`/`cq_rx_clone`, the compiler-derived endpoint drop bodies, and
`cq_new`. For each: the O1-O4 tenure/handoff facts (MM-3) where it issues or
releases exclusion, the MM-4/MM-5 publication/seriality facts where it hands data
across a boundary, and the MM-6 reclamation facts where it frees shared storage.

### [CONC-1] Scoped threads (rebuilt)

[CONC-V3-2] **Grammar.** `scope 'p { stmt* }` introduces a thread-scope region
`'p`. `spawn['p]<body_targs>(body, capture_list)` starts a child thread running
the named `fn body` (no closures [FN-5]; per-thread state is the env-struct
pattern). `body_targs` carries `body`'s explicit type/region/brand arguments in
TYPE-5 form (this is where a brand instantiation `'q := 'qa` is written — the v2
walk's hand-waved instantiation now has a spelling). `capture_list` is written
GRAM-11-named (`name: atom`) against `body`'s parameter list. `spawn` returns
`own Result<unit, SpawnError>`; add `enum SpawnError { Eagain(); }` to the
companion enums (`Eagain` is returned before the child ever runs).

[CONC-V3-3] **Persistent per-capture loan entries (the FATAL fix).** The v2 claim
that capture disjointness "is R14 statement-local mint-disjointness verbatim, no
new disjointness machinery, no new dataflow" is WITHDRAWN — it was false and
admitted the core race. R14/AMD-1 are sound only because the `par` STATEMENT
blocks until join; `spawn` returns immediately while the child runs, so AMD-1's
per-statement pseudo-entries evaporate at the spawn statement's end and an
un-let-bound capture borrow is an OWN-6 call-scoped temporary dead before the next
statement. Replacement rule: **each borrow capture of `spawn['p]` issues a loan
entry on the captured place — kind `shr` for a `&'p` capture, kind `uniq` for a
`&uniq 'p` capture — held by a compiler-introduced SCOPE HOLDER (one per `scope`),
removed only at `scope 'p` exit (the join).** This is declared as `spawn`'s
form-table loan clause (satisfying R15's fail-closed letter — an undeclared
`spawn` was, by that letter, uncallable). A capture borrow's liveness is to scope
exit by OWN-4 named-region liveness (the capture is at region `'p`, live to the
end of `'p`'s block), which DISAPPLIES OWN-6's statement-temporary reading for
spawn captures. All later parent statements and later spawns are then governed by
these entries via R5/R6/OWN-5: a `set` over, or a `&uniq`/own re-access of, a
place under a live capture entry rejects (R6/OWN-5); a second `&uniq 'p` capture
of the same place rejects (R5 uniq-overlap); two `&` captures coexist (shr).
`own` Sendable captures are moved into the child and consumed at the spawn.

[CONC-V3-4] **Scope exit is EVERY leaving edge, join-before-drop (the second
FATAL fix).** "`scope` exit" is defined as every control-flow edge leaving the
scope block — fallthrough, `break` to an outer label, and `return` — matching
STOR-3's edge enumeration. On each such edge the join of all children executes
FIRST, before that edge's R7/STOR-3 releases and drops. This closes the
`return`-out-of-scope UAF (a child holding a `&'p` borrow into a frame the return
would otherwise pop): the frame's drops cannot run until every child has joined,
and the capture entries (CONC-V3-3) are live across the whole block, so no leaving
edge can free a captured place under a live child.

[CONC-V3-5] **Publication edges.** By CONC-0 MM-1 the spawn statement is a release
edge from the parent to the child body's entry (publishing every capture); by MM-2
each child's body exit is a release edge acquired by the scope-exit join (so a
`&uniq 'p` capture's child-side writes are visible to the parent after the join,
and the MM-8 split-disjointness makes them non-conflicting during the run). These
are the two edges every scoped-thread program rides on; they are added to the
open-flag memory-model pin list.

[CONC-V3-6] **Scope effect row (the restriction bug fixed).** The v2 "each body's
row restricted to `'p` and to `heap`" was wrong twice: EFF-1 cannot even spell
"restricted to `'p`" in the enclosing signature (`'p` is not in scope there), and
it dropped a child's writes to OUTER regions (a child writing through a `&uniq 'b`
capture rooted at a caller borrow) from the row, hiding a cross-thread write
channel (EFF-2 both-ways). Replacement: **the `scope` statement exhibits the
UNION of each body's row instantiated at the actual capture regions, plus
`allocates(heap)` (child stacks) and `sync` (MM-7), dropping ONLY regions
introduced inside the scope or a body** (the CAT-5a(ii) discipline). Effects on
caller-supplied or enclosing regions never drop.

[CONC-V3-7] **Loop-spawn: an honest restriction for this delta.** OWN-11 forbids
naming an outer region in a `loop @l` body and forbids moving an outside binding
into the loop (copies exempt), so `spawn['p](worker, &'p shared)` and a
move-capture of an outer own value both REJECT inside a loop. This delta therefore
admits, inside a loop, only COPY-own captures and captures of loop-body-local
regions — runtime-count fan-out that SHARES outer state is not spellable, and the
D16 admission claim is corrected to the fixed (straight-line) fan-out it actually
covers. The carve-out (admit `&'p` captures per iteration at the enclosing scope
region — sound because the CONC-V3-3 scope-local capture entries enforce
cross-iteration disjointness and the join precedes `'p`'s end) is a FUTURE delta,
gated on those entries and on an OWN-11 amendment. This is an owner escalation:
the named consumers 11/38/41/42/44 include N-worker data-parallel shapes that need
loop-spawn, so v1 either accepts fixed fan-out or authorizes the carve-out now.

[CONC-V3-8] **A capture is a thread-boundary position, not an R2 call argument.**
The v2 "guard is never-Sendable BY R2 derivation" was textually false: R2 permits
a confined value as a call argument, and CONC-V2-1 itself modeled a capture as a
body-fn argument. Corrected normative rule: a `spawn`/`par` capture is a
THREAD-BOUNDARY position, NOT an R2 call-argument position; any capture whose type
is confined (a form-table opaque token OR a user `confined(...)` type per R1)
rejects at the capture citing CONC-2 (a stipulated CONC rule — new authority —
not an R2 corollary). The R6 second-thread-shares-the-interior argument is dropped
here (it mis-cited the loaned place; see appendix Walk 2).

Admission (D16): thread lifecycle at par is unreachable from primitives (no thread
primitive exists, CAP-1); named consumers are the concurrent 51-map scenarios and
the member audit's five canonical programs — with the loop-spawn coverage
correction (CONC-V3-7). Checker cost (re-costed, NOT "no new dataflow"): a new
per-scope capture-entry pass adding scope-local disjointness — O(captures x
later-statements-in-scope) loan-table checks, plus the join-on-every-exit-edge
wiring; genuinely new machinery, bounded and fixpoint-free.

### [CONC-2] Send/Share capability judgment (rebuilt: total structural induction)

[CONC-V3-9] `Sendable` and `Shareable` are BUILT-IN structural predicates (the
Int/Float closed-conformer precedent), NEVER user-conformable — CQ-1/CQ-3's
"conform Sendable" wording is amended in the same landing to "the built-in
Sendable predicate holds." The judgment is computed by a TOTAL structural
induction over the whole post-monomorphization type graph, a memoized
greatest-fixpoint (assume-holds-on-cycle) so recursion through `box<List>`
terminates. The headline is corrected: the judgment is DERIVED for the
loan-token / brand-carrier / ordinary-structural classes and STIPULATED-with-
obligation for the sealed-synchronizer class — not a uniform per-form read-off.
Every capture and every `par`/`spawn` slot consults it; **anything not matched by
a row below is fail-closed: neither Sendable nor Shareable.**

| type | Sendable | Shareable |
|---|---|---|
| primitive, tag-only enum | yes | yes |
| user `struct` | iff every field Sendable | iff every field Shareable |
| user `enum`, `Option<T>`, `Result<T, E>` | iff every payload Sendable | iff every payload Shareable |
| `array<T, N>` | iff `T` Sendable | iff `T` Shareable |
| `box<T>`, `buffer<T>`, `seq<T, N>`, `table<K, V, h>` | iff every payload Sendable | iff every payload Shareable |
| `cq_tx<'q,T>`, `cq_rx<'q,T>`, `cq_ends<'q,T>` (brand-carrier) | iff `T` Sendable [CQ-3] | never [CQ-3] |
| `mutex<T>` (sealed synchronizer, CONC-3) | iff `T` Sendable | iff `T` Sendable — STIPULATED |
| `slice<'r,T>`, the flagged `uslice<'e,T>`, `ahdl<place,T>` | fail-closed (deferred, v1) | fail-closed (deferred, v1) |
| any `confined(...)` type (form-table token OR user) | never | never |

[CONC-V3-10] Justifications, by class:
- **Ordinary structural (Shareable = every-payload-Shareable, replacing "deeply
  immutable").** Sound because non-confined forms have no interior mutability
  under `&` (OWN-5 makes a shared borrow read-only for its duration); the vacuous
  "no interior `&uniq` reachable" predicate is deleted. The interior-mutability
  types (`mutex`, `conc_queue`) are the exceptions and carry their own rows, so
  `seq<mutex<u64>, N>` is Shareable iff `mutex<u64>` is (the striped-lock ACCEPT,
  appendix), NOT falsely excluded.
- **Confined = never (repartition by R1, not "ordinary owned").** ANY confined
  type — a form-table opaque loan token (guard, cursor) or a USER `confined(uniq)`
  /`confined(shr)` struct/enum carrying a borrow-typed or confined field — is
  never Sendable/Shareable, a STIPULATED thread-boundary rule (CONC-V3-8). The v2
  partition wrongly filed a user confined struct as "ordinary owned," which had no
  row.
- **Sealed synchronizer = stipulated with obligation.** `mutex<T>` Shareable iff
  `T` Sendable is NOT a structural read-off (the ordinary rule would say NO — an
  interior `&uniq` is reachable via `mtx_lock`); it is the tenure-exclusion
  property (MM-3 O1/O2) supplied only by the trusted proof. It is a NAMED third
  declaration class in AMD-6's taxonomy (sealed synchronizer), with `T` required
  Sendable at instantiation (CONC-3). The content matches the standard judgment
  (Sendable iff `T` Sendable; Shareable iff `T` Sendable, never requiring `T`
  Shareable). Corollary: `mutex<cq_tx<'q,T>>` is Shareable, so serialized
  multi-thread use of one `spsc` producer is legal — sound only under MM-5's
  HB-seriality reading.

[CONC-V3-11] **Clone-row reconciliation.** CQ-3's "every endpoint op takes
`&uniq`" is false for the v0 `cq_tx_clone`/`cq_rx_clone` rows (`&` receivers), and
two threads reaching `&` to one shared endpoint could run the clone concurrently
on unsynchronized registration/count state. Fix (companion S.3 change, same
landing): **re-mode `cq_tx_clone`/`cq_rx_clone` to `&uniq` receivers**, restoring
CQ-3's invariant literally and making a concurrent clone unspellable by
construction (a `&uniq` receiver cannot be aliased across threads). The
alternative (keep `&`, add both rows to the behavior-based R15 obligation set with
a `sync` effect home) is recorded but not recommended — re-moding is the smaller
trusted surface. Either way both clone rows are inside the AMD-8 obligation net
(CONC-3).

[AMD-7, proposed] **Par/spawn slot capability premise.** Every `par` slot and
every `spawn` capture carries a capability premise ON TOP OF R14/AMD-1 loan
disjointness (both must pass): a replicate/`&` slot requires the referent
Shareable; a split-unique/`&uniq` slot requires the referent Sendable-and-
exclusively-transferred; an `own` slot requires the value Sendable. This is a
marked amendment to R14, counted as a rule change (the v2 walks used it unmarked).

### [CONC-3] Mutex — the full sealed form (rebuilt)

[CONC-V3-12] The v2 "guard is a confined loan token, no new loan machinery"
headline is WITHDRAWN. The guard needs a NEW interior-view loan clause, `mutex`
needs its formation rows, and R15 needs a concurrency schema — all new machinery.

**[AMD-8, proposed] R15 concurrency schema (behavior-based attachment).** R15 as
ratified obliges only per-invocation safety ("preserve interior addresses; safe
under concurrent invocation") — a per-invocation predicate that a conforming
recursive or reader-shared lock satisfies while admitting a race. Amend R15 so
that **every sealed op or compiler-derived drop whose body may access state
reachable from another live binding or thread** carries, by BEHAVIOR (not by loan
class, so it reaches the loan-NONE cq carriers), the obligations: MM-3 O1-O4 where
it issues/releases exclusion, MM-4/MM-5 where it hands data across a boundary, and
MM-6 where it frees shared storage. The mandatory per-form scope is the CONC-0
list. A green checker is not this proof.

**Mutex form-table rows** (nine-column S.4 discipline; `sync` per MM-7):

| op | signature | own | loan | effects | failure | facts | kills | cg |
|---|---|---|---|---|---|---|---|---|
| `mtx_new` | `<T>(v: own T) -> own mutex<T>` (`T` must be Sendable, else compile reject [CAP-1]) | consumes `v` | NONE | pure (frame init; no publication yet) | — | — | — | — |
| `mtx_lock` | `['m](m: &'m mutex<T>) -> own guard<'m, T>` | returns own guard | ISSUE uniq (interior) | `sync` [blocks, pending BLOCKS-EFFECT] | — (blocking, total) | — | — | CG-LOCK |
| `guard_uniq` | `['x, 'v](g: &'x guard<'m, T>) -> &uniq 'v T` | — | ISSUE uniq on source(guard-holder), result region `'v` (dedicated) | reads('x) | — | — | — | CG-INL |
| `mtx_try_lock` | `['m](m: &'m mutex<T>) -> own Result<guard<'m,T>, LockBusy>` | guard own-out on Ok | ISSUE uniq (interior) on the Ok arm ONLY [O4] | `sync` | Result: LockBusy | — | — | CG-LOCK |

`enum LockBusy { Busy(); }` (companion). Guard drop is a surfaced [STOR-3]
compiler-derived drop whose form-declared release is the UNLOCK; it removes the
interior-uniq entry, is blocked if any `guard_uniq` view entry on `g` is still
live (R7 overlapped-drop check), and its body is trap-free (MM-9).

[CONC-V3-13] **The interior-view clause (the third FATAL fix), a marked AMD-5
carve-out.** `guard_uniq` cannot use `issues uniq on source(receiver)` — AMD-5
declaration-rejects a uniq result — and the v2 "statement-scoped [R3]" story is
unspellable under GRAM-9 (a call result is not an atom, so it must be let-bound,
and a let-bound `&uniq 'm` view lives to `'m`'s end and can be returned or `give`n
past the unlock). Replacement: **`guard_uniq` issues a uniq loan ENTRY on the
GUARD HOLDER's place (entry `(g, uniq, view)`), and returns the interior as
`&uniq 'v T` where `'v` is a DEDICATED result region strictly inside `g`'s life
(the `pool_entry` pattern), never `'m`.** Consequences: the entry FREEZES `g`
(R6), so a second `guard_uniq` (a second uniq issue overlapping `g`) rejects —
exactly one live interior view, restoring OWN-9 noalias; the guard's R7 unlock is
blocked while a view entry is live (R7 overlapped-drop check); and because the
view is at the locally-introduced `'v`, it can never be returned or `give`n past
the guard (R13/GIVE-1/OWN-4 reject a borrow at a locally-introduced region). This
is new loan machinery, carried as a marked AMD-5 carve-out (owner escalation:
AMD-5 was a D18 tightening). The interior address is stable across the view by
MM-3 O3.

Admission (D16): a lock-protects-data guard with compiler-derived, un-leakable,
single-view unlock is unreachable from primitives; named consumer is scenario 40
and every shared-state server/DB scenario. Checker cost: one loanable sealed form
plus the interior-view clause under R15/AMD-8's obligation table; no new judgment
kind beyond the view clause.

### [CONC-4] Child trap is a whole-process abort (reworded on MM-9)

[CONC-V3-14] D18 ruling 2 makes a runtime safety trap terminate the WHOLE
process; SCOPE-4/EFF-4 make it abort with no unwinding and no cleanup. The v2
argument's conclusion holds but three premises were wrong or unstated; reworded:

1. **A trapping child runs no drops** (SCOPE-4/EFF-4: abort, no unwinding, no
   cleanup), so it reaches none of its R7 scope-end releases.
2. **No thread ever returns from a join or observes a trap as a value.** (The v2
   "the parent is torn down at the same instant" was false — SIGABRT hits the
   trapping thread and siblings run for a bounded scheduling window.) The join is
   sound not by instantaneity but because there is no trap-value channel out of a
   child and the abort is process-wide: no join returns after a child traps, and
   MM-9 gives "a trap happens-before any effect of the violating operation; the
   abort path performs no language-visible write."
3. **Surviving threads observe only pre-trap-valid in-process state during the
   bounded teardown window**, and no thread reaches its R7 drops on the abort
   path. Skipping every teardown is sound for PROCESS MEMORY specifically: no
   surviving in-process observer exists (cross-process shared writable maps are a
   ratified v1 non-goal; the sealed sticky-flag signal handler is the only code in
   the window, benign by the no-user-handler invariant).
4. **External (persisted/peer) state is NOT inert** — an in-flight `pwrite`/
   `net_sendv` issued before the trap can land after it, and a sibling mid-syscall
   can complete a partial write in the window; external state receives
   power-loss-prefix semantics, and this MANDATES the abort-mid-scenario
   fault-injection battery (the KV WAL-recovery path is the consumer). The claim
   is scoped to the pinned OS targets.

Implication (unchanged): guard unlock and CQ-5 drain-on-drop are NORMAL-exit R7
actions; the abort path bypasses them and by (3) needs to; a drain-on-drop or
unlock body must be trap-free on the normal path (an R15/AMD-8 obligation).

### Delta-1 open flags (what the model phase still owes)

[CONC-V3-15]
1. **MM-0..MM-10 must land as KERNEL text** — the whole of CONC-0 is a proposed
   kernel memory-model addition, including the new `sync` EFF-1 effect atom
   (MM-7) and the MM-10 target-mapping proofs; D1 is uncheckable until it does.
2. **AMD-7 and AMD-8 need owner ratification** (they amend ratified R14 and R15),
   as does the AMD-5 carve-out for `guard_uniq` (CONC-V3-13).
3. **The per-form model proofs** (the CONC-0 list) — the R15/AMD-8 obligations
   discharged per form (`mtx_lock`/guard drop, all ten `cq_*`, both clone rows,
   endpoint drops, `cq_new`) — are the hostile-review MODEL phase's job; none is
   discharged here.
4. **The abort-mid-scenario fault-injection battery** (MM-9) is required before
   any WAL/peer-durability claim.
5. **Effect-row companion changes** in the same landing: the `sync` atom on all
   `cq_*`/mutex rows (correcting the 5.5 `writes('q)`-strike so it can't yield a
   pure enqueue), and the clone-row `&uniq` re-mode (CONC-V3-11).
6. **Spec-mass budget.** The honest kernel-rule count is ~11 (scope/spawn,
   capture-entry persistence, exit-edge join, scope effect row, Sendable class,
   Shareable structural recursion, the AMD-7 boundary premise, guard + interior-
   view clause, CONC-4, the publication axiom) plus the full mutex form section —
   not the implied 4. The always-loaded set is already ~78-90% of the ~48k budget;
   verbatim adoption of this delta likely busts it, so a normative-only cut
   (rule text + form rows; rationale and walks to the review record) with a
   measured token count is required before landing.

### Delta-1 regression appendix (v3)

[CONC-V3-16] The three FATAL programs now REJECT (firing clause named):

- **F-race-1: two-spawn `&uniq` overlap / spawn-then-parent-write.**
  `scope 'p { let s1 = spawn['p](writer, x: &uniq 'p a); let s2 = spawn['p](writer,
  x: &uniq 'p a); }` — REJECT: the first spawn issues a persistent `(a, uniq,
  scope-holder)` entry live to scope exit (CONC-V3-3); the second `&uniq 'p a`
  capture is a uniq issue overlapping a live uniq entry — R5/OWN-5 reject. The
  variant `spawn['p](reader, x: &'p a); set a = 2_u64;` REJECTS at the `set`: a is
  under a live shr capture entry, R6/OWN-5 forbid the write.
- **F-race-2: container-Shareable endpoint-clone race.** mint `cq_new<u64, mpmc,
  2>()`, push `tx` into `sq: own seq<cq_tx<'qa,u64>, 4>`, then `scope 'p {
  spawn['p](toucher, sq: &'p sq); spawn['p](toucher, sq: &'p sq); }` where
  `toucher` clones an element — REJECT: `seq<cq_tx<'qa,u64>,4>` is Shareable iff
  `cq_tx` is Shareable (CONC-V3-9 compositional rule), and `cq_tx` is never
  Shareable (CQ-3), so `seq<cq_tx>` is not Shareable; the replicate-`&` capture
  fails the AMD-7 capability premise. Independently the clone `&uniq` re-mode
  (CONC-V3-11) makes a concurrent clone unspellable.
- **F-race-3: guard interior-view escape.** `fn peek['m,'x](g: &'x guard<'m,u64>)
  -> &uniq 'm u64 { let r = guard_uniq(g); return r; }` then a `give`/`return` of
  the view past the guard drop — REJECT: `guard_uniq` now returns `&uniq 'v u64`
  at a dedicated locally-introduced `'v`, and returning/`give`-ing a
  locally-introduced-region borrow fails R13/GIVE-1/OWN-4; the `peek` signature
  `-> &uniq 'm` no longer type-checks against the `'v` result. The single-threaded
  two-view variant (`let v1 = guard_uniq(g); let v2 = guard_uniq(g);`) REJECTS:
  the second `guard_uniq` issues a uniq entry overlapping the live `(g, uniq,
  view)` entry (CONC-V3-13). An early guard drop under a live view REJECTS at R7's
  overlapped-drop check.

Reviewer walks added:
- **Cross-function re-lock REJECT.** `let g1 = mtx_lock(&'m m); helper(&'m m);`
  where `helper` calls `mtx_lock` again — REJECT under MM-3 O1 (process-wide,
  thread-agnostic tenure exclusion: a same-instance re-acquire must block or trap,
  never issue a second token). This is the race a per-invocation R15 accepted.
- **seq<mutex<u64>, 4> striped lock ACCEPT.** Replicate-`&` capture of the stripe
  array into par bodies, each locking its stripe — ACCEPT: `seq<mutex<u64>,4>` is
  Shareable iff `mutex<u64>` is, and `mutex<u64>` is Shareable (`u64` Sendable);
  AMD-7 replicate premise passes.
- **mutex<cq_tx> serialized-send.** `mutex<cq_tx<'q,u64>>` shared `&'p` across a
  scope, each thread locking then sending on the one `spsc` producer — ACCEPT,
  sound only by MM-5 HB-seriality (mutex tenures chain HB edges via MM-3 O2), NOT
  by CQ-3's literal single-threaded reading.

Three original walks (verdicts preserved, citations corrected):
- **Walk 1 two-thread pipeline** (spawn + endpoint move + loop send + join):
  ACCEPT — now with the CONC-V3-2 spawn grammar giving the `'q := 'qa`
  instantiation a spelling, MM-1/MM-2 supplying publication, and the endpoint an
  `own` Sendable capture; BRAND-MINT/SEALED-MATCH-gated.
- **Walk 2 guard-across-threads forgery** (`spawn['p](worker, g: move g)`):
  REJECT at CONC-V3-8 (a capture is a thread-boundary position; a confined
  loan-token type rejects there — CONC-2 rule, not R2). The `&'p g` variant
  rejects at R3 (a borrow minted from a live confined binding is statement-scoped,
  unspellable as a `'p`-persistent capture) plus the CONC-2 never-Shareable row —
  the v2 R6 citation is dropped (R6 governs the mutex interior, not borrows of the
  holder `g`).
- **Walk 3 replicate-shared par mutex capture:** Direction A (`u64` Sendable, so
  legal) ACCEPT — each body locks inside; mtx_lock's `sync` effect is NOT a
  "write through a replicated slot" in R14's sense (R14's no-writes clause refers
  to loan-judged source writes; R15/AMD-8-certified sync internals are the
  reviewed exception), so the replicate-`&` capture stands. Direction B (`T` not
  Sendable, so rejected) REJECT at the CONC-2 `mutex` row via the AMD-7 replicate
  premise.

### Escalations (decisions for the owner)

[CONC-V3-17] Prominent — cannot be made sound at the draft level alone:
- **CONC-0 is a kernel memory-model addition.** D1 cannot be made checkable
  without MM-0..MM-10 landing as kernel text (plus the new `sync` effect atom).
  This is the foundational decision the whole delta waits on.
- **OWN-11 spawn-in-loop.** As restricted (CONC-V3-7) this delta does NOT spell
  the N-worker data-parallel fan-out its D16 admission names (scenarios
  11/38/41/42/44). Decide: accept fixed fan-out for v1, or authorize the OWN-11
  capture carve-out now (it is sound under the CONC-V3-3 entries but amends a
  ratified region rule).
- **Ratified-rule amendments:** AMD-7 (R14 slot capability premise), AMD-8 (R15
  concurrency schema), and the AMD-5 carve-out for `guard_uniq` all amend ratified
  text and need the same ratification path as AMD-1..5 (D18).
- **Clone-row re-mode** (`cq_tx_clone`/`cq_rx_clone` to `&uniq`) is a behavioral
  change to a landed catalog row; confirm before the companion S.3 landing.
- **Budget:** verbatim adoption likely busts the ~48k always-loaded budget; a
  normative-only cut with a measured count is required before spec.

---

## Delta 2 — `tbl_clone` row for S.2

### [TBLCLONE-1] Whole-table clone

New S.2 `table` row:

`tbl_clone['r](t: &'r table<K, V, h>) -> own table<K, V, h>` — deep-COPIES the
whole table and returns a FRESH, independent owner. [DELTA-FIX-4] K and V must be
COPY (OWN-1) — the enforceable predicate, identical to `seq_extend_copy`'s "T
copy required", NOT an undefined "clone" (v0 has only copy/affine and no Clone
contract); an affine K or V is a compile-time reject citing this row and OWN-1.
loan NONE; own: returns own (a new table, `t` unchanged); effects `reads('r),
allocates(heap), traps`; failure `trap "table capacity overflow"` [TBL-4] on the
fresh bucket-array byte-size overflow, OOM per [CAT-6]; facts `LEN(r)=LEN(t)
(link)` — a relational len-link matching the `seq_as_slice` "LEN(r)=LEN(s)
(link)" precedent [CAT-2], not a `len=value` fact; kills nothing on `t`; cg
`CG-CLONE`. The hasher instance state (`sip_keyed` k0/k1) transfers, so equal
keys hash equal in the clone (normative, not optional). No loan is issued or
consumed — the result is a plain owned value.

Cost: O(n), a control-byte + slot bulk copy at DRAM bandwidth (~1-2 ns/entry,
`evidence/microbench/RESULTS.md`). `CG-CLONE`: at most one growth-free bulk
`memcpy` region.

FUTURE WORK (NOT this delta) [DELTA-FIX-4]: an owning-value (heap V, bytes K)
whole-table clone is BLOCKED on a separate Clone-contract delta that first adds a
checkable Clone capability predicate plus a per-type deep-clone conformer (and a
byte-buffer clone for bytes keys), and passes its own review; its measured cost
is ~30-3000 ns/entry by value size (same source). A shallow "share the values"
fallback is a double-free and is excluded — do not lower an owning-V clone to
anything in v0.

Interactions: **[TBL-4]** (rehash/overflow discipline reused for the fresh
array), **[CAT-6]** (OOM stance), **[CAT-2]** (produces the LEN(r) link, touches
no fact on `t`), **[OWN-1]** (the copy K/V predicate is the enforceable rule). No
loan-rule interaction (loan-free row; a clone under a live loan on `t` is sound —
R6 blocks the clone-under-uniq-token case, and a shared loan coexists read-only,
both reviewer-confirmed). Admission (D16): a bulk-copy whole-table clone is
unreachable from primitives — a `for_each`-then-`insert` rebuild pays n hashes +
n probes (~10-40 ns/entry) versus ~1-2 ns/entry bulk copy, not at par; named
consumer is C5 COW-republish (the POD/handle regime, the clone IS the publish).
Checker cost: one row, no new judgment. Hostile review: light (no fact channel,
no loan).

---

## Delta 3 — Machine-core byte-load ops

### [LOAD-1] Endian-explicit byte loads

New OP-1 rows (machine-core intrinsics, admitted through the frozen-list
one-line rule): `load_le_u16`, `load_le_u32`, `load_le_u64`, `load_be_u16`,
`load_be_u32`, `load_be_u64`. Each: `(s: slice<'r, u8>, off: u64) -> own uK`
reads the `K/8` bytes at byte offset `off` and assembles a `uK` with the stated
endianness. Effect `reads('r), traps`. [DELTA-FIX-2] The out-of-range trap is
NEVER spelled `off + K/8 > len(s)` — that sum wraps at the u64 edge and would
admit an OOB read on an attacker-influenced near-max `off` even with elision OFF
(fail-closed does not save it). The runtime pass condition is `len(s) >= K/8 AND
off <= len(s) - K/8`: the subtraction `len(s) - K/8` is computed ONLY under the
first conjunct so it never underflows, and `K/8` is a monomorphization constant
(one subtraction). Equivalently, trap iff `len(s) < K/8` OR `off > len(s) - K/8`.
This exact non-wrapping form is pinned in the codegen corpus. **Bounds-trap
elidability**: the trap is discharged when the requires engine proves `off <=
len(s) - K/8` (same non-wrapping form) by a deterministic-checker discharge
[OP-4] — a `check` fact [OP-5], a `requires` prologue fact [FN-8], or the
length-domination fact [DOM-1(b)]; a solver may never promote it. **CG contract
[DELTA-FIX-2]**: a discharged load lowers to an LLVM `load iK, ptr, align 1` (the
unaligned / `memcpy`-to-temp idiom, per-target legalized), plus one `bswap` for
the big-endian rows. LOAD-1 needs NO alignment fact BECAUSE it lowers at align 1;
a strict-alignment target (e.g. arm64 strict-align) lowers to the safe byte-wise
sequence, never a natural-alignment assumption, and never a trap or UB. The
codegen corpus pins BOTH an x86-64 and a strict-alignment (arm64) asm-diff.

### [LOAD-2] `reinterpret` stays scalar-only

`reinterpret` [OP-8] is a same-width bit relabel of a REGISTER value
(`int<->float`, same-width `int<->int` resign), never a memory read at an
offset. It therefore cannot express a byte-slice `->` typed load, and the two
are disjoint and both required: `reinterpret` for register-level bit
reinterpretation, [LOAD-1] for offset reads out of borrowed bytes. Keeping
`reinterpret` scalar-only preserves its `pure` effect and its 1:1 lowering to
`bitcast`.

Interactions: **[OP-4]** (bounds discharge target), **[OP-5]/[FN-8]/[DOM-1]**
(the three discharge producers), **[OP-8]** (`reinterpret` unchanged),
**[TYPE-1]** (result types are the primitive `uK`). Admission (D16): byte
assembly (`index<u8>` + `ishl.wrap`/`ior` over K/8 bytes) is 4-8 instructions per
field versus 1 load — not at par; named consumers are C8 validated-view and
51-map scenarios 24 (serialization) and 27 (zero-copy typed views). Checker
cost: the bounds obligation `off <= len(s) - K/8` (non-wrapping [DELTA-FIX-2]) is
one linear range test the requires engine already performs for `index`; low. Open
questions: (a) a `store_le/be` writer counterpart (deferred to the same delta once
a writer scenario names it); (b) whether `off` as a compile-const should get a
stronger elision. (The former alignment open-Q is CLOSED as a correctness pin —
align-1 lowering above — not a performance note.) Hostile-review flag: LIGHT — the
base trap arithmetic is now non-wrapping [DELTA-FIX-2] and the only remaining
fact channel is the bounds discharge, shared with [DOM-1]'s review.

---

## Delta 4 — Length-dominates-bounds fact extension

### [DOM-1] Length-domination facts (the [OP-5]-deferred range vocabulary, first slice)

Two checked fact forms enter the stated-and-checked channel [OP-5] (whose
"loop invariants, ranges" vocabulary is explicitly DEFERRED there; this is the
first slice). Both are deterministic-checker discharges [OP-4], never
solver-promoted, and both carry a FORMATION CONDITION [DELTA-FIX-3]: a
length-domination fact may be formed ONLY on a NON-RESIZABLE backing place —
`buffer<T>`, `slice<'r, T>`, or `array<T, N>` — whose length cannot change after
formation (`buffer` length is fixed at allocation [TYPE-2], a slice is a
fixed-length view, an array is compile-time sized). This covers both consumers
(C2's ring on a `buffer<u64>`, C8's views on a `slice<'r, u8>`) and removes every
length-writing op from the picture; windows over a resizable `seq<T, N>` are
FUTURE WORK, gated on the cross-call length-invalidation rule below.

(a) **POW2-MASK domination.** For a non-resizable place `b`, a passed `check
ieq(ipopcount<u64>(len<T>(b)), 1_u32)` (or a `requires` prologue [FN-8] proving
`pow2(len(b))`) produces `pow2(len(b))`. [DELTA-FIX-3] The engine admits
`in_bounds(b, iand<u64>(x, isub.wrap<u64>(L, 1_u64)))` for any `x` ONLY where `L`
is provably `len(b)` at the index site (a live `LEN(b)=L` fact tied to the SAME
binding `b`) and the mask operand is that same `b`'s length — no free variable,
and the masked index uses the CURRENT tracked length of the very place indexed.
The safety-sufficient premise is `len(b) != 0` (which `popcount == 1` already
guarantees, blocking the `len = 0` mask-nothing edge); `pow2` is the correctness
superset the ring's F1 story rests on. Named consumer: C2's ring.

(b) **LEN-CHECK domination.** For a non-resizable place `s`, the fact is produced
ONLY by a `check ile<u64>(SUM, len<T>(s))` (or `ige`) where SUM is a PROVEN
non-wrapping `off + n` [DELTA-FIX-1]: the Ok-arm binding of `iadd.checked<u64>(off,
n)`; or `iadd.trap<u64>(off, n)` (overflow traps before the check); or — inside a
`requires` block, the only non-trapping legal form — `iadd.sat<u64>(off, n)`
(sound by the actual-`SUM` invariant below, NOT by any `len < u64::MAX`
assumption). A SUM produced by `iadd.wrap<u64>`, or any value not proven
overflow-free, is REJECTED as a producer (the ill-typed `iadd.checked-proven
off+n` exemplar is deleted). From an accepted producer the engine derives
`in_bounds(s, i)` for every `off <= i < SUM` (a checked prefix window),
discharging the [OP-4] bounds trap for the [LOAD-1] byte-field loads and any
`index` within it. Named consumer: C8's validated-view.

[REATTACK-FIX-1] Soundness invariant (for ANY accepted `SUM`, saturated or
otherwise): the window binds to the ACTUAL `SUM`, and the passed `check
ile(SUM, len(s))` gives `SUM <= len(s)`, so every `i` in `[off, SUM)` has
`i < SUM <= len(s)`, hence `i < len(s)`. There is NO `len < u64::MAX` premise —
`len(s) = u64::MAX` is realizable (1-byte or zero-sized elements), and the check
then passes but the derived window stays true (the place genuinely has that many
indices). A wrapped `SUM < off` yields an EMPTY window that claims nothing.
LOAD-1's own `off <= len(s) - K/8` runtime guard [DELTA-FIX-2] is the independent
backstop.

Why the forge now rejects [DELTA-FIX-1]: the reviewer's forge puts `off` near
`u64::MAX` with a small `n`, produces `off + n` by `iadd.wrap` (wrapping to a
small value `< len`), and passes `check ile(wrapped, len)` to forge an unbounded
in-bounds window. Under the repair `iadd.wrap` is NOT an accepted producer, and
the only accepted sums make `off + n` at the u64 edge either TRAP
(`iadd.trap`), take the `Err` arm (`iadd.checked`), or clamp to `u64::MAX`
(`iadd.sat`) — and by the actual-`SUM` invariant above no accepted `SUM`
(saturated, or even a wrapped one, which yields an empty window) ever produces a
FALSE in-bounds fact: the window is always bounded by the checked `SUM <= len`.
No path forges a non-empty over-claim.

**Cross-call length invalidation [DELTA-FIX-3]** (a rule, not an appositive): any
call that MAY WRITE THE LENGTH of the fact's place (or any overlapping place
[OWN-7]) — a call reaching the place through a mode that admits a length write —
KILLS all DOM-1 fact families on that place; a call that only writes ELEMENTS
(leaving `len` unchanged) PRESERVES them [REATTACK-FIX-2]. v0 declares no
length-preservation obligation, so any length-write-capable call is unconditional
havoc. For the non-resizable backing this delta admits the rule is VACUOUS —
literally, not approximately: a `buffer`/`slice`/`array` has NO length-writing op
at all, and element writes through `&uniq` leave `len` unchanged — which is
precisely why restricting the backing closes the cross-call FATAL; the rule is
stated so a future `seq`-backed extension inherits it. The ring/C8 cards were
already sound because each fact lives inside a single op body that calls no
resizer.

**Kill wiring [DELTA-FIX-3] / [REATTACK-FIX-2].** The DOM-1 PRODUCER facts
(POW2-MASK, LEN-window) are NOT monotone-cached: they are re-evaluated against
the current tracked `len` of their place, and the AUTHORITATIVE rule is that ANY
row writing a place's LENGTH kills them for that place. The length-writing
S.1/S.2 rows (an ILLUSTRATIVE enumeration under that rule) whose `kills` columns
gain the DOM-1 producer families are: `seq_push`, `seq_pop`, `seq_insert_at`,
`seq_remove_at`, `seq_truncate`, `seq_clear`, `seq_drain`, `seq_take_all`,
`seq_extend_move`, `seq_extend_copy`; `tbl_insert` (None arm), `tbl_remove`,
`tbl_retain`, `tbl_drain`, `entry_fill`, `entry_remove`; and S.3's `LEN(dst)`
writers `cq_recv_batch`/`cq_try_recv_batch` inherit it. (`seq_reserve`/
`tbl_reserve` are NOT in this set — they are length-PRESERVING reallocations that
touch only CAP/SLACK.) NONE operates on a `buffer`/`slice`/`array`, so for this
delta's admitted backing the addition is inert — it is the guard for the deferred
`seq`-backed case. Reconciled with [CAT-2]: the DERIVED `in_bounds` may survive a
length INCREASE (CAT-2 monotone-truth), but the PRODUCER pow2/LEN-window facts
die on ANY length write.

Interactions: **[OP-4]** (the discharge target), **[OP-5]** (DOM-1 IS the first
slice of its deferred range vocabulary), **[FN-8]** (a `requires` prologue is a
legal producer, with the `iadd.sat` non-wrapping spelling above), **[CAT-2]**
(kill discipline + the monotone-truth caveat), **[OWN-7]** (overlap for the
cross-call kill), **[TYPE-2]** (the non-resizable-backing formation condition).
Admission (D16): without DOM-1 every masked-ring access and every validated-view
field retains a runtime bounds branch — not at par; named consumers C2, C8.
Checker cost: two path-local fact families, tied to a place's current `len`,
killed by any length write, produced only by the pinned non-wrapping checks; no
fixpoint, matching the M1 decidability posture (O(statements × facts)).

> **HOSTILE-REVIEW FLAG.** DOM-1 is a fact channel that licenses eliding a
> safety check (the [OP-4] bounds trap) — the exact class the standing rule
> requires be adversarially reviewed BEFORE shipping. The repair round closed
> the two FATALs the first review found: the wrapping-`off+n` forge (b) is
> rejected by the pinned non-wrapping producers [DELTA-FIX-1], and the
> cross-call resize UAF (a/b) is removed by the non-resizable-backing formation
> condition + the stated havoc rule [DELTA-FIX-3]. The delta MUST be re-attacked
> before spec: the new surfaces are (i) whether a `slice<'r, T>` view of a
> resizable `seq` can smuggle a stale length past the freeze (it should not — the
> view's `'r` borrow freezes the seq, but pin this), and (ii) the `iadd.sat`
> requires-block producer's clamp-to-MAX-fails-the-check argument. Per PATTERNS
> P8 this is proof-elision of a non-source-weakening check: the source retains
> the check spelling; only the proven-away branch is elided.

---

## Delta 5 — BRAND-CROSS-FN (BRAND-1, v2.2; authority-carrying, CLOSED (D18-R18; closing regression zero findings))

> **REDRAFT [REDRAFT].** This replaces the first BRAND-1 draft, which two hostile
> reviews rejected (`evidence/brand1-review.json`). The core architecture — the
> call check as brand-identity equality, generative-vs-lexical sort separation,
> seeding/transfer reuse — repelled every DIRECT attack; every successful forgery
> exploited an UNSTATED foundation beside the core, and each had a one-clause fix.
> This redraft states the foundations FIRST. Central design change (both
> reviewers): a brand instantiation is a NOMINAL TYPE CONSTITUENT, so [TYPE-5]
> exact type-match does the identity checking at every boundary (call, return,
> construction, container element, destructure) — the "brand identity comparison"
> IS type equality, not a bolted-on pass. Verified against RULES-RATIFIED
> (R1-R15, AMD-1..5) and kernel-spec-v0.6.

### 5.1 Foundation — brand names and identity

[BRAND-1.1] Brand names. A brand name is an apostrophe-lexeme occupying the
REGIONID lexical namespace [FORM-3], carrying a declared SORT (region or brand)
FIXED at its binder. TYPE-6 no-shadowing / no-redeclaration and OWN-3-style
within-function uniqueness apply VERBATIM to every brand binder — brand
parameters, the mint binder (the fresh `'q` a `cq_new` introduces), and the
existential-unpack binder. Two brand occurrences denote the SAME brand iff they
resolve to the same binder; distinct binders are assumed-distinct. A branded
binding's tracked IDENTITY is exactly `env(binder)` of the brand occurrence in
its stated type; the per-binding identity tag is a CACHE of this, never an
independent fact.

[BRAND-1.2] Brands are nominal type constituents. A brand instantiation appears
in a type (`cq_tx<'q, T>`, `ahdl<'a, T>`) as a first-class type constituent.
[TYPE-5]'s exact-match — "argument types match declared parameter types exactly"
— therefore compares brand positions at EVERY argument, return value,
construction field, container element type, and match binder. **Invariant
[BRAND-INV]: a branded binding's recorded identity ALWAYS equals its type's brand
instantiation** — established at the `let`, preserved by `move` and container
`push` (both exact-matched by TYPE-5), re-derived at a `pop`/`match` from the
stated element/payload type. Every boundary check below is an instance of this
ONE type-equality mechanism; there are no separate brand-comparison passes.

Container defense chain (a stated CONSEQUENCE of 5.1, not a new rule): a branded
value entering a sealed container `seq<cq_tx<'b1, T>, N>` fixes the element
type's brand to `'b1`; a `seq_push` of a `cq_tx<'b2, T>` is a TYPE-5
argument-type MISMATCH (`'b2 != 'b1`) and rejects; `seq_pop`/`seq_get` yields a
`cq_tx<'b1, T>` whose identity is re-derived as `'b1` from the element type. No
fresh-instance endpoint can be laundered into a container of another instance's
endpoints (the review's F1-container forge; see 5.6).

### 5.2 The lexical-sort decision — arena ids: OPTION (a), source-place freeze

[BRAND-1.3] Arena ids use the LEXICAL sort with a source-place freeze. An arena
handle `ahdl<'a, T>` carries the RESOLVED PLACE of the arena it indexes as its
brand identity — NOT the region: two arenas `a1`, `a2` in one `region 'a { }`
share the region but are DISTINCT places, and their ids must not mix (the
review's same-region two-arena FATAL). Minimal rows [B1V21-2]:
`arena_mint['a](ar: &uniq 'a arena<'a, T>, v: own T) -> own ahdl<place(ar), T>` —
loan NONE, effects `writes('a), allocates(heap), traps`, records `ar`'s resolved
place; `arena_get['a, 'h](ar: &'a arena<'a, T>, h: &'h ahdl<place(ar), T>) -> &'a T` —
[B1V22-1] the id `h` is passed by a SHARED BORROW `&'h`, NOT own-mode: an affine
id passed bare is an OWN-1 `move` (5.8's sibling walk), so an own-mode `h` would
CONSUME the id on every get and — affine ids being one-per-allocation — make each
allocation readable exactly once; the `&'h` borrow leaves the id unconsumed and
its 5.2 freeze record live across the call, so mint-then-read-twice ACCEPTS. The
place-brand check is TYPE-5 equality on the nominal `ahdl<place(ar), T>`
constituent and compares identically through the borrow. loan column `ISSUE &
(content) at 'a` (the `seq_get` precedent: a subsequent `&uniq`-receiver op on the
arena rejects under the live content issue), effects `reads('a), traps`; the
result region is `'a`, the arena's OWN region carried by the `ar` parameter
(there is NO free result region `'v` — a caller could otherwise book a content
borrow at a region outliving the arena, an accepted UAF; the leak forge is
rewalked in 5.8). (`arena_mint` takes the VALUE `v: own T` correctly own — it
STORES it — and touches no id; there is no `arena_put` or other id-consuming row,
so `arena_get` was the only own-mode-id trap.) The brand elides only the WHICH-ARENA check —
the id provably indexes THIS arena — never the generation/liveness check
(`traps`, retained). `arena_mint`'s [R15] interior-address obligation is
discharged by `arena_get`'s ISSUE clause blocking mint-under-borrow.

[B1V21-4] Arena ids are AFFINE, not copy — a member of the AMD-6 affine
brand-carrier class, transferred by R8 (`move`) exactly like every carrier, never
copied. A live arena id imposes an R6-shr-class FREEZE on its recorded source
place: while any id into that arena is live, the place cannot be moved, rebound,
assigned over, passed by own, or reached by an early drop [R6]. A freeze record
exists for every live BINDING whose stated type TRANSITIVELY carries the
lexical-sort brand [B1V22-5]: `box<ahdl<...>>` and `Option<ahdl<...>>` are the
ONLY admitted transitive-carrier forms in this delta; the transitivity SCAN looks
THROUGH every constructor — generic positions included — to FIND the brand (so
"generic position" scopes the scan, not admission). A record is created at the
`let`/extract/result-stamp, expires R7-style at that binding's scope end, and the
freeze covers the recorded place and every overlapping place [OWN-7]. Because ids are affine there is exactly ONE live
carrier per allocation (a `move` renames the record; there is no second copy to
count), so the record expires exactly when that last carrier dies — which is why
copy would be unsound: a copy outlives its per-binding record, the freeze expires
early, and a same-binder `set`-over re-attaches a stale id (the sibling
stale-copy forge, rewalked in 5.8). REJECTED option (copy handles): per-binding
lexical machinery cannot count copies, and no type-driven copy-accounting is in
v0. CONSEQUENCE of affine ids: exactly one live handle per allocation; the C1
pool card's COPYABLE generational-handle ergonomics stay with `pool`, and arena
ids are the strict affine cousin (a `pool` handle is the copyable one when you
need many live references).

Why option (a), not (b): option (b) — keying by binding INSTANCE (fresh `let` =
fresh identity) — needs a "binding instance identity" notion absent from the
kernel and SILENTLY invalidates every id when its arena name is re-let (a
footgun). Option (a) reuses the ratified R6 freeze + R7 expiry verbatim; its only
cost is "an arena cannot be moved while ids into it are live," acceptable because
arenas are region-bound and are scoped, not moved, in practice. A lexical-sort
brand in ANY container element or generic-instantiation position OTHER than the
two admitted `box`/`Option` stack forms is FAIL-CLOSED rejected in this delta [B1V22-5]
(a `seq<ahdl<...>, N>`, a user `Pair<ahdl<...>>`, a `Result<ahdl<...>, E>` all
reject at instantiation); only `box<ahdl<...>>` and `Option<ahdl<...>>` are
admitted, covered by the transitive-carrier freeze above. Deferred to a follow-up
that adds generation-keyed records.

### 5.3 Identity sources at every boundary

Every source establishes or checks a nominal brand constituent per [BRAND-1.2]:
- MINT (generative): `cq_new` introduces a FRESH existential brand; its result
  `cq_ends<'q, T>` binds `'q` at the mint binder (BRAND-MINT dependency — the
  mint-position binder spelling; BRAND-1 gates on it). The fresh `'q` is unequal
  to every in-scope brand (5.1 no-shadowing enforces it).
- SEED: at callee entry EVERY carrier parameter's binding is seeded with the
  rigid parameter symbol `'q` (the R10(c) seeding discipline, on brands).
- CALL: ALL carrier arguments' identities must be pairwise equal and equal to
  `'q`'s instantiation — a TYPE-5 exact-match at each carrier argument [5.4].
- RETURN (callee-side check — the first draft's was VACUOUS for entry-less
  carriers): at every return of a branded result the returned value's recorded
  identity MUST equal the declared result brand's identity (the seeded rigid
  symbol, or the fresh existential for a pack); a mismatch rejects. Because
  identity is the type's brand constituent (5.1), this is the SAME TYPE-5 check
  as the return-type match — redundant by design, not both absent.
- CONTAINER EXTRACT: `seq_pop`/`seq_get`/`match` yields a value whose identity is
  `env(binder)` of the brand in the stated element/payload type (generative sort
  only; lexical-sort element positions rejected per 5.2).
- DESTRUCTURE: a `match` on a brand-parameterized sealed enum (`cq_ends<'q, T>`)
  binds each branded payload (`tx`, `rx`) with the SCRUTINEE's recorded identity
  `'q` [R11 rename, on brands].

### 5.4 Tie rule — all-carriers

[BRAND-1.4] Every parameter or result whose type names brand `'q` is a CARRIER of
`'q`. A declaration is legal iff `'q` has AT LEAST ONE parameter carrier, OR is
result-only under the existential-pack carve-out; a zero-carrier non-result `'q`
rejects. One designated parameter carrier seeds the body identity [R10(c)]; at a
call, R10(a) verifies EVERY carrier argument's recorded identity against that one
instantiation of `'q` (mirroring R10(a)'s existing ranging over "each confined
argument") — a missing record or any mismatch rejects. A brand carried ONLY by
the result is the EXISTENTIAL PACK: a fresh mint the caller unpacks (BRAND-MINT),
legal solely under this carve-out and spelled as such. This passes all five
original derivations, multi-carrier (derivation 4) and result-only (derivation 5)
INCLUDED — the first draft's exactly-one-tie clause wrong-rejected 4 and 5.

### 5.5 Housekeeping — the ratified-rule amendments

[AMD-6, proposed in this change] Scoped BY DECLARATION, not by the noun
"endpoint" [B1V21-3]. A form-table result type is EITHER an opaque-confined LOAN
TOKEN (it declares a loan clause: `issues`/`consumes`/`reissues`) OR an affine
BRAND-CARRIER (it declares a brand constituent in its type and loan clause
`NONE`); the two classes are DISJOINT, fixed at form declaration, and R15 fails
closed on a result declaring both. AMD-6 strikes from R1's opaque-confined list
ONLY the loan-NONE brand-carrying endpoint TYPES `cq_tx`/`cq_rx`/`cq_ends` (and
the arena `ahdl`), reclassifying them as affine brand-carriers with full R8
transfer (`move` renames the binding, merges the brand record, consumes the
source; no duplication) that hold NO loan (no R4 source-place loan-entry; the
arena-id place freeze of 5.2 is the lexical sort's separate stated discipline,
not a loan). LOAN-ISSUING endpoint result types — a ring's `Prod`/`Cons`, which
declare `issues Prod/Cons (shr)` — REMAIN opaque-confined under the token kind
(R4 loan holders must be confined), so RULES-RATIFIED's ring-endpoint programs
(the corpus's P5 canonical two-ring REJECT, A11 ACCEPT, ATK-two-struct-rings,
ATK-zero-region-endpoint) keep their ratified verdicts and clauses UNTOUCHED.
(RULES-RATIFIED mentions "endpoint" exactly once — R1's opaque-confined list;
under the by-declaration scoping that sentence stays true for every
loan-issuing endpoint and is amended only for the loan-NONE cq/arena carriers.)
Confined LOAN tokens (guards, cursors) remain R1/R2 as ratified.

Storage ownership of a brand-carrier [B1V22-2]: a brand-carrier's internals may
reference ONLY storage owned by the carrier set (heap, torn down by the CQ-5
endpoint-drop protocol) — never region-bound storage or borrows. This restates
the guarantee that ATK-zero-region-endpoint's R1/R13 proof carried under the old
confined classification ("the queue can never die under a live endpoint"): per
CQ-5 (S.3) the queue's heap storage is freed only when the LAST endpoint overall
drops (drain-on-drop, a surfaced [STOR-3] drop), so endpoint liveness keeps the
storage alive without any region binding. It is a sealed-form proof obligation
under R15's hostile review.

Sendable [B1V21-5]: GENERATIVE-sort brand-carriers (`cq_tx`/`cq_rx`/`cq_ends`)
are Sendable per Delta-1 CONC-2 (a generative brand is a compile-time tag,
erased, so meaningful across a thread) — this RESOLVES the Delta-1
R2-stack-confinement-vs-Sendable tension [B1V22-3] (these types are NO LONGER
R2-confined — they WERE, under ratified R1/R2, until AMD-6 struck them; the sound
reason they are now Sendable is that removal, not a false "never confined"). A
LEXICAL-sort carrier (arena `ahdl`) is Sendable only while its source form is
neither Sendable nor Shareable — currently VACUOUS for `arena` (no arena
capability row exists); revisit with the 5.2 freeze-record story before any arena
capability row is added, and the Delta-1 review inherits this pin.

ep discipline in the brand parameter, checkable END TO END [B1V21-1]: a brand
parameter carries its endpoint discipline as a bound — `brand 'q : ep`, where
`ep` is the TAG-1 tag {spsc, mpmc} (concrete, or an ep tag parameter for an
ep-generic helper). Every brand-generic body then knows the discipline;
`cq_tx_clone`/`cq_rx_clone` check `ep` and a clone under a discipline-free brand
parameter is a FAIL-CLOSED reject citing CQ-3. The bound is made checkable by two
clauses: (i) a MINT binder's bound is the mint row's ep tag — `cq_new<T, spsc, K>`
introduces `'q : spsc`, recorded on the brand; the existential-unpack binder
RESTATES the bound and must match the packed declaration's bound. (ii) At EVERY
brand instantiation (a brand targ at a call, an unpack, any brand-sorted
position) the argument brand's RECORDED bound tag must EQUAL the parameter's
declared bound tag — TAG-1 closed-set equality, re-checked per monomorphization
for ep-tag-generic helpers [FN-2] — and a bound-free brand argument in a bounded
slot, OR any mismatch, rejects citing CQ-3/TAG-1. (The endpoint type `cq_tx<'q,
T>` inherits `ep` from `'q`'s bound, so it is not repeated in the type; TYPE-5
alone therefore CANNOT catch an ep mismatch — clause (ii) is what does.) The fan
ep-forge — `fn fan[brand 'q : mpmc, 'x](tx: &'x cq_tx<'q, u64>) -> ...` (its body
lawfully `cq_tx_clone`s, a producer fan-out, legal only for `mpmc`) called
`fan<'qa>(...)` where `'qa` was minted by `cq_new<u64, spsc, 4>()` (recorded bound
`spsc`) — REJECTS at the `fan<'qa>` instantiation: `'qa`'s recorded bound `spsc`
!= `fan`'s declared bound `mpmc` (clause (ii), CQ-3/TAG-1); the body's clone is
never reached.

GRAM amendment lines [B1V21-5]: `region_params` gains a brand entry `"brand"
REGIONID (":" TAG)?` (GRAM-2), and GRAM-3's `targ` REGIONID production covers
brand names, sort-checked at the binder per the two-sort wall below (the TAG-1
precedent — a distinct monomorphization-adjacent sort in the same bracket
grammar).

Effect rows WITHOUT brand names: a queue op's runtime effect is on its ENDPOINT'S
BORROW REGION and the sealed op's own rows, NEVER on the brand — a brand is a
type constituent, not an effect region. `reads('q)`/`writes('q)` are STRUCK from
all S.3 rows and derivations; `cq_send`/`cq_try_send`/... exhibit `writes('e)`
(the `&uniq 'e cq_tx` endpoint borrow region) plus their real effects
(`allocates(heap)` only at `cq_new`, blocking per CQ-7). The BRAND-EFFECTS open
flag (CQ-7) is thereby resolved by ELIMINATION, not by adding brand-sorted effect
atoms. Companion change: S.3's `cq_*` rows and the RED BOX are rewritten in the
same landing to strike `'q` from every effect column.

Two-sort wall, BOTH directions: every apostrophe-lexeme resolves with its
binder's sort. A brand-sorted position (a form's `brand` slot, a brand targ)
accepts ONLY brand names; a region-sorted position (`borrow_expr`,
`region_params`, effect atoms, region targs) accepts ONLY regions. Each cross-
sort instantiation is a compile-time reject citing BRAND-1/CQ-2. Distinct brand
parameters are assumed-distinct and an R10(a) equality between two of them fails
closed.

Freshness and erasure (promoted from open questions to RULES): brand parameters
are CHECK-TIME-ONLY, erased BEFORE monomorphization, and are NEVER
instantiation keys — UNLIKE TAG-1 tags, which ARE monomorphization keys. FN-2/FN-6
treat a brand argument like a region argument (erased, not a monomorph key).
Loop-mint freshness is then a THEOREM, not a rule: the mint binder is body-scoped
[5.1], so a `cq_new` in a `loop @l` body introduces a binder that dies each
iteration, and R12 back-edge equality makes cross-iteration brand coexistence
unspellable. No hoisting rule is needed.

### 5.6 Rewalk — five derivations + review forge programs

Derivations (all ACCEPT under the redraft):
1. Factored producer loop: `fn produce[brand 'q : spsc](tx: own cq_tx<'q, u64>, n: own u64) -> own unit`. One carrier `tx` (tie 5.4); body seeded with `'q` (5.3 SEED); `cq_try_send` inside a `region 'e { }` type-checks (endpoint region `'e` confined); the effect row names NO `'q` (5.5). Caller mints B, `produce<B>(tx: move t, n: 100_u64)` (TYPE-5 brand match). ACCEPT — the exact code round-3 could not spell.
2. `(arena, id)`: `fn use_id['a, 'h](ar: &'a arena<'a, T>, h: &'h ahdl<place(ar), T>) -> &'a T reads('a), traps` [B1V21-2, B1V22-1] — lexical sort (5.2); `h` is a SHARED BORROW of the id (so the get does not consume it — mint-then-read-twice works); the id's place-brand ties to `ar`'s resolved place (R10(a)-place check, TYPE-5 through the borrow); the returned content borrow is at `'a` (the arena's own region, carried by `ar`), so it cannot outlive the arena under either reading. ACCEPT (clean under both readings).
3. Two endpoints of one queue to two helpers: `produce<B>(tx: move txB)`, `consume<B>(rx: move rxB)`; each helper's `'q` instantiates to B independently; B is a fresh mint, distinct from any other queue's C. ACCEPT.
4. Forgery negative — queues A, B; `f[brand 'q : spsc](tx: cq_tx<'q, u64>, rx: cq_rx<'q, u64>)` called `f(tx: move txA, rx: move rxB)`: TWO carriers of `'q` (all-carriers tie 5.4); `txA` identity A, `rxB` identity B; A != B → REJECT at the call carrier-equality check (R10(a) / TYPE-5). ACCEPT-as-reject.
5. Mint-and-return: `fn make() -> own cq_ends<'q, u64>`; result-only `'q` under the existential-pack carve-out (5.4); returns a fresh brand the caller unpacks; the callee-side return check (5.3 RETURN) verifies the returned identity equals the fresh existential. ACCEPT (BRAND-MINT- and SEALED-MATCH-gated [B1V21-5] — `make`'s caller destructures `cq_ends` via CQ-4).

Review forge programs (all REJECT; firing clause named):
- F0.1 brand-binder shadowing launder (a mint binder reuses a caller's brand name to launder a fresh-instance endpoint through a container or an R10(b) return): REJECT — TYPE-6 no-redeclaration on brand binders [5.1] rejects the shadowing mint binder at the mint site.
- F0.2 lexical stale-id re-attach (move an arena + same-name re-let; a stale id addresses the successor arena): REJECT — the R6-shr-class freeze [5.2] forbids moving/re-letting the arena place while any id is live; the `move`/re-let is the firing site.
- F1.FATAL same-region two-arena (ids of `a1`, `a2` sharing `region 'a`): REJECT — the brand is the resolved PLACE [5.2], `a1 != a2`, so an id of `a1` passed where `a2`'s place is tied fails the R10(a) place comparison.
- F1.container container-transit launder (push `cq_tx<'b2, T>` into `seq<cq_tx<'b1, T>, N>`): REJECT — TYPE-5 argument-type mismatch at `seq_push` (`'b2 != 'b1` in the nominal element type) [5.1 container chain]. The "natural pop" is sound: a pop yields `cq_tx<'b1, T>`, identity re-derived as `'b1`.
- F1.return vacuous-return launder (return an entry-less brand carrier where the loan-entry equality never fires): REJECT — the callee-side return check [5.3 RETURN] is a TYPE-5 brand-constituent match, not a loan-entry check, so it fires for entry-less carriers.

### 5.7 Interactions, cost, open questions, hostile-review

Interactions: R4 (per-binding brand record is a cache of env(binder)), R8
(transfer carries the brand constituent, no duplication), R9 (carrier-tie
totality), R10(a/b/c) (call check = TYPE-5 nominal equality; the callee-side
return check; seeding), R11 (destructure rename on brands), R12 (back-edge
equality gives loop freshness; AMD-4's comparison domain extends to brand records
of outside-declared bindings — inert today, guards future rot), R1 (AMD-6
declassifies endpoints), **TYPE-5/TYPE-6** (nominal equality + no-shadowing, the
foundation), CQ-2/3/4, TAG-1 (`ep` is a tag), FORM-3 (namespace), FN-2/FN-6
(brand erasure). Checker cost: one-pass, O(statements x env) — the type-
constituent design keeps the identity check as TYPE-5 equality on brand positions
(binder-resolved tag equality), no unification, no fixpoint. (The first draft's
per-record design did NOT preserve this; the redraft does — the reviewers noted
the cost claim survives only under the type-constituent redraft.)

Open questions (honest): (1) BRAND-MINT (the fresh-return-brand binder spelling)
AND SEALED-MATCH (CQ-4, the matchable brand-parameterized sealed enum for
`cq_ends` destructure) BOTH gate derivations 1, 3, AND 5 [B1V21-5] — not just 5;
so any GENERATIVE brand crossing a boundary is BRAND-MINT- and
SEALED-MATCH-gated, correcting the first draft's false "same-boundary helpers
land immediately" claim. Arena ids (lexical, no mint binder, no destructure) DO
land immediately. (2) Whether the affine-brand-carrier class (AMD-6) and the
confined-loan-token class share the R8 transfer machinery without a third case
(they should — both affine, R8 is kind-agnostic). (3) The lexical-sort container
fail-closed is a real expressiveness cut (no `seq<ahdl>`), deferred to a
generation-keyed follow-up.

> **HOSTILE-REVIEW DEMAND [REDRAFT].** Mandatory RE-review. The architecture is
> confirmed sound by two reviews; this redraft states the foundations they proved
> missing. Re-attack surfaces: (i) the [BRAND-INV] nominal-type-equality invariant
> under move/push/pop — whether any path breaks "recorded identity = type's brand
> constituent"; (ii) the R6-shr-class arena freeze against copy-handle
> proliferation — does every live COPY of an id keep the freeze alive to its
> scope end; (iii) the AMD-6 declassification against the R2/Sendable story and
> whether any ratified R1-R15 proof quoted "endpoints are confined".

### 5.8 Regression appendix (v2 -> v2.1) [B1V21-6]

No clause was renumbered by v2.1; 5.1-5.7 keep their numbers, and the v2 forge
verdicts are unchanged. The five v1 forge programs still REJECT at the v2 clauses
(F0.1 shadowing at 5.1 TYPE-6 mint-binder redeclaration, plus the fresh-binder
and two-line-return variants at TYPE-5 seq_push / the 5.3 RETURN check; F0.2
stale-id at the 5.2 R6 freeze with the TYPE-6 new-binder backstop; F1 same-region
two-arena at the 5.2/R10(a) place comparison; container transit at TYPE-5 element
matching; vacuous-return at the 5.3 callee-side check). The five derivations keep
their verdicts (D1/D3 ACCEPT, D2 ACCEPT now clean under the fixed `arena_get` row
[B1V21-2] with the [B1V22-1] borrow-mode id, D4 accept-as-reject, D5 ACCEPT), with
the generative ones now noted BRAND-MINT- and SEALED-MATCH-gated [B1V21-5].

The v2 review's LEAK forge [B1V22-4] (`fn leak['o]() -> &'o u64` booking a
content borrow at a caller-chosen region `'o` outliving a locally-scoped arena)
dies at the fixed [B1V21-2] row: `arena_get` returns `&'a T` = `&'i u64` at the
arena's own locally-introduced region `'i`, and `return rv` as `&'o` REJECTS —
a borrow at a locally-introduced region cannot be returned (R13/OWN-4); there is
no caller-chosen result region to book against.

Mint-then-read-twice [B1V22-1]: `let h = arena_mint(...); let x = arena_get(ar,
&'h h); let y = arena_get(ar, &'h h);` ACCEPTS — the `&'h` borrow does not consume
the affine id, so the second get is legal (under the earlier own-mode spelling
the first get would have moved `h`, dead-ending the second).

Two NEW forges, rejected:
- Fan ep-forge [B1V21-1]: `fan[brand 'q : mpmc, 'x](tx: &'x cq_tx<'q, u64>)`
  (body `cq_tx_clone`s a producer, legal only for `mpmc`) called `fan<'qa>(...)`
  with `'qa` minted `cq_new<u64, spsc, 4>()` (recorded bound `spsc`). REJECT at
  the `fan<'qa>` instantiation: the argument brand's recorded bound `spsc` != the
  parameter bound `mpmc` (ep-bound instantiation check, clause (ii), CQ-3/TAG-1).
  Without the fix TYPE-5 was silent (ep is not in the endpoint type); the recorded
  bound + instantiation comparison is what fires. The body's illegal spsc-clone is
  never reached.
- Sibling stale-copy [B1V21-4]: attempt two live copies of one arena id
  (`let id2 = id1;`) so the freeze expires when `id1`'s binding dies while a copy
  survives, then `set`-over the arena. REJECT: arena ids are AFFINE, so `let id2
  = id1` is a `move` (a bare affine place is the OWN-1 move; no copy) — it renames
  the single freeze record to `id2` and consumes `id1`; there is never a second
  live carrier to strand. The `box<ahdl>`/`Option<ahdl>` smuggling variant is
  covered by the transitive-carrier freeze clause (every live binding whose type
  carries the lexical brand holds a record). No stale copy is expressible.

## Delta 6 — TAG-TARGS (TAG-1; closes the GRAM-3 gap the round-4 catalog exposed)

The problem (verified against the kernel): sealed forms parameterize on closed-set
TAGS — the hasher `h` in `table<K, V, h>` (`h` in {fold, sip_keyed, identity,
crc}, TBL-2) and the endpoint discipline `ep` in `conc_queue<T, ep, K>` (`ep` in
{spsc, mpmc}, CQ-1). These are written in the targ position, but GRAM-3 `targ :=
type | REGIONID | const` and a `type` TYPEID is uppercase-initial [FORM-3], so a
lowercase tag (`fold`, `spsc`) is NOT a valid targ. Every `table<..., h>` and
`conc_queue<T, ep, K>` in the catalog is, as written, ungrammatical — a latent
spec gap the catalog assumed away.

### [TAG-1] Tag parameters and tag targs

A sealed form may declare a TAG PARAMETER `tag NAME : TAGSET`, where TAGSET is a
form-declared CLOSED set of lowercase tag identifiers (each a nullary marker —
the closed-enum-of-markers discipline). GRAM-2 `gparam` gains this sort, and
GRAM-3 `targ` gains `| TAG`, where a TAG is a lowercase IDENT that MUST name a
member of the corresponding parameter's declared TAGSET (a compile-time reject
otherwise, citing the form and its set [DIAG-1], with the set listed). A tag is a
monomorphization-only, compile-time-ERASED selector [FN-2]: it selects WHICH
sealed monomorphization runs (which hasher family, which endpoint protocol), has
NO runtime representation, carries no value, and is resolved by NAME against the
form's closed set (context-free [META-2], no search). It is not a type, region,
or const. Instance state is distinct from the tag: `sip_keyed`'s `k0`/`k1` are
RUNTIME arguments supplied at `tbl_new`/`cq_new` (TBL-2), not part of the tag —
the tag selects the family, the runtime args parameterize the instance.
[REATTACK-FIX-3] A tag is part of the sealed form's TYPE IDENTITY: for tags
`tagA != tagB`, `form<..., tagA>` and `form<..., tagB>` are DISTINCT types with
distinct [FN-2] monomorphizations, never unifiable, and no value of one converts
to the other; tag erasure is runtime-only and does NOT erase this type-level
distinction. [REATTACK-FIX-4] A TAG targ position resolves its lowercase IDENT
SOLELY against the corresponding form parameter's declared TAGSET (positional, by
parameter sort), never against a `const`/`fn`/region/type binding in scope — a
same-named const or fn is not consulted there; the sort of each form gparam (tag
vs const vs region vs type) is fixed at the form declaration, so every targ
position is unambiguous and tag-vs-const is never shape-decided.

Interactions: **GRAM-2/GRAM-3** (the new sort and targ production), **[FORM-3]**
(resolves the lowercase-tag-vs-uppercase-TYPEID collision the gap exposed),
**[CONST-1]** (tags are the closed analog of const targs — closed, no
computation, monomorphization-evaluated), **[FN-2]** (monomorphization-only,
explicit), **[TBL-2]** (`h` is a tag parameter, TAGSET {fold, sip_keyed,
identity, crc}), **[CQ-1]** (`ep` is a tag parameter, TAGSET {spsc, mpmc}),
**[META-2]** (positional context-free resolution, the OP-1 op-vs-fn partition).
It is the natural companion to BRAND-1's brand parameter — both are
non-type/non-region/non-const monomorphization-time parameters.

Admission (D16): the closed-set tags are used pervasively and cannot be spelled
at all without this (`cq_new<Record, spsc, 10>()`, `table<u64, u64, fold>`); the
hasher/endpoint selection picks a sealed monomorphization and is not reachable
from primitives. Named consumers: every `table<K, V, h>` and `conc_queue<T, ep,
K>`. Checker cost: a name lookup against the form's closed tag set at the targ
position; no search, no unification.

Open questions: (1) whether tag, const, and brand parameters unify into one
"non-type gparam" sort or stay distinct (this draft keeps tag distinct, closest
to the existing closed-enum discipline); (2) whether a `fn` may be generic OVER a
tag (`fn f(t: &'r table<K, V, h>)` for any `h`) — needs a tag gparam on the fn
tied to the receiver's tag, a TYPE-5-style explicit tag arg at the call; (3)
misspelled-tag diagnostics must list the closed set. Hostile-review flag: LIGHT —
no fact channel, no loan, no runtime representation; authority-ADJACENT only in
that a tag selects which trusted hasher/protocol monomorphization runs, so the
review need only confirm tag ERASURE and the closed-set totality (the
frozen-list discipline — no open-ended tag admission). [DELTA-FIX-5]

---

## Adoption ordering (dependency note)

- Delta 4 (DOM-1) and Delta 3 (LOAD-1) are adoptable together and independently
  of concurrency; DOM-1 (b) is a prerequisite for LOAD-1 being at par, and
  DOM-1 (a) unblocks C2. Both need the fact-channel hostile review.
- Delta 6 (TAG-1) is adoptable FIRST and standalone (lightest of all; no fact
  channel, no loan, no runtime rep) — it closes the GRAM-3 tag-targ gap that
  makes every existing `table<..., h>` and `conc_queue<T, ep, K>` spelling
  grammatical, so it gates nothing but is a prerequisite for the catalog parsing
  at all. Adopt it before or with anything that spells a tag.
- Delta 2 (`tbl_clone`, copy K/V only after [DELTA-FIX-4]) is adoptable
  standalone (light; no fact channel, no loan) and unblocks C5's POD/handle
  clone-modify step; C5's owning-value clone waits on a Clone-contract delta and
  its atomic publish waits on Delta 1.
- Delta 5 (BRAND-1, v2 redraft) is the named unblocker for Delta 1 and for the
  pipeline cards; it is authority-carrying and needs a fresh hostile RE-review
  (the v2 states the foundations the first two reviews proved missing). Adoption
  dependency, corrected: ANY generative brand (queue endpoint) crossing a `fn`
  boundary is BRAND-MINT- and SEALED-MATCH-gated — including the factored producer
  loop and two-helper cases, NOT only mint-and-return (the first draft's claim was
  false). Arena ids (the lexical sort, no mint binder, no destructure) DO land
  immediately. Adopt it BEFORE Delta 1, after its re-review.
- Delta 1 (concurrency) is the heaviest and is BLOCKED on Delta 5 (BRAND-1) and
  gated on full D1/fact-channel hostile review; it should be the last adopted,
  and every clause re-proved, not this draft transcribed.
