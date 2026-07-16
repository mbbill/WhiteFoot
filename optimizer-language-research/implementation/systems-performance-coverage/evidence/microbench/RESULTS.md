# Micro-measurement results (2026-07-16, Apple M4, macOS aarch64)

Indicative constants; deployment target is Linux x86-64. Sources in this
directory (clonebench_main.rs, bench_accept.c).

## A. Sealed-table clone constant (POD entries, u64->u64)

std HashMap (SipHash): 100k 1.39 ns/entry, 1M 1.03, 10M 0.68 (median).
hashbrown 0.17.1 (foldhash): 100k 1.21, 1M 2.06, 10M 1.79.
Verdict: the audit's assumed ~50-100 ns/entry is wrong by ~25-100x for
Copy/POD entries — clone is a bandwidth-bound bulk copy (~15-25 GB/s here),
no per-entry rehash or allocation. Caveat: owning-value tables (heap V) are
allocation-dominated and need a separate measurement; one number does not
cover both entry kinds.

## B. Darwin accept + SO_RCVTIMEO

Listener SO_RCVTIMEO=1s accepted silently (rc=0) but accept() blocked past
the timeout (returned only via a 4s safety alarm, EINTR): macOS does NOT
honor listener SO_RCVTIMEO — the member audit's timed-accept graceful-drain
mechanism is broken on Darwin. Control: SO_RCVTIMEO on an ACCEPTED socket
works (read returns EAGAIN at 1.001s) — per-connection deadlines are fine.
Consequence: the self-connect-wakeup / kqueue-drain fallback is the required
Darwin path and what the acceptance battery must exercise; Linux behavior
(claimed to honor it) must be verified on the deployment target separately.

## A2. Owning-value table clone constants (same platform/method)

ns/entry median: String 24B — 9.3 (100k), 25.6 (1M), 31.9 (10M);
String 200B — 36.2 (100k), 50.9 (1M), 248.7 (10M);
Vec<u8> 4KB — 363.5 (100k), 3062.9 (1M). Decomposition: POD bulk copy
(~1-2 ns) + exactly one malloc per entry + payload memcpy + page faults at
scale. The old ~50-100 ns/entry assumption is right only for ~200B values
near 1M entries; it is 25-100x too high for POD and 3-30x too low for
KB-scale values.

Interpretation for the COW-republish card (correcting the measuring agent's
final framing): the clone cost IS the publish cost. POD/handle tables:
publish ~1-2 ms per 1M entries — COW viable at modest update rates.
KB-value tables: publish ~3 s per 1M entries — COW republish is non-viable
except at very low update rates; that regime belongs to the sharded-mutex
card or the deferred in-place concurrent table. The card's falsifier must
select its constant by the target scenario's value type; no single threshold
is honest.
