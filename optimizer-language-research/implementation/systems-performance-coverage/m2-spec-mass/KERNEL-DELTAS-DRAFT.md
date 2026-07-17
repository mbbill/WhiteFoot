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

`tbl_clone['r](t: &'r table<K, V, h>) -> own table<K, V, h>` — deep-clones the
whole table and returns a FRESH, independent owner. K and V must be clone
(compile reject otherwise, cites this row; an affine V has no clone and is
rejected). loan NONE; own: returns own (a new table, `t` unchanged);
effects `reads('r), allocates(heap), traps`; failure `trap "table capacity
overflow"` [TBL-4] on the fresh bucket-array byte-size overflow, OOM per
[CAT-6]; facts `LEN(r)=LEN(t)`; kills nothing on `t`; cg `CG-CLONE`. No loan is
issued or consumed — the result is a plain owned value.

Cost: O(n). For copy V the clone is a control-byte + slot bulk copy at DRAM
bandwidth (~1-2 ns/entry, `evidence/microbench/RESULTS.md`); for owning V it is
n element clones + n allocations (~30-3000 ns/entry by value size, same source).
`CG-CLONE`: at most one growth-free bulk `memcpy` region for copy V; a serial
per-entry clone loop for owning V.

Interactions: **[TBL-4]** (rehash/overflow discipline reused for the fresh
array), **[CAT-6]** (OOM stance), **[CAT-2]** (produces LEN(r), touches no fact
on `t`). No loan-rule interaction (loan-free row). Admission (D16): a
bulk-copy whole-table clone is unreachable from primitives — a
`for_each`-then-`insert` rebuild pays n hashes + n probes (~10-40 ns/entry)
versus the ~1-2 ns/entry bulk copy, not at par; named consumer is C5
COW-republish (the clone IS the publish). Checker cost: one row, no new
judgment. Open questions: (a) a shallow "share immutable values" clone variant
for owning V (would need a Shareable-value refcount — defer to the concurrency
delta); (b) whether `h`'s instance state (sip_keyed k0/k1) is cloned (yes — the
fresh table must hash identically); (c) hostile review is light here (no fact
channel, no loan), but the owning-V clone cost must be cited honestly in any
COW falsifier by value type.

---

## Delta 3 — Machine-core byte-load ops

### [LOAD-1] Endian-explicit byte loads

New OP-1 rows (machine-core intrinsics, admitted through the frozen-list
one-line rule): `load_le_u16`, `load_le_u32`, `load_le_u64`, `load_be_u16`,
`load_be_u32`, `load_be_u64`. Each: `(s: slice<'r, u8>, off: u64) -> own uK`
reads the `K/8` bytes at byte offset `off` and assembles a `uK` with the stated
endianness. Effect `reads('r), traps`: an out-of-range access
(`off + K/8 > len(s)`) traps [OP-4, SCOPE-4]. **Bounds-trap elidability**: the
trap is discharged when the requires engine proves `off + K/8 <= len(s)` by a
deterministic-checker discharge [OP-4] — a `check` fact [OP-5], a `requires`
prologue fact [FN-8], or the length-domination fact [DOM-1]; a solver may never
promote it. **CG contract**: a discharged load lowers to exactly one unaligned
machine load, plus one `bswap` for the big-endian rows — codegen-identical to
the C idiom, asm-diff pinned in the codegen corpus.

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
cost: the bounds obligation `off + K/8 <= len(s)` is one linear range test the
requires engine already performs for `index`; low. Open questions: (a) a
`store_le/be` writer counterpart (deferred to the same delta once a writer
scenario names it); (b) whether the CG "penalty-free unaligned" assumption needs
a split-cache-line note for the deployment target; (c) whether `off` as a
compile-const should get a stronger elision. Hostile-review flag: LIGHT — the
only fact channel is the bounds discharge, shared with [DOM-1]'s review.

---

## Delta 4 — Length-dominates-bounds fact extension

### [DOM-1] Length-domination facts (the [OP-5]-deferred range vocabulary, first slice)

Two checked fact forms enter the stated-and-checked channel [OP-5] (whose
"loop invariants, ranges" vocabulary is explicitly DEFERRED there; this is the
first slice). Both attach to a resolved place and its length binding, and both
are deterministic-checker discharges [OP-4], never solver-promoted.

(a) **POW2-MASK domination.** From a passed `check ieq(ipopcount<u64>(len), 1_u32)`
(or a `requires` prologue [FN-8] proving `pow2(len(b))`), the engine derives
`in_bounds(b, iand<u64>(x, isub.wrap<u64>(len, 1_u64)))` for any `x` — a masked
index `x & (len-1)` is always `< len`. This discharges the [OP-4] bounds trap at
masked-index sites. Named consumer: C2's ring (the `F1 pow2-mask domination`
the ring card already gates on).

(b) **LEN-CHECK domination.** From a passed `check ile(iadd.checked-proven off+n, len(s))`
— an offset+count within length — the engine derives `in_bounds(s, i)` for every
`off <= i < off + n` (a checked prefix window). This discharges the [OP-4]
bounds trap for the [LOAD-1] byte-field loads and any `index` within the window.
Named consumer: C8's validated-view (validate length once, then trust the field
loads).

**Producers**: the pow2 `check`/`requires` fact (a); the length `check`/`requires`
fact (b). **Invalidators**: any op that writes the place's length — grow,
reserve, clear, truncate, a resizing store — KILLS both fact families for that
place [CAT-2 kill discipline]; a `move` or drop of the place kills them; the
facts do not survive across a length write. **What the prover must ADDITIONALLY
discharge**: for (a), the pow2 fact must hold AND no length-writing op may lie on
the dominated path between the check and the index (syntactic: the ring card's
"no row in this card resizes buf" property, checked, not assumed); for (b), the
`off + n` arithmetic must be proven non-overflowing (spelled `.checked` or a
proven range) so the derived `i < len` is sound — an overflowing `off + n` that
wrapped could otherwise forge an in-bounds fact.

Interactions: **[OP-4]** (the discharge target; DOM-1 facts are exactly the
"deterministic-checker discharge" OP-4 admits), **[OP-5]** (DOM-1 IS the
first slice of OP-5's deferred range vocabulary — this is the delta OP-5 names),
**[FN-8]** (a `requires` prologue is a legal producer; FN-8 already says its
passed fact "may eliminate downstream implicit checks such as [OP-4] bounds
checks"), **[CAT-2]** (kill discipline on length writes). Admission (D16):
without DOM-1 every masked-ring access and every validated-view field retains a
runtime bounds branch — not at par (the whole point of both cards); named
consumers are C2 and C8, both of which currently "fail closed" pending exactly
this extension. Checker cost: two path-local fact families, produced by a check,
killed by a length write; no fixpoint, matching the M1 decidability posture
(O(statements × facts)).

> **HOSTILE-REVIEW FLAG.** DOM-1 is a fact channel that licenses eliding a
> safety check (the [OP-4] bounds trap) — the exact class the standing rule
> requires be adversarially reviewed BEFORE shipping. The two soundness edges
> are the overflow of `off + n` (b) and the "no resize on the dominated path"
> obligation (a); both must survive a hostile attack (e.g. a wrapping offset, a
> resize hidden behind a conformer call, an aliased length binding) before
> adoption. Per PATTERNS P8 this is proof-elision of a non-source-weakening
> check: the source retains the check spelling; only the proven-away branch is
> elided.

---

## Adoption ordering (dependency note)

- Delta 4 (DOM-1) and Delta 3 (LOAD-1) are adoptable together and independently
  of concurrency; DOM-1 (b) is a prerequisite for LOAD-1 being at par, and
  DOM-1 (a) unblocks C2. Both need the fact-channel hostile review.
- Delta 2 (`tbl_clone`) is adoptable standalone (lightest; no fact channel, no
  loan) and unblocks C5's single-threaded clone-modify step; C5's atomic publish
  still waits on Delta 1.
- Delta 1 (concurrency) is the heaviest and is BLOCKED on the brand-cross-fn
  kernel rule (open question 2) and gated on full D1/fact-channel hostile review;
  it should be the last adopted, and every clause re-proved, not this draft
  transcribed.
