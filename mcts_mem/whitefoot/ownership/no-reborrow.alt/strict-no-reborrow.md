- Every borrow's provenance was one immutable resolved root. Borrows bound once, never rebound at control-flow merges, and never formed a parent-child lineage.
- Uniq borrows were affine: passing one to a callee consumed it; there was no implicit reborrow, no reborrow through a holder, and no result reborrow.
- Exclusive access flowed through a call chain only by linear threading — the borrow or owned value passed in and came back out — or the code restructured.
- Scattered deep writes used returned write intents. Deep functions stayed read-only while one shallow function applied the intents under the single exclusive borrow (the command-buffer pattern, P1).

## Facts

- 2026-07-07 rationale: prohibiting borrow reassignment and provenance joins collapses Featherweight Rust's path sets to a singleton and was the load-bearing frontend-scale-checker theorem (T-A). (sourced)
- 2026-07-10 measurement: the binary-trees port restructured around the restriction without a measured performance loss, so the strict form stayed defensible for workloads that did not need repeated calls through a retained uniq holder. (sourced)
- 2026-07-08 statement: explicit through-holder and result reborrows were already carded as the evidence-first relief valves if production evidence justified reopening this boundary. (sourced)

## Moves

- 2026-07-18 (f9e0abbb) replaced by [[../no-reborrow]]: the ~1,062 statement-scoped through-holder sites made strict no-reborrow force the compiler into an unblessed owned-context shape, while the bounded non-escaping child form preserves the reviewed no-alias facts; result transfer and harder reborrow forms remain deferred (sourced)
