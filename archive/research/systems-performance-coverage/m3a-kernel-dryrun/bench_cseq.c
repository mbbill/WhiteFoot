/* B1: 1M u64 push-then-sum on cseq. Median of measured runs after warmup.
 * ns/op == ns per element. Prints push, sum, and combined. */
#include "common.h"
#include "cseq.h"

#define N 1000000
#define WARM 3
#define RUNS 21

int main(void) {
    /* Fixed key stream (identical to the Rust harness). */
    uint64_t *keys = (uint64_t *)malloc(N * sizeof(uint64_t));
    uint64_t st = 0x1234567890abcdefULL;
    for (long i = 0; i < N; i++) keys[i] = splitmix64(&st);

    double push_t[RUNS], sum_t[RUNS], comb_t[RUNS];
    volatile uint64_t sink = 0;

    for (int r = 0; r < WARM + RUNS; r++) {
        cseq s = {0, 0, 0};
        double t0 = now_ns();
        for (long i = 0; i < N; i++) cseq_push(&s, keys[i]);
        double t1 = now_ns();
        uint64_t acc = cseq_sum(&s);
        double t2 = now_ns();
        sink += acc;
        if (r >= WARM) {
            push_t[r - WARM] = (t1 - t0) / N;
            sum_t[r - WARM] = (t2 - t1) / N;
            comb_t[r - WARM] = (t2 - t0) / N;
        }
        cseq_free(&s);
    }
    printf("B1 cseq push-then-sum (ns/elem, median of %d):\n", RUNS);
    printf("  push    = %.4f\n", median(push_t, RUNS));
    printf("  sum     = %.4f\n", median(sum_t, RUNS));
    printf("  combined= %.4f\n", median(comb_t, RUNS));
    printf("  (sink=%llu)\n", (unsigned long long)sink);
    free(keys);
    return 0;
}
