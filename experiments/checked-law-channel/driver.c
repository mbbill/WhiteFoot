/* Driver for the checked-law reduction kernel: whitefoot `reduce` takes an owned
   buffer ({ptr,i64} by value: x0=ptr, x1=len on arm64) and returns u64. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>

typedef struct { uint64_t *p; int64_t n; } Buf;
extern uint64_t reduce(Buf b);

int main(int argc, char **argv) {
  int64_t n = argc > 1 ? atoll(argv[1]) : 65536;
  int64_t k = argc > 2 ? atoll(argv[2]) : 20000;
  Buf b; b.p = malloc(n * 8); b.n = n;
  for (int64_t i = 0; i < n; i++) b.p[i] = (uint64_t)i * 2654435761u;
  uint64_t sink = 0;
  for (int w = 0; w < 20; w++) sink ^= reduce(b);
  struct timespec t0, t1;
  clock_gettime(CLOCK_MONOTONIC, &t0);
  for (int64_t it = 0; it < k; it++) sink ^= reduce(b);
  clock_gettime(CLOCK_MONOTONIC, &t1);
  double ns = (t1.tv_sec - t0.tv_sec) * 1e9 + (t1.tv_nsec - t0.tv_nsec);
  printf("n=%lld k=%lld ns/elem=%.4f sink=%llu\n",
         (long long)n, (long long)k, ns / ((double)n * k), (unsigned long long)sink);
  return 0;
}
