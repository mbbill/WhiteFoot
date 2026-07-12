- Bool and two-variant tag-only user enums lower to i1 end-to-end: let-slots, field storage, construction, and match all stay in the machine-boolean domain, and the boolean table ops (band/bor/bxor/bnot) operate in i1.
- Loop-carried predicate state stays an i1 recurrence through the whole pipeline; a domain-named two-variant state enum costs nothing over Bool.
- Tag-only enums of three or more variants lower at word width.

## Facts

- 2026-07-10 (c658bc34) measurement: the i1 dataflow scan vectorizes at width 16 (29 16-byte vector ops, previously zero), taking chunk-wc to 134 ms — parity with C and safe Rust — and the wc full-counts port from 0.28 to 0.23 s. (sourced)
- 2026-07-10 statement: three-plus-variant tag-only enums staying at i32 is a recorded, unmeasured need — i8 is possible later if a workload demands it. (sourced)
- 2026-07-10 pitfall: before the fix, `_llty(Bool)` was i32 (breaking Bool-typed give-slots) and the boolean ops were entirely missing from lowering — the affine-era design had left the whole boolean domain untouched by codegen. (code)
- 2026-07-10 statement: writer doctrine P7 pairs with this lowering — keep classifier state and predicates in Bool dataflow with give-match selects for counters; never route state through integer flags or match-arm control flow, which is the shape that regressed to width 2x4. (sourced)

## Moves

- 2026-07-10 (9d44262b) replaced [[word-sized-tag-lowering]]: equivalent shapes must not have unequal speed — word-sized tags kept the state recurrence out of i1, a measured 34% penalty blocking the width-16 vectorization that the i1 lowering restores to Bool/C/Rust parity (sourced)
