# xlang Research Handover

Status: active task handover, 2026-07-15. This document records the current
owner clarification after the privileged-basis research took an out-of-scope
cryptographic turn. It is sufficient to resume the active research without the
conversation transcript. It does not select a language design or authorize an
implementation.

## 0. Read this first

The immediate research question is **not** how to authenticate independently
distributed privileged extensions. The owner wants to study how Rust and other
production languages let the compiler, runtime, or official core library define
operations that ordinary user source cannot define, then choose one elegant
xlang mechanism of that class and determine the smallest safe public capability
basis ordinary libraries need.

In this task, "ordinary source cannot obtain the back door" means a static
compiler/toolchain boundary. It does **not** mean cryptographic nonforgeability.
Do not continue the F/C/S, signed-grant, snapshot, replay, revocation, key-
rotation, or identity-DAG line of work.

The next agent should proceed in this order:

1. make the scope correction durable in the active status documents without
   rewriting hash-pinned historical reports;
2. research compiler- and core-library-private mechanisms in Rust and selected
   comparable production languages;
3. compare the mechanism classes and recommend one static xlang privilege-
   definition route;
4. only then derive the minimal safe public capability basis and test it against
   the existing finite systems-demand ledgers and held-out witnesses; and
5. return the research result to the owner before any production design or
   implementation.

## 1. Project objective and standing constraints

xlang is intended to become a general-purpose systems language for AI-written,
human-approved code. The project gives machine-code performance highest
priority, while making memory corruption, data races, silent overflow, and
uninitialized reads unrepresentable in accepted programs. There is no writer-
accessible `unsafe` escape. Checks remain enabled unless a machine-verified
proof removes them.

The capability research exists because xlang may ship no standard library, yet
ordinary checked libraries must still be able to implement the capabilities
needed by everyday systems programs with competitive asymptotic and structural
performance. xlang does not need to reproduce Rust types or APIs one for one.
Several named Rust abstractions may derive from one smaller xlang substrate when
their observable contracts permit it.

The binding sources are:

- `CONSTITUTION.md`, especially P0, W1, W3, T1, T2, and R0 through R6;
- `optimizer-language-research/notes/user-directives.md`, especially D10
  through D14;
- `PATTERNS.md`, especially the COMPLETE and EFFICIENT acceptance rules;
- `spec/kernel-spec-v0.6.md`, for the current language rather than proposed
  future semantics;
- `THE-PLAN.md`, after the stale D14 cryptographic focus is corrected; and
- `optimizer-language-research/implementation/decision-gates.md`, which is the
  append-only durable lab log.

Repository process remains binding:

- every repository artifact added or modified by the project is English-only;
- `AGENTS.md` and `CLAUDE.md` must remain byte-identical;
- every completed step receives one commit and one `decision-gates.md` entry;
- fact channels receive hostile review before shipping;
- no production implementation follows from research without explicit owner
  approval; and
- `make check` and `make -C compiler check` must pass before and after changes.

## 2. Correct active research goal

Study how systems languages grant the compiler, runtime, or official core
library implementation capabilities that ordinary source cannot use to define
new semantics. Select the smallest coherent static privilege-definition
mechanism for xlang. Then show that a Pareto-small set of safe public primitives
exposed through that mechanism lets ordinary xlang libraries implement the
finite required systems and container capability set with native
representations and without unavoidable asymptotic or structural performance
tax, while xlang ships no standard library and exposes no writer-accessible
`unsafe`.

This goal has two serial decisions:

1. **Privilege-definition mechanism:** how compiler-owned or official-core code
   defines an operation ordinary source cannot define.
2. **Safe public capability basis:** which irreducible semantic operations that
   mechanism must expose so all remaining abstractions can be ordinary checked
   libraries.

Do not design the public basis before the mechanism classes have been compared.
Do not confuse a single privilege-definition mechanism with a single semantic
operation. Allocation, typed storage transitions, atomics, OS boundaries, and
target operations may be independently irreducible even if one internal route
defines all of them.

## 3. Layer model and terminology

Use these terms consistently:

```text
compiler/runtime/official core implementation
  -> uses the source-inaccessible privilege-definition mechanism
  -> defines safe public primitive contracts
  -> ordinary xlang libraries compose those primitives
  -> applications use containers, strings, I/O wrappers, and systems services
```

### 3.1 Privilege-definition mechanism

The compiler-recognized route by which trusted implementation code can define
semantics unavailable to an ordinary xlang definition. Candidate classes may
include hard-coded operations, compiler-only intrinsic declarations, a sealed
embedded core module, a specially compiled official core dialect, or a native
runtime boundary.

This is the object currently called the "back door." The final terminology is
not selected.

### 3.2 Safe public primitive

An operation ordinary xlang code may call under normal typing, ownership,
effect, and checking rules. Public availability is not privilege. For example,
ordinary source may safely allocate through a compiler-defined operation while
remaining unable to define another allocator primitive with fabricated
semantics.

### 3.3 Derived ordinary library

A container, string, iterator, resource wrapper, synchronization abstraction,
or other system facility implemented in ordinary checked xlang over the public
primitive basis. Such a library receives no special package, path, module,
attribute, or name-based authority.

### 3.4 Runtime resource authority

A file handle, socket, device lease, or similar runtime value may control which
operations a program can perform. That is separate from the compile-time
privilege-definition mechanism. The current research may account for resource
ownership and lifetime when required for safety and performance, but it is not
designing a general OS access-control or sandbox policy.

## 4. Explicit non-goals

The following work is outside the active research scope:

- public-key signatures, certificates, authorization releases, or approval
  envelopes;
- replay prevention, revocation, snapshot succession, key custody, key
  rotation, or cryptographic identity graphs;
- accepting independently distributed third-party privileged definitions at
  application build, link, load, or JIT time;
- a package manager, supply-chain security system, plugin permission system, or
  software-update protocol;
- a general runtime authorization, sandbox, or multi-tenant security model;
- writer-accessible `unsafe`, trusted assertions, unchecked contracts, or a
  user-selectable privileged compilation flag;
- implementing or shipping a standard library;
- implementing, tuning, or benchmarking a concrete container or candidate in
  the current research authorization;
- copying Rust's standard library one API or one type at a time;
- designing collection API names, methods, traits, interfaces, inheritance, or
  human-facing ergonomics unrelated to the capability lower bound;
- selecting final source spelling, keyword spelling, grammar, or diagnostics
  before the mechanism class and semantic need are selected;
- changing `spec/kernel-spec-v0.6.md`, the checker, `prototype/democ`, `xlc`,
  code generation, the runtime, or any production fact channel;
- restarting E0.1, migrating xlc, changing default teaching, or running a
  scored/default-writer experiment;
- fully designing concurrency, async, FFI, JIT, loader, or device subsystems in
  this pass; their categories are coverage tests, and an uncovered requirement
  is recorded as a gap rather than expanded into a new research program; and
- claiming complete formal proof, proof automation, throughput, code size,
  compile time, or default-writer evidence from a paper construction.

If structural analysis cannot resolve a performance question, the research may
specify the smallest experiment that would decide it, but it may not construct
or run that experiment without separate owner authorization.

## 5. In-scope research questions

### 5.1 Production-language mechanism census

Study mechanisms, not surface API counts. The census should include Rust and a
small set of relevant production-language contrasts. Candidate evidence may
cover:

- compiler-hard-coded primitive types, operations, and keywords;
- compiler intrinsics and builtins;
- lang items or compiler-recognized library declarations;
- standard-library-only or bootstrap-only attributes and language modes;
- compiler-embedded or sealed core modules;
- native runtime shims and compiler-provided ABI operations;
- standard-library internal `unsafe` or equivalent trusted implementation
  code; and
- ordinary user-accessible `unsafe` as a counterexample to xlang's W3 goal.

For each mechanism, record:

1. what authority it grants;
2. why ordinary source cannot define an equivalent operation;
3. what ordinary source may safely call;
4. what the compiler, official library, and runtime each own;
5. whether the mechanism has runtime cost;
6. how a new primitive is added and reviewed;
7. whether it works when the language ships no standard library;
8. whether it is backend- and target-independent at the language boundary;
9. whether it creates more than one privileged route; and
10. its P0, W1, W3, auditability, and TCB consequences for xlang.

Do not assume Rust's mechanism is the answer. Rust is both a source of useful
precedent and a counterexample because ordinary Rust users can write `unsafe`.

### 5.2 Static xlang gate comparison

Compare at least these mechanism classes at the architectural level:

- compiler-hard-coded public operations;
- one compiler-only intrinsic or builtin definition form;
- a sealed compiler-embedded core module;
- a specially compiled official core source mode; and
- exact native runtime imports recognized by the compiler.

It is permissible for one implementation to combine two physical pieces, such
as a compiler-owned declaration and a runtime body. Count semantic authority,
TCB branches, maintenance paths, and writer-visible rules rather than keyword
count. Prefer one primary definition route, but do not claim one is sufficient
if an independently irreducible path remains.

The mechanism comparison must answer where the authority decision is made and
what prevents ordinary source, dependencies, package names, module paths,
attributes, or command-line flags from entering that mode. This is a static
compiler boundary, not a cryptographic protocol.

### 5.3 Minimal safe public capability basis

After selecting a gate class, identify only the irreducible operations ordinary
xlang cannot implement safely and efficiently from existing semantics. Likely
question categories include, but are not preapproved as primitives:

- acquiring, resizing, and releasing storage;
- representing vacant storage and moving a place between vacant and live state;
- taking, putting, replacing, relocating, borrowing, and copying values without
  hidden `Copy`, `Clone`, or `Default` assumptions;
- atomics and the minimal thread/runtime leaves;
- OS byte/resource operations and narrow FFI boundaries;
- target operations, SIMD, virtual memory, code activation, MMIO, and device
  leaves where the finite demand set requires them.

The basis is minimized semantically, not by combining independent authority
behind a generic descriptor. A user-supplied pre/postcondition, opcode,
syscall number, arbitrary state machine, or asserted effect cannot turn an
ordinary definition into a primitive.

### 5.4 Derivability and cost coverage

Use the existing finite demand universe rather than inventing a new unbounded
list. The coverage argument should construct ordinary-library routes for
representative:

- dynamic sequences, deques, strings, and byte builders;
- hash tables, ordered structures, heaps, pools, and stable handles;
- graphs, linked structures, arenas, and inline-small storage;
- iterators, cursors, draining, and ownership transfer;
- files, sockets, processes, clocks, and buffered I/O wrappers;
- shared ownership, synchronization, channels, and async/task structures at
  the category level;
- FFI, target, loader/JIT, MMIO, DMA, and device held-outs at the category
  level.

Several named abstractions may share one substrate. No privileged named
container receives derivability or performance credit.

For every route, record at least:

- asymptotic time and space;
- allocation count and allocation topology;
- payload layout and contiguity;
- initialization and zero-fill traffic;
- copies, moves, and relocations;
- mandatory metadata such as bitmaps, tags, headers, generations, or counts;
- indirections and dynamic dispatch;
- system-call or machine-event multiplicity;
- cleanup and failure behavior;
- facts needed to authorize access or remove checks; and
- tax imposed on weaker protected shapes.

## 6. Completion and falsification criteria

The research is complete only if all of the following hold:

1. One primary static privilege-definition mechanism is recommended, or the
   report proves why more than one independently irreducible route is required.
2. Ordinary source cannot define privileged semantics or enter the privileged
   mode through a name, path, package, attribute, flag, plugin, or ordinary
   contract.
3. Ordinary source can call the exposed primitives safely under the normal
   language rules and never needs writer-accessible `unsafe`.
4. The privileged layer contains irreducible leaves, not `HashMap`, sorting,
   parsing, buffering policy, allocator policy, retry policy, executor policy,
   or another high-level library implementation.
5. Every required capability category has a constructive ordinary-library
   route or is marked as an unresolved gap.
6. No accepted route has asymptotic regression, pathological simulation, a
   hidden `Copy`/`Clone`/`Default` premise, or standard-library-only raw
   privilege.
7. Protected weaker shapes do not pay an unavoidable safety bitmap, per-element
   tag, extra header, refcount, zero-fill, copy, allocation, indirection,
   dynamic-dispatch, or extra-call tax selected only for a stronger contract.
8. Every proposed primitive has a removal witness: deleting it makes some
   required route impossible or necessarily more expensive under the same
   contract.
9. Structural evidence and unmeasured hypotheses are separated. Any remaining
   measurement need is returned as a separately authorizable experiment.
10. Hostile review finds no route by which a high-level operation, arbitrary
    asserted contract, or user-provided descriptor recreates private `unsafe`.

Immediate falsifiers include:

- the candidate lets ordinary source declare a new intrinsic or trusted
  contract;
- the candidate relies only on a reserved module or package name that ordinary
  source can reproduce;
- a generic external operation requires a user-authored memory, lifetime,
  callback, cleanup, or concurrency claim;
- a standard-library-only named container is needed for good performance;
- a missing capability is simulated through whole-buffer copying, mandatory
  zero-initialization, a universal liveness bitmap, or an avoidable extra
  allocation;
- the compiler recognizes individual containers or census rows instead of a
  lower-level semantic need; or
- a performance conclusion depends on an experiment that was not authorized or
  run.

## 7. Work completed before this handover

### 7.1 Default-shape performance evidence

D9a is complete on two independently preregistered shipped-library targets:

- first-green `gpt-5.6-terra`/medium xlang beats `percent-encoding` 2.3.2 by
  1.653x, confidence interval [1.631, 1.667]; and
- one-shot xlang beats `utf8parse` 0.2.2 by 1.098x, confidence interval
  [1.085, 1.145].

Both xlang results retain every bounds site. This is replicated default-code-
shape evidence, not proof-elision evidence. The utf8parse facts control is
statistically inconclusive, while facts-on/off reports and optimized
instruction bodies are identical. Do not tune either completed protocol from
its result.

### 7.2 E0.1 data-layout and owning-sequence investigation

The E0.1 work in `experiments/data-layout-owning-sequence/` established that the
current language cannot express row-oriented fixed storage of affine records or
a general initialized-prefix owning sequence. The detached prototype and
reviews also found checker-flow bugs and exposed the deeper requirement for
vacant/live storage transitions, failure-atomic growth, and exact cleanup.

The experiment is historical. D11 superseded its immediate mechanism choice.
Do not restart its paired candidate protocol. The most useful entry points are:

- `experiments/data-layout-owning-sequence/RESEARCH_REPORT.md`;
- `experiments/data-layout-owning-sequence/REVIEW_RESPONSE.md`;
- `experiments/data-layout-owning-sequence/RESULTS.md`; and
- `experiments/data-layout-owning-sequence/FLAT_DESIGN_CANDIDATE.md`.

### 7.3 General systems-capability demand accounting

D11 and D12 broadened the question from one sequence implementation to the
minimum capability floor of a general-purpose systems language. The completed
accounting includes:

- a pinned Rust 1.97.0 `core`, `alloc`, and `std` inventory with 17,135 rendered
  rows across 297 reachable public modules;
- 5,555 canonical stable declarations on the detailed semantic axes;
- a 276-row G0 coverage-cluster and obligation universe;
- a 26-domain systems envelope;
- cross-ecosystem and held-out topology witnesses; and
- exact ownership, failure, destruction, invalidation, behavior, and structural
  cost dimensions for the dense unique-owner family.

Primary entry points:

- `optimizer-language-research/implementation/minimal-systems-capability/G0-CORE-REPORT.md`;
- `optimizer-language-research/implementation/minimal-systems-capability/SYSTEMS-DOMAIN-LEDGER.md`;
- `optimizer-language-research/implementation/minimal-systems-capability/CAPABILITY-OBLIGATION-REGISTRY.tsv`;
- `optimizer-language-research/implementation/minimal-systems-capability/DERIVATION-MATRIX.tsv`;
- `optimizer-language-research/implementation/minimal-systems-capability/WITNESS-REGISTRY.md`; and
- `optimizer-language-research/implementation/minimal-systems-capability/dense-family-lock-a/`.

These artifacts are a finite completeness and falsification anchor. They do not
select a mechanism or a list of language primitives.

### 7.4 Initial privileged-basis synthesis

Commit `76244e9` added an initial privilege-gate synthesis, sequential witness
derivations, an admission map, hostile review, D14, and related status updates.
It correctly recognized several durable principles:

- one admission/definition mechanism is not one semantic operation;
- high-level containers should remain ordinary libraries;
- storage needs vacant/live state rather than forced full initialization;
- a generic fully initialized `Box`-class operation is insufficient by itself;
- arbitrary raw allocation exposed to writers violates xlang's safety goals;
- safety facts require static proof, runtime validation/enforcement, or an
  explicit trusted implementation boundary; and
- container correctness properties need not become storage-safety authority
  unless a checked contract or optimization consumes them.

However, that work did not first settle the simpler static compiler/core
privilege-definition mechanism requested by the owner. Treat its proposed
public basis as a hypothesis and source of test cases, not a selected design.

### 7.5 Certified-resource architecture packet

Commit `43f2c3f` added a large proposed proof-carrying resource architecture,
systems derivations, held-outs, generated dense obligation ledgers, and hostile
review. Its candidate axes were spatial resources, place identity,
lifecycle/control, weak-memory interference, external frames, and final-code
binding.

The packet is not complete and was never owner-selected. Its exact dense
derivation remains fail-closed:

- 340 unique required route obligations remain unresolved;
- those obligations occur across 150 contexts;
- 208 are Convert-related;
- 136 are allocator-related;
- 12 concern ZST or fullness; and
- 16 occur in both the Convert and allocator sets.

Exact D-2 derivability and P-1 same-contract structural performance remain
pending. The packet may be mined later for demand cases, ownership arguments,
and cost hazards. Do not treat its six-axis architecture, proof language,
`Plan`/`MustClose`, or resource algebra as the selected public basis.

Relevant files include:

- `optimizer-language-research/implementation/minimal-systems-capability/privileged-basis/CERTIFIED-RESOURCE-BASIS-DECISION.md`;
- `optimizer-language-research/implementation/minimal-systems-capability/privileged-basis/SYSTEMS-WITNESS-DERIVATIONS.md`;
- `optimizer-language-research/implementation/minimal-systems-capability/privileged-basis/FRESH-HELDOUT-DERIVATIONS.md`;
- `optimizer-language-research/implementation/minimal-systems-capability/privileged-basis/DENSE-EXACT-BASIS-DERIVATION-REPORT.md`; and
- `optimizer-language-research/implementation/minimal-systems-capability/privileged-basis/PRIVILEGED-BASIS-RESEARCH-VERDICT.md`.

### 7.6 Out-of-scope cryptographic detour

Commits `6318615` and `d0e6cc0`, with onboarding changes in `9c71822`, pursued a
different problem: admitting independently distributed privileged capsules by
fixed release entries, stateless signed grants, or stateful successor
snapshots. That led to work on identity graphs, signatures, replay, revocation,
key migration, authorization receipts, and compile/link/load admission state.

The owner explicitly clarified that this was not the requested research. The
intended back door is a static compiler/official-core privilege boundary like
the private mechanisms used by production languages and their standard
libraries. Therefore:

- the cryptographic work is an out-of-scope historical detour, not the active
  recommendation;
- its hostile-review PASS means only that the artifacts were internally
  reviewed for the wrong question;
- no F/C/S choice is pending;
- no signed extension ecosystem is required;
- no replay, revocation, key, snapshot, or distributed-state question should be
  carried into the static mechanism comparison; and
- none of these commits changed the production language, specification,
  compiler, runtime, or standard library.

The exact historical artifacts are:

- `optimizer-language-research/implementation/minimal-systems-capability/privileged-basis/GATE-AUTHENTICATION-LOCK.md`;
- `optimizer-language-research/implementation/minimal-systems-capability/privileged-basis/GATE-AUTHENTICATION-HOSTILE-REVIEW.md`;
- `optimizer-language-research/implementation/minimal-systems-capability/privileged-basis/GATE-ADMISSION-PARETO-DECISION.md`;
- `optimizer-language-research/implementation/minimal-systems-capability/privileged-basis/GATE-ADMISSION-PARETO-DIMENSIONS.tsv`;
- `optimizer-language-research/implementation/minimal-systems-capability/privileged-basis/GATE-ADMISSION-PARETO-MATRIX.tsv`;
- `optimizer-language-research/implementation/minimal-systems-capability/privileged-basis/GATE-ADMISSION-PARETO-HOSTILE-REVIEW.md`;
- `optimizer-language-research/implementation/minimal-systems-capability/privileged-basis/verify_gate_admission_pareto.py`; and
- `optimizer-language-research/implementation/minimal-systems-capability/privileged-basis/test_verify_gate_admission_pareto.py`.

Preserve these exact bytes and their historical hashes. Do not rewrite them to
pretend they answered the corrected question. Mark them historical from active
status documents instead.

## 8. Current repository state at handover creation

The worktree was clean before `HANDOVER.md` was added. The starting HEAD was:

```text
d0e6cc0 research: freeze conditional privileged gate
```

The last full verification on that research state passed:

- `make check`: all verification layers green; and
- `make -C compiler check`: green.

The cryptographic detour created only research documents, generated research
tables, validators, and active-status edits. It made no production language,
specification, compiler, checker, runtime, container, or standard-library
change.

No capability-basis experiment, candidate construction, E0.1 restart, xlc
migration, or default-teaching change is authorized or in progress.

The separate xlc self-hosting build track remains as described in
`THE-PLAN.md`. Do not mix an unrelated xlc implementation slice into this
research cleanup or mechanism study.

## 9. Active documents that are currently stale

The following active documents still present the cryptographic F/C/S branch as
the next action and must be corrected before substantive research resumes:

- `THE-PLAN.md`, section 4 item 1;
- `AGENTS.md`, Current focus;
- `CLAUDE.md`, Current focus; and
- `mcts_mem/xlang.md`, whose final facts accurately record historical research
  at the time but lack the owner's subsequent scope correction.

`optimizer-language-research/notes/user-directives.md` D14 uses the phrase
"nonforgeable privileged admission route." The new durable clarification must
state that this means an ordinary-source-inaccessible static compiler or
official-core privilege-definition mechanism. It excludes cryptographic
authorization and independently distributed privileged extensions from the
current research.

`optimizer-language-research/implementation/decision-gates.md` is append-only.
Do not edit or delete D14-R2 through D14-R4. Append a correction that identifies
them as research for an out-of-scope third-party authorization problem and
records the new static mechanism scope.

The hash-pinned reports and generated tables are historical evidence. Do not
rewrite them. If a later cleanup moves them, preserve exact bytes, repair every
reference, and follow the repository's design-memory rules. The smallest safe
cleanup is to leave them in place and correct the authoritative active status.

## 10. Exact continuation plan

### Step 1: durable scope cleanup

Complete one documentation-only step:

1. append an owner-scope clarification after D14 in
   `optimizer-language-research/notes/user-directives.md`;
2. replace the cryptographic F/C/S focus in `THE-PLAN.md` with the corrected
   two-stage research goal;
3. update `AGENTS.md` and `CLAUDE.md` identically so the Current focus points to
   the static compiler/core mechanism census, not signed grants;
4. append a sourced correction fact to `mcts_mem/xlang.md`; preserve earlier
   facts as dated historical evidence unless the design-tree discipline
   requires a paired `.alt/` move after reviewing the relevant node;
5. append one correction line to `decision-gates.md` without editing old lines;
6. scan all changed prose and filenames for non-English content;
7. run `make check` and `make -C compiler check`; and
8. commit the cleanup as one durable step.

Do not change production files or start the production-language census in the
same commit.

### Step 2: mechanism census

Research Rust and a small, explicitly justified contrast set. Use primary
sources: official language/compiler documentation, compiler and standard-
library source, specifications, and original papers where applicable. Avoid a
large language catalog that adds names without separating mechanism classes.

Produce a table whose rows are mechanism classes and whose columns include:

- authority location;
- ordinary-source reachability;
- safe public-call model;
- compiler/library/runtime split;
- extension path through a reviewed toolchain change;
- number of independent semantic routes;
- runtime and code-shape cost;
- TCB and audit surface;
- no-standard-library compatibility;
- backend portability;
- P0 consequence;
- W1 consequence; and
- W3 consequence.

Do not research cryptographic admission, package signing, extension revocation,
or plugin distribution.

### Step 3: static gate recommendation

From the census, recommend one architectural class for xlang. The result should
define:

- where privileged definitions live;
- what exact compiler condition makes them privileged;
- why ordinary source and dependencies cannot enter that condition;
- how safe public declarations are exposed when xlang ships no standard
  library;
- how backend or runtime bodies attach without creating a second authority
  path;
- how a reviewed toolchain version adds a new primitive;
- what remains hard-coded in the compiler; and
- which alternatives lose on P0, W1, W3, TCB size, or multiplicity.

Select the mechanism class, not final keyword spelling or production grammar.
Receive hostile review before asking the owner to accept it as the basis for
the capability study.

### Step 4: minimal public capability basis

Only after Step 3, derive the smallest safe semantic basis. Reuse the Rust
census, 26-domain ledger, dense-family obligations, and held-outs as tests.
Do not inherit the prior six-axis certified-resource architecture by default.
Every retained element must earn its place again under the selected static
gate.

For each proposed primitive:

1. state the abstract safe contract;
2. state why ordinary current xlang cannot implement it;
3. give at least one required capability that depends on it;
4. show that it does not hide a high-level policy;
5. identify its runtime representation and cost;
6. identify any safety or optimizer fact it creates;
7. identify invalidation and cleanup obligations; and
8. provide a removal or subsumption argument.

### Step 5: derivability and cost packet

Map each finite demand category and held-out witness to:

- current-language semantics;
- proposed public primitives;
- ordinary library code;
- irreducible compiler/runtime leaves;
- structural costs; and
- unresolved evidence.

Keep exact D-2 and P-1 fail-closed. A paper route is not measurement. If a
candidate needs empirical confirmation, propose the minimum experiment and
return it for separate authorization.

### Step 6: owner review

Return one packet that asks only decisions supported by the research. At
minimum, separate:

1. selection of the static privilege-definition mechanism;
2. acceptance of the abstract public capability basis for further research;
3. any separately proposed experiment; and
4. any later production syntax, specification, compiler, or runtime work.

No owner decision is currently pending on F versus C, signatures, snapshots,
or revocation.

## 11. Do not do these next

- Do not continue the F/C/S matrix or design a replacement signature scheme.
- Do not build the previously proposed external-frame template registry as a
  cryptographically authorized extension language.
- Do not treat a package, module, path, attribute, or flag as the answer before
  comparing the static mechanism classes.
- Do not assume the six-axis certified-resource basis is selected.
- Do not convert Rust std API rows into one intrinsic per API.
- Do not implement `Vec`, `HashMap`, strings, allocators, atomics, I/O, FFI, or
  another standard library facility.
- Do not modify the language specification or compiler.
- Do not run a benchmark or candidate experiment under D14.
- Do not rewrite hash-pinned historical reports.
- Do not report a category-level paper derivation as exact D-2 or P-1 closure.

## 12. Expected handoff result

A successful continuation will eventually give the owner a short decision
surface:

- the best static compiler/core privilege-definition mechanism and why;
- the smallest independently justified safe public semantic basis;
- constructive evidence that ordinary libraries can derive the required
  systems capabilities;
- explicit structural performance accounting against native conventional
  implementations;
- gaps and the smallest experiments, if any, needed to resolve them; and
- a precise statement of what production work would require separate approval.

Until that packet exists, the honest status is: the finite demand accounting is
valuable, the static gate mechanism has not been researched or selected, the
public basis remains a hypothesis, the cryptographic admission branch is out of
scope, and no production change is authorized.
