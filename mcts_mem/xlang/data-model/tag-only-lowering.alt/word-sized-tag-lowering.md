- Every enum tag, including Bool and two-variant tag-only user enums, lowered at i32 in slots, fields, and buffers; boolean values left the i1 domain at every binding.

## Facts

- 2026-07-10 measurement: the owner measured a 34% penalty on the ScanState probe with the i32 lowering relative to Bool's i1 path — two spellings of the same two-state machine had different speeds, which the project's own doctrine classifies as a compiler-side violation. (sourced)

## Moves

- 2026-07-10 (9d44262b) replaced by [[tag-only-lowering]]: equivalent shapes must not have unequal speed — word-sized tags kept the state recurrence out of i1, a measured 34% penalty blocking the width-16 vectorization that the i1 lowering restores to Bool/C/Rust parity (sourced)
