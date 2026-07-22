- Surface names label checked invariants, defined self-containedly in the spec; backend-IR vocabulary never appears at the surface (LEX-1).
- The exclusive borrow mode is spelled `&uniq`; a name is borrowed from another language's convention only where a divergence census shows the semantics genuinely match.

## Facts

- 2026-07-03 statement: owner ruling D3 fixed the spelling — uniq follows the uniqueness-type lineage (Clean, Futhark; cf. Pony iso); mut was rejected because Rust's overload conflates exclusivity with mutation and breaks under future interior-mutability capabilities; noalias was rejected as backend vocabulary naming a lowering consequence, with rustc's noalias on/off history cited as evidence that backend coupling ages badly. (sourced)
- 2026-07-07 statement: the lexicon census returned 8 PASS, 1 HOLD (the apostrophe region sigil, kept provisionally), 0 FAIL, and recorded the reusable errs-toward-rejection principle: a borrowed name is safe when every prior-driven misuse lands as checker rejection, never as accepted-but-wrong code. (sourced)

## Moves

- 2026-07-07 (7c1d7641) replaced [[mut-spelling]]: the exclusive mode's invariant is uniqueness, not mutation — `mut` conflates exclusivity with write permission and breaks under future interior-mutability capabilities (owner ruling D3, 2026-07-03) (sourced)
