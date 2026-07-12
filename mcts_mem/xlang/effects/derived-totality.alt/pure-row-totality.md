- willreturn was granted only to a function whose entire effect row was `pure`, whose body was loop-free, and whose callees were all total; any memory effect in the row disqualified the function.

## Facts

- 2026-07-09 (ad22aa73) rationale: the pure-only tier shipped with the effect-attribute channel after measuring that memory(none) alone hoists nothing — LICM requires non-divergence, so a sound willreturn derivation was needed and the fully-pure row was the conservative first cut. (sourced)

## Moves

- 2026-07-10 (b95aad02) replaced by [[derived-totality]]: memory-only effect rows are termination-irrelevant — a loop-free, trap-free function with reads/writes/allocates rows still returns, so demanding a fully pure row blocked willreturn with no soundness gain (sourced)
