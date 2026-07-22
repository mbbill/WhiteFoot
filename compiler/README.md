# Whitefoot compiler

This directory is one safe-Rust crate containing the active compiler. It is an
implementation, not a collection of stable libraries: module boundaries are
private design choices and should change when the next compiler capability
needs them.

The implemented path is currently:

```text
ordered source bundle
  -> lossless lexer
  -> terminal classification
  -> strong-LL(2) parser
  -> finalized source-bound syntax tree
  -> exact FORM-2 validation
  -> direct v0.11 lexical name resolution
  -> scalar semantic checking
  -> private checked program
  -> target-independent scalar IR
  -> conservative textual LLVM
  -> host executable
```

The frontend targets the exact bytes of
`../spec/kernel-spec-v0.11.md`. `cargo run --bin whitefoot-spec` checks that
those bytes are the approved candidate and that the terminal and grammar data
name the same specification identity. The committed grammar tables are
ordinary compiler data. For a specification proposal, run the native verifier
through this compiler:

```sh
cargo run --bin whitefoot-grammar -- ../governance/spec-evolution/CANDIDATE.md
```

It compares the proposal's complete canonical-format, lexer, and grammar
contract with the active contract, checks the compiler's terminal inventory
and every strong-LL(2) decision, and runs the real lexer and parser. It fails
closed when a proposal changes that contract; a structural change must first
extend this same native path rather than reviving an independent grammar
engine.

The resolver covers every v0.11 declaration, lexical-use, and deferred
owner/member role through one grammar-driven path, including exact scopes,
visibility, reservations, collisions, and deterministic diagnostics.

The first executable semantic family supports exact scalar integers, unit,
`Bool` construction/checking, integer and unit constants, nongeneric own-mode functions,
locals, direct calls, returns, pure/traps effects, wrapping and trapping
add/subtract/multiply, and integer comparisons. Semantic success produces the
only lowering authority. The IR retains required checks and source trap sites;
the backend uses conservative LLVM without unearned overflow flags or check
elision. Unimplemented v0.11 families stop as explicit unsupported compiler
capabilities.

Compile a source file through the normal path with:

```sh
cargo run --bin whitefootc -- source.wf -o program
cargo run --bin whitefootc -- --emit-llvm source.wf
```

There is deliberately no artifact protocol, replay layer, resource-profile
product, or compatibility boundary in front of this path.

Run the compiler gate with:

```sh
make check
```
