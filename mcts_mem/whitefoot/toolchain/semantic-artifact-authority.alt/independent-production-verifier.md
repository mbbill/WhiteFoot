- One source-independent syntax-directed checker publishes a source-, tree-, specification-, catalog-, and proof-schema-bound checked unit.
- A separate closed production verifier validates source binding, local proofs, whole-unit closure, and catalog completeness without parsing source or reproducing frontend semantics.
- One generic lowerer consumes only artifacts accepted by the separate verifier.

## Moves

- 2026-07-21 (4ecc14dd) replaced by [[mandatory-artifact-replay]]: a separately correct semantic verifier would duplicate the complete language while still needing producer-to-bytes consistency checks; one semantic kernel with mandatory artifact-only replay closes projection and codec defects without creating a second production compiler (sourced)
