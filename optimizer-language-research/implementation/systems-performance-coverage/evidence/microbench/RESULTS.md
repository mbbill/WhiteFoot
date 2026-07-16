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
