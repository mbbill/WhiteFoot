- xlang is a systems language whose sole intended writer is an AI; a human approves but does not author.
- Every covered bug class (memory corruption, data races, silent overflow, uninitialized reads) is unrepresentable in accepted source; no writer-accessible unsafe exists anywhere — the sole trusted-assertion class is toolchain-gated, human-approved records the writer cannot author.
- The safety checker's proofs are exported to the optimizer as facts; safety analysis and optimization share one fact base.
- A runtime check exists at every unproved hazardous operation; removing a check requires a machine-verified proof, never writer assertion (one entry-check class is deliberately never removed).
- The language has exactly one canonical spelling per program down to bytes.
- Performance ranks above every remaining goal once AI-writability floors are met; every major decision names its delta over Rust.

## Facts

- 2026-07-05 rationale: the founding priority order and the Rust test (R0: a decision leaving parity with Rust on performance and cheat-proofness has failed) are fixed in CONSTITUTION.md; memory/thread safety is derived from AI-writability, not axiomatic. (sourced)
- 2026-07-09 measurement: the three optimizer-fact channels measured against rustc — effect rows give O(n)->O(1) at opaque boundaries at per-file build cost; scoped aliasing wins short trips with 17x code-size advantage; checked laws give 3.3x on reductions with false laws refuted at compile time. See [[fact-channels]]. (sourced)
- 2026-07-11 measurement: proof-driven check elision made the base64 port the fastest measured implementation on the reference machine (0.16s vs BSD 0.21, GNU/uutils 0.36; kernel 1.66x from proofs) at full checked semantics — the first fact-attributable real-program win over shipped incumbents (the broader vs-Rust reading is superseded by the next entry). (sourced)
- 2026-07-11 statement: expert safe Rust ties the base64 port through iterator restructuring (chunks_exact/zip; throughput ratio 0.997 inside a pre-registered ±2% equivalence band) while the assert-up-front idiom recovers zero checks — the strict D9 bar (a fact-attributable real-program win over best-effort safe Rust) is still open and QOI decode is the designated decider. (sourced)
- 2026-07-10 rationale: D9 pre-registers a confidence gate ahead of large compiler investment: at least one real-program fact-attributable win over best-effort safe Rust, plus corpus frequency evidence that the winning pattern is not vanishingly rare; failing both, the pitch honestly becomes C-class speed with everything checked, reproducible, and AI-authored at parity — a finding, not a failure. (sourced)
