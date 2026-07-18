- The reference bar for T1 was Rust-class static enforcement as Rust ships it: inferred lifetimes and elision, non-lexical (flow-sensitive) borrow liveness, implicit reborrowing — a checker that infers what the writer does not state.

## Facts

- 2026-07-02 statement: the owner preferred this class of checker on capability grounds and conditioned D1a on feasibility in the same ruling — "it is pointless if the effort of implementing such a checker is an impossible task". (sourced)
- 2026-07-06 statement: Oxide is the recorded NLL-upgrade reference if lexical regions ever prove too lossy; its fully-annotated-types premise matches the no-inference direction, so a future revival would relax liveness, not reintroduce inference. (sourced)

## Moves

- 2026-07-07 (7c1d7641) replaced by [[ownership]]: replicating rustc's borrow checker is unacceptable implementation effort — a normal compiler frontend is acceptable, rustc-scale inference is not — so D1 stands only on a simplified explicit-region, reject-when-unsure calculus (owner ruling D1a, 2026-07-02) (sourced)
