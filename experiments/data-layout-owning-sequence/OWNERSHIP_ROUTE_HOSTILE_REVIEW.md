# E0.1a ownership-route protocol hostile review

Status: HISTORICAL EXACT-SNAPSHOT PASS; NEXT STEP SUPERSEDED BY D11, 2026-07-13.

The exact reviewed `OWNERSHIP_ROUTE_PROTOCOL.md` bytes have SHA-256:

```text
88d70083f9cf0219d558675b34a42f54c851793125fccebc07c3f48f4aa1b003
```

This verdict means that three independent read-only review scopes found no
remaining P0/P1 blocker in that exact historical protocol draft. D11 later
superseded its proposed next step; the PASS does not cover a future G0-Core or
dense-family lock. It is not Lock A, a
preregistration, a language-design selection, an implementation authorization,
an external-disclosure authorization, or production approval.

## 1. Review method

The protocol received separate hostile reviews for:

1. ownership, contraction safety, builder-state closure, and cleanup edges;
2. benchmark design, statistics, blinding, and transfer attribution; and
3. consistency with the current spec, constitutional rules, prior E0.1
   protocol, production handoff, and repository process.

The second exact snapshot, SHA-256
`acfd3ac34163b2b7bfe10023a63ab359d026d0362ba5ee9979d38855e8e9f1e1`,
received three `REVISE` verdicts. Every reported blocker was dispositioned. The
three scopes then re-read the final exact snapshot above and independently
returned `PASS`. Reviewers made no repository edits.

## 2. Ownership and state dispositions

### S1: an outer marker could duplicate an unmarked affine inner record

The rejected snapshot defined `DeclaredCopy(T)` as an outer marker plus the
shared structural record domain. A marked wrapper could therefore make an
unmarked affine inner record duplicable.

Resolution: `DeclaredCopy` now recurses through record fields. Every nested
record must independently carry the marker; primitive and tag-only Copy fields
are the leaves. A marked-outer/unmarked-inner negative and a both-marked
positive are mandatory fixtures.

### S2: destructive assignment could overwrite an open builder

The rejected snapshot did not explicitly close `set builder = ...`, leaving the
old allocation's ownership undefined.

Resolution: a builder is forbidden as either the target or right-hand side of
`set`, and both forms are mandatory negative fixtures. Finish remains its only
consuming operation.

### S3: cleanup coverage omitted normal exit forms

The abstract state machine said “normal scope exit,” but the fixture list named
only fallthrough, `return`, and `break`. An arm-local `give` and ERR-3 `try`
propagation could therefore miss cleanup without failing the frozen suite.

Resolution: every non-trap scope-exit edge is explicit. Fallthrough, `return`,
`break`, `give`, and `try` propagation must free an open builder exactly once.
The matching successful-finish cases must transfer the pointer and later free
the buffer once. Complete-row replacement now makes the old resource-free row
dead once, installs the moved row as the sole slot value, and enters transfer
accounting without becoming extraction.

## 3. Benchmark and attribution dispositions

### B1: two locks could choose the sample count

Resolution: Lock A alone freezes every scored count and power assumption before
candidate implementation. Lock B can only attest that those counts remain
unchanged and executable. A count change requires a new reviewed Lock A.

### B2: correlated writer tasks could be pseudo-replicated

Resolution: the template family is the resampling cluster for correctness,
repair, and ownership-policy edits. Lock A must choose one fully specified
cluster-aware paired method and power the run from independent cluster count. A
task-independent exact binary test is forbidden unless there is one paired
observation per cluster.

### B3: source/output identity could not transfer backend counts

Resolution: semantic events and physical backend materializations are separate
channels joined by stable site and run/input identifiers. Backend counts must
come from direct scoring-binary tracing or a post-code-generation instrumented
clone whose CFG, successor map, and materialization map are identical after
counter stripping. Any unmatched site or path is `indeterminate` and fails a
protected lane. Load and store bytes are separate.

### B4: per-task hidden results could influence later requests

Resolution: hidden timing, IR, assembly, code shape, and transfer accounting are
not generated or inspected until every scheduled task/arm trajectory has a Run
Freeze and the campaign receives a Campaign Freeze. Before then, operators can
see only the deterministic correctness diagnostics registered for repair.

### B5: the xlc contrast could admit candidate-only arrays

Resolution: an AST-level allowlist permits only the declaration marker, the
exact registered initialization region, and ownership-mandated `move` tokens.
Declared-Copy arrays are ceiling evidence outside the direct route contrast.

### B6: protected-lane accounting was asymmetric

Resolution: an unregistered semantic or backend record-wide transfer fails
either candidate in protected field-only and field-update lanes. Only
Lock-A-registered initialization and complete-row replacement traffic is exempt,
and that traffic remains measured.

### B7: Lock A itself lacked hostile review

Resolution: the exact Lock A bytes must pass ownership/state, layout/codegen,
and benchmark/statistics hostile reviews before owner approval. A material
correction changes the hash and repeats all three.

### B8: current SoA events did not define row weights

Resolution: Lock A must contain a machine-readable, independently audited
mapping from current column events to logical row events, including temporal
grouping and corpus identity. Ambiguity invokes the unweighted intersection
fallback.

## 4. Specification and process dispositions

### C1: static maintenance evidence could select a route

Resolution: only a preregistered weak-writer correctness, repair, or
ownership-policy-edit endpoint can establish W1 in this screen. Source size,
token count, readability, and expert maintenance opinion are descriptive.

### C2: the older protocol still appeared to authorize implementation

Resolution: the paired protocol now has explicit global precedence for
authorization, baseline, locks, timing, profiling, and external calls. The old
isolated-smoke permission does not apply to either candidate.

### C3: the spec-price ledger and record-array consequences were incomplete

Resolution: Lock A must classify every current normative rule and related formal
obligation as unchanged-reused, candidate-amended, or not-applicable, with
implementation, test, and report consequences. The minimum rule surfaces for
both bundles are explicit. Declared-Copy arrays now have frozen target stride,
alignment, checked size, frame-limit rejection, fill, and drop semantics, and
remain outside the direct contrast.

### C4: production handoff underpriced the builder

Resolution: advancement remains only input to the absolute capability gate.
Production requires an explicit META-5/spec/design-tree disposition, including
STOR-1/STOR-3 changes for the built-in heap-owning builder, plus the existing
R0, R1, migration, and PATTERNS gates.

## 5. Earlier hardening retained in the final snapshot

The final protocol also retains the earlier review dispositions that:

- replaced the colliding candidate word `copy` with the currently
  collision-free `copyable`, with a repeated Lock A census;
- separated the shared target-independent record domain, recursive declared
  Copy, and target-specific fixed layout;
- froze record-buffer layout, overflow, zero-count allocation, OOM, and
  exact-once normal-drop behavior without changing primitive-buffer lowering;
- defined the builder's exact type, operations, effects, call shape,
  confinement, state machine, traps, and no-partial-view rule;
- closed the ownership-context table and many-to-many semantic/backend transfer
  provenance;
- made `CURRENT` an exact unchanged-source identity control;
- used one direct paired candidate contrast instead of comparing separate
  significance results against current SoA; and
- separated intrinsic bundle contradiction from repairable artifact or campaign
  failure, so an invalid run never advances its rival.

## 6. Historical verdict and superseded next stop

The exact final protocol is fit for owner review. It deliberately selects
neither bundle. No candidate code, timing, profiling, xlc migration, pattern
change, production semantics, or external model call is authorized.

The next-stop paragraph in the reviewed snapshot proposed a concrete Lock A for
this paired narrowing. D11 supersedes that proposal. The owner will separately
discuss whether to authorize bounded G0-Core work. Only after G0-Core and an
exact dense-family Lock A close may the owner consider lifting the E0.1 pause;
the dense lock must retain, revise, or supersede this protocol's relevant arms
and measurements. This historical PASS authorizes no such work and does not
automatically restart the paired experiment.
