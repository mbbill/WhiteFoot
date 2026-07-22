- Every borrow's provenance was a singleton with no parent-child lineage: borrows bound once, never rebound at control-flow merges, and `set` through a reference wrote through it rather than retargeting it.
- Uniq borrows were affine: passing one to a callee consumed it; there was no implicit reborrow, no reborrow through a holder, and no result reborrow.
- Exclusive access flowed through a call chain only by linear threading — the borrow or owned value passed in and came back out — or the code restructured.
- Scattered deep writes used returned write intents so deep functions stayed read-only and one shallow function applied the intents under the single exclusive borrow (the command-buffer pattern, P1).

## Facts

- 2026-07-07 rationale: prohibiting borrow reassignment and provenance joins collapses Featherweight Rust's path sets to a singleton and was the load-bearing frontend-scale-checker theorem (T-A). (sourced)
- 2026-07-10 measurement: the binary-trees port restructured around the restriction without a measured performance loss, so the strict form stayed defensible for workloads that did not need repeated calls through a retained uniq holder. (sourced)
- 2026-07-08 statement: explicit through-holder and result reborrows were already carded as the evidence-first relief valves if production evidence justified reopening this boundary. (sourced)

## Moves

- 2026-07-18 replaced by [[../no-reborrow]]: the self-hosting compiler needs ~1,062 statement-scoped through-holder reborrows (`&uniq 'local deref(holder)` passed as call arguments) that the strict form rejects, and the investigation showed keeping the rule forces the hot recursive analyzer core into an unblessed opaque owned-context shape that erodes the very no-alias facts the rule protects; v0.7 replaced it with a bounded, non-escaping, statement-scoped child reborrow (result-transfer and the harder forms deferred). (sourced)
