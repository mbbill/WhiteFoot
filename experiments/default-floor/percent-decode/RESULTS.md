# Default-floor percent-decode result

Status: complete preregistered primary campaign. This is the result of the one
allowed `gpt-5.6-terra` trajectory and the one allowed scoring campaign; it is
not a smoke run, rerun, best-of-N selection, or expert-xlang/Rust comparison.

## Outcome

The first correctness-green AI-written xlang decoder is meaningfully faster
than the shipped Rust comparator on the frozen workload.

| Variant | Median throughput | MAD / median | Samples |
|---|---:|---:|---:|
| xlang, facts on | 629.484 MiB/s | 1.221% | 30 |
| xlang, facts off | 620.343 MiB/s | 1.647% | 30 |
| `percent-encoding` 2.3.2 | 383.456 MiB/s | 1.403% | 30 |

The preregistered primary paired ratio is:

- median `throughput(xlang facts-on) / throughput(Rust)`: **1.6533**;
- stratified 10,000-resample 95% bootstrap interval: **[1.6309, 1.6668]**;
- frozen ±2% verdict: **meaningful xlang win**.

The attribution control is:

- median `throughput(xlang facts-on) / throughput(xlang facts-off)`: **1.0100**;
- 95% bootstrap interval: **[1.0047, 1.0196]**;
- frozen ±2% verdict: **practical parity**.

The facts-on and facts-off proof reports are byte-identical. Both enumerate six
bounds sites and retain all six; neither proves a site. The 65% primary win is
therefore not a proof-elision result. It is evidence for the narrower
default-floor claim: this ordinary Terra-written xlang shape beat the
unmodified, released Rust library path without expert source tuning.

## Frozen generation

The model was Codex CLI 0.144.0 with exact model slug `gpt-5.6-terra`, medium
reasoning, default service tier, one sequential trajectory, and no repository,
Rust source, performance result, profiler, IR, assembly, or optimization hint.

- round 0: compile failure, missing statement terminator;
- round 1: compiled, but `%0A` decoded as `00` instead of `0a`;
- round 2: first correctness-green source; frozen immediately;
- round 3: not invoked.

Frozen source SHA-256:
`b67dd2912ba907d64e38fc1044f52a305824b3d9141043a901027b64b94e00bd`.
The post-freeze evaluator independently repeated compile and all 153,014
ordered differential cases successfully. The capacity subprocess gate also
covered every undersized capacity and exact capacity for the six frozen
boundary sources, for both facts modes.

## Compared Rust implementation

The comparator is crates.io `percent-encoding` 2.3.2, exact default features
and ordinary Cargo release settings, checksum
`9b4f627cb1b25917193a259e49bdad08f671f8d9708acfd5fe0a8c1455d87220`.
The minimal adapter checks input-sized caller-owned capacity, consumes the
public `percent_decode(src)` iterator, and writes every yielded byte in order.
It does not reimplement, specialize, batch, or replace the crate algorithm.

A post-result assembly inspection gives a concrete, non-preregistered
explanation for part of the gap. The shipped Rust `decode_into` loop contains a
`bl` call to `PercentDecode::next` for every output byte. That trait method and
its `after_percent_sign` helper are out-of-line in the cross-crate release
build. The xlang helpers optimize into one call-free hot loop. This observation
does not change the primary verdict and is not evidence that expert Rust could
not close the gap: adding inlining, LTO, or restructuring the Rust is exactly
the expert/ceiling experiment deliberately excluded from this default-floor
score.

## Measurement

- host: MacBook Air (`Mac16,12`), Apple M4, 10 cores, 16 GB;
- OS: macOS 26.5.1, arm64;
- source revision: `7acd18adfd985c568b90fcec43b5146e1c41dd96`;
- corpus: 256 MiB, SHA-256
  `a8ea65fd669fe1ca5d5fc635c305067c12de30d67b4fcf9e9e6a85d7bb99e286`;
- schedule: all six three-variant orders repeated five times, then the frozen
  seeded Fisher-Yates shuffle; 30 fresh processes and 90 retained samples;
- power: AC before, during, and after the campaign;
- thermal probe: unavailable before and after with the same `pmset` error, so
  no observed transition but no positive thermal-state reading;
- compiler settings: Rust/Cargo 1.91.1 ordinary release; Apple Clang 21.0.0
  `-O3` for both xlang variants; default target CPU; no native CPU flag, LTO,
  PGO, alternate crate features, or scoring rerun.

One unusually slow facts-off sample was retained as preregistered. No sample
was removed or replaced. The raw paired result, bootstrap, order-position and
order-stratum summaries remain in `analysis.json`.

## Durable evidence

- protocol SHA-256:
  `34f4ad8bf9ae1a8371562a0c2c7562795eb19f56a49ab38c189d54c1a14eda56`;
- raw 30-block JSONL SHA-256:
  `a659855f0d3fa909874f861f6d7ec7401653a877a7c0bd0d1544d4333054324b`;
- schedule SHA-256:
  `a04d77da5d658672c1b82bc957ac5c81487d015f4da428a1b9f3776336b4220b`;
- analysis SHA-256:
  `24cfe1e9a3aed9d647d7ae9f684f178fe62c363bff1afa405a1dc245376bd5b9`;
- generation-freeze index SHA-256:
  `81793e6922c0a61b945d0f5eb6cedf6576b2e89afad750d2dba650ac3968c3ea`;
- scoring executable SHA-256:
  `7c3dec34669a7aee2b3f70be4053fd996bb6d496a2157fb9b7e70884181638c5`.

The 256-MiB corpus and Cargo target directory are intentionally ignored because
they are deterministically regenerable. Metadata, complete generation copy,
schedule, raw rows, logs, proof reports, xlang IR, and analysis are
retained under `results/primary-terra-medium-preregistered/`.

## Scope

This proves one implementation/corpus/machine result, not that every xlang
program beats every Rust library. It supports the chosen product claim much
more directly than an expert-Rust contest: a low-tier model's first green xlang
program was already in a faster performance class than a real shipped library.
A second independently preregistered library target is still required before
making a broad default-language claim.
