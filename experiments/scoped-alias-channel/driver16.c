#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
typedef struct { uint64_t *p; int64_t n; } Buf;
typedef struct { Buf c0, c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14, c15; } Wide;
extern void kernel(Wide *s);
static Buf mk(int64_t n, uint64_t seed) {
  Buf b; b.p = malloc(n * 8); b.n = n;
  for (int64_t i = 0; i < n; i++) b.p[i] = seed + (uint64_t)i;
  return b;
}
int main(int argc, char **argv) {
  int64_t n = argc > 1 ? atoll(argv[1]) : 4096;
  int64_t k = argc > 2 ? atoll(argv[2]) : 20000;
  Wide s = { mk(n,1), mk(n,2), mk(n,3), mk(n,4), mk(n,5), mk(n,6), mk(n,7), mk(n,8), mk(n,9), mk(n,10), mk(n,11), mk(n,12), mk(n,13), mk(n,14), mk(n,15), mk(n,16) };
  for (int w = 0; w < 50; w++) kernel(&s);
  struct timespec t0, t1;
  clock_gettime(CLOCK_MONOTONIC, &t0);
  for (int64_t it = 0; it < k; it++) kernel(&s);
  clock_gettime(CLOCK_MONOTONIC, &t1);
  double ns = (t1.tv_sec - t0.tv_sec) * 1e9 + (t1.tv_nsec - t0.tv_nsec);
  uint64_t sum = 0;
  for (int64_t i = 0; i < n; i++) sum += s.c0.p[i] ^ s.c3.p[i];
  printf("n=%lld k=%lld ns/elem=%.3f checksum=%llu\n",
         (long long)n, (long long)k, ns / ((double)n * k), (unsigned long long)sum);
  return 0;
}
