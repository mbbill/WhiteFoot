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

[docs/roadmap.md](docs/roadmap.md) is the sole source for current execution
order and authorization. [AGENTS.md](AGENTS.md) records the priority rule and
structure discipline future agents must apply.

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

## Repository layout

The top level is a small, curated set. Each entry has one clear purpose; scripts
live next to what they check.

| Directory | What it is |
|---|---|
| [docs/](docs/) | The plan of record ([roadmap](docs/roadmap.md)), project law ([constitution](docs/constitution.md)), writer forms ([patterns](docs/patterns.md)), and the design rationale ([why-whitefoot](docs/why-whitefoot.md)) |
| [spec/](spec/) | The language: numbered kernel specifications (append-only) and the rule-derivation ledger under `spec/derivation/` |
| [compiler/](compiler/README.md) | The safe-Rust compiler (frontend today; resolver → checker → IR → LLVM to come) |
| [tests/](tests/) | Correctness evidence: `conformance/` behavior corpus, `reference/` semantics oracle, `codegen/` optimization-proof corpus (dormant, for the future backend) |
| [governance/](governance/) | The append-only [decision log](governance/decision-log.md), standing directives, the small repository-invariant and spec-append-only guards, and the pending `spec-evolution/` v0.10 proposal |
| [research/](research/) | Design memory: the [decision tree](research/design-tree/), measured `experiments/`, and exploratory notes |
| [archive/](archive/) | Retired and superseded material, inert — no active source, build, test, or tool depends on it |

## Verification

```sh
make install-hooks   # once: enable the spec append-only pre-commit hook
make check           # the gate: compiler, conformance, reference, lexical, spec append-only
```

The gate is deliberately small — the compiler builds and passes its tests, the
behavior corpus and reference model agree, and the numbered spec stays
append-only. Everything else (keeping conformance, tests, and other spec-derived
material consistent with the newest spec) is guarded by the guidance in
`AGENTS.md`, not by machinery. A green result states only what it exercises; it
does not claim the language or compiler is complete.

## License

Whitefoot is available under the [MIT License](LICENSE).
