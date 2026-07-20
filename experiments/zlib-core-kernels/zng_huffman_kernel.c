#include <stdint.h>
#include <string.h>

#include "zbuild.h"
#include "inftrees.h"
#include "inffixed_tbl.h"

uint64_t zng_huffman_literals(
    const uint8_t *src,
    uint8_t *out,
    uint64_t symbol_count
) {
    if (symbol_count % 3 != 0) {
        __builtin_trap();
    }
    const uint8_t *in = src;
    uint64_t hold = 0;
    unsigned bits = 0;
    uint64_t produced = 0;
    while (produced < symbol_count) {
        uint64_t chunk;
        memcpy(&chunk, in, sizeof(chunk));
        hold |= chunk << bits;
        in += 7;
        in -= (bits >> 3) & 7;
        bits |= 56;

        const code *entry = lenfix + (hold & 511U);
        if (entry->op != 0) {
            __builtin_trap();
        }
        out[produced++] = (uint8_t)entry->val;
        unsigned used = entry->bits;
        hold >>= used;
        bits -= used;

        entry = lenfix + (hold & 511U);
        if (entry->op != 0) {
            __builtin_trap();
        }
        out[produced++] = (uint8_t)entry->val;
        used = entry->bits;
        hold >>= used;
        bits -= used;

        entry = lenfix + (hold & 511U);
        used = entry->bits;
        hold >>= used;
        bits -= used;
        if (entry->op != 0) {
            __builtin_trap();
        }
        out[produced++] = (uint8_t)entry->val;
    }
    return produced;
}
