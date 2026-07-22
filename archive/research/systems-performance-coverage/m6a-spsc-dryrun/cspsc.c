#include "cspsc.h"

cspsc *cspsc_new(uint64_t cap_pow2) {
    cspsc *q = (cspsc *)aligned_alloc(64, sizeof(cspsc));
    if (!q) abort();
    atomic_init(&q->tail, 0);
    atomic_init(&q->head, 0);
    q->cached_head = 0;
    q->cached_tail = 0;
    q->buf = (uint64_t *)malloc(cap_pow2 * sizeof(uint64_t));
    if (!q->buf) abort();
    q->mask = cap_pow2 - 1;
    return q;
}

void cspsc_free(cspsc *q) {
    if (q) { free(q->buf); free(q); }
}
