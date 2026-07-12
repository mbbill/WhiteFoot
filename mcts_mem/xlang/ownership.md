- Ownership is a deliberately simplified affine calculus: single owner per value, explicit `move` at every consumption site, whole-binding death on any partial move, reinitialization only via a new binding.
- Regions are lexical and named; every borrow is written with its mode and region — there is no inference of modes, regions, or lifetimes anywhere in the language.
- Two borrow modes exist beside ownership: shared and exclusive; exclusivity is judged over resolved places, and content reached through any borrow can never be moved.
- Overlap is conservative: struct fields are disjoint by prefix; two indexed places are disjoint only when both indices are unequal literals; slices over the same root always overlap (OWN-7).
- The checker rejects when unsure: a sound-but-unprovable program is rejected with a diagnostic naming the rule and a restructuring, never accepted on trust.

## Facts

- 2026-07-02 rationale: owner ruling D1a fixed the quantifier — Rust-class conditional envelope, but standing only if the checker is implementable at normal-compiler-frontend effort; the simplification levers (explicit regions over inference, lexical borrows before flow sensitivity, soundness-over-completeness, adopt a formalized minimal calculus) were adopted as design requirements, not conveniences. (sourced)
- 2026-07-07 statement: the ownership core is formally reconciled against Featherweight Rust — obligations OBL-0 through OBL-3 all discharged, including a verbatim page-anchored paper pass; the checker fragment is a proven sound subset of FR's state space, and FR itself bans shadowing for the same simplification reason. (sourced)
- 2026-07-07 measurement: generative model checking with an independent dynamic oracle found 0 soundness violations over 30,000 programs; true over-rejection measured at 7.2% then 5.5%, all on never-escaping statement temporaries — the first measured price of reject-when-unsure. (sourced)
- 2026-07-07 statement: the OWN-7 overlap judgment is conservatism, not measurement — the prototype tested prefix overlap only, slices are uncovered, and the rejection cost on AI-written array code is unmeasured; it interacts with the still-open arrays-loops design gate. (code)
- 2026-07-11 pitfall: pre-commit adversarial audits repeatedly found accepted holes at the type/flow seam — bare affine call arguments becoming type-layer-only implicit moves, shared-for-uniq mode substitution, affine uniq-borrow copying; each closed with exact negative gates. The seam between the two checker layers is where soundness bugs hide. (code)

## Moves

- 2026-07-07 (7c1d7641) replaced [[inferred-borrow-checking]]: replicating rustc's borrow checker is unacceptable implementation effort — a normal compiler frontend is acceptable, rustc-scale inference is not — so D1 stands only on a simplified explicit-region, reject-when-unsure calculus (owner ruling D1a, 2026-07-02) (sourced)
