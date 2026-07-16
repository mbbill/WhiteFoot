# M6 SPSC queue dry run — results

INDICATIVE (Apple M4, macOS arm64; threads not hard-pinned). Deploy target is
Linux x86-64. cc = /usr/bin/cc (Apple clang), not the wasi clang in PATH.

## Part A — exhaustive small-bound model check (model.py)
Protocol modeled: optables.md S.3 conc_queue spsc — Lamport ring, pow2 capacity,
MONOTONE head/tail (index = counter & mask, full utilization), acquire/release
handoff, cursor caching (CG-QOP, no RMW). Bounds: capacity 2, producer sends
[1,2,3,4], consumer receives 4. Exhaustive over all reachable states (dedup
fixpoint). Properties: no lost/duplicated/wrong item, no read-before-published
slot, FIFO (terminal recv == (1,2,3,4)), both threads terminate (no deadlock).

Memory model: a release/acquire OPERATIONAL semantics with per-thread views
(captures inter-thread store->load staleness: a release store carries the
writer's view, an acquire load imports it, relaxed does neither, and slot reads
branch over every coherence-visible message) PLUS the intra-thread reordering
each weakened fence stops forbidding (the head/WAR pair carries no data, so its
role is pure ordering: relaxed head-release => publish-before-read; relaxed
head-acquire => overwrite-while-apparently-full).

| config                              | states | verdict          | violation class |
|-------------------------------------|-------:|------------------|-----------------|
| CORRECT (all acquire/release)       |    249 | SAFE             | — (12 good terminals, 0 bad, 0 deadlock) |
| M1 tail publish release->relaxed    |   1579 | VIOLATION FOUND  | read-before-published (slot holds BOT) |
| M2 tail read    acquire->relaxed    |   2219 | VIOLATION FOUND  | read-before-published (slot holds BOT) |
| M3 head publish release->relaxed    |    446 | VIOLATION FOUND  | WAR overwrite: wrong/lost item |
| M4 head read    acquire->relaxed    |   1404 | VIOLATION FOUND  | WAR overwrite: wrong/lost item |

All four acquire/release halves are load-bearing: weakening any one is caught at
this bound. NOT bounds-limited here — including the head/WAR pair, which carries
no consumer->producer data and is a pure ordering fence (redundant on a strong
model, required on ARM; the model's reordering leg exposes it).

## Part B — C implementation (cspsc.h/.c) + benchmark vs rtrb 0.3.4
Same machine, same run. cspsc built /usr/bin/cc -O3 -mcpu=native -pthread;
rtrb built cargo --release lto=fat target-cpu=native. Median of 21.

| benchmark              | cspsc (C)   | rtrb 0.3.4  | band          | verdict |
|------------------------|------------:|------------:|---------------|---------|
| round-trip latency     | ~31 ns/way  | ~39 ns/way  | 6-15 ns/way   | OVER (platform) |
| batched-32 throughput  | ~1050 M/s   | ~1320 M/s   | >= 80 M/s     | PASS (13-16x) |

Concurrent correctness: 50,000,000 items received strictly FIFO in-order, sum OK.

Latency band miss is PLATFORM, not the implementation: rtrb (a mature reference
SPSC crate) also lands ~39 ns/way on this M4/macOS host, and cspsc BEATS it
(~31 ns). ~30 ns is the M4 unpinned cross-core cache-coherency floor; the 6-15 ns
band is calibrated for a pinned x86 server (the spec's "reference pin host"). The
SHAPE is validated by the cspsc<=rtrb parity plus the asm below.

## ASM — the WIN claim (zero RMW on the steady-state path)
cspsc_try_send / cspsc_try_recv (otool of the inlined hot paths):
  ts:  ldr x8,[x0]        ; load own tail   (relaxed = plain ldr)
       ldr ... cached_head ; cached full-check
       b.ne  <publish>     ; not full -> straight to write+publish
       ldapur x9,[x0,#64]  ; ONLY when apparently full: acquire-load head
  tr:  ldr x8,[x0,#64]     ; load own head   (relaxed = plain ldr)
       ldr ... cached_tail
       b.ne  <read+pub>    ; not empty -> straight to read+publish
       ldapr  x9,[x0]      ; ONLY when apparently empty: acquire-load tail
Instruction-class summary across both paths:
  acquire-loads: 1x ldapr + 1x ldapur ; release-stores: 1x stlr + 1x stlur
  RMW (ldadd / ldaxr / stlxr / cas / swp / ldset...): ZERO
The amortized fast path (not full / not empty) has NO atomic acquire at all —
just a cached compare, a plain slot access, and one release store to publish —
exactly CG-QOP ("no RMW; one acquire load of the opposite cursor amortized below
one/op by caching; one release store to publish").

## Catalog finding
NONE required. The protocol exactly as specified (monotone counters, acquire/
release pairs, cursor caching, no-RMW) passes throughput by 13-16x and beats rtrb
on latency, with no deviation. Cache-line separation of the two cursors was
applied as standard practice (`_Alignas(64)` on head and tail); at batch-32 it is
amortized (touched once per 32 items) and measured NOT load-bearing for these
bands, though it matters for single-item latency use. The model check adds a
positive finding: all four acquire/release halves are essential, including the
data-less head/WAR pair.
