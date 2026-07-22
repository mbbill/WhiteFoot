- Recoverable failures are ordinary `Result` values; Whitefoot has no exception, throw, catch, unwinding, or exception-handling region.
- The sole forwarding form is `let value: own T = propagate expression;`.
- `propagate` is the fixed terminal for this form; `try` is an ordinary IDENT and there is no compatibility alias.
- `Ok` binds its payload and continues; `Err` returns through the enclosing function's Result type and receives the checked auto-derived context record.

## Facts

- 2026-07-22 (c95bda9b) owner selection: `propagate` replaced `try` one-for-one because the construct forwards a Result value and does not enter an exception-handling region. (sourced)
- 2026-07-22 (d5c95b72) implementation: exact v0.11, the compiler frontend and resolver, conformance source, and the focused reference model all use `propagate`; `try` lexes and resolves as an ordinary identifier. (code)

## Moves

- 2026-07-22 (c95bda9b) replaced [[try-spelling]]: `try` commonly suggests entering exception-handling control flow, but Whitefoot only forwards an ordinary Result value; `propagate` names that exact action without implying throw, catch, or unwinding semantics (sourced)
