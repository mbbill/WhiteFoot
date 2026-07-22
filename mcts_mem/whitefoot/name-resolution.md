- Name resolution starts from one complete declaration inventory and then resolves grammar-selected use roles in their specified domains and scopes.
- Every top-level function signature is visible throughout the closed compilation unit.
- Prelude source-visible entries are whole-unit visible; source nominals, constructors, contracts, generics, parameters, locals, regions, labels, and named constants retain their exact lexical visibility rules.
- Inventory knowledge never grants visibility outside the rule selected for that declaration class.

## Facts

- 2026-07-21 (4ecc14dd) owner ruling: whole-unit top-level function visibility was selected to admit direct and mutual recursion without making function source order semantic, while every other declaration retained its specified lexical visibility point. (sourced)
- 2026-07-22 (72f4ac18) implementation: one direct resolver inventories the complete unit, makes every top-level function visible at every use, preserves lexical declaration-before-use for the other source classes, and reports a nested declaration that shadows a source-later function. (code)
- 2026-07-22 (d5c95b72) specification: exact v0.11 retains the closed-unit visibility rule and the resolver remains on the ordinary compiler path. (sourced)

## Moves

- 2026-07-21 (4ecc14dd) replaced [[source-order-functions]]: source-order visibility made function item order semantically significant and obstructed direct mutual recursion; whole-unit function-signature visibility preserves the closed-unit recursion model while every non-function declaration keeps its explicit lexical visibility rule (sourced)
