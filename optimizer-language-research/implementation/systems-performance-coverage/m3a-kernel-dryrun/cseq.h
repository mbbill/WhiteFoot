/* cseq: monomorphized seq<u64, inline 0> from optables.md S.1.
 * Layout (ptr,len,cap); growth = least power of two >= max(2*cap, need, 4)
 * [SEQ-3]. push fast path per CG-PUSH: slack compare+branch, one store, one
 * length increment; growth is one out-of-line cold call. */
#ifndef M3A_CSEQ_H
#define M3A_CSEQ_H
#include <stdint.h>

typedef struct { uint64_t *ptr; uint64_t len; uint64_t cap; } cseq;

void     cseq_grow(cseq *s, uint64_t need);   /* cold, out-of-line */
void     cseq_reserve(cseq *s, uint64_t n);   /* S.1 seq_reserve (TCB OOM) */
uint64_t cseq_pop(cseq *s, int *ok);          /* S.1 seq_pop (Option<T>) */
uint64_t cseq_get(const cseq *s, uint64_t i); /* S.1 seq_get (bounds-trapped) */
uint64_t cseq_sum(const cseq *s);             /* CG-ITER iterate-sum */
void     cseq_free(cseq *s);

/* seq_push [CG-PUSH], header-inlined so callers get the pinned fast shape. */
static inline void cseq_push(cseq *s, uint64_t v) {
    if (__builtin_expect(s->len == s->cap, 0))
        cseq_grow(s, s->len + 1);
    s->ptr[s->len++] = v;
}

#endif
