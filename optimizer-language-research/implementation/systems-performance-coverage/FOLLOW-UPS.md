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

## Resolved follow-ups

(none yet)
