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
> load-bearing soundness points are marked (H1)-(H4) inline.

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

### [CONC-2] Send/Share capability judgment

`Sendable` (safe to transfer to another thread) and `Shareable` (safe to share
across threads by `&`) are the CAP-1 predicates, now bound. A value crossing a
`spawn` boundary must be: Sendable if moved `own`; its referent Shareable if
captured `&'p`; Sendable-and-exclusively-transferred if captured `&uniq 'p`.
Conformance is a **per-form conditional table** (the member audit's
form-conditional rows), not a user `conform`:

| form | Sendable | Shareable |
|---|---|---|
| primitive, tag-only enum | yes | yes |
| `box<T>`, `buffer<T>`, `seq<T, N>`, `table<K, V, h>` | iff every payload Sendable | iff deeply immutable (no interior `&uniq` reachable) |
| `cq_tx<'q, T>`, `cq_rx<'q, T>` | iff `T: Sendable` [CQ-3] | never [CQ-3] |
| `mutex<T>` (CONC-3) | iff `T: Sendable` | iff `T: Sendable` |
| `guard<'m, T>`, other confined tokens [R1] | no (H2) | no (H2) |

A capability violation is a compile-time reject; there is NO runtime capability
check — data-race impossibility is static (D1). Interactions: **CAP-1** binds
its reserved words; **CQ-3** endpoint rows are now formal table entries;
**R1/R2 (CONF-1/CONF-2)** — (H2) a confined token is stack-confined (R2: it may
exist only as a local/arg/result/field-of-confined, never stored or sent), so
it is judged NOT Sendable. This COLLIDES with CQ-3's "endpoints are Sendable":
`cq_tx`/`cq_rx` must therefore be affine-own-but-NOT-confined values (they carry
a brand, not a loan), which the M1 rules already allow (a brand is an identity
tag, not a loan-table entry) — but the boundary "affine-Sendable vs
confined-not-Sendable" is exactly the open question below.

Admission (D16): a static Send/Share judgment is the only way to reach D1's
race-freedom without a runtime check; named consumer is every cross-thread
handoff. Checker cost: a per-form table lookup at each `spawn` capture, closed
over payload types at monomorphization; no search.

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

Admission (D16): a lock-protects-data guard whose unlock is compiler-derived and
un-leakable is unreachable from primitives (a hand-rolled lock has no way to tie
unlock to scope end soundly); named consumer is 51-map scenario 40 and every
shared-state server/DB scenario. Checker cost: `mutex` is one more loanable
sealed form under R15's fail-closed table; zero new judgment.

### Delta-1 open questions (honest)

1. **Sendable for confined types (H2).** R2 stack-confinement says a confined
   token may never be stored or sent; yet CQ-3 needs endpoints Sendable. The
   draft resolves this by classing endpoints as affine-own-brand-carrying (NOT
   loan-confined) values, but the exact predicate — "which affine values are
   Sendable, and is any confined token ever Sendable" — is unresolved and is the
   first thing hostile review must pin. A guard is firmly NOT Sendable (it holds
   an interior loan); an endpoint must be Sendable; the line between them is a
   brand-vs-loan distinction that has not been stress-tested across threads.
2. **Brand-cross-fn dependency.** Sending a `cq_tx<'q, T>` into a `spawn` body
   moves a brand-carrying value across a `fn` boundary — exactly what
   OPEN-FLAG (BRAND-CROSS-FN) says is unspellable today. So CONC-1's endpoint
   captures are BLOCKED until the brand-cross-fn kernel rule lands; the concurrency
   delta cannot be adopted before, or independently of, the brand rule.
3. **Whole-process abort on child trap (CONC-4, referenced above).** "Trap on any
   thread = immediate whole-process abort; no cross-thread unwinding, no lock
   poisoning, no observation channel" (member audit) — D18 ratified trap =
   process abort. This must be re-proved to compose with R7 drop semantics (a
   trapping child never runs its drops; the parent's scope-exit join must not
   deadlock on a dead child) before adoption.
4. The `&`-receiver concurrent-invocation obligation (H3) is the single most
   dangerous fact channel in the language; it and D1 soundness gate the whole
   delta.

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
(overflow clamps to `u64::MAX`, which is `>= len(s)`, so the check FAILS and no
window is produced). A SUM produced by `iadd.wrap<u64>`, or any value not proven
overflow-free, is REJECTED as a producer (the ill-typed `iadd.checked-proven
off+n` exemplar is deleted). From an accepted producer the engine derives
`in_bounds(s, i)` for every `off <= i < SUM` (a checked prefix window),
discharging the [OP-4] bounds trap for the [LOAD-1] byte-field loads and any
`index` within it. Named consumer: C8's validated-view.

Why the forge now rejects [DELTA-FIX-1]: the reviewer's forge puts `off` near
`u64::MAX` with a small `n`, produces `off + n` by `iadd.wrap` (wrapping to a
small value `< len`), and passes `check ile(wrapped, len)` to forge an unbounded
in-bounds window. Under the repair `iadd.wrap` is NOT an accepted producer, and
the only accepted sums make `off + n` at the u64 edge either TRAP
(`iadd.trap`), take the `Err` arm (`iadd.checked`), or clamp to `u64::MAX >=
len` so the check FAILS (`iadd.sat`). No path both wraps AND produces the fact.

**Cross-call length invalidation [DELTA-FIX-3]** (a rule, not an appositive): any
call whose effect row includes `writes(R)` where `R` reaches the fact's place (or
any overlapping place [OWN-7]) KILLS all DOM-1 fact families on that place — v0
declares no length-preservation obligation, so this is unconditional havoc on any
writes-reaching call. For the non-resizable backing this delta admits the rule is
VACUOUS (a `buffer`/`slice`/`array` has no length-writing op; element writes
through `&uniq` leave `len` unchanged), which is precisely why restricting the
backing closes the cross-call FATAL; the rule is stated so a future `seq`-backed
extension inherits it. The ring/C8 cards were already sound because each fact
lives inside a single op body that calls no resizer.

**Kill wiring [DELTA-FIX-3].** The DOM-1 PRODUCER facts (POW2-MASK, LEN-window)
are NOT monotone-cached: they are re-evaluated against the current tracked `len`
of their place, and any row that writes a place's length kills them for that
place. The length-writing S.1/S.2 rows whose `kills` columns gain the DOM-1
producer families are: `seq_push`, `seq_pop`, `seq_reserve`, `seq_insert_at`,
`seq_remove_at`, `seq_truncate`, `seq_clear`, `seq_drain`, `seq_take_all`,
`seq_extend_move`, `seq_extend_copy`; `tbl_insert` (None arm), `tbl_reserve`,
`tbl_remove`, `tbl_retain`, `tbl_drain`. NONE operates on a
`buffer`/`slice`/`array`, so for this delta's admitted backing the addition is
inert — it is the guard for the deferred `seq`-backed case. Reconciled with
[CAT-2]: the DERIVED `in_bounds` may survive a length INCREASE (CAT-2
monotone-truth), but the PRODUCER pow2/LEN-window facts die on ANY length write.

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

## Delta 5 — BRAND-CROSS-FN (BRAND-1; authority-carrying, hostile review required)

> **HOSTILE-REVIEW FLAG (whole delta).** This is the machinery that keeps two
> queues' endpoints from mixing and an arena id from addressing the wrong arena
> — an authority/soundness property (mixing SPSC endpoints breaks the
> single-producer invariant D1 rests on). The generalized identity comparison
> (I2) and generative-brand freshness (I3) are the attack surfaces.

### The problem, precisely (verified against RULES-RATIFIED)

R4 records, per confined holder, a source PLACE per region parameter; R10(a)
verifies a call by comparing that recorded source place against the resolved
place of the tied argument (the instance-brand check). This is total INSIDE one
function and dies at every signature boundary: a branded value passed into a
callee loses the caller's place identity, so a queue endpoint or arena id cannot
cross a `fn` boundary — the factored-pipeline killer (round-3 pipeline 0/4).

### [BRAND-1] Brand parameters and cross-function brand identity

A signature may declare, in its parameter bracket alongside region parameters, a
BRAND PARAMETER `'q` (a distinct sort — spelled `brand 'q` to preserve CQ-2's
"a brand is not a lexical region"). A branded parameter or result names `'q`;
`'q` must TIE to exactly one carrying argument whose type carries `'q` (the R9
totality discipline verbatim: zero or several carriers, or a `'q` named only by
a result, reject the declaration). The checker tracks per branded binding a
BRAND IDENTITY, records it (R4-style), transfers it on move (R8), verifies it at
each call (R10a), seeds the callee body from its signature (R10c), and
propagates it on return (R10b) — reusing that scaffolding with no new pass.

Two brand SORTS, and this is the one place the reuse is not verbatim:
- **Lexical-region brand (arena)** — an arena handle carries the arena's region
  `'r`; its identity IS `'r`'s source place, so R10(a)'s PLACE comparison applies
  VERBATIM. Arenas need only the "brand parameter is a region parameter" reading.
- **Generative brand (queue, CQ-2)** — a `cq_new` mints a FRESH existential brand
  per execution; its identity is that fresh skolem symbol, NOT a place. (I2)
  R10(a) must therefore compare BRAND IDENTITIES, not places: place identity
  would wrongly equate two queues minted at one syntactic `cq_new` in a loop, so
  a generative brand cannot be a place. This is the single generalization
  BRAND-1 makes to R10(a): "same recorded source place" becomes "same brand
  identity," where an identity is a place (arena) or a generative symbol (queue).

Everything else is R9/R10 reuse: the tie is R9; the call-site check is R10(a) on
identities; the body is seeded per brand parameter like R10(c) seeds loans; a
returned branded value propagates its brand per R10(b).

### Must-handle derivations

1. **Factored producer loop** (the round-3 killer). `fn produce['q](tx: own cq_tx<'q, u64>, n: own u64) -> own unit reads('q), writes('q)` — sends `n` items in a `loop`/self-recursion, borrowing `tx` per send. `'q` is a brand parameter tied to `tx`. Caller: `cq_new` mints identity B, destructures, `produce<B>(tx: move t, n: 100_u64)`. The body is seeded with `'q` (R10c-analog), so `cq_send(&uniq 'e tx, v)` type-checks; no brand crosses further. Writable — the exact code round-3 could not spell.
2. **`(arena, id)` pairs** — `fn use_id['a](ar: &'a arena<'a, T>, id: ahdl<'a, T>) -> ...` ties the id's region `'a` to the `ar` argument. This is the LEXICAL-region case: R9 tie + R10(a) PLACE comparison verbatim, no generalization; the id addresses only the tied arena.
3. **Two endpoints of ONE queue to two helpers** — `produce['q](tx)` and `consume['q](rx)`; caller mints B, `produce<B>(tx: move txB)`, `consume<B>(rx: move rxB)`. Each helper instantiates its own `'q` to B independently; B is a fresh skolem distinct from any other queue's C, so no endpoint of B is ever accepted where C is expected.
4. **Forgery negative** — queues A and B; `fn f['q](tx: cq_tx<'q, u64>, rx: cq_rx<'q, u64>)`. `f<?>(tx: move txA, rx: move rxB)` REJECTS: the single brand parameter `'q` requires both arguments tied to it to share ONE brand identity; `txA` carries A, `rxB` carries B, and A != B. **The clause that fires is R10(a)** (the instance-brand check, generalized to identities) — the same clause that already rejects loan-token source-place mismatches, now on generative symbols.
5. **Mint-and-return** — `fn make() -> own cq_ends<'q, u64>` calls `cq_new` and returns the ends. The return type EXISTENTIALLY binds a fresh `'q` (the caller unpacks a fresh skolem on each `make()` call, so two calls yield unconfusable brands). This is NOT the R13 escape violation: R13 forbids returning a value carrying a locally-introduced LEXICAL region; a generative brand return is an existential PACK, sound because the returned brand is fresh-to-the-caller (exactly `cq_new`'s own behavior, which `make` wraps). It DEPENDS on OPEN-FLAG (BRAND-MINT): the fresh-return-brand binder spelling is the remaining gap.

### Interactions with R1-R15 / AMD

- **R4 (LOAN-1)**: adds a per-branded-binding brand-identity record, parallel to R4's per-holder source-place record; the two coexist (a value is a loan holder OR a brand carrier — endpoints/arena-ids are brand carriers, NOT loan-confined tokens, so R2 stack-confinement does not bind them; see Delta-1 open Q1).
- **R8 (LOAN-5)**: a `move` of a branded value carries its brand identity to the destination, exactly as it carries a holder's source records; kind/identity never changes in transfer.
- **R9 (SIG-1)**: a brand parameter ties to exactly one carrying argument under R9's totality — zero/several carriers reject at declaration.
- **R10 (SIG-2)**: (a) generalized to compare brand identities (the ONE change); (b) a branded result propagates its brand to the tied argument's identity; (c) the body is seeded with each brand parameter.
- **R13 (ESC-1)**: unchanged for lexical regions; BRAND-1 adds the generative-brand existential-pack return (derivation 5) as a distinct, sound return path gated on BRAND-MINT.
- **R14 (PAR-1) / CONC-1**: a `par`/`scope` body is a named `fn`, so passing a branded endpoint into it is a brand crossing a `fn` boundary — BRAND-1 is exactly what makes that spellable; this is why concurrency is BLOCKED on BRAND-1.
- **CQ-2/CQ-3/CQ-4**: brand stays a distinct non-region sort (CQ-2); Sendable endpoints (CQ-3) are the brand-carrier-not-loan-token class; the mint origin is the `cq_new`/destructure site (CQ-4).
- **AMD-1..5**: untouched — BRAND-1 changes no loan clause, no par disjointness, no form-table rule; AMD-3's receiver-holder tie and AMD-5's declaration fail-closed are orthogonal.

### What CONC-1's spawn additionally needs (noted, not solved here)

Capturing a branded endpoint into a `spawn` body moves the brand across the
`scope` boundary. BRAND-1 makes the brand crossing type-check, but the spawn
ALSO needs: the branded value Sendable (Delta-1 CONC-2 — a brand identity is a
compile-time tag, erased at runtime, so it is meaningful across the thread), and
the `scope` join to keep the queue alive for the child's extent (CONC-1). Those
are concurrency obligations, not resolved by BRAND-1.

### Checker cost

One-pass, table lookups only. A brand identity is a per-binding tag in the same
decidability environment that already holds the region-parameter -> source-place
map (M1 §Decidability); a call is a positional lookup + one identity comparison
(R10a), seeding is one entry per brand parameter (R10c), transfer is a rename
(R8). No unification search, no fixpoint, no lattice — the identity comparison is
an equality test on tags. Cost stays O(statements x env size).

### Open questions

1. Generative-brand identity representation: how the fresh skolem per `cq_new` is
   allocated and equality-tested; ties directly to OPEN-FLAG (BRAND-MINT) for the
   mint-and-return binder (derivation 5).
2. Loop-minted freshness: a `cq_new` inside a `loop` mints a fresh brand each
   iteration; the checker must treat each as a distinct identity and must not
   hoist — an OWN-11-style per-iteration rule for brands.
3. Whether to unify the two sorts (lexical-region arena brand vs generative queue
   brand) or keep them distinct; this draft keeps them distinct (arenas = pure
   R9/R10 reuse, queues = the R10a generalization), which is the smaller change.
4. Erasure: a brand identity must be provably compile-time-only (zero runtime
   representation) so it can cross a thread by Sendable without a runtime tag —
   an erasure obligation for the hostile review.

### Admission (D16) and hostile-review demand

Admission: factored pipeline code (helpers over endpoints/ids) is unreachable
without this — round-3 measured pipeline 0/4 precisely because it is unwritable;
named consumers are every pipeline scenario and CONC-1. Hostile review: YES,
mandatory. This is authority-carrying — the R10(a) generalization is what
prevents endpoint forgery/mixing (derivation 4), and a hole lets two queues'
endpoints cross, breaking the SPSC/MPMC single-owner invariants that D1's
data-race-freedom rests on. The attack surface is (I2) the identity comparison
admitting a place where a generative symbol is required (or vice versa) and (I3)
two `cq_new` sites colliding on one identity.

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
- Delta 5 (BRAND-1) is the named unblocker for Delta 1 and for the pipeline
  cards; it is authority-carrying and needs its own hostile review, but it is
  adoptable independently of concurrency (arena ids and same-function-boundary
  endpoint helpers land immediately; only the mint-and-return path waits on
  BRAND-MINT). Adopt it BEFORE Delta 1.
- Delta 1 (concurrency) is the heaviest and is BLOCKED on Delta 5 (BRAND-1) and
  gated on full D1/fact-channel hostile review; it should be the last adopted,
  and every clause re-proved, not this draft transcribed.
