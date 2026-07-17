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

## Delta 1 — CONCURRENCY BINDINGS (the big one; hostile review of ALL of it)

> **HOSTILE-REVIEW FLAG (whole delta).** Every clause below touches the D1
> data-race-impossibility law and introduces the first cross-thread trust in the
> language. None of it ships without adversarial fact-channel review. The
> load-bearing soundness points are marked (H1), (H3), (H4) inline; (H2) — the
> old Sendable-for-confined question — is RESOLVED by BRAND-1's AMD-6 declaration
> classes (see [CONC-V2-2]) and no longer a soundness gap. This delta was revised
> [CONC-V2-*] against the now-CLOSED BRAND-1 v2.2 foundations.

### [CONC-1] Scoped threads

A `scope 'p { stmt* }` statement introduces a **thread-scope region** `'p`.
Inside it, `spawn['p](body, capture*)` starts a child thread that runs the named
`fn body` (there are no closures [FN-5]; the body is a top-level `fn` and its
per-thread state is the env-struct pattern, exactly R14's "par bodies are named
functions"). Each `capture` is either an `own` Sendable value moved into the
child, or a `&'p`/`&uniq 'p` borrow of a place whose storage outlives `'p`
[OWN-10]. `spawn` returns `own Result<unit, SpawnError>` (`EAGAIN` before the
child ever runs). `scope` exit BLOCKS until every child spawned in it has
joined; therefore no captured borrow outlives `'p`, and R14's
join-before-return discipline holds for the scope statement exactly as for the
`par` statement. The `scope` statement's effect row is `allocates(heap)` (child
stacks) joined with each body's declared row restricted to `'p` and to `heap`;
a child trap is a whole-process abort (CONC-4), so no child effect escapes as a
recoverable value.

Interactions: **R14 (PAR-1) + [AMD-1]** — the cross-capture disjointness of a
`scope` is R14's statement-local mint-disjointness verbatim: the captures of one
`spawn` are mints, and two `&uniq` mints on overlapping places reject, while
replicate `&` captures may alias; no new disjointness machinery. **OWN-10** —
`'p` is introduced by the `scope` block, so a `&'p` capture of an
enclosing-scope place is legal only because `'p` lies within that place's scope.
**OWN-11** — a `spawn` inside a `loop` body may capture only regions introduced
inside the loop body (per-iteration freshness). **FN-7** — `main`'s at-most row
is unaffected; a `scope` adds `allocates(heap)`. (H1) The claim "scope exit
joins all children so no borrow outlives `'p`" is the entire lifetime-soundness
argument and must be re-proved against the R7 reverse-order scope processing
before adoption.

Admission (D16): thread lifecycle at par (pool-amortized ~0/task spawn, scoped
borrow of stack data) is unreachable from primitives — there is no thread
primitive at all (CAP-1); named consumers are every concurrent 51-map scenario
(11, 38, 41, 42, 44) and the member audit's five canonical programs. Checker
cost: `scope`/`spawn` reuse the R14 mint-disjointness pass and the OWN-10/11
region checks; one new statement form, no new dataflow.

[CONC-V2-1] **Capturing a brand-carrier into a spawn body (was blocked; now
resolved by BRAND-1 v2.2).** A `spawn` body is a named `fn` (FN-5: no closures;
R14: "par bodies are named functions"), so moving a queue endpoint into a child
is passing a brand-carrying value across a `fn` boundary — the exact operation
the old Delta-1 open question 2 said was unspellable. Delta 5 (BRAND-1 v2.2)
closes it: `cq_tx<'q, T>`/`cq_rx<'q, T>` are affine brand-carriers, and a
captured endpoint is an ordinary carrier ARGUMENT of the spawn body's `fn`,
checked by the SAME BRAND-1 machinery as any call — the all-carriers tie
(BRAND-1 5.4), the recorded-identity comparison against the body's seeded `'q`
(TYPE-5 nominal-constituent equality, BRAND-1 5.3 CALL), and the `ep`-bound tag
comparison (5.5). No cross-thread brand machinery is added: the endpoint is
Sendable by CONC-2, its brand `'q` is a check-time-only tag erased before
monomorphization (5.5 freshness/erasure), so nothing about `'q` survives to run
time and there is nothing to transfer physically. The endpoint's own
single-endpoint discipline (CQ-3: every endpoint op takes `&uniq`, so
per-endpoint use is single-threaded) is what makes "distinct endpoints on
distinct threads" the sound concurrency shape. Honest gate: this capture rides
the same BRAND-MINT (fresh-mint binder spelling) and SEALED-MATCH (CQ-4
`cq_ends` destructure) dependencies BRAND-1 flags — a producer endpoint minted
in the parent and moved into a child is BRAND-MINT/SEALED-MATCH-gated exactly as
BRAND-1 derivation 1 is (5.6). The cross-thread walk is in the CONC regression
appendix below.

### [CONC-2] Send/Share capability judgment

`Sendable` (safe to transfer to another thread) and `Shareable` (safe to share
across threads by `&`) are the CAP-1 predicates, now bound. A value crossing a
`spawn` boundary must be: Sendable if moved `own`; its referent Shareable if
captured `&'p`; Sendable-and-exclusively-transferred if captured `&uniq 'p`. A
capability violation is a compile-time reject; there is NO runtime capability
check — data-race impossibility is static (D1).

[CONC-V2-2] **The judgment is DERIVED, not asserted per form.** With BRAND-1's
AMD-6 (5.5) in force, every form-table result type belongs to exactly one of
two DECLARATION CLASSES — an opaque-confined LOAN TOKEN (it declares a loan
clause `issues`/`consumes`/`reissues`) or an affine BRAND-CARRIER (it declares a
brand constituent and loan clause `NONE`) — and every other type is an ORDINARY
owned value. Send/Share is READ OFF that class plus the payload condition, not
stipulated form by form:

- **Opaque-confined loan token** [R1/R2, AMD-6] — `guard<'m, T>` (CONC-3),
  cursors, and every confined token: **never Sendable, never Shareable.** This
  is a derivation, not a stipulation: R2 stack-confinement forbids storing or
  sending a confined value at all (it may exist only as a local/arg/result/
  match-binding/field-of-confined), so it can never cross a `spawn` boundary in
  any capture mode. A `guard` additionally holds an interior-uniq loan (R5/R6),
  so even `&`-sharing it would hand two threads the same exclusive interior —
  independently disqualifying Shareable.
- **Affine brand-carrier** [AMD-6] — `cq_tx<'q, T>`/`cq_rx<'q, T>`/
  `cq_ends<'q, T>`: **Sendable iff `T: Sendable`, never Shareable**, exactly
  CQ-3's ratified endpoint rule. AMD-6 struck these from R1's opaque-confined
  list, so R2 no longer bars them; they carry a brand (an identity tag, erased
  before monomorphization — 5.5), not a loan, and per CQ-3 every endpoint op
  takes `&uniq`, which is why an endpoint is transferable but never shared.
  The lexical brand-carrier `ahdl<place, T>` (arena id) is a DEFERRED cell: per
  5.5 its Sendability is currently vacuous (no arena capability row exists) and
  it is never Shareable; do not send arena ids across threads until 5.5's
  freeze-record story is extended and the arena gets a capability row.
- **Ordinary owned value** — payload-structural, unchanged from the pre-brand
  draft:

| ordinary form | Sendable | Shareable |
|---|---|---|
| primitive, tag-only enum | yes | yes |
| `box<T>`, `buffer<T>`, `seq<T, N>`, `table<K, V, h>` | iff every payload Sendable | iff deeply immutable (no interior `&uniq` reachable) |
| `mutex<T>` (CONC-3) | iff `T: Sendable` | iff `T: Sendable` (derived; see the CONC open-flag sweep) |

The old provisional hedge — that "which affine values are Sendable, and is any
confined token ever Sendable" was unresolved, with endpoints sitting in an
undecided "affine-Sendable vs confined-not-Sendable" gap — is DELETED: AMD-6's
by-declaration classes decide it. Loan tokens are confined and never Sendable;
brand-carriers are not confined and are Sendable per their payload. There is no
residual undecided case at the class level.

Interactions: **CAP-1** binds its reserved words; **AMD-6 (Delta 5.5)** supplies
the two declaration classes the judgment reads off; **CQ-3** is the brand-carrier
row, now a consequence of the class rather than a standalone assertion; **R1/R2
(CONF-1/CONF-2)** give the loan-token row (stack-confinement means not
Sendable).

Admission (D16): a static Send/Share judgment is the only way to reach D1's
race-freedom without a runtime check; named consumer is every cross-thread
handoff. Checker cost: at each `spawn` capture, one classification of the
captured type (loan-token vs brand-carrier vs ordinary — a syntactic property of
its form declaration) plus, for the ordinary and brand-carrier classes, a
payload-Sendable walk closed at monomorphization; no search.

### [CONC-3] Mutex guard is a confined loan token (no new loan machinery for its lifecycle)

A sealed `mutex<T>` form exposes `mtx_lock` and the guard type `guard<'m, T>`,
an opaque `confined(uniq)` type [R1] with region parameter `'m`. `mtx_lock` is a
**`&`-receiver** form-table op: `mtx_lock['m](m: &'m mutex<T>) -> own guard<'m, T>`,
loan clause `issues uniq` [R5/R9], the issued uniq loan landing on the mutex's
INTERIOR `T` (not on the shared `&'m` mutex place). While the guard is live the
interior view is frozen [R6]; `guard_uniq['x](g: &'x guard<'m, T>) -> &uniq 'm T`
yields the protected data as a statement-scoped borrow [R3]. Dropping or
consuming the guard runs the form-declared release (unlock) and removes its
entries [R7]; the guard is auto-consumed at scope end in reverse binding order
[R7], so a lock is never leaked and never double-released [R8: no holder
duplication]. The acquire-then-return helper is writable because `'m` is a `fn`
region parameter, so returning the guard is legal [R13]; a guard carrying a
locally introduced `'m` cannot escape [R13].

The guard's SINGLE-THREADED lifecycle is pure R1/R5/R6/R7/R9 — no new loan
machinery, exactly the `tbl_entry` token precedent (an `issues uniq` form op
returning a confined token that freezes its receiver). (H3) The CROSS-THREAD
exclusivity — that no two threads' guards over the same `mutex<T>` hold the
interior-uniq loan simultaneously — is NOT derived by the loan table (the mutex
is `&'m`-shared across threads; the loan table is per-function). It rests
entirely on **[R15]**'s obligation for a `&`-receiver op on a loanable form:
"its internals both preserve every interior address and are safe under
concurrent invocation," discharged by the runtime lock. This is a sealed-form
proof obligation subject to hostile fact-channel review — a green checker is not
that review [R15]. **[AMD-5]** does not bite: `mtx_lock` is a plain `issues uniq`
(source = the interior), not an `issues K on source(receiver)` clause, so the
declaration-time fail-closed on provably-dead sibling issues is not engaged.

[CONC-V2-4] **Guard clauses re-expressed in RULES-RATIFIED + v2.2 vocabulary,
each checked against the ratified text.**
- **Class.** By AMD-6 (Delta 5.5), `guard<'m, T>` is the OPAQUE-CONFINED LOAN
  TOKEN class, not a brand-carrier: it declares a loan clause (`mtx_lock` issues
  uniq), so it stays R1/R2 as ratified — this is the same class CONC-2 reads as
  "never Sendable, never Shareable." AMD-6 struck ONLY the loan-NONE cq/arena
  carriers from R1; a loan-issuing result like the guard is explicitly retained
  as opaque-confined (5.5), so nothing in the brand work loosens the guard.
- **Acquire (R5/R9/R15).** `mtx_lock['m](m: &'m mutex<T>) -> own guard<'m, T>`
  is a `&`-receiver form-table op whose loan clause `issues uniq` lands on the
  mutex INTERIOR `T` — verified legal under R15 (a `&`-receiver op on a loanable
  form is admitted only under the interior-address + concurrent-invocation
  obligation) and R9 (the op declares its loan clause in the ratified
  vocabulary and is subject to the same call-site checks as a derived
  signature). The issued uniq loans the interior, NOT the shared `&'m` mutex
  place, so no `&uniq` is minted from the `&`-shared receiver (AMD-2 mode-
  capability is not violated: the interior loan originates in the trusted sealed
  body, not a user `&uniq`-mint of a `&`-shared place).
- **Interior view (R6/R3).** While the guard is live the interior is frozen
  under the live uniq entry (R6); `guard_uniq['x](g: &'x guard<'m, T>) ->
  &uniq 'm T` yields the protected data as a statement-scoped borrow (R3's
  single-statement mint discipline), consumed by its receiving call.
- **Release (R7).** The guard is auto-consumed at scope end in reverse binding
  order (R7: a live holder's compiler-derived drop runs the form-declared
  release — here the unlock — and removes its entries), so a lock is never
  leaked and never double-released (R8: no holder or entry duplication). The
  acquire-then-return helper is writable because `'m` is a `fn` region parameter
  (R13: a confined value returns only if every region parameter of its type is a
  region parameter of the enclosing function); a guard carrying a locally
  introduced `'m` cannot escape (R13).
- **Cross-thread exclusivity = the R15 concurrent-invocation obligation (H3),
  restated exactly).** That no two threads' guards over one `mutex<T>` hold the
  interior-uniq loan at once is NOT derived by the loan table — the mutex is
  `&'m`-shared across threads and the loan table is per-function. It rests
  ENTIRELY on R15's stated obligation for a `&`-receiver op on a loanable form:
  "its internals both preserve every interior address and are safe under
  concurrent invocation," discharged by the runtime lock. R15 names this a
  sealed-form proof obligation subject to hostile fact-channel review before
  shipping — a green checker is NOT that review. This is the single load-bearing
  cross-thread trust in the mutex and is the (H4) fact channel the whole-delta
  flag gates.

Admission (D16): a lock-protects-data guard whose unlock is compiler-derived and
un-leakable is unreachable from primitives (a hand-rolled lock has no way to tie
unlock to scope end soundly); named consumer is 51-map scenario 40 and every
shared-state server/DB scenario. Checker cost: `mutex` is one more loanable
sealed form under R15's fail-closed table; zero new judgment.

### [CONC-4] Child trap is a whole-process abort — how it composes with R7 drops

[CONC-V2-3] D18 ruling 2 (trap scope, option A) is that a runtime safety trap
terminates the WHOLE PROCESS; the kernel makes this operational: a contract
violation aborts with no unwinding (SCOPE-4) and trap has NO cleanup semantics —
"no unwinding, no cleanup semantics; the trap report is the only post-violation
artifact" (EFF-4). The member audit's panic-across-thread row is the concurrency
instance: "Trap on any thread = immediate whole-process abort; no cross-thread
unwinding, no lock poisoning, no observation channel — join never reports 'child
trapped' because the process is already gone." The composition argument with
R7's scope-end drops, stated plainly:

1. **A trapping child runs no drops.** Trap = abort with no unwinding (SCOPE-4,
   EFF-4), so the child never reaches its own R7 reverse-order scope-end
   processing. None of its holders are auto-consumed; none of its form-declared
   releases (unlock, close, drain) run.
2. **The scope's join never deadlocks on a dead child.** `scope` exit blocks
   until every child JOINS (CONC-1, R14's join-before-return). A join could only
   hang forever on a child that neither finishes nor aborts — but a trap is a
   whole-process abort delivered immediately and process-wide, so the joining
   parent thread is itself torn down at the same instant. No join ever OBSERVES
   a trapped child and then waits: the process is gone before the join could
   return (member audit: "join never reports 'child trapped'"). There is no
   trap-value channel out of a child precisely because there is no surviving
   join to carry it.
3. **Surviving threads' drops never run either.** Because the abort is
   process-wide, no OTHER thread reaches its R7 scope-end drops on the abort
   path — parent and siblings are torn down together. R7 drop processing is a
   NORMAL-exit-path guarantee only; the abort path bypasses it entirely, for
   every thread at once.
4. **This is exactly D18's ruling, and it is what makes (1)-(3) SOUND rather
   than a leak bug.** Skipping every teardown on the abort path cannot corrupt
   or expose any reachable state, because there is no surviving in-process
   observer: the OS reclaims the whole address space wholesale. A half-drained
   `conc_queue`, a still-locked `mutex`, an unflushed buffer — none is reachable
   after a process-wide abort, so leaving them is observationally inert (this is
   why D18 rules out lock poisoning and cross-thread unwinding as unnecessary).

**Implication for the sealed forms' teardown obligations.** Every sealed
teardown this delta relies on is a NORMAL-scope-exit R7 drop, NOT an abort-path
action. The guard's unlock (R7 above) and the queue's drain-on-drop run only
when their holder's derived drop is actually reached on a normal exit. The
`conc_queue` drain-on-drop is the reference protocol: per CQ-5 the queue's heap
storage is freed only when the LAST endpoint overall drops, and "every endpoint
drop is a surfaced compiler-derived drop [STOR-3] whose sealed body performs the
counting and drain (drain-on-drop)" — this is the io/teardown drain-on-drop note
Delta 5.5 also cites for endpoint-liveness-keeps-storage-alive. On the abort
path none of it runs, and by (4) none of it NEEDS to. The one obligation this
places on the sealed forms is the converse: a drain-on-drop body must itself be
trap-free on the normal path (a trap inside teardown would itself abort the
process), which is an R15 sealed-form obligation to confirm in the hostile
review, listed in the open-flag sweep below.

### Delta-1 open flags for the CONC hostile review (honest sweep)

[CONC-V2-5] Two of the original four open questions are now CLOSED by the brand
work and by CONC-4 above: the Sendable-for-confined question (old Q1) is decided
by AMD-6's declaration classes (CONC-2), and the brand-cross-fn dependency (old
Q2) is closed by BRAND-1 v2.2 (CONC-V2-1). What GENUINELY remains open for the
concurrency hostile review:

1. **The R15 concurrent-invocation obligation itself (H3/H4) — the single most
   dangerous fact channel in the language.** The mutex's cross-thread
   exclusivity, and every `&`-receiver op on a loanable sealed form under
   concurrent invocation, rests on R15's "safe under concurrent invocation"
   proof obligation discharged in trusted sealed code. A green checker is not
   that review (R15). This gates the whole delta together with D1 soundness.
2. **The publication / memory-model statement CONC ops ride on — NOT axiomatized
   in the kernel.** CQ-6 asserts "every handoff is release/acquire; reads of a
   received `T` are data-race-free (D1)," and the mutex's acquire/release order
   the interior view — but the kernel states D1 as a LAW (CAP-1) without a
   formal happens-before / publication model underneath it. The review must pin
   the memory-ordering contract these sealed forms rely on (what "release/
   acquire" means normatively, on which the arm64 dev bed is the honest stress
   target per the member audit's Chase-Lev note), because D1's static
   race-freedom is only as sound as that unstated model.
3. **`mutex<T>` Sendable/Shareable is DERIVED here, not quoted from a member-
   audit table.** The audit has NO literal per-form Sendable/Shareable table
   (the only formal capability rows are CQ-1 "`T` Sendable" and CQ-3 "endpoints
   Sendable iff `T`, never Shareable"); CONC-2's `mutex<T>` row —
   `Sendable iff T: Sendable`, `Shareable iff T: Sendable` — is a derivation on
   the standard argument (a mutex serializes access, so `&`-sharing it across
   threads needs only that its interior can be handed thread-to-thread, i.e.
   `T: Sendable`, never `T: Shareable`). The review must confirm this derivation
   and, ideally, land the missing `mutex` capability row explicitly so it stops
   being inferred.
4. **Sealed teardown bodies must be trap-free on the normal path (from
   CONC-4).** The drain-on-drop and unlock bodies run on normal scope exit; a
   trap inside one would itself abort the process. This is an R15 sealed-form
   obligation to confirm per form (`conc_queue` CQ-5, `mutex`).
5. **The CONC-1 lifetime-soundness claim (H1) is unre-proved.** "Scope exit
   joins all children, so no captured borrow outlives `'p`" is the whole
   lifetime argument and must be re-proved against R7's reverse-order scope
   processing before adoption — unchanged from the original draft, still open.
6. **Arena-id cross-thread Sendability is deferred, not decided (5.5).** The
   lexical brand-carrier `ahdl` has no arena capability row; CONC-2 marks it a
   deferred cell. If any future scenario sends arena ids across threads, 5.5's
   freeze-record story and an arena capability row must land first — the review
   should record this as out of scope for the current delta, not silently
   Sendable.

### Delta-1 regression appendix (v2, against closed BRAND-1 foundations)

[CONC-V2-6] Three walks. Capability at a `spawn` capture or a `par` slot is the
CONC-2 judgment (a replicate `&` slot requires the referent Shareable; a
split/own slot requires Sendable); R14/AMD-1 supply the loan disjointness
underneath it. Both must pass.

**Walk 1 — two-thread pipeline (spawn + endpoint move + loop send + join),
ACCEPT.** The producer body is a named fn declaring its brand parameter, exactly
BRAND-1 5.6 derivation 1: `fn producer[brand 'q : spsc](tx: own cq_tx<'q, u64>)
-> own unit` (one carrier `tx`, tie 5.4; body seeded with `'q`, 5.3 SEED; sends
in a `loop`, each `cq_send(&uniq 'e tx, ...)` under an endpoint borrow region
`'e`). Driver:

```
scope 'p {
  let ends: own cq_ends<'qa, u64> = cq_new<u64, spsc, 10>();  // mints 'qa (BRAND-MINT), bound spsc
  match ends {                                                 // CQ-4 (SEALED-MATCH)
    QueueEnds(tx: t, rx: r) => {                               // t: cq_tx<'qa,u64>, r: cq_rx<'qa,u64>
      let sp = spawn['p](producer, move t);   // move endpoint into child
      let got = drain(move r);                // parent consumes the rx end
    }
  }
}                                             // scope exit BLOCKS until producer joins
```

At `spawn['p](producer, move t)`: the body instantiates `'q := 'qa`; BRAND-1
checks the CALL identity (TYPE-5 nominal constituent — `t`'s recorded identity
`'qa` equals the seeded `'q`), the all-carriers tie (5.4, `tx` the sole
carrier), and the `ep`-bound (`'qa` recorded `spsc` == `producer`'s declared
`spsc`, 5.5 clause (ii)). CONC-2 checks the capture: `cq_tx<'qa, u64>` is a
brand-carrier, Sendable iff `u64` Sendable — yes. Inside the child, the loop's
`cq_send` uses `&uniq 'e tx`; CQ-3's per-endpoint `&uniq` discipline makes the
child the sole toucher of `tx` (single-threaded per endpoint). Join: `scope 'p`
exit blocks until the child joins (CONC-1, R14 join-before-return), so the moved
`tx` never outlives `'p`. Teardown on the NORMAL path (CONC-4): the child's `tx`
drops at its exit and the parent's `rx` drops after `drain`; when the last
endpoint drops, CQ-5 drain-on-drop frees the queue. ACCEPT — the cross-thread
form of BRAND-1 derivation 1, BRAND-MINT/SEALED-MATCH-gated.

**Walk 2 — guard-across-threads forgery, REJECT (clause named).** Attempt to
acquire a guard in the parent and carry it into a child:

```
let g: own guard<'m, u64> = mtx_lock(&'m m);
scope 'p { let sp = spawn['p](worker, move g); }   // REJECT
```

REJECT at the capture, firing clause **CONC-2 opaque-confined loan-token row**:
by AMD-6 `guard<'m, u64>` is the loan-token class (it declares `issues uniq`),
so CONC-2 derives it NEVER Sendable — grounded in R2 (CONF-2) stack-confinement,
which forbids the guard existing anywhere but a local/arg/result/match-binding/
field-of-confined, and a `spawn` capture stores it into the child's env, none of
those. The `&`-capture variant `spawn['p](worker, &'p g)` also REJECTS: the
guard is NEVER Shareable (CONC-2), and independently R6 forbids it — the guard
holds a live interior-uniq entry, so `&`-sharing it would hand a second thread
the exclusive interior. The SOUND pattern is Walk 3: share the `mutex` (not the
guard) and lock inside each body, so the guard never crosses a thread boundary.

**Walk 3 — replicate-shared `par` capture of a mutex, legal IFF Shareable (both
directions).**

- *Direction A (T Sendable, so legal).* `mutex<u64>`: `u64` is Sendable, so by
  CONC-2 `mutex<u64>` is Shareable. A `par` replicate-shared slot takes a `&`
  mint of the mutex place (no uniq entries on it, R14; AMD-1 lets two replicate
  `&` mints on the same place coexist). Each body receives `&'p mutex<u64>`,
  calls `mtx_lock` INSIDE its own scope to get its own `guard<'m, u64>`
  (single-threaded within the body), works, and drops the guard at body scope
  end (R7 unlock). Cross-body mutual exclusion is the R15 concurrent-invocation
  obligation (CONC-3, H3), hostile-review-gated. ACCEPT — the canonical
  shared-state-under-mutex par pattern; the guard is minted and dropped per
  body, never captured.
- *Direction B (T not Sendable, so rejected).* Take a `mutex<T>` whose `T` is not
  Sendable. By CONC-2 `mutex<T>` is then NOT Shareable (`Shareable iff
  T: Sendable`). The replicate-shared `&` capture into the par body REJECTS at
  the CONC-2 capability check on the slot (a replicate `&` slot requires the
  referent Shareable), even though the R14/AMD-1 loan-disjointness would pass on
  its own. Firing clause: **CONC-2 `mutex` row (Shareable iff T Sendable)** at
  the par replicate slot. This is correct: sharing the mutex would let bodies on
  different threads hand the non-Sendable interior `T` thread-to-thread, the
  exact transfer CONC-2 forbids.

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
