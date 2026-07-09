# M3 Current Results

Status: local reference scaffold plus blocker audit; not decision-ready.

Last local command:

```
python3 m3/harness/run.py --suite reference --out /private/tmp/xlang-m3-reference.jsonl
python3 m3/harness/score.py /private/tmp/xlang-m3-reference.jsonl
```

## Reference Summary

| suite | language | runnable | passed | pending | current meaning |
|---|---:|---:|---:|---:|---|
| reference | Rust | 7 | 7 | 0 | Rust can express and pass every current task prompt. |
| reference | xlang | 3 | 3 | 4 | xlang passes the currently expressible smoke tasks but cannot yet express four minimum-sprint tasks. |

The three runnable xlang tasks are:

- `checked_loop_sum`
- `value_match_result`
- `noalias_add`

The four xlang-pending tasks are:

- `checked_integer_parser`: current democ lacks byte-string values, buffers/slices, and enough library surface for a realistic byte parser.
- `arena_ast_builder`: current democ lacks the `pool<T>`/`handle<T>` or arena-backed AST shape required by `compiler/PLAN.md`.
- `buffer_index_kernel`: UNBLOCKED 2026-07-09 — buffer_new/index/len landed (conformance op4/op9 cases green).
- `error_propagation_chain`: UNBLOCKED 2026-07-09 — try/ERR-3 landed (same-E enforced; conformance err3 cases green).

## Decision Readiness

The current evidence is **not** sufficient for a continue/stop decision.

Two independent blockers remain:

1. **Language/toolchain surface blocker**: xlang cannot yet run the first four minimum decision-sprint tasks. Rust can.
2. **Model evidence blocker**: no weak/middle/strong generated submissions have been run yet.

The strict scorer makes this explicit:

```
python3 m3/harness/score.py /private/tmp/xlang-m3-reference.jsonl \
  --required-suite weak --required-suite middle --required-suite strong \
  --require-decision-ready
```

Expected current result: nonzero exit with `decision_ready: false`.

The harness now also supports multiple generated trials per task and
`--min-trials-per-task` readiness checks, so model-tier evidence can be judged
against the fixed-budget protocol rather than a single cherry-picked source.

## Current Interpretation

This is not a pass for xlang and not a final failure of the project thesis. It is a
clear finding that the project cannot honestly run the stated M3 decision sprint
until the missing xlang subset lands or the sprint is narrowed with an explicit
owner decision.

The next decision is therefore smaller than continue/stop:

- either implement the missing xlang subset needed for the four pending tasks,
- or narrow the sprint to the three runnable smoke tasks and accept that the result
  cannot decide the full AI-codegen thesis.

See `IMPLEMENTATION_GATES.md` for the local audit. The important finding is that
the four pending tasks are not harness mistakes: they are real democ/subset gaps.
In particular, implementing `try` without preserving `Result<T,E>` type
arguments would create a false positive because the checker could miss the ERR-3
same-error-type rejection.

## Working Recommendation

Do not proceed to self-hosting compiler work yet.

Continue only if the next unit of work is the minimum M3 unblock: byte/buffer
support, fixed-capacity pool/handle support, checked indexing, and sound ERR-3
`try` propagation. If that unblock is not worth doing, stop or pivot now.
