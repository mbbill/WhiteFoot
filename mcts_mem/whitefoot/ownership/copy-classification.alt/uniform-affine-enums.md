- Every enum value was affine regardless of payload: only primitives and shared borrows copied, and a Bool or any other tag-only enum was consumed by match and by owned-argument passing like any resource.

## Facts

- 2026-07-10 statement: the uniform rule's own provenance was minimality-selection (one classification clause for all enums), an R3-provisional ground; the amendment's recorded derivation states that affinity of resource-free values was never evidence-selected. (sourced)
- 2026-07-10 measurement: the integer-flag workaround this rule forced on loop-carried predicate state lowered as an i64 recurrence vectorizing at width 2x4 versus width 16 for the i1 form — the 1.6–1.8x classifier gap on the chunk-summary wc kernel. (sourced)

## Moves

- 2026-07-10 (c658bc34) replaced by [[copy-classification]]: affine classification of resource-free tag-only values bought zero safety while taxing every boolean — an owned Bool could not be loop-carried state or flow through band/bnot dataflow, forcing integer-flag workarounds whose i64 recurrence vectorized at width 2x4 instead of 16, a measured 1.6–1.8x kernel loss (sourced)
