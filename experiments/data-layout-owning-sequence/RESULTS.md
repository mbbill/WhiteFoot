# E0.1 results ledger

Status: research plus isolated non-production experimentation.  No production
implementation or scored timing has started.

Completed:

- pre-prototype repository verification is green;
- exact compiler source/count/layout/memory baseline is recorded;
- layout, initialization, growth, allocation, owner/lifetime, and capacity-policy
  confounds are identified; valid causal controls are not yet complete;
- the baseline-only native harness passes self-test and a two-process non-scoring
  smoke with frozen source/IR/executable/correctness hashes;
- an unconditional candidate was executed only in the detached worktree
  `/private/tmp/xlang-e01a-candidate`; its exact 57,547-byte reviewed source diff is
  durable as `DETACHED_CANDIDATE.patch` at commit `68a55e4`; its repository-wide
  `make check`, 73 checker tests, 10,000-case modelcheck, field-only IR shape, two
  64-bit target layout folds, and four unchanged-source raw-IR pins passed;
- independent hostile review rejected that candidate as a production design.
- separately authorized current-language work repaired the checker expression-context
  gaps at `7438e17` and strict GRAM-9 plus recursive projection at `50a1ddd`;
  these fixes select no E0.1 design.

The candidate's green tests do not close E0.1a.  Known blockers include:

- `buffer_new<Record>(n, move seed)` evaluates one affine record then stores it
  N times, contradicting `Flat != Copy`; a nested move inside an outer fresh
  constructor has the same contraction;
- the disposable backend's object-size and pointer facts are correct only for
  its frozen 64-bit experiment targets, not a target-generic or 32-bit claim;
- native ASan and UBSan passed on the frozen fixture, but MSan, allocation-fault,
  32-bit/cross-architecture execution, complete internal-tape equivalence, and
  lifecycle/free gates have not run.

No performance result, language adoption, xlc migration, or default-teaching
claim exists.  `BASELINE.md` numbers are static accounting and harness smoke
elapsed values are explicitly non-scoring.

Next stop: owner selection among the reopened ownership, initialization, and STOR-1
branches in `RESEARCH_REPORT.md`. No further candidate iteration implies production
authorization. Production E0.1a still requires explicit confirmation. Under a
non-builder route, E0.1b opens only after E0.1a reaches adopt/reject/defer; under a
builder route, it may open only through an explicitly approved coupled replacement
protocol.
