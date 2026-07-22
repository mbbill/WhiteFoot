# Default-floor replicated result

Status: complete two-target preregistered series. This document synthesizes
the two frozen primary results; the target-specific reports and raw campaigns
remain authoritative for every number and caveat.

## Question

The experiment asks a deliberately practical question: when a fixed Terra
model writes its first correctness-green xlang implementation, does that
default program compete with the ordinary public path of an existing released
Rust library?

This is a performance-floor comparison. It is not an expert-Rust ceiling
contest and does not compare hand-tuned implementations in either language.

## Results

| Locked target | First green | Correctness gate | xlang facts-on | Shipped Rust | Paired median ratio + descriptive 95% interval | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `percent-encoding` 2.3.2 `percent_decode` | round 2 | 153,014 cases | 629.484 MiB/s | 383.456 MiB/s | **1.6533** [1.6309, 1.6668] | meaningful xlang win |
| `utf8parse` 0.2.2 one-shot parsing | round 0 | 84,041 cases | 333.105 MiB/s | 280.474 MiB/s | **1.0980** [1.0849, 1.1448] | meaningful xlang win |

Both separately frozen target results are outside the preregistered ±2%
practical-equivalence band in xlang's favor. The second effect is much smaller
than the first. There is deliberately no pooled effect estimate: the two
targets use different semantics, corpora, input sizes, adapters, and power
conditions, so averaging their ratios would imply a population model this
study does not have.

The primary statistic is the median of 30 within-process xlang/Rust throughput
ratios, not the quotient of the two descriptive throughput medians shown in
the table. Its interval is the protocol's descriptive, order-stratified
bootstrap interval; it is not an estimate for a randomly sampled ecosystem.

## What was held fixed

Each target used the same generation policy:

- Codex CLI 0.144.0, exact model `gpt-5.6-terra`, medium reasoning, default
  service tier;
- one sequential trajectory, with one initial response and at most three
  compile/correctness machine-diagnostic repair responses;
- first compile-and-correctness-green source frozen immediately;
- no parallel samples, restart, best-of-N selection, stronger-model fallback,
  human source edit, performance feedback, profiler, proof report, IR, or
  assembly before freeze;
- no Rust crate identity, Rust source, adapter source, benchmark corpus, or
  prior implementation exposed to the model.

Percent-decode reached first green only after one compile-diagnostic repair
and one correctness-diagnostic repair. Utf8parse's initial response was green.
Both outcomes follow the same first-green policy; “first green” does not mean
that every target's raw first response compiled or was correct.

The locked stage-0 compiler and checker hashes are identical across the two
target records. No compiler or checker change was fitted between the first
score and the replication target.

The Rust comparators are the exact checksummed crates with ordinary default
features and ordinary Cargo release builds. Small safe adapters consume only
their public APIs and write into caller-owned output. They do not reimplement,
specialize, batch, or replace the crate algorithms. No expert-Rust variant is
part of either primary score.

Each score uses 30 fresh processes, all six three-variant orders repeated five
times, paired within-block ratios, and the same locked 10,000-resample
order-stratified bootstrap. The xlang source is measured both facts-on and
facts-off; facts-off is an attribution control, never another generated
candidate.

## What caused the wins

The evidence rules out one broad explanation: neither primary win came from
the current xlang facts proving away bounds checks.

| Target | facts-on / facts-off | Attribution verdict | Proof accounting |
|---|---:|---|---|
| percent-decode | 1.0100 [1.0047, 1.0196] | practical parity | both reports identical; 6/6 sites retained |
| utf8parse | 1.0051 [0.9856, 1.0349] | inconclusive against ±2% | both reports identical; 11/11 sites retained |

The two mechanism inspections also differ. In percent-decode, the ordinary
cross-crate Rust build retains an out-of-line iterator `next` call while the
xlang helpers fold into one call-free loop. In utf8parse, Rust's generic
`Parser`/`Receiver` path monomorphizes and inlines completely; both sides are
call-free branch state machines, and the plausible difference is state
numbering, control-flow layout, and source-loop lowering. Therefore the
percent-decode out-of-line-call mechanism does not recur in utf8parse, but
neither inspection proves that an expert Rust rewrite could not close its gap.

## Claim boundary

A concise claim supported by the frozen evidence is:

> Across two separately preregistered shipped-library tasks, the first
> correctness-green programs produced by GPT-5.6-Terra in xlang had paired
> throughput ratios of 1.65x and 1.10x against the ordinary public Rust
> library paths on their locked workloads, while retaining all reported xlang
> bounds checks.

The result supports the narrower design thesis that xlang can give an AI a
high default performance floor without benchmark-specific source tuning. It
does not establish any of the following:

- that xlang is generally faster than Rust;
- that every AI-written xlang program is optimal;
- that these two selected tasks estimate an ecosystem-wide win rate;
- that xlang beats expert Rust, LTO, manual inlining, SIMD, or an algorithmic
  rewrite;
- that the current proof/facts channels caused either win;
- that either synthetic corpus represents a typical application workload.

The second target was selected and preregistered after the first result; neither
target is a random ecosystem sample. Their freezes are separate in prompt,
correctness corpus, scoring corpus, and source identity, but they share one
model family, compiler, machine, and overall harness design. This is
replication across tasks, not statistically independent replication across
laboratories, hardware, or toolchains.

## Target-specific caveats

The percent-decode campaign used a 256 MiB frozen workload under stable AC
power and had low dispersion. Its 65% result is partly explained by the
ordinary released iterator path's surviving out-of-line call, so it should not
be presented as a Rust ceiling.

The utf8parse campaign is one-shot rather than persistent streaming. Its 128
MiB corpus gives equal weight to ASCII, valid ASCII-heavy, valid
multibyte-heavy, and malformed/boundary-heavy classes; this is not a typical
terminal or text distribution. The first scoring attempt was invalidated by an
AC-to-battery transition and preserved. The protocol-authorized complete
rerun remained on stable Battery Power and produced the valid result, but had
13–15% dispersion, with descriptive position medians falling roughly 21–26%
from first to third execution position. The preregistered balanced schedule and
paired, order-stratified analysis nevertheless yield an interval wholly above
1.02; absolute throughput should still be extrapolated cautiously.

## Decision

D9a's requested shipped-library replication is complete. A third target is not
required to preserve this gate result. Any additional timing of either frozen
source must be labeled secondary sensitivity evidence and cannot replace its
primary campaign. In particular, a stable-AC utf8parse rerun could quantify
environment sensitivity, but cannot be selected as a new primary result.

The experiment track can now stop steering target selection and return to the
xlc self-hosting build track. Further language/compiler features should follow
the normal staged roadmap rather than being fitted to these two measured
sources.

## Authoritative records

- percent-decode protocol and result:
  `percent-decode/PROTOCOL.md`, `percent-decode/RESULTS.md`;
- utf8parse protocol and result:
  `utf8parse/PROTOCOL.md`, `utf8parse/RESULTS.md`;
- target-independent generation boundary: `PROTOCOL.md`;
- chronological decisions:
  `../../optimizer-language-research/implementation/decision-gates.md`.
