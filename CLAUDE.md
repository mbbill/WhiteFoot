# Whitefoot — agent onboarding

Whitefoot is a systems language for AI-written, human-approved code. Entire bug
classes are unrepresentable (memory corruption, races, silent overflow,
uninitialized reads); there is no unsafe escape. The checker's proofs double
as optimizer facts: safety checks are always on unless a machine-verified proof
discharges them — speed is earned by proof, never by weakening a check.

## Read order

1. `THE-PLAN.md` is the sole source for roadmap and authorization.
2. The tail of
   `optimizer-language-research/implementation/decision-gates.md`.
3. The relevant live `mcts_mem/` node and its `.alt/` history before a
   non-trivial design change.
4. As needed: `CONSTITUTION.md`, `PATTERNS.md`,
   `spec/kernel-spec-v0.8.md`, and
   `optimizer-language-research/notes/user-directives.md`.

## Verify

- `make check` is always required. During the Phase-2 foundation it checks
  repository structure, specification governance and integrity, the retained
  focused reference model, and conformance data. Its output explicitly says
  that no compiler exists yet.
- Once Phase 2 creates `compiler/`, `make -C compiler check` is also required
  before and after compiler work. The root gate must incorporate it in the same
  tranche.
- A release claim uses the separate release gate defined by `THE-PLAN.md`; a
  green development gate is not a completeness claim.

## Standing rules

- English only: every new or modified repository artifact, identifier, comment,
  diagnostic, fixture, test name, document, and file or directory name uses
  English prose. Formal notation, programming-language tokens, numeric data,
  and external proper names are allowed.
- `AGENTS.md` and `CLAUDE.md` must remain byte-identical.
- The exact first implementation target is
  `spec/kernel-spec-v0.8.md`, SHA-256
  `d04336f7fa8d1a6a0f03fe58a17f972b658217a73a3dff91a906b4ba295328a8`.
  The implementation does not reinterpret or edit that numbered file.
- Kernel-spec changes are owner-gated in advance. Present the exact delta, get
  explicit approval, create a new numbered version and update every live
  reference, then record the approval in `governance/APPROVALS.md`.
- Earn a specification change with independent evidence, never implementation
  convenience. A compiler/spec discrepancy stops for investigation; compiler
  behavior cannot define the language.
- Conformance source and expected verdicts, frozen oracle digests, and active
  reference-semantics tests are owner-gated. Additive tests are free; modifying,
  deleting, weakening, or regenerating protected material needs exact logged
  approval followed by `make approve-spec REASON="..."`.
- A red spec guard means stop and obtain approval. Never regenerate a baseline
  merely to make the gate green.
- The conformance corpus is implementation-independent authority. Compiler
  capability, internal errors, timeouts, verifier failures, and backend
  failures live in adapter results, not normative expectations.
- Facts that can increase optimizer authority require hostile adversarial
  review before shipment. A green gate is not a review.
- Never trade a source check for speed. Proof-elision is the only path.
- Durability: each completed step gets one commit and one append-only
  `decision-gates.md` entry.
- Keep files cohesive and reviewable. Split by invariant-bearing
  responsibility, not arbitrary line counts, corpus functions, or one-use
  forwarding modules.
- Report results in plain performance and correctness language; keep internal
  project codenames in repository logs.
- Subagent tiering: sonnet only for mechanical work, opus for most tasks, and
  top tier for subtle soundness reasoning. Never haiku.

## Layout

- `spec/` — exact language versions and derivation evidence.
- `conformance/` — compiler-independent source and expected behavior.
- `codegen-corpus/` — implementation-independent proof/code-shape premises
  and hostile near misses; its old democ runner is dormant until replaced.
- `prototype/checker/` — retained focused reference model, never compiler or
  language authority.
- `compiler/` — the fresh Rust production compiler once Phase 2 creates it.
- `tools/` — active repository, governance, and verification tooling.
- `experiments/` — measured evidence and open development workloads.
- `optimizer-language-research/` — owner directives, decision log, design
  dossiers, and historical research evidence.
- `mcts_mem/` — current design decisions plus rejected alternatives.
- `archive/` — inert historical material. No active tool, build, test, or
  source import may read from it.

## Current authority

The owner replaced the self-host-first wfc/democ route on 2026-07-20. The old
implementations are archived, the exact v0.8 Rust implementation is the active
direction, and there is no disposable Rust compiler. `THE-PLAN.md` authorizes
phases 1 through 5 in order through the production v0.8 compiler baseline.
Specification changes, Phase-7 product qualification, and any later
self-hosting require their stated separate owner gates.
