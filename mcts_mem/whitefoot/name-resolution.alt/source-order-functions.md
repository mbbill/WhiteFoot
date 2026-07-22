- A top-level function signature becomes visible only after its declaration, following the ordinary declaration-before-use rule.
- Calling a source-later function is rejected, including one edge of direct mutual recursion unless declarations are reordered or another indirection is introduced.

## Moves

- 2026-07-21 (4ecc14dd) replaced by [[name-resolution]]: source-order visibility made function item order semantically significant and obstructed direct mutual recursion; whole-unit function-signature visibility preserves the closed-unit recursion model while every non-function declaration keeps its explicit lexical visibility rule (sourced)
