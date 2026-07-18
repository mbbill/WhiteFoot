- wfc was planned as fifteen modules over per-kind arena pools with typed handle children (diagnostics as data in a pool, interning arena, recursive-descent parser mirroring the prototype), with two protected seams (typed-AST-to-passes, thin-core-IR-to-backend) and the compiler's own source frozen to a listable, bounded subset.
- I/O was to be about five gated primitives in a trusted C runtime shim owning the process entry, deliberately without process-spawning.

## Facts

- 2026-07-08 statement: approved as the bootstrap sketch then in force; the whole-program single-unit model, the LLVM-IR-text target, the trusted-shim boundary, and the byte-identical fixpoint definition all survived into the successor — what died was the pool/handle data architecture and the module inventory. (sourced)

## Moves

- 2026-07-12 (e8c8eeb1) replaced by [[toolchain]]: fixed-capacity structure-of-arrays tapes with token and node counts bounded from source size let stage-0 democ bootstrap wfc without growable collections, pool, handle, or general generics — none of which stage 0 implements (sourced)
