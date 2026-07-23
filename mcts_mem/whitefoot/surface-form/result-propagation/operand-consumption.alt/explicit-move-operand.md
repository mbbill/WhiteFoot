- A bare affine Result place follows the ordinary OWN-1 expression rule and is rejected as a `propagate` operand.
- Forwarding a named affine Result requires `propagate move result`; non-place Result expressions remain valid.

## Facts

- 2026-07-22 statement: exact v0.12 had no ERR-3 exception to OWN-1, so this was the numbered rule the compiler followed while the corpus discrepancy awaited owner resolution. (sourced)

## Moves

- 2026-07-22 (e7b985ee) replaced by [[../operand-consumption]]: Result forwarding must consume one affine operand, and matching OWN-13 lets the canonical bare propagation form do so without weakening ownership, while requiring `propagate move p` contradicted the approved writer form. (sourced)
