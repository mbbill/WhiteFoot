# Minimal Systems Capability Basis: G0-Core Synthesis

Status: pre-review synthesis, 2026-07-14. This report selects no language
mechanism, syntax, runtime representation, privileged transition, compiler
path, standard-library type, benchmark candidate, or production change.

## 1. Result

The research supports a bounded answer, but not the originally tempting one.
The minimum cannot be a list such as "four storage states plus three language
features," and it cannot be one universal container substrate. Storage
topology, ownership transition, normal-exit closure, destruction, borrowing,
failure, identity, semantic refinement, behavior calls, optimizer facts, and
structural cost are independent proof dimensions. A candidate language
mechanism may discharge several dimensions, but no mechanism name proves them
by itself.

The defensible G0-Core result is therefore:

1. a finite external demand anchor and an exact accounting boundary;
2. a registry of caller contracts and semantic proof obligations;
3. global safety, lifecycle, generativity, and no-tax laws;
4. topology and cross-container witnesses that separate superficially similar
   designs;
5. explicit gaps in current xlang and explicit later systems families; and
6. an evidence protocol by which a later family can compare concrete
   mechanisms without smuggling one into this research result.

This is a capability **obligation basis**, not a selected primitive basis. The
smallest production mechanism set remains an empirical Pareto question. It can
be answered only family by family after exact semantics, reference algorithms,
soundness attacks, structural costs, workloads, and selection rules are frozen.

## 2. Evidence boundary

The finite anchor is stable public Rust 1.97.0 `core`, `alloc`, and `std`, at
annotated tag `eca4cdea45792600b4275e9d4c64fd827d575a24`, peeled commit
`2d8144b7880597b6e6d3dfd63a9a9efae3f533d3`. The checked inventory contains:

- 290 reachable public modules, with 28 architecture/intrinsic catalogs
  retained as digest-backed collapsed ledgers;
- 16,432 rendered declaration rows;
- 9,874 stable-safe and 554 stable-unsafe renderings;
- 5,096 canonical stable-safe and 273 canonical stable-unsafe source
  declarations; and
- exact extraction-policy, source, tool, count, and output hashes.

All 5,369 canonical stable declarations are routed through the applicable
public-facing domains of a 26-domain systems ledger, with Rust caller safety
retained. D26 accounts cross-cutting compiler/runtime support rather than a
primary public declaration family. The classifier now uses two independent
axes. Surface evidence contains 4,609 safe contract anchors, 170 Rust-safe
boundary declarations, 273 unsafe boundary declarations, and 317 Rust-only
namespace/source declarations. Underlying needs independently route to 1,033
G0 contracts, 302 library contracts, 3,765 later-family contracts, seven
boundary-frame services, 43 redundant declarations, 217 declarations with no
independent need, and only two owner-authorized non-goals: panic unwind recovery
under current EFF-4. Rust-safe raw-pointer, manual-lifetime, leak, and
spare-capacity routes therefore remain boundary evidence rather than checked
xlang APIs, while their underlying partial-initialization, ownership, resource,
or platform need remains visible. The detailed data-contract census
independently normalizes the selected array,
slice, text, unique-owner, sequence, deque, list, heap, ordered and unordered
map/set, shared-owner, dynamic-borrow, and lifecycle surface. Its seed contains
545 canonical stable-safe inherent declarations, 35 stable-unsafe evidence
declarations, 118 one-hop helper types, selected protocol entrances, ownership
atoms, and allocation-failure contracts. A separate D10 map routes all 150
canonical stable iteration/range declarations exactly once: 132 iteration and
18 range declarations, with 107 declaration-to-contract routes and 43
redundant-surface routes. `ExactSize` and `Fused` remain separate, and the range
surface is split into 13 exact contracts. The resulting detailed census and
derivation matrix each contain 258 normalized rows. Contract clustering
preserves differences in ownership, failure, invalidation, order, identity,
cleanup, complexity, and structural cost.

Rust is used only as caller-demand and implementation-pressure evidence. Its
traits, destructors, raw pointers, unsafe internals, representations, and API
names receive no xlang presumption. Rust's standard library is also not treated
as sufficient: the witness registry adds stable pools, arenas, inline-small
sequences, recursive ownership, dynamic graphs, ECS migration, and gap storage,
plus three separately budgeted held-outs.

## 3. What the census establishes

### 3.1 Uninitialized or non-`T` storage is a semantic necessity

An efficient growable owner of arbitrary affine `T` needs allocated capacity in
which no `T` currently exists. Otherwise spare capacity requires constructing
dummy values, imposing hidden `Default`/`Clone`/`Copy`, or rebuilding on every
append. The required capability is not writer-visible raw bytes or
`MaybeUninit`; it is a checked state relation under which dead storage cannot be
read or dropped as `T`, and under which initialization, move-out, relocation,
failure, and destruction remain coupled.

### 3.2 One live-set representation is not performance-minimal

Full fixed storage, a dense prefix, a wrapped ring, sparse occupancy, dependent
node-local prefixes, and a temporary hole are separating topologies. A bitmap
can encode most of them, but charging bitmap memory and an occupancy branch to
every access would tax contracts whose live set is already proved by a length,
`head + len`, or compact node-local counters. Conversely, a single dense prefix
cannot directly express a deque, hash table, B-tree node, or gap without losing
the required complexity or layout contract.

The minimum is therefore semantic support for the relevant live-set proofs,
with family-selected representations that erase proof state when existing
metadata suffices. It is not a runtime enum carried by every owner.

### 3.3 Steady state is insufficient

Push, pop, replacement, swap, growth, compaction, sorting, node split, rehash,
and cross-buffer migration are ownership transitions. They require conservation
of affine values through source, destination, and possible hole states. Merely
defining `Full` and `Vacant` does not prove commit ordering, failure ownership,
borrow invalidation, callback containment, or exact destruction.

Whole-place `replace` and runtime-disjoint affine `swap` are foundational
obligations rather than conveniences. Simulating replacement through extra
swaps or simulating local mutation through whole-structure rebuilds changes
element traffic and can violate the required asymptotic contract.

### 3.4 No unwind does not remove lifecycle obligations

xlang traps abort and run no cleanup. This removes Rust's panic-unwind repair
edges, but not fallthrough, `return`, `break`, `give`, recoverable error
propagation, callback return, owner destruction, or abandonment of an affine
protocol value. Current affinity prevents duplication but does not require a
value to be consumed. A rebuild token, drain cursor, entry guard, or partially
initialized owner is therefore unsound or unusable if validity depends on the
writer remembering to call `finish`.

Every admissible route must instead leave the base owner valid before an
abandonable value exists, establish an exact-use rule on every normal path, or
provide compiler-owned derived cleanup with fully specified semantics and cost.
G0-Core selects none of those alternatives.

### 3.5 Identity, address, and refinement are independent axes

Logical identity across relocation does not imply physical address stability.
Append-only indices do not imply safe recycling. A recyclable finite copied
handle cannot simultaneously promise indefinite reuse, memory bounded only by
peak live population, and permanent rejection of every stale handle; the
family must freeze exhaustion, retirement, history, revocation, or another
explicitly relinquished guarantee.

Likewise, initialized bytes do not imply UTF-8, sortedness, heap order, or tree
balance. These are refinement states established by checked producers and
preserved or invalidated by every mutation. `Rc`/`Weak` adds another independent
distinction between payload lifetime and allocation lifetime, while pinning
adds address stability and pre-invalidation obligations. Those latter families
remain outside the first detailed closure.

### 3.6 Metadata-to-payload relations are fact channels

A length, occupancy byte, generation, borrow flag, or refinement seal can
authorize a payload read or remove a check. It is therefore not ordinary
library metadata once the checker or optimizer relies on it. Every such fact
needs an exact proposition, owner and provenance, producer, state version,
scope, transfer rule, consumers, invalidators, speculation rule, facts-off
equivalence, artifact evidence, and hostile negative canaries. Splitting a
payload write from a forgeable `mark_full` operation is inadmissible.

## 4. The obligation basis

The checked registries contain 49 operational obligations, 12 orthogonal proof
dimensions, and 16 global laws. Their important groupings are:

- live-set and validity: full, fixed-record AoS, dense, ring, sparse,
  dependent, hole, and refinement obligations;
- affine ownership: initialize, move out, replace, swap, relocate, explicit
  clone, and exact drop;
- exit and failure: normal-exit closure, abandonment, abort boundary, checked
  capacity, allocation/OOM policy, failure atomicity, and callbacks;
- access: provenance, reborrow, result reborrow, borrow-bearing stored payloads,
  runtime disjointness, invalidation, and cursors;
- identity: logical identity, temporal freshness, pool provenance, physical
  address, and shared lifecycle;
- ordinary-library abstraction: sealing, static behavior, stateful behavior,
  and concrete generic instantiation;
- traversal: shared, unique, owning, and zero-materialization composed
  iteration;
- optimizer facts: live-state, refinement, identity, dynamic-borrow, and
  shared-lifecycle facts; and
- protected performance: no new field, branch, check, allocation, or code path
  on the fixed full-buffer or append-only SoA/index baselines.

This list is not a proposal to add one source construct per obligation. A good
candidate may prove many rows through a smaller checked substrate. It still has
to show, row
by row, that the proof and cost exist and that unrelated protected contracts do
not pay for its generality.

## 5. Current xlang status

Current xlang has useful but narrow evidence:

- fixed, fully initialized Copy buffers with checked indexing;
- unique heap ownership and compiler-derived simple normal-exit release;
- explicit affine moves of whole bindings, with whole-root death after partial
  move;
- lexical shared/unique borrow provenance and literal-index disjointness;
- checked size multiplication and aborting traps; and
- the measured append-only SoA/index pattern, with non-reused indices.

It does **not** currently establish general affine element storage, spare
capacity, move-out followed by owner reuse, affine replace/swap/relocation,
dynamic disjoint positions, exact live-subset drop, recoverable growth,
ordinary-library representation sealing, complete static behavior calls,
generic owning/unique cursors, zero-materialization traversal composition,
sparse metadata-to-payload facts, recyclable identity, UTF-8 seals, shared
lifecycle, address stability, or preservation of borrows stored inside moving
payloads. Most normalized owning-container contracts are therefore gaps, not
merely missing convenience APIs.

The result also confirms that several current design directions are necessary
but insufficient. Reborrow and result-reborrow are prerequisites for ergonomic
and efficient access, but they do not solve storage or cleanup. Encapsulation is
necessary to prevent forged length/occupancy state, but private fields alone do
not prove preservation. Monomorphized behavior can avoid vtable cost, but it
does not prove comparator law containment or partial construction.

The exact 258-row derivation matrix currently records four complete direct
routes (`E`), no evidence-backed complete pattern route (`P`), ten unproved or
narrow workarounds (`U`), 212 semantic/soundness/asymptotic/structural gaps
(`X`), four named frame dependencies, 19 scoped deferrals, and nine
Rust boundary-evidence rows whose raw/unchecked spelling is inadmissible while
the checked need remains routed. No true `NG` occurs in the detailed matrix;
the full classifier's two true non-goals are panic unwind recovery. `E` means
the complete normalized contract is directly established;
`P` is reserved for a derived pattern with correctness and performance
evidence; `U` never counts as closure. These are accounting rows, not equally
weighted features or an estimate that 212 language primitives are needed.

## 6. Ordinary-library and performance standard

A capability is not closed by showing that a privileged xlang standard library
could implement `Vec` or `HashMap`. It must support an ordinary external
no-unsafe library using the same checked public mechanisms available to an
unrelated library. It fails if it requires raw payload access, a hidden
container opcode, source-name recognition, a writer-called finalizer, or a
completed container outside its dependency budget.

The visible witnesses prevent census-specific overfitting. W-PIPE requires an
ordinary library to derive a reusable zero-materialization traversal pipeline,
not just one hand-fused loop. H-STORE tests the storage substrate directly with
a bounded-key sparse set and forbids importing a finished sequence, map, set,
pool, slab, small sequence, or ECS. H-LRU tests two-way coherence between keyed
membership, stable identity, linked order, and payload ownership. H-IPQ tests
heap/reverse-index coherence without O(n) repair. Their contracts and
dependency budgets are frozen, but no hidden source, trace, or scored input
exists until a separately authorized Family Lock A establishes custody.

Performance closure has two distinct controls:

1. same-shape attribution against Rust with matched algorithm,
   representation, capacity policy, allocator, payload, and trace, including
   facts-on/off and structural counters; and
2. end-to-end comparison between the selected canonical xlang route and the
   unmodified idiomatic Rust 1.97.0 standard-library route for the same
   observable contract.

G0-Core freezes no numeric timing margin. Each family must first prove its
asymptotic contract, then count allocations, initialized/touched/moved bytes,
live/high-water/transient memory, metadata, checks, branches, drops, code size,
and failure rollback. Only its Family Lock A may freeze algorithms, workloads,
targets, thresholds, and selection rules. This prevents a convenient benchmark
from silently redefining the capability.

## 7. Whole systems-language boundary

The 26-domain ledger makes the scope limit explicit. The first detailed closure
is only the sequential, unique-owner data-structure floor over region-free,
borrow-free payloads and its byte/UTF-8, iteration, behavior, lifecycle,
allocator-frame, and proof prerequisites. `BR-STORED` records the separate
stored-borrow family required before a complete sequential payload claim.

A general-purpose systems-language claim additionally remains blocked on
separate work for complete numerics; shared ownership and interior mutation;
pinning and address-sensitive values; custom allocation; formatting and build
integration; I/O, filesystems, processes, OS resources, FFI, networking, and
clocks; threads, atomics, synchronization, channels, and concurrent
reclamation; async execution and cancellation; complete Unicode text; target
SIMD/intrinsics; checked volatile device-memory/MMIO; and reviewed
compiler/runtime frames. `F-MMIO` records the minimum trust dossier:
authority/provenance, access width/alignment, non-elision, device-access
ordering, platform effects, and target/OS mapping. Rust's raw-pointer volatile
spelling remains inadmissible; the underlying systems need does not disappear.
Rust `std` also leaves negative space that needs separate anchors, including
cryptography/TLS, memory mapping and virtual-memory control, signals,
terminals, event multiplexing, secure randomness, serialization/protocol
boundaries, and dynamic-library policy.

Thus G0-Core can make the first family experiment eligible. It cannot support
the statement that xlang already covers systems programming.

## 8. E0.1 reconciliation

The old fixed-record experiment remains suspended. It mixed record layout,
semantic Copy, and partial live storage, which this research separates.
Declarative Copy remains one unselected fixed-AoS possibility; automatic
structural Copy and explicit Clone remain distinct alternatives; the old
affine exact-fill builder remains a useful control but does not support unknown
length, growth, pop, removal, arbitrary affine destruction, cross-call use, or
safe abandonment.

Every old arm, layout control, capacity policy, source-shape warning,
ownership-context audit, structural metric, numeric threshold, and migration
separation is carried into the traceability ledger. A later dense-family lock
must retain, revise, or supersede each item explicitly. G0-Core does not restart
E0.1 and supplies no reason to add a runtime mode flag or universal storage
representation.

## 9. Smallest defensible next request

After the exact artifact set passes hostile review, the smallest useful owner
discussion is whether to authorize drafting a **dense unique-owner Family Lock
A**. Dense storage is first because sequence growth, arbitrary affine
initialization/move-out/drop, replacement, swap, relocation, failure, and
iteration are dependencies of more later structures than any other one family.

That discussion would authorize only an exact lock, not implementation. The
lock would need to instantiate:

- arbitrary region-free, borrow-free affine payload scope or an honestly
  narrower claim;
- construction, append, pop, ordered and unordered removal, replace, swap,
  growth, reserve, shrink, truncate/clear, compaction, sorting, clone, views,
  and owning/unique traversal as applicable;
- normal exits, abandonment, exact live-prefix drop, allocation/capacity
  failure, callback behavior, and borrow invalidation;
- candidate and reference algorithms without assuming a winner;
- same-shape and end-to-end controls, structural counters, targets, payloads,
  traces, numeric margins, and protected B-FIX/B-P2 gates;
- applicable visible/held-out budgets and custody;
- exact fact propositions and hostile canaries; and
- the complete META-5 cost of every candidate spelling and checker/runtime
  change.

Only after that lock itself receives exact-hash hostile review and separate
owner approval could candidate experiments begin. Production language changes,
specification edits, xlc migration, default teaching, and E0.1 restart would
remain separately unauthorized.

## 10. Claims permitted by this report

Once its checked artifacts and final hostile reviews are recorded, this report
permits only the following claim:

> The sequential, unique-owner data-structure research boundary, its required
> caller contracts, semantic proof obligations, prohibited pathological
> simulations, lifecycle and fact-channel laws, protected baselines,
> generativity tests, and later-family boundaries are accounted well enough for
> the owner to review whether to authorize the first Family Lock A.

It does not claim that a minimal production mechanism set has been selected,
that current xlang can implement the floor, that any family is closed, that any
timing threshold has been met, or that the general-purpose systems-language
goal is complete.

## 11. Auditable artifact map

- `RUST-1.97.0-CENSUS-MANIFEST.json`, `RUST-1.97.0-API-INVENTORY.tsv`, and
  `RUST-1.97.0-MODULE-ACCOUNTING.tsv`: exact mechanical source census.
- `RUST-1.97.0-DOMAIN-CLASSIFICATION.tsv`,
  `RUST-1.97.0-MODULE-DOMAIN-MAP.tsv`, and
  `SYSTEMS-DOMAIN-LEDGER.md`: full-envelope destination accounting.
- `RUST-DATA-CONTRACT-CENSUS.tsv`: normalized detailed caller contracts.
- `RUST-D10-SURFACE-MAP.tsv`: exact 150-declaration iteration/range crosswalk,
  including redundant surface routes.
- `CAPABILITY-OBLIGATION-REGISTRY.tsv` and
  `SEMANTIC-OBLIGATION-REGISTRY.md`: operational obligations, proof laws, and
  source-backed lower bounds.
- `DERIVATION-MATRIX.tsv`: one contract-to-capability, current-status,
  ownership, cost, fact, canary, and later-gate record per normalized contract.
- `WITNESS-REGISTRY.md`: visible witnesses, exact held-outs, dependency
  budgets, and anti-special-casing rules.
- `E01-TRACEABILITY.md`: complete reconciliation of the paused experiment.
- `FAMILY-LOCK-A-TEMPLATE.md`: mandatory schema for any later family request.
- `G0-CORE-ARTIFACT-MANIFEST.json`: exact hashes for the research set and its
  controlling law, directives, plan, and design-memory inputs.
