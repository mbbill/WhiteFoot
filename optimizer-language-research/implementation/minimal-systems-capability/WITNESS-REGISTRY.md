# Ordinary-Library and Held-Out Witness Registry

Status: proposed G0-Core research registry, 2026-07-14; pending final
exact-hash review and owner review. On G0-Core closure, this file freezes
research coverage purposes, observable contracts, family dependencies,
held-out budgets, and anti-special-casing rules for later lock drafting. That
research freeze is not a language, mechanism, experiment, or production
decision. This file contains no witness implementation, candidate mechanism,
harness, scored trace, or production authorization.

## 1. Claim being tested

Rust's standard library is a finite demand anchor, not a generativity proof.
Passing only Rust-shaped containers could mean that xlang or a privileged
standard library prebuilt those exact types. The stronger detailed claim is:

> Ordinary no-unsafe xlang libraries can implement the registered sequential,
> unique-owner collection and topology contracts efficiently through the same
> public checked mechanisms available to unrelated libraries.

This is not the complete general-purpose systems-language claim. Concurrency,
shared ownership, resources and FFI, custom allocation, async cancellation,
pinning/address-sensitive values, full text semantics, and target intrinsics
retain separate blocked claims in `SYSTEMS-DOMAIN-LEDGER.md`.

The witness set is deliberately finite. Visible witnesses separate known
topologies and failure obligations. Three training-excluded held-outs test one
direct-storage derivation and two cross-container invariants. A named data
structure need not become a kernel or standard-library type merely because it
is a witness.

## 2. Protected baselines

| ID | Contract | Protection |
|---|---|---|
| B-FIX | Existing fixed, fully initialized Copy buffer | Preserve its two-word owner, one allocation, fixed length, checked indexing, and optimized body. No capacity, occupancy, generation, sharing, or policy field/branch may appear. |
| B-P2 | Existing append-only SoA/index pool | Preserve non-reused indices and the measured append-only access path. No generation, recycling, sparse-state, shared-ownership, or provenance branch may appear. |

These controls run for every family even when that family does not use their
topology. A shared substrate is rejected if its generality becomes a tax on
either protected contract.

### 2.1 Closed dependency vocabulary

Every dependency budget below is an exact allowlist. A token must be one of:

- an exact capability ID from `CAPABILITY-OBLIGATION-REGISTRY.tsv`;
- an exact canonical contract ID from `RUST-DATA-CONTRACT-CENSUS.tsv`;
- a baseline or witness ID defined in this file;
- one of the exact family-closure IDs below; or
- a named frame ID from `SYSTEMS-DOMAIN-LEDGER.md`.

| ID | Exact meaning |
|---|---|
| `K-SCALAR` | The existing checked scalar, Boolean, index, control-flow, `Option`-class, and `Result`-class kernel operations. It grants no storage transition, callable behavior, unchecked memory access, or privileged frame. |
| `FAM-DENSE` | The selected ordinary-library dense affine sequence public contract, but only after its own family lock, evidence, hostile review, and adoption close. |
| `FAM-UMAP` | The selected ordinary-library unordered map public contract, but only after its own family lock, evidence, hostile review, and adoption close. |

Wildcards, prefixes, negated sets, and prose aliases are forbidden in a budget.
Adding a future capability whose ID shares a prefix with an allowed token does
not widen any budget. A family-closure token permits only that family's frozen
public API; it never imports its private representation or implementation
capabilities. A frame token likewise grants only its reviewed public checked
caller contract. It never grants raw payload access, manual liveness authority,
unchecked capacity mutation, allocator-identity forgery, manual deallocation,
or any other private frame privilege.

## 3. Visible capability and topology witnesses

The mandatory operation canaries in the D11 capability matrix remain in force.
The table below refines the ordinary-library topology witnesses that prevent a
named-container-only result.

| ID | Role | Frozen observable contract | Separating purpose | Capability dependency budget |
|---|:---:|---|---|---|
| W-POOL | W | Insert, shared `get`, replace, and remove affine payloads through finite copyable logical handles; a returned borrow is tied to the pool and blocks incompatible mutation. Each slot generation advances without wrap; reaching its maximum retires that slot permanently. The pool has a frozen maximum slot count, so insertion returns `IdentityExhausted` with the offered owner unchanged before any stale handle could revive. Storage/history is O(maximum slots), including retired slots. A same-typed handle from another pool is a memory-safe logic error with no guaranteed rejection. Access/update/removal are O(1), and disposition is exact. | Distinguishes reusable storage and temporal freshness from an append-only index or a bare-key slab. | `K-SCALAR`, `ST-SPARSE`, `OW-INIT`, `OW-MOVEOUT`, `OW-REPLACE`, `OW-DROP`, `EX-NORMAL`, `EX-ABANDON`, `EX-ABORT`, `BR-PROV`, `BR-REBORROW`, `BR-RESULT`, `BR-INVALIDATE`, `FL-CAPACITY`, `FL-ALLOC`, `FL-ATOMIC`, `ID-LOGICAL`, `ID-FRESH`, `ID-POOL`, `FT-STATE`, `FT-IDENTITY`, `AB-SEAL`, `AB-GENERIC` |
| W-ARENA | W | Amortized O(1) phase allocation returns a borrow tied to the arena; that borrow remains valid across later arena allocations, and reset/destroy is rejected until every phase borrow ends. No individual free exists; after borrows end, reset/destroy disposes every complete affine payload exactly once, drops exactly the initialized subvalues of partial construction, and never treats an incomplete object or dead slot as T. Recoverable allocation failure leaves all existing contents unchanged and returns or preserves the offered affine input. For a lock-frozen regular-chunk usable-byte budget C, non-oversized backing allocation calls are at most `ceil(total_aligned_requested_bytes / C) + 1`; C must hold at least eight minimum test payloads. Dedicated oversized allocations are classified separately. Calls, chunk count, slack, peak memory, and growth policy are charged. No logical identity, observable address promise after a borrow ends, self-reference, `Pin`-class projection, or pre-drop notification is implied. | Bulk phase reclamation differs from per-slot deletion and from Rust bump allocators that intentionally skip payload destruction, without importing the deferred address-stability family. | `K-SCALAR`, `ST-DENSE`, `OW-INIT`, `OW-DROP`, `EX-NORMAL`, `EX-ABANDON`, `EX-ABORT`, `BR-PROV`, `BR-REBORROW`, `BR-RESULT`, `BR-INVALIDATE`, `FL-CAPACITY`, `FL-ALLOC`, `FL-ATOMIC`, `AB-SEAL`, `AB-GENERIC`, `FT-STATE`, `F-ALLOC` |
| W-SMALL | W | No heap allocation through inline capacity N; insertion at N+1 performs one sound spill; contiguous slice semantics survive; affine pop/remove/drop work; failed spill preserves the original owner and offered input; automatic spill-back is not required. | Exposes a one-time representation transition and an externally measurable allocation ceiling absent from an ordinary growable sequence contract. | `K-SCALAR`, `ST-FULL`, `ST-DENSE`, `ST-HOLE`, `OW-INIT`, `OW-MOVEOUT`, `OW-REPLACE`, `OW-RELOCATE`, `OW-DROP`, `EX-NORMAL`, `EX-ABANDON`, `EX-ABORT`, `BR-PROV`, `BR-REBORROW`, `BR-RESULT`, `BR-INVALIDATE`, `FL-CAPACITY`, `FL-ALLOC`, `FL-ATOMIC`, `AB-SEAL`, `AB-GENERIC`, `FT-STATE`, `F-ALLOC` |
| W-RECUR | W | Finite layout, unique recursive construction and node extraction, mutable cursor, exact partial-construction cleanup, and bounded-stack destruction for adversarial depth. | Tests unique recursive ownership without importing shared ownership or stable raw addresses. | `K-SCALAR`, `BOX-NEW-01`, `OW-MOVEOUT`, `OW-REPLACE`, `OW-DROP`, `EX-NORMAL`, `EX-ABANDON`, `EX-ABORT`, `BR-PROV`, `BR-REBORROW`, `BR-RESULT`, `BR-INVALIDATE`, `BR-CURSOR`, `FL-CAPACITY`, `FL-ALLOC`, `FL-ATOMIC`, `AB-SEAL`, `AB-GENERIC`, `F-ALLOC` |
| W-GRAPH | W | Frozen CSR has O(V+E) storage and contiguous edge scans. Dynamic form has stable non-reviving node/edge identities, O(1) lookup, O(local degree) node removal including incident edges, unrelated-handle stability, and O(1) known-neighbor handle-based splice/rewire. | A pool alone does not test referential integrity, cascading mutation, or multi-node repair. Handle-based rewiring is the safe analogue under the current pin/intrusive deferral. | `K-SCALAR`, `FAM-DENSE`, `W-POOL`, `ST-DEPENDENT`, `OW-MOVEOUT`, `OW-REPLACE`, `OW-DROP`, `EX-NORMAL`, `EX-ABANDON`, `EX-ABORT`, `BR-PROV`, `BR-REBORROW`, `BR-RESULT`, `BR-DISJOINT`, `BR-INVALIDATE`, `BR-CURSOR`, `FL-CAPACITY`, `FL-ALLOC`, `FL-ATOMIC`, `ID-LOGICAL`, `ID-FRESH`, `ID-POOL`, `FT-STATE`, `FT-IDENTITY`, `AB-SEAL`, `AB-GENERIC`, `IT-SHARED`, `IT-UNIQ` |
| W-ECS | W | Two or three fixed archetypes suffice. Entity identity remains stable while adding/removing a component migrates aligned affine columns; swap-removal repairs the displaced entity's reverse location; column scans remain contiguous; no per-entity allocation; failure duplicates or loses no payload. | Existing append-only compiler SoA does not test atomic movement across several aligned buffers plus reverse-index repair. | `K-SCALAR`, `FAM-DENSE`, `W-POOL`, `ST-DENSE`, `ST-DEPENDENT`, `ST-HOLE`, `OW-INIT`, `OW-MOVEOUT`, `OW-SWAP`, `OW-RELOCATE`, `OW-DROP`, `EX-NORMAL`, `EX-ABANDON`, `EX-ABORT`, `BR-PROV`, `BR-REBORROW`, `BR-RESULT`, `BR-DISJOINT`, `BR-INVALIDATE`, `FL-CAPACITY`, `FL-ALLOC`, `FL-ATOMIC`, `ID-LOGICAL`, `ID-FRESH`, `FT-STATE`, `FT-IDENTITY`, `AB-SEAL`, `AB-GENERIC`, `IT-SHARED`, `IT-UNIQ` |
| W-GAP | W | Logical sequence content is independent of gap position; shared indexed observation returns an owner-tied borrow; insert/delete at the gap are amortized O(1); moving the gap is O(distance); the hole is never readable or droppable as T; growth and recoverable failure preserve the old logical sequence. Use bytes and affine records, not Unicode semantics. | Separates a simultaneous initialized prefix and suffix from a one-prefix owner or arbitrary sparse bitmap, and prices direct bulk movement. | `K-SCALAR`, `ST-DENSE`, `ST-HOLE`, `OW-INIT`, `OW-MOVEOUT`, `OW-RELOCATE`, `OW-DROP`, `EX-NORMAL`, `EX-ABANDON`, `EX-ABORT`, `BR-PROV`, `BR-REBORROW`, `BR-RESULT`, `BR-INVALIDATE`, `FL-CAPACITY`, `FL-ALLOC`, `FL-ATOMIC`, `FT-STATE`, `AB-SEAL`, `AB-GENERIC`, `F-ALLOC` |
| W-PIPE | W | An ordinary external library composes lazy sources, nested stateful transform/select adapters, a two-input adapter, and an early-stop or recoverable-error consumer over shared, unique, and owning affine inputs. Output order, callback order/count, progress, and exhaustion are exact. Every early stop, error, and permitted abandonment leaves borrows valid and disposes each consumed and remaining owner exactly once. Advisory size hints never authorize unchecked access or uninitialized reads. | Separates reusable traversal composition from one hand-written loop and tests whether xlang can derive a zero-materialization pipeline without copying Rust's trait surface. | `K-SCALAR`, `BR-PROV`, `BR-REBORROW`, `BR-RESULT`, `BR-INVALIDATE`, `BR-CURSOR`, `OW-MOVEOUT`, `OW-DROP`, `EX-NORMAL`, `EX-ABANDON`, `EX-ABORT`, `FL-CALLBACK`, `AB-BEHAVIOR`, `AB-STATEFUL`, `AB-GENERIC`, `IT-SHARED`, `IT-UNIQ`, `IT-OWN`, `IT-COMPOSE` |

W-PIPE's structural gate rejects every intermediate collection, adapter heap
allocation, per-element allocation, indirect behavior call, stronger-than-
O(depth) live adapter state, and avoidable second source pass. It compares the
ordinary-library composition with a hand-fused xlang loop and the equivalent
idiomatic Rust 1.97.0 pipeline under matched callbacks and inputs. Code-size
growth from monomorphization remains a charged output rather than a hidden
cost.

### 3.1 Visible controls and optional compositions

- **O-SLAB:** a bare reusable integer-key slab is a weaker performance/control
  contract. Its stale-key alias risk must be explicit. It cannot discharge
  W-POOL.
- **O-ROPE-UNIQUE:** a uniquely owned rope may be admitted later as composition
  over growable chunks and ordered recursive nodes. O(1) clone or persistent
  snapshots depend on the shared-ownership deferral and are not implied.
- **O-INTRUSIVE:** true pointer-intrusive, self-referential, or multiple-membership
  structures remain scoped to the pin/address family. W-GRAPH's handle-based
  known-neighbor rewiring is required now; it does not claim address pinning.
- **O-LAZY-DRAIN:** the lazy partially consumed form remains optional unless a
  family promotes it. Eager drain/compaction remains mandatory. The lazy form
  cannot inherit correctness from Rust's `Drop` guards without an xlang exit
  proof.

## 4. Exact held-out contracts

The semantic contracts and dependency budgets below are visible and frozen.
Candidate source, tests, traces, and performance observations remain excluded
until Candidate Freeze B. A held-out may not be used for candidate training,
manual tuning, compiler pattern recognition, or threshold selection.

### H-STORE — direct storage substrate: bounded-key sparse set

Caller-visible contract:

- creation fixes a key universe `[0, U)` but constructs no payload value;
- `insert(key, own T)` admits at most one live payload per key and preserves or
  returns the offered owner on duplicate key or recoverable failure;
- `contains` and shared `get` are O(1); the returned borrow is tied to the set
  owner and blocks incompatible mutation; `remove` is O(1) and returns the
  affine payload;
- shared live iteration is O(n), visits each current key/value exactly once by
  owner-tied borrow, and makes no stable-order promise across removal;
- there is no per-element heap allocation;
- payload storage is O(capacity), key-position metadata is O(U), and operation
  traces freeze both terms separately; and
- removal, swap-repair, clear, destruction, and every failure path preserve the
  key-to-position/value relation and exact drop.

Allowed dependencies:

`K-SCALAR`, `ST-FULL`, `ST-DENSE`, `ST-DEPENDENT`, `ST-HOLE`, `OW-INIT`,
`OW-MOVEOUT`, `OW-REPLACE`, `OW-SWAP`, `OW-RELOCATE`, `OW-DROP`,
`EX-NORMAL`, `EX-ABANDON`, `EX-ABORT`, `BR-PROV`, `BR-REBORROW`,
`BR-RESULT`, `BR-DISJOINT`, `BR-INVALIDATE`, `BR-CURSOR`, `FL-CAPACITY`,
`FL-ALLOC`, `FL-ATOMIC`, `AB-SEAL`, `AB-GENERIC`, `IT-SHARED`, `FT-STATE`,
and `F-ALLOC`.

Anti-privilege rejection criteria:

The allowlist above is exhaustive; every unlisted dependency is rejected
mechanically. The following examples are additional review canaries, not a
second negated dependency budget:

- any finished growable sequence, map, set, pool, slab, small-sequence, or ECS
  library;
- a container-specific intrinsic, compiler opcode, recognizable source-name
  rule, or sealed-standard-library raw payload access; and
- shared ownership, pinning, concurrency, custom allocators, or unsafe FFI.

H-STORE therefore tests public checked storage transitions directly. `F-ALLOC`
permits only its reviewed public checked allocation facade. It grants no raw
bytes, manual liveness authority, unchecked capacity change, allocator-identity
forgery, or manual deallocation, and H-STORE cannot rebuild or expose the frame.

### H-LRU — composition under two-way coherence

Caller-visible contract:

- construction takes a fixed positive capacity, preallocates the complete
  steady-state backing budget, and either returns an empty cache or a
  recoverable allocation/capacity error with no live partial cache;
- lookup takes unique cache access; success promotes exactly that key to most-
  recently used, then returns a shared result-reborrow tied to the cache owner.
  The result blocks subsequent incompatible mutation until it ends;
- missing lookup returns `None` and leaves order unchanged;
- insertion of a new key below capacity consumes the offered key/value and
  returns `Inserted`;
- insertion of an equivalent existing key atomically replaces both stored key
  and value, promotes the entry, consumes the offered pair, and returns
  `Replaced(old_key, old_value)` with both old owners;
- insertion of a new key at capacity consumes the offered pair, reuses
  preallocated storage, promotes the new entry, and returns
  `Evicted(old_key, old_value)` for exactly the least-recently-used pair;
- removal returns `Some(owned_key, owned_value)` or `None` without mutation;
- no successful steady-state lookup/insert/update/remove performs a backing
  allocation; any recoverable pre-commit failure returns every offered affine
  owner and leaves membership, order, and payloads unchanged;
- expected O(1) get/insert/remove under the frozen hash/adversary assumptions;
- no per-operation scan of all entries; and
- hash membership, stable identity, linked order, payload ownership, and
  failure behavior remain coherent. Hash/equality traps follow EFF-4: no
  recoverable post-state is promised, but no invalid access occurs before
  abort.

Dependency budget: `K-SCALAR`, `FAM-UMAP`, `W-POOL`, `BR-PROV`,
`BR-REBORROW`, `BR-RESULT`, `BR-INVALIDATE`, `OW-MOVEOUT`, `OW-REPLACE`,
`OW-DROP`, `EX-NORMAL`, `EX-ABANDON`, `EX-ABORT`, `FL-CAPACITY`, `FL-ALLOC`,
`FL-ATOMIC`, `FL-CALLBACK`, `AB-BEHAVIOR`, `AB-SEAL`, and `AB-GENERIC`.
Only the frozen public APIs of `FAM-UMAP` and `W-POOL` are importable. H-LRU
may not receive new raw storage privilege or a compiler-recognized LRU path.
It is a composition witness and cannot substitute for H-STORE.

### H-IPQ — composition under heap/reverse-index coherence

Caller-visible contract:

- keyed items are unique;
- peek is O(1) and returns `None` or a pair of coexisting shared key/priority
  borrows tied to the queue;
- successful push consumes the offered owned key/priority pair; a duplicate
  returns `Duplicate(owned_key, owned_priority)` with the queue unchanged, and
  a recoverable capacity/allocation failure returns
  `Failure(error, owned_key, owned_priority)` with the queue unchanged;
- pop returns `None` or the owned minimum/maximum key/priority pair selected by
  the frozen order direction;
- keyed removal returns `None` or the owned matching key/priority pair;
- priority change returns `Missing(owned_new_priority)` without mutation, or
  consumes the new priority and returns `Changed(owned_old_priority)` while
  retaining the stored key owner;
- push, pop, keyed removal, and priority change are O(log n);
- every heap exchange atomically repairs the keyed reverse position;
- ownership and failure behavior are exact for affine item/priority payloads;
- comparison/hash/equality traps follow EFF-4 and perform no invalid access
  before abort; recoverable allocation failure occurs before destructive
  commit; and
- no operation repairs coherence by an O(n) search.

Dependency budget: `K-SCALAR`, `FAM-UMAP`, `FAM-DENSE`,
`BR-PROV`, `BR-REBORROW`, `BR-RESULT`, `BR-DISJOINT`, `BR-INVALIDATE`,
`OW-INIT`, `OW-MOVEOUT`, `OW-REPLACE`, `OW-SWAP`, `OW-DROP`, `EX-NORMAL`,
`EX-ABANDON`, `EX-ABORT`, `FL-CAPACITY`, `FL-ALLOC`, `FL-ATOMIC`,
`FL-CALLBACK`, `AB-BEHAVIOR`, `AB-SEAL`, and `AB-GENERIC`. Only the frozen
public APIs of `FAM-UMAP` and `FAM-DENSE` are importable; the held-out itself
implements heap order and reverse-index repair through those APIs. H-IPQ
receives no finished heap, bespoke compiler path, or exchange hook and cannot
substitute for H-STORE.

## 5. Ordinary-library generativity gate

Every W and H witness must satisfy all of the following:

1. Compile as an ordinary external xlang library with the same compiler
   artifact and public capability set used for unrelated programs.
2. Import only its frozen dependency allowlist. No privileged module, hidden
   intrinsic, container-specific opcode, unchecked payload access, or
   standard-library-only transition is legal.
3. Pass negative canaries for inaccessible-state reads, duplicate/drop loss,
   interrupted transitions, stale identity, overlapping mutable places,
   partial construction, and all applicable failure points.
4. Meet frozen asymptotics before timing, then report allocation count,
   initialized/touched/moved bytes, live/high-water/transient memory, metadata,
   checks, branches, code size, and failure injection where applicable.
5. Demonstrate that facts-off changes only retained checks/performance, never
   acceptance or semantics.
6. Reject candidate-specific compiler recognition even if the result is fast.

A standard-library implementation may serve as a reviewed witness of API
sealing, but it cannot alone close W or H. This gate is the difference between
"xlang ships useful containers" and "ordinary libraries can build an unseen
efficient structure."

## 6. Holdout custody and rotation

- G0-Core freezes the contracts, budgets, and exclusion rules above.
- Family Lock A freezes exact test-oracle schemas, payload classes, targets,
  trace families, endpoints, and the custodian responsible for source/tests.
- Before candidate construction, the custodian records hashes of the hidden
  source, tests, trace generator, and sealed inputs outside candidate-visible
  material. Candidate agents receive only the visible contract and allowlist.
- Candidate Freeze B records candidate hashes first; only then may the held-out
  implementation and immutable scoring inputs be disclosed to the scoring
  process.
- Any leak, candidate-specific correction, compiler recognition, or post-freeze
  semantic/gating change compromises the held-out. The family lock reopens and
  the custodian rotates to a new implementation within the same frozen contract
  and dependency budget. The compromised result is diagnostic only.
- H-STORE, H-LRU, and H-IPQ are logically independent. One passing held-out
  cannot compensate for another failure.

No hidden artifact is created by G0-Core; custody begins only under a separately
authorized Family Lock A. This avoids false claims that a plaintext repository
fixture is training-excluded.

## 7. Primary evidence

- Rust's intentionally bounded standard collection set:
  <https://doc.rust-lang.org/1.97.0/std/collections/>
- Generational identity and exhaustion pressure:
  <https://docs.rs/generational-arena/latest/generational_arena/>
- Bare slab key reuse:
  <https://docs.rs/slab/latest/slab/>
- Phase/bump arena behavior:
  <https://docs.rs/bumpalo/latest/bumpalo/>
- Inline-to-heap sequence transition:
  <https://docs.rs/smallvec/latest/smallvec/>
- Stable graph mutation:
  <https://docs.rs/petgraph/latest/petgraph/stable_graph/struct.StableGraph.html>
- ECS table/archetype storage:
  <https://docs.rs/bevy_ecs/latest/bevy_ecs/storage/> and
  <https://docs.rs/bevy/latest/bevy/ecs/archetype/>
- Movable gap behavior:
  <https://www.gnu.org/software/emacs/manual/html_node/elisp/Buffer-Gap.html>
- LRU contract:
  <https://docs.rs/lru/latest/lru/struct.LruCache.html>
- Indexed priority queue contract and costs:
  <https://docs.rs/priority-queue/latest/priority_queue/priority_queue/struct.PriorityQueue.html>
- Address-sensitive/intrusive motivation:
  <https://doc.rust-lang.org/1.97.0/std/pin/> and
  <https://docs.rs/intrusive-collections/latest/intrusive_collections/>
- Rope composition and sharing distinction:
  <https://docs.rs/ropey/latest/ropey/struct.Rope.html> and
  <https://research.google/pubs/ropes-an-alternative-to-strings/>
