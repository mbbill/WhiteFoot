- Construction listed field values positionally in declared order and match binders were positional; no field names appeared at construction or destructuring sites.

## Facts

- 2026-07-07 statement: the spec's rule-derivation audit had already flagged this form before the re-decision — positional construct was never evaluated for weak-writer field-order transposition errors and sat off the provisional register entirely. (sourced)

## Moves

- 2026-07-08 (e687100a) replaced by [[construction-form]]: positional construction of same-typed fields admits silent transposition — an in-bounds wrong value on the forbidden silent-corruption rung; named-in-declared-order fields lift it to a check-time reject while declared order keeps one byte sequence (sourced)
