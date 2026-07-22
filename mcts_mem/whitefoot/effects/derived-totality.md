- The active safe-Rust compiler has no totality analysis or `willreturn` lowering.
- The archived democ derived totality from loop freedom, trap freedom, and total callees; that rule and its measurements remain historical evidence for a later optimizer experiment rather than live compiler authority.
- Any future totality fact must be derived after semantic checking and must not let proof elision alter source effects or source acceptance.

## Facts

- 2026-07-10 statement: totality is infectious — owner flag, not to be forgotten: one trapping op in a leaf strips willreturn from every transitive caller, killing call-hoisting and CSE for the whole tower above it; Rust suffers identically through panic paths but offers no lever. (sourced)
- 2026-07-10 measurement: the wc counter case — per-increment overflow-trapping counters emitted zero vector ops; switching the structurally bounded counters to wrap mode produced 24 vector ops of SIMD byte-compare and 2x on `wc -l`. Trap-freedom is what admits vectorizable single-exit loops, exactly as the tier's economics predicted. (sourced)
- 2026-07-10 (b95aad02) pitfall: adversarial review of the tier relaxation found the try case missing from the trap-exhibits computation (an EFF-2 violation weaponized into willreturn on an aborting function, IR-verified) and give-match arms invisible to the loop/call scans (willreturn earned with a hidden loop even under the old tier); all fixed with negative conformance cases and a zero-willreturn regression pin. Lesson: fact channels get adversarial review before ship — green checks missed a real unsoundness. (code)
- 2026-07-10 statement: of the four totality levers only the diagnostic tier is built; the const-trip willreturn tier (a literal-bounded loop is willreturn) remains carded and unbuilt, and proof elision deliberately does not restore totality. (sourced)

## Moves

- 2026-07-10 (b95aad02) replaced [[pure-row-totality]]: memory-only effect rows are termination-irrelevant — a loop-free, trap-free function with reads/writes/allocates rows still returns, so demanding a fully pure row blocked willreturn with no soundness gain (sourced)
