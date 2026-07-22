# Catalog v1 Re-Cut under the D16 Minimality Criterion

Date: 2026-07-16

Status: research result under D15/D16; production changes remain gated. This
re-cut applies the owner's D16 criterion — a sealed built-in is admitted only
when ordinary users cannot reach par performance from the language primitives
and checked libraries — to the pass-1 recommended catalog. Method: eight
per-unit adjudications, two hostile attacks (cuts-are-performance-naive and
keeps-violate-minimality), one synthesis resolving every FATAL/MAJOR finding.
Raw outputs: `evidence/recut-*.json`.

## Headline accounting

- Sealed kernels: 10 (pass-1 recommendation had ~18 forms)
- Spec objects: 17
- Sealed op rows: ~85-100 (from ~130-160)
- Trusted LOC estimate: ~15-24k trusted LOC across 10 sealed kernels (threads+par scheduler 3-5k; io-file 2-3k with evring deferred; table 2-3k without inline mode; conc_queue 1.5-2.5k with spsc conditional; sync ~2k; seq incl. kept inline mode 1.5-2.5k; pool+arena 2-3k incl. the new two-slot-borrow row; shared<T> 1-1.5k; extern-C lowering ~0.5k), carrying ~85-100 sealed op rows — down from ~130-160 rows and ~25-35k trusted LOC pre-cut. Honest caveat per the accounting MAJOR: the residual trusted library still rivals the 90-rule kernel spec, and the two largest pockets (scheduler, io) have their member-level audits scheduled but not yet run.

## Final catalog


### Language primitives

- **loan/freeze confined borrows** — Per-binding loan/freeze judgment: borrow-carrying tokens/cursors/guards typecheck and the container is frozen while a token lives.
  - Why this tier: Checker-level judgment; definitionally not library-implementable. Load-bearing for validated-view layout tokens, snapshot guards, and btree node borrows.
  - Preregistered check: Spec CI soundness suite, plus a paper check that the btree split/merge sequence (owned-node extraction via pool two-slot borrow, transient parent-handle rewrite) is expressible without spurious generation panics — run before the btree lib is written.
- **wbuf typed-initialized-extent byte buffers + margin views** — Checked partial initialization of BYTE buffers (initialized-extent judgment), margin views for over-read slack, align(N); bytes only.
  - Why this tier: Extent judgment is sound and cheap precisely because bytes carry no drop obligations and every bit pattern inhabits the type — the named reason the typed-affine analog (tbuf) is not admitted (see deferred).
  - Preregistered check: LZ self-alias paper check: can a read view of the initialized prefix coexist with a live append cursor under loan/freeze? If not, the single copy_within_extend member is added as fact-adjacent trusted surface and must pass hostile review BEFORE layout-cursor Gate 2 runs (its cost is charged, not booked at zero).
- **requires-prologue fact system** — Compiler proves prologue facts and elides dominated bounds checks; measured capability today is dominated constant/loop-index bounds (1.71x base64).
  - Why this tier: Optimizer-integrated proof channel, not expressible in user code. Resolution of the fact-overdraft MAJORs: three named extension candidates are now explicit, gated deliverables, not assumptions — F1 pow2-mask domination ((i & (cap-1)) < cap from a pow2 fact), F2 type-range facts (u8 value < 256 as index bound), F3 runtime/element-wise offset facts (off + w <= len carried across access sites and over validated-offset arrays).
  - Preregistered check: Each of F1/F2/F3 requires hostile adversarial review as a fact channel PLUS a preregistered elision demonstration (facts report + disassembly) before any dependent verdict binds; every dependent unit has a fail-closed retained-bounds measurement path so no par claim rests on an unbuilt extension.
- **machine core (SIMD value types, named intrinsics, ISA dispatch, endian loads, bit ops, branchless select, prefetch, NT copy/fill, align/cachepad)** — Portable instruction-level codegen guarantees with one-time ISA dispatch and portable fallback semantics per row.
  - Why this tier: Codegen guarantees are definitionally sealed. Resolves the accretion MINOR: the intrinsic list is FROZEN and gains a one-line admission rule — a new row requires a named consumer kernel or corpus operation plus stated portable fallback semantics, through the same D16 gate as sealed members.
  - Preregistered check: Verify crc32c presence (bytescan + wal recovery depend on it) and audit json-stage1's clmul/pdep-class needs against the frozen list before those benches run; any addition goes through the admission rule, never in as a benchmark fix.
- **arena brands + lexical regions (one spec cluster with the arena kernel)** — Generative brands (checker mechanism) + lexical region scoping (scoping rule), presented and charged as ONE cluster with the bump kernel.
  - Why this tier: Checker/scoping mechanisms are not library-buildable. Resolves the three-spellings MINOR: brands/regions/kernel are one capability story with one rule set, counted as one spec object plus the kernel.
  - Preregistered check: Spec-draft consolidation review confirming a single rule cluster; reviewer must be able to answer 'one mechanism or three?' from the page.
- **explicit copy struct** — Opt-in Copy semantics for structs; overwriting a Copy slot is plain checked assignment.
  - Why this tier: Type-system rule; load-bearing for the sort core's hole-free insertion base case (n+2 moves, not 3n swaps).
  - Preregistered check: Sort-core codegen inspection confirms Copy overwrite lowers to the same mov shape as the unsafe hole idiom.
- **core forms (affine values, array/slice/box/buffer, match/loop/ANF, contracts with 3 checked laws, effects rows, monomorphized generics, env-struct)** — The baseline kernel language; buffer = fixed-length, Copy elements, fully initialized.
  - Why this tier: The language itself; consolidated to one catalog line so the surface count stays honest.
  - Preregistered check: Existing spec CI + conformance suite.

### Sealed kernels (trusted internals)

- **seq<T, inline N>** — Growable sequence: uninit spare capacity, affine elements, take/replace/swap/insert-at/remove-at/drain-range; inline mode KEPT and pinned as embeddable in user structs (including pool slots).
  - Why this tier: Named blocker: typed uninit affine slots + take/replace out of containers are floor-forbidden; Option-tag or default-init user routes fail Vec par mechanically (tag+branch on hottest path or O(n) reserve). RESOLVES THE FATAL CONTRADICTION: the primitives-audit inline trim is REVERSED — btree's node representation load-bears on embeddable inline seq, and wfc is exactly the SmallVec-hungry workload the trim bet against; the defensible half of that trim (table's inline=N) is taken instead.
  - Preregistered check: (a) Embeddability gate: inline seq as a struct field inside a pool slot with insert-at/remove-at/drain-range compiles, and prologue facts flow through the handle deref — must pass before the btree lib is written; (b) tiny-vector wfc-shaped bench: within 1.10x of a SmallVec reference end-to-end.
- **table<K,V>** — SwissTable hash map (SIMD group probe, one-load-one-compare hit path); inline=N tiny-map knob removed.
  - Why this tier: Control bytes are user-buildable but the uninit affine K/V slot array with take/replace on probe hit is not; the tiny-map mode's job is covered at par by the linear-scan card (n<=8 is where linear scan is the state-of-the-art mechanism anyway).
  - Preregistered check: Tiny-map card within 1.05x of an inline-mode SwissTable reference on n in [1,8]; failure re-admits inline=N. Additionally: measure the sealed table's iterate+insert clone constant (ns/entry) — it arms the M7 COW band, which is otherwise not a meaningful falsifier.
- **pool<T>** — Generational slab: insert/take/get with generation-checked handles, PLUS one new charged row — checked disjoint two-slot &uniq borrow.
  - Why this tier: Reusable uninit typed slots + generation witnesses are runtime disciplines the static checker cannot express. RESOLVES the btree rebalancing MAJOR: the two-slot borrow is promoted from 'optional' to a required, costed row so split/merge never reminting handles — without it, pool.remove+insert invalidates the sibling leaf chain (predecessor next_leaf points at a dead generation) and the range cursor breaks.
  - Preregistered check: Two-slot borrow row passes hostile review as new sealed surface; paper check that btree split/merge under it preserves leaf-chain validity with no extra slab touches beyond the parent rewrite.
- **arena kernel (bump allocator)** — Typed emplacement of affine values into region memory, pointer-bump alloc, O(1) bulk free; brand/region integrated.
  - Why this tier: Typed emplacement into raw memory is the forbidden op; pool does not subsume it (freelist pop + generation write + key construction is ~3-5x the bump path's 2-3 instructions, and per-element accounting loses O(1) bulk free).
  - Preregistered check: Alloc fast-path inspection: 2-3 instructions, par with bumpalo/typed_arena.
- **threads + par (scoped spawn, parallel-for, work-stealing scheduler)** — The only thread-spawning and task-scheduling surface; the Chase-Lev steal deque is an internal detail (user endpoint demoted).
  - Why this tier: No user spawn and no atomics on the floor — categorically closed. Steal demotion changes visibility, not code: the deque still runs at crossbeam-deque parity inside par, and users cannot spawn the threads a hand scheduler would need.
  - Preregistered check: (a) Member-level audit (sync-trim-style, per-row scenario evidence) BEFORE catalog freeze — this pocket never got one; (b) irregular fork-join (unbalanced task tree, 8 cores) via par within 1.10x of a crossbeam-deque hand scheduler; miss + demonstrated closure by a steal endpoint re-exposes it.
- **sync vocabulary (relaxed counter, publish/snapshot cell, mutex<T>, once<T>, condvar)** — Five members, one rule each: counter = NO PUBLICATION (normative spec text, not card prose); cell = Copy-word payloads ONLY, snapshot sees fully-built value, NO heap publication — use shared<T>; mutex/condvar = guard discipline; once = first-wins; cas-cell cut.
  - Why this tier: No atomic type or memory model on the floor. RESOLVES the two-spellings MAJOR: the cell's payload domain is pinned to Copy words, making cell and shared<T> disjoint domains (scalar swap vs heap publication with reclamation) — one spelling each; a heap-publishing cell would have to answer reclamation and degenerate into shared<T>. Condvar's keep is converted from speculative to evidenced: io-wal's leader-follower group commit is its named scenario.
  - Preregistered check: cas-cell necessity sweep: the 14 frozen corpus ops + 10 pre-nominated concurrency scenario kernels, implemented from the trimmed vocabulary only, each within 1.10x of its named C/C++/Rust reference without writing a raw CAS retry loop; re-verify config-swap scenarios split cleanly across the pinned cell (scalars) and shared<T> (heap state).
- **conc_queue (spsc + mpmc endpoints)** — Crossbeam-channel-class endpoints; steal endpoint removed (internal to par); spsc kept CONDITIONALLY.
  - Why this tier: Lock-free queue protocols need atomics. spsc's only evidence is the pre-nominated pipeline kernels — the keep is explicitly conditioned on the sweep, since a sealed endpoint is purely additive later.
  - Preregistered check: In the necessity sweep, if mpmc lands within 1.10x of an rtrb/crossbeam spsc reference on the pipeline/bounded-producer-consumer kernels, spsc moves to deferred; otherwise it stays with that measurement as its evidence line.
- **shared<T> (epoch-pinned publish/snapshot)** — ~4 rows — new/publish/snapshot/guard-drop — with one rule: readers write zero shared lines, reclamation after grace period; update-with row CUT.
  - Why this tier: Per-thread epoch slots, fences, and grace-period reclamation need raw atomics; the refcount substitute is exactly the shared-line write that kills M7 scaling. update-with is unevidenced convenience: all multi-writer mutation routes through the external mutex (stated normatively on the COW card), and the row is purely additive later.
  - Preregistered check: M7 harness via the COW card bands, run only AFTER the table clone constant is measured; reader cost pinned at one uncontended epoch-pin store + frozen-snapshot probe.
- **io-file (enumerated syscall leaves)** — open (O_DIRECT/alignment-honoring), pread/pwrite, read/write, fdatasync, fsync, fsync-on-directory-handle, rename, stat/len, logical-block-size query, close — every row with a named consumer; evring deferred out of v1.
  - Why this tier: Syscalls are sealed by definition, but RESOLVES the unenumerated-family MAJOR: the family is now row-enumerated with per-row scenario evidence (the durability rows are charged to the wal cut; the block-size query closes the 4Kn/512e O_DIRECT gap). evring has zero consumers in the frozen fourteen-op corpus and is deferrable at zero cost.
  - Preregistered check: Row-set verification (fdatasync/rename/dir-fsync semantics on Linux and macOS) BEFORE the wal cut is ratified — the dependency runs that direction; any remaining io-family members (net/process/time) get the same row-by-row audit before freeze or do not ship.
- **extern-C records** — C-ABI layout-guaranteed records, minimal row set; named v1 consumer: the differential-testing and benchmark harnesses that link pinned C references (miniz, SQLite shapes, protobuf varint) plus sealed-io shims.
  - Why this tier: ABI layout control is a codegen guarantee, not expressible in checked source; the consumer is now named rather than assumed ('a systems language obviously needs FFI' is struck as justification).
  - Preregistered check: Row minimality audit: only the rows the verification harnesses and sealed io actually use ship in v1; the rest defer.

### Checked libraries (zero trust, project-written)

- **btree (sequential ordered map)** — Zero-trust checked source: pool-slab nodes of embedded inline seqs (keys/vals/children), SIMD or comparator in-node search, two-slot-borrow rebalancing, leaf-chained range cursors, O(n) bulk-load.
  - Why this tier: With seq-inline KEPT (contradiction resolved) and pool's two-slot borrow row charged (rebalancing protocol completed — no handle reminting, leaf chain stays valid), every par mechanism survives in checked source: slab deref is the same latency class as a heap chase, in-node bounds elide from the len<=capacity container invariant, scan is a pointer-bump loop. Verdict is CONDITIONAL and fails closed to a deferred sealed btree, never silently.
  - Preregistered check: Gate 0: seq embeddability + fact-flow-through-handle-deref demo. Then vs Rust std BTreeMap, u64/u64, n=1M: lookup <=1.10x, random insert <=1.15x (costed WITH the complete rebalancing protocol), full scan <=2.0ns/elem and <=1.15x, bulk-load <=1.10x, affine-payload (24B) scan <=1.15x; secondary falsifier: any surviving per-element bounds check in the scan loop. Tuning budget: node size/fanout only.
- **bytescan + hash kernels (memchr/memmem/utf8-validate/json-stage1/base64/crc32c/xxh3/siphash)** — Wide-load + movemask + branchless-select kernels over machine core, margin-view vector tails, dominated i+VLEN<=len facts; zero trust.
  - Why this tier: Every needed instruction is a named machine-core op; no sealed mechanism is missing. json-stage1's intrinsic needs go through the machine-core admission rule, not ad-hoc additions.
  - Preregistered check: Checked memchr on 1MiB haystacks >=0.90x of memchr-crate per lane; short-input (<64B) latency documented as a known tail-path concession, not hidden.
- **sort core (ipnsort-class Copy sort + radix dispatch + branchless binary search + itoa/ryu)** — Block partition with u8-offset wbuf, Copy insertion base (n+2 moves via Copy overwrite), heapsort fallback, radix scatter — all checked source; F2-GATED.
  - Why this tier: The cut is recorded as CONDITIONAL on fact-extension F2 (type-range facts), per the overdraft MAJOR — the partition loop is the most bounds-dense loop in the catalog and the D9a retained-bounds precedent does not transfer to it; the radix scatter's prefix-sum index is explicitly carved OUT of the elision claim (memory-bound, measured with bounds retained). Fail-closed: below band re-seals the core.
  - Preregistered check: Checked ipnsort port, random u64 N=1e6, 30 runs vs Rust ipnsort: >=0.90x either via F2 elision (after F2's hostile review) or with bounds retained and still in band; facts report + disassembly of the partition inner loop attached either way.
- **layout modules (fixed-format accessors, validation-pass walkers, varint/LEB128, bit readers, LZ copy loop)** — Per-format checked modules: validate-once size fact + frozen-buffer token + constant-offset leaf accessors (1 load + <=1 bswap); variable-offset half F3-gated.
  - Why this tier: Fixed half binds NOW — constant-offset domination is the measured easy case and a sealed schema cannot beat 1 load. Variable half (SQLite cell walks, TLV) is CONDITIONAL on F3, with a fail-closed one-predicted-branch-per-access measurement. The wrong-offset objection is rebutted as an accepted trade: the schema mechanism made a LOGIC-bug class structurally checked at the price of a trusted generator whose failure mode is silent OOB — a SAFETY bug; D16 prefers the zero-trust route, mitigated by shipping the corpus formats as checked libs so modest writers consume rather than hand-chain offsets.
  - Preregistered check: Gate 1 (codegen): every fixed accessor = exactly 1 load + <=1 bswap/movbe, zero residual checks. Gate 2 (measured, x86-64 AND AArch64 pinned per the ISA-variance risk): >=0.97x geomean vs pinned C references with CI excluding 0.95x; SQLite cell walk measured both without F3 (branch retained) and, post-review, with F3.
- **wal (group-commit write-ahead log)** — align(4096) wbuf frames + crc32c, leader-follower group commit over mutex+condvar, checkpoint via fdatasync-rename-dirfsync, checksum-truncating recovery; payload copy OUTSIDE the leader lock.
  - Why this tier: fdatasync dominates by 2-3 orders of magnitude and the lib issues the identical syscall sequence as SQLite's C WAL; sealing buys no mechanism. Now unconditional-modulo-verification: the required file rows are enumerated and charged in io-file (the dependency inversion is fixed — rows verified before ratification), and the shipped lib teaches the copy-outside-lock shape.
  - Preregistered check: Throughput at 1/4/16 committers, 256B and 4KB payloads: >=0.90x SQLite WAL (normalized) and >=0.95x a minimal C group-commit harness; syscall count per batch <= the C reference; 10k random-kill crash-consistency trials (dm-log-writes/fsync-fault) with zero acknowledged-transaction loss.

### Composition cards (taught patterns)

- **FIFO/ring card (unified single spelling)** — ONE taught FIFO card: primary = Copy masked ring over a runtime-pow2 heap buffer (boxed slice/seq with cap-is-pow2 fact at construction) with CORRECTED as_slices (unwrapped case head&m < tail&m returns the single slice [head&m..tail&m]; two slices only when wrapped); affine payloads = pool-handle ring; two-stack amortized queue = affine fallback subsection ONLY, documented amortized-only.
  - Why this tier: RESOLVES the two-spellings MAJOR (the primitives-audit two-stack card is demoted into this card — it was strictly dominated for Copy T, and its claim that no Copy user ring exists was false) and the ring-card mechanism MAJOR (as_slices formula and the fixed-length-buffer backing story are both fixed; the pow2-mask elision is F1-gated, not assumed).
  - Preregistered check: SINGLE reconciled band (no band shopping): push/pop cycle at cap 4096 + BFS frontier over a 1M-edge graph, within [0.90x, 1.10x] of VecDeque with zero residual bounds branches (F1-dependent, fail-closed to seal-or-extend); pool-handle ring vs VecDeque<Box<T>> on 64B tasks, same band; escalate the deferred seal if the affine route exceeds 1.25x vs inline VecDeque on a workload the target set actually contains.
- **tiny-map card (linear-scan small map)** — Parallel keys-seq/vals-seq (NOT interleaved tuples — strided keys defeat the vector load) with machine-core SIMD key compare and a stated scalar early-exit fallback, for n<=8.
  - Why this tier: Replaces table's inline=N knob; linear scan with SIMD compare is what inline map modes compile to at these sizes, so the card concedes nothing — with the mechanism error from the audit corrected in the card text.
  - Preregistered check: Within 1.05x of an inline-mode SwissTable reference on lookup/insert with sizes drawn n in [1,8]; failure re-admits table's inline=N.
- **COW-republish read-mostly map card** — shared<table<K,V>> + writer mutex batch-republish; ALL mutation through the mutex (normative on the card); staleness and transient 2x footprint stated; note that papaya also heap-allocates and derefs entries on read, so boxed-affine-V is at parity, not behind.
  - Why this tier: Covers the actual read-mostly regime (Hz-to-kHz updates) at or better than papaya's read path; the O(n)-republish update ceiling is stated, not hidden — the high-churn regime is honestly deferred, not claimed covered.
  - Preregistered check: M7 at 16 cores, Zipf 99.9% read, n=1e6, vs pinned papaya 0.2.x, run AFTER measuring the sealed table's clone ns/entry: read scaling >=12x, read latency <=1.3x papaya, sustained >=1e4 updates/s at <=10ms staleness; any band failing flips rcu_table back toward sealing.
- **sharded-mutex-map card** — [cachepad mutex<table<K,V>>; S] sharded by high hash bits, for mixed read/write loads.
  - Why this tier: Pure floor composition over sealed mutex + table; covers the update-throughput regime the COW card cannot, with the Zipf hot-shard convoy limitation stated.
  - Preregistered check: 99% read / 1% write at 16 cores >=0.5x papaya aggregate throughput; if mixed loads prove to be the common case rather than the rare one, the two-card coverage story is re-opened.
- **sort-by-key-then-permute card** — Large/affine T: sort Copy (key, u32 idx) pairs with the checked sort core, then apply the permutation by cycle-following seq take/replace.
  - Why this tier: Also the fast route in C++/Rust for large elements, so not a downgrade; leans only on seq's existing sealed rows.
  - Preregistered check: seq take/replace confirmed O(1) without per-call state churn; large-element sort par with the indirect-sort idiom in the reference languages.
- **validated-view layout card** — Chained const offsets (each = previous + previous-width), leaf accessors with one requires clause, const-assert final size, round-trip test discipline; validate-once claims scoped to private/owned mappings only.
  - Why this tier: The pattern behind the layout checked libs; the residual wrong-offset class is documented ON the card as a logic-bug concession (accepted in exchange for deleting the trusted generator whose bug class was silent OOB).
  - Preregistered check: Card discipline demonstrated end-to-end on the four preregistered corpus formats; a deliberate seeded offset error must be caught by the mandated round-trip test, demonstrating the mitigation works.
- **durability-ordering card** — What to fsync, in what order, and why: log append then fdatasync; checkpoint = new-file fdatasync, rename, directory fsync; recovery truncates at first bad checksum.
  - Why this tier: Durability ordering is semantically unverifiable by the checker; the card plus the shipped wal lib is the blessed writing, and the hand-roll hazard is stated.
  - Preregistered check: Card's sequence matches an strace of the SQLite reference byte-for-byte in syscall order; crash harness zero-loss.

### Deferred (with reinstatement triggers)

- **tbuf<T> typed prefix-extent affine buffer (language-primitive candidate)** — Would provide initialized-prefix typed uninit storage for affine T in user code — the capability whose absence justifies most container seals.
  - Why this tier: EXPLICIT ADJUDICATION of the cross-cutting FATAL, rejected for v1 with a named checker limitation: (1) wbuf's extent judgment is sound because bytes have no drop obligations; the typed analog must track per-index initialization (holes) — a flow-per-index, dependent-typing-class judgment outside the per-binding discipline D2's compactness constraint permits; (2) the sound whole-prefix approximation with atomic rule-level take/replace/grow reproduces exactly seq's API while the bulk-relocate of affine values remains TRUSTED CODEGEN either way — the primitive relocates seq's trust into language rules (the most expensive spec real estate) rather than removing it; (3) its uniquely-unlocked capabilities (user seq, inline-affine ring, stable merge scratch) have zero par-critical consumers in the frozen fourteen-op corpus.
  - Preregistered check: Escalation trigger: if two or more typed-uninit-blocked deferred capabilities (inline-affine deque, stable affine sort, a future embeddable-slots need) acquire corpus-evidenced par demands, tbuf is adjudicated head-to-head against sealing each individually before either ships.
- **sealed inline-affine ring/deque** — VecDeque-class contiguous ring for affine T (wraparound over uninit spare capacity).
  - Why this tier: No corpus operation is a single-threaded affine deque; the Copy card + pool-handle route cover v1; sealing is the correct future answer only when a scenario forces it.
  - Preregistered check: Trigger: an inline-affine deque hot path enters the target scenario set, or the pool-handle route exceeds 1.25x vs inline VecDeque on a workload the perf-target set contains, or F1 fails hostile review/demonstration.
- **rcu_table (papaya-class concurrent in-place table)** — Per-bucket CAS, incremental migration, epoch-guarded reclamation — the high-churn concurrent map.
  - Why this tier: Not user-buildable (no atomics, no take/replace out of user containers) but no frozen-corpus op needs the >1e5-updates/s-with-linear-read-scaling regime; among the hardest units to review hostilely, so it must not arrive under time pressure.
  - Preregistered check: Trigger: a declared v1 scenario requiring >1e5 in-place updates/s with >=12x concurrent read scaling and <1ms visibility, or any M7 COW-card band (a)-(c) failing.
- **evring (io_uring-class submission/completion)** — High-QD async submission, linked ops, registered buffers (~10-20 rows, 2-3k trusted LOC of kernel-shared-memory lifecycle).
  - Why this tier: RESOLVES the io MAJOR: zero consumers in the frozen corpus (SQLite needs pwrite/fdatasync/rename/dir-fsync; wal's falsifier runs entirely on synchronous rows); sealed syscall surface is purely additive later, so carrying it now is ecosystem mirroring.
  - Preregistered check: Trigger: a v1 scenario whose par target demonstrably needs high-QD async submission (syscall-bound beyond what synchronous file rows + threads can reach); admission then includes its own hostile review of the shared-ring lifecycle.
- **stable affine-T merge-sort core** — driftsort-class stable sort of affine T (needs typed uninit affine merge scratch).
  - Why this tier: Genuinely unimplementable from the floor (wbuf is bytes-only) and outside the current par-target set; a narrow sealed core is admitted only on demand.
  - Preregistered check: Trigger: a corpus-evidenced demand for par stable sort of affine T; adjudicated against tbuf per its trigger.
- **table inline=N tiny-map knob** — Dual-representation small-map mode inside the sealed table.
  - Why this tier: The defensible half of the primitives-audit trim: the linear-scan card is the same mechanism at these sizes, and re-admission is additive.
  - Preregistered check: Trigger: tiny-map card fails its 1.05x band on the preregistered n in [1,8] workload.
- **sealed btree** — Sealed ordered-map kernel — the fail-closed target of the btree checked-library verdict.
  - Why this tier: Only re-enters if the checked route's preregistered gates fail (embeddability, fact flow through handle deref, or perf bands); the concurrent ordered map remains a separate non-goal.
  - Preregistered check: Trigger: any btree checked-lib gate failing after the node-size/fanout tuning budget, or a v1 scenario requiring a concurrent ordered map.
- **layout schema mechanism (compiler-known layouts)** — Declarative field/endian/offset schemas with trusted lowering to accesses and facts.
  - Why this tier: A schema cannot beat 1 load — its wins are ergonomic; the trusted generator's failure mode is silent OOB. Deferred-with-trigger rather than dead, per the layout falsifier.
  - Preregistered check: Trigger: layout Gate 1/Gate 2 failures, or measured evidence that the wrong-offset logic-bug class causes unacceptable defect rates in corpus-format modules despite card discipline.
- **cas-cell** — Raw compare-exchange scalar cell.
  - Why this tier: Every nominated scenario maps to a kept member, and the residual raw-CAS protocols are unbuildable on this floor anyway (no second atomic, no uninit slots), so the member completes no user program; reinstatement must clear the full D16 bar INCLUDING the memory-model teaching burden it drags back in.
  - Preregistered check: Trigger: the necessity sweep finds a scenario kernel that cannot reach 1.10x of its named reference without a raw CAS retry loop.
- **seqlock-cell** — Version-stamped optimistic-read cell for high-rate telemetry.
  - Why this tier: Publish/snapshot cell cannot express seqlock reads, but no v1 scenario needs them; additive later.
  - Preregistered check: Trigger: a version-stamped optimistic-read scenario enters the v1 set with a par target the mutex/cell routes miss.
- **steal user endpoint (conc_queue)** — User-visible work-stealing deque endpoint.
  - Why this tier: Users cannot spawn the threads a hand scheduler needs; the deque stays at crossbeam parity inside par.
  - Preregistered check: Trigger: the par route misses the 1.10x irregular fork-join band AND a user steal endpoint demonstrably closes the gap.
- **shared<T> update-with row** — In-place read-modify-publish helper on shared<T>.
  - Why this tier: Unevidenced convenience; the writer-mutex route is the one spelling and is stated normatively on the COW card.
  - Preregistered check: Trigger: a scenario where the mutex+publish pair misses a preregistered band that update-with closes.

## Cut log (every change vs the pass-1 catalog)

- ring/deque sealed variant -> CUT to one unified FIFO card + deferred sealed inline-affine deque. Card errors from the attack fixed before blessing: as_slices returns a single slice in the unwrapped case (the two-slice formula only when head&m >= tail&m wraps); backing store corrected from fixed-length buffer to runtime-pow2 boxed slice/seq with the pow2 fact established at construction; the masked-bound elision is explicitly F1-gated, not assumed.
- btree sealed kernel -> CHECKED-LIBRARY, made internally consistent: the seq-inline trim it contradicted is REVERSED (seq<T,inline N> kept and its embeddability pinned by a preregistered gate), and the rebalancing MAJOR is resolved by promoting pool's disjoint two-slot &uniq borrow from optional to a required, charged, hostile-reviewed row — eliminating handle reminting that would have invalidated the sibling leaf chain. Fails closed to deferred sealed btree.
- seq inline (SmallVec) knob trim -> REVERSED (kept sealed). Two independent reasons: btree's node representation load-bears on embeddable inline seq (the FATAL contradiction), and wfc — the flagship workload — is exactly the SmallVec-hungry shape the defer bet against, with the three-word-header ABI freeze making later re-admission a breaking change. The defensible half of the audit's trim (table inline=N) is taken instead.
- table inline=N tiny-map knob -> CUT to the linear-scan card, with the card's mechanism error fixed: parallel keys/vals seqs (SIMD cannot scan keys interleaved in tuples) and a stated scalar early-exit fallback.
- layout-schema mechanism -> CUT to validated-view card + checked format libraries. Fixed-offset half binds now (constant-offset domination is the measured easy case; a schema cannot beat 1 load); variable-offset half is F3-gated with a fail-closed retained-branch measurement. The wrong-offset objection is rebutted as an accepted logic-bug/safety-bug trade: the schema's trusted generator risked silent OOB, which D16 weighs heavier than a checked wrong-field read mitigated by shipping the corpus formats as libs.
- sealed sort core -> CHECKED-LIBRARY, recorded as CONDITIONAL on fact-extension F2 (type-range facts) per the overdraft MAJOR, with the radix scatter's prefix-sum index explicitly carved out of the elision claim and a retained-bounds fallback measurement path; stable affine-T sort separately deferred.
- rcu_table -> TRIMMED to two cards (COW-republish + sharded-mutex-map); papaya-class in-place table deferred with a quantified regime trigger; card text pins the papaya-also-derefs comparison so the read-latency band is not mis-scored, and the M7 update band is armed only after measuring the sealed table's clone constant.
- wal sealed kernel -> CHECKED-LIBRARY over enumerated io-file rows; the dependency inversion from the attack is fixed — fdatasync/rename/dir-fsync/O_DIRECT-open/block-size rows are enumerated and charged in io-file and verified BEFORE ratification; the shipped lib copies payloads outside the leader lock.
- cas-cell -> CUT from sync (coverage argument: every scenario maps to a kept member; residual raw-CAS protocols are unbuildable on this floor so the member completes no user program); relaxed counter's 'no publication' rule promoted to normative spec text; reinstatement bar includes the full memory-model teaching cost.
- publish/snapshot cell -> payload domain PINNED to Copy words with a normative 'no heap publication — use shared<T>' rule line, resolving the two-sealed-spellings MAJOR by making cell and shared<T> disjoint domains rather than merging them.
- shared<T> update-with row -> CUT as unevidenced convenience; multi-writer mutation routes through the external mutex, stated normatively on the COW card.
- steal endpoint -> DEMOTED from conc_queue user endpoint to internal detail of threads+par (visibility change, not code); re-exposure trigger preregistered.
- spsc endpoint -> keep made CONDITIONAL on the necessity sweep (mpmc in-band on pipeline kernels moves spsc to deferred).
- evring -> DEFERRED out of the io family: zero frozen-corpus consumers, purely additive later; the io family itself is enumerated row-by-row with per-row scenario evidence, ending the unauditable 'family' keep.
- condvar keep -> converted from speculative to EVIDENCED by recording io-wal's leader-follower group commit as its named scenario, closing the cross-unit trap where a later trim pass could cut wal's substrate.
- pool<T> -> +1 op row (checked disjoint two-slot &uniq borrow), an ADDITION logged and charged against the btree cut's savings, subject to hostile review as new sealed surface.
- wbuf -> conditional +1 member (copy_within_extend) ONLY if the loan judgment rejects the self-alias LZ read+append; charged as fact-adjacent trusted surface requiring hostile review, correcting the zero-cost bookkeeping the attack flagged.
- machine core -> intrinsic list FROZEN with a one-line admission rule (named consumer kernel/corpus op + portable fallback semantics, through the D16 gate), closing the std::arch-accretion vector.
- tbuf<T> typed prefix-extent primitive -> explicitly ADJUDICATED AND REJECTED for v1 (resolving the cross-cutting FATAL) with a named checker limitation: per-index typed initialization is a dependent-class judgment outside the per-binding discipline, and the sound whole-prefix approximation merely relocates seq's trusted relocate/take-replace codegen into language rules without removing it; recorded as the standing deferred alternative with a two-capability trigger.
- FIFO story -> the primitives-audit two-stack card and the ring card RECONCILED into one taught spelling with one preregistered band ([0.90x,1.10x] vs VecDeque — the stricter number), eliminating the band-shopping hazard; two-stack survives only as the affine amortized-fallback subsection.
- Catalog accounting -> honest totals published for the first time (10 sealed objects, ~85-100 rows, ~15-24k trusted LOC vs ~130-160 rows / ~25-35k pre-cut); member-level audits for threads+par and the residual io family scheduled as blocking items before freeze.

## Deferred list with triggers

- tbuf<T> typed prefix-extent affine buffer — trigger: >=2 typed-uninit-blocked deferred capabilities (inline-affine deque, stable affine sort, embeddable-slots need) acquire corpus-evidenced par demands; then adjudicated head-to-head against sealing each individually.
- Sealed inline-affine ring/deque — trigger: an inline-affine deque hot path enters the target scenario set, or pool-handle route >1.25x vs inline VecDeque on a target workload, or F1 fails review/demonstration.
- rcu_table (papaya-class concurrent table) — trigger: declared v1 scenario needing >1e5 in-place updates/s with >=12x concurrent read scaling and <1ms visibility, or any M7 COW band (a)-(c) failure.
- evring (io_uring-class async submission) — trigger: a v1 scenario whose par target demonstrably needs high-QD async submission beyond synchronous file rows + threads; admission includes hostile review of the kernel-shared-ring lifecycle.
- Stable affine-T merge-sort core — trigger: corpus-evidenced demand for par stable sort of affine T; adjudicated against tbuf's trigger first.
- table inline=N tiny-map knob — trigger: tiny-map card fails its 1.05x band on n in [1,8].
- Sealed btree — trigger: any btree checked-lib preregistered gate fails after the tuning budget, or a concurrent ordered-map scenario is declared.
- Layout schema mechanism — trigger: layout Gate 1/2 failures, or measured unacceptable wrong-offset defect rates in corpus-format modules despite card discipline.
- cas-cell — trigger: necessity sweep finds a scenario kernel that cannot reach 1.10x of its reference without a raw CAS retry loop; reinstatement must clear D16 plus the full memory-model teaching burden.
- seqlock-cell — trigger: a version-stamped optimistic-read (high-rate telemetry) scenario enters the v1 set with a par target the kept members miss.
- steal user endpoint — trigger: par misses the 1.10x irregular fork-join band AND a user steal endpoint demonstrably closes the gap.
- shared<T> update-with row — trigger: a scenario where the mutex+publish pair misses a preregistered band that update-with closes.
- spsc endpoint (contingent) — moves here if the necessity sweep shows mpmc within 1.10x on the pipeline kernels; re-admission trigger: pipeline kernels miss 1.10x with mpmc only.

## Open flags (load-bearing uncertainties)

- Fact extensions F1 (pow2-mask domination), F2 (type-range facts), F3 (runtime/element-wise offset facts) are the load-bearing uncertainty of the whole re-cut: each needs hostile review plus its preregistered elision demo (ring microbench disassembly; partition-loop facts report; SQLite cell-walk carry). Until each lands, its dependent verdicts (FIFO card par claim, sort-core cut, layout variable half) are provisional with fail-closed retained-bounds paths.
- seq<T,inline> embeddability as a pool-slot struct field with insert-at/remove-at/drain-range, and fact flow through the handle deref, is asserted from the kernel's design, not demonstrated — settled by the Gate 0 checker demo before any btree code is written; failure re-opens both the btree tier and the seq-inline keep rationale.
- threads+par and the residual io family (anything beyond the enumerated file rows) have NOT had the sync-trim-style member audit; both are blocking items before catalog freeze — the two largest trusted-LOC pockets cannot ship on habit.
- wbuf self-alias question (read view of initialized prefix concurrent with live append cursor) — settled by a loan-judgment paper check; if rejected, copy_within_extend goes to hostile review and the layout LZ gate waits on it.
- Sealed table clone constant (assumed ~50-100ns/entry) — must be measured before the M7 update band is a meaningful falsifier for the rcu_table trim; a 2-3x miss changes the COW card's honest coverage claim, not just the band.
- btree rebalancing expressibility under loan/freeze with the two-slot borrow (transient parent-handle rewrite without generation panics) — settled by paper check plus the smallest possible checker prototype before the library is committed to.
- file leaf-row OS semantics (dir-fsync behavior on non-Linux, 4Kn/512e block-size query correctness) — settled by the row-set verification run that must precede wal ratification.
- wfc tiny-vector exposure: the 1.10x SmallVec band on a wfc-shaped workload validates the seq-inline keep empirically; if arena-backed seq were somehow in-band there AND btree's gates failed, the inline keep could be revisited in a post-v1 trim pass — but not before both measurements exist.
- condvar remains the weakest sealed member on first principles; its keep is now evidenced by wal's leader-follower, so it is re-examined only if wal moves off condvar (e.g., onto a future evring path).
- Whether the pinned Copy-word publish/snapshot cell still covers every config-swap scenario in the necessity sweep after the payload restriction — the sweep re-runs those kernels split across cell (scalars) and shared<T> (heap state); a gap there re-opens the merge-vs-pin decision.