#include <arm_neon.h>
#include <stdint.h>
#include <string.h>

/*
 * Experimental lowering ceiling for a proved periodic forward copy.
 *
 * This is intentionally not a new Whitefoot source form.  It models code a
 * backend could emit after proving the recurrence out[p] = out[p - distance].
 * Every load reads initialized history and every store stays within the exact
 * match length; unlike the zlib-ng helper, it assumes no writable padding.
 */
static inline uint8_t *copy_scalar(
    uint8_t *out,
    uint64_t distance,
    uint64_t length
) {
    for (uint64_t copied = 0; copied < length; ++copied) {
        out[copied] = *(out - distance + copied);
    }
    return out + length;
}

static const uint8_t period_indices[14][16] __attribute__((aligned(16))) = {
    {14, 15, 14, 15, 14, 15, 14, 15, 14, 15, 14, 15, 14, 15, 14, 15},
    {13, 14, 15, 13, 14, 15, 13, 14, 15, 13, 14, 15, 13, 14, 15, 13},
    {12, 13, 14, 15, 12, 13, 14, 15, 12, 13, 14, 15, 12, 13, 14, 15},
    {11, 12, 13, 14, 15, 11, 12, 13, 14, 15, 11, 12, 13, 14, 15, 11},
    {10, 11, 12, 13, 14, 15, 10, 11, 12, 13, 14, 15, 10, 11, 12, 13},
    {9, 10, 11, 12, 13, 14, 15, 9, 10, 11, 12, 13, 14, 15, 9, 10},
    {8, 9, 10, 11, 12, 13, 14, 15, 8, 9, 10, 11, 12, 13, 14, 15},
    {7, 8, 9, 10, 11, 12, 13, 14, 15, 7, 8, 9, 10, 11, 12, 13},
    {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 6, 7, 8, 9, 10, 11},
    {5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 5, 6, 7, 8, 9},
    {4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 4, 5, 6, 7},
    {3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 3, 4, 5},
    {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 2, 3},
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 1},
};

static inline uint8x16_t make_period_chunk(
    const uint8_t *out,
    uint64_t distance
) {
    if (distance == 2) {
        uint16_t value;
        memcpy(&value, out - 2, sizeof(value));
        return vreinterpretq_u8_u16(vdupq_n_u16(value));
    }
    if (distance == 4) {
        uint32_t value;
        memcpy(&value, out - 4, sizeof(value));
        return vreinterpretq_u8_u32(vdupq_n_u32(value));
    }
    if (distance == 16) {
        return vld1q_u8(out - 16);
    }
    uint8x16_t initialized_history = vld1q_u8(out - 16);
    uint8x16_t indices = vld1q_u8(period_indices[distance - 2]);
    return vqtbl1q_u8(initialized_history, indices);
}

static inline uint8_t *copy_short_period(
    uint8_t *out,
    uint64_t distance,
    uint64_t length
) {
    uint8x16_t chunk = make_period_chunk(out, distance);
    uint64_t advance = 16 - (16 % distance);

    while (length >= 64) {
        vst1q_u8(out, chunk);
        vst1q_u8(out + advance, chunk);
        vst1q_u8(out + 2 * advance, chunk);
        vst1q_u8(out + 3 * advance, chunk);
        out += 4 * advance;
        length -= 4 * advance;
    }
    while (length >= 32) {
        vst1q_u8(out, chunk);
        vst1q_u8(out + advance, chunk);
        out += 2 * advance;
        length -= 2 * advance;
    }
    while (length >= 16) {
        vst1q_u8(out, chunk);
        out += advance;
        length -= advance;
    }
    for (uint64_t copied = 0; copied < length; ++copied) {
        out[copied] = vgetq_lane_u8(chunk, 0);
        chunk = vextq_u8(chunk, chunk, 1);
    }
    return out + length;
}

static inline uint8_t *copy_medium_period(
    uint8_t *out,
    uint64_t distance,
    uint64_t length
) {
    static const uint8_t lane_numbers[16] __attribute__((aligned(16))) = {
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
    };
    uint8x16_t first = vld1q_u8(out - distance);
    uint8x16x2_t sources;
    sources.val[0] = vld1q_u8(out - 16);
    sources.val[1] = first;
    uint8x16_t indices = vaddq_u8(
        vld1q_u8(lane_numbers),
        vdupq_n_u8((uint8_t)(32 - distance))
    );
    uint8x16_t second = vqtbl2q_u8(sources, indices);

    while (length >= 64) {
        vst1q_u8(out, first);
        vst1q_u8(out + 16, second);
        vst1q_u8(out + distance, first);
        vst1q_u8(out + distance + 16, second);
        out += 2 * distance;
        length -= 2 * distance;
    }
    while (length >= 32) {
        vst1q_u8(out, first);
        vst1q_u8(out + 16, second);
        out += distance;
        length -= distance;
    }

    uint8x16_t tail = first;
    if (length >= 16) {
        vst1q_u8(out, first);
        out += 16;
        length -= 16;
        tail = second;
    }
    for (uint64_t copied = 0; copied < length; ++copied) {
        out[copied] = vgetq_lane_u8(tail, 0);
        tail = vextq_u8(tail, tail, 1);
    }
    return out + length;
}

static inline uint8_t *copy_separated(
    uint8_t *out,
    uint64_t distance,
    uint64_t length
) {
    while (distance >= 64 && length >= 64) {
        const uint8_t *from = out - distance;
        uint8x16_t a = vld1q_u8(from);
        uint8x16_t b = vld1q_u8(from + 16);
        uint8x16_t c = vld1q_u8(from + 32);
        uint8x16_t d = vld1q_u8(from + 48);
        vst1q_u8(out, a);
        vst1q_u8(out + 16, b);
        vst1q_u8(out + 32, c);
        vst1q_u8(out + 48, d);
        out += 64;
        length -= 64;
    }
    while (length >= 16) {
        uint8x16_t chunk = vld1q_u8(out - distance);
        vst1q_u8(out, chunk);
        out += 16;
        length -= 16;
    }
    return copy_scalar(out, distance, length);
}

uint64_t candidate_inflate_match_copy(
    uint8_t *out,
    uint64_t out_len,
    uint64_t seed_len,
    uint64_t distance,
    uint64_t match_len,
    uint64_t repeats
) {
    if (distance == 0 || distance > seed_len || distance > 32768 ||
        match_len < 3 || match_len > 258 ||
        repeats > (UINT64_MAX - seed_len) / match_len ||
        seed_len + repeats * match_len > out_len) {
        __builtin_trap();
    }

    uint8_t *next = out + seed_len;
    if (match_len <= 8) {
        for (uint64_t match = 0; match < repeats; ++match) {
            next = copy_scalar(next, distance, match_len);
        }
    } else if (distance == 1) {
        uint8_t value = next[-1];
        for (uint64_t match = 0; match < repeats; ++match) {
            memset(next, value, (size_t)match_len);
            next += match_len;
        }
    } else if ((distance <= 16 && seed_len < 16) ||
               (distance >= 24 && distance < 32 && seed_len < 32)) {
        for (uint64_t match = 0; match < repeats; ++match) {
            next = copy_scalar(next, distance, match_len);
        }
    } else if (distance <= 16) {
        for (uint64_t match = 0; match < repeats; ++match) {
            next = copy_short_period(next, distance, match_len);
        }
    } else if (distance >= 24 && distance < 32) {
        for (uint64_t match = 0; match < repeats; ++match) {
            next = copy_medium_period(next, distance, match_len);
        }
    } else {
        for (uint64_t match = 0; match < repeats; ++match) {
            next = copy_separated(next, distance, match_len);
        }
    }
    return (uint64_t)(next - out);
}
