// Opaque-boundary driver for the whitefoot scoped-alias kernel: builds the Cols
// struct ({ptr,i64} x 8), times K calls of kernel(&s), prints ns/elem and a
// checksum. Linked against kernel_{facts,nofacts}.ll with no LTO, so the
// kernel sees only its declared parameter facts -- the channel under test.
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>

typedef struct { uint64_t *p; int64_t n; } Buf;
typedef struct { Buf a, b, c, d, e, f, g, h; } Cols;
extern void kernel(Cols *s);

static Buf mk(int64_t n, uint64_t seed) {
  Buf b; b.p = malloc(n * 8); b.n = n;
  for (int64_t i = 0; i < n; i++) b.p[i] = seed + (uint64_t)i;
  return b;
}

int main(int argc, char **argv) {
  int64_t n = argc > 1 ? atoll(argv[1]) : 4096;
  int64_t k = argc > 2 ? atoll(argv[2]) : 100000;
  Cols s = { mk(n,1), mk(n,2), mk(n,3), mk(n,4), mk(n,5), mk(n,6), mk(n,7), mk(n,8) };
  for (int w = 0; w < 100; w++) kernel(&s);           /* warm */
  struct timespec t0, t1;
  clock_gettime(CLOCK_MONOTONIC, &t0);
  for (int64_t it = 0; it < k; it++) kernel(&s);
  clock_gettime(CLOCK_MONOTONIC, &t1);
  double ns = (t1.tv_sec - t0.tv_sec) * 1e9 + (t1.tv_nsec - t0.tv_nsec);
  uint64_t sum = 0;
  for (int64_t i = 0; i < n; i++) sum += s.a.p[i] ^ s.b.p[i];
  printf("n=%lld k=%lld ns/elem=%.3f checksum=%llu\n",
         (long long)n, (long long)k, ns / ((double)n * k), (unsigned long long)sum);
  return 0;
}
