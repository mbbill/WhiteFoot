# xlc — the self-hosting xlang compiler: bootstrap plan

*Approved 2026-07-08. This is the structure we build forward on — clean, no rewrite.*

## Goal

Bootstrap a **production compiler for xlang, written in xlang itself** (self-hosting is
the endgame). The Python `prototype/` toolchain (democ + checker) is the **disposable
bootstrap** that compiles xlc until xlc compiles itself; it is retired at M-D. This
`compiler/` tree is the product.

## The subset-S invariant (the load-bearing idea)

xlc **implements** the full v0.6 language, but **its own source is restricted to a frozen
subset S**. S is finite and listable, so "the bootstrap must compile xlc" reduces to
"grow democ to exactly S" — a bounded target — and self-compilation becomes mechanical.
xlc drops the S discipline only at M-E, once it compiles the whole language.

## Architecture — 15 modules, 2 protected seams

**Front:** `source` (bytes + spans) · `intern` (byte-string arena → integer ids) ·
`diag` (diagnostics-as-**data**: `enum RuleId` + `pool<Diag>`) · `token` · `lexer`
(hand-written byte DFA — no regex in xlang).
**Middle:** `ast` (per-kind arena pools, `handle` children, spans on every node) ·
`parser` (recursive descent, ~1:1 with democ) · `symbols` · `types` · `check_type` ·
`check_own` · `check_eff`.
**Back:** `lower` (thin core IR) · `emit_llvm` (IR → `.ll` text) · `driver`.

Two **protected seams** keep growth additive (never a rewrite): the typed-AST↔passes
boundary, and the thin-core-IR↔backend boundary (**emit never reads the AST**).
Cross-cutting from day one (cannot be retrofitted): spans on every node; the
`Result<T, DiagId>` diagnostics-as-data error spine.

## Compile & link model

- **Whole-program.** Many `.xl` files are source organization only; xlc concatenates them
  (ordered) into **one `PROG-1` closed unit** and emits **one `.ll`**. No `.ll`-level
  linking, no linker of ours.
- **Target: LLVM IR text.** `clang` (in the Makefile / conformance adapter — *never*
  spawned by xlc) compiles the one `.ll` plus a tiny trusted C runtime shim, drives the
  system linker, and links libc → native binary:
  `clang -O2 out.ll runtime/xlrt.c -o xlc`.
- **I/O = ~5 gated §14 primitives** (`io_read_file`, `io_write_file`, `io_args_len`,
  `io_arg`, `io_exit`) implemented in `runtime/xlrt.c` over libc; xlc's `.ll` `declare`s
  and `call`s them; the shim owns C `main(argc,argv)` and stashes argv for `io_arg`.
  This shim **is** the gated boundary: trusted, human-approved (LEDGER-1), **outside
  T1/T2** safety, deliberately no process-spawn (clang stays in the Makefile).
- **Self-hosting = a 3-stage byte-identical `.ll` fixpoint:** democ→xlc0, xlc0→xlc1,
  xlc1→xlc2; assert `xlc1.ll == xlc2.ll` (byte-stability from insertion-order-only
  iteration over pools; hashing is lookup-only).

## Subset S

**HAVE today** (democ already compiles): fn decls with `own`/`&'r`/`&uniq 'r` params;
cross-fn calls; self-recursion; `let`/`set`/`return`; `deref`; exhaustive `match` with
named binders, own+borrow scrutinees, and `let`-init `give`; `loop`/`break`; `region`;
`check … else trap`; i32 arith (`iadd`/`isub`/`imul` ×`.wrap`/`.trap`/`.checked`) +
integer comparisons; tag-only enums + prelude Bool/Option/Result; named construction,
named call args, ANF; FORM-1/2/3/4/5/7 + EFF-1/2 enforcement; string literals in
doc/trap-msg; the conformance verdict/exit-code contract.

**MUST ADD** (democ codegen unless marked spec):
1. Multi-width ints `u8/u32/u64/i64` + bit-ops (`iand`/`ior`/`ixor`/`ishl`/`ishr`) +
   `cvt`/`reinterpret` + `idiv`/`irem` *(idiv/irem required for int→decimal-ASCII in the
   emitter)*.
2. **General struct codegen** (democ sets `structs={}`): `%T = type {…}`, alloca/GEP/
   load/store, construct, field-place set. **Highest leverage — land first.**
3. **Payload-carrying enum codegen**, word-sized/copy payloads only (no struct-in-variant,
   no move-out) + prelude Option/Result payload erasure.
4. `buffer<T>` + `array<T,N>` + `index`(OP-4 bounds-trap)/`len`/`slice_of`.
5. **[spec]** Byte-**string literals as values** (`array<u8,N>`, viewable as `slice<'r,u8>`),
   appendable into a `pool<u8>` — narrowest possible (literals only, no String type).
6. **[spec]** Fixed-capacity **`pool<T>` + `handle<T>`** (construction-sized, append-only,
   no realloc → no cluster-1C / no growable-pool §5 machinery): OP-1 rows
   `pool_new/push/at/at_uniq/len`, `handle_eq`; STOR-1; OWN-6 reborrow-through-holder;
   OWN-14 result-reborrow provenance; OWN-15/16.
7. Compiler-derived drop/free on region-exit/return/break edges (STOR-3).
8. A small **builtin-generic monomorphizer** over *only* the concrete instantiations xlc
   uses (`pool<Token>`, `pool<Node>`, `handle<Node>`, `Option<handle<Node>>`, `buffer<u8>`,
   `buffer<u32>`, `slice<'r,u8>`, `array<u8,N>`). Keeps general user-generics off the
   critical path.
9. `try` / ERR-3 propagation over `Result<T, DiagId>`.
10. **[spec]** Minimal gated §14 I/O signatures via LEDGER-1 (the ~5 primitives above).
11. Whole-unit input: ordered multi-file concatenation into one closed unit (PROG-1;
    v1 uses a naming-prefix convention, a real module system is M-E).
12. **[convention]** `Result<_, DiagId>` reject spine (diagnostics-as-data, replaces the
    Python `CheckError` control-flow rejection).

## Bootstrap milestones

- **M0 — Freeze S + apply spec deltas.** This doc + the FORM-1-breaking spec addenda
  (string-literal values, fixed-cap pool/handle, gated §14 io, Result/DiagId). Matching
  pending conformance cases promoted to active targets. *Honest caveat: §5 ratification
  stays BLOCKING on the independent D1a/FR gate (owner ruling #1); the fixed-capacity pool
  profile is sound and independent of it, so the bootstrap proceeds without waiting.*
- **M-A — Grow democ to compile S** *(the dominant, throwaway effort — a real second
  compiler)*. Land the MUST-ADD list in dependency order, each flipping a batch of pending
  conformance cases. democ codegen stays correctness-only (clang -O2 optimizes). Exit gate:
  democ compiles a hand-written "read file → build `pool<Node>` → emit bytes → write file"
  program; make check green.
- **M-B — Write `xlc.xl` in S**, hosted on grown-democ. Modules bottom-up; `check_own`
  ported LAST, arm-for-arm from `checker.py` ("do not improve during the port"). Gate:
  **differential testing** — all 191 conformance sources through both democ/checker.py and
  democ-compiled-xlc, identical verdict *and* exact cited rule id.
- **M-C — Full-corpus green.** Point the runner ADAPTER at `xlc0` (democ-compiled xlc);
  xlc0 reproduces every runnable manifest verdict + rule id. xlc0 is now an independent
  oracle.
- **M-D — Self-compile + byte-identical fixpoint** (self-hosting achieved). `xlc1.ll ==
  xlc2.ll` byte-for-byte. democ demoted to audit oracle, then retired.
- **M-E — Grow xlc forward, never democ again.** User generics + FN-2 mono; contracts/laws
  (FN-3/4); floats + full op-table + full cvt matrix; growable pool (post cluster-1C, the
  §5 take/replace resolution); DIAG-2 elaborated artifact; a real module system. The two
  seams absorb each additively. Once xlc compiles the whole v0.6 language, its source may
  drop the "stay inside S" discipline.

## Top risks (and mitigations)

- **`check_own` port over provisional §5** — highest-logic-risk. Port arm-for-arm,
  differential-test against `checker.py` on every OWN/GIVE case, isolate pool-reborrow
  behind a stable module boundary so §5/D1a ratification touches only `check_own`.
- **M-A is real, throwaway, largest line-count.** Freeze S tightly (word-sized copy enum
  payloads, no user generics/floats), keep democ codegen dumb, validate every step against
  the reusable 191-case oracle.
- **Fixed-capacity pools trap on large input (possibly xlc.xl itself).** Two-pass sizing
  (count then allocate), generous multipliers, clear overflow trap; growable pools remove
  this at M-E.
- **regex → hand-scanner drift** vs byte-exact FORM-2/5/7 fixtures + DIAG-1 rule ids.
  Differential-test the scanner's token stream against democ's `TOK` on all 191 cases
  before building the parser on it.
- **Byte-identical fixpoint (M-D)** needs stable SSA numbering + iteration order. All
  user-visible iteration is insertion-order over pools; hashing is lookup-only.
- **The gated-io shim is outside T1/T2.** Keep it to exactly the ~5 opaque human-approved
  primitives; no process-spawn.

## Directory layout

- `prototype/` — disposable Python bootstrap (democ, checker). Grown during M-A, retired at M-D.
- `compiler/` — **xlc**, the production xlang-in-xlang compiler.
  - `PLAN.md` (this doc) · `src/*.xl` (modules, M-B onward) · `runtime/xlrt.c` (gated C shim).
- `conformance/` — the acceptance oracle (191 cases); the adapter swaps democ→xlc at M-C.
- `spec/` — the language spec (89 rules); M0 applies the S deltas here.
