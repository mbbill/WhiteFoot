#include <errno.h>
#include <inttypes.h>
#include <mach/mach_time.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef MAP_ANON
#define MAP_ANON MAP_ANONYMOUS
#endif

typedef struct {
    void *data;
    uint64_t len;
} wf_buffer;

_Static_assert(sizeof(wf_buffer) == 16, "Whitefoot buffer ABI size");
_Static_assert(offsetof(wf_buffer, len) == 8, "Whitefoot buffer ABI length offset");

extern uint64_t inflate_huffman_literals(
    wf_buffer src,
    wf_buffer out,
    uint64_t symbol_count
);

extern uint64_t zng_huffman_literals(
    const uint8_t *src,
    uint8_t *out,
    uint64_t symbol_count
);

static uint64_t parse_u64(const char *text) {
    char *end = NULL;
    errno = 0;
    unsigned long long value = strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0') {
        fprintf(stderr, "invalid integer: %s\n", text);
        exit(2);
    }
    return (uint64_t)value;
}

static unsigned reverse_bits(unsigned value, unsigned count) {
    unsigned reversed = 0;
    for (unsigned bit = 0; bit < count; ++bit) {
        reversed = (reversed << 1) | ((value >> bit) & 1U);
    }
    return reversed;
}

static void fixed_codes(unsigned *codes, unsigned *lengths) {
    unsigned counts[10] = {0};
    for (unsigned symbol = 0; symbol < 288; ++symbol) {
        unsigned length = symbol <= 143 ? 8 : symbol <= 255 ? 9 :
            symbol <= 279 ? 7 : 8;
        lengths[symbol] = length;
        ++counts[length];
    }
    unsigned next[10] = {0};
    unsigned code = 0;
    for (unsigned length = 1; length <= 9; ++length) {
        code = (code + counts[length - 1]) << 1;
        next[length] = code;
    }
    for (unsigned symbol = 0; symbol < 288; ++symbol) {
        unsigned length = lengths[symbol];
        codes[symbol] = next[length]++;
    }
}

static uint64_t write_fixed_symbol_at(
    uint8_t *src,
    uint64_t bit_position,
    unsigned symbol,
    const unsigned *codes,
    const unsigned *lengths
) {
    unsigned length = lengths[symbol];
    unsigned stream_code = reverse_bits(codes[symbol], length);
    for (unsigned bit = 0; bit < length; ++bit) {
        if ((stream_code >> bit) & 1U) {
            uint64_t position = bit_position + bit;
            src[position >> 3] |= (uint8_t)(1U << (position & 7));
        }
    }
    return bit_position + length;
}

static void write_fixed_symbol(
    uint8_t *src,
    unsigned symbol,
    const unsigned *codes,
    const unsigned *lengths
) {
    (void)write_fixed_symbol_at(src, 0, symbol, codes, lengths);
}

static int exact_guard_page_case(
    uint64_t count,
    const unsigned *codes,
    const unsigned *lengths
) {
    long page_size_value = sysconf(_SC_PAGESIZE);
    if (page_size_value <= 0) {
        return 2;
    }
    size_t page_size = (size_t)page_size_value;
    uint8_t *mapping = mmap(
        NULL,
        page_size * 2,
        PROT_READ | PROT_WRITE,
        MAP_SHARED | MAP_ANON,
        -1,
        0
    );
    if (mapping == MAP_FAILED || mprotect(
        mapping + page_size, page_size, PROT_NONE
    ) != 0) {
        return 2;
    }
    uint64_t exact_len = (9 * count + 7) >> 3;
    uint8_t *src = mapping + page_size - exact_len;
    uint8_t out[13] = {0};
    uint64_t bit_position = 0;
    for (uint64_t index = 0; index < count; ++index) {
        bit_position = write_fixed_symbol_at(
            src, bit_position, 144, codes, lengths
        );
    }
    uint64_t result = inflate_huffman_literals(
        (wf_buffer){src, exact_len}, (wf_buffer){out, count}, count
    );
    int status = result == count ? 0 : 1;
    for (uint64_t index = 0; index < count; ++index) {
        if (out[index] != 144) {
            status = 1;
        }
    }
    if (munmap(mapping, page_size * 2) != 0) {
        return 2;
    }
    return status;
}

static int nonliteral_prefix_case(
    int in_tail,
    const unsigned *codes,
    const unsigned *lengths
) {
    uint64_t count = in_tail ? 7 : 6;
    uint64_t failing_index = in_tail ? 6 : 2;
    uint8_t src[16] = {0};
    uint64_t bit_position = 0;
    for (uint64_t index = 0; index < count; ++index) {
        unsigned symbol = index == failing_index ? 256 : (unsigned)index;
        bit_position = write_fixed_symbol_at(
            src, bit_position, symbol, codes, lengths
        );
    }
    uint64_t exact_contract_len = (9 * count + 7) >> 3;
    uint64_t visible_src_len = in_tail ? exact_contract_len : sizeof(src);
    long page_size_value = sysconf(_SC_PAGESIZE);
    if (page_size_value <= 0) {
        return 2;
    }
    size_t page_size = (size_t)page_size_value;
    uint8_t *shared_out = mmap(
        NULL,
        page_size,
        PROT_READ | PROT_WRITE,
        MAP_SHARED | MAP_ANON,
        -1,
        0
    );
    if (shared_out == MAP_FAILED) {
        return 2;
    }
    memset(shared_out, 0xcc, (size_t)count);
    pid_t child = fork();
    if (child < 0) {
        (void)munmap(shared_out, page_size);
        return 2;
    }
    if (child == 0) {
        (void)inflate_huffman_literals(
            (wf_buffer){src, visible_src_len},
            (wf_buffer){shared_out, count},
            count
        );
        _exit(111);
    }
    int child_status = 0;
    if (waitpid(child, &child_status, 0) != child ||
        !WIFSIGNALED(child_status)) {
        (void)munmap(shared_out, page_size);
        return 1;
    }
    int status = 0;
    for (uint64_t index = 0; index < failing_index; ++index) {
        if (shared_out[index] != (uint8_t)index) {
            status = 1;
        }
    }
    for (uint64_t index = failing_index; index < count; ++index) {
        if (shared_out[index] != 0xcc) {
            status = 1;
        }
    }
    if (munmap(shared_out, page_size) != 0) {
        return 2;
    }
    return status;
}

static int contract_case(const char *name) {
    unsigned codes[288];
    unsigned lengths[288];
    uint8_t src[2] = {0, 0};
    uint8_t out[1] = {0};
    fixed_codes(codes, lengths);

    if (strcmp(name, "zero") == 0) {
        return inflate_huffman_literals(
            (wf_buffer){NULL, 0}, (wf_buffer){NULL, 0}, 0
        ) == 0 ? 0 : 1;
    }
    if (strcmp(name, "exact-input") == 0) {
        write_fixed_symbol(src, 144, codes, lengths);
        uint64_t result = inflate_huffman_literals(
            (wf_buffer){src, 2}, (wf_buffer){out, 1}, 1
        );
        return result == 1 && out[0] == 144 ? 0 : 1;
    }
    if (strcmp(name, "exact-bulk") == 0 ||
        strcmp(name, "exact-bulk-tail") == 0) {
        uint64_t count = strcmp(name, "exact-bulk") == 0 ? 12 : 13;
        uint8_t exact_src[15] = {0};
        uint8_t exact_out[13] = {0};
        uint64_t bit_position = 0;
        for (uint64_t index = 0; index < count; ++index) {
            bit_position = write_fixed_symbol_at(
                exact_src, bit_position, 144, codes, lengths
            );
        }
        uint64_t exact_len = (bit_position + 7) >> 3;
        uint64_t result = inflate_huffman_literals(
            (wf_buffer){exact_src, exact_len},
            (wf_buffer){exact_out, count},
            count
        );
        for (uint64_t index = 0; index < count; ++index) {
            if (exact_out[index] != 144) {
                return 1;
            }
        }
        return result == count ? 0 : 1;
    }
    if (strcmp(name, "guard-page-bulk") == 0) {
        return exact_guard_page_case(12, codes, lengths);
    }
    if (strcmp(name, "guard-page-bulk-tail") == 0) {
        return exact_guard_page_case(13, codes, lengths);
    }
    if (strcmp(name, "nonliteral-bulk-prefix") == 0) {
        return nonliteral_prefix_case(0, codes, lengths);
    }
    if (strcmp(name, "nonliteral-tail-prefix") == 0) {
        return nonliteral_prefix_case(1, codes, lengths);
    }
    if (strcmp(name, "short-input") == 0) {
        write_fixed_symbol(src, 144, codes, lengths);
        (void)inflate_huffman_literals(
            (wf_buffer){src, 1}, (wf_buffer){out, 1}, 1
        );
        return 1;
    }
    if (strcmp(name, "short-output") == 0) {
        write_fixed_symbol(src, 144, codes, lengths);
        (void)inflate_huffman_literals(
            (wf_buffer){src, 2}, (wf_buffer){out, 0}, 1
        );
        return 1;
    }
    if (strcmp(name, "nonliteral") == 0) {
        write_fixed_symbol(src, 256, codes, lengths);
        (void)inflate_huffman_literals(
            (wf_buffer){src, 2}, (wf_buffer){out, 1}, 1
        );
        return 1;
    }
    if (strcmp(name, "count-overflow") == 0) {
        (void)inflate_huffman_literals(
            (wf_buffer){src, sizeof(src)},
            (wf_buffer){out, sizeof(out)},
            UINT64_C(16397105843297379214)
        );
        return 1;
    }
    fprintf(stderr, "unknown contract case: %s\n", name);
    return 2;
}

static uint64_t make_stream(
    uint8_t *src,
    uint8_t *expected,
    uint64_t count,
    const unsigned *codes,
    const unsigned *lengths
) {
    memset(src, 0, (size_t)(count * 2 + 16));
    uint64_t bit_position = 0;
    uint64_t state = UINT64_C(0xd1b54a32d192ed03);
    for (uint64_t index = 0; index < count; ++index) {
        state ^= state << 7;
        state ^= state >> 9;
        state ^= state << 8;
        unsigned symbol = (unsigned)(state & 255U);
        expected[index] = (uint8_t)symbol;
        unsigned length = lengths[symbol];
        unsigned stream_code = reverse_bits(codes[symbol], length);
        for (unsigned bit = 0; bit < length; ++bit) {
            if ((stream_code >> bit) & 1U) {
                src[bit_position >> 3] |= (uint8_t)(1U << (bit_position & 7));
            }
            ++bit_position;
        }
    }
    return (bit_position + 7) >> 3;
}

static uint64_t ticks_to_ns(uint64_t ticks) {
    mach_timebase_info_data_t info;
    if (mach_timebase_info(&info) != KERN_SUCCESS) {
        exit(2);
    }
    return (uint64_t)((__uint128_t)ticks * info.numer / info.denom);
}

static uint64_t digest(const uint8_t *data, uint64_t length) {
    uint64_t hash = UINT64_C(1469598103934665603);
    for (uint64_t index = 0; index < length; ++index) {
        hash ^= data[index];
        hash *= UINT64_C(1099511628211);
    }
    return hash;
}

int main(int argc, char **argv) {
    if (argc == 3 && strcmp(argv[1], "contract") == 0) {
        return contract_case(argv[2]);
    }
    if (argc != 5 || strcmp(argv[1], "run") != 0) {
        fprintf(
            stderr,
            "usage: %s {run {wf|zng} SYMBOLS PASSES|contract CASE}\n",
            argv[0]
        );
        return 2;
    }
    const char *variant = argv[2];
    uint64_t count = parse_u64(argv[3]);
    uint64_t passes = parse_u64(argv[4]);
    if (count == 0 || passes == 0 || count > UINT32_MAX / 2) {
        return 2;
    }
    unsigned codes[288];
    unsigned lengths[288];
    uint64_t src_capacity = count * 2 + 16;
    uint8_t *src = malloc((size_t)src_capacity);
    uint8_t *expected = malloc((size_t)count);
    uint8_t *out = malloc((size_t)count);
    if (src == NULL || expected == NULL || out == NULL) {
        return 2;
    }
    memset(out, 0, (size_t)count);
    fixed_codes(codes, lengths);
    uint64_t src_len = make_stream(src, expected, count, codes, lengths);
    uint64_t result = 0;
    if (strcmp(variant, "wf") == 0) {
        result = inflate_huffman_literals(
            (wf_buffer){src, src_capacity},
            (wf_buffer){out, count},
            count
        );
    } else if (strcmp(variant, "zng") == 0) {
        result = zng_huffman_literals(src, out, count);
    } else {
        return 2;
    }
    if (result != count || memcmp(out, expected, (size_t)count) != 0) {
        fputs("correctness failed\n", stderr);
        return 1;
    }
    uint64_t start = mach_continuous_time();
    for (uint64_t pass = 0; pass < passes; ++pass) {
        if (strcmp(variant, "wf") == 0) {
            result = inflate_huffman_literals(
                (wf_buffer){src, src_capacity},
                (wf_buffer){out, count},
                count
            );
        } else {
            result = zng_huffman_literals(src, out, count);
        }
    }
    uint64_t elapsed_ns = ticks_to_ns(mach_continuous_time() - start);
    printf(
        "{\"variant\":\"%s\",\"symbols\":%" PRIu64
        ",\"compressed_bytes\":%" PRIu64 ",\"passes\":%" PRIu64
        ",\"elapsed_ns\":%" PRIu64 ",\"digest\":\"%016" PRIx64 "\"}\n",
        variant,
        count,
        src_len,
        passes,
        elapsed_ns,
        digest(out, result)
    );
    free(src);
    free(expected);
    free(out);
    return 0;
}
