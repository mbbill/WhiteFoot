# Phase 5 entrance review

Status: SUPERSEDED FOR OWNER REVIEW, 2026-07-21. This document remains a
historical entrance audit and grants no implementation authority. Its R-01
combined nominal/constructor namespace would reject every struct and PRE-1's
same-spelled `Overflow` and `NarrowError` enum/variant pairs. Its R-04
standalone resolver limits also violate Decision 15's one invocation-wide
validated resource profile. Do not approve or implement those withdrawn
proposals. The corrected exact non-authoritative packet is
`phase5-successor-proposal/PROPOSAL.md`. Exact v0.9 remains active.

## Result

Do not start the resolver yet.

Phase 5 is not one giant gate that requires every remaining language question
to be answered first. Each semantic substage should close only the questions
that it actually needs. The first substage is nevertheless blocked today by
three numbered-specification decisions and one architecture/resource decision:

1. the collision rule between nominal `TYPEID` declarations and enum variant
   constructors is missing (A-07);
2. OP-1's dotless operation table and its reserved-name list disagree;
3. DIAG-1 deliberately leaves semantic-stage error selection for later
   approval; and
4. the resolver's explicit resource and failure contract is not yet recorded.

The architecture also needs several corrections before it can guide code. The
most immediate one is concrete: `CanonicalSyntaxUnit` owns the verified tree,
but currently lends no read-only way for a resolver to traverse that tree.
Inventing a second AST, reparsing, or putting semantic code inside the syntax
crate would violate the approved one-tree design.

The correct next deliverable is one coherent successor-specification proposal
and the architecture corrections in this packet. Only after exact owner
approval, versioned installation, independent evidence, and the guarded
baseline update may the complete resolver tranche begin.

## Evidence consulted

This review used:

- `THE-PLAN.md`, especially the active blockers and Phase 5;
- exact `spec/kernel-spec-v0.9.md`, including TYPE-6/7, OWN-1..13,
  STOR-1..5, OP-1/9, FN-1..8, EFF-1/2, PROG-2, and DIAG-1/3;
- the approved architecture index and Decisions 5 through 10;
- `facets/v0.9/open-discrepancies.json` and the source evidence named by every
  record;
- the tail of `decision-gates.md`;
- the live compiler, ownership, effects, checks/proofs, fact-channel, and
  semantic-artifact MCTS-Mem nodes and their rejected alternatives; and
- three independent read-only hostile reviews of discrepancy freshness,
  A-question staging, and semantic-stage dependencies.

`python3 tools/facet_discrepancies.py check` still derives exactly seven open
records from the pinned v0.9 bytes. None is stale. The reviews disagreed about
whether contract semantics could be deferred past lexical resolution. The
exact grammar and Decision 6 resolve that disagreement: `callee := IDENT |
OPNAME`, and OP-1 makes a bare IDENT callee either a table operation or a
top-level source `fn_decl`. The language has no contract-member call form.
Conform-binding left names, contract members, and law roles are therefore
closed typed-dependent use kinds for Decision 7, while their enclosing contract
TYPEID and bound-function right IDENT receive ordinary lexical resolution.
Whole-conformance and any future member-call semantics block symbolic typing,
not the first resolver.

## What is already closed

The first resolver may rely on these exact facts:

- PROG-2 forms one ordered, nonempty, closed compilation unit and defines
  top-level declaration order.
- TYPE-6 makes every top-level function signature visible throughout that
  closed unit.
- Locals, regions, labels, generic parameters, and named constants remain
  lexically declaration-before-use.
- The canonical frontend supplies one source-bound, exact-v0.9
  `CanonicalSyntaxUnit`; it has already rejected malformed syntax and
  noncanonical FORM-2 bytes.
- Prelude and operation identities are versioned built-ins, not synthetic
  source declarations.
- Runtime handles stay local. Portable references are structural and are not
  introduced by the resolver tranche.
- Same-kernel artifact replay remains the selected later authority model; the
  rejected second production semantic verifier is not reopened.

## First successor-specification decisions

### R-01: one exact TYPEID collision rule (A-07)

Recommended ruling:

- Source `struct` and `enum` declaration names and every enum variant
  constructor occupy one closed whole-unit nominal/constructor `TYPEID`
  namespace. No two entries may have the same exact spelling.
- Prelude nominal type and constructor names are reserved entries in that same
  namespace. A source collision points to the source node.
- A collision between top-level items points to the later item in PROG-2 order.
  A collision inside one enum or between its variant and an earlier item points
  to the later variant in source variant order. Every case cites TYPE-6.
- Contract declaration names remain in their own whole-unit contract namespace
  because every contract reference occurs in a contract-specific grammar role.
  Built-in contract/predicate names, including v0.9 `Int` and `Float`, are
  reserved entries in that namespace. Duplicate contracts or a source
  collision with a built-in point to the later/source declaration, but a
  contract spelling is not silently made a nominal type or constructor.
- Generic TYPEID parameters remain lexical type declarations. They may not be
  redeclared in their generic list or shadow a live nominal, constructor,
  prelude, or enclosing generic type name. This no-shadow extension is an
  explicit part of the proposed ruling, not something implied by A-07 alone.
- Whole-unit inventory establishes uniqueness; it does not grant early
  visibility. A top-level nominal or contract name becomes visible immediately
  after its declaring TYPEID terminal and remains visible through the end of the
  closed compilation unit. An enum variant constructor becomes visible
  immediately after its variant TYPEID terminal and remains visible through the
  end of the unit. Prelude entries are visible throughout the unit. A generic
  parameter becomes visible after its declaring TYPEID through the end of its
  declaration's generic/header/body scope. It is compared with names visible at
  that declaration; a later nonfunction top-level declaration does not become
  retroactively visible inside the earlier generic scope.

Why: variant constructors are deliberately resolved without a nominal type
context. One nominal/constructor namespace preserves that property, matches the
no-shadowing doctrine, and prevents declaration kind from becoming hidden
lookup context. Contract references already have distinct grammar roles, so
merging them into this namespace would broaden A-07 without a resolution need.

Rejected routes:

- Do not permit a nominal type and constructor to share a spelling and then
  choose by type context.
- Do not use insertion order or a host map collision as the diagnostic rule.

### R-02: derive dotless reservations from OP-1

Recommended ruling:

- The reserved dotless-operation set is exactly the set of every dotless IDENT
  operation name in the normative OP-1 table.
- The numbered specification may print the full list for review, but equality
  with the table is normative and independently checked.
- A source function, field, parameter, binder, generic parameter, named
  constant, region, or other declaration covered by OP-1's reservation rule
  may not bind any member of that derived set.
- Dotted OPNAMEs remain selected by their raw token form and are not IDENT
  declarations.

This closes the current 51-versus-20 mismatch and prevents the same drift from
returning. Merely appending the missing 31 names to another hand-maintained
list is not sufficient.

### R-03: semantic diagnostic selection

Recommended numbered-specification structure:

- Declaration inventory precedes lexical resolution. Resolution starts only
  after the complete declaration set is valid; uses are never resolved against
  poison declarations.
- Every declaration event and lexical-use event has the canonical key
  `(source_ordinal, byte_start, byte_end, NodePath, role_ordinal)`. The role
  ordinal is the left-to-right ordinal of that declaration/use role in its
  owning production. This orders generic parameters, regions, fields, variants,
  parameters, requires locals, match binders, labels, and several roles in one
  node without relying on traversal or allocation order.
- `NodePath` comparison is lexicographic over child ordinals; when one path is
  a prefix of another, the shorter path sorts first. `role_ordinal` is consulted
  only after the complete path is equal.
- The inventory stage selects the minimum declaration-event key, then a closed
  violation rank at that event: reserved/prelude collision; duplicate or
  nominal/constructor collision; then live-name shadowing. The exact successor
  text must give each row its rule ID, location, and payload.
- The resolution stage selects the minimum use-event key, then a closed lookup
  rank at that event: a known declaration outside its visibility interval; a
  known label that does not enclose the `break`; then absence from the required
  namespace or operation inventory. Wrong-type and typed-label/member questions
  belong to Decision 7, not this lookup rank.
- A typed-dependent field, named-argument, conform-member, contract-member, or
  law-role name is classified into its exact deferred-use kind. Classification
  itself is complete resolver coverage; the resolver neither accepts nor
  rejects its later type/member relation.
- An inventory defect outranks every resolution defect even when the latter is
  earlier in source bytes. This preserves failure-atomic, poison-free
  resolution: uses are never resolved against a malformed declaration set.
- Resource, invocation, and compiler-invariant failures stay outside language
  diagnostic ranking.

The exact successor delta must carry the complete closed rows, including
missing and duplicate whole-unit payloads, rather than only this structure.
Every later semantic tranche must add its own numbered within-stage order before
it lands. A host-map iteration order, traversal accident, rule-name sort, or
"first error the implementation happens to notice" is banned.

### R-04: resolver resource and failure contract

The resolver API should take an explicit caller-selected `ResolutionLimits`
value with these `u64` inclusive maxima, in this exact enum order:

1. `max_declarations`;
2. `max_scopes`;
3. `max_scope_depth`;
4. `max_declaration_events`;
5. `max_lexical_uses`;
6. `max_deferred_uses`;
7. `max_spelling_bytes`;
8. `max_lookup_entries`;
9. `max_ancestry_steps`;
10. `max_node_path_depth`; and
11. `max_coverage_records`;
12. `max_node_path_components`; and
13. `max_work`.

Zero is valid and admits only an actual count of zero. Counts are elements
except `spelling_bytes` (source bytes), depths (root/empty path is zero),
ancestry steps (one examined parent edge), node-path components (one stored
child ordinal across all retained paths), and work units defined below. Every
complete event/record belongs to exactly one corresponding count. Coverage is
one record per required syntax node or grammar role under C-02's closed
inventory. Shared spelling interiors are charged once per declaration/use
record that retains them; no interning success changes the normative resource
count.

One read-only structural preflight counts declarations, scopes/depth,
declaration/use/deferred events, spelling bytes, lookup-table/output records,
node-path depth, coverage records, and total retained node-path components with
checked `u64` arithmetic. It does not perform lookup, ancestry walking, or a
null-sink semantic resolution. The preflight charges one work unit before
visiting each syntax element, grammar role, or projected path component; online
`max_work` exhaustion returns before the unperformed visit and outranks a count
excess that has not yet been completely measured. Counter overflow or inability
to represent a required element count in the host address space returns
`AddressSpaceExceeded { family, requested }`. After complete preflight, every
structurally known configured limit is tested in enum order; the first exceeded
family returns `LimitExceeded { family, maximum, actual }`. Output storages are
fallibly reserved in declaration, scope, lexical-use, deferred-use, coverage,
and path-work order; the first failed reserve returns
`StorageUnavailable { storage, requested }` in that storage order. Only after
preflight succeeds does construction continue the same work counter, charging
one unit before each event visit, lookup probe, ancestry-edge examination,
emitted record, and node-path ordinal append, in canonical event order.
`max_ancestry_steps` is charged online because its exact count depends on
lookup. If an ancestry step would exceed both ancestry and work maxima, enum
order selects ancestry first; otherwise exceeding work returns before the
charged action. Checked aggregate multiplication
or addition needed for preflight uses the family of the result being computed;
it never wraps or falls through to allocation.

The root scope counts as one scope. Source declaration roles and exact active
prelude declarations both count as declarations; only source roles count as
declaration events. Exact active operation entries and declarations each count
once in `lookup_entries`. Source declaration/use spellings and retained built-in
declaration/operation spellings count their UTF-8 byte length in
`spelling_bytes`. Prelude and operation counts come from the exact active
specification inventory, not ambient compiler tables. `ancestry_steps` and
`work` are the only online totals; every storage-sized output family is counted
and limited before its reserve.

A resource failure publishes no partial resolution tables and is not a source
rejection. Runs under two profiles that are both sufficient to reach a source
verdict select the same rejection. An insufficient profile may resource-fail
before discovering that rejection. Concrete CLI/release values remain later
profile decisions; this tranche approves the explicit schema and
caller-selected library contract, not a release claim.

## Architecture corrections required before resolver code

### Successor identity transition

R-01 through R-03 necessarily create a new numbered specification. The current
`CanonicalSyntaxUnit` is exact-v0.9 authority and cannot be passed to a resolver
using successor rules. After the successor is separately approved and
installed, the frontend must bind the successor specification hash, regenerate
or revalidate every versioned terminal/grammar table, reproduce the independent
grammar and source-contract evidence, and publish a canonical syntax capability
carrying that exact successor identity. Even if the source EBNF bytes are
unchanged, grammar compatibility is reproduced rather than assumed from a hash
change. The resolver rejects any syntax/prelude/operation
specification-identity mismatch before work. Exact v0.9 remains immutable
historical authority for its own evidence and cannot silently authorize
successor semantics.

### C-01: lend the one canonical tree

`CanonicalSyntaxUnit` must provide a borrowed, read-only traversal seam that
exposes exactly the already-verified representation needed downstream:

- one opaque runtime-local `SyntaxNodeHandle` scoped to the borrowing canonical
  unit, plus root access and production kind;
- one ordered direct-child sequence whose closed elements are
  `SyntaxElement::Production(SyntaxNodeHandle)` or
  `SyntaxElement::Terminal(SyntaxTerminalHandle)`, preserving exact production
  and terminal interleaving and grammar-slot order;
- for a terminal handle, its source token handle and selected terminal
  predicate;
- checked source extent and source ownership; and
- fallible `NodePath` formation under an explicit depth/storage limit.

The handles cannot be constructed, compared, or used without their owning
`CanonicalSyntaxUnit`; they are not portable identity. The seam exists only on
`CanonicalSyntaxUnit`, not on parsed or finalized intermediates. The view
creates no second AST, no semantic fields, no portable IDs, and no mutable
access. It is landed with the resolver tranche and used by production
resolution; it is not an otherwise-unused placeholder. Decision 6's independent
bounded scope model may share exact source/tree input, but must derive roles and
scope events independently and may not call the resolver or reuse its tables or
production role classifier.

### C-02: add one opaque resolution capability

The first semantic tranche publishes one opaque `ResolutionCompleteUnit` (name
subject to ordinary code review). Resolution consumes the exact
`CanonicalSyntaxUnit`; the result owns that unit, the scope tree, declaration
inventory, use-to-target records, typed-dependent deferred-use records, and
coverage tables. Tables can therefore never be paired with another syntax
unit.

Only its private constructor can close the capability. Loose maps plus a
`complete = true` flag are not authority. Symbolic typing accepts this
capability, never raw syntax plus independently supplied tables.

Completeness means every syntactic lexical declaration and lexical use has
exactly one role record and, where required, exactly one resolved target; every
typed-dependent field/member/named-argument/conform/law role has exactly one
closed deferred-use record; and no source node or role is missing, duplicated,
or classified twice. The exact active-successor specification identity,
prelude, and operation inventories are bound internally before work and must
equal the identity carried by the canonical syntax capability. There is no
mutable/raw-table constructor. The public
operation has a closed `Complete`, `SourceIssue`, `ResourceFailure`, and
`CompilerFailure` outcome family and publishes no partial unit.

This capability explicitly contains no types, call edges, CFG, ownership,
effect, optimizer, artifact, backend, executable, or release authority.

### C-03: check every signature before any body

Inside the later symbolic-typing tranche, first kind- and type-check every
declaration schema on which signatures can depend, respecting its own
declaration-before-use rule. Then kind- and type-check every top-level source
`fn_decl` signature as one complete batch and seal the signature environment.
Only then may any function body be checked. Contract `fn_sig` schemas, if
retained, have their own contract scope and do not inherit A-01 whole-unit
visibility. Named constants and other nonfunction declarations retain their
exact declaration-before-use rules. This is the direct implementation
consequence of v0.9's A-01 ruling.

### C-04: keep one graph authority and one judgment definition

- Decision 7 validates each typed call boundary locally and records its
  obligations under the A-17-approved local slot/profile rule. A-17 must close
  before those typed-boundary and instance-identity schemas land.
- Decision 9 is the sole call-graph authority, but constructs two canonical
  stage-specific graph instances: `TemplateCallGraph` from template typed-call
  records and `ConcreteCallGraph` from concrete typed-call records. It alone
  constructs their SCCs. The template SCC gate discharges FN-6 and approved
  A-17 graph-wide preservation before instance work. The provenance-equation
  SCC remains a distinct non-call record family. There is no second boundary
  call graph.
- Template checking and concrete rechecking call the same local
  syntax-directed judgment predicates with explicit symbolic or substituted
  concrete environments. A non-authorizing immutable source-control skeleton
  may share traversal shape, but every template and concrete semantic owner
  constructs and validates its own CFG and judgment records. No template proof
  substitutes for FN-2 concrete rechecking.
- Artifact replay traverses decoded derivation and coverage records
  independently, then invokes the same local judgment predicates. It never
  reuses producer state, traversal sinks, capabilities, completeness flags, or
  in-memory CFG records.
- A dependency/policy test rejects duplicated rule tables or judgment
  functions across phase-specific modules while preserving the separate
  producer and replay traversals.

### C-05: structural CFG precedes cleanup

Phase 5 item 6 currently overstates what an ownership-free CFG can contain.
`ConcreteControlFlowUnit` may contain complete normal, trap, check, and
scope-exit edge topology, but it cannot contain live-value drop plans. After
provenance and ownership close, item 8 attaches exact drop, free, and arena
release operations to normal exit edges. Trap/abort edges carry no cleanup.
There are no placeholder cleanup slots or empty plans with future meaning.

Template effects still run before `TemplateSemanticCoverage` and concrete
effects still run during final whole-unit closure. The compact roadmap must not
be read as deferring all effect checks until the end.

### C-06: Phase 5 records report premises, not final reports

`SemanticallyCheckedDraft` may retain complete trap origins, logical-call
premises, a mandatory check-site inventory with its baseline retained-check
obligation, lifetime dispositions, and report coverage. It cannot contain final
DIAG-3 bytes, final eliminated/retained statuses, or `artifact_hash`: those
depend on later artifact projection, exact empty-or-verified overlay selection,
and final compilation identity. Final report status is derived only after that
overlay is selected.

This correction prevents proof elision or report status from becoming hidden
Phase 5 optimizer authority.

## Later blockers by first affected boundary

The first resolver tranche does not need every item below. They remain explicit
stops for their own semantic capabilities.

| First affected boundary | Open authority |
|---|---|
| declaration schemas, signatures, and symbolic body typing | A-05 recursive nominal layout; A-13 recursive storable-type judgment; EFF-1 row canonicality; whole-conformance/member semantics; FN-7 main spelling; A-09 unreachable-suffix rule before every body node can receive a total typing judgment |
| typed-call and instance identity schemas | A-17 local finite region-slot/fact profile |
| template FN-6/A-17 graph gate | A-18 exact type/const cyclic-edge vector rule; A-17 incoming-edge and SCC preservation |
| template structural CFG | A-03 evaluation order and A-09 reachability are needed before the CFG operation/edge order can be normative |
| complete template semantic coverage | recursive-effect disposition and origin-sensitive body-local effect projection; A-11/A-12 provenance; A-02/A-08/A-16 ownership and joins; A-04 cleanup obligations; affine-deref backing-storage lifecycle |
| concrete instance closure and rechecks | every applicable template rule above plus concrete A-13 storage and A-17 environment validation; no template proof substitutes for a concrete judgment |
| artifact/report projection | retained-check `proof_ref`; A-14 lifetime dispositions; A-15 logical stack frames |
| target qualification | A-06 target-bound frame/object limits |

The contract decision belongs to the symbolic stage, not resolver approval. A
later packet must treat three concerns separately: general interface behavior,
the bounded source-checked FN-4 law facility, and built-in `Int`/`Float`
predicates. At least three honest routes exist:

1. remove provisional general interfaces while separately deciding whether to
   retain or re-home FN-4 and the numeric predicates;
2. retain contract/conform and the exact FN-4 facility, define complete
   conformance checking, but explicitly prohibit general behavior-member calls
   and revise FN-5 for the next kernel; or
3. design an explicit member-call form and complete substitution, conformance,
   provenance, graph, and diagnostic semantics.

The nine directly affected protected FN-3/FN-4 cases are
`fn3-pos-contract-conform`, `fn3-neg-two-conformances`,
`fn4-pos-law-in-contract`, `fn4-neg-bad-lawname`,
`fn4-pos-law-discharged`, `fn4-neg-law-refuted-signedness`,
`fn4-neg-law-undischarged`, `fn3-neg-requires-member`, and
`fn3-neg-signature-effect-mismatch`. Removing or re-homing the facility also
changes six grammar productions, terminal status, FORM-2 sets, PRE-1,
syntax-data generation, grammar evidence, catalogs/facets, discrepancy
identities, and the MCTS fact-channel history. FN-4's checked-law path is part
of the measured checked-algebraic-law differentiator; removing it is a design
redecision, not cleanup. No contract route is selected by this resolver packet.

The following are review hypotheses for later packets, not approved rulings or
implementation-independent evidence:

- EFF-1: one group per effect kind; unique regions in declared parameter order;
  allocations ordered `heap` then arena regions in parameter order. This
  preserves protected duplicate-row rejection
  `x-eff-dup-reads-effect`; the registry's protected-conflict authority still
  needs an exact closure record, while accepting duplicates would require a
  protected verdict change.
- body-local effects: STOR-4-confined local arena allocation may be discharged,
  preserving `stor4-pos-arena-confined`. Reads and writes require complete
  origin sets: a local reborrow of caller storage maps back to its caller-visible
  region/effect and is never projected away; only an effect whose every origin
  is callee-owned, local, and nonescaping may be discharged. This depends on
  A-11/A-12/A-16 provenance and needs an independent adversarial model.
- FN-7: spell the entry point as `fn main() -> own unit`, matching grammar,
  examples, and existing protected sources.
- retained check reports: use a tagged retained/eliminated field or canonical
  null for retained; never a magic proof identifier.
- unreachable suffixes: rejecting the first structurally unreachable statement
  is one conservative candidate, not a selected rule; it changes source
  acceptance and needs exact examples, an independent reachability model, and
  a protected-surface census.
- FN-6: any cyclic SCC containing type/const generics needs one exact kinded
  vector rule that also covers const-only and generic-to-nongeneric cycles;
  region-only functions do not create monomorphization keys.

Each hypothesis needs exact source deltas, models/oracles, mutants, and a
protected-impact analysis. Reviewer agreement alone is not evidence. Listing
them does not authorize implementation.

## Routes explicitly prohibited

- No resolver code before the first successor decisions and semantic
  diagnostic policy are approved and installed.
- No reparse, second AST, CST/AST pair, semantic fields in parser decisions, or
  tree reconstruction from token tape.
- No source-function name, corpus ID, test family, or known project dispatch.
- No "support current examples first" admission architecture.
- No poisoned declarations, partial resolution capability, or continuation
  after an inventory error.
- No host hash-map order, Rust integer behavior, implicit type inference, or
  backend behavior as language semantics.
- No call graph in the resolver or type checker; Decision 9 owns all call-graph
  authority and both stage-specific graph instances.
- No cleanup plan before ownership state is known.
- No duplicate template/concrete/replay judgment implementations.
- No semantic record, law, `pure` row, OWN-9 consequence, or proved check may
  authorize optimization in Phase 5.
- No modification, deletion, weakening, or regeneration of a protected case,
  oracle, digest, or numbered spec merely to make a gate green.

## Approval requested

The owner should decide:

1. approve, reject, or revise R-01's nominal/constructor namespace, prelude
   reservation, separate contract namespace, and lexical generic no-shadowing
   rule;
2. approve R-02's operation-table-derived dotless reservation set;
3. approve R-03's numbered semantic diagnostic event/rank structure for
   drafting as exact successor text, or request a different precedence;
4. approve the R-04 caller-selected resolver limit/failure schema; and
5. approve the architecture corrections C-01 through C-06 as the required
   paper precondition for the first semantic tranche.

No contract/FN-4 redecision is requested by this resolver packet.

After those rulings, the next step is not immediate code. R-01 through R-03
become an exact version-bumped specification candidate with a complete
protected-surface impact census, independent transition evidence,
live-reference update list, and owner-visible byte delta. R-04 and C-01 through
C-06 become exact architecture/plan text. Only the separately approved and
guarded result may activate Phase 5 implementation.
