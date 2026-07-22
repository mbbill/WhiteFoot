# Raw DEFLATE default-shape protocol

Status: **DRAFT — generation forbidden**.

This protocol becomes preregistered only after every implementation, corpus,
prompt, tool, source-tree, and artifact identity below is concrete, all harness
tests pass, the repository gates pass, and the freeze is committed. No model
output may be requested before that commit. Any incomplete identity keeps
generation forbidden.

## Question

The primary question is whether one fixed model's first correctness-green
Whitefoot implementation of a complete one-shot raw RFC 1951 decoder reaches
the performance class of a strong optimized ordinary zlib-family
implementation on a frozen bulk-decode workload: zlib-ng 2.3.3 decoding twelve
large Silesia members independently compressed by stock zlib 1.3.2 at level 6
with the default strategy.

The primary statistic is:

```text
throughput(frozen Whitefoot facts-on) / throughput(zlib-ng 2.3.3 public raw inflate)
```

The facts-off build uses the identical frozen Whitefoot bytes and is an
attribution control. It is not another candidate. There is no hand-written,
expert, tuned, or post-profile Whitefoot arm.

This is an exploratory stage-0 result. It does not claim production-`wfc`
readiness, general Whitefoot performance, or an extension of the completed D9
series. Its performance conclusion is limited to this bulk raw-inflate
workload; it does not cover small streams, other encoders or levels, or other
block distributions.

## Frozen behavior

The required public declarations are a two-word result record and one
function:

```text
struct InflateResult {
  status: u64;
  produced: u64;
}

fn inflate_raw ['s, 'o, 'r] (src: &'s buffer<u8>, out: &uniq 'o buffer<u8>, result: &uniq 'r InflateResult, work8: own buffer<u8>, work16: own buffer<u16>, work32: own buffer<u32>) -> own unit EFFECTS {
  ...
}
```

`EFFECTS` is not literal source. The candidate must write a sound row. The row
must read `'s`, write exactly `'o` and `'r`, include `traps`, and exclude
allocation. It may conservatively also declare reads of `'o` and/or `'r`. No
function in the file may allocate. This leaves output-history and
separate-history designs both available without pretending that current
stage-0 checks effect-row minimality beyond `traps`. `inflate_raw` may not add a
`requires` block because this protocol defines its complete callable domain;
the writer may establish a supplied length guarantee with an ordinary edge
check in the body. Helpers may use real internal caller obligations.

The evaluator supplies mutually disjoint buffers with these exact visible
lengths:

- `work8`: 65,536 `u8` elements;
- `work16`: 4,096 `u16` elements;
- `work32`: 4,096 `u32` elements.

Their initial contents are unspecified. Ownership transfers for one call. The
candidate may use or ignore them. Scratch preparation is outside later timing;
all decoder work performed by the candidate, including scratch initialization
and table construction, is inside timing. The sizes are a conservative fixed
resource envelope derived from the format's 32 KiB history and bounded RFC
alphabets. They were not selected from candidate, comparator, profile, or
timing evidence and do not prescribe a table layout.

Status values are:

- `0_u64`: `Done`;
- `1_u64`: `NeedOutput`;
- `2_u64`: `Malformed`.

Every normal return overwrites both result fields. Any other status is wrong.
Input and output lengths are nonnegative and at most `2^31 - 1`.

`Done` means that a final RFC 1951 block ended. Unused high bits in its final
byte and trailing whole input bytes are ignored. `produced` is the complete
decoded length; `out[0..produced]` is exact; the remaining visible output is
unchanged.

`NeedOutput` is used only for otherwise-valid input. Stored bytes and literals
are one-byte output units; a length-distance match is one indivisible unit. If
the next unit does not fit, the function returns before writing any part of
that unit. `produced` ends on the preceding unit boundary, the exact output
prefix is present, and the remaining visible output is unchanged. This is a
restart-from-input operation, not a continuation API.

`Malformed` covers truncated input and every RFC 1951 violation. It must return
normally rather than trap. `produced` must name a complete output-unit boundary
no later than the independent oracle's longest valid prefix, the written prefix
must equal the oracle prefix, and the remaining visible output must be
unchanged. This permits eager or progressive validation without standardizing
an incumbent's error-detection order.

All calls preserve the input bytes and every guard surrounding input, output,
result, and scratch. An implicit bounds trap, explicit trap, signal, timeout,
or non-return on any in-contract case is a correctness failure.

The decoder supports all RFC 1951 stored, fixed-Huffman, and dynamic-Huffman
blocks; arbitrary block sequences; all legal literals, lengths, and distances;
the full 32 KiB history; and overlapping matches. It excludes zlib and gzip
wrappers, checksums, preset dictionaries, concatenated-stream decoding, and
resumable continuation.

## Model and information boundary

The single trajectory uses:

- Codex CLI `0.144.5` through
  `/opt/homebrew/lib/node_modules/@openai/codex/bin/codex.js`, SHA-256
  `134063e133f0b4244fa3b251acf973d4fe4b4aeeacbdc135211bf480f59f1477`;
- its arm64 native executable, SHA-256
  `5e29ab10ca1171be158f7335dd6bd8ce1aaf9af1556939db36a5ee338be6f5f2`;
- Node `25.9.0`, SHA-256
  `32e234a5b6bec67d72a016f2baadf7fadf3afd328470b395b73af473fdee0d85`;
- model: `gpt-5.6-terra`;
- reasoning effort: `medium`;
- service tier: `default`;
- round zero plus at most three sequential compile/correctness repairs;
- no restart, sampling pool, best-of-N, alternate model, human source edit, or
  unused repair after the first green result.

The unchanged generic runner is `../default-floor/generate.py`; the unchanged
model boundary is `../default-floor/codex_model_adapter.py`. Each invocation is
ephemeral, read-only, and runs in a new empty directory with user configuration
and repository rules ignored. Exactly one agent message and no tool event is
accepted.

The prompt is the literal bytes of `task.md`, the writer-pack separator, the
literal bytes of `teaching-pack.md`, the pattern-doctrine separator and neutral
syntax-precedence sentence, then the literal bytes of the repository's complete
`PATTERNS.md`. The precedence sentence says that the doctrine is architecture
guidance and only forms admitted by the preceding stage-0 pack are available.
Frozen identities:

- `task.md`:
  `cf241974c39ecb2bbb1311f43b4cd0c7f5b71f2f032f60b433f76986432083c7`;
- `teaching-pack.md`:
  `466325804fd934665e41e2d9552bb1941f22ff542fb401f614d1879b1ea9cd98`;
- `PATTERNS.md`:
  `69213a146c84911f0675ca11f9be70c7515ea74a4a2d15788a2ce280550e51f4`;
- `base-prompt.txt` (29,569 bytes):
  `87d66cbad65b3643228541e0cc19f77ef8ca1b463ef25ed144352475a1aef6d6`.

The model receives the behavior contract, the complete task-relevant stage-0
writer surface, and the exact canonical pattern doctrine. Generic optimizer
rationales and historical measurements already present in that doctrine are
intentionally part of default teaching. It never receives or accesses the
comparator identity or source, adapters, protocol, correctness or scoring
corpora, another decoder, candidate proof reports, candidate IR or assembly,
profiles, retained-check counts, task or comparator timings or ratios, or any
task-, candidate-, or comparator-specific implementation or optimization
advice beyond the exact doctrine.

Repairs receive only the preceding candidate and accepted machine feedback.
Compiler feedback contains compiler diagnostics. Correctness feedback contains
an opaque call ordinal, valid/malformed classification, at most 4,096 input
bytes, output capacity, status/prefix metadata, termination, and integrity
flags. Fixture names, fixture kinds, payload descriptions, and native-generator
provenance are withheld. Feedback never contains task-specific comparator,
proof, optimizer, or performance information.

The first candidate passing compilation and the entire facts-on and facts-off
correctness gate freezes immediately, byte-for-byte and by SHA-256. Exhausting
four candidates is the scored `generation failure` outcome.

## Correctness oracle and corpus

`oracle.py` is an independent bit-level RFC 1951 implementation. It does not
call, translate, or reuse zlib or zlib-ng source, decoding tables, or state
machines. `corpus.py` produces one canonical JSON manifest. Before any
candidate evaluation, both pinned zlib 1.3.2 and pinned zlib-ng 2.3.3 must agree
with the oracle on every native-compatible valid fixture at complete and
surplus capacity. Capacity-limited prefixes are oracle-only because the public
native decoders may split a match.

Two oracle-valid fixtures deliberately fall outside that native agreement:
`dynamic-unused-distance-hdist-field-30` and
`dynamic-unused-distance-hdist-field-31` declare 31 and 32 distance lengths,
leave reserved distance symbols unused at length zero, and produce one literal.
RFC 1951 permits both fields, while both pinned native decoders reject them.
Their exact native observations are frozen in the corpus metadata; they remain
valid candidate cases under the independent oracle. This exception prevents an
incumbent's stricter parser from silently narrowing the task.

The frozen correctness corpus contains, in stable manifest order:

1. empty and minimal streams for stored, fixed, and dynamic blocks;
2. every literal byte and final-block endings at every reachable bit offset;
3. length and distance boundary vectors, including lengths 3 and 258,
   distances 1 and 2, `distance == produced`, overlap, and 32 KiB history;
4. stored `LEN` boundaries and mixed multi-block streams;
5. dynamic-tree boundaries for `HLIT`, `HDIST`, `HCLEN`, repeats 16/17/18,
   one-symbol distance trees, and no-distance-use streams;
6. deterministic valid streams generated independently and by pinned stock
   zlib across levels 0, 1, 6, and 9 and applicable strategies;
7. exact and surplus output capacities plus every small capacity and capacities
   immediately around literal, stored-byte, and whole-match boundaries;
8. reserved block types, stored `LEN/NLEN` mismatch, invalid code sets, illegal
   repeats, missing end codes, reserved symbols, impossible distances, and
   truncation at structural boundaries;
9. deterministic flip, insert, delete, duplicate, and truncate mutations,
   classified by the independent oracle.

The corpus seed is `2026071901`. It contains 351 fixtures (153 valid and 198
malformed) and 1,817 capacity calls. Of the valid fixtures, 151 receive 604
full-capacity native cross-check calls; the two RFC-valid native exceptions
receive eight recorded rejection observations. Frozen identities are:

- `oracle.py`:
  `85ac30f6d18d8a154d6c974985b08f904b9d5043fb6f569f9ccb4c8b2b3da3fb`;
- `corpus.py`:
  `528b301a7b82dc2ac76b63d4abc6c3b12f54c891c361e742510c6be9d489d040`;
- `correctness-corpus.json`:
  `e5ab4727c474fe3dfb9d0a83eaf7c9f95252d88d8ef2b0e074fe3e21d2317494`.

Each candidate call runs in a guarded child process. Input is mapped read-only.
Output, result, and scratch begin with distinct deterministic poison. The
parent checks termination, result overwrite, permitted status and prefix,
untouched output suffix, unchanged input, and all guards. Facts-on and
facts-off must produce identical observable results for every case. Each mode
runs once with visible spans adjacent to the left guard and once adjacent to
the right guard, for 7,268 child calls per complete gate. Any individual call
that does not return within 2.0 seconds is a candidate correctness failure.
Candidate source is UTF-8, at most 1,048,576 bytes, and is never rewritten.

## Locked comparator

The comparator is pristine zlib-ng 2.3.3, selected before generation as a
strong ordinary zlib-family implementation rather than asserted to be the
absolute fastest DEFLATE decoder:

- commit: `12731092979c6d07f42da27da673a9f6c7b13586`;
- tree: `baa7e2050b51c3db4c88bc8f2daf93ca0ae88a98`;
- compatibility aliases disabled;
- ARMv8 and NEON implementations enabled;
- optimized implementations and runtime CPU detection enabled;
- native-instruction build specialization disabled;
- ordinary public native API only.

For each input, its adapter uses only the public API and a fresh aligned state:

```text
outside timing: prepare state, set spans, inflateInit2(stream, -15)
inside timing:  inflate(stream, Z_FINISH) exactly once
outside timing: inflateEnd(stream)
```

There is no pre-scan, input copy, internal-symbol call, custom fast path,
chunking, or source modification. Runtime CPU dispatch and all default
architecture implementations remain enabled. The public adapter is compiled at
generic-target `-O3` so wrapper code does not handicap the comparator.

The source checkout, CMake cache, generated header, shared library, and public
adapter are frozen by `scoring-manifest.json`. In particular:

- CMake cache:
  `1f33ac2526160ba43db7d25eccd77d8efe0756e7fe55d380ea86ebfac955ac3c`;
- zlib-ng shared library:
  `5d576fbb399cf51c8297d00f78dc993fe480cd00a7521637fda5dff6d800eec2`;
- generated public header:
  `b21c9e41b294ba4e23d06e1ce9ff1851ac10ba6fba51ce8e8c3f4e9a477c7176`;
- public adapter:
  `71d9ae20d5a0a5c7e29988b99b06a9b80481e9eab8545720cafdc0bf26180169`;
- adapter source:
  `77fe9577c98273fbf3ceb73aba8a0946f60354c8501cc6536cf9af72f31a86d2`;
- adapter helper:
  `d8db1eff66fb4982a0755f4fa2e379f8d70cbd5e59109851a32587e4e88088b4`.

## Scoring corpus

The bulk-decode scoring input is the twelve-file Silesia corpus in canonical
order: `dickens`, `mozilla`, `mr`, `nci`, `ooffice`, `osdb`, `reymont`,
`samba`, `sao`, `webster`, `xml`, `x-ray`. The uncompressed total is
211,938,580 bytes.

Before generation, the source archive hash, every member name/hash/size, and a
canonical corpus manifest are frozen. Each file is independently compressed
outside timing into one raw RFC 1951 stream by pristine stock zlib 1.3.2:

- commit: `da607da739fa6047df13e66a2af6b8bec7c2a498`;
- tree: `79b5a06f88838dd54f90f821e8650254abfedb7e`;
- `deflateInit2(Z_DEFAULT_COMPRESSION, Z_DEFLATED, -15, 8,
  Z_DEFAULT_STRATEGY)`.

Every compressed stream is frozen byte-for-byte and both reference decoders
must reproduce its source member. The official archive is 68,182,744 bytes,
SHA-256
`0626e25f45c0ffb5dc801f13b7c82a3b75743ba07e3a71835a41e3d9f63c77af`.
The twelve raw streams total 68,220,415 bytes. Exact member and stream hashes
and sizes are in `scoring-manifest.json`, SHA-256
`798da6cb825a3765859c44711db2f89b6c01a58e4783a4b0365faa56b318e51a`;
its generator is
`e9a5baa0cd265266002a07665455b5f63d45f7f7a3ff20435280babb42548e19`.
The pinned stock-zlib shared library and adapter hashes are respectively
`e878d444956b94d01dde8a49d75c0252f563762621ea6b9f71dc179d0200f521`
and `1122b2cd4c04223ead53f128f594007b7eeb7d7ce8e30db048cd1248ce35587f`.

The writer receives none of these bytes or descriptions.

## Builds and measurement

zlib-ng uses its ordinary CMake Release configuration with tests off and
compatibility aliases off. ARMv8, NEON, default optimized implementations, and
runtime CPU detection stay enabled; native-only flags, LTO, PGO, source
patches, internal entry points, and post-result flag search are forbidden.

The identical frozen Whitefoot source is compiled by the frozen stage-0
compiler in facts-on and facts-off modes, then by the frozen system Clang at
`-O3` with the generic/default CPU target. Native CPU flags, LTO, PGO, source
patches, alternate features, and post-result flag search are forbidden.

For every stream, Whitefoot timing begins immediately before `inflate_raw` and
ends immediately after return. Comparator timing begins immediately before its
prepared public `inflate(Z_FINISH)` call and ends immediately after that call;
fresh-state preparation, `inflateInit2(-15)`, and `inflateEnd` are outside.
Corpus loading, allocation, page touching, scratch/state poisoning, guard
setup, and output verification are outside timing. All variants receive
identical input bytes, alignment, and exact decompressed-size output capacity.
Any allocation or initialization performed inside candidate source remains
timed. Workers perform no decoder warmup for any variant; executable adapter
status tests run only in the parent process before fresh workers are spawned.

Generation and scoring are bound to one host: Mac model `Mac16,12`, Apple M4
with 10 cores (`proc 10:4:6:0`), 16 GB memory, arm64, macOS 26.5.1 build
`25F80`. Both launchers require AC power and AC `lowpowermode = 0`. On this host
`pmset -g therm` cannot report thermal or performance warning state, so the
experiment makes no thermal-stability claim; balanced variant ordering is the
predeclared mitigation for temporal drift.

One aggregate sample decodes all twelve streams four times in canonical order,
for 847,754,320 decoded bytes per variant. The campaign uses 30 fresh
processes. Facts-on (`F`), facts-off (`N`), and zlib-ng (`Z`) run in all six
orders repeated five times under one frozen deterministic shuffle using seed
`0x5244464c41544531`. Every complete sample is retained. There is no
fastest-of-N, warmup selection,
outlier removal, timeout removal, or rerun selected from its result.

The primary statistic is the median of 30 within-process `F/Z` aggregate
throughput ratios. Its 95% empirical nearest-rank percentile interval uses a
deterministic 10,000-resample order-stratified bootstrap with seed
`0x5244424f4f543031`: within each of the six order strata, five paired rows are
sampled with replacement from its five rows; each draw's statistic is the
median of all 30 paired ratios; sorted indices 249 and 9,749 are the bounds.
The predeclared practical-equivalence band is plus or minus 2%:

- interval lower bound above 1.02: meaningful Whitefoot win;
- both interval bounds inside `[0.98, 1.02]`: practical parity;
- interval upper bound below 0.98: meaningful zlib-ng win;
- otherwise: inconclusive.

A win or parity supports the current default-shape claim for this bulk
level-6 Silesia scenario. A zlib-ng win contradicts it for this scenario.
Generation failure, correctness failure, or invalid measurement is reported
directly and cannot be converted into a performance claim. Facts-on/facts-off
explains only this frozen source and cannot change the primary verdict.

## Freeze and amendment rule

The canonical `generation-inputs.json` binds every semantic, generation,
verification, and measurement input plus exact tool and host identities. The
launcher hard-codes that manifest's SHA-256. To avoid a self-hash cycle, the
manifest binds `run_generation.py` after normalizing only the value of its
64-hex manifest-hash assignment to zeros; every other launcher byte is hashed.
The exact run path is
`experiments/raw-deflate-default-shape/runs/primary-terra-medium-preregistered`.
Launch requires the complete repository to equal the committed
preregistration `HEAD`; that revision is recorded in the frozen trace.

Once frozen, any methodological or semantic change creates a new explicitly
secondary experiment. The primary source, corpus, comparator, schedule, or
verdict cannot be amended after generation starts.
