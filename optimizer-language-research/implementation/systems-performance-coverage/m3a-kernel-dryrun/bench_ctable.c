/* B2/B3/B4 on ctable, same protocol as rustbench (splitmix64 streams, seeds,
 * warmup + runs, median). value = key. ns/op == ns per key. */
#include "common.h"
#include "ctable.h"

#define N 1000000
#define WARM 3
#define RUNS 21
#define INSERT_SEED 0x1234567890abcdefULL
#define MISS_SEED   0xdeadbeefcafef00dULL

static void build(ctable *t, const uint64_t *keys) {
    ctable_init(t);
    uint64_t o;
    for (long i = 0; i < N; i++) ctable_insert(t, keys[i], keys[i], &o);
}

int main(void) {
    uint64_t *ins = malloc(N * sizeof(uint64_t));
    uint64_t *miss = malloc(N * sizeof(uint64_t));
    uint64_t s1 = INSERT_SEED, s2 = MISS_SEED;
    for (long i = 0; i < N; i++) ins[i] = splitmix64(&s1);
    for (long i = 0; i < N; i++) miss[i] = splitmix64(&s2);

    double t[RUNS];
    volatile uint64_t sink = 0;

    /* B2-build: insert 1M (ns/op) */
    for (int r = 0; r < WARM + RUNS; r++) {
        ctable tb;
        double t0 = now_ns();
        build(&tb, ins);
        double t1 = now_ns();
        sink += ctable_len(&tb);
        if (r >= WARM) t[r - WARM] = (t1 - t0) / N;
        ctable_free(&tb);
    }
    printf("B2-build ctable insert (ns/op, median of %d): %.4f\n", RUNS, median(t, RUNS));

    /* B2r-diag: reserved build (no rehash) -- isolates steady-state insert. */
    for (int r = 0; r < WARM + RUNS; r++) {
        ctable tb; ctable_init(&tb); ctable_reserve(&tb, N);
        double t0 = now_ns();
        uint64_t o;
        for (long i = 0; i < N; i++) ctable_insert(&tb, ins[i], ins[i], &o);
        double t1 = now_ns();
        sink += ctable_len(&tb);
        if (r >= WARM) t[r - WARM] = (t1 - t0) / N;
        ctable_free(&tb);
    }
    printf("B2r ctable reserved-insert (ns/op, median of %d): %.4f\n", RUNS, median(t, RUNS));

    /* Build once for the read benchmarks. */
    ctable tb; build(&tb, ins);

    /* B2: 1M hit lookups */
    for (int r = 0; r < WARM + RUNS; r++) {
        double t0 = now_ns();
        uint64_t acc = 0, v;
        for (long i = 0; i < N; i++) { ctable_get(&tb, ins[i], &v); acc += v; }
        double t1 = now_ns();
        sink += acc;
        if (r >= WARM) t[r - WARM] = (t1 - t0) / N;
    }
    printf("B2 ctable hit-lookup (ns/op, median of %d): %.4f\n", RUNS, median(t, RUNS));

    /* B3: 1M miss lookups */
    for (int r = 0; r < WARM + RUNS; r++) {
        double t0 = now_ns();
        uint64_t acc = 0, v;
        for (long i = 0; i < N; i++) { if (ctable_get(&tb, miss[i], &v)) acc += v; }
        double t1 = now_ns();
        sink += acc;
        if (r >= WARM) t[r - WARM] = (t1 - t0) / N;
    }
    printf("B3 ctable miss-lookup (ns/op, median of %d): %.4f\n", RUNS, median(t, RUNS));

    /* B4: iterate-sum over 1M entries */
    for (int r = 0; r < WARM + RUNS; r++) {
        double t0 = now_ns();
        uint64_t acc = ctable_iterate_sum(&tb);
        double t1 = now_ns();
        sink += acc;
        if (r >= WARM) t[r - WARM] = (t1 - t0) / ctable_len(&tb);
    }
    printf("B4 ctable iterate-sum (ns/elem, median of %d): %.4f\n", RUNS, median(t, RUNS));

    printf("(sink=%llu)\n", (unsigned long long)sink);
    ctable_free(&tb); free(ins); free(miss);
    return 0;
}
