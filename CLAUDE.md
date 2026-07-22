# Whitefoot — agent onboarding

Whitefoot is a systems language for AI-written, human-approved code. Entire bug
classes are unrepresentable (memory corruption, races, silent overflow,
uninitialized reads); there is no unsafe escape. The checker's proofs double
as optimizer facts: safety checks are always on unless a machine-verified proof
discharges them — speed is earned by proof, never by weakening a check.

## Project goal

The target is a serious research compiler: general enough to implement the
real language, clean enough to evolve, and capable of compiling nontrivial
programs so we can test semantics and performance ideas quickly. It is not an
untrusted-input service or a stable LLVM-scale product.

“Good enough” means a real compiler rather than a source-shaped demo: one
general implementation path, independent correctness tests, useful
diagnostics, an executable backend, and real programs that expose language and
compiler weaknesses. It does not mean exhaustive operational hardening,
service guarantees, stable external protocols, or infrastructure for imagined
future users.

When priorities conflict, use this order:

1. reach the next meaningful end-to-end language or performance experiment;
2. preserve semantic correctness and required safety checks;
3. keep the implementation understandable and easy to change;
4. add only the evidence needed to trust the current result; and
5. defer robustness, general infrastructure, and product polish that no
   current experiment needs.

If work does not help compile a real program, test a language rule, measure a
compiler idea, or remove the immediate blocker to one of those outcomes, it is
probably not the next work.

## Read order

1. `THE-PLAN.md` is the sole source for roadmap and authorization.
2. The tail of
   `optimizer-language-research/implementation/decision-gates.md`.
3. The relevant live `mcts_mem/` node and its `.alt/` history before a
   non-trivial design change.
4. As needed: `CONSTITUTION.md`, `PATTERNS.md`,
   `spec/kernel-spec-v0.9.md`, and
   `optimizer-language-research/notes/user-directives.md`.

## Goal discipline

The primary goal is the research compiler described above. It follows the
latest owner-approved Whitefoot specification and remains a continuing
implementation rather than a throwaway demo.

Optimize for trustworthy experimental feedback and iteration speed. Normal
Rust data structures, internal APIs that can evolve, and explicit development
limitations are acceptable. Release engineering, service-level resource
guarantees, stable interchange formats, transactional publication, exhaustive
failure taxonomies, and compatibility machinery are out of scope unless a
current experiment directly requires them.

Architecture, evidence, governance, tools, protocols, and documentation
support the compiler and the experiments; they are not competing products and
must not become self-justifying work streams.

Before starting or extending a step, state the concrete compiler or experiment
capability it unlocks and why that capability is the next one required by
`THE-PLAN.md`. Supporting work is justified only when it is the smallest
necessary way to remove a current blocker. A blocker being real does not make
every possible treatment proportionate.

Apply this relevance review before work, after hostile review exposes new
scope, and before every commit:

1. What concrete compiler capability or experiment does this unlock?
2. Is it required now, or can it wait until the real implementation provides
   better evidence?
3. What is the smallest sound solution?
4. Are we validating an implemented path, or constructing machinery for a
   hypothetical path?
5. Has the supporting work become larger or more complex than the capability
   it supports?
6. Will this help us run a meaningful language, correctness, or performance
   experiment soon?

If the answers show that work has drifted from the primary goal, stop. Do not
continue because the branch is internally consistent, already approved in
outline, difficult, interesting, or expensive to abandon. Preserve useful
facts, identify the mistaken assumption, and ask the owner to correct
`THE-PLAN.md` before continuing. Sunk cost grants no authority.

Do not build generalized frameworks, exhaustive protocol machinery, portable
identity systems, replay infrastructure, resource-profile systems, or
release-grade operational controls unless a current compiler capability or
experiment genuinely needs them. Prefer the simplest real end-to-end
implementation that can expose missing language rules, compiler mistakes, and
performance results. Development scaffolding may be temporary when it is
small, obvious, and easy to replace.

Hostile review must challenge relevance, proportionality, sequencing, and the
possibility of a smaller solution, not merely internal soundness. A technically
sound design that delays the next important compiler capability without
necessity is a failed review.

## Verify

- `make check` is always required. It checks repository structure,
  specification governance and integrity, the retained focused reference
  model, conformance data, the standalone grammar evidence, and the active Rust
  foundation. Its green result is an exact development-capability statement,
  never a release claim.
- `make -C compiler check` is also required before and after compiler work. The
  root gate incorporates it.
- A green development gate states only the capabilities its checks exercise;
  it is not a completeness claim.

## Standing rules

- English only: every new or modified repository artifact, identifier, comment,
  diagnostic, fixture, test name, document, and file or directory name uses
  English prose. Formal notation, programming-language tokens, numeric data,
  and external proper names are allowed.
- `AGENTS.md` and `CLAUDE.md` must remain byte-identical.
- The active numbered specification and evidence baseline is
  `spec/kernel-spec-v0.9.md`, SHA-256
  `bdfb461d1901f610633c5cbcd2477d24df3c77ca90599b9580c8289e50b82b68`.
  Compiler code does not reinterpret or edit that numbered file. Exact v0.8
  remains immutable historical authority for its versioned evidence.
- Kernel-spec changes are owner-gated in advance. Present the exact delta, get
  explicit approval, create a new numbered version and update every live
  reference, then run `make approve-spec REASON="..."` to regenerate the
  guarded baseline and append the governance entry.
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
- The compiler has one semantic implementation path. Do not add a second
  production-style verifier, certificate protocol, or artifact replay boundary
  unless an experiment later establishes a concrete need for one.
- [PROG-2] gives `SourceBundle` transport exact language meaning: one ordered,
  nonempty logical-source sequence forms one flattened program root; record
  order fixes top-level declaration order, and paths never create namespaces.
- A fact used to remove a required safety check needs independent adversarial
  evidence. Ordinary implementation decisions do not need release-grade
  hostile review.
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
- `compiler/` — the active safe-Rust research compiler workspace.
- `grammar-verifier/` — separately runnable independent grammar-change
  evidence; never compiler or language authority.
- `tools/` — active repository, governance, and verification tooling.
- `experiments/` — measured evidence and open development workloads.
- `optimizer-language-research/` — owner directives, decision log, design
  dossiers, and historical research evidence.
- `mcts_mem/` — current design decisions plus rejected alternatives.
- `archive/` — inert historical material. No active tool, build, test, or
  source import may read from it.

## Current authority

The owner replaced the self-host-first wfc/democ route on 2026-07-20. The old
implementations are archived and the Rust compiler is the continuing research
implementation rather than a disposable demo. The owner-approved exact v0.9
specification is active; v0.8 remains immutable history. Phases 1 through 4 are
complete, including the independently checked grammar repair, protected
migration, active-target switch, and exact canonical frontend.

The owner approved the exact v0.10 candidate. After the repository correction,
the next work is guarded installation of those unchanged bytes, frontend
reproduction, and then a direct general resolver. Numerical resource maxima,
measurement replay, release profiles, artifact protocols, and other
product-hardening work are not prerequisites. Later specification or protected
changes remain owner-gated; self-hosting remains a later decision.

The active workspace contains `whitefoot-contract`,
`whitefoot-language-data`, `whitefoot-lexer`, `whitefoot-syntax`,
`whitefoot-syntax-data`, `whitefoot-source-audit`, and the binary-only
`whitefoot-lexical-observer`. The observer is evidence only, the source audit
checks exact source/specification binding only, and the syntax package grants
canonical syntax authority only after its private derivation, linear
topology/source finalizer, and streaming FORM-2 audit all complete. No resolver,
semantic checker, backend, or compiler executable exists yet.
