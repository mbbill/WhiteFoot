/*
 * Public-API adapter for the pinned zlib-ng raw-inflate reference.
 *
 * This file deliberately exposes only the experiment's small status ABI.  It
 * neither calls zlib-ng internals nor reproduces any part of its decoder.
 */

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "zlib-ng.h"

#if ZLIBNG_VERNUM != 0x020303F0L
#error "raw-deflate reference requires zlib-ng 2.3.3 headers"
#endif

#if defined(_WIN32)
#define WF_EXPORT __declspec(dllexport)
#elif defined(__GNUC__) || defined(__clang__)
#define WF_EXPORT __attribute__((visibility("default")))
#else
#define WF_EXPORT
#endif

enum wf_raw_status {
    WF_RAW_DONE = 0,
    WF_RAW_NEED_OUTPUT = 1,
    WF_RAW_MALFORMED = 2,
};

struct wf_zng_raw_state {
    zng_stream stream;
    size_t dst_cap;
    uint8_t empty_src;
    uint8_t empty_dst;
    int initialized;
    int used;
};

WF_EXPORT const char *wf_zng_header_version(void) {
    return ZLIBNG_VERSION;
}

WF_EXPORT const char *wf_zng_runtime_version(void) {
    return zlibng_version();
}

WF_EXPORT size_t wf_zng_raw_state_size(void) {
    return sizeof(struct wf_zng_raw_state);
}

WF_EXPORT size_t wf_zng_raw_state_alignment(void) {
    return _Alignof(struct wf_zng_raw_state);
}

/*
 * Prepare one fresh public zlib-ng stream outside the decoder-kernel timing
 * boundary.  The caller owns suitably aligned storage of the reported size.
 */
WF_EXPORT int32_t wf_zng_raw_prepare(
    void *storage,
    size_t storage_size,
    uint8_t *dst,
    size_t dst_cap,
    const uint8_t *src,
    size_t src_len
) {
    struct wf_zng_raw_state *state;

    if (storage == NULL || storage_size != sizeof(struct wf_zng_raw_state) ||
        (uintptr_t)storage % _Alignof(struct wf_zng_raw_state) != 0 ||
        (src == NULL && src_len != 0) || (dst == NULL && dst_cap != 0) ||
        src_len > UINT32_MAX || dst_cap > UINT32_MAX) {
        return WF_RAW_MALFORMED;
    }

    state = (struct wf_zng_raw_state *)storage;
    memset(state, 0, sizeof(*state));
    state->dst_cap = dst_cap;
    state->stream.next_in = src != NULL ? src : &state->empty_src;
    state->stream.avail_in = (uint32_t)src_len;
    state->stream.next_out = dst != NULL ? dst : &state->empty_dst;
    state->stream.avail_out = (uint32_t)dst_cap;
    if (zng_inflateInit2(&state->stream, -15) != Z_OK) {
        return WF_RAW_MALFORMED;
    }
    state->initialized = 1;
    return WF_RAW_DONE;
}

/* Time exactly this call when comparing the two prepared decoder kernels. */
WF_EXPORT int32_t wf_zng_raw_inflate_prepared(
    void *storage,
    size_t *produced
) {
    struct wf_zng_raw_state *state;
    int32_t inflate_status;
    int output_exhausted;

    if (storage == NULL || produced == NULL) {
        return WF_RAW_MALFORMED;
    }
    *produced = 0;
    state = (struct wf_zng_raw_state *)storage;
    if (state->initialized == 0 || state->used != 0) {
        return WF_RAW_MALFORMED;
    }
    state->used = 1;

    inflate_status = zng_inflate(&state->stream, Z_FINISH);
    *produced = state->dst_cap - (size_t)state->stream.avail_out;
    output_exhausted = state->stream.avail_out == 0;
    if (inflate_status == Z_STREAM_END) {
        return WF_RAW_DONE;
    }
    if (inflate_status == Z_BUF_ERROR && output_exhausted) {
        return WF_RAW_NEED_OUTPUT;
    }
    return WF_RAW_MALFORMED;
}

WF_EXPORT int32_t wf_zng_raw_end(void *storage) {
    struct wf_zng_raw_state *state;
    int32_t end_status;

    if (storage == NULL) {
        return WF_RAW_MALFORMED;
    }
    state = (struct wf_zng_raw_state *)storage;
    if (state->initialized == 0) {
        return WF_RAW_MALFORMED;
    }
    end_status = zng_inflateEnd(&state->stream);
    state->initialized = 0;
    return end_status == Z_OK ? WF_RAW_DONE : WF_RAW_MALFORMED;
}

/*
 * Decode one complete RFC 1951 stream with one inflate(..., Z_FINISH) call.
 *
 * A zero-length input or output may use a null pointer.  Nonzero spans must
 * have storage, and both span lengths must fit zng_stream's uint32_t counters.
 * `produced` is set to zero before initialization and to the number of bytes
 * written after the inflate call.
 */
WF_EXPORT int32_t wf_zng_raw_inflate_once(
    uint8_t *dst,
    size_t dst_cap,
    const uint8_t *src,
    size_t src_len,
    size_t *produced
) {
    struct wf_zng_raw_state state;
    int32_t prepare_status;
    int32_t inflate_status;
    int32_t end_status;

    if (produced == NULL) {
        return WF_RAW_MALFORMED;
    }
    *produced = 0;
    prepare_status = wf_zng_raw_prepare(
        &state, sizeof(state), dst, dst_cap, src, src_len
    );
    if (prepare_status != WF_RAW_DONE) {
        return WF_RAW_MALFORMED;
    }
    inflate_status = wf_zng_raw_inflate_prepared(&state, produced);
    end_status = wf_zng_raw_end(&state);
    return end_status == WF_RAW_DONE ? inflate_status : WF_RAW_MALFORMED;
}
