# Compiler-triggered periodic-copy result

Date: 2026-07-19. Host: Apple M4, Mac16,12. Compiler: Apple Clang
21.0.0, `-O3`, ARMv8-A plus SIMD. Reference: zlib-ng 2.3.3 commit
`12731092979c6d07f42da27da673a9f6c7b13586`.

## Result

For this batched repeated-match API, the unchanged canonical Whitefoot source
shape is sufficient to compete with the pinned zlib-ng match-copy wrapper once
the compiler recognizes its proved periodic recurrence and selects a safe
bulk-copy strategy. The experimental lowering's median exceeded the wrapper's
median in all 14 pinned cases. This separates the source-shape question from
the current literal-lowering result: the source shape carries the necessary
recurrence, but the ordinary compiler does not yet consume it.

The experiment is opt-in in the stage-0 `prototype/democ` compiler, not the
production wfc compiler, through `--periodic-copy-experiment`. It runs only
after normal checker acceptance, infers parameter roles structurally rather
than by identifier, verifies the exact loop recurrence, and alpha-normalizes
the complete DEFLATE, overflow, and capacity precondition before lowering. The
source `match_copy.wf` remains byte-identical at SHA-256
`cd4962c29f6725141d2c555a22986c585f1da8e46274cd776bfee48e270239d7`.
Its explicit volatile precondition check also remains in the generated LLVM IR.

Each sample expands approximately 32 MiB four times in one process. There are
nine balanced-order samples per variant and case. Both compiler paths passed
all 14 reference-output comparisons and all ten accepted/trapping contract
boundaries. Values are medians in GiB/s.

The batched API exposes invariants unavailable to a general token-at-a-time
inflate loop. The certified helper validates total output capacity once, while
this benchmark's zlib-ng wrapper retains an output-safety branch after every
repeated match. For distance one, the helper also loads the invariant source
byte once across all repeats. Both are valid compiler transformations for this
API, but they give the helper work-amortization opportunities that a mixed
literal/match replay may not preserve.

| Distance | Length | Ordinary lowering | Periodic lowering | zlib-ng | Periodic / zlib-ng |
|---:|---:|---:|---:|---:|---:|
| 1 | 3 | 2.086 | 4.567 | 0.950 | 4.809x |
| 1 | 258 | 2.050 | 39.301 | 35.439 | 1.109x |
| 2 | 258 | 0.902 | 35.117 | 30.333 | 1.158x |
| 3 | 8 | 1.276 | 2.214 | 1.657 | 1.337x |
| 3 | 258 | 1.247 | 30.896 | 26.553 | 1.164x |
| 4 | 258 | 1.605 | 27.426 | 25.659 | 1.069x |
| 8 | 32 | 2.343 | 18.775 | 8.246 | 2.277x |
| 8 | 258 | 2.367 | 31.683 | 26.729 | 1.185x |
| 16 | 258 | 2.384 | 35.487 | 7.875 | 4.506x |
| 31 | 64 | 2.378 | 13.095 | 7.509 | 1.744x |
| 31 | 258 | 2.337 | 27.574 | 7.863 | 3.507x |
| 64 | 258 | 21.652 | 21.721 | 17.046 | 1.274x |
| 257 | 258 | 34.255 | 34.550 | 31.055 | 1.113x |
| 32768 | 258 | 33.987 | 34.333 | 29.395 | 1.168x |

## Interpretation

The default source shape is not the limiting factor exposed by this batched
kernel. Its ordinary machine lowering is. LLVM sees a loop-carried overlap
dependency for short distances and leaves a scalar byte loop with bounds
branches. It does not derive that
`out[position] = out[position - distance]` creates a periodic sequence, so it
cannot turn distance one into a fill, short periods into vector
broadcast/permutation, or separated regions into wide copies.

The opt-in compiler pass supplies exactly that missing consumer. It keeps the
single checked source spelling and makes the target strategy a compiler
decision. The former 11x-33x long-match deficits disappear without editing the
Whitefoot kernel. At distances 64 and above, ordinary LLVM lowering was
already competitive and the experimental path changes little; that control
again points to periodic-overlap recognition, rather than general Whitefoot
buffer overhead, as the cause of the original gap.

The 1.069x distance-four and 1.113x distance-257 median advantages are small
enough to overlap ordinary timing uncertainty; this run establishes parity,
not a durable lead, at those points. The large distance-one/length-three ratio
is dominated by per-repeat setup and safety-branch amortization rather than a
claim about a real mixed inflate stream.

This is a `prototype/democ` experiment, not a production wfc pass or a
whole-inflate result. The lowering currently links an ARM NEON target helper,
recognizes one exact canonical recurrence, and covers only this isolated
repeated match-copy kernel. It establishes that the design can pay off for
this batched kernel when proofs feed a strategy-changing lowering; it does not
establish mixed-stream zlib throughput or generalize the result to other
kernel families. A mixed literal/match token replay is required to measure how
much of the gain remains when distance, length, and token kind vary and neither
implementation can amortize work across an artificial run of identical
matches.

Raw samples and provenance are in `periodic-compiler-results.json`; the
reproducible runner is `run_periodic_compiler.py`.
