# M3 kernel-shape parity dry run — results

INDICATIVE numbers (Apple M4, macOS arm64, NEON). Deploy target is Linux x86-64;
these validate SHAPE, not deploy-target magnitudes.

## Method
- Kernels in C (optables.md S.1 seq, S.2 table), built with `/usr/bin/cc -O3
  -mcpu=native -flto -std=c11` (system Apple clang, NOT the wasi clang in PATH).
- Baselines: Rust `Vec` (B1) and `hashbrown 0.17.1` + `foldhash 0.2` default
  hasher (B2-B4), `cargo --release`, lto=fat, codegen-units=1, target-cpu=native.
- Separate binaries, internal timing (`CLOCK_MONOTONIC` / `Instant`), warmup 3 +
  21 measured runs -> per-run median; then 15 outer runs interleaving C and Rust
  to share thermal state -> median-of-medians (drive.py). Identical splitmix64
  key streams and seeds in C and Rust. 1,000,000 u64 keys/values (value = key).

## Ratios (C kernel / Rust baseline; band: <= 1.25x = shape validated)
| benchmark              | C (ns) | Rust (ns) | ratio  | band |
|------------------------|-------:|----------:|-------:|------|
| B1 push-then-sum       |  1.17  |   1.74    | 0.67x  | OK   |
| B2 build (1M insert)   | 17.57  |  14.84    | 1.18x  | OK   |
| B2 hit-lookup          |  6.02  |   5.63    | 1.07x  | OK   |
| B3 miss-lookup         |  2.03  |   1.61    | 1.26x  | edge |
| B4 iterate-sum         |  1.45  |   2.04    | 0.71x  | OK   |

B3-miss straddles the band (observed 1.22-1.28x across runs). Diagnostic:
reserved-insert (no rehash) is ~1.40x (ctable 5.5 / hashbrown 4.0) — steady-state
insert is compute-bound-slower than hashbrown's tuned path; the B2 grow-build is
1.18x because the shared rehash cost dominates and the group-scan rehash is
competitive.

## Correctness (differential vs std HashMap oracle, via FFI)
3 seeds x 1,000,000 mixed ops (insert/remove/get, key domain 200k), comparing
every return value + length after every op + a full-domain final scan.
Result: DIFFERENTIAL OK on all 3 seeds — zero divergence. Exercises rehash
(in-place purge and 2x grow), tombstone remove, and tombstone reuse.

## Probe-shape asm confirmation (CG-PROBE)
`ctable_get` inner group step (otool):
    ldr   q2, [x8, x11]     ; ONE 16-byte control load
    cmeq.16b v3, v2, v0     ; H2 broadcast compare
    shrn.8b  v3, v3, #0x4   ; \
    fmov  x12, d3           ;  } mask extract (4-bit stride)
    ands  x12, x12, #0x8888888888888888
    cmeq.16b v2, v2, v1     ; empty compare REUSES the same loaded v2 (no 2nd load)
One 16B load + compare(s) + mask per group step, exactly as pinned.

## Catalog / shape findings (deviations needed to reach the band)
1. **K/V physical layout is unspecified in S.2 and it matters (AoS required).**
   S.2 pins the control-byte/probe shape but says nothing about how K and V are
   stored. A struct-of-arrays layout (separate key[] and value[] arrays) doubles
   insert cache misses (two distant lines per insert) and measured **2.0x** vs
   hashbrown on steady-state insert. Switching to array-of-structs `(key,val)`
   pairs — matching hashbrown's `Bucket<(K,V)>` — closed it. RECOMMEND the
   catalog pin the AoS `(K,V)` slot layout (or explicitly leave it to codegen
   with AoS as the parity target). Not a cheat; a genuine gap.
2. **CG-PUSH parity needs the guaranteed-inline lowering.** The (ptr,len,cap)
   push hits Vec parity (0.67x here) only when the receiver fields are register-
   promoted across the hot loop. A naive separate-TU C build with an out-of-line
   `grow` leaves `&s` address-taken, so every push reloads len/cap/ptr from
   memory -> 1.6x. LTO (which inlines grow, as the mandated guaranteed-inline
   CG-PUSH does) recovers parity. cseq was therefore benchmarked with -flto to
   represent the catalog's mandated inline shape.
3. **CG-PROBE must fuse the group load.** Writing `match_h2`/`match_empty` as
   separate helpers that each `vld1q` the group violates "one 16B load per group"
   and was measured slower; the code now loads the group once per step and derives
   all masks from that vector (confirmed in asm).
4. **CG-ITER wants a group-scan, not a per-bucket branch.** Iterating with an
   `if (ctrl[i] full)` branch per bucket is ~2x (unpredictable branch at load
   factor); group-scanning control bytes (16 at a time, vectorized) gets 0.71x
   and beats hashbrown's iterator.
