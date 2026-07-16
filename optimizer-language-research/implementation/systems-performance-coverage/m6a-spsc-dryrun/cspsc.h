/* cspsc: the modeled conc_queue<T=u64, spsc, K> from optables.md S.3.
 * Lamport ring, pow2 capacity, monotone head/tail counters (index = counter &
 * mask), acquire/release handoff, cursor caching (CG-QOP: NO read-modify-write;
 * one acquire load of the opposite cursor amortized below one/op by caching; one
 * release store to publish; hot path guaranteed-inline). Owned endpoints: only
 * the producer thread touches tail/cached_head, only the consumer touches
 * head/cached_tail. */
#ifndef M6A_CSPSC_H
#define M6A_CSPSC_H
#include <stdint.h>
#include <stdatomic.h>
#include <stdlib.h>

typedef struct {
    /* producer-owned cache line */
    _Alignas(64) _Atomic uint64_t tail;   /* written by producer, read by consumer */
    uint64_t cached_head;                 /* producer-local mirror of head */
    /* consumer-owned cache line */
    _Alignas(64) _Atomic uint64_t head;   /* written by consumer, read by producer */
    uint64_t cached_tail;                 /* consumer-local mirror of tail */
    /* shared read-only after init */
    _Alignas(64) uint64_t *buf;
    uint64_t mask;                        /* capacity-1 */
} cspsc;

cspsc *cspsc_new(uint64_t cap_pow2);      /* cap must be a power of two */
void   cspsc_free(cspsc *q);

/* cq_try_send: 1 on success (v enqueued), 0 if full. */
static inline int cspsc_try_send(cspsc *q, uint64_t v) {
    uint64_t t = atomic_load_explicit(&q->tail, memory_order_relaxed);  /* own cursor */
    uint64_t cap = q->mask + 1;
    if (t - q->cached_head == cap) {                    /* appears full: one acquire */
        q->cached_head = atomic_load_explicit(&q->head, memory_order_acquire);
        if (t - q->cached_head == cap) return 0;        /* really full */
    }
    q->buf[t & q->mask] = v;                            /* plain store */
    atomic_store_explicit(&q->tail, t + 1, memory_order_release);  /* publish */
    return 1;
}

/* cq_try_recv: 1 on success (*out set), 0 if empty. */
static inline int cspsc_try_recv(cspsc *q, uint64_t *out) {
    uint64_t h = atomic_load_explicit(&q->head, memory_order_relaxed);  /* own cursor */
    if (q->cached_tail == h) {                          /* appears empty: one acquire */
        q->cached_tail = atomic_load_explicit(&q->tail, memory_order_acquire);
        if (q->cached_tail == h) return 0;              /* really empty */
    }
    *out = q->buf[h & q->mask];                         /* plain load */
    atomic_store_explicit(&q->head, h + 1, memory_order_release);  /* publish (free slot) */
    return 1;
}

/* CG-QBATCH: one cursor reservation (plain, spsc), contiguous copy, one release
 * publish per batch. Returns the count admitted (0..n). */
static inline uint64_t cspsc_send_batch(cspsc *q, const uint64_t *src, uint64_t n) {
    uint64_t t = atomic_load_explicit(&q->tail, memory_order_relaxed);
    uint64_t cap = q->mask + 1;
    uint64_t space = cap - (t - q->cached_head);
    if (space < n) {
        q->cached_head = atomic_load_explicit(&q->head, memory_order_acquire);
        space = cap - (t - q->cached_head);
    }
    uint64_t k = n < space ? n : space;
    uint64_t off = t & q->mask;
    uint64_t first = cap - off; if (first > k) first = k;   /* up to wrap */
    for (uint64_t i = 0; i < first; i++) q->buf[off + i] = src[i];
    for (uint64_t i = first; i < k; i++) q->buf[i - first] = src[i];
    atomic_store_explicit(&q->tail, t + k, memory_order_release);
    return k;
}

/* CG-QBATCH recv side: pull up to max into dst; returns count. */
static inline uint64_t cspsc_recv_batch(cspsc *q, uint64_t *dst, uint64_t max) {
    uint64_t h = atomic_load_explicit(&q->head, memory_order_relaxed);
    uint64_t avail = q->cached_tail - h;
    if (avail < max) {
        q->cached_tail = atomic_load_explicit(&q->tail, memory_order_acquire);
        avail = q->cached_tail - h;
    }
    uint64_t k = max < avail ? max : avail;
    uint64_t off = h & q->mask;
    uint64_t cap = q->mask + 1;
    uint64_t first = cap - off; if (first > k) first = k;
    for (uint64_t i = 0; i < first; i++) dst[i] = q->buf[off + i];
    for (uint64_t i = first; i < k; i++) dst[i] = q->buf[i - first];
    atomic_store_explicit(&q->head, h + k, memory_order_release);
    return k;
}

#endif
