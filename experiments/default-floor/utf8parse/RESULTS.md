# Default-floor utf8parse result

Status: complete preregistered primary result. This is the protocol-permitted
full rerun of an invalid first scoring attempt, using the same frozen source,
protocol, generation binding, corpus, and schedule. It is not a smoke run,
elective rerun, best-of-N selection, or expert-xlang/Rust comparison.

## Outcome

The round-0, first-correctness-green AI-written xlang parser is meaningfully
faster than the shipped Rust comparator on the frozen workload.

| Variant | Median throughput | MAD / median | Samples |
|---|---:|---:|---:|
| xlang, facts on | 333.105 MiB/s | 15.062% | 30 |
| xlang, facts off | 319.673 MiB/s | 13.279% | 30 |
| `utf8parse` 0.2.2 | 280.474 MiB/s | 13.414% | 30 |

The preregistered primary paired ratio is:

- median `throughput(xlang facts-on) / throughput(Rust)`: **1.098014**;
- stratified 10,000-resample 95% bootstrap interval:
  **[1.084935, 1.144764]**;
- frozen ±2% verdict: **meaningful xlang win**.

The attribution control is:

- median `throughput(xlang facts-on) / throughput(xlang facts-off)`:
  **1.005071**;
- 95% bootstrap interval: **[0.985637, 1.034867]**;
- frozen ±2% verdict: **inconclusive against the 2% band**.

The facts-on and facts-off proof reports are byte-identical. Each enumerates
11 bounds sites, retains all 11, and proves none. A post-result comparison also
found their emitted machine code structurally isomorphic. The primary win is
therefore not evidence of proof-driven check elimination; it supports the
narrower default-floor claim that this ordinary Terra-written xlang program
beat an unmodified released Rust-library path without expert source tuning.

## Frozen generation

The generator was Codex CLI 0.144.0 with exact model slug `gpt-5.6-terra`,
medium reasoning, default service tier, one sequential trajectory, and no Rust
crate identity or source, performance result, profiler, IR, assembly, proof
report, or optimization hint.

- round 0: compiled and passed all 84,041 correctness cases; frozen
  immediately;
- rounds 1 through 3: not invoked.

Frozen source SHA-256:
`3bb7951995120d24c651b6750ac9ba4c7a8fb9b61bc02fb5d219e64e640c1535`.
The complete gate covered the independent oracle, shipped Rust, facts-on, and
facts-off implementations under both exact and surplus output capacities. The
separate capacity subprocess gate checked that representative undersized
outputs trap before writing.

## Compared Rust implementation

The comparator is crates.io `utf8parse` 0.2.2 with ordinary default features
and Cargo release settings, checksum
`06abde3611657adf66d383f00b093d7faecc7fa57071cce2578660c9f1010821`.
The minimal safe adapter creates the public `Parser`, advances it once per
input byte, and records public `Receiver` events in caller-owned storage. It
does not reimplement, specialize, batch, or replace the crate state machine,
and it has no manual inline annotations.

A post-result assembly inspection rules out a tempting explanation from the
earlier percent-decode target: the concrete Rust `Receiver` is monomorphized
and inlined, with no dynamic dispatch or out-of-line receiver call in the hot
path. The observed difference is consistent with the implementations' distinct
state-machine control-flow graphs and branch layouts on this synthetic mix,
but this is a mechanism hypothesis, not a causal proof. It is not evidence
that expert Rust restructuring or tuning could not close the gap.

## Measurement and rerun lineage

The first scoring directory began on AC power. After block 27 completed, the
mandatory probe observed a transition from AC Power to Battery Power, so the
entire campaign became invalid. Its 28 raw block rows were preserved for
audit, excluded from the result, and neither resumed nor selectively reused.

The frozen rerun rule required a new directory with explicit lineage to that
invalid attempt. The valid `rerun-01` campaign restarted from block 0 and
completed all 30 fresh-process blocks, retaining 90 samples. Battery Power was
stable before preparation, before measurement, across every block, and after
measurement.

- host: MacBook Air (`Mac16,12`), Apple M4, 10 cores, 16 GB;
- OS: macOS 26.5.1, arm64;
- source revision: `5b9360b6b94e8290297433077decb88c61ddf716`;
- corpus: 128 MiB, SHA-256
  `e7387acef66a3a0ca0cfa88cd7b57c18625cc9713bc16a41827c4899cb39ce18`;
- schedule: all six three-variant orders repeated five times, followed by the
  frozen seeded Fisher-Yates shuffle; 30 fresh processes and 90 retained
  samples;
- compiler settings: Rust/Cargo 1.91.1 ordinary release; Apple Clang 21.0.0
  `-O3` for both xlang variants; generic `aarch64-apple-darwin` target; no
  native CPU flag, LTO, PGO, alternate crate features, or sample removal.

The valid run is noisier than the percent-decode campaign: MAD/median is
13–15%, and median throughput falls by roughly 21–26% from first to third
execution position. All variants occupy every position ten times, all six
orders occur five times, and the preregistered bootstrap resamples within those
order strata; its paired interval remains wholly above 1.02. Even so, the
absolute throughput medians should be extrapolated cautiously. The 63 recorded
environment snapshots agree on Battery Power and the same no-warning thermal
output, but `pmset` is a coarse probe and does not record actual temperature,
frequency, or battery-level drift.

All three variants produced 84,446,861 events per measured block with the
same event-stream digest. Throughput is based on the 128 MiB input size; corpus
generation, file I/O, allocation and page touching, correctness hashing, and
output digesting are outside the timed interval.

## Durable evidence

- protocol SHA-256:
  `e786e949d1500c605ef37195dadc60e25380d4e02b7afc9f660d1cf5e062d960`;
- raw 30-block JSONL SHA-256:
  `71297ba0bfc2bc7b8af1f29b33f7c4769cb6c706f8a0c3f7c855363b86404ab3`;
- schedule SHA-256:
  `a04d77da5d658672c1b82bc957ac5c81487d015f4da428a1b9f3776336b4220b`;
- analysis SHA-256:
  `1a16044495b3e4d2e41c6f49d6f32cf9390d95a3b40f5f3e8c278077e115ff1c`;
- generation-freeze index SHA-256:
  `5ac7bfa8c4b81e6c3db1eb1c1a45879253232ae39d343a68f55ab466063ce822`;
- scoring executable SHA-256:
  `4795059eaeeb5597da3701823d833a8f9345fdca2eec2ad01feacdcfd652dc5f`.

The 128-MiB corpus and Cargo target directory are deterministically
regenerable. Metadata, the complete generation copy, schedule, raw rows,
logs, proof reports, xlang IR, and analysis are retained under
`results/primary-terra-medium-preregistered-rerun-01/`; the invalid first
campaign remains under `results/primary-terra-medium-preregistered/`.

## Scope

The corpus deliberately gives equal 32-MiB weight to four synthetic classes:
ASCII, valid ASCII-heavy text, valid multibyte-heavy text, and malformed or
boundary-stressing bytes. It is not a representative terminal, application,
or general text distribution.

The benchmark is also one-shot: every call starts in UTF-8 ground state and
parses one complete buffer. It does not measure persistent parser state across
chunks, EOF/finalization behavior, or `utf8parse`'s normal streaming use. The
result is a second preregistered default-floor datapoint, not a claim that every
xlang program beats every Rust library or that expert Rust cannot do better.
