- Every function signature declares an effect row — reads/writes/allocates over named regions, plus traps — in one canonical order; `pure` is the unique spelling of the empty row (EFF-1).
- Rows are checked in both directions against a syntactic exhibits relation: undeclared-but-exhibited and declared-but-unexhibited are both errors; the relation counts proof-elided checks as still exhibited, and rows are stable under optimization.
- There is no global mutable state and no static region; parameter-reachable memory is the only memory a function can observe, and the row's named regions cover all of it.
- Declared rows lower to guaranteed attributes on both the definition and the declaration; callers optimize across opaque boundaries without body visibility.
- `pure` licenses deduplication and reordering; eliminating an unused pure call additionally requires a termination proof, which v0 does not have; unused pure calls are retained.

## Facts

- 2026-07-09 measurement: the effect-attribute channel on a 2e9-iteration opaque-boundary kernel — declared facts 0.00 s versus 1.47 s own control and 1.49 s cross-crate Rust without LTO, tying Rust's fat-LTO 0.00 s: an O(n)-to-O(1) class change, LTO-grade cross-module optimization at per-file build cost; Rust structurally lacks the source channel (no way to declare trusted effects on an extern fn). (sourced)
- 2026-07-09 pitfall: three separate conformance case files shipped spec-wrong effect rows (pure or missing traps) and the implementation correctly rejected its own test suite each time — effect rows in hand-written cases must be derived from the exhibits relation, not guessed. (code)
- 2026-07-09 rationale: exactness of rows (declared-but-unexhibited is an error too) exists to maximize optimizer facts and to block padding a row as a place to smuggle effects; the "even if later proven away" clause keeps acceptance decidable from the artifact alone. (sourced)
