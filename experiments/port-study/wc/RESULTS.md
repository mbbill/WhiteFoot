# wc port (safe-direction pilot #1)

Status: MEASURED 2026-07-10. First swap-in-class utility: byte-identical
outputs, C-locale parity fuzz-verified, faster than both incumbent wc
implementations on full counts.

## Correctness
- Byte-identical output vs system wc on real files and a 426MB corpus.
- Fuzz-diff: 45/45 cases identical under LC_ALL=C (staged parity target:
  byte mode first; locale modes later, labeled). One initial mismatch was the
  ORACLE's locale (UTF-8 wc classifies extra bytes as spaces), not the port.

## Performance (426MB, 5.4M lines, warm, medians of 3, Apple M4)
| command | time |
|---|---:|
| xwc full counts (xlang kernel + C driver) | **0.28s** |
| GNU wc (gwc, LC_ALL=C) | 0.48s |
| BSD wc (macOS, LC_ALL=C) | 0.54s |
| xwc -l | 0.10s |
| gwc -l | **0.05s** |
| BSD wc -l | 0.33s |

- Full counts (the default invocation): xlang 1.7x faster than GNU, 1.9x
  faster than BSD.
- -l honest gap: GNU's memchr path is hand-tuned platform SIMD and beats our
  autovectorized naive loop 2x. Ours is the NAIVE source shape; closing this
  needs a dedicated scan shape or a memchr-class blessed pattern. BSD is 3.3x
  behind us.
- facts-vs-nofacts: neutral on this kernel (single own buffer, no aliasing
  pressure — LLVM already sees everything; the channels are not the story
  here, scalar/vector codegen quality is).

## The totality-economics lesson (owner's flag, vindicated with data)
First version used iadd.trap for counters: ZERO vector ops emitted — the
per-increment overflow side-exit blocked vectorization entirely. Counters are
bounded by buffer length, so .wrap is semantically safe: switching unlocked
SIMD byte-compare (24 vector ops) and took -l from 0.20s to 0.10s and full
counts from 0.37s to 0.28s. This is the concrete case for (a) the
totality/trap lint tier and (b) proof-driven check elision (gates 2026-07-10
entry): one avoidable trap in a leaf halves throughput.

## Caveats / next
- Driver slurps the whole file; incumbents stream in chunks. Warm-cache
  comparison is fair-ish but a chunked driver variant should confirm.
- Formatting parity verified on these cases; full flag matrix (-c/-m/-w/-l
  combinations, multiple-file totals, stdin) needs the systematic diff pass.
- Next utility: base64 (pulls const-array codegen, the top gap).
