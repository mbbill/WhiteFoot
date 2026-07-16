# Candidate B-Strata Decisive Research and Landing Plan

Date: 2026-07-15

Status: controlling plan for the owner-selected B-Strata-only research track.
It supersedes the exhausted authorization boundary in
`CANDIDATE-B-ELEGANT-DESIGN-PLAN.md` without rewriting that completed result.

## 1. Owner decision and forced outcome

The owner has selected B-Strata as the only capability architecture to pursue.
The project will not pivot to Candidate C and will not develop B-Graphs as a
competing architecture. Prior alternatives remain historical evidence and
falsifiers only.

The objective is no longer another comparative paper result. It is:

> Determine whether one normalized, project-independent B-Strata core can make
> the fourteen frozen native operations safe and performance-preserving, then
> test the decisive claims far enough to return a forced YES or NO verdict.

The final result must be exactly one of:

- `STRATA-YES`: one coherent core closes all fourteen operations, survives
  hostile safety and erasure review, has an implementable deterministic
  checker and lowering, and preserves every protected native structural budget
  in the bounded evidence; or
- `STRATA-NO`: a named irreducible conflict, unavoidable runtime or structural
  tax, unsafe authority cycle, unbounded rule interaction, or infeasible
  checker/lowering prevents B-Strata from meeting the project constraints.

`REVISE`, `OPEN`, and `UNKNOWN` may describe intermediate work. They are not
permitted as the final disposition. A NO verdict must explain why another
local B-Strata repair cannot remove the blocker without violating a binding
constraint. Lack of elapsed research time alone is not a NO argument.

## 2. What remains fixed

### 2.1 Performance-first objective

The problem remains missing safe expressiveness that would otherwise force
initialization, zeroing, copies, relocation, tags, runtime metadata,
allocation, indirection, retained checks, stronger atomics or fences, larger
scans, or an unavailable native representation. Isolation is not the goal.

Every source-level check remains present unless a machine-verified proof
discharges it. No route may weaken safety to preserve source performance.

### 2.2 Frozen operation corpus

The decisive corpus remains exactly the previously audited fourteen complete
operations:

1. Hashbrown lookup;
2. Hashbrown vacant insertion;
3. Hashbrown replacement;
4. Hashbrown removal;
5. Hashbrown rehash;
6. mimalloc small allocation, including frozen cold outcomes;
7. mimalloc local free through final page disposition;
8. mimalloc remote free, collection, and page disposition;
9. SQLite insertion and split;
10. SQLite deletion and balance;
11. SQLite rollback;
12. Crossbeam protected load;
13. Crossbeam retirement; and
14. Crossbeam collection.

The pinned source identities and exact source anchors in
`CANDIDATE-B-MULTIPROJECT-AUDIT.md` remain controlling. Definition chasing is
allowed only inside those complete routes. No fifth project or fifteenth
operation may be added merely to postpone the verdict.

### 2.3 Historical evidence

The completed `B-REVISE` comparison is evidence, not an active alternative
contest. In particular:

- the six previously labeled paper-closed B-Strata routes are now only
  `PAPER-ROUTED`; they receive no soundness, erasure, implementation,
  code-shape, or performance credit;
- the eight open routes are not presumed impossible;
- the validator-to-liveness correction remains binding;
- hot-subpath credit remains prohibited;
- B-Forms demonstrates special-form growth risk; and
- B-Graphs demonstrates the boundary at which local protocol descriptions
  become arbitrary writer invariants.

Those controls may falsify a proposed B-Strata rule. They receive no parallel
design or implementation budget.

## 3. What B-Strata must become

The existing eight strata are analytical jobs, not eight preselected language
keywords, runtime objects, or checker subsystems. The first task is to
normalize them into the smallest coherent semantic core.

Every rule must preserve one common resource-conservation invariant:

> Each live physical root owns one affine release authority and one current
> checked partition whose nonoverlapping leaves completely cover the root.
> Every leaf is exactly vacant bytes, initialized bytes, one live typed value,
> one transit/progress obligation, or one disposition obligation. Loans,
> observations, and deferred rights are a separate obligation set that escrows
> incompatible move, reclassification, or release authority while retaining
> the original root and nonwrapping version. Release is legal only after the
> partition is reunited and every subowner and obligation has ended; released
> is a terminal root state, not a footprint state. Metadata, addresses,
> validators, and ordinary predicates create no owner or authority. Abort need
> not run cleanup, but no invalid read, duplicate disposition, race, or
> premature release is permitted before abort.

The normalized design must answer, without circular premises:

1. what physical authority exists over a root and its disjoint places;
2. what establishes a layout or live owner in a place;
3. what checked transition consumes and produces each owner and obligation;
4. how partial progress, repair-required state, and poison restrict later use;
5. how every borrow, result, and fact retains exact physical-root provenance;
6. how outstanding obligations become executable, finite disposition;
7. how checked facts are produced, transferred, invalidated, and erased; and
8. how atomic custody, protected observation, retirement, and final
   disposition compose without embedding one reclamation policy.

The result may have fewer semantic primitives than the eight analytical
strata. A stratum that is derived must be shown as a deterministic composition.
A stratum that remains primitive must have a deletion witness showing why the
other rules cannot derive it without safety loss or a protected structural
delta.

### 3.1 First normalization hypothesis

The first hypothesis to try to falsify is a three-judgment kernel:

- `K1 ROOTED-PLACE`: generative physical roots; exact fields, checked indices,
  and byte ranges; layout versions; split/join; and disjointness. It carries no
  liveness, owner, container identity, or logical handle authority.
- `K2 SEALED-STATE`: sealed certificates with explicit affine, shared, or
  scoped multiplicity, bound to exact roots and versions for vacant/live
  layout, roles, strict children, loans, observations, and deferred
  obligations. Its sum/product/span/classifier descriptions are closed and
  accept no ordinary predicate, proof term, validator, or cleanup program.
- `K3 LINEAR-STEP`: fixed initialize, take, replace, swap, relocate,
  reclassify, borrow, destroy, exact event, commit, outcome, and structured
  close transitions. It accepts no writer-defined state relation, global
  invariant, or termination proof.

This is a falsifiable starting hypothesis, not a primitive-count quota. A
fourth primitive is admissible only with an irreducibility witness and need in
at least two independent frozen projects.

Under this hypothesis, physical-root footprints derive from K1 plus K2 loans;
focus/progress/repair are sealed K2 states consumed by K3; executable
disposition is a structural K2 fold whose terminal actions are K3 leaves; and
optimizer facts are read-only projections from accepted K1-K3 derivations.
Facts never feed back into safety authority. Atomic transfer is a K3 exact
event, while observation, retirement, and quiescence remain the first hard K2
authority-production test.

Phase 1 must maintain an authority-origin ledger with no cycles:

- roots originate only in exact allocation or acquisition leaves, which also
  create affine release authority and vacant bytes;
- initialized bytes originate only in checked writes or exact external reads;
- typed state certificates originate only in a fixed generic validity/adoption
  rule over existing bytes or a valid predecessor transition;
- metadata may select a role maintained by a certificate but may not create
  the role, typed validity, ownership, or a strict child edge;
- borrows originate only in a live state over an exact place;
- observations originate only in an exact begin-observe or pin event;
- retirement rights originate only in a successful unlink or custody-transfer
  event;
- quiescence originates only in complete checked domain validation; and
- optimizer facts originate only as projections and create no authority.

## 4. Boundary between generic semantics and exact leaves

B-Strata is not required to manufacture machine or external semantics from
ordinary memory rules. It may consume exact fixed leaves for allocation,
release, atomics, threads, file or device events, target operations, and
foreign callbacks. That boundary does not permit a loophole.

Every exact leaf must state:

- the concrete event and target/platform scope;
- argument and result ownership;
- physical-root and borrow provenance;
- effects, traps, failure, cancellation, and partial completion;
- atomic order or external ordering where relevant;
- facts produced and exact invalidators;
- runtime and code-shape cost; and
- why the row is a machine/external semantic rather than a disguised
  Hashbrown, allocator, B-tree, pager, or reclamation operation.

Leaf outputs are closed by kind:

- allocation or acquisition may produce only a generative root, its affine
  release authority, vacant bytes, and an exact failure result;
- external reads may produce only initialized bytes under the supplied root or
  an exact failure/partial-completion result;
- fixed generic typed adoption may establish only the layout validity that its
  closed rule checks; a trusted foreign adoption is an explicit TCB assumption
  and earns no ordinary-library closure credit;
- atomics and fences may produce exact event witnesses and the declared
  success/failure custody transition, but no unrelated state fact;
- release consumes a reunited root and complete release authority;
- callable packing and invocation may perform only the closed erased-callable
  state transitions; and
- target or device leaves may produce only their enumerated low-level event
  results and effects.

No leaf may directly mint `Quiescent`, `Stable`, `RepairComplete`, a live-role
certificate, a strict child edge, or any fact not implied by its concrete
machine event. A SQLite page reinitializer is ordinary checked byte parsing and
transition code, not a high-level trusted leaf.

A high-level project operation hidden behind an exact-leaf name does not close
a route. Conversely, an irreducible exact machine event is not counted as a
new B-Strata topology rule merely because one frozen project needs it.

## 5. Admission test for every semantic rule

Every primitive or derived rule must have one ledger row with:

1. exact inputs, outputs, and linearity;
2. its sole authority producer;
3. normal, recoverable, abort, and abandonment behavior;
4. physical roots, versions, byte ranges, and invalidators;
5. executable disposition of every outstanding owner;
6. a deterministic local checking procedure;
7. a static-erasure argument;
8. the native operations that need it;
9. a deletion witness;
10. hostile negative examples;
11. interaction points with every other primitive; and
12. an observable falsifier.

A rule is rejected if any of the following holds:

- its semantics depend on a project, container, algorithm, API, path, or
  reclamation-policy identity;
- it accepts a writer predicate, proof, invariant, termination argument, or
  cleanup program as new safety authority;
- metadata, validation, a guard value, or compiler recognition can forge a
  live owner, borrow, quiescence fact, release right, or optimizer fact;
- it requires runtime state not already selected by the program's native
  representation;
- it adds work or code to an unrelated weaker route;
- its checker requires open-ended theorem proving or unbounded graph search;
- its interactions grow as operation-specific cross-products; or
- it closes only a hot subpath while leaving a rare or failure path undefined.

## 6. Work phases and mandatory gates

The entire track has one semantic-repair budget after Phase 0. Any change to a
primitive, authority producer, rule semantics, leaf contract, route semantics,
or state model consumes it, reopens the earliest affected gate, and invalidates
every downstream proof, prototype, and measurement. A second missing-authority
failure must end in `STRATA-NO` with a minimal witness that exhausts the frozen
grammar and shows that no admitted local composition can produce the required
authority. Mechanical verifier, model, checker, or lowerer defects may be fixed
without consuming this budget only when the frozen semantics and route remain
unchanged; affected evidence must still be regenerated.

### Phase 0: durability and baseline

Produce and commit this plan, the owner ruling, synchronized active status,
the MCTS-Mem decision, the status verifier, and one decision-log entry. Preserve
all pre-existing user worktree changes. Both repository verification gates
must be green before and after the step.

Gate: `STRATA-PLAN-LOCKED`.

### Phase 1: normalize the semantic core

Front-load four verdict-forcing definitions before expanding the rest of the
document:

1. a finite liveness-authority judgment in which only vacant creation, exact
   adoption leaves, and sealed owner transitions can establish or change live
   layout; metadata decoders can select maintained authority but cannot mint
   owners, typed validity, or strict child edges; and
2. a finite quiescence-producer judgment that must derive safe final release
   for both audited mimalloc and Crossbeam observer protocols from their native
   events without a per-load or per-object tax. One theorem schema must prove
   complete pre-cutoff observer coverage, observer exit or cutoff advance,
   registration/scan race closure, exclusion of new access to the retired
   target, required ordering, generative-root protection against ABA/reuse, and
   stalled-observer blocking. It accepts no project/policy identity, callback
   predicate, writer proof, or quiescence-producing leaf;
3. an erased affine one-shot disposition judgment that preserves Crossbeam's
   inline representation, exact effects, environment provenance, cross-thread
   use, and consume-before-invoke behavior without a hidden allocation, count,
   or second owner box; and
4. an exact external-event and repair boundary showing that SQLite's pager,
   VFS/WAL, reinitializer, and poison route decomposes into generic sealed
   repair/poison authority plus a finite low-level leaf interface. Phase 1 must
   expose a minimal falsifying witness and prohibit hidden database operations
   or arbitrary foreign contracts; Phase 2 performs the complete leaf
   enumeration and route closure.

If any boundary requires a project/policy identity, an arbitrary writer
invariant, a hidden trusted assertion, or an extra protected-path event, record
`STRATA-NO` before spending time completing lower-risk exposition.

Each of the four boundaries must already provide, for every relevant frozen
project, one machine-checkable positive derivation, one single-fault authority-
forgery rejection, and the exact native event manifest. These are early
falsifiers, not substitutes for the general proof and complete route work in
later phases.

Produce:

- `CANDIDATE-B-STRATA-CORE.md`, defining the exact judgments, authority flow,
  primitive inventory, derived strata, and illustrative reductions;
- `CANDIDATE-B-STRATA-RULES.tsv`, one complete admission row per primitive and
  derived rule;
- `CANDIDATE-B-STRATA-NORMALIZATION.tsv`, mapping every old BS-1 through BS-8
  statement to exactly one primitive or one acyclic derivation;
- `CANDIDATE-B-STRATA-AUTHORITY-ORIGINS.tsv`, recording every authority kind,
  sole producer class, consumers, transfers, and invalidators;
- an interaction matrix showing which rule pairs can exchange authority and
  why no unchecked cross-product exists; and
- a deterministic verifier for inventory, required fields, authority-source
  uniqueness, deletion witnesses, and interaction coverage.

The core document must use one representation-independent state model for
vacant/live layouts, owner obligations, progress, repair, facts, and concurrent
custody. It must not add source syntax or choose a production encoding yet.

Gate: `STRATA-CORE-PASS` or `STRATA-NO`.

`STRATA-CORE-PASS` requires a finite deterministic core with no circular
authority, no hidden runtime state, and a syntax-directed checking algorithm
for every rule. The plan must state a termination measure and worst-case bound
in program size, monomorphized instance count, and state arity; acceptance may
not depend on solver timeout, heuristic success, backtracking, or unbounded
search. The verifier must reject a cycle in the complete authority-origin graph,
not merely uncovered pairwise interactions, and every K2 constructor must fix
its affine, shared, or scoped multiplicity.

One targeted correction may repair an omitted definition by consuming the
global semantic-repair budget. After that correction, every required authority
must have either a complete derivation or a minimal missing-authority witness
over the exhaustively enumerated frozen grammar; it may not remain an open
expository task.

After `STRATA-CORE-PASS`, no primitive or stratum may be silently added. A
proposed addition reopens the core gate, must pass the full admission ledger
and interaction matrix, and consumes the global semantic-repair budget.

### Phase 2: close all fourteen complete routes

Freeze `CANDIDATE-B-STRATA-CROSS-FAMILY-LOCK.md` before constructing a
candidate model or prototype. It binds every operation's reference algorithm,
outcome partition, owner/drop account, roots, synchronization and external
events, hostile mutations, and forbidden structural deltas. It also freezes the
complete endpoint registry: reference source/function/corpus hashes,
correctness digest, target triple, compiler and flags, allocator, endpoint and
aggregation, ratio direction, sample or sequential-stop rule, balanced run
order, exclusions, confidence method and level, non-inferiority margin,
multiplicity treatment, and the preselected structural/event-count substitute
for a cold or rare route. Results may not rewrite this lock.

Derive every frozen operation from the normalized core and exact leaves. Each
route records:

- complete normal, recoverable, abort, abandonment, and rare-path behavior;
- every owner and obligation before and after each logical commit;
- every root, range, borrow, fact, invalidator, and re-root prohibition;
- exact cleanup or repair progression;
- exact atomic or external events;
- static state expected to erase;
- every forbidden structural delta; and
- one executable or mechanically checkable falsifier.

The route matrix has exactly fourteen rows because B-Strata is now the sole
candidate. Each operation also has stable `outcome_id` rows for every frozen
normal, precommit failure, retry, partial-progress, abandonment, abort, and
rare outcome. Operation closure is the conjunction of all its outcomes. A
verifier must prove that every frozen source anchor, event, owner outcome, and
failure class appears exactly once.

A failing row may trigger the one global normalization repair only when the
same irreducible semantic-core relation is required by at least two independent
projects and still passes Section 5. Multiple operations in one project may
support a derived composition or a genuine exact machine/external/callable
leaf, but cannot justify a new core authority. A project-specific patch is
prohibited.

Produce a separate `CANDIDATE-B-STRATA-LEAVES.tsv` for every allocation,
release, atomic, external, target, and callable leaf. No route may receive
closure credit merely because a missing operation was moved into that ledger.

Map the normalized core back to all fifteen existing performance-demand
families as a non-regression check. This reuses the existing ledger and opens
no new source-audit scope.

Gate: `STRATA-PAPER-YES` or `STRATA-NO`.

`STRATA-PAPER-YES` requires fourteen complete paper-closed operations, every
frozen outcome closed, and all fifteen existing demand families mapped to an
exact K1/K2/K3 derivation or legitimate exact leaf with no new semantic gap or
runtime tax. This mapping earns routing/non-regression credit only; it does not
close the 340 exact dense obligations or exact D-2/P-1. Any remaining `OPEN`,
`UNKNOWN`, structural tax, arbitrary-authority dependency, or hidden high-level
exact leaf blocks the gate.

### Phase 3: hostile safety, erasure, and implementability model

After `STRATA-PAPER-YES`, define a general operational semantics and the
concurrent memory model for every admitted authority-bearing rule and leaf.
Give independently reviewed proofs of:

- type/state preservation and the common resource-conservation invariant;
- absence of uninitialized typed reads;
- exact-once owner traffic, no double disposition, and overlay exclusivity;
- non-escapable progress, repair-required, and poisoned states;
- physical-root, nonwrapping-version, and footprint provenance;
- safe disposition across callbacks, divergence, abort, and nested resources;
- fact production, invalidation, speculation, and facts-off semantic identity;
- race freedom under the admitted publication/interference rules;
- custody transfer only on the declared successful atomic event; and
- no retired-root release before the shared quiescence theorem applies.

Exact leaves appear as explicit, enumerated TCB assumptions in conditional
theorems; the semantics may not assume a high-level leaf conclusion for free.
A mechanically generated coverage table must map every rule and authority-
producing leaf in the ledgers to its formation, preservation, progress or
termination measure, erasure, and hostile-proof obligations.

Build a separate executable checker and independent byte/owner/root/observer
oracle for counterexample search. Bounded execution and negative corpora
support the general proofs but never substitute for them. Freeze state-space
bounds, seeds, and input hashes, with at least four Hashbrown slots; four
mimalloc blocks, two threads, and one reader; three SQLite page roots with
failure after every external event; and three Crossbeam participants including
one stalled participant, a two-entry bag, and two distinct deferred payloads.
Every producer, transfer, consumer, and invalidator needs a positive case and a
single-fault mutation; concurrent leaves need fixed interleaving/litmus cases.
Accepted oracle violations must be zero, every preregistered negative must be
rejected, and facts-on/off program semantics must match.

A Phase 3 correction that changes any frozen semantics consumes the global
semantic-repair budget and reopens the earliest affected gate. A proof,
checker, oracle, or generator defect that leaves semantics unchanged may be
fixed, but all affected evidence must be regenerated. Once the semantic-repair
budget is exhausted, a second accepted counterexample at the same authority
boundary yields `STRATA-NO` with its minimized witness.

Gate: `STRATA-MODEL-YES` or `STRATA-NO`.

### Phase 4: decisive cross-project vertical evidence

Only after `STRATA-MODEL-YES`, preregister and build the smallest prototypes
that collectively exercise every authority class:

1. a Hashbrown-shaped rehash route for classified liveness, direct owner
   traffic, progress, invalidation, and disposition;
2. a mimalloc-shaped allocation/free/page-disposition route for overlays,
   suballocation, local versus atomic custody, observation, and release;
3. a SQLite-shaped mutation/rollback route for checked byte subranges,
   multiple roots, repair-required state, exact external events, and poison;
4. a Crossbeam-shaped load/retire/collect route for zero-extra-event protected
   loads, unique retirement, erased one-shot disposition, and quiescence.

These are four project fixtures, not four credited subpaths. Together they
must execute every one of the fourteen frozen operation contracts; the named
routes above are the highest-pressure lanes used for detailed hostile and
code-shape inspection.

The operation-to-entrypoint map is exact:

| Fixture | Required independent entrypoints |
|---|---|
| Hashbrown | `H-LOOKUP`, `H-INSERT`, `H-REPLACE`, `H-REMOVE`, `H-REHASH` |
| mimalloc | `M-ALLOC`, `M-LOCAL-FREE`, `M-REMOTE-FREE` |
| SQLite | `S-INSERT-SPLIT`, `S-DELETE-BALANCE`, `S-ROLLBACK` |
| Crossbeam | `X-PROTECTED-LOAD`, `X-RETIRE`, `X-COLLECT` |

The verifier requires every operation ID exactly once. Each entrypoint must be
trace/contract-equivalent to its frozen complete operation and must carry its
own normal/failure/rare semantic differential, adversarial rejection set,
structural manifest, and measurement or preregistered structural-substitution
disposition. A combined workload may time several operations, but it cannot
replace any operation's independent code-shape audit.

Each prototype must pass semantic differentials and adversarial rejection
tests before code-shape inspection. Freeze the source, reference route,
compiler revision, target, allocator, event counts, instruction-body
comparison, and measurement protocol before observing performance.

Use one shared non-production checker, oracle, normalizer, and lowerer. Project
or operation identities may label fixtures and reports but may not enter the
accepted semantic input or lowering dispatch. Keep this prototype isolated
from the production specification, stage-0 compiler, and xlc so bootstrap
coverage cannot masquerade as B-Strata feasibility or failure.

Static erasure must hold in the canonical checked artifact and generic pre-
optimization lowering; fixture-specific backend dead-code elimination receives
no erasure credit. Lowering is local and syntax-directed by verified primitive,
never by recognizing a whole operation graph or fixture-shaped pattern. Freeze
per-entrypoint code-size, instruction-body, call/event, and rare-path limits
before inspecting generated artifacts.

For each protected route, fail on any required extra:

- initialization or zeroing;
- payload copy, clone, relocation, or owner movement;
- tag, descriptor, backpointer, counter, hazard record, or dynamic borrow
  table;
- allocation, indirection, dynamic dispatch beyond the frozen reference,
  atomic, fence, synchronization, scan, or asymptotic work;
- success-path cleanup traversal absent from the reference; or
- mandatory code-size expansion caused by unused strata.

Benchmark tuning may diagnose a failure but may not change a frozen semantic
route after results are seen.

An endpoint earns performance credit in exactly one preregistered way:

- optimized instruction body plus transitive call/event manifest is identical
  to the reference, with timing reported as confirmation; or
- its own quantitative non-inferiority test passes under the frozen sampling,
  confidence, margin, and multiplicity protocol.

Results may not be pooled to hide a failing operation. Rare failure and release
paths may use exact event-count and structural limits only when that substitute
was frozen in the cross-family lock. `INCONCLUSIVE` grants no performance
credit and is not a third final state. A preregistered sample extension may run
once. If the maximum campaign remains inconclusive and structural identity is
absent, mandatory root-cause analysis must reduce the endpoint to its finite
instruction, call, event, and workload differences. The one nonsemantic
implementation-correction round may then run without changing the lock,
semantics, or route. After regeneration, the endpoint must either earn
performance credit or expose a semantically required structural cost or a
deterministic-lowering infeasibility that supports `STRATA-NO`. The goal may not
stop at unexplained evidence insufficiency.

Classify every regression before a verdict. A semantic requirement that forces
an extra field, event, instruction class, or unit of work is an immediate NO
witness. A nonsemantic checker/lowerer defect permits one implementation-
correction round without changing the lock, semantics, or route, followed by a
fully regenerated campaign. An unexplained slow measurement alone cannot be
presented as an irreducible semantic NO. Post-result semantic, route, leaf,
algorithm, threshold, or workload changes invalidate the campaign and reopen
the earliest affected gate under the global repair rule.

Gate: `STRATA-EVIDENCE-YES` or `STRATA-NO`.

### Phase 5: final verdict and landing boundary

`STRATA-YES` requires all previous YES gates. The final report must name the
exact minimal core, derived strata, exact-leaf boundary, checker/lowering
shape, fourteen derivations, hostile-review result, structural evidence, known
limitations, and remaining non-gating ecosystem work.

The YES scope is the frozen fourteen operations and the admitted semantic
rules actually proved and exercised. It is not general-purpose systems
completeness, exact dense D-2, P-1, or closure of the 340 unresolved dense
obligations. The fifteen-family map receives routing/non-regression credit
only.

`STRATA-NO` must name the first irreducible failed constraint, the complete
repair attempts, the evidence that the failure is not a local omission, and
the native performance or safety consequence. It must not recommend Candidate
C as part of this goal.

A final YES selects B-Strata for owner review and must include
`CANDIDATE-B-STRATA-PRODUCTION-LANDING-PROPOSAL.md`. That proposal freezes the
first minimal production slice, affected specification rules, stage-0 and xlc
checker/lowering surfaces, conformance and derivation updates, code-shape pins,
migration/compatibility conditions, hostile review, both repository gates, and
rollback conditions. The verdict commit does not silently rewrite the kernel
specification or ship a production feature. Production specification, checker,
compiler, runtime, pattern-doctrine, standard-library, and xlc migration
changes remain separate reviewed landing slices.

## 7. Required deliverables

The complete track must leave durable English artifacts for:

1. this controlling plan;
2. the cross-family lock;
3. the normalized core and rule ledger;
4. the normalization and authority-origin ledgers;
5. the exact-leaf ledger;
6. the exact fourteen-route derivation report and matrix;
7. deterministic verifiers for rules, interactions, routes, and status;
8. the hostile safety and erasure model plus negative corpus;
9. the lowering and structural-budget contract;
10. preregistered cross-project prototype and measurement protocols;
11. prototype results and generated-code evidence; and
12. the final `STRATA-YES` or `STRATA-NO` report; and
13. on YES, the exact production landing proposal.

Every completed phase receives its own commit and one append-only
`decision-gates.md` entry. Active status files advance only after the phase
gate passes or fails.

## 8. Research discipline

- Do not use a broad brainstorming or mind-expansion workflow.
- Do not reopen Candidate C or develop another full candidate.
- Do not add a capability because its name makes an open route look closed.
- Do not confuse a token type with a safe producer of that token.
- Do not confuse memory safety with abstract container correctness, database
  crash consistency, eventual reclamation, or application progress.
- Do not claim zero cost from paper erasure alone; inspect generated artifacts.
- Do not claim measured performance from code-shape parity alone.
- Do not weaken a check or accept writer trust for performance.
- Do not continue refining after a proven irreducible NO condition.

The work is complete only at `STRATA-YES` or `STRATA-NO`.
