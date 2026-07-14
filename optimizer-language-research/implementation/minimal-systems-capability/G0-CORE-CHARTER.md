# Minimal Systems Capability Basis: G0-Core Research Charter

Status: owner-authorized research charter, 2026-07-14. This charter authorizes
the complete research and accounting program described below. It authorizes no
candidate or production language mechanism, compiler implementation,
specification change, pattern-catalog change, xlc migration, scored candidate
run, or default teaching change.

## 1. Research question

xlang is intended to be a general-purpose systems language. It may ship no
standard library, and it need not reproduce Rust's named types or APIs. It must,
however, let checked ordinary libraries derive the everyday capabilities that a
systems-language standard library provides, with competitive asymptotic and
structural performance and without writer-visible unsafe or container-specific
compiler privilege.

The research question is therefore:

> What Pareto-small set of checked storage, ownership, lifetime, behavior,
> boundary, and proof capabilities lets ordinary xlang libraries derive the
> required systems contracts efficiently while preserving the protected
> zero-tax paths?

"Small" does not mean the fewest primitive names. A one-item raw-memory escape
has maximal permission and proof cost and is inadmissible. Candidate bases are
compared by normative rules, checker and trusted-computing-base state, trusted
facts and paths, writer spellings, runtime metadata and branches, code size, and
tax on protected baselines. The result may be a Pareto frontier rather than a
mathematically unique minimum.

## 2. Finite external anchor

The primary completeness anchor is the stable public library surface of Rust
1.97.0, released 2026-07-09:

- release tag: `1.97.0`;
- annotated tag object: `eca4cdea45792600b4275e9d4c64fd827d575a24`;
- peeled source commit: `2d8144b7880597b6e6d3dfd63a9a9efae3f533d3`;
- reference crates: `core`, `alloc`, and `std`;
- reference documentation and source: the rustdoc and `library/` tree generated
  from that exact commit.

Rust supplies a finite, independently maintained list of caller needs. It is
not a design oracle. Rust names, traits, `Deref`, `Drop`, unsafe implementation
techniques, and concrete representations are evidence, not defaults for xlang.
The census extracts observable contracts: results and order, ownership and
invalidation, failure and destruction, complexity, contiguity and address or
identity guarantees, iteration and range behavior, allocation and memory
ceilings, behavior parameters, concurrency semantics, and platform boundaries.

Stable safe caller operations form the primary contract anchor. Stable unsafe
operations, nightly APIs, and unsafe standard-library implementation code are
recorded separately as evidence of implementation requirements or privileged
boundaries; they are never treated as an acceptable xlang surface merely
because Rust exposes or uses them.

## 3. Completeness accounting

Every stable public Rust item in scope must terminate in exactly one auditable
accounting route:

1. a normalized caller-observable contract cluster;
2. a redundant surface form derived from another cluster;
3. a trusted platform-frame or ABI boundary whose privilege is explicitly
   priced;
4. an explicit later family lock with a named blocked claim; or
5. a documented non-goal with a first-principles reason.

No unclassified item or subsystem may disappear because it is inconvenient.
Target-specific intrinsic catalogs may be compressed by architecture and
semantic class, but their module set, counts, and digest remain mechanically
accounted. Generated impl duplication and purely documentary aliases may be
deduplicated only by a recorded rule.

The detailed first closure is the sequential, unique-owner, ordinary-library
data-structure floor established by D11. The whole systems envelope is also
accounted at domain level so that passing the data-structure floor cannot be
misreported as completing concurrency, resource/FFI, custom-allocation,
async/cancellation, pin/address-sensitive, shared-ownership, Unicode-text, or
target-intrinsic capability.

Rust's standard library is necessary but insufficient as a generativity test.
Visible cross-ecosystem topology witnesses and three training-excluded held-out
witnesses test whether public checked mechanisms support structures that were
not prebuilt for the census.

## 4. Contract normalization

Each nonredundant operation is normalized as:

```text
pre-state + input ownership + behavior parameters
    -> post-state + result ownership + failure/destruction effects
```

Each row records, when applicable:

- occupancy topology: full, dense prefix, circular or segmented, sparse,
  multi-range or transient hole;
- ownership transition: borrow, move-in, move-out, replace, relocate, clone,
  share, revoke, or destroy;
- borrow provenance and invalidation;
- exact destruction on every normal exit and the current aborting-trap rule;
- checked capacity, allocation, callback, I/O, and platform failure;
- identity, address stability, order, contiguity, and range guarantees;
- callable equality, hashing, ordering, cloning, formatting, or callback
  behavior;
- asymptotic time, allocation count, initialized and moved bytes, metadata,
  checks, branches, and memory ceilings; and
- every metadata-to-payload or state-to-access optimizer fact and its
  invalidation events.

Aliases and convenience methods may share a contract cluster. Distinct
ownership, failure, invalidation, complexity, stability, or resource guarantees
must remain distinct even when Rust gives them similar names.

## 5. Derivation standard

A Rust contract is covered only when the ledger contains all of the following:

- an ordinary checked xlang library sketch using only an explicit dependency
  allowlist;
- a normal-exit ownership and exact-destruction argument, including early
  return, checked failure, partial construction, and abandoned affine state;
- an asymptotic argument;
- structural cost accounting for allocation, initialization, element traffic,
  metadata, checks, branches, and code size;
- fact-channel and invalidation accounting;
- applicable negative soundness canaries; and
- a status of direct, derived, unproved, gap, trusted boundary, scoped deferral,
  redundant surface, or non-goal.

The following do not count as efficient derivations unless a family lock later
measures and admits them for the exact contract:

- constructing generic payload values for spare capacity;
- per-element allocation for a contiguous-storage contract;
- rebuilding an entire structure for a local operation with a stronger
  required bound;
- hidden `Copy` or deep-clone requirements;
- generation, sparse-state, or recycling tax on the protected append-only path;
- standard-library-only raw privilege or a container-specific compiler opcode;
- a transition that is safe only if the writer later calls `finish`;
- a route valid only for Copy, tiny payloads, or one disclosed witness; or
- a candidate-specific compiler recognition rule.

## 6. Performance evidence model

Later family locks, not G0-Core, freeze numeric margins and scored workloads.
G0-Core freezes two required controls:

1. **same-shape attribution:** match algorithm, representation, capacity policy,
   allocator, payload, and trace against Rust where possible; compare facts on
   and off and count structural operations before timing; and
2. **end-to-end contract comparison:** compare the selected canonical xlang
   route with the unmodified idiomatic Rust 1.97.0 standard-library route under
   the same observable contract.

The first control identifies language/checking tax or benefit. The second tests
whether the canonical route is competitive for the actual caller need. A named
container may be derived from another family when it preserves the frozen
contract and cost class; one-to-one API or representation parity is not
required.

## 7. Required research artifacts

G0-Core is complete only when the repository contains:

1. this exact baseline and extraction policy;
2. a reproducible raw stable-API inventory with tool version, counts, digest,
   and deduplication rules;
3. a domain ledger accounting for the full stable `core`/`alloc`/`std` surface;
4. a normalized operation-contract census for the detailed data, text,
   iteration, ownership, and lifecycle scope;
5. a capability-basis registry separating caller contracts from candidate
   language mechanisms;
6. a contract-to-capability derivation matrix with gaps, structural costs,
   fact channels, and xlang evidence;
7. visible cross-ecosystem witnesses, held-out dependency budgets, and scoped
   deferrals;
8. explicit traceability to the D11 registry and paused E0.1 obligations;
9. a Family Lock A template carrying exact semantics, soundness, performance,
   construction, holdout, and META-5 schemas forward; and
10. a synthesis report that states what is closed, what remains a gap, and the
    smallest defensible next family research request without selecting a
    production mechanism.

Every generated table must be reproducible from checked-in scripts and
checked-in classification data. Every manual exclusion or merge needs a reason.
The final exact artifact set receives independent hostile reviews for:

- census completeness and repository/design-tree consistency;
- ownership, initialization, destruction, failure, and fact-channel soundness;
  and
- performance contracts, derivability, staging, and claim discipline.

Findings are repaired before the final exact-hash pass. Durability remains one
commit plus one `decision-gates.md` entry per completed step.

## 8. Non-authorization and claims discipline

This research may inspect sources, generate inventories, construct proof
sketches, and run non-candidate accounting tools. It may not implement or expose
language syntax, a kernel transition, trusted fact, standard container,
candidate mechanism, benchmark candidate, or production compiler path.

Completion of G0-Core authorizes only an owner discussion of the first Family
Lock A. It does not authorize that lock, any candidate implementation, or E0.1
restart. The complete general-purpose systems-language claim remains blocked by
every explicitly deferred systems domain until its own contract and evidence
gate closes.
