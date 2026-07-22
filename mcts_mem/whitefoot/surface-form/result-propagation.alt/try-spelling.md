- Result forwarding is written `let value: own T = try expression;`.
- The operation still returns `Err` from the enclosing function and has no exception, throw, catch, or unwinding semantics.

## Facts

- 2026-07-09 statement: `try` was the fixed ERR-3 spelling from v0.3.1 through v0.10 and in the first v0.11 semantic-closure candidate. (sourced)

## Moves

- 2026-07-22 (c95bda9b) replaced by [[result-propagation]]: `try` commonly suggests entering exception-handling control flow, but Whitefoot only forwards an ordinary Result value; `propagate` names that exact action without implying throw, catch, or unwinding semantics (sourced)
