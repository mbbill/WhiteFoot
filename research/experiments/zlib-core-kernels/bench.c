#include <errno.h>
#include <inttypes.h>
#include <mach/mach_time.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    uint8_t *data;
    uint64_t len;
} wf_u8_buffer;

_Static_assert(sizeof(wf_u8_buffer) == 16, "Whitefoot buffer ABI size");
_Static_assert(offsetof(wf_u8_buffer, len) == 8, "Whitefoot buffer ABI length offset");

extern uint64_t inflate_match_copy(
    wf_u8_buffer out,
    uint64_t seed_len,
    uint64_t distance,
    uint64_t match_len,
    uint64_t repeats
);

extern uint64_t zng_inflate_match_copy(
    uint8_t *out,
    uint64_t out_len,
    uint64_t seed_len,
    uint64_t distance,
    uint64_t match_len,
    uint64_t repeats
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

static void initialize(uint8_t *out, uint64_t size, uint64_t seed_len) {
    memset(out, 0xa5, (size_t)size);
    uint64_t state = UINT64_C(0x9e3779b97f4a7c15);
    for (uint64_t i = 0; i < seed_len; ++i) {
        state ^= state << 7;
        state ^= state >> 9;
        state ^= state << 8;
        out[i] = (uint8_t)state;
    }
}

static int contract_case(const char *name) {
    uint8_t out[33027];
    initialize(out, sizeof(out), 4);
    if (strcmp(name, "zero-repeats") == 0) {
        return inflate_match_copy(
            (wf_u8_buffer){out, 1}, 1, 1, 3, 0
        ) == 1 ? 0 : 1;
    }
    if (strcmp(name, "exact-capacity") == 0) {
        return inflate_match_copy(
            (wf_u8_buffer){out, 7}, 4, 1, 3, 1
        ) == 7 ? 0 : 1;
    }
    if (strcmp(name, "length-below") == 0) {
        (void)inflate_match_copy(
            (wf_u8_buffer){out, sizeof(out)}, 4, 1, 2, 1
        );
        return 1;
    }
    if (strcmp(name, "length-above") == 0) {
        (void)inflate_match_copy(
            (wf_u8_buffer){out, 263}, 4, 1, 259, 1
        );
        return 1;
    }
    if (strcmp(name, "distance-zero") == 0) {
        (void)inflate_match_copy(
            (wf_u8_buffer){out, sizeof(out)}, 4, 0, 3, 1
        );
        return 1;
    }
    if (strcmp(name, "distance-above") == 0) {
        (void)inflate_match_copy(
            (wf_u8_buffer){out, 32769}, 32769, 32769, 3, 0
        );
        return 1;
    }
    if (strcmp(name, "distance-history") == 0) {
        (void)inflate_match_copy(
            (wf_u8_buffer){out, sizeof(out)}, 1, 2, 3, 0
        );
        return 1;
    }
    if (strcmp(name, "product-overflow") == 0) {
        (void)inflate_match_copy(
            (wf_u8_buffer){out, sizeof(out)},
            1,
            1,
            258,
            UINT64_MAX / 258 + 1
        );
        return 1;
    }
    if (strcmp(name, "sum-overflow") == 0) {
        (void)inflate_match_copy(
            (wf_u8_buffer){out, 32768},
            32768,
            1,
            3,
            UINT64_MAX / 3
        );
        return 1;
    }
    if (strcmp(name, "capacity-short") == 0) {
        (void)inflate_match_copy((wf_u8_buffer){out, 6}, 4, 1, 3, 1);
        return 1;
    }
    fprintf(stderr, "unknown contract case: %s\n", name);
    return 2;
}

static uint64_t reference_copy(
    uint8_t *out,
    uint64_t seed_len,
    uint64_t distance,
    uint64_t match_len,
    uint64_t repeats
) {
    uint64_t position = seed_len;
    for (uint64_t match = 0; match < repeats; ++match) {
        for (uint64_t copied = 0; copied < match_len; ++copied) {
            out[position] = out[position - distance];
            ++position;
        }
    }
    return position;
}

static uint64_t zng_copy(
    uint8_t *out,
    uint64_t out_len,
    uint64_t seed_len,
    uint64_t distance,
    uint64_t match_len,
    uint64_t repeats
) {
    return zng_inflate_match_copy(
        out, out_len, seed_len, distance, match_len, repeats
    );
}

static uint64_t digest(const uint8_t *data, uint64_t length) {
    uint64_t hash = UINT64_C(1469598103934665603);
    for (uint64_t index = 0; index < length; ++index) {
        hash ^= data[index];
        hash *= UINT64_C(1099511628211);
    }
    return hash;
}

static uint64_t ticks_to_ns(uint64_t ticks) {
    mach_timebase_info_data_t info;
    if (mach_timebase_info(&info) != KERN_SUCCESS) {
        fputs("mach_timebase_info failed\n", stderr);
        exit(2);
    }
    __uint128_t scaled = (__uint128_t)ticks * info.numer;
    return (uint64_t)(scaled / info.denom);
}

static int check_case(uint64_t distance, uint64_t match_len) {
    const uint64_t seed_len = 32768;
    const uint64_t repeats = 257;
    const uint64_t logical_size = seed_len + match_len * repeats;
    const uint64_t size = logical_size + 320;
    uint8_t *expected = malloc((size_t)size);
    uint8_t *wf = malloc((size_t)size);
    uint8_t *zng = malloc((size_t)size);
    if (expected == NULL || wf == NULL || zng == NULL) {
        fputs("allocation failed\n", stderr);
        return 2;
    }
    initialize(expected, size, seed_len);
    memcpy(wf, expected, (size_t)size);
    memcpy(zng, expected, (size_t)size);
    uint64_t expected_end = reference_copy(
        expected, seed_len, distance, match_len, repeats
    );
    uint64_t wf_end = inflate_match_copy(
        (wf_u8_buffer){wf, size}, seed_len, distance, match_len, repeats
    );
    uint64_t zng_end = zng_copy(
        zng, size, seed_len, distance, match_len, repeats
    );
    int okay = expected_end == wf_end && expected_end == zng_end &&
        memcmp(expected, wf, (size_t)expected_end) == 0 &&
        memcmp(expected, zng, (size_t)expected_end) == 0;
    free(expected);
    free(wf);
    free(zng);
    return okay ? 0 : 1;
}

static int check_all(void) {
    static const uint64_t cases[][2] = {
        {1, 3}, {1, 258}, {2, 258}, {3, 8}, {3, 258}, {4, 258},
        {8, 32}, {8, 258}, {16, 258}, {31, 64}, {31, 258},
        {64, 258}, {257, 258}, {32768, 258}
    };
    for (size_t index = 0; index < sizeof(cases) / sizeof(cases[0]); ++index) {
        int status = check_case(cases[index][0], cases[index][1]);
        if (status != 0) {
            fprintf(
                stderr,
                "correctness failed: distance=%" PRIu64 " length=%" PRIu64 "\n",
                cases[index][0],
                cases[index][1]
            );
            return status;
        }
    }
    puts("correctness: 14/14 cases passed");
    return 0;
}

int main(int argc, char **argv) {
    if (argc == 3 && strcmp(argv[1], "contract") == 0) {
        return contract_case(argv[2]);
    }
    if (argc == 2 && strcmp(argv[1], "check") == 0) {
        return check_all();
    }
    if (argc != 7) {
        fprintf(
            stderr,
            "usage: %s run {wf|zng} DISTANCE MATCH_LEN OUTPUT_BYTES PASSES\n",
            argv[0]
        );
        return 2;
    }
    if (strcmp(argv[1], "run") != 0) {
        return 2;
    }
    const char *variant = argv[2];
    uint64_t distance = parse_u64(argv[3]);
    uint64_t match_len = parse_u64(argv[4]);
    uint64_t logical_size = parse_u64(argv[5]);
    uint64_t passes = parse_u64(argv[6]);
    const uint64_t seed_len = 32768;
    if (distance == 0 || distance > seed_len || match_len == 0 ||
        match_len > 258 || logical_size <= seed_len + match_len || passes == 0 ||
        logical_size > UINT32_MAX - 320) {
        fputs("invalid workload\n", stderr);
        return 2;
    }
    uint64_t repeats = (logical_size - seed_len) / match_len;
    uint64_t produced = repeats * match_len;
    uint64_t size = logical_size + 320;
    uint8_t *out = NULL;
    if (posix_memalign((void **)&out, 64, (size_t)size) != 0) {
        fputs("allocation failed\n", stderr);
        return 2;
    }
    initialize(out, size, seed_len);
    uint64_t start = mach_continuous_time();
    uint64_t end_position = 0;
    for (uint64_t pass = 0; pass < passes; ++pass) {
        if (strcmp(variant, "wf") == 0) {
            end_position = inflate_match_copy(
                (wf_u8_buffer){out, size}, seed_len, distance, match_len, repeats
            );
        } else if (strcmp(variant, "zng") == 0) {
            end_position = zng_copy(
                out, size, seed_len, distance, match_len, repeats
            );
        } else {
            fputs("unknown variant\n", stderr);
            free(out);
            return 2;
        }
    }
    uint64_t elapsed_ns = ticks_to_ns(mach_continuous_time() - start);
    uint64_t checksum = digest(out, end_position);
    printf(
        "{\"variant\":\"%s\",\"distance\":%" PRIu64
        ",\"match_len\":%" PRIu64 ",\"produced_per_pass\":%" PRIu64
        ",\"passes\":%" PRIu64 ",\"elapsed_ns\":%" PRIu64
        ",\"digest\":\"%016" PRIx64 "\"}\n",
        variant,
        distance,
        match_len,
        produced,
        passes,
        elapsed_ns,
        checksum
    );
    free(out);
    return 0;
}
