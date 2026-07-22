#include "cmemchr.h"
#include <arm_neon.h>

/* First matching lane in a compare vector (0xFF in matching byte lanes), or -1.
   shrn-by-4 gives a 4-bit-per-lane 64-bit mask (the standard NEON movemask). */
static inline int first_lane(uint8x16_t cmp) {
    uint8x8_t narrowed = vshrn_n_u16(vreinterpretq_u16_u8(cmp), 4);
    uint64_t mask = vget_lane_u64(vreinterpret_u64_u8(narrowed), 0);
    if (mask == 0) return -1;
    return (int)(__builtin_ctzll(mask) >> 2);
}

/* Precise position within a hit 64B block (rare path; off the hot loop). */
static inline const uint8_t *locate4(const uint8_t *p, uint8x16_t m0,
                                     uint8x16_t m1, uint8x16_t m2, uint8x16_t m3) {
    int l;
    if ((l = first_lane(m0)) >= 0) return p + l;
    if ((l = first_lane(m1)) >= 0) return p + 16 + l;
    if ((l = first_lane(m2)) >= 0) return p + 32 + l;
    l = first_lane(m3); return p + 48 + l;
}

/* (a) UNCHECKED reference shape: 64B/step (4x16 unroll, combined reduce) — the
   memchr-crate mechanism — then a 16B stride, then scalar tail. Raw loads. */
const uint8_t *cmemchr_unchecked(const uint8_t *s, size_t len, uint8_t needle) {
    uint8x16_t nvec = vdupq_n_u8(needle);
    size_t i = 0;
    if (len >= 64) {
        size_t limit = len - 64;
        for (; i <= limit; i += 64) {
            uint8x16_t m0 = vceqq_u8(vld1q_u8(s + i), nvec);
            uint8x16_t m1 = vceqq_u8(vld1q_u8(s + i + 16), nvec);
            uint8x16_t m2 = vceqq_u8(vld1q_u8(s + i + 32), nvec);
            uint8x16_t m3 = vceqq_u8(vld1q_u8(s + i + 48), nvec);
            uint8x16_t any = vorrq_u8(vorrq_u8(m0, m1), vorrq_u8(m2, m3));
            if (vmaxvq_u8(any) != 0) return locate4(s + i, m0, m1, m2, m3);
        }
    }
    if (len >= 16) {
        size_t limit = len - 16;
        for (; i <= limit; i += 16) {
            int lane = first_lane(vceqq_u8(vld1q_u8(s + i), nvec));
            if (lane >= 0) return s + i + lane;
        }
    }
    for (; i < len; i++) if (s[i] == needle) return s + i;
    return (const uint8_t *)0;
}

/* (b) BOUNDS-MODELED: the DOM-1 non-wrapping window predicate before each block,
   loop-invariant so the optimizer can discharge it. The 64B window fact
   `len >= 64 AND i <= len - 64` dominates all four 16B loads (i+48 <= len-16). */
const uint8_t *cmemchr_modeled(const uint8_t *s, size_t len, uint8_t needle) {
    uint8x16_t nvec = vdupq_n_u8(needle);
    size_t i = 0;
    if (len >= 64) {
        size_t limit = len - 64;
        for (; i <= limit; i += 64) {
            if (__builtin_expect(!((len >= 64) && (i <= len - 64)), 0))
                __builtin_trap();
            uint8x16_t m0 = vceqq_u8(vld1q_u8(s + i), nvec);
            uint8x16_t m1 = vceqq_u8(vld1q_u8(s + i + 16), nvec);
            uint8x16_t m2 = vceqq_u8(vld1q_u8(s + i + 32), nvec);
            uint8x16_t m3 = vceqq_u8(vld1q_u8(s + i + 48), nvec);
            uint8x16_t any = vorrq_u8(vorrq_u8(m0, m1), vorrq_u8(m2, m3));
            if (vmaxvq_u8(any) != 0) return locate4(s + i, m0, m1, m2, m3);
        }
    }
    if (len >= 16) {
        size_t limit = len - 16;
        for (; i <= limit; i += 16) {
            if (__builtin_expect(!((len >= 16) && (i <= len - 16)), 0))
                __builtin_trap();
            int lane = first_lane(vceqq_u8(vld1q_u8(s + i), nvec));
            if (lane >= 0) return s + i + lane;
        }
    }
    for (; i < len; i++) {
        if (__builtin_expect(!(i < len), 0)) __builtin_trap();
        if (s[i] == needle) return s + i;
    }
    return (const uint8_t *)0;
}

/* (b-naive) DIAGNOSTIC: an opaque per-16B-access bound (volatile len defeats
   range analysis) — models a check DOM-1 did NOT discharge; four per 64B step. */
const uint8_t *cmemchr_checked_naive(const uint8_t *s, size_t len, uint8_t needle) {
    uint8x16_t nvec = vdupq_n_u8(needle);
    volatile size_t vlen = len;
    size_t i = 0;
    if (len >= 64) {
        size_t limit = len - 64;
        for (; i <= limit; i += 64) {
            size_t l = vlen;
            if (!((l >= 16) && (i +  0 <= l - 16))) __builtin_trap();
            if (!((l >= 16) && (i + 16 <= l - 16))) __builtin_trap();
            if (!((l >= 16) && (i + 32 <= l - 16))) __builtin_trap();
            if (!((l >= 16) && (i + 48 <= l - 16))) __builtin_trap();
            uint8x16_t m0 = vceqq_u8(vld1q_u8(s + i), nvec);
            uint8x16_t m1 = vceqq_u8(vld1q_u8(s + i + 16), nvec);
            uint8x16_t m2 = vceqq_u8(vld1q_u8(s + i + 32), nvec);
            uint8x16_t m3 = vceqq_u8(vld1q_u8(s + i + 48), nvec);
            uint8x16_t any = vorrq_u8(vorrq_u8(m0, m1), vorrq_u8(m2, m3));
            if (vmaxvq_u8(any) != 0) return locate4(s + i, m0, m1, m2, m3);
        }
    }
    if (len >= 16) {
        size_t limit = len - 16;
        for (; i <= limit; i += 16) {
            int lane = first_lane(vceqq_u8(vld1q_u8(s + i), nvec));
            if (lane >= 0) return s + i + lane;
        }
    }
    for (; i < len; i++) if (s[i] == needle) return s + i;
    return (const uint8_t *)0;
}
