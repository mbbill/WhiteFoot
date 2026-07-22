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
  -> direct v0.10 lexical name resolution
```

The frontend targets the exact bytes of
`../spec/kernel-spec-v0.10.md`. `cargo run --bin whitefoot-spec` checks that
those bytes are the approved candidate and that the terminal and grammar data
name the same specification identity. The committed grammar tables are
ordinary compiler data. For a specification proposal, run the native verifier
through this compiler:

```sh
cargo run --bin whitefoot-grammar -- ../governance/spec-evolution/CANDIDATE.md
```

It compares the proposal's complete canonical-format, lexer, and grammar
contract with the active contract and checks the compiler's terminal inventory
and every strong-LL(2) decision. In addition to an unchanged grammar, it accepts
v0.11's exact one-for-one `try_let_rhs` / `"try"` to
`propagate_let_rhs` / `"propagate"` rename. The candidate spelling passes
through the real raw lexer; inverse translation then proves the active
classifier and parser exercise the identical structure, including the changed
fixed-terminal/IDENT partition. It fails closed on every other grammar change;
a structural change must extend this same native path rather than reviving an
independent grammar engine.

The resolver covers every v0.10 declaration, lexical-use, and deferred
owner/member role through one grammar-driven path, including exact scopes,
visibility, reservations, collisions, and deterministic diagnostics. The next
implementation is the first coherent semantic-to-LLVM slice over its
`ResolvedSyntaxUnit`, after the exact semantic-closure candidate is approved.
There is deliberately no artifact protocol, replay layer, resource-profile
product, or compatibility boundary in front of it.

Run the compiler gate with:

```sh
make check
```
