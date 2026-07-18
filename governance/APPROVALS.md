# Spec & test approvals ledger

Append-only. The kernel specification and the semantics-bearing test surface are
OWNER-GATED. This file is the authorization record: an agent must obtain the
owner's explicit approval for a change to a guarded surface, append an entry
here, and only then commit. Approval of a plan or phase is **not** approval to
change the spec.

Guarded surfaces (see `tools/spec_guard.py`):

- numbered kernel specs `spec/kernel-spec-v*.md` — any add/remove/in-place edit;
- conformance expected verdicts `conformance/manifest.jsonl` + `conformance/cases/**`;
- frozen oracle digests in `tools/codegen_parity.py`, `tools/test_checked_automation.py`;
- reference semantics tests `prototype/checker/test_checker.py`, `prototype/democ/test_codegen.py`.

Adding a new test or a new conformance case is always allowed. Modifying,
deleting, or weakening an existing one — or regenerating a pinned oracle digest —
requires an approval below. Never make a failing check pass by changing what it
expects.

Protocol for an approved change:

1. Present the exact delta to the owner and get explicit approval in the session.
2. Make the change (numbered specs bump version + rename; never edit in place).
3. Run `make approve-spec REASON="<what the owner approved>"`. This regenerates
   `governance/guard-baseline.json` and appends an entry with its `baseline`
   hash. `make check`'s `spec-guard` layer fails on any guarded change whose
   baseline hash is not logged here.

Each entry records: the date, that the owner approved, the reason, and the
`baseline` SHA-256 the approval authorizes.

## 2026-07-18 — approval
- owner: approved in session
- reason: Governance baseline: establish the spec/test guard at the committed main state (commit c18013b); no guarded content changed. Owner-directed governance lockdown 2026-07-18.
- baseline: 0e876fd68b1da613de96364ba1d5ce33ccebe7c3ea508b0ad0d2dc06f9709749
