- The exclusive borrow mode was spelled `&mut`, following the Rust convention, through kernel-spec v0.1.

## Facts

- 2026-07-03 statement: the rename was the v0.2 lexicon revision — one rule added (the lexicon policy itself), zero new spellings (a rename replaces a spelling), checker diagnostics realigned in the same change. (sourced)

## Moves

- 2026-07-07 (7c1d7641) replaced by [[borrow-lexicon]]: the exclusive mode's invariant is uniqueness, not mutation — `mut` conflates exclusivity with write permission and breaks under future interior-mutability capabilities (owner ruling D3, 2026-07-03) (sourced)
