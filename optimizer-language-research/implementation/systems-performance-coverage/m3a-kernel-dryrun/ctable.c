#include "ctable.h"
#include <stdlib.h>
#include <string.h>
#include <arm_neon.h>

#define GROUP_W       16
#define CTRL_EMPTY    0x80u
#define CTRL_DELETED  0xFEu
#define BITMASK_MASK  0x8888888888888888ULL

/* foldhash-class hasher: foldhash-fast's single folded 128-bit multiply for a
 * u64, fixed seed. NOT byte-identical to the foldhash crate; same op shape. */
#define FH_C1 0x2d358dccaa6c78a5ULL
#define FH_C2 0x8bb84b93962eacc9ULL
static inline uint64_t hash_u64(uint64_t x) {
    unsigned __int128 w = (unsigned __int128)(x ^ FH_C1) * (x ^ FH_C2);
    return (uint64_t)w ^ (uint64_t)(w >> 64);
}

/* --- NEON group ops (CG-PROBE). A probe step does ONE 16B control load; the
 * masks below are computed from that single loaded vector (never re-loading). */
static inline uint64_t movemask4(uint8x16_t cmp) {
    /* 4-bit-stride bitmask, hashbrown-on-aarch64 shape. Matching lane i => bit
     * (4*i+3) set; LANE() recovers i via ctz>>2. */
    uint8x8_t nar = vshrn_n_u16(vreinterpretq_u16_u8(cmp), 4);
    return vget_lane_u64(vreinterpret_u64_u8(nar), 0) & BITMASK_MASK;
}
static inline uint64_t mask_h2(uint8x16_t g, uint8_t h2) {
    return movemask4(vceqq_u8(g, vdupq_n_u8(h2)));
}
static inline uint64_t mask_empty(uint8x16_t g) {
    return movemask4(vceqq_u8(g, vdupq_n_u8(CTRL_EMPTY)));
}
static inline uint64_t mask_empty_or_deleted(uint8x16_t g) {
    return movemask4(vreinterpretq_u8_s8(vshrq_n_s8(vreinterpretq_s8_u8(g), 7)));
}
static inline uint64_t mask_full(uint8x16_t g) {
    return movemask4(vreinterpretq_u8_s8(vcgezq_s8(vreinterpretq_s8_u8(g))));
}
#define LANE(mask) ((uint64_t)__builtin_ctzll(mask) >> 2)

void ctable_init(ctable *t) { memset(t, 0, sizeof(*t)); }

void ctable_free(ctable *t) {
    free(t->ctrl); free(t->slots);
    memset(t, 0, sizeof(*t));
}

static inline void set_ctrl(ctable *t, uint64_t idx, uint8_t val) {
    t->ctrl[idx] = val;
    /* mirror the first group at the tail so unaligned group loads wrap [TBL-3] */
    uint64_t idx2 = ((idx - GROUP_W) & t->bucket_mask) + GROUP_W;
    t->ctrl[idx2] = val;
}

static void alloc_buckets(ctable *t, uint64_t nb) {
    t->ctrl  = (uint8_t *)malloc(nb + GROUP_W);
    t->slots = (slot_t *)malloc(nb * sizeof(slot_t));
    if (!t->ctrl || !t->slots) abort();
    memset(t->ctrl, CTRL_EMPTY, nb + GROUP_W);
    t->bucket_mask = nb - 1;
    t->occupied = 0;
    t->growth_left = nb - nb / 8;      /* floor(7/8 * nb) */
}

/* first empty-or-deleted slot in probe order (used on a tombstone-free table) */
static uint64_t find_insert_slot(const ctable *t, uint64_t hash) {
    uint64_t mask = t->bucket_mask, pos = (hash >> 7) & mask, stride = 0;
    for (;;) {
        uint64_t med = mask_empty_or_deleted(vld1q_u8(&t->ctrl[pos]));
        if (med) return (pos + LANE(med)) & mask;
        stride += GROUP_W;
        pos = (pos + stride) & mask;
    }
}

/* find key OR the insertion slot. returns 1 (found, *idx) or 0 (absent, *slot).
 * Common path is two group masks (h2, empty); empty_or_deleted only for a full
 * group -- matches CG-PROBE and hashbrown's find_or_find_insert_slot. */
static int find_or_slot(const ctable *t, uint64_t key, uint64_t hash, uint8_t h2,
                        uint64_t *idx, uint64_t *slot) {
    uint64_t mask = t->bucket_mask, pos = (hash >> 7) & mask, stride = 0;
    uint64_t cand = (uint64_t)-1;
    for (;;) {
        uint8x16_t g = vld1q_u8(&t->ctrl[pos]);      /* one 16B control load */
        uint64_t mh = mask_h2(g, h2);
        while (mh) {
            uint64_t i = (pos + LANE(mh)) & mask;
            if (t->slots[i].key == key) { *idx = i; return 1; }
            mh &= mh - 1;
        }
        uint64_t me = mask_empty(g);
        if (me) {
            *slot = (cand != (uint64_t)-1) ? cand : ((pos + LANE(me)) & mask);
            return 0;
        }
        if (cand == (uint64_t)-1) {
            uint64_t med = mask_empty_or_deleted(g);
            if (med) cand = (pos + LANE(med)) & mask;
        }
        stride += GROUP_W;
        pos = (pos + stride) & mask;
    }
}

static void reinsert(ctable *t, uint64_t key, uint64_t val) {
    uint64_t h = hash_u64(key);
    uint64_t slot = find_insert_slot(t, h);
    t->slots[slot].key = key; t->slots[slot].val = val;
    set_ctrl(t, slot, (uint8_t)(h & 0x7F));
}

/* rehash [TBL-4]: in-place purge (same size) when live <= buckets/2, else 2x. */
static void rehash(ctable *t) {
    uint64_t old_nb = t->bucket_mask + 1;
    uint64_t new_nb = (t->live <= old_nb / 2) ? old_nb : old_nb * 2;
    uint8_t *octrl = t->ctrl;  slot_t *oslots = t->slots;
    alloc_buckets(t, new_nb);
    for (uint64_t base = 0; base < old_nb; base += GROUP_W) {   /* group-scan full slots */
        uint64_t m = mask_full(vld1q_u8(&octrl[base]));
        while (m) { uint64_t i = base + LANE(m); reinsert(t, oslots[i].key, oslots[i].val); m &= m - 1; }
    }
    t->occupied = t->live;
    t->growth_left = (new_nb - new_nb / 8) - t->live;
    free(octrl); free(oslots);
}

void ctable_reserve(ctable *t, uint64_t n) {
    uint64_t target = t->live + n;
    uint64_t nb = GROUP_W;
    while (nb - nb / 8 < target) nb <<= 1;
    if (t->ctrl && (t->bucket_mask + 1) >= nb) return;
    if (t->ctrl == NULL) { alloc_buckets(t, nb); return; }
    uint8_t *octrl = t->ctrl; slot_t *oslots = t->slots;
    uint64_t old_nb = t->bucket_mask + 1;
    alloc_buckets(t, nb);
    for (uint64_t base = 0; base < old_nb; base += GROUP_W) {
        uint64_t m = mask_full(vld1q_u8(&octrl[base]));
        while (m) { uint64_t i = base + LANE(m); reinsert(t, oslots[i].key, oslots[i].val); m &= m - 1; }
    }
    t->occupied = t->live;
    t->growth_left = (nb - nb / 8) - t->live;
    free(octrl); free(oslots);
}

int ctable_insert(ctable *t, uint64_t key, uint64_t val, uint64_t *old) {
    if (t->ctrl == NULL) alloc_buckets(t, GROUP_W);   /* first insert allocates */
    uint64_t h = hash_u64(key);
    uint8_t h2 = (uint8_t)(h & 0x7F);
    uint64_t idx, slot;
    if (find_or_slot(t, key, h, h2, &idx, &slot)) {
        if (old) *old = t->slots[idx].val;
        t->slots[idx].val = val;                       /* update in place */
        return 1;
    }
    if (t->ctrl[slot] == CTRL_EMPTY) {
        if (t->growth_left == 0) {
            rehash(t);
            slot = find_insert_slot(t, h);
        }
        t->growth_left--;
        t->occupied++;
    }  /* else: reusing a tombstone -- occupied/growth_left unchanged [TBL-5] */
    t->live++;
    t->slots[slot].key = key; t->slots[slot].val = val;
    set_ctrl(t, slot, h2);
    return 0;
}

int ctable_get(const ctable *t, uint64_t key, uint64_t *out) {
    if (t->ctrl == NULL) return 0;
    uint64_t h = hash_u64(key);
    uint8_t h2 = (uint8_t)(h & 0x7F);
    uint64_t mask = t->bucket_mask, pos = (h >> 7) & mask, stride = 0;
    for (;;) {
        uint8x16_t g = vld1q_u8(&t->ctrl[pos]);      /* one 16B control load */
        uint64_t mh = mask_h2(g, h2);
        while (mh) {
            uint64_t i = (pos + LANE(mh)) & mask;
            if (t->slots[i].key == key) { if (out) *out = t->slots[i].val; return 1; }
            mh &= mh - 1;
        }
        if (mask_empty(g)) return 0;
        stride += GROUP_W;
        pos = (pos + stride) & mask;
    }
}

uint64_t *ctable_get_uniq(ctable *t, uint64_t key) {
    if (t->ctrl == NULL) return NULL;
    uint64_t h = hash_u64(key);
    uint8_t h2 = (uint8_t)(h & 0x7F);
    uint64_t mask = t->bucket_mask, pos = (h >> 7) & mask, stride = 0;
    for (;;) {
        uint8x16_t g = vld1q_u8(&t->ctrl[pos]);
        uint64_t mh = mask_h2(g, h2);
        while (mh) {
            uint64_t i = (pos + LANE(mh)) & mask;
            if (t->slots[i].key == key) return &t->slots[i].val;
            mh &= mh - 1;
        }
        if (mask_empty(g)) return NULL;
        stride += GROUP_W;
        pos = (pos + stride) & mask;
    }
}

int ctable_remove(ctable *t, uint64_t key, uint64_t *old) {
    if (t->ctrl == NULL) return 0;
    uint64_t h = hash_u64(key);
    uint8_t h2 = (uint8_t)(h & 0x7F);
    uint64_t mask = t->bucket_mask, pos = (h >> 7) & mask, stride = 0;
    for (;;) {
        uint8x16_t g = vld1q_u8(&t->ctrl[pos]);
        uint64_t mh = mask_h2(g, h2);
        while (mh) {
            uint64_t i = (pos + LANE(mh)) & mask;
            if (t->slots[i].key == key) {
                if (old) *old = t->slots[i].val;
                set_ctrl(t, i, CTRL_DELETED);          /* tombstone [TBL-4] */
                t->live--;
                return 1;
            }
            mh &= mh - 1;
        }
        if (mask_empty(g)) return 0;
        stride += GROUP_W;
        pos = (pos + stride) & mask;
    }
}

uint64_t ctable_len(const ctable *t) { return t->live; }

/* CG-ITER: group-scan the control bytes (one 16B load per group), summing only
 * the live lanes -- avoids an unpredictable data-dependent branch per bucket. */
uint64_t ctable_iterate_sum(const ctable *t) {
    uint64_t acc = 0;
    if (t->ctrl == NULL) return 0;
    uint64_t nb = t->bucket_mask + 1;
    for (uint64_t base = 0; base < nb; base += GROUP_W) {
        uint64_t m = mask_full(vld1q_u8(&t->ctrl[base]));
        while (m) { acc += t->slots[base + LANE(m)].val; m &= m - 1; }
    }
    return acc;
}
