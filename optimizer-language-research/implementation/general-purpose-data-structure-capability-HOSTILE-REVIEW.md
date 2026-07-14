# General-Purpose Data-Structure Capability Hostile Review

Status: PASS AS A RESEARCH BOUNDARY, 2026-07-13.

The exact reviewed
`general-purpose-data-structure-capability-RESEARCH.md` bytes have SHA-256:

```text
48384d74624c40dad13514232985d39df6fa5910ba5bf513cd39f941440d82c7
```

This verdict means that three independent read-only review scopes found no
remaining P0/P1 blocker in the research report. It does not select a language
mechanism, collection representation, standard-library surface, specification
delta, compiler implementation, xlc migration, performance winner, pattern, or
default teaching. It is not Lock A and authorizes no candidate implementation,
scored run, or external disclosure.

## 1. Review method

The report received separate hostile reviews for:

1. ownership, initialization, destruction, borrowing, cursor escape, sparse
   fact channels, failure atomicity, and stable-handle identity;
2. lower bounds, operation coverage, structural and runtime performance gates,
   R3 winner selection, workload/target sensitivity, and unsupported empirical
   claims; and
3. consistency with the Constitution, specification, MCTS-Mem tree and its
   alternatives, E0.1 pause, standing owner directives, META-5, and repository
   process.

The first merged snapshot received blocking findings in all three scopes. Those
findings were dispositioned in the report and the scopes re-read the final exact
snapshot above. All three independently returned `PASS` on those exact bytes.
Reviewers made no repository edits.

## 2. Ownership, state, and failure dispositions

### S1: initialized-prefix state was mistaken for a complete optimal mechanism

The rejected form treated `[0, len)` as enough for both steady state and every
efficient transition. Direct growth, ordered movement, stable retain, drain,
and partial construction can require a transient hole or separate source and
destination prefixes.

Resolution: the report distinguishes public steady-state coverage from
contained transient state. It keeps high-level atomic operations, a checked
linear transaction, and another generative mechanism live as candidates. An
unguarded writer-readable hole is rejected; a scoped take guard remains
eligible only if every non-trap exit restores or completes a valid state.

### S2: an affine token could be dropped without completing its protocol

Affineness prevents copying but not abandonment. The rejected form allowed a
hole-bearing rebuild token to repair or finish merely by being dropped, despite
current STOR-3 having no finalizers.

Resolution: current candidates must leave a valid owner at every non-trap escape
or token drop. Repair-on-drop is priced as a new kernel derived-cleanup/finalizer
rule, never assumed as an ordinary-library capability. The report separately
states that EFF-4 trap abort runs no cleanup and owes no recoverable post-state.

### S3: raw partial initialization could leak through a privileged library

A private `set_len`, `mark_full`, uninitialized tail, or unchecked payload read
would move unsafe from users into an unreviewable library protocol rather than
make the operation safe.

Resolution: every writer-callable transition must preserve a valid owner on its
own. Neither a sealed witness nor an ordinary library receives raw uninitialized
payload access or split control/payload privilege. H-STORE must directly use the
same public checked storage-state transitions available to an unseen library.

### S4: sparse occupancy was an unpriced optimizer fact channel

A Swiss-style `Full` control state can authorize payload access. If control and
payload state can diverge, the fact permits an uninitialized read, missed drop,
or double drop; masked SIMD loads can also probe non-live payload lanes.

Resolution: control-to-payload coherence is explicitly a hostile-reviewed fact
channel. Mutations invalidate derived facts, separately forgeable state is
rejected, and SIMD probing may not read payload for a lane that has not
established `Full`. Fully initialized tagged slots remain a measured candidate
rather than a prejudged failure.

### S5: relocation, borrow, and failure edges were incomplete

The rejected form did not fully constrain move-out, recoverable growth, element
reference provenance, structural mutation under a live borrow, or partial
cleanup.

Resolution: ordinary move-out occurs only through a complete state transition;
growth checks arithmetic and allocation before moves and preserves the owner,
elements, and offered affine input on recoverable failure. Physical references
and cursors carry owner provenance and freeze relocation, deletion, and owner
drop. Logical handles revalidate identity and occupancy. Replace/swap initially
remain region-free and borrow-free under T-A pending a separate lifetime proof.

### S6: copied finite generations were overpromised

A finite-width freely copied handle cannot simultaneously promise indefinite
reuse, memory bounded only by peak live population, and permanent rejection of
every stale handle.

Resolution: the impossibility is explicit. G0 must freeze which guarantee is
relinquished, account separately for live payload, high-water capacity, retired
slots, and identity history, and run tiny-generation steady-live churn. A
generation never silently wraps; clear/reset and shrink/regrow cannot resurrect
an identity. The standing wrong-pool ruling remains a memory-safe logic bug, not
a promoted safety theorem. Recycling remains a census-gated witness rather than
a mandatory standard container.

## 3. Performance and selection dispositions

### P1: private implementation details could manufacture new R3 contracts

The rejected form included private layout and dispatch class in contract
identity. Flat and node tables could therefore evade direct comparison by
declaring themselves different “performance contracts.”

Resolution: contract identity is limited to observable semantics and enforceable
bounds: results/order, ownership/invalidation, failure/drop, asymptotics,
contiguity/stability/range guarantees, and externally promised allocation or
memory ceilings. Private layout, algorithm, node size, monomorphization, and
internal dispatch remain candidates in the same R3 class. One writer-facing
route may specialize internally by payload, size, target, or measured crossover.

### P2: non-inferiority alone could leave several winners

The rejected form had no frozen rule for ties, Pareto trade-offs, payload/target
crossovers, or held-out validation.

Resolution: G0 must freeze payload classes, sizes/load factors, realistic and
adversarial traces, target/allocator, peak/transient memory, throughput,
p50/p95/p99 latency, code size, a primary endpoint, lexicographic tie-breaks,
crossover policy, and training/held-out separation. No unique survivor means no
selection. H-STORE, H-LRU, and H-IPQ are all excluded from candidate tuning.

### P3: the capability list had no executable closure rule

The rejected matrix mixed protected baselines, mandatory defaults, topology
witnesses, held-out structures, and prevalence-gated options, while claiming
that all “mandatory” gaps must close.

Resolution: every row now has role B, M, W, H, or O and a named canary. All M
cells must be E or P; B controls may not regress; W structures must be complete
and efficient through the public substrate; all three H witnesses must pass
without compiler special-casing; every O deferral names its corpus/dependency
decision. Stable and unstable sort, eager versus optional lazy drain, generic
bulk move-append, `swap_remove`, arena/reset, deep recursive destruction,
UTF-8 sealing, adversarial deque/hash churn, and inline-to-heap transition are
explicitly covered.

### P4: structural rejection mixed theorems with machine-dependent costs

The rejected form treated tags, branches, indirect calls, allocator calls, and
loss of SIMD as absolute failures without payload or target conditions.

Resolution: hard rejects are now unsupported mandatory behavior, a safety or
asymptotic failure, per-element allocation under a contiguous contract,
full-capacity generic payload construction, hidden Copy/Clone, memory growth
beyond the contract, writer-visible raw state, or a generation tax on the
protected append-only path. Tags, traffic, calls, scans, branches, static versus
indirect behavior, and SIMD are measured with preregistered thresholds. The
counter set includes metadata, peak/transient bytes, load/probe behavior,
cache/TLB effects, fragmentation, tail latency, instructions, and code size on
32-bit and 64-bit DataLayouts.

### P5: candidate families were selected before measurement

The rejected form narrowed deque and priority-queue representations and used one
hash algorithm comparison as though it selected the canonical map.

Resolution: ring, segmented, and centered/sliding deques remain live; binary,
d-ary, min-max, and other sequence-backed heaps remain live until the priority
contract is frozen. G2's fixed-algorithm comparison isolates sparse storage
state only. Later canonical-map selection still compares eligible algorithm
families. Standard-library placement is likewise an experimental sealed-library
witness until a family passes G0, R1, and selection.

## 4. Specification, MCTS-Mem, and process dispositions

### C1: the report could appear to create its own E0.1 authority

Resolution: the report attributes the existing implementation pause to the
standing owner instruction. It neither creates nor lifts that pause and asks
only whether G0 closure should be a prerequisite for a later reopening.

### C2: the recorded collection and ownership routes were not fully confronted

Resolution: STOR-1's “future libraries over buffer” remains a direction, not
proof that current `buffer<T>` exposes sufficient checked transitions. The
append-only P2 route remains protected and generation-free. Recycling remains
census-gated, and a zero residue still means it is not admitted. The already
greenlit OWN-6 and OWN-14 reborrow directions are not reopened; canaries test
their sufficiency before proposing an additional cursor mechanism.

### C3: a nominal mechanism-count budget could still admit unrelated intrinsics

Resolution: G0 must produce a machine-readable META-5 ledger for every grammar,
type, ownership, effect, drop, fact, diagnostic, and lowering delta, its R1
ground, and a derivability matrix from candidate kernel transitions to every
canary operation. Dense and sparse candidates stay jointly live until a shared
generative route is compared. Calling unrelated intrinsics “opaque operations”
does not evade the budget or R3.

### C4: library derivation occurred after a premature substrate selection

Resolution: every surviving substrate candidate must derive the G4 libraries
and pass the three-layer and held-out witnesses before R3 selection. H-STORE has
a frozen dependency budget and cannot compose the corresponding finished
sequence, map, or pool. H-LRU and H-IPQ remain separate composition witnesses.

### C5: a research correction could silently rewrite the active design tree

Resolution: the report records gaps, alternatives, and proposed gates only. It
changes no normative specification, PATTERNS entry, production implementation,
or MCTS-Mem node. A later owner-selected production route must perform the
normal same-change spec, derivation-ledger, and design-tree redecision.

## 5. Final verdict and next stop

The exact report is fit for owner review as a capability-floor research boundary.
Its evidence supports opening G0; it does not establish that any proposed route
is sound, fastest, production-ready, or teachable.

If the owner accepts the boundary, the next durable step is G0 only: freeze the
role-mapped registry, exact contracts, workload/target matrix, winner rules,
META-5 derivability ledger, held-out dependency budgets, and rejection
thresholds. G0 itself requires review before any candidate implementation.
