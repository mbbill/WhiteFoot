/* ctable: monomorphized table<u64, u64, fold> from optables.md S.2.
 * SwissTable: power-of-two buckets >= 16, one control byte per bucket, 16-byte
 * NEON group probe, H2 = low 7 hash bits [TBL-3, spec], H1 = remaining bits,
 * 7/8 max load, triangular probing, tombstone remove, foldhash-class hasher. */
#ifndef M3A_CTABLE_H
#define M3A_CTABLE_H
#include <stdint.h>

/* AoS slot: key and value stored together (one cache line per bucket access),
 * matching hashbrown's Bucket<(K,V)>. The catalog fixes the control/probe shape
 * but not the K/V physical layout; see the report's catalog finding. */
typedef struct { uint64_t key, val; } slot_t;

typedef struct {
    uint8_t  *ctrl;         /* num_buckets + 16 (mirrored first group) */
    slot_t   *slots;        /* num_buckets (K,V) pairs */
    uint64_t  bucket_mask;  /* num_buckets - 1; 0 and ctrl==NULL when empty */
    uint64_t  live;         /* live entries */
    uint64_t  occupied;     /* live + tombstones (FULL|DELETED control bytes) */
    uint64_t  growth_left;  /* floor(7/8*buckets) - occupied */
} ctable;

void     ctable_init(ctable *t);
void     ctable_free(ctable *t);
void     ctable_reserve(ctable *t, uint64_t n);  /* tbl_reserve: no later rehash */
/* tbl_insert: returns 1 if key existed (old value in *old), else 0. */
int      ctable_insert(ctable *t, uint64_t key, uint64_t val, uint64_t *old);
/* tbl_get / tbl_contains: returns 1 on hit (value in *out), else 0. */
int      ctable_get(const ctable *t, uint64_t key, uint64_t *out);
/* tbl_get_uniq: returns a mutable pointer to the value, or NULL on miss. */
uint64_t *ctable_get_uniq(ctable *t, uint64_t key);
/* tbl_remove: returns 1 if removed (old value in *old), else 0. */
int      ctable_remove(ctable *t, uint64_t key, uint64_t *old);
uint64_t ctable_len(const ctable *t);
uint64_t ctable_iterate_sum(const ctable *t);  /* CG-ITER over live slots */

#endif
