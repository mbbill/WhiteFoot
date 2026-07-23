- The production compiler is written in Whitefoot and bootstrapped by the Python democ compiler until emitted LLVM reaches a byte-identical self-hosting fixpoint.
- wfc uses fixed-capacity structure-of-arrays tapes; stage 0 lacks ordinary growable collections, keyed collections, strings, general generics, and related compiler-building facilities.
- Stage 0 compiles with optimizer facts disabled until wfc implements its own effect checking; the first facts-off fixpoint freezes stage 0 as an independent oracle.
- After the first fixpoint, accepted-language growth and optimizer fact channels move to wfc, which later re-establishes a facts-on fixpoint.
- Exact compilation of the compiler source unit, bootstrap stage progression, and byte-identical self-hosting are required milestones for production-language progress.

## Facts

- 2026-07-07 rationale: the selected ladder was temporary host-language demo, then real compiler, then compiler in Whitefoot, using self-hosting as the language's ultimate dogfood project. (sourced)
- 2026-07-12 implementation decision: fixed-capacity structure-of-arrays tapes replaced the pool plan because democ did not implement growable collections, pool and handle types, or general generics. (sourced)
- 2026-07-17 owner ruling: democ would freeze after the first facts-off fixpoint, while later language growth would occur in wfc with focused independent semantic models. (sourced)
- 2026-07-20 limiting evidence: wfc had 655 functions but only 166 provisional clean classifications and 15 emitted functions, while its source omitted 4,568 required explicit region arguments and lacked a conforming entry point; implementation effort had shifted toward exact source-shaped profiles rather than a general compiler. (sourced)

## Moves

- 2026-07-20 (75b768ba) replaced by [[permanent-artifact-compiler]]: the self-host-first ladder coupled production semantic progress to repairing stage 0 and a nonconforming, incomplete compiler unit under a language without ordinary compiler-building collections or text; one safe-Rust production implementation preserves the specification-derived checked-artifact architecture while freezing both predecessors (sourced)
