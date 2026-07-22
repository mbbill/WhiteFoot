#include <stdint.h>
#include <string.h>

#include "zbuild.h"
#include "inftrees.h"
#include "inffixed_tbl.h"

/*
 * Experimental lowering ceiling for a proved table-driven bit-window loop.
 * The packed load matches Whitefoot's u32 table representation.  Wide input
 * reads are guarded by the logical source length, and the scalar tail handles
 * all remaining symbol counts without relying on padding.
 */
static inline uint32_t packed_entry(uint64_t index) {
    uint32_t packed;
    memcpy(&packed, &lenfix[index], sizeof(packed));
    return packed;
}

static inline void validate_arguments(
    uint64_t src_len,
    uint64_t out_len,
    uint64_t symbol_count
) {
    if (symbol_count > UINT64_C(16397105843297379213)) {
        __builtin_trap();
    }
    uint64_t required = symbol_count + (symbol_count >> 3);
    if ((symbol_count & 7) != 0) {
        ++required;
    }
    if (src_len < required || out_len < symbol_count) {
        __builtin_trap();
    }
}

uint64_t candidate_huffman_literals(
    const uint8_t *src,
    uint64_t src_len,
    uint8_t *out,
    uint64_t out_len,
    uint64_t symbol_count
) {
    validate_arguments(src_len, out_len, symbol_count);

    uint64_t byte_position = 0;
    unsigned bit_offset = 0;
    uint64_t produced = 0;
    while (symbol_count - produced >= 6) {
        if (byte_position > src_len || src_len - byte_position < 8) {
            break;
        }
        uint64_t window;
        memcpy(&window, src + byte_position, sizeof(window));
        uint64_t hold = window >> bit_offset;
        unsigned consumed = bit_offset;

#define DECODE_LITERAL() do {                                                   \
        uint32_t entry = packed_entry(hold & 511U);                             \
        if ((entry & 255U) != 0) {                                              \
            __builtin_trap();                                                   \
        }                                                                       \
        out[produced] = (uint8_t)(entry >> 16);                                 \
        uint32_t used = (entry >> 8) & 255U;                                    \
        hold >>= used;                                                          \
        consumed += used;                                                       \
        ++produced;                                                             \
    } while (0)

        DECODE_LITERAL();
        DECODE_LITERAL();
        DECODE_LITERAL();
        DECODE_LITERAL();
        DECODE_LITERAL();
        DECODE_LITERAL();
#undef DECODE_LITERAL
        byte_position += consumed >> 3;
        bit_offset = consumed & 7;
    }

    while (produced < symbol_count) {
        uint32_t window = src[byte_position];
        window |= (uint32_t)src[byte_position + 1] << 8;
        uint32_t entry = packed_entry((window >> bit_offset) & 511U);
        if ((entry & 255U) != 0) {
            __builtin_trap();
        }
        out[produced] = (uint8_t)(entry >> 16);
        unsigned consumed = bit_offset + ((entry >> 8) & 255U);
        byte_position += consumed >> 3;
        bit_offset = consumed & 7;
        ++produced;
    }
    return produced;
}
