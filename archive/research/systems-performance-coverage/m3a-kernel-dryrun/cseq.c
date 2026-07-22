#include "cseq.h"
#include <stdlib.h>

/* least power of two >= max(2*cap, need, 4)  [SEQ-3] */
static uint64_t next_cap(uint64_t cap, uint64_t need) {
    uint64_t base = 2 * cap;
    if (need > base) base = need;
    if (base < 4) base = 4;
    if ((base & (base - 1)) == 0) return base;          /* already 2^k */
    return 1ULL << (64 - __builtin_clzll(base - 1));
}

__attribute__((noinline, cold))
void cseq_grow(cseq *s, uint64_t need) {
    uint64_t nc = next_cap(s->cap, need);
    /* byte-size overflow trap per [SEQ-3]; TCB OOM per [CAT-6]. */
    if (nc > (uint64_t)-1 / sizeof(uint64_t)) { abort(); }
    uint64_t *p = (uint64_t *)realloc(s->ptr, (size_t)nc * sizeof(uint64_t));
    if (!p) abort();
    s->ptr = p;
    s->cap = nc;
}

void cseq_reserve(cseq *s, uint64_t n) {
    if (s->cap - s->len < n) cseq_grow(s, s->len + n);
}

uint64_t cseq_pop(cseq *s, int *ok) {
    if (s->len == 0) { *ok = 0; return 0; }
    *ok = 1;
    return s->ptr[--s->len];
}

uint64_t cseq_get(const cseq *s, uint64_t i) {
    if (__builtin_expect(i >= s->len, 0)) abort();      /* "seq index out of bounds" */
    return s->ptr[i];
}

uint64_t cseq_sum(const cseq *s) {
    uint64_t acc = 0;
    const uint64_t *p = s->ptr;
    uint64_t n = s->len;
    for (uint64_t i = 0; i < n; i++) acc += p[i];       /* CG-ITER: vectorizable */
    return acc;
}

void cseq_free(cseq *s) {
    free(s->ptr);
    s->ptr = 0; s->len = 0; s->cap = 0;
}
