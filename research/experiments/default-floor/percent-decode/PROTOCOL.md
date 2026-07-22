# Default-floor percent-decode protocol

Status: preregistered; no model output or timing result may be inspected before
this protocol, `task.md`, and `teaching-pack.md` are fixed and the target base
prompt is assembled.  The generic runner archives and hash-binds the exact
prompt supplied in every round into the trial trace and frozen manifest.  Any
later protocol amendment is appended with a date and cannot change the primary
score of the original run.

## Question and primary comparison

The primary question is whether the first correctness-green xlang program from
one fixed low-tier-model trajectory is competitive with the ordinary released
implementation of a widely shipped Rust crate.  The primary performance ratio
is:

`throughput(xlang facts-on) / throughput(shipped Rust)`.

The exact same frozen xlang source compiled facts-off is an attribution control,
not another generated candidate.  There is no hand-written or expert xlang arm
in the primary score.  There is no constructed expert-Rust arm.

## Locked shipped-Rust target

- crate: `percent-encoding` 2.3.2, selected before generation;
- Cargo requirement: exact `=2.3.2`;
- features: Cargo default features enabled: `default = ["std"]`, with `std`
  enabling `alloc`;
- registry artifact SHA-256 / crates.io checksum:
  `9b4f627cb1b25917193a259e49bdad08f671f8d9708acfd5fe0a8c1455d87220`;
- repository: `https://github.com/servo/rust-url/`;
- published source anchor:
  `91377f48bf35011d042aa5abef9e7f2a0a625aaa`, path
  `percent_encoding`;
- authoritative lock: `rust-baseline/Cargo.lock` plus the registry checksum.

The crate's published `.cargo_vcs_info.json` records the source anchor with
`"dirty": true`.  The commit is therefore provenance, not a claim that a clean
checkout is byte-identical to the release.  The checksummed `.crate` artifact
and committed lockfile define the tested library.

Before the official prompt is sent, the launcher verifies the cached `.crate`
against that checksum and byte-compares every packaged file with every local
Cargo registry source tree named `percent-encoding-2.3.2` (apart from Cargo's
own `.cargo-ok` marker).  The correctness evaluator repeats this check on each
round.  The scoring harness repeats it before and after measurement and also
requires Cargo's verbose build log to identify one of those verified trees.
The observed archive and per-file hashes are retained in generation and score
metadata.

The Rust baseline must remain the published crate with default features.  The
only adapter is the committed safe `decode_into(out, src)` sink: it checks that
the caller-owned output slice is at least as long as the input, consumes the
public `percent_encoding::percent_decode(src)` iterator directly, writes each
yielded byte in order, and returns the written length.  It may not copy,
reimplement, batch, specialize, or inspect the crate algorithm.  The timed Rust
path and the Rust/oracle correctness preflight call this safe adapter directly;
only the xlang variants cross the C ABI.

## Frozen ABI and behavior

The compared kernel has this xlang ABI:

```text
fn decode ['r] (out: &uniq 'r buffer<u8>, src: own buffer<u8>) -> own u64 reads('r), writes('r), traps requires { ... } { ... }
```

At the machine boundary this is:

```c
typedef struct { uint8_t *p; int64_t n; } Buf;
uint64_t decode(Buf out, Buf src);
```

Inputs are arbitrary bytes, not necessarily UTF-8.  A `%` byte immediately
followed by two ASCII hexadecimal digits (`0`-`9`, `A`-`F`, or `a`-`f`) and
encountered as the next undecoded input item denotes the byte represented by
those two digits; the three input bytes produce that one byte.  A `%` without
two following hexadecimal digits is emitted unchanged and does not consume
lookahead bytes.  Every other byte is emitted unchanged.

The entry contract is `out.len >= src.len`, even when a particular input would
contract enough to fit in a smaller output.  Violation must trap before the
first output write.  On success the return value is the produced length, the
result occupies exactly `out[0..return]`, the remaining output suffix is
unchanged, and the source bytes are unchanged.  Source and output are distinct
live buffers.

## Model trajectory and information boundary

The generator is exactly:

- `codex-cli 0.144.0`;
- model `gpt-5.6-terra`;
- reasoning effort `medium`;
- Codex service tier `default`;
- one initial response and at most three repair responses on the same logical
  trajectory (four candidate sources maximum);
- no parallel samples, restarts, alternate seeds, best-of-N selection, or
  stronger-model replacement.

Every round is a fresh invocation through `codex_model_adapter.py`.  The
adapter invokes `codex exec --ephemeral` with model `gpt-5.6-terra`,
`model_reasoning_effort="medium"`, `service_tier="default"`, JSONL capture, an empty isolated working
directory, a read-only sandbox, and ignored user configuration and rules.
There is no session identifier, resume, or hidden conversational state.  On a
repair round, the generic runner supplies the complete self-contained prompt
for that round: the same target base prompt, its fixed source-only output
contract, the immediately preceding candidate, and the immediately preceding
accepted machine-evaluator JSON.  Thus all repair context is explicit even
though each invocation is ephemeral, and there is still only one sequential
trajectory.

The target base prompt contains only the literal bytes of `task.md`, then the
UTF-8 separator `\n===== BEGIN COMPLETE XLANG WRITER'S PACK =====\n\n`, then
the literal bytes of `teaching-pack.md`.  The locked component SHA-256 values
are respectively
`5ee6fbf0def51248ccc7749855a11c9b6cb8f44a664ff74326d84f91285fc022`
and
`a4ee1213415af5c56bdbbfa21697388b37f644bbc64a478ff7006fd03dcdfcd5`;
the resulting 6,764-byte `base-prompt.txt` SHA-256 is
`554050441f265d5c290756209a4a911f91004b1d55d73e6dd6a42bdc40d00dc7`.
`assemble_prompt.py` refuses changed components or an existing output.  On
every round,
`generate.py` appends its fixed `DEFAULT-FLOOR OUTPUT CONTRACT`, requiring only
complete candidate source and forbidding Markdown fences, explanations,
benchmark results, timing data, and performance measurements.  On repairs it
then appends the preceding source and accepted feedback as described above.
The exact resulting `prompt.txt`, canonical argv hashes and public metadata,
native stderr, CLI JSONL, accepted source, exit status, and environment
versions are retained and hash-bound by the run artifacts; raw argv is not
archived because it may contain credentials.  The temporary working directory
contains no repository checkout or baseline source.

The Codex JSONL boundary accepts exactly four events in order:
`thread.started`, `turn.started`, one `item.completed` whose item type is
`agent_message`, then `turn.completed`.  Any missing, repeated, reordered, or
post-completion event, any other item state, any tool or non-agent-message item,
or zero or multiple agent messages is a protocol failure and yields no
candidate.  The rejected JSONL remains archived for audit.  Consequently even
an attempted read or network/tool call invalidates the trial before scoring.

The model is forbidden from receiving or accessing:

- Rust source, crate implementation details, generated LLVM IR, assembly, or
  an implementation of the decoding task in any language;
- this protocol, the correctness corpus, benchmark corpus, Rust-library
  identity, timing data, profiler data, proof-site counts, bounds-check counts,
  throughput targets, or optimization advice;
- prior xlang percent-decode source or human edits to its candidate;
- feedback from another model.

The candidate source is the text of that single final completed agent message
exactly as emitted by the adapter.  There is no CRLF normalization, whitespace
stripping, fence extraction, prose removal, answer rewriting, or other cleanup.
Those exact UTF-8 bytes become `model.raw.txt`, the evaluator candidate, and—if
this is the first correctness-green round—the frozen source.

Repair feedback is limited to machine compiler/checker diagnostics or a
correctness failure containing the case bytes, expected result/termination,
actual result/termination, returned length, and sentinel/source-integrity
status.  Successful proof accounting, retained-check counts, code shape,
timings, comparative results, and human suggestions are never returned.  A
repair prompt asks only for a complete corrected source.

Compilation failure or correctness failure consumes one attempt.  The first
candidate passing the entire correctness gate is frozen immediately.  The
harness records its byte-for-byte source and SHA-256 before any proof report,
IR, assembly, or benchmark is inspected.  No unused repairs may be spent to
improve it.  If no candidate is green after the initial response plus three
repairs, the preregistered outcome is generation failure and there is no
performance score for this trajectory.

The adapter timeout is 600 seconds, the outer model-process timeout is 660
seconds, and the evaluator timeout is 900 seconds.  Every inner compiler,
linker, verifier, or capacity-process execution limit is likewise a protocol
failure, not permission to restart the trajectory under another run path.
`run_generation.py` is the sole launch surface and fixes the one run directory
to `runs/primary-terra-medium-preregistered`; it accepts no arguments, and its
existence permanently prevents a second launch under that identity.  Before
launch it requires every model, prompt, protocol, correctness, and benchmark
input to be tracked and byte-clean against `HEAD`.  It hash-locks Codex CLI
0.144.0, Python 3.9.6, Cargo/rustc 1.91.1, Apple Clang 21.0.0, their selected
executables, the transitive checker/compiler sources, and every harness input;
any mismatch aborts before the prompt is sent.

During the still-uncommitted freeze audit, the then-launcher incorrectly
ignored `--help` and attempted the retired identity `runs/primary-terra-medium`.
The adapter returned protocol error 70 before producing any model bytes: both
model stdout and candidate were empty, no evaluator ran, and nothing froze.
The artifact hashes and disposition are retained in
`incidents/2026-07-12-pre-freeze-launch.json`; opaque failed artifacts were
removed, that identity will never be reused, and the no-arguments guard was
tested before this preregistration.  This pre-freeze incident is not a sampled
candidate or part of the official trajectory.

## Deterministic correctness gate

Facts-on xlang, facts-off xlang, the Rust public-iterator adapter, and an
independent specification oracle must agree on every successful case.  Before
xlang is frozen, the generator receives only the single failing case selected
by stable corpus order, never Rust output or source.  The locked Rust adapter
and the independent oracle must first agree for the entire corpus; disagreement
is a harness failure, not model feedback.

All integer arithmetic in the generators below is modulo `2^64`.  `hex(v)` is
the two uppercase ASCII hexadecimal digits for byte `v`.

The stable corpus order is:

1. empty input; every one-byte input `[x]`; and the explicit truncations `%`
   and `%x` for every byte `x`;
2. every three-byte input `%xy`, in numeric `x` then `y` order, covering all
   65,536 suffix pairs (including all valid, invalid, binary, and mixed-case
   possibilities);
3. adjacency: `hex`-encoded `%HH%HH` for every ordered pair of decoded bytes
   `(a, b)` in `0..255` (65,536 cases), then `%HH%`, `%%HH`, and `%%%HH` for
   every byte value, followed by `%H%HH` for every `H` drawn in order from
   `0123456789ABCDEFabcdef` at each of its three digit positions;
4. the literal fixed cases `plain`, `100%`, `%GG`, `%4Z`, `%00`, `%ff`,
   `%41%42%43`, `a%%41b`, `%2%30`, `%%%`, `%25%32%35`, and the byte sequence
   `00 25 46 46 ff`;
5. 10,000 seeded fuzz cases from the generator below.

The fuzz generator is xorshift64*: initialize `state` to
`0x50455243454e5432`.  Each `next()` applies, in order,
`state ^= state >> 12`, `state ^= state << 25`, and
`state ^= state >> 27`, then returns
`state * 2685821657736338717`.  For each case, set
`length = next() % 4097`.  For each byte, take one `r = next()`; emit `%`
(`0x25`) when `(r & 7) == 0`, otherwise emit `(r >> 8) & 0xff`.  Case order is
generation order.

For every successful case, allocate output length `src.len + 32`, surround the
visible output range with 32-byte guard regions, fill all output and guards with
`0xA5`, and preserve a copy of the source.  Verify the returned length, exact
result prefix, unchanged suffix through the end of the visible output, both
guards, and unchanged source.

Capacity behavior is a separate subprocess gate.  For each source in ASCII
`A`, `%41`, `%41%42`, `%GG`, `a%20b`, and hexadecimal bytes
`00 25 46 46 ff`, call the C ABI
with every visible output length from zero through `src.len - 1`.  Shared guard
storage must demonstrate no output byte was changed before the nonzero trapped
termination.  In particular, `%41` with capacities one and two must still trap
despite its one-byte decoded result.  Exact-capacity calls must succeed.
Their returned length, exact decoded prefix, untouched suffix and guards, and
unchanged shared source are checked against an independent C oracle.

Both xlang builds must pass this entire gate.  Facts-on and facts-off must be
compiled from the exact frozen source; only the compiler's facts toggle may
differ.

## Builds and primary benchmark

Record the repository revision and dirty-state manifest, source/tool hashes,
host and OS, CPU and power state, `rustc`, Cargo, Clang, and Python versions,
and full build commands before measurement.  The final benchmark binary uses
`cargo rustc --release --locked --offline` solely to link the two xlang object
files; its Rust dependency still follows Cargo's ordinary default release
profile, default crate features, and generic/default CPU target.  There is no
`target-cpu=native`, target-specific `RUSTFLAGS`, or release-profile override.
Both xlang variants use the same compiler snapshot and Clang `-O3`
with its generic/default CPU target, with no `-mcpu=native`, `-march=native`,
or equivalent target attribute.  Facts-on versus facts-off is their only
difference.  No LTO, PGO, source patch, alternate feature set, unsafe
replacement adapter, or post-result compiler-flag search is allowed.

The primary input is exactly 256 MiB (`268,435,456` bytes), divided into
4,096-byte blocks repeating classes A, B, C, D, so each class contributes
exactly 64 MiB.  A separate xorshift64* stream uses seed
`0x504442454e434832` and the same `next()` definition as the correctness
generator.  Generation never depends on a measured result.

- A, literal: each byte uses one `r = next()` and is `(r >> 8) & 0xff`, except
  `0x25` is deterministically changed to `0x24`.
- B, sparse valid: each token uses one `r = next()`; when `(r & 15) == 0`, emit
  `%` plus the two hexadecimal digits of `(r >> 16) & 0xff`, otherwise emit the
  same mapped literal byte as A.
- C, dense valid: as B, but emit a valid escape when `(r & 1) == 0`.
- D, mixed malformed: each token uses one `r = next()`.  For `(r & 3)` equal
  to zero emit a valid escape as above; for one emit one of `%G0`, `%0G`,
  `%%0`, `%G%` selected by `(r >> 16) & 3`; otherwise emit the mapped literal.

For valid escapes, digits `0`-`9` are numeric ASCII; digits 10-15 use uppercase
for the high digit when bit 24 is zero and lowercase otherwise, and use
uppercase for the low digit when bit 25 is zero and lowercase otherwise.  A
token that does not fully fit in its current block is not emitted; fill each
remaining byte using successive class-A bytes.  Reset no RNG state at block or
class boundaries.  The harness records and asserts the completed corpus
SHA-256 before running a timed process.

The three timed variants are, in this fixed identity order:

1. frozen xlang, facts-on;
2. the same frozen xlang, facts-off;
3. shipped Rust through the direct public-iterator adapter.

They run in one executable against the same immutable input and equally sized
caller-owned output buffers.  Corpus generation, allocation, page touching,
correctness checks, and output digesting are outside timed intervals.  Each
timed result covers one full 256-MiB decode; input bytes divided by elapsed time
is the reported throughput.  The returned length and a digest of the produced
prefix are consumed after timing and must match across variants, preventing
dead-code removal.

Run 30 fresh-process blocks.  Each block measures all three variants exactly
once.  Name the variants `F` (facts-on), `N` (facts-off), and `R` (Rust).  Form
the list `FNR, FRN, NFR, NRF, RFN, RNF` repeated five times, then apply one
descending Fisher-Yates shuffle: for `i` from 29 through 1, swap positions `i`
and `next() % (i + 1)`, using xorshift64* seed `0x50444f5244455233`.
Thus every variant
occupies every ordinal position ten times and every ordered adjacent pair five
times per adjacency position, ten times in total.  Use one shared monotonic
clock implementation.  Retain every complete
sample; there is no outlier removal or fastest-of-N selection.  A process
crash, missing row, digest mismatch, thermal/power-state transition recorded by
the harness, or external interruption invalidates the campaign, preserves its
logs, and permits only a complete rerun with an appended reason.  On macOS the
orchestrator records the parsed power-source identity (not battery percentage)
and `pmset -g therm` state before and after every block; a changed available
value is a transition, while an unavailable probe is recorded as unavailable
at both points.  A slow sample alone is never invalid.

## Statistics and preregistered verdict

For each process block compute paired throughput ratios.  The primary point
estimate is the median of the 30 facts-on/Rust ratios.  Compute a descriptive
95% percentile interval with 10,000 bootstrap resamples, seed
`0x5044424f4f5432`; resample five blocks with replacement within each of the six
order strata, visiting strata in `FNR, FRN, NFR, NRF, RFN, RNF` order and
ordering each stratum's five source rows by ascending campaign block index,
then selecting each source index as `next() % 5`.  Take the median of the
resulting 30 ratios.  The median of an even-sized set is the arithmetic mean of
its two central sorted values.  After sorting the 10,000 bootstrap estimates,
the empirical nearest-rank interval is elements 249 and 9,749 at zero-based
indices.  Report raw
samples, per-variant median throughput, MAD/median, all order-position medians,
the primary ratio and interval, and the facts-on/facts-off paired ratio and
interval.  The facts attribution interval uses the same resample indices.

For the primary facts-on/Rust interval:

- lower bound greater than `1.02`: meaningful xlang win;
- both bounds within `[0.98, 1.02]`: practical parity;
- upper bound less than `0.98`: meaningful Rust win;
- every other overlap with a boundary: inconclusive against the 2% band.

These labels apply only to this implementation, corpus, machine, and run.  The
same four-way rule is reported for facts-on versus facts-off as attribution,
but it cannot change the primary verdict.  Correctness failure, generation
failure, or an invalid measurement campaign is reported directly and is not
converted into a performance claim.
