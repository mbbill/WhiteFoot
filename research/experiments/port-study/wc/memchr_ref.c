/* local speed-of-light reference for the -l path: whole-file memchr loop */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc, char **argv) {
  FILE *f = fopen(argv[1], "rb");
  fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
  char *p = malloc(n); fread(p, 1, n, f); fclose(f);
  long lines = 0; char *q = p, *end = p + n;
  while ((q = memchr(q, '\n', end - q))) { lines++; q++; }
  printf("%ld\n", lines);
  return 0;
}
