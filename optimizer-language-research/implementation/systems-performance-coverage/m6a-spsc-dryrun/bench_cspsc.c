/* Part B benchmarks for cspsc: concurrent correctness, cross-core round-trip
 * latency (ping-pong through two queues), and batched-32 throughput.
 * Indicative (Apple M4; macOS gives no easy core pinning -- threads land on
 * whatever cores the scheduler picks, noted in the report). */
#include "cspsc.h"
#include <pthread.h>
#include <stdio.h>
#include <time.h>
#include <string.h>
#include <stdlib.h>
#include <pthread/qos.h>

/* Hint the scheduler to keep both endpoints on performance cores (same cluster)
 * -- macOS has no hard core pinning; this is a QoS hint. */
static void want_pcore(void) { pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0); }
static pthread_t spawn_pcore(void *(*fn)(void *), void *arg) {
    pthread_attr_t a; pthread_attr_init(&a);
    pthread_attr_set_qos_class_np(&a, QOS_CLASS_USER_INTERACTIVE, 0);
    pthread_t th; pthread_create(&th, &a, fn, arg);
    pthread_attr_destroy(&a);
    return th;
}

static inline double now_ns(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec * 1e9 + (double)t.tv_nsec;
}
static inline void spin_send(cspsc *q, uint64_t v) { while (!cspsc_try_send(q, v)) {} }
static inline uint64_t spin_recv(cspsc *q) { uint64_t v; while (!cspsc_try_recv(q, &v)) {} return v; }
static int cmp_d(const void *a, const void *b){ double x=*(const double*)a,y=*(const double*)b; return (x>y)-(x<y);}
static double median(double *v,int n){ qsort(v,n,sizeof(double),cmp_d); return n&1?v[n/2]:0.5*(v[n/2-1]+v[n/2]); }

#define STOP UINT64_MAX

/* ---------- concurrent correctness ---------- */
typedef struct { cspsc *q; uint64_t n; uint64_t sum; int ok; } corr_arg;
static void *corr_consumer(void *a) {
    corr_arg *c = (corr_arg *)a;
    uint64_t expect = 0, sum = 0; int ok = 1;
    for (uint64_t i = 0; i < c->n; i++) {
        uint64_t v = spin_recv(c->q);
        if (v != expect) ok = 0;         /* FIFO: strictly increasing by 1 */
        expect++; sum += v;
    }
    c->sum = sum; c->ok = ok;
    return NULL;
}
static int correctness(uint64_t n) {
    cspsc *q = cspsc_new(1024);
    corr_arg ca = { q, n, 0, 0 };
    pthread_t th; pthread_create(&th, NULL, corr_consumer, &ca);
    for (uint64_t i = 0; i < n; i++) spin_send(q, i);
    pthread_join(th, NULL);
    uint64_t exp_sum = (n & 1) ? (n / 2) * (n - 1) + (n - 1) : (n / 2) * (n - 1);
    /* n*(n-1)/2 */
    exp_sum = n ? (uint64_t)((__uint128_t)n * (n - 1) / 2) : 0;
    int ok = ca.ok && ca.sum == exp_sum;
    printf("correctness: %llu items FIFO in-order, sum %s (%llu)\n",
           (unsigned long long)n, ok ? "OK" : "MISMATCH", (unsigned long long)ca.sum);
    cspsc_free(q);
    return ok;
}

/* ---------- round-trip latency ---------- */
typedef struct { cspsc *in; cspsc *out; } pp_arg;
static void *pp_worker(void *a) {
    pp_arg *p = (pp_arg *)a;
    for (;;) { uint64_t v = spin_recv(p->in); if (v == STOP) break; spin_send(p->out, v); }
    return NULL;
}
static void latency(void) {
    want_pcore();
    cspsc *q1 = cspsc_new(64), *q2 = cspsc_new(64);
    pp_arg pa = { q1, q2 };
    pthread_t th; th = spawn_pcore(pp_worker, &pa);
    for (int i = 0; i < 200000; i++) { spin_send(q1, i); (void)spin_recv(q2); }  /* warmup */
    const int RUNS = 21, N = 200000;
    double oneway[RUNS];
    for (int r = 0; r < RUNS; r++) {
        double t0 = now_ns();
        for (int i = 0; i < N; i++) { spin_send(q1, (uint64_t)i); (void)spin_recv(q2); }
        double t1 = now_ns();
        oneway[r] = (t1 - t0) / N / 2.0;   /* two hops per round trip */
    }
    spin_send(q1, STOP); pthread_join(th, NULL);
    printf("round-trip latency: %.2f ns each way (median of %d; band 6-15ns)\n",
           median(oneway, RUNS), RUNS);
    cspsc_free(q1); cspsc_free(q2);
}

/* ---------- batched-32 throughput ---------- */
typedef struct { cspsc *q; uint64_t total; } thr_arg;
static void *thr_consumer(void *a) {
    thr_arg *c = (thr_arg *)a;
    uint64_t got = 0, buf[32], sink = 0;
    while (got < c->total) {
        uint64_t k = cspsc_recv_batch(c->q, buf, 32);
        for (uint64_t i = 0; i < k; i++) sink += buf[i];
        got += k;
    }
    c->q->cached_tail ^= (sink & 0);   /* keep sink live */
    return NULL;
}
static void throughput(void) {
    const uint64_t TOTAL = 200ull * 1000 * 1000;   /* 200M items */
    cspsc *q = cspsc_new(8192);
    thr_arg ca = { q, TOTAL };
    uint64_t src[32]; for (int i = 0; i < 32; i++) src[i] = (uint64_t)i;
    /* warmup */
    thr_arg wca = { q, 5ull * 1000 * 1000 };
    pthread_t wth; pthread_create(&wth, NULL, thr_consumer, &wca);
    for (uint64_t sent = 0; sent < wca.total; ) { uint64_t k = cspsc_send_batch(q, src, 32); sent += k; }
    pthread_join(wth, NULL);
    /* measured */
    pthread_t th; pthread_create(&th, NULL, thr_consumer, &ca);
    double t0 = now_ns();
    for (uint64_t sent = 0; sent < TOTAL; ) { uint64_t k = cspsc_send_batch(q, src, 32); sent += k; }
    pthread_join(th, NULL);
    double t1 = now_ns();
    double items_per_s = TOTAL / ((t1 - t0) / 1e9);
    printf("batched-32 throughput: %.1f M items/s (band >= 80M)\n", items_per_s / 1e6);
    cspsc_free(q);
}

int main(void) {
    if (!correctness(50ull * 1000 * 1000)) { fprintf(stderr, "CORRECTNESS FAILED\n"); return 1; }
    latency();
    throughput();
    return 0;
}
