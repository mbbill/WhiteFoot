# Archived decision history

This is the retired transition log and stable index for Whitefoot's historical
design and implementation records. The complete dated volumes live in the
adjacent `decisions/` directory, split by the kernel-specification era that was
active when the work happened. This index was archived on 2026-07-22.

The history explains why earlier work existed. It does not authorize current
work or override `../../docs/roadmap.md`, the active numbered specification,
`../../docs/constitution.md`, or `../../governance/directives.md`.

The live design-memory map is [`mcts_mem/whitefoot.md`](../../mcts_mem/whitefoot.md).
A durable choice with a real competing alternative belongs there as a current
node plus its rejected `.alt` branch. These versioned files retain the fuller
chronology, approvals, implementation results, and superseded evidence; do not
copy that activity stream into the design tree.

## Final live transitions before archival

- 2026-07-22: exact v0.11 became the active immutable language specification;
  the compiler frontend, resolver, conformance corpus, and focused reference
  model moved together to the sole `propagate` Result-forwarding spelling.
- 2026-07-22: the inactive v0.8/v0.9 specification catalogs moved under
  `archive/`; no active compiler, build, test, or tool imports them.
- 2026-07-22: durable current choices and genuine rejected alternatives were
  reconciled into `mcts_mem/`; the complete older chronology moved to the
  archive rather than remaining in live governance.

## Archived current and recent versions

| Era | Dates | Record |
|---|---|---|
| v0.11 | 2026-07-22 | [v0.11](decisions/v0.11.md) |
| v0.10 | 2026-07-22 | [v0.10](decisions/v0.10.md) |
| v0.9 | 2026-07-21 to 2026-07-22 | [v0.9](decisions/v0.9.md) |
| v0.8 | 2026-07-19 | [v0.8, July 19](decisions/v0.8-2026-07-19.md) |
| v0.8 | 2026-07-20 | [v0.8, July 20](decisions/v0.8-2026-07-20.md) |
| v0.8 | 2026-07-21 before v0.9 activation | [v0.8, July 21](decisions/v0.8-2026-07-21.md) |
| v0.7 | 2026-07-18 to 2026-07-19 | [v0.7](decisions/v0.7.md) |

## Archived early versions

The v0.6 era contains most of the early language and performance research, so
it is divided by date to keep each file reviewable.

| Era | Dates | Record |
|---|---|---|
| v0.6 | 2026-07-18 before v0.7 activation | [v0.6, July 18](decisions/v0.6-2026-07-18.md) |
| v0.6 | 2026-07-17 | [v0.6, July 17](decisions/v0.6-2026-07-17.md) |
| v0.6 | 2026-07-16 | [v0.6, July 16](decisions/v0.6-2026-07-16.md) |
| v0.6 | 2026-07-15 | [v0.6, July 15](decisions/v0.6-2026-07-15.md) |
| v0.6 | 2026-07-14 | [v0.6, July 14](decisions/v0.6-2026-07-14.md) |
| v0.6 | 2026-07-12 to 2026-07-13 | [v0.6, July 12–13](decisions/v0.6-2026-07-12-to-13.md) |
| v0.5–v0.6 | 2026-07-08 to 2026-07-11 | [v0.5–v0.6, July 8–11](decisions/v0.5-v0.6-2026-07-08-to-11.md) |
| v0.0–v0.4 | 2026-07-01 to 2026-07-07 | [v0.0–v0.4 foundations](decisions/v0.0-v0.4.md) |

## Successor record locations

Current implementation status lives in `../../docs/roadmap.md`, durable design
choices and rejected alternatives live in `../../mcts_mem/`, and protected
owner approvals live in `../../governance/APPROVALS.md`. This archived index and
its dated volumes are not appended or rewritten to match current terminology.
