# zlib core-kernel results

Date: 2026-07-19. Host: Apple M4, Mac16,12. Compiler: Apple Clang 21.0.0,
`-O3`, ARMv8-A plus SIMD. Reference: zlib-ng 2.3.3 commit
`12731092979c6d07f42da27da673a9f6c7b13586`.

## Result

The current default Whitefoot shape is not generally competitive with
zlib-ng's optimized inflate kernels. It is competitive for non-overlapping
copy distances that LLVM can vectorize, but DEFLATE's important short-distance
overlap cases remain scalar and are much slower. The prepared Huffman literal
loop also trails the source-order-exact all-literal projection of zlib-ng's
three-literal fast path.

Facts-on and facts-off produce byte-identical Apple-Clang `-O3` kernel objects
for both kernels. In democ IR, match copy differs only in effect attributes;
Huffman facts also discharge the masked 512-entry constant-table bound, which
Clang independently proves in the no-facts build. The timings therefore show
no native performance payoff from facts on this toolchain for these shapes.

## Length/distance overlap copy

Each sample expands approximately 32 MiB four times in one process. There are
nine balanced-order samples per variant and case. All 14 correctness cases
pass for facts-on, facts-off, and zlib-ng. Ten accepted/trapping contract
boundaries also pass in child processes for both Whitefoot builds. Values are
medians in GiB/s.

| Distance | Length | Whitefoot facts | Whitefoot no facts | zlib-ng | WF / zlib-ng |
|---:|---:|---:|---:|---:|---:|
| 1 | 3 | 1.921 | 2.039 | 0.944 | 2.034 |
| 1 | 258 | 1.959 | 2.014 | 33.223 | 0.059 |
| 2 | 258 | 0.889 | 0.890 | 29.187 | 0.030 |
| 3 | 8 | 1.255 | 1.257 | 1.625 | 0.772 |
| 3 | 258 | 1.248 | 1.244 | 26.603 | 0.047 |
| 4 | 258 | 1.593 | 1.590 | 26.326 | 0.061 |
| 8 | 32 | 2.422 | 2.426 | 8.236 | 0.294 |
| 8 | 258 | 2.336 | 2.337 | 26.091 | 0.090 |
| 16 | 258 | 2.346 | 2.350 | 7.565 | 0.310 |
| 31 | 64 | 2.340 | 2.321 | 6.714 | 0.348 |
| 31 | 258 | 2.264 | 2.268 | 7.442 | 0.304 |
| 64 | 258 | 20.113 | 20.871 | 15.682 | 1.283 |
| 257 | 258 | 32.947 | 29.875 | 30.522 | 1.079 |
| 32768 | 258 | 33.264 | 33.853 | 29.757 | 1.118 |

The distance-one, length-three win is a narrow helper-setup effect: three
scalar bytes are cheaper than preparing zlib-ng's wide repeated-byte path.
It does not survive at long match lengths. At length 258 and distances 1-8,
Whitefoot reaches only 3.0% to 9.0% of zlib-ng. At distance 64 and above,
LLVM recognizes a non-overlapping copy and Whitefoot reaches 1.08x to 1.28x
zlib-ng in this isolated kernel.

## Prepared Huffman literal decode

Each sample decodes 33,554,430 literal symbols four times; the count is
divisible by three. There are twelve balanced-order samples per variant. The
input is a deterministic uniform byte sequence encoded with the RFC 1951 fixed
literal alphabet. The runner verifies every embedded packed entry against
zlib-ng's pinned `lenfix` table before compiling, and both implementations
produce the same output. Six accepted/trapping contract boundaries pass in
child processes for both Whitefoot builds.

| Variant | Median M symbols/s | Relative to zlib-ng |
|---|---:|---:|
| Whitefoot facts | 313.100 | 0.822 |
| Whitefoot no facts | 318.516 | 0.836 |
| zlib-ng `inffast` all-literal projection | 380.850 | 1.000 |

This isolates table lookup and bit consumption; it does not include dynamic
table construction, match copying, block transitions, checksum, or stream
bookkeeping. The gap is therefore evidence about the default hot-loop shape,
not a whole-decoder throughput claim.

## Diagnosis and conclusion

The broad claim that the current default source shape already lowers to an
optimal machine shape is false for these kernels. The result does not rule out
one canonical source spelling as a design goal; it shows that the compiler
must lower that spelling into multiple proof-selected machine strategies
rather than lower it literally.

For short-distance match overlap, Whitefoot retains a dependent byte
load/store loop with two bounds branches per byte. zlib-ng instead treats the
same recurrence as periodic expansion: distance one becomes a repeated-byte
fill, distances two/four/eight become vector broadcasts, and other short
periods use vector permutation followed by chunk stores. Removing bounds
checks alone would not invent that algorithm. The reversal at distance 64 is
the control: LLVM then proves enough separation, emits a 64-byte vector loop,
and Whitefoot meets or beats the pinned helper. General safe-buffer overhead is
therefore not the fundamental cause of the short-distance loss.

For Huffman literals, Whitefoot refills by bytes and decodes one symbol per
outer iteration. The zlib-ng projection performs one 64-bit refill and three
literal decodes, amortizing refill, cursor, and loop control. Whitefoot also
retains per-symbol input/output bounds checks and a checked value conversion.
The shared verified 512-entry table is not the cause of the gap.

The exact contracts do not currently become the nested-loop invariants needed
to remove those checks. Facts-on and facts-off native objects are identical,
and existing alias/effect facts cannot synthesize periodic expansion or burst
decoding. The missing capability is therefore closed compiler recognition of
periodic overlap and guarded bulk decode regions with a verified tail, not a
general prover or writer-maintained distance matrix. Until those consumers
exist, the claimed
default performance floor is not supported for this workload class.

## Scope

The result contradicts a broad claim that the current default Whitefoot shape
is already optimal or automatically competitive with these pinned optimized
zlib-ng paths. It does not establish whole-zlib performance, and it does not
say that Whitefoot cannot reach the optimized shapes after compiler work. The
next useful test is a mixed literal/match `inflate_fast` replay using token
frequencies captured from real compressed corpora; these two kernels already
identify the mechanisms that such a replay must preserve.

Raw SHA-256: match-copy
`eee80b5c19fface86213eba7cb7ee68828b994102cbb2273f1bd91458986bd25`;
Huffman
`ce49c0d5e87ee7f445221b19693201e2d9427321381fbf4d5ed29ca26ab5c169`.
