# Diagnostic-order transition evidence

This directory is non-authoritative evidence for the Phase 5 successor
proposal. It does **not** parse Whitefoot source. Its inputs are deliberately
abstract role streams that a future independently audited syntax-to-role
projection would have to produce. It exercises a deliberately selected
critical subset of the proposed resolver rows; it is not an exhaustive role
matrix or a completeness claim for the resolver.

Two bounded models implement the same proposed resolver boundary without
importing each other. Both first perform FN-8 structural admission; after
admission:

- `model_ledger.py` inventories declarations in canonical event order and
  resolves uses by walking per-scope binding ledgers;
- `model_relational.py` finds declaration conflicts pairwise and resolves uses
  from independently computed visibility relations.

They share only `schema.py`, which validates the neutral input envelope, and
`report.py`, which compares complete reports. Namespace expansion, visibility,
diagnostic attribution, lookup, metering, and report construction are repeated
independently in both models.

The modeled proposal has separate nominal, constructor, and contract domains.
A struct declaration creates one declaration/event and two binding entries:
one nominal and one constructor. The two entries cannot collide with each
other. Prelude `Overflow` and `NarrowError` nominal declarations can therefore
coexist with their same-spelled variant constructors. Ordinary duplicate,
shadow, and constructor-domain failures cite TYPE-6.

The canonical abstract event key is:

```text
(source ordinal, byte start, byte end, NodePath,
 role ordinal, subtoken ordinal)
```

`NodePath` uses production-child ordinals. Prefix order puts the shorter path
first. The subtoken ordinal is explicit because `0_T` and `1_T` each contain a
lexical type use for `T` inside one literal token; the positive case records
that use without pretending the evidence model lexed the token.

FN-8 structural admission completes before declaration and use roles are
classified. Roles inside an inadmissible requires block are suppressed, and
the selected FN-8 issue outranks every inventory or resolution issue.
That branch performs no resolver count, ordinary limit check, ordinary layout
validation, or ordinary reservation; the evidence injects each dormant failure
kind against FN-8 cases and requires every ordinary resolver count to stay
zero.
Declaration inventory then completes before lexical resolution begins. An
inventory issue therefore outranks every resolution issue, even an earlier one.
The role rows exercised here preserve specific attribution: region lookup
failures cite OWN-3; ordinary unresolved values (including the
requires-local-outside-clause case) and explicit type/generic-argument matching
roles cite TYPE-5; constructor, duplicate, and shadow failures cite TYPE-6.
GRAM-10 field-name/order roles are emitted as deferred records. Binder
freshness is inventory work: equality with its written field, repetition in one
arm, or collision with a value live on arm entry points to the offending/later
binder and cites GRAM-10. A FORM-3 reserved spelling at that same binder wins
before the GRAM-10 rows.
Only the selected reason payload is retained. A reserved binder therefore has
no GRAM-10 payload or origins. For a selected GRAM-10 binder, the arm-entry
origins include a later root function (whole-unit visibility) and an enclosing
outer-arm binder; only same-arm binders use the earlier-binder slot.
An arm-constructor role resolves only an enum-variant constructor; a
same-spelled struct constructor is an inadmissible class. The foreign-variant
case first resolves the enum variant and then records the scrutinee/variant
relation as deferred TYPE-6 work.

The FORM-5 numeric-identity suffix resolves any live type parameter with the
exact spelling. Resolution deliberately does not inspect whether that
parameter is unbound or bound to `Int`, `Float`, or another contract. The
numeric-bound requirement is later typed FORM-5 work. Resolving a written
generic bound as a contract is the separate lexical FN-3 row.

Every source declaration and use carries a closed owner path. Global bindings
remain candidates everywhere; non-global bindings enter a use's candidate
universe only from the same owner chain. This retains same-function candidates
from expired sibling scopes for lookup rank 1 while excluding locals and
generics from unrelated functions, top-level declarations, and contract
signatures. LABEL lookup uses a separate same-function inventory: exactly one
matching enclosing loop resolves, same-function matches with no enclosing loop
produce rank 2 with ordered origins, and no same-function match produces rank
3. Disjoint loops in one function may reuse a label spelling.

Both models use a closed evidence-only resource outcome family:
`limit_exceeded`, `count_unrepresentable`, `address_space_exceeded`, and
`allocation_failure`.
The fifteen limit names exactly mirror R-04, including
`diagnostic_origins`. Distinct scopes, maximum parent-edge depth, and exactly
one ancestry construction edge per non-root scope are counted during
preflight; all three limits are tested only after the complete count pass.
No lookup charges or performs a parent walk. In this evidence subset,
`lookup_entries` includes every modeled declaration-to-domain entry actually
inserted into a lookup inventory and every modeled operation entry,
so one struct adds two even though it remains one declaration/event. The
subset has no dependent-declaration carriers; under R-04 those owner-table
records would count as declarations/events but not lookup entries. No
NodePath arena is retained before issue selection. `OrderingScratch` has the
exact `lookup_entries` capacity. Ordinary storage injections model the frozen
all-layouts-before-any-reserve order: any address/layout failure wins before
the first allocation failure, and each family is ordered by storage.

The neutral fixtures retain absolute approved identities: PRE-1 origins carry
their zero-based ordinal in the exact twenty-four-record preorder; operation
families carry their zero-based ordinal in the exact eighty-three-family OP-1
inventory; dotless reservations reuse that family ordinal and mode words use
their FORM-3 alternative ordinal. The schema rejects subset renumbering,
duplicates, and out-of-order inventory projections.

The work abstraction charges one append for every projected lookup entry and
runs the same bottom-up stable merge engine exactly four times over that `D`-
entry vector: `SameScopeKey`, `RegionOwnerKey`, `ArmBinderKey`, then final
lookup key. Each run charges `D` scratch copies, every reached numeric or UTF-8
comparison, every destination write, and the parity-required final copy; the
first three runs also charge their adjacent-prefix scan and predecessor writes.
There is no charged event sort. UTF-8 comparison charges one per byte pair and
one end decision only after an equal shorter prefix. Lexical queries use only
the root and applicable owner-chain partition ranges (or the one current-
function LABEL partition), with charged lower/upper and greatest-start probes.
Source declarations and uses share one dense ordinal in canonical direct-event
order. Each non-whole-unit visibility start is the lower bound of its exact
boundary in that same event order, and each greatest-start search compares
against the queried use's ordinal. A focused sibling-scope fixture places a use
between two same-spelled declarations so substituting lookup-row count for that
use coordinate changes the observable work boundary and fails the suite.
This bounded query projection tests Decision 6's indexed and common-prefix
work edges; it is not a claim that the evidence subset implements every
production partition/class query.

Issue selection retains no counted payload. For the selected issue, one exact
abstract origin iterator runs once to count descriptors and source paths, and
once again to write descriptors. It charges range-entry examination,
fixed-head comparison when both modeled origin-kind heads are present,
self-exclusion, accepted origins, and descriptor writes. The models then write
the primary path and derive source-origin paths by reading those descriptors
once; PRE-1 descriptors add no path. They enforce origin, path, component, and
selected-depth limits, then model concrete-layout validation followed by one
fallible `DiagnosticIssueData` reservation for exactly
`1 + origins + paths + components` elements. That late failure injection is
dormant on a complete result and is observed only after an issue is selected.
The three checked additions use the derived-only
`diagnostic_issue_elements` count family, which is deliberately not a
sixteenth profile limit.

The raw limit objects in this evidence are private test support. Production
R-04 accepts only the validated invocation-wide
`ResolutionResourceProfile<'invocation>` view. The models meter the abstract
transcription of the proposed action schedule, including the fixed bottom-up
stable merge sort for the lookup inventory, rather than a Rust implementation,
allocator, parser, or proof of concrete data-structure costs. Their work counts and injected
storage failures test closure, precedence, exact/one-over behavior, and
sufficient-limit determinism for this selected subset; they are not proposed
hard maxima or an allocation proof for production code. The evidence therefore
proves only the modeled action order at the tested edges and cannot justify a
production `max_work` value.

Run all cases and tests with:

```sh
python3 optimizer-language-research/implementation/phase5-successor-proposal/diagnostic_evidence/run.py
python3 -m unittest discover \
  -s optimizer-language-research/implementation/phase5-successor-proposal/diagnostic_evidence \
  -p 'test_*.py'
```

The commit-bound suite contains 77 cases and 46 tests. In addition to the
focused boundaries, it sweeps `max_work` from zero through the unconstrained
terminal work count for every fixture and requires the complete reports from
both models to remain identical at every seam. Its canonical agreed
report SHA-256 is
`94b2b33e0bad33b66eb85c88e2d5c5bc3129e334530a0477d40574b5604db397`.
`run.py` and a unit test reject any changed report identity even when both
models still agree. This pin freezes non-authoritative evidence; it does not
make the report language or compiler authority.

## Deliberate limits

- The input is already a role stream; no lexer, parser, syntax traversal,
  source extent, or role-classifier correctness is proved here.
- Only the critical rows listed above are modeled. The complete successor role
  matrix remains separate authority; this evidence rejects roles outside its
  closed subset instead of assigning an invented rule attribution.
- Lookup requires an admissible declaration class as well as a matching
  domain. An IDENT/OPNAME callee accepts only a top-level function or operation;
  a same-spelled local/constant does not satisfy it and the closed row cites
  OP-1. The `T` suffix in `0_T`/`1_T` accepts only a live type parameter; a
  same-spelled nominal declaration does not satisfy it and cites FORM-5.
- Typed field/member relations are recorded for their later owner; this
  evidence does not decide them.
- Python allocation and integer behavior are outside the claimed model. A
  production safe-Rust implementation still needs the architecture's checked
  address calculations, fallible reservation, no-growth audit, and failure
  injection for every concrete storage.
- This directory changes no numbered specification, protected case, oracle,
  active compiler capability, optimizer authority, or release claim.
