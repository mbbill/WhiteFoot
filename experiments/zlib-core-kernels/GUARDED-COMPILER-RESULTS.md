# Experimental guarded bit-window compiler result

Date: 2026-07-19. Host: Apple M4, Mac16,12. Compiler: Apple Clang
21.0.0 at `-O3`. Reference: zlib-ng 2.3.3 commit
`12731092979c6d07f42da27da673a9f6c7b13586`.

## Result

An explicit stage-0 compiler experiment closes the fixed-Huffman literal gap
without changing the Whitefoot source. The guarded lowering is 1.309x the
ordinary stage-0 lowering and 1.088x the pinned zlib-ng all-literal projection
by ratios of the three variant medians.

| Variant | Median M symbols/s | Relative to guarded |
|---|---:|---:|
| Ordinary stage-0 lowering | 345.644 | 0.764 |
| Guarded bit-window lowering | 452.485 | 1.000 |
| zlib-ng all-literal projection | 415.729 | 0.919 |

Each of twelve balanced samples decodes 33,554,430 symbols four times. The
paired median guarded/ordinary ratio is 1.319 with a deterministic paired
bootstrap 95% interval of [1.309, 1.326]. The paired median guarded/zlib-ng
ratio is 1.094 with interval [1.074, 1.105]. The intervals use 200,000 median
resamples with seed 20260719; they describe run-to-run sampling uncertainty on
this host, not portability to another machine.

The guarded object has 2,640 text bytes versus 2,404 for the ordinary object,
an increase of 236 bytes or 9.8%, including the common 2 KiB decode table.

## What the experiment implements

`prototype/democ/democ.py` accepts
`--experimental-guarded-bit-window`. Normal compilation does not run the
experimental path. After the ordinary parser and checker accept the program,
the flag:

1. alpha-normalizes the checked function AST;
2. requires one closed structural digest;
3. certifies a 512-entry packed table, 1..9-bit progress on literal entries,
   and literal values representable as `u8`;
4. proves that a seven-bit initial offset plus six nine-bit lookups needs at
   most 61 bits of a 64-bit window;
5. emits a local input/output capacity guard, one 64-bit lookahead load, and
   six source-ordered literal decodes; and
6. enters a two-byte checked scalar tail for the remaining zero to five
   symbols or whenever fewer than eight input bytes remain.

The internal state is a `(byte_cursor, bit_offset)` pair, rather than an
absolute bit count, so the accepted `u64` contract domain does not introduce a
hidden `9 * symbol_count` overflow. LLVM combines the eight target-independent
byte loads into one unaligned ARM64 `ldr`; the scalar tail becomes one `ldrh`.

This certificate is a feasibility mechanism, not a general bit-accumulator
recurrence analyzer. The single alpha-normalized digest ignores identifier,
label, region, documentation, and diagnostic spelling, but it intentionally
rejects any operation, control, contract, place, type, or constant drift. A
production transform would replace the digest with explicit recurrence and
proof-obligation analysis.

## Correctness and hostile boundaries

The experiment preserves the exact source file:

```text
huffman_literals.wf SHA-256
de44aca1c03a889834a56f15138c4ebb924feaedabece766633f45fd73974847
```

The following pass for both ordinary and guarded compiler outputs:

- the original six accepted/trapping contract cases;
- exact logical source lengths for a twelve-symbol bulk case and a
  thirteen-symbol bulk-plus-tail case;
- those two exact-length cases placed immediately before a protected guard
  page, so any wide over-read faults;
- shared-memory child tests with a nonliteral in the middle of the six-symbol
  block and in the scalar tail, checking that only the preceding literal
  prefix was written before the trap; and
- 27 successful counts spanning every tail remainder and several fast-loop
  boundaries from 1 through 257 symbols.

Seven compiler tests additionally pin explicit flag selection, unchanged
source identity, alpha-renaming acceptance, and fail-closed rejection of mask,
refill-threshold, zero-progress table entry, and out-of-range literal changes.
The runner rechecks all 512 source table entries against the pinned zlib-ng
table before compilation.

## Scope

This is an experimental path in the disposable Python stage-0 compiler,
`democ`. It is not implemented in production `wfc`, is not a specification or
pattern-doctrine change, and does not integrate with the canonical proof report.
The flag rejects proof-report mode rather than assigning unearned provenance.

The measured function accepts only literal table entries and traps on every
nonliteral. Prefix-preserving trap tests establish that behavior for the bulk
and tail paths, but they do not establish correct length/distance dispatch,
block transitions, dynamic tables, or complete decoder behavior. In
particular, beating the all-literal projection is not a whole-inflate result.

The result isolates the earlier gap: the source shape was sufficient, but its
literal one-symbol/byte-refill lowering was not. A proof-guarded six-symbol
word window closes that isolated gap on this target. Production still requires
a finite explicit recurrence verifier and a mixed literal/match replay; it does
not require a general loop prover.

Raw measurements SHA-256:
`a87a9229548849fba55787c0d6f3270e799819dc050121b6724fe94418fd7925`.
