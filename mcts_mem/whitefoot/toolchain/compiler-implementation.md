- The active implementation is one safe-Rust crate under `compiler/`; crate boundaries and public protocols are not design goals.
- Exact active-spec behavior is preserved while implementation machinery is simplified around the next end-to-end consumer.
- The direct resolver and exact v0.11 activation are complete. The next consumer is one small semantic checker and checked in-memory representation feeding a target-independent scalar IR and one LLVM host backend.
- Semantic slices describe implementation and test order only; they never become a normative source-admission profile, function/signature allowlist, or alternate compiler path.
- Post-resolution rejection must establish an actual numbered-rule violation and be deterministic for one compiler executable, but competing first-error choice is not a portable language identity. Whole-unit semantic success remains the only path to checked lowering authority.
- Retired compiler and derivation scripts are inert under `archive/`; active source and gates never import them.
- The native grammar-proposal verifier accepts the unchanged active frontend contract and fails closed on grammar changes. It is a spec-development tool, not part of routine compilation; a future grammar-changing proposal must deliberately extend the compiler-sharing path.

## Facts

- 2026-07-22 code: six frontend crates, two hash/catalog identities, a source-audit crate, and version-forked Python table scripts were consolidated into one dependency-free Rust crate; the inherited v0.10 frontend suite passes. (code)
- 2026-07-22 code: exact active specification bytes are checked against the approved candidate and terminal/grammar data share the approved SHA-256 identity. (code)
- 2026-07-22 code: one direct general resolver covers the complete v0.10 declaration inventory and lexical-use relation, and the protected duplicate-main expectation now agrees with TYPE-6 after owner approval. (code)
- 2026-07-22 code: `whitefoot-grammar` verifies grammar-preserving proposals against 62 productions, 72 strong-LL(2) decisions, 72 terminal predicates, and the real frontend path. (code)
- 2026-07-22 reviewed proposal: v0.11 candidate SHA-256 `e4b3368a84c46235ad2bf6d91df6506050e116773cf183e001213b67f36cec1f` has three hostile-review GOs and remains non-authoritative pending exact owner approval. (sourced)
- 2026-07-22 code: the grammar verifier compares the complete FORM-1-through-GRAM contract, checks the translated fixed-terminal and IDENT partition, sends the candidate spelling through the raw lexer, and sends its inverse translation through the active classifier and parser; FORM-4, FORM-6, partial-rename, and structural-grammar mutations fail closed. (code)
- 2026-07-22 reviewed proposal: the preceding v0.11 freeze is superseded by SHA-256 `050e110c8c5eb3143c9d3f54968a9df9125f1d4b5991f527b8a15938a4292fbc`, which replaces exception-suggestive `try` with exact Result-forwarding `propagate` and remains non-authoritative pending exact owner approval. (sourced)
- 2026-07-22 owner approval: exact v0.11 candidate SHA-256 `050e110c8c5eb3143c9d3f54968a9df9125f1d4b5991f527b8a15938a4292fbc` is authorized for append-only activation and synchronized implementation. (sourced)
- 2026-07-22 code: the approved candidate is installed byte-identically as the active v0.11 specification; compiler syntax identity uses `Propagate`/`PropagateLetRhs`, conformance and the focused reference model use `propagate`, and the permanent grammar verifier again accepts only an unchanged active frontend contract. (code)

## Moves

- 2026-07-22 replaced [[permanent-artifact-compiler]]: starting with a permanent checked-artifact architecture treated private research-compiler boundaries as product protocols and multiplied crates and gates before a resolver or backend existed; one mutable compiler crate better serves the next end-to-end capability (sourced)
