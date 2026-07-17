# M8 memchr dry run — results

INDICATIVE (Apple M4, macOS arm64, NEON). Deploy target is Linux x86-64; these
validate SHAPE, not deploy-target magnitudes. cc = `/usr/bin/cc` (Apple clang 21),
NOT the wasi clang in PATH. rustc/cargo 1.91.1. Reference: the `memchr` crate,
`memchr::memchr` — the caret requirement `2.7` resolved to **2.8.3** (the current
2.x; same SIMD memchr mechanism). Sources: `cmemchr.c`, `cmemchr.h`, `m8bench/`.

## The question

The catalog (`CATALOG-V1-RECUT.md`) places bytescan/hash kernels (memchr, memmem,
utf8-validate) as CHECKED LIBRARIES over the machine-core SIMD primitive, NOT as
sealed parts. That holds only if the DOM-1 bounds facts (Delta 4, review-clean)
discharge every main-loop bounds check — so a fully-checked SIMD memchr emits the
SAME inner loop as an unchecked one and reaches memchr-crate par. If not, memchr
must become a sealed kernel. This dry run tests exactly that.

## Implementations (`cmemchr.c`)

Both written to the memchr-crate mechanism: 64 bytes/step (4x16 NEON unroll with a
combined OR-reduce, one `umaxv`+`fmov` per 64B), then a 16B stride, then scalar
tail.
- **(a) unchecked** — raw pointer loads, no per-access bound (the reference shape).
- **(b) bounds-modeled** — every load preceded by the exact DOM-1 non-wrapping
  window predicate `len >= 64 AND i <= len - 64` (which dominates all four 16B
  loads), written loop-invariant so the optimizer can discharge it. Models the
  checked language AFTER DOM-1.
- **(b-naive), diagnostic** — the same per-16B-access bound made opaque
  (`volatile len`) so the optimizer CANNOT fold it; models a check DOM-1 did NOT
  discharge. Quantifies what a surviving bounds branch costs.

## Result 1 (load-bearing): inner-loop ASM identity

Compiled `-O3 -mcpu=native -std=c11`; disassembled with `otool -tvV`. Stripping
addresses and branch offsets, **(a) and (b) are IDENTICAL — 86 instructions each,
zero diff.** The modeled DOM-1 bound produces ZERO residual instructions; no
compare, no branch, no register survives per step. The shared hot loop:

```
ldp   q1, q2, [x10]        ; two 16B loads (pair)
cmeq.16b v4, v1, v0        ; compare x4
cmeq.16b v3, v2, v0
ldp   q1, q5, [x10, #0x20]
cmeq.16b v2, v1, v0
cmeq.16b v1, v5, v0
orr.16b v5, v3, v4         ; OR-reduce the four
orr.16b v6, v2, v1
orr.16b v5, v5, v6
umaxv.16b b5, v5           ; ONE horizontal reduce per 64B
fmov  w10, s5
cbnz  w10, <hit>
add   x8, x8, #0x40        ; i += 64
cmp   x8, x9               ; i vs (len-64)
b.ls  <loop>
```

The diagnostic (b-naive) is NOT identical: the non-discharged check adds, per 64B
step, a stack reload of `len`, subtract, compare, and `b.hi` to a `brk` trap
(plus a prologue stack spill) — the cost DOM-1 removes.

## Result 2: parity vs memchr crate (median of 21 runs, 3 warmup, ns/call)

Bands: bulk a/rust and b/rust in [0.85, 1.15]; b/a <= 1.05; short-input <= 2.0x.
Representative run (stable across three repeats):

| case | rust | (a) | (b) | a/rust | b/rust | b/a | naive/a |
|---|---:|---:|---:|---:|---:|---:|---:|
| 16KB not-present | 143.0 | 141.1 | 143.4 | 0.99x | 1.00x | 1.02x | 1.83x |
| 16KB needle@25%  |  36.4 |  36.4 |  36.4 | 1.00x | 1.00x | 1.00x | 1.68x |
| 1MB  not-present | 9248  | 9198  | 8640  | 0.99x | 0.93x | 0.94x | 1.74x |
| 1MB  needle@25%  | 2314  | 2332  | 2326  | 1.01x | 1.01x | 1.00x | 1.74x |
| 16B  not-present |  1.20 |  1.41 |  1.41 | 1.18x | 1.18x | 1.00x | 1.02x |
| 16B  needle@25%  |  0.57 |  1.21 |  1.21 | 2.12x | 2.11x | 1.00x | 1.00x |

- **Bulk (16KB, 1MB): PASS.** All a/rust and b/rust in [0.93, 1.01] — the checked
  and unchecked versions both reach memchr-crate par. b/a in [0.94, 1.02],
  within 1.05.
- **Short input: 16B not-present PASSES (1.18x); 16B needle@25% marginally OVER
  at ~2.13x** (stable across runs). This is a ~0.64 ns absolute gap from
  memchr-crate's specialized tiny-input path (finding an early byte with less
  work than the general 16B-stride + `shrn`/`fmov`/`ctz` extract); it is the
  noisiest regime and non-load-bearing for the catalog decision. Critically,
  b/a ≈ 1.00 in both short cases — the CHECK is free even here; the miss is the
  reference's small-input path, not checking.
- **Diagnostic:** a non-discharged bounds check costs ~1.7-1.87x on bulk
  (naive/a), quantifying what DOM-1 saves.

## Result 3: correctness

Differential over 1,000,000 random cases (len 0..=4096, random content and
needle, so the needle is present or absent at random positions): rust / (a) / (b)
/ (b-naive) — **zero divergence**.

## Catalog consequence

**memchr STAYS a checked library — confirmed.** DOM-1's len-check domination
(Delta 4, review-clean) discharges every main-loop bounds check: the checked
memchr compiles to the byte-identical inner loop as the unchecked reference and
reaches memchr-crate par on bulk. No sealed kernel is warranted. This validates
the catalog's placement of bytescan/hash kernels as checked libraries over the
machine-core SIMD primitive.

Honest scope: this exercises the len-check-domination case (DOM-1(b)) — the
loop's window fact IS the access bound, the "measured easy case" the catalog
names. It does NOT test the harder variable-offset / F3-class facts (SQLite cell
walks, TLV) that the catalog gates separately; memchr is squarely the discharged
easy case. The discharge works because the predicate is loop-invariant and tied
to the loop bound over a fixed-length slice — exactly DOM-1(b)'s formation
condition (a live length fact on a non-resizable backing), which memchr satisfies.
