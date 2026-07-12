- `requires` is an optional prologue on a concrete function after its effect row: zero or more clause-local lets then exactly one final check, all in flat form over pure, total, non-trapping table operations (FN-8).
- Every invocation executes the block at callee entry — including entries from foreign callers; a false condition traps; a true condition contributes exactly one checked fact, visible only in the dominated body.
- Ordinary call acceptance never depends on a caller proof, and the entry check itself is never removed by any proof tier.
- The clause is checked, never trusted: it is not an assume and not a member of the toolchain-gated trusted-assertion family; a clause with no effective statements is rejected.
- Elision is obligation-driven: the compiler derives the discharging obligation from the body, independently normalizes the requirement, and elides a dominated implicit check only on an exact match; with facts off the identical analysis runs and applies no marker, and diagnostics double as a control oracle.

## Facts

- 2026-07-11 rationale: callee-boundary coverage was selected over reliance on known callers because the direct-C entry path showed entry enforcement is necessary — a caller-proof scheme leaves foreign entries unprotected; contract/refinement placement was deliberately deferred rather than silently giving conditional semantics to the contract system. (sourced)
- 2026-07-11 (c0b3ef8d) measurement: the checked capacity relation N <= 3*floor(C/4), tied to the zero-based i+=3/o+=4 lockstep induction, proves all 27 base64 bounds sites; kernel 2.480 to 4.233 GB/s (1.71x), reaching the perfect-index-elision ceiling within noise with one retained entry trap; the hostile panel re-derived the relation as exactly tight (12 passes, 11 traps at N=9) and verified wrap-impossibility of 3*(C>>2) line by line. (sourced)
- 2026-07-11 (2d819233) pitfall: the panel found one real hole — a doc-only `requires` clause vanished before validation (doc fields filtered, the empty list treated as no clause at all); fixed by rejecting present-but-empty clauses, and the clause statement filter was inverted from blacklist to whitelist so unknown statement kinds fail closed. (code)
- 2026-07-11 statement: review ruling B1 — approval identity for any future retained-site approval must be a per-site dependency-cone digest, never whole-artifact hashing, because whole-artifact identity invalidates every approval on every commit and guarantees a rubber-stamping approver whose records launder unreviewed debt with false provenance; approvals stay forbidden until cone identity exists. (sourced)
- 2026-07-11 statement: writer doctrine P9 — a `requires` predicate states an actual invalid-call boundary, never a common-case or worst-case allocator hint; expected shortage is a recoverable value, not a contract trap. (sourced)
- 2026-07-11 statement: the semantics (existence, callee-entry execution, always-retained check, concrete-only scope) are evidence-selected; the `requires { let* check }` block spelling is minimality-selected and R3-provisional pending a writer-tier comparison against a credible single-predicate alternative. (sourced)
- 2026-07-11 statement: the obligation-driven replacement preserved the recognizer's exact acceptance set — 176/176 identical acceptance results and byte-identical IR over the full corpus in both facts modes. (sourced)

## Moves

- 2026-07-11 (6f031496) replaced [[recognizer-driven-elision]]: the compiler must derive the discharging obligation from the body and independently normalize the requirement, so that unresolved accounting fails closed and diagnostics name the first missing fact and first failed premise instead of an opaque recognizer verdict (sourced)
