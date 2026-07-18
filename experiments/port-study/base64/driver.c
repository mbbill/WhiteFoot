/* base64 driver: reads a file, calls the whitefoot encode kernel, writes the
   base64 output. Kernel ABI: encode(&uniq buffer<u8> out, own buffer<u8> src)
   -> u64 length. buffer<u8> = {ptr,i64} by value. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

typedef struct { uint8_t *p; int64_t n; } Buf;
extern uint64_t encode(Buf out, Buf src);

int main(int argc, char **argv) {
  FILE *f = fopen(argv[1], "rb");
  if (!f) { perror(argv[1]); return 1; }
  fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
  Buf src; src.p = malloc(n ? n : 1); src.n = n;
  if (n && fread(src.p, 1, n, f) != (size_t)n) { perror("read"); return 1; }
  fclose(f);
  Buf out; out.n = ((n + 2) / 3) * 4 + 16; out.p = malloc(out.n);
  uint64_t len = encode(out, src);
  fwrite(out.p, 1, len, stdout);
  fputc('\n', stdout);
  return 0;
}
