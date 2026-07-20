# Retired self-hosting toolchain

This directory preserves the compiler implementations retired by the
2026-07-20 owner decision to build the production compiler from scratch in
Rust.

Source identity:

- source commit: `75b768ba`;
- Whitefoot wfc tree: `1657f14a8d1b61938f84ee59d9337e7cf3892885`;
- Python democ tree: `21232a7a3cd6309a189e9212e427a0185ee394e1`;
- retained active reference-checker tree at the transition:
  `8f05bc894fb98c3b2928f7343a492da5aab4d074`.

Contents:

- `wfc/` — the incomplete Whitefoot compiler and its implementation-specific
  tests;
- `democ/` — the Python stage-0 compiler and its implementation-specific tests;
  and
- `notes/` — implementation inventories that described the retired tape-based
  compiler.

The last recorded wfc state had 655 functions, 166 provisional clean results,
489 `Unsupported` results, and a 15-function profile lowerer. Its source also
contained 4,568 omitted explicit region arguments and no conforming FN-7 entry
point. These measurements describe the archived implementation, not Whitefoot
language coverage.

Nothing in this directory is active authority or part of a repository gate.
For an exact replay, use a separate worktree at the source commit:

```sh
git worktree add /tmp/whitefoot-self-hosting-2026-07-20 75b768ba
make -C /tmp/whitefoot-self-hosting-2026-07-20 check
make -C /tmp/whitefoot-self-hosting-2026-07-20/compiler check
```

The active repository may re-derive general regressions from this evidence, but
must not import implementation code or read files from this archive during a
build or test.
