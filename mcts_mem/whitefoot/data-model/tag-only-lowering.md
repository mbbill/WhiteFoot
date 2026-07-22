- The active safe-Rust compiler lowers Bool and user tag-only enums with at most two variants to i1, and tag-only enums with three or more variants to i32, consistently across values, calls, equality, and match dispatch.
- Exact v0.11 requires nominal tag equality to compare validated discriminants without exposing their representation; it does not require the archived democ's physical widths.
- The archived democ's i1 lowering for Bool and two-variant tag-only enums is retained as measured evidence for the future backend, including the width-16 vectorization result; its word-width lowering for larger enums is unmeasured historical policy, not current authority.

## Facts

- 2026-07-10 (c658bc34) measurement: the i1 dataflow scan vectorizes at width 16 (29 16-byte vector ops, previously zero), taking chunk-wc to 134 ms — parity with C and safe Rust — and the wc full-counts port from 0.28 to 0.23 s. (sourced)
- 2026-07-10 statement: three-plus-variant tag-only enums staying at i32 is a recorded, unmeasured need — i8 is possible later if a workload demands it. (sourced)
- 2026-07-10 pitfall: before the fix, `_llty(Bool)` was i32 (breaking Bool-typed give-slots) and the boolean ops were entirely missing from lowering — the affine-era design had left the whole boolean domain untouched by codegen. (code)
- 2026-07-10 statement: writer doctrine P7 pairs with this lowering — keep classifier state and predicates in Bool dataflow with give-match selects for counters; never route state through integer flags or match-arm control flow, which is the shape that regressed to width 2x4. (sourced)
- 2026-07-22 code: the production LLVM path now implements the measured i1 choice for Bool and two-state user enums while retaining the recorded i32 choice for larger tag-only enums; independent equality and dispatch programs execute through both widths. (code)

## Moves

- 2026-07-10 (9d44262b) replaced [[word-sized-tag-lowering]]: equivalent shapes must not have unequal speed — word-sized tags kept the state recurrence out of i1, a measured 34% penalty blocking the width-16 vectorization that the i1 lowering restores to Bool/C/Rust parity (sourced)
