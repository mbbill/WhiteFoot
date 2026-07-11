# base64 port (safe-direction pilot #2)

Status: MEASURED 2026-07-10. First const-array consumer: byte-identical to the
RFC 4648 alphabet, fuzz-verified, faster than GNU and the Rust rewrite, ~parity
with the platform-tuned BSD tool.

## What it proves
- The const-array feature (implemented this session) works on a real codec:
  the 64-entry alphabet is a `const b64: array<u8, 64>` looked up per sextet.
- Byte-identical to system base64 on all RFC 4648 test vectors and 300/300
  random fuzz cases (newline-normalized; both encode identically).

## Performance (384MB random input, warm, medians, Apple M4)
| implementation | time |
|---|---:|
| BSD base64 (macOS, platform-tuned) | **0.20s** |
| xlang xb64 (kernel + C driver) | 0.23s |
| xlang xb64 (no-facts control) | 0.23s |
| GNU base64 (gbase64) | 0.36s |
| uutils base64 (Rust) | 0.36s |

- xlang is 1.6x faster than GNU AND the Rust rewrite; ~15% behind BSD's
  hand-tuned encoder. A codec is the "fast shape is the obvious shape" case —
  parity-at-C-speed is the honest headline, not a speed win.
- facts vs no-facts is neutral here (single owned src buffer + one out-borrow,
  no cross-buffer aliasing pressure) — the story is codegen quality + safety,
  not the alias channels.

## Language findings surfaced (fed to notes/pattern doctrine)
1. ANF is verbose for bit-twiddling: base64's `(x >> 18) & 63` becomes two
   bound lets. Expected under D2a (AI pays it), but the encode kernel is ~90
   lines for what C does in ~15 — worth a "the obvious xlang shape is verbose
   here" honesty note when advertising.
2. Whole-function no-shadowing forces globally-unique local names across
   sibling blocks (loop body vs the two tail match arms) — had to suffix each
   arm's locals (p*, q*). Mechanical for an AI writer; a human would chafe.
3. Implemented this session to make it compile: `&uniq buffer<u8>` /
   `&buffer<u8>` params (lowered as {ptr,i64} by value — element writes go
   through the shared data pointer, caller-visible; exclusivity stays a
   checker fact). This is the out-buffer idiom for codecs.

## Caveats / next
- Encode only; decode (with input validation — the CVE-relevant direction)
  is the natural follow-up and a stronger safety story.
- Driver slurps; a streaming/chunked driver would confirm the warm numbers.
- The table lookup is scalar; SIMD base64 (which BSD approximates) is a
  blessed-pattern opportunity, not attempted.

## Elision-ceiling experiment (2026-07-10)

`--elide-bounds-experiment` (perfect-prover upper bound; experiment-only
flag, never a shipping mode): encode kernel 2.44 -> 4.2 GB/s (**1.7x**),
hot-loop branches 41 -> 9, outputs byte-identical to system base64 on random
data. Still ZERO auto-vectorization even fully elided — the SIMD base64
algorithm (wide tables + tbl shuffles) is not vectorizer-discoverable, so
elision's honest value here is scalar: shorter dependency chains, no
side-exits. Checks in this kernel divide into two provable classes:
(a) loop-guard-dominated source reads (`rem >= 3` implies i, i+1, i+2 < n) —
a structural prover covers these; (b) output writes bounded by a CALLER
guarantee (out capacity >= 4*ceil(n/3)) — needs a precondition surface;
LLVM cannot know it and the checker can. Design card: gates 2026-07-10.

## PROOF-1 local discharge (2026-07-10)

The shipping facts path now reports every lowered bounds site in `encode`:

- 27 total sites;
- 15 proved locally: 6 source reads from the fixed-stride remainder invariant
  and 9 alphabet reads from masked ranges propagated through unsigned widening;
- 12 retained: every remaining site is an output write whose safety depends on
  the caller-provided capacity.

Five-sample medians on the same 384MB encode-only harness:

| variant | throughput | time/pass |
|---|---:|---:|
| no facts | 2.50 GB/s | 153.9 ms |
| PROOF-1 local facts | **2.93 GB/s** | **131.2 ms** |
| perfect-prover ceiling | 4.23 GB/s | 90.9 ms |

Local proof discharge is a 1.17x throughput gain and recovers about 36% of the
removable time measured by the ceiling. Optimized `encode` shrinks from 127 to
110 instructions (ceiling: 66). The 9 alphabet checks were already removed by
LLVM, so the measured gain comes from the 6 structurally proved source reads.
Output correctness is unchanged: facts vs no-facts and facts vs system base64
both passed 139/139 boundary-biased random cases. The remaining performance
gap is now cleanly a PROOF-2 question: establish
`len(out) >= 4 * ceil(len(src)/3)` at the call boundary and connect it to the
lockstep `i=3k, o=4k` loop invariant.

Reproduce with `python3 proof_benchmark.py [BYTES] [SAMPLES]`; it rebuilds all
three variants in a temporary directory before measuring them.

## PROOF-2 checked capacity + lockstep discharge (2026-07-11)

`encode` now carries one checked callee-entry `requires` clause spelling the
overflow-safe relation `len(src) <= 3 * floor(len(out)/4)`. The check remains
in every build and direct C entry cannot bypass it. The deterministic prover
then connects that passed fact to the exact loop induction `i = 3k, o = 4k`
and the mutually exclusive one-/two-byte tail arms.

Structured accounting on the unchanged 27 lowered index sites is now:

- 27 proved, 0 retained;
- 6 source reads and 9 alphabet reads from PROOF-1;
- 12 output writes from `output-capacity-lockstep`;
- facts-off retains all 27 sites while executing the identical entry check.

Five-sample medians on the 384MB encode-only harness:

| variant | throughput | time/pass |
|---|---:|---:|
| no facts (entry check + all index checks) | 2.480 GB/s | 154.9 ms |
| PROOF-2 | **4.233 GB/s** | **90.7 ms** |
| perfect index-elision ceiling (entry check retained) | 4.215 GB/s | 91.1 ms |

PROOF-2 is 1.71x over the same-source facts-off control and reaches the
measurement-noise envelope of the perfect-prover ceiling: both optimized
`encode` bodies contain 77 instructions and one retained trap path. Correctness
remains pinned by 139/139 deterministic boundary-biased facts/nofacts/Python
reference differentials. A separate direct-C ABI probe confirms exact capacity
succeeds and one-byte-under capacity traps at the callee boundary before the
first body byte store (`verify.py`).

## Post-PROOF-1/2 ladder (2026-07-11, 384MB, byte-identical outputs)

| implementation | time |
|---|---:|
| **xlang, proofs active** | **0.16s** |
| BSD base64 (Apple, wide-table) | 0.21s |
| GNU base64 | 0.36s |
| uutils base64 (Rust) | 0.36s |

Kernel: 4.05-4.12 GB/s with proofs vs 2.45-2.48 no-facts control (1.66x) —
97% of the perfect-prover ceiling (4.2), with full trap-on-violation
semantics and the boundary check intact. History: pre-proof checked build
was 0.23s and LOST to BSD's 0.20; the proof tier flipped the ladder — now
1.3x ahead of BSD, 2.25x ahead of GNU and the Rust rewrite.

## Pre-registered adversary: Rust assert-up-front (2026-07-11)

Four Rust variants, same 384MB, same machine (kernel GB/s):
| variant | GB/s |
|---|---:|
| rust naive indexed | 2.52 |
| rust assert-up-front (the requires-equivalent) | **2.51 — recovers NOTHING** |
| rust idiomatic chunks_exact/zip (expert shape) | 4.29 |
| rust unsafe get_unchecked ceiling | 4.29 |
| xlang obvious shape + requires (for reference) | 4.09 |

Verdicts: (1) The assert idiom is REFUTED as a recovery path — LLVM cannot
connect the hoisted capacity assert to the coupled-counter bounds checks; the
elision is genuinely checker-attributable, not heuristic-recoverable.
(2) BUT expert Rust reaches the ceiling by RESTRUCTURING: chunks_exact/zip
makes the checks structurally nonexistent (base64's fixed 3:4 shape is
exactly iterator-friendly). Base64 therefore does NOT clear D9's strict
"beats best-effort safe Rust" bar; the honest claim is distributional:
xlang's obvious indexed shape + a one-line checked contract = 4.09; Rust's
obvious indexed shape = 2.5 with NO local annotation fix — the writer must
know the iterator rewrite. (3) Residual 4.29 vs 4.09 (~5%) is loop-shape
quality, worth a look. (4) CONSEQUENCE: the decisive leg-B test moves to the
class where iterator restructuring CANNOT sidestep checks — variable-size
writes (QOI decode, the chosen decoder experiment).
