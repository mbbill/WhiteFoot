/* wc driver: reads each file into one buffer, calls the xlang kernels,
   prints GNU-format counts. Kernel ABI: buffer<u8> = {ptr, i64} by value;
   Counts returned as {i64,i64,i64}. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

typedef struct { uint8_t *p; int64_t n; } Buf;
typedef struct { uint64_t lines, words, bytes; } Counts;
extern uint64_t count_lines(Buf b);
extern void count_all(Counts *out, Buf b);

static Buf slurp(const char *path) {
  FILE *f = fopen(path, "rb");
  if (!f) { perror(path); exit(1); }
  fseek(f, 0, SEEK_END);
  long n = ftell(f);
  fseek(f, 0, SEEK_SET);
  Buf b; b.p = malloc(n ? n : 1); b.n = n;
  if (n && fread(b.p, 1, n, f) != (size_t)n) { perror(path); exit(1); }
  fclose(f);
  return b;
}

int main(int argc, char **argv) {
  int lonly = argc > 1 && strcmp(argv[1], "-l") == 0;
  int first = lonly ? 2 : 1;
  uint64_t tl = 0, tw = 0, tb = 0;
  for (int i = first; i < argc; i++) {
    Buf b = slurp(argv[i]);
    if (lonly) {
      uint64_t l = count_lines(b);
      printf("%8llu %s\n", (unsigned long long)l, argv[i]);
      tl += l;
    } else {
      Counts c; count_all(&c, b);
      printf("%8llu %7llu %7llu %s\n", (unsigned long long)c.lines,
             (unsigned long long)c.words, (unsigned long long)c.bytes, argv[i]);
      tl += c.lines; tw += c.words; tb += c.bytes;
    }
    free(b.p);
  }
  if (argc - first > 1) {
    if (lonly) printf("%8llu total\n", (unsigned long long)tl);
    else printf("%8llu %7llu %7llu total\n", (unsigned long long)tl,
                (unsigned long long)tw, (unsigned long long)tb);
  }
  return 0;
}
