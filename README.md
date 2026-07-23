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
order and authorization. [WORKFLOW.md](WORKFLOW.md) defines the complete
cross-directory language-change process. [AGENTS.md](AGENTS.md) records the
priority rule and structure discipline future agents must apply.

## Current state

[Kernel specification v0.12](spec/kernel-spec-v0.12.md), SHA-256
`e2d5566379891454c090e037bd45c5f1a8df90ba23506a0f83ce9aaa03b41463`,
is the immutable active specification. Exact v0.8 through v0.11 remain
immutable history.

The safe-Rust compiler currently implements one ordinary path:

```text
ordered source bundle
  -> lossless lexer
  -> context-free terminal classification
  -> iterative strong-LL(2) parsing
  -> one finalized source-bound syntax tree
  -> exact FORM-2 source validation
  -> CanonicalSyntaxUnit
  -> direct v0.12 lexical name resolution
  -> ResolvedSyntaxUnit
  -> semantic and ownership checking
  -> private checked program
  -> target-independent typed control-flow IR
  -> conservative LLVM
  -> host executable
```

The executable slice covers scalar integer/unit values, `Bool`, integer and unit
constants, nongeneric own-mode functions, locals, direct named calls, returns,
pure/traps effects, integer wrap/trap arithmetic and comparisons, Boolean
operations, nominal tag equality, and nongeneric acyclic structs and enums.
Nominal values use the same path for construction, nested projection,
statement/value matching, `give`, whole-binding affine moves, explicit cleanup,
and cross-function aggregate values. SET-1 copy-place assignment is implemented
for live own-mode locals and nested struct fields through the same checked and
LLVM path. Other valid v0.12 families stop as explicit unsupported compiler
capabilities; they are not reported as invalid Whitefoot.

## Repository layout

The top level is a small, curated set. Each entry has one clear purpose; scripts
live next to what they check.

| Directory | What it is |
|---|---|
| [docs/](docs/) | The plan of record ([roadmap](docs/roadmap.md)), project law ([constitution](docs/constitution.md)), writer forms ([patterns](docs/patterns.md)), and the design rationale ([why-whitefoot](docs/why-whitefoot.md)) |
| [spec/](spec/) | The language: numbered kernel specifications (append-only) and the rule-derivation ledger under `spec/derivation/` |
| [compiler/](compiler/README.md) | The safe-Rust compiler: frontend, resolver, first semantic/IR slice, LLVM backend, and `whitefootc` |
| [tests/](tests/) | Test evidence: the active compiler-independent `conformance/` behavior corpus, plus preserved `codegen/` source cases awaiting production-compiler integration |
| [governance/](governance/) | The protected approval ledger, exact successor candidates, and the tracked spec-append-only hook |
| [research/](research/) | Active language and compiler experiments |
| [mcts_mem/](mcts_mem/) | The live design tree, consulted and maintained only through the `mcts-mem-use` skill |
| [archive/](archive/) | Retired and superseded material, including the historical [decision log](archive/governance/decision-log.md), Python reference model, and democ-era codegen harness; inert — no active source, build, test, or tool depends on it |

## Verification

```sh
make install-hooks   # once: enable the spec append-only pre-commit hook
make check           # the gate: compiler, conformance, spec append-only
```

The gate is deliberately small: the compiler builds and passes its tests; the
conformance corpus has valid active-spec identity, structure, rule coverage,
and expectations; and numbered specifications remain append-only. The complete
conformance corpus is not yet executed against the compiler because its
adapter is still Phase 8 work. A green result states only what the gate
exercises and is not a completeness claim.

## License

Whitefoot is available under the [MIT License](LICENSE).
