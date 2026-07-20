#include <stdint.h>

/* Compile zlib-ng 2.3.3's real ARM NEON fast-path helpers in this translation unit. */
#include "arch/arm/chunkset_neon.c"

uint64_t zng_inflate_match_copy(
    uint8_t *out,
    uint64_t out_len,
    uint64_t seed_len,
    uint64_t distance,
    uint64_t match_len,
    uint64_t repeats
) {
    uint8_t *next = out + seed_len;
    uint8_t *safe = out + out_len;
    for (uint64_t match = 0; match < repeats; ++match) {
        if (distance >= match_len || distance >= CHUNKSIZE()) {
            next = CHUNKCOPY(next, next - distance, (unsigned)match_len);
        } else {
            next = CHUNKMEMSET(next, next - distance, (unsigned)match_len);
        }
        if (next + 258 > safe) {
            __builtin_trap();
        }
    }
    return (uint64_t)(next - out);
}
