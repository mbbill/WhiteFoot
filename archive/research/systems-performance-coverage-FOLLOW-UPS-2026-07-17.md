# Systems-Performance Coverage — Tracked Follow-Ups

Date opened: 2026-07-17

Durable register of deferred items that must NOT be lost. Committed (rewind-proof)
per the repo's durability discipline; the authoritative list even if the task
system is cleared. Each item: what, why deferred, the trigger/gate to resume, and
its source ruling.

## Open follow-ups

### FU-1 — OWN-11 loop-spawn capture carve-out (owner-flagged "don't forget")
- **What:** allow user-written dynamic spawn loops whose N workers each capture
  shared outer state (e.g. N request-handlers reading one routing table, count
  set at startup), by carving out OWN-11's "no outer region name in a loop body"
  rule under the concurrency delta's persistent per-capture loan entries.
- **Why deferred:** D19 decision 2 shipped option (a) for v1 (fixed straight-line
  spawn + the sealed `par.for_chunks` combinator, which already covers runtime-N
  chunk parallelism). The carve-out amends a ratified region rule and needs its
  own hostile-review round.
- **Covered in v1 without it:** split-one-buffer data parallelism (parallel grep,
  parallel sort partition, parallel map) via `par.for_chunks`.
- **NOT covered until it lands:** custom dynamic spawn topologies where workers
  capture shared outer references rather than disjoint chunks.
- **Resume trigger:** after v1's concurrency layer is real, OR sooner if a named
  scenario needs runtime-N workers each holding a shared borrow of common state.
  Must pass its own hostile review before adoption (sound under the persistent
  capture-loan machinery, but authority-amending).
- **Source:** D19 decision 2 (`../../notes/user-directives.md`).


### FU-2 — Fold AMD-6/AMD-7/AMD-8 into RULES-RATIFIED.md (at landing)
- **What:** `RULES-RATIFIED.md` currently holds AMD-1..5. AMD-6 (BRAND-1
  endpoint declassification) and AMD-7/AMD-8 (the concurrency amendments,
  ratified by D19 decision 3) are not yet consolidated into the ratified
  rule set; drafts reference them but the canonical file stops at AMD-5.
- **Why deferred:** consolidation is a landing/production-spec step, gated on
  the separate landing review.
- **Resume trigger:** production spec drafting begins.
- **Source:** decision-5 spec-cut verification (D19-R1).

### FU-3 — Relocate MM-1..MM-6 / MM-10 to the kernel spec, keep only MM-0+MM-7 in the manual
- **What:** the memory-model discharge obligations (MM-1..MM-6 spawn/join/
  mutex/queue/reclamation edges, MM-10 target lowering) are TCB-author /
  reviewer material, not writer-facing. Per the D19 decision-5 principle (the
  always-loaded manual holds only what a WRITER needs), the always-loaded
  concurrency section should keep only MM-0's D1 guarantee and MM-7's `sync`
  rule; MM-1..6/MM-10 move to the kernel spec (separately budgeted), where
  decision 1 lands CONC-0 anyway.
- **Why deferred:** it is both a correctness improvement and the top spec-mass
  reduction lever (~1.5-2k of the current 4k conc-normative extract); apply at
  landing, or sooner if the ~1.6k always-loaded headroom tightens.
- **Resume trigger:** production spec drafting, or any concurrency/catalog
  growth that pushes the always-loaded set toward 48k.
- **Source:** decision-5 spec-cut finding (D19-R1); [[spec-content-principle]] applies.

## Resolved follow-ups

(none yet)
