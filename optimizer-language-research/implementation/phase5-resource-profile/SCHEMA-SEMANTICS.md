# ResourceProfile v1 count and failure semantics

Status: NON-AUTHORITATIVE REVIEW CANDIDATE. These semantics become selected
only with exact owner approval of the eventual profile packet.

This document defines the meaning of every ResourceProfile v1 field that is
not already fixed by the approved R-04 resolver contract. R-04 remains
verbatim authority for fields 19 through 33 and its internal failure order.

## Common counter rule

Every count is an inclusive `u64` maximum. To count one item, the owning stage
first computes `next = used.checked_add(1)`. Overflow returns
`CountUnrepresentable { family }`. It then compares `next` with the effective
maximum. Excess returns `LimitExceeded { family, maximum, actual: next }`.
Only then may it commit `used = next` and perform the counted action.

For an amount greater than one, the same rule uses
`next = used.checked_add(amount)`. A failed check performs none of the covered
actions. No path computes or reports `maximum + 1`.

Every stage entry checks the exact specification identity first and the
effective parent-profile identity second, before work or allocation. A caller
cannot construct a stage view. A capability carries the effective identity
forward. Malformed profile bytes, unsupported profile version or host, wrong
selected hard identity, loosening, specification mismatch at a stage entry,
or pairing a capability/view from another effective profile is
`InvocationFailure`. A build whose compiled schema, work schedule, storage
model, or hard-profile constants disagree with the already validated selected
identities returns `CompilerFailure`. Neither class is a source verdict or
resource limit. R-04 retains the same specification-first, profile-second
entry order.

## Fields 1 through 5: ingress

1. `max_sources` counts records in the required nonempty ordered SourceBundle
   before any record copy. A record may contain zero source bytes. The hard and
   effective value must fit `u32`; source ordinals remain `0 .. count - 1`.
2. `max_logical_path_bytes` is the byte length of one exact UTF-8 logical path
   before validation or copy.
3. `max_source_bytes` is the byte length of one source record before copy.
4. `max_total_source_bytes` is the checked sum of source byte lengths in
   bundle order. Each prefix is checked before the next record is inspected.
5. `max_binding_bytes` is the complete canonical WFSOURCE encoding length:
   `50 + sum(16 + path_bytes + source_bytes)` with every addition checked.

Ingress first tests the complete source count. It then visits records in bundle
order and tests path bytes, source bytes, and the next total-source-byte prefix
for that record. Canonical binding construction separately tests its fixed
50-byte prefix and then each next checked `16 + path + source` prefix against
field 5. Duplicate-path ordering work happens only after the SourceBundle size
counts succeed. Host conversion and layout for source
records, duplicate-order scratch, paths, source bytes, and binding bytes then
follow their production storage order; every admitted fallible reservation
failure is `AllocationFailure`, not `StorageUnavailable`. No partial
SourceBundle or binding escapes.

## Fields 6 through 9: lexical partition

6. `max_token_bytes` is the exact nonempty byte span of one token-shaped
   lexeme. Trivia does not use this field.
7. `max_tokens` counts token-shaped lexemes across the ordered bundle.
8. `max_lexemes` counts every maximal token or trivia partition member.
9. `max_lexical_scan_work` is spent by the exact schedule in
   `WORK-SCHEDULE.md` across both immutable scanner passes. The meter never
   resets between sources or passes.

Each pass visits sources in bundle order. During the count pass, online work
failures occur at their exact action. After a complete lexeme is known, the
lexeme count is tested, then token bytes and token count when applicable.
The first source issue or resource failure stops the pass. Only a successful
complete count permits storage preflight and exact reservation. Storage order
is `Lexemes`, then `SourceBoundaries`. The emission pass uses the same work
meter and must reproduce the count pass exactly; disagreement is a compiler
failure. Allocation failure is failure-atomic.

## Fields 10 through 18: syntax and canonical tree

10. `max_classified_tokens` is tested against the lexer-established complete
    token count before classified-token layout, reservation, membership work,
    or writes. A successful complete classification has
    `classified_tokens == tokens`.
11. `max_production_nodes` counts every completed grammar production written
    to the private derivation, including exactly one `Program` root at depth
    zero.
12. `max_mixed_elements` counts the successor topology's complete interleaved
    non-root sequence: `(production_nodes - 1) + terminals`. The root
    subtraction occurs only after proving exactly one `Program` root.
13. `max_tree_depth` is the maximum production-parent edge count. `Program`
    has depth zero. Terminals do not add a component. Every finalized node's
    computed depth is checked before it is stored.
14. `max_parser_stack_entries` is the prospective checked sum after either
    push: `tasks.len + 1 + frames.len` for a task, or
    `tasks.len + frames.len + 1` for a frame. The sum and limit are checked
    before mutating or reserving either vector. It applies to both ordinary
    recognition and DIAG-1 diagnostic descent. Separate task and frame vectors
    remain permitted, but neither receives a separate caller maximum.
15. `max_list_members` counts every successfully selected member of a
    generated `RepeatZero` or `RepeatOne` grammar node. The mandatory first
    member of `RepeatOne` counts. Nested repeat memberships count separately.
    The count is committed immediately after the member arm is selected and
    before that member is scheduled.
16. `max_expected_terminals` is the maximum cardinality of any one DIAG-1
    expected set constructed for publication. Distinct terminal predicates
    count once; the `SourceEnd` sentinel counts one when present. The closed
    v1 universe has at most 73 members. The complete set is counted before the
    SyntaxIssue is constructed.
17. `max_syntax_work` is one cumulative meter covering terminal
    classification, ordinary parse, parse diagnostic descent, tree
    finalization, and canonical FORM-2 audit in that order. Classification
    creates the meter. Each successful intermediate capability moves the same
    non-cloneable meter and exact used value forward. It never resets, forks,
    saturates, or refunds. Its action schedule is `WORK-SCHEDULE.md`.
18. `max_tree_bytes` is the cumulative charged byte total for the five tree
    record arrays in `STORAGE-MODEL.md`: private `DerivationElement`,
    `NodeRecord`, successor `MixedElement`, `TerminalRecord`, and
    `BundleSourceExtent`. Each array charges `count * approved_stride` with
    checked arithmetic after exact count and before host conversion, layout,
    or reservation. Dropping the private derivation after finalization does
    not refund its charge.

On a complete derivation, `terminals == classified_tokens` and
`private_derivation_elements == production_nodes + terminals`. Both sums are
checked. Parser stack storage order is `Tasks`, `Frames`, then
`DerivationElements`. Parser work occurs online before its charged action;
count/stack failures therefore occur at the attempted event. Production nodes
and DerivationElement tree bytes are counted online before each write. The
mixed-element total and the remaining topology tree-byte charges are tested
only after the complete private derivation establishes their exact values.

Finalization first proves one Program root and the checked inventory. It then
tests fields in this order: `ProductionNodes`, `MixedElements`, `TreeDepth`,
`TreeBytes`. `Sources` and `Terminals` were already bounded by earlier profile
fields but are rechecked for compiler agreement, not as new caller limits.
The exact topology storage order is `Nodes`, `MixedElements`, `Terminals`,
`SourceExtents`. Every nonzero storage undergoes `u64 -> usize`, concrete
`Layout::array`, then exact fallible reservation before any topology write.
Address conversion/layout failure is `AddressSpaceExceeded`, followed by
`AllocationFailure` for an admitted reserve failure. Zero storage performs no
allocation call. There is no production-edge vector, reconstruction scan, or
second mixed sequence.

Canonical audit derives exactly one gap record per terminal, so
`gaps == terminals`. A published canonical diagnostic path has component
count no greater than the already checked `max_tree_depth`; its exact count is
host-converted, laid out, and reserved only after issue selection. Gaps are
the only successful-audit temporary array and are reserved before comparison.
The audit moves the cumulative syntax meter into `CanonicalSyntaxUnit` only on
success. No source issue, resource failure, or compiler failure publishes a
partial capability.

## Current raw-limit migration

Production APIs stop accepting public raw limit structs. Private unit tests
may retain raw helpers that can only be constructed inside their crate. Typed
views derive current implementation inputs as follows:

| predecessor field | v1 source |
|---|---|
| Source `max_sources` | checked conversion of field 1 |
| Source path/source/total/binding bytes | fields 2 through 5 |
| Lex sources/source/total bytes | carried ingress facts; mismatch is compiler failure |
| Lex token bytes/tokens/lexemes | fields 6 through 8 |
| Terminal tokens | field 10; actual must equal field-7-bounded token count |
| Parse tasks + frames | one combined field 14 checked at every push |
| Parse elements | raw combined limit removed; node and terminal writes are independently metered and actual `E = N + T` is checked |
| Parse work | carried field-17 meter |
| Finalize roots | at most private derivation elements; compiler agreement |
| Finalize shape tasks | generated-grammar fixed ceiling and identity |
| Finalize nodes | field 11 |
| Finalize child edges | removed; field 12 MixedElements replaces its position |
| Finalize terminals | field-10 actual |
| Finalize sources | field-1 actual |
| Finalize work | carried field-17 meter |
| Canonical source/total bytes | carried ingress facts |
| Canonical gaps | exact field-10 actual |
| Canonical path components | bounded by field 13 |
| Canonical work | carried field-17 meter |

The grammar-fixed shape-task ceiling is independently extracted from the
exact generated grammar and bound to its identity. Exceeding it is a compiler
data mismatch, not a caller limit.

## Exact count receipts after successful FN-8 admission

All arithmetic below is checked `u64`. These are actual-count receipts, not
relational validity requirements on independently tightened maxima.

```text
classified_tokens = terminals
private_derivation_elements = production_nodes + terminals
mixed_elements = (production_nodes - 1) + terminals
gaps = terminals
source_extents = sources
canonical_path_depth <= tree_depth

declarations = declaration_events + 24
ancestry_steps = scopes - 1
scope_depth <= ancestry_steps
lookup_entries
    = 101
    + sum(exact per-source role insertion multiplicity 0, 1, or 2)
coverage_records
    = production_nodes
    + declaration_events
    + lexical_uses
    + deferred_uses
diagnostic_origins = source_origins + prelude_origins
diagnostic_paths = 1 + source_origins
diagnostic_path_components = exact sum of all selected path lengths
diagnostic_path_components
    <= checked(diagnostic_paths * node_path_depth)
diagnostic_issue_elements
    = 1 + diagnostic_origins + diagnostic_paths
      + diagnostic_path_components
```

The exact fixed spelling charge is reported as separate PRE-1,
operation-family, dotless-reservation, and mode-word components. Source role
intervals charge once each except the approved X09/U18 overlap, which charges
both complete intervals. The final charge is their checked sum.

## Failure authority

Profile validation precedes source handling. Stage identity checks precede
stage work. Online work/count failures precede the action they block. Once a
complete exact count exists, the closed order is field limit, checked host
conversion, concrete layout, exact reservation, then construction. An
`AllocationFailure` means only that an admitted fallible API refused the
reservation. Allocator abort, OS kill, or unaudited dependency allocation is a
supervisor-classified compiler-process failure.

No resource outcome cites a language rule, changes a source verdict, emits a
partial diagnostic or table, skips coverage, or creates an `Unsupported`
language result.
