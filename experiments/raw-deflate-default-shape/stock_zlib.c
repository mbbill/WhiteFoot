/*
 * Public-API adapter for deterministic corpus preparation with stock zlib.
 *
 * The adapter fixes the experiment's raw RFC 1951 parameters and exposes no
 * zlib internals.  Compression and decompression each use one Z_FINISH call.
 */

#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "zlib.h"

#if ZLIB_VERNUM != 0x1320
#error "raw-deflate corpus preparation requires zlib 1.3.2 headers"
#endif

#if Z_DEFAULT_STRATEGY != 0 || Z_FILTERED != 1 || Z_HUFFMAN_ONLY != 2 || \
    Z_RLE != 3 || Z_FIXED != 4
#error "unexpected zlib strategy constants"
#endif

#if defined(_WIN32)
#define WF_EXPORT __declspec(dllexport)
#elif defined(__GNUC__) || defined(__clang__)
#define WF_EXPORT __attribute__((visibility("default")))
#else
#define WF_EXPORT
#endif

enum wf_stock_status {
    WF_STOCK_DONE = 0,
    WF_STOCK_NEED_OUTPUT = 1,
    WF_STOCK_MALFORMED = 2,
    WF_STOCK_ERROR = 3,
};

static int wf_valid_level(int32_t level) {
    return level == 0 || level == 1 || level == 6 || level == 9;
}

static int wf_valid_strategy(int32_t strategy) {
    return strategy == Z_DEFAULT_STRATEGY || strategy == Z_FILTERED ||
           strategy == Z_HUFFMAN_ONLY || strategy == Z_RLE ||
           strategy == Z_FIXED;
}

WF_EXPORT const char *wf_stock_header_version(void) {
    return ZLIB_VERSION;
}

WF_EXPORT const char *wf_stock_runtime_version(void) {
    return zlibVersion();
}

/* Return the public deflateBound_z result for the exact raw configuration. */
WF_EXPORT int32_t wf_stock_raw_deflate_bound(
    size_t src_len,
    int32_t level,
    int32_t strategy,
    size_t *bound
) {
    z_stream stream;
    int init_status;
    int end_status;

    if (bound == NULL) {
        return WF_STOCK_ERROR;
    }
    *bound = 0;
    if (src_len > (size_t)UINT_MAX || !wf_valid_level(level) ||
        !wf_valid_strategy(strategy)) {
        return WF_STOCK_ERROR;
    }

    memset(&stream, 0, sizeof(stream));
    init_status = deflateInit2(
        &stream,
        (int)level,
        Z_DEFLATED,
        -15,
        8,
        (int)strategy
    );
    if (init_status != Z_OK) {
        return WF_STOCK_ERROR;
    }

    *bound = deflateBound_z(&stream, src_len);
    end_status = deflateEnd(&stream);
    if (end_status != Z_OK) {
        *bound = 0;
        return WF_STOCK_ERROR;
    }
    return WF_STOCK_DONE;
}

/* Compress one complete input as raw RFC 1951 with one deflate call. */
WF_EXPORT int32_t wf_stock_raw_deflate_once(
    uint8_t *dst,
    size_t dst_cap,
    const uint8_t *src,
    size_t src_len,
    int32_t level,
    int32_t strategy,
    size_t *produced
) {
    uint8_t empty_src = 0;
    uint8_t empty_dst = 0;
    z_stream stream;
    int deflate_status;
    int end_status;
    int input_consumed;
    int output_exhausted;

    if (produced == NULL) {
        return WF_STOCK_ERROR;
    }
    *produced = 0;
    if ((src == NULL && src_len != 0) || (dst == NULL && dst_cap != 0) ||
        src_len > (size_t)UINT_MAX || dst_cap > (size_t)UINT_MAX ||
        !wf_valid_level(level) || !wf_valid_strategy(strategy)) {
        return WF_STOCK_ERROR;
    }

    memset(&stream, 0, sizeof(stream));
    stream.next_in = src != NULL ? (Bytef *)(uintptr_t)src : &empty_src;
    stream.avail_in = (uInt)src_len;
    stream.next_out = dst != NULL ? dst : &empty_dst;
    stream.avail_out = (uInt)dst_cap;

    if (deflateInit2(
            &stream,
            (int)level,
            Z_DEFLATED,
            -15,
            8,
            (int)strategy
        ) != Z_OK) {
        return WF_STOCK_ERROR;
    }

    deflate_status = deflate(&stream, Z_FINISH);
    *produced = dst_cap - (size_t)stream.avail_out;
    input_consumed = stream.avail_in == 0;
    output_exhausted = stream.avail_out == 0;
    end_status = deflateEnd(&stream);

    if (end_status != Z_OK) {
        return WF_STOCK_ERROR;
    }
    if (deflate_status == Z_STREAM_END && input_consumed) {
        return WF_STOCK_DONE;
    }
    if ((deflate_status == Z_OK || deflate_status == Z_BUF_ERROR) &&
        output_exhausted) {
        return WF_STOCK_NEED_OUTPUT;
    }
    return WF_STOCK_ERROR;
}

/* Inflate one raw stream for corpus cross-checking with one inflate call. */
WF_EXPORT int32_t wf_stock_raw_inflate_full(
    uint8_t *dst,
    size_t dst_cap,
    const uint8_t *src,
    size_t src_len,
    size_t *produced
) {
    uint8_t empty_src = 0;
    uint8_t empty_dst = 0;
    z_stream stream;
    int inflate_status;
    int end_status;
    int output_exhausted;

    if (produced == NULL) {
        return WF_STOCK_ERROR;
    }
    *produced = 0;
    if ((src == NULL && src_len != 0) || (dst == NULL && dst_cap != 0) ||
        src_len > (size_t)UINT_MAX || dst_cap > (size_t)UINT_MAX) {
        return WF_STOCK_ERROR;
    }

    memset(&stream, 0, sizeof(stream));
    stream.next_in = src != NULL ? (Bytef *)(uintptr_t)src : &empty_src;
    stream.avail_in = (uInt)src_len;
    stream.next_out = dst != NULL ? dst : &empty_dst;
    stream.avail_out = (uInt)dst_cap;

    if (inflateInit2(&stream, -15) != Z_OK) {
        return WF_STOCK_ERROR;
    }

    inflate_status = inflate(&stream, Z_FINISH);
    *produced = dst_cap - (size_t)stream.avail_out;
    output_exhausted = stream.avail_out == 0;
    end_status = inflateEnd(&stream);

    if (end_status != Z_OK) {
        return WF_STOCK_ERROR;
    }
    if (inflate_status == Z_STREAM_END) {
        return WF_STOCK_DONE;
    }
    if (inflate_status == Z_BUF_ERROR && output_exhausted) {
        return WF_STOCK_NEED_OUTPUT;
    }
    if (inflate_status == Z_DATA_ERROR || inflate_status == Z_BUF_ERROR) {
        return WF_STOCK_MALFORMED;
    }
    return WF_STOCK_ERROR;
}
