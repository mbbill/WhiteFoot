# ResourceProfile v1 work schedules

Status: NON-AUTHORITATIVE REVIEW CANDIDATE. This document proposes the exact
work meaning that the eventual hard-profile identity must bind.

Every charge uses the common checked-add, compare, commit, then action rule in
`SCHEMA-SEMANTICS.md`. A charge amount is the explicit number of constant-
bounded actions; it never stands for elapsed time. No listed action may call a
hidden unmetered loop.

## Lexical scan work

One lexical work unit is spent immediately before each of these actions in
both the immutable count and emission passes:

1. read or one-past-end probe of one source byte;
2. comparison of one source byte with one fixed spelling byte, suffix byte,
   escape byte, or continuation-class predicate;
3. validation of one byte in a candidate UTF-8 scalar;
4. commit of one complete raw lexeme or raw issue; and
5. emission-pass conversion of one raw span into one bound token or trivia
   record.

All source access in the scanner goes through a metered byte/probe accessor.
Maximal-run loops, operation-mode suffix matching, exponent-sign lookbehind,
escape validation, and UTF-8 validation use metered comparisons. A bounded
ASCII dispatch after the initial byte read is part of that read action. Count
and emission passes share one meter; a pass disagreement is not additional
work and is a compiler failure.

## Cumulative syntax work

The syntax meter begins at zero after a complete lexical tape and is moved
through classification, parsing, finalization, and canonical audit.

### Terminal classification

Spend one unit before each:

1. formed-token dispatch;
2. fixed-terminal candidate dispatch;
3. one spelling-byte equality comparison for each compared byte, followed by
   exactly one length/end decision for that candidate;
4. byte comparison or byte-class test performed by an external terminal
   predicate;
5. terminal-set insertion attempt; and
6. classified-token record write.

Generated fixed-terminal lookup and every external predicate expose metered
iterators; an unmetered slice comparison is forbidden. A token that produces a
source issue spends only the actions performed before issue selection.

### Deterministic parsing and DIAG-1 syntax selection

The following list is the complete parser schedule. The Phase-4 implementation
must migrate to it and spend from the carried syntax meter:

1. one unit immediately after popping and before executing each ordinary
   parser task;
2. one unit before testing each strong-LL(2) SELECT row in ordinary selection;
3. one unit immediately after popping and before executing each diagnostic
   probe task;
4. one unit before each diagnostic SELECT-row score;
5. one unit before each row revisited while building the maximum-frontier
   expected set or checking the unique best arm;
6. one unit before each bounded four-token dotted-name override window;
7. one unit before each candidate checked by every other bounded diagnostic
   override scan; and
8. one unit before each derivation-element write.

The generated row representation performs at most two constant-time terminal-
set membership tests per score. Task/frame stack pushes are resource-count
actions, not additional work actions. `RepeatZero`/`RepeatOne` member counting
occurs after arm selection and before member scheduling.

### Tree finalization

The following list is the complete finalizer schedule and places C-01's mixed
write at the former child-edge position. Spend one unit before each:

1. private postorder element inspection;
2. source-root extent inspection;
3. local grammar-shape task pop;
4. generated grammar-shape edge comparison;
5. production-node record write;
6. mixed-element record write;
7. terminal record write;
8. source-extent record write;
9. parent/ordinal assignment inspection; and
10. depth-propagation edge inspection.

No mixed write also creates a production-edge record. Production-only child
iteration filters the retained mixed range without allocation.

### Canonical FORM-2 audit

The following list is the complete streaming-audit schedule. Spend one unit
before each:

1. finalized node inspected while deriving format metadata;
2. terminal inspected while deriving one gap;
3. source record whose expected byte length is checked;
4. one actual source byte fetched and compared with one expected fixed,
   variable-token, or gap byte, including production of that expected byte;
5. one unpaired actual or expected byte inspected after the paired prefix
   ends;
6. gap-style record write; and
7. diagnostic NodePath component write after mismatch selection.

For a paired comparison of `N` actual bytes with `N` expected bytes, exactly
`N` units are charged by item 4. If one side has `M` unpaired remaining bytes,
exactly `M` further units are charged by item 5 while those bytes are inspected
to select the length mismatch. No rendered-source buffer or copied AST exists.

## Resolution work

The exact approved R-04 schedule remains unchanged. In summary, it includes
FN-8 structural inspections; complete role/count projection; lookup-record
append; four bottom-up stable merge passes with every scratch copy,
comparison, destination write, prefix scan, predecessor write, and parity copy;
indexed range probes; exactly two selected-origin scans; path writes; and
diagnostic materialization. It performs no event sort, per-use parent walk,
unrelated-owner scan, or hidden string comparison.

The eventual profile packet binds the complete R-04 proposal bytes in addition
to this document. This summary cannot weaken or reorder R-04.

## Evidence obligation

Two independent meters must agree on exact totals. Scaling doubles every
loop-owning dimension. A timing witness measures batches of each constant-
bounded action on the pinned host and uses the slowest hostile batch rate to
derive a conservative service upper bound. This is a preimplementation sizing
witness, not release proof. The production implementation later must
differential-match every exact counter and remain inside the approved RSS/time
envelope; otherwise work stops for redesign or reapproval.
