#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>

typedef struct {
  uint8_t *p;
  int64_t n;
} Buf;

typedef uint64_t (*decode_fn)(Buf, Buf);

extern uint64_t xlang_decode_facts(Buf out, Buf src);
extern uint64_t xlang_decode_nofacts(Buf out, Buf src);

enum check_result {
  CHECK_OK = 0,
  CHECK_CANDIDATE_FAILURE = 1,
  CHECK_HARNESS_FAILURE = 2,
};

static void print_bytes(const uint8_t *bytes, size_t len) {
  for (size_t i = 0; i < len; ++i) {
    fprintf(stderr, "%02x", bytes[i]);
  }
}

static int hex_value(uint8_t byte) {
  if (byte >= '0' && byte <= '9') {
    return byte - '0';
  }
  if (byte >= 'A' && byte <= 'F') {
    return byte - 'A' + 10;
  }
  if (byte >= 'a' && byte <= 'f') {
    return byte - 'a' + 10;
  }
  return -1;
}

static size_t oracle_decode(uint8_t *out, const uint8_t *src, size_t len) {
  size_t input = 0;
  size_t output = 0;
  while (input < len) {
    if (src[input] == '%' && input + 2 < len) {
      int high = hex_value(src[input + 1]);
      int low = hex_value(src[input + 2]);
      if (high >= 0 && low >= 0) {
        out[output++] = (uint8_t)((high << 4) | low);
        input += 3;
        continue;
      }
    }
    out[output++] = src[input++];
  }
  return output;
}

static int harness_failure(const char *operation) {
  fprintf(stderr, "HARNESS: capacity subprocess %s failed\n", operation);
  return CHECK_HARNESS_FAILURE;
}

static void print_actual_termination(int status) {
  if (WIFSIGNALED(status)) {
    fprintf(stderr, "signal-%d", WTERMSIG(status));
  } else if (WIFEXITED(status)) {
    fprintf(stderr, "exit-%d", WEXITSTATUS(status));
  } else {
    fprintf(stderr, "unknown-process-status");
  }
}

static int run_child(const char *decoder_name, decode_fn decode,
                     unsigned case_index, const uint8_t *src_data,
                     int64_t src_len, int64_t out_len, int expect_success) {
  const size_t output_storage_len = 4096;
  const size_t source_storage_len = 4096;
  const size_t control_storage_len = 4096;
  const size_t mapping_len =
      output_storage_len + source_storage_len + control_storage_len;
  uint8_t expected_output[16];
  uint8_t actual_prefix[16];
  if (src_len < 0 || (size_t)src_len > sizeof(expected_output)) {
    return harness_failure("locked source size");
  }
  size_t expected_len =
      oracle_decode(expected_output, src_data, (size_t)src_len);
  uint8_t *storage = mmap(NULL, mapping_len, PROT_READ | PROT_WRITE,
                          MAP_SHARED | MAP_ANON, -1, 0);
  if (storage == MAP_FAILED) {
    return harness_failure("mmap");
  }
  uint8_t *out = storage + 32;
  uint8_t *source = storage + output_storage_len;
  uint8_t *control = source + source_storage_len;
  uint64_t *returned = (uint64_t *)control;
  uint8_t *returned_set = control + sizeof(*returned);
  memset(storage, 0xA5, output_storage_len);
  memset(source, 0x5A, source_storage_len);
  memset(control, 0, control_storage_len);
  memcpy(source, src_data, (size_t)src_len);
  pid_t child = fork();
  if (child < 0) {
    (void)munmap(storage, mapping_len);
    return harness_failure("fork");
  }
  if (child == 0) {
    Buf src = {source, src_len};
    Buf output = {out, out_len};
    *returned = decode(output, src);
    *returned_set = 1;
    _exit(expect_success ? 0 : 99);
  }
  int status = 0;
  pid_t waited;
  do {
    waited = waitpid(child, &status, 0);
  } while (waited < 0 && errno == EINTR);
  if (waited != child) {
    (void)munmap(storage, mapping_len);
    return harness_failure("waitpid");
  }

  int sentinel_unchanged = 1;
  int source_unchanged = 1;
  int prefix_matches = 1;
  int returned_matches = 1;
  uint64_t returned_value = *returned;
  int return_available = *returned_set != 0;
  if (expect_success) {
    memcpy(actual_prefix, out, expected_len);
    prefix_matches = memcmp(out, expected_output, expected_len) == 0;
    returned_matches =
        return_available && returned_value == (uint64_t)expected_len;
    for (size_t i = 0; i < 32; ++i) {
      if (storage[i] != 0xA5) {
        sentinel_unchanged = 0;
      }
    }
    for (size_t i = 32 + expected_len; i < output_storage_len; ++i) {
      if (storage[i] != 0xA5) {
        sentinel_unchanged = 0;
      }
    }
  } else {
    for (size_t i = 0; i < output_storage_len; ++i) {
      if (storage[i] != 0xA5) {
        sentinel_unchanged = 0;
      }
    }
  }
  for (size_t i = 0; i < source_storage_len; ++i) {
    uint8_t expected =
        i < (size_t)src_len ? src_data[i] : (uint8_t)0x5A;
    if (source[i] != expected) {
      source_unchanged = 0;
    }
  }

  if (munmap(storage, mapping_len) != 0) {
    return harness_failure("munmap");
  }

  int termination_matches = expect_success
                                ? WIFEXITED(status) && WEXITSTATUS(status) == 0
                                : WIFSIGNALED(status);
  if (!termination_matches || !sentinel_unchanged || !source_unchanged ||
      (expect_success && (!returned_matches || !prefix_matches))) {
    fprintf(stderr, "%s/capacity: case=%u input=", decoder_name, case_index);
    print_bytes(src_data, (size_t)src_len);
    fprintf(stderr, " output_capacity=%lld expected=%s actual=",
            (long long)out_len,
            expect_success ? "success" : "trapped-before-write");
    print_actual_termination(status);
    if (return_available) {
      fprintf(stderr, " returned=%llu", (unsigned long long)returned_value);
    } else {
      fprintf(stderr, " returned=unavailable");
    }
    if (expect_success) {
      fprintf(stderr, " expected_length=%zu expected_output=", expected_len);
      print_bytes(expected_output, expected_len);
      fprintf(stderr, " actual_prefix=");
      print_bytes(actual_prefix, expected_len);
      fprintf(stderr, " prefix_matches=%s",
              prefix_matches ? "true" : "false");
    }
    fprintf(stderr, " sentinel_unchanged=%s source_unchanged=%s\n",
            sentinel_unchanged ? "true" : "false",
            source_unchanged ? "true" : "false");
    return CHECK_CANDIDATE_FAILURE;
  }
  return CHECK_OK;
}

static int check_source(const char *decoder_name, decode_fn decode,
                        unsigned case_index, const uint8_t *src, int64_t len) {
  for (int64_t capacity = 0; capacity < len; ++capacity) {
    int rejected = run_child(decoder_name, decode, case_index, src, len,
                             capacity, 0);
    if (rejected != 0) {
      return rejected;
    }
  }
  return run_child(decoder_name, decode, case_index, src, len, len, 1);
}

static int check_decoder(const char *decoder_name, decode_fn decode) {
  static const uint8_t s0[] = {'A'};
  static const uint8_t s1[] = {'%', '4', '1'};
  static const uint8_t s2[] = {'%', '4', '1', '%', '4', '2'};
  static const uint8_t s3[] = {'%', 'G', 'G'};
  static const uint8_t s4[] = {'a', '%', '2', '0', 'b'};
  static const uint8_t s5[] = {0x00, 0x25, 0x46, 0x46, 0xFF};
  struct {
    const uint8_t *src;
    int64_t len;
  } cases[] = {
      {s0, sizeof(s0)}, {s1, sizeof(s1)}, {s2, sizeof(s2)},
      {s3, sizeof(s3)}, {s4, sizeof(s4)}, {s5, sizeof(s5)},
  };
  for (unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
    int status = check_source(decoder_name, decode, i, cases[i].src,
                              cases[i].len);
    if (status != 0) {
      return status;
    }
  }
  return 0;
}

int main(void) {
  int facts = check_decoder("facts-on", xlang_decode_facts);
  if (facts != 0) {
    return facts;
  }
  int nofacts = check_decoder("facts-off", xlang_decode_nofacts);
  if (nofacts != 0) {
    return nofacts;
  }
  return 0;
}
