# Whitefoot

Whitefoot is a systems language for AI-written, human-approved code. It is
designed so that memory corruption, data races, uninitialized reads, and silent
overflow are unrepresentable in accepted source. There is no writer-accessible
unsafe escape. Runtime safety checks remain enabled unless a machine-verified
proof authorizes their removal.

## Project goal

The target is a serious research compiler: general enough to implement the
real language, clean enough to evolve, and capable of compiling nontrivial
programs so we can test semantics and performance ideas quickly. It is not an
untrusted-input service or a stable LLVM-scale product.

This is more than a demo compiler: language behavior must come from general
rules, correctness tests stay compiler-independent where useful, and the
compiler must eventually emit and run real programs. Product-scale resource
controls, stable artifact protocols, distribution, and release engineering are
not current goals.

[THE-PLAN.md](THE-PLAN.md) is the sole source for current execution order and
authorization. [AGENTS.md](AGENTS.md) records the priority rule future agents
must apply.

## Current state

[Kernel specification v0.9](spec/kernel-spec-v0.9.md), SHA-256
`bdfb461d1901f610633c5cbcd2477d24df3c77ca90599b9580c8289e50b82b68`,
is the immutable active specification. Exact v0.8 remains immutable history.
The exact v0.10 candidate has been approved but is not active until guarded
installation and frontend reproduction complete.

The safe-Rust compiler currently implements:

```text
ordered source bundle
  -> lossless lexer
  -> context-free terminal classification
  -> iterative strong-LL(2) parsing
  -> one finalized source-bound syntax tree
  -> exact FORM-2 source validation
  -> CanonicalSyntaxUnit
```

There is not yet a resolver, semantic checker, IR, LLVM backend, compiler
executable, or runnable Whitefoot program. The immediate path is to activate
v0.10, reproduce the frontend, implement direct general name resolution, and
then drive the first coherent semantic slice through LLVM.

## What exists

The active compiler workspace contains:

- `whitefoot-contract` for specification identity, ordered source transport,
  spans, and shared frontend contracts;
- `whitefoot-language-data` for specification-derived terminal predicates;
- `whitefoot-lexer` for lossless shape-only lexical formation;
- `whitefoot-syntax-data` for generated grammar and predictive data;
- `whitefoot-syntax` for classification, parsing, finalization, and canonical
  source validation;
- `whitefoot-source-audit` for exact source/specification binding; and
- `whitefoot-lexical-observer` as a development adapter for the independent
  lexical model.

The standalone `grammar-verifier/` is a specification-development tool, not a
normal compiler dependency. The conformance corpus, code-shape corpus, focused
reference models, and experiments are evidence. None defines compiler behavior
or licenses source-specific handling.

The retired wfc and democ implementations remain inert under `archive/`. No
active source, build, test, or tool imports from them.

## Verification

Run:

```sh
make -C compiler check
make check
```

A green result states only the capabilities those checks exercise. It does not
claim that the language or compiler is complete.

## Repository guide

The top level is small and ordered so the most important things come first: the
plan, the language specification, and the compiler. Everything below that is
supporting evidence, gate tooling, design history, and retired code. Many of
these paths are pinned by the project's spec-and-test guard or wired into the
build, so the layout is deliberately stable.

**Start here**

| Purpose | Location |
|---|---|
| Current execution order and authorization (sole source) | [THE-PLAN.md](THE-PLAN.md) |
| Project law | [CONSTITUTION.md](CONSTITUTION.md) |
| Writer forms (pattern doctrine) | [PATTERNS.md](PATTERNS.md) |
| Agent instructions (byte-identical) | [AGENTS.md](AGENTS.md) / [CLAUDE.md](CLAUDE.md) |

**The language and the compiler**

| Purpose | Location |
|---|---|
| Numbered kernel specifications; the active one defines the language (append-only) | [spec/](spec/) |
| Active safe-Rust compiler | [compiler/](compiler/README.md) |

**Behavior evidence and gate tooling**

| Purpose | Location |
|---|---|
| Compiler-independent behavior corpus (owner-gated) | [conformance/](conformance/README.md) |
| Repository gate scripts (spec guard, catalogs, models) | [tools/](tools/) |
| Owner approvals and the guard baseline | [governance/](governance/) |
| Standalone grammar and spec-development evidence (holds the v0.10 candidate) | [grammar-verifier/](grammar-verifier/README.md) |
| Focused reference semantics | [prototype/checker/](prototype/checker/) |
| Proof, catalog, and fixture evidence | [codegen-corpus/](codegen-corpus/README.md), [facets/](facets/), [capabilities/](capabilities/README.md), [frontend-corpus/](frontend-corpus/) |

**Design memory and research**

| Purpose | Location |
|---|---|
| Design decision tree (why the language is the way it is) | [mcts_mem/](mcts_mem/) |
| Design dossiers, notes, the append-only decision log, and the v0.10 successor generator | [optimizer-language-research/](optimizer-language-research/) |
| Vision and rationale prose | [docs/why-whitefoot.md](docs/why-whitefoot.md) |
| Measured performance experiments | [experiments/](experiments/README.md) |

**History**

| Purpose | Location |
|---|---|
| Retired implementations, inert (no active dependency) | [archive/](archive/) |

## License

Whitefoot is available under the [MIT License](LICENSE).
