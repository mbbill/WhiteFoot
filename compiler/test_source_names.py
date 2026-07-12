#!/usr/bin/env python3
"""Test exact, collision-free comparisons between source token spans."""

import ctypes
import tempfile
from pathlib import Path

from test_lexer import Buffer, TokenTape, build_library


TOK_END = 0
TOK_WORD = 1
TOK_TYPE_ID = 3
LEX_CLEAN = 0


def make_buffer(data):
    storage = (ctypes.c_uint8 * max(1, len(data)))()
    for index, byte in enumerate(data):
        storage[index] = byte
    return storage, Buffer(ctypes.cast(storage, ctypes.c_void_p), len(data))


def make_tape(spans, kinds=None):
    capacity = max(1, len(spans))
    kind_storage = (ctypes.c_int32 * capacity)()
    start_storage = (ctypes.c_uint64 * capacity)()
    end_storage = (ctypes.c_uint64 * capacity)()
    if kinds is None:
        kinds = [TOK_WORD] * len(spans)
    for ordinal, ((start, end), kind) in enumerate(zip(spans, kinds)):
        kind_storage[ordinal] = kind
        start_storage[ordinal] = start
        end_storage[ordinal] = end
    tape = TokenTape(
        Buffer(ctypes.cast(kind_storage, ctypes.c_void_p), capacity),
        Buffer(ctypes.cast(start_storage, ctypes.c_void_p), capacity),
        Buffer(ctypes.cast(end_storage, ctypes.c_void_p), capacity),
        len(spans),
        LEX_CLEAN,
        0,
        0,
    )
    return (kind_storage, start_storage, end_storage), tape


def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))
        library.token_text_equal_probe.argtypes = [
            Buffer,
            ctypes.POINTER(TokenTape),
            ctypes.c_uint64,
            ctypes.c_uint64,
        ]
        library.token_text_equal_probe.restype = ctypes.c_bool
        library.token_text_equal_span.argtypes = [
            Buffer,
            ctypes.POINTER(TokenTape),
            ctypes.c_uint64,
            Buffer,
            ctypes.c_uint64,
            ctypes.c_uint64,
        ]
        library.token_text_equal_span.restype = ctypes.c_bool

        data = b"foo foo bar foobar Name name"
        source_storage, source = make_buffer(data)
        tape_storage, tape = make_tape(
            [(0, 3), (4, 7), (8, 11), (12, 18), (19, 23), (24, 28), (28, 28)],
            [TOK_WORD, TOK_WORD, TOK_WORD, TOK_WORD, TOK_TYPE_ID, TOK_WORD, TOK_END],
        )
        equal = library.token_text_equal_probe
        assert equal(source, ctypes.byref(tape), 0, 1)
        assert not equal(source, ctypes.byref(tape), 0, 2)
        assert not equal(source, ctypes.byref(tape), 0, 3)
        assert not equal(source, ctypes.byref(tape), 4, 5)
        assert equal(source, ctypes.byref(tape), 6, 6)
        assert not equal(source, ctypes.byref(tape), 6, 0)
        assert not equal(source, ctypes.byref(tape), 99, 0)

        other_storage, other = make_buffer(b"xxfooyy")
        equal_span = library.token_text_equal_span
        assert equal_span(source, ctypes.byref(tape), 0, other, 2, 5)
        assert not equal_span(source, ctypes.byref(tape), 0, other, 2, 4)
        assert not equal_span(source, ctypes.byref(tape), 0, other, 0, 3)
        assert not equal_span(source, ctypes.byref(tape), 0, other, 5, 4)
        assert not equal_span(source, ctypes.byref(tape), 0, other, 0, 9)

        empty_storage, empty_source = make_buffer(b"")
        empty_tape_storage, empty_tape = make_tape([(0, 0)], [TOK_END])
        assert equal(empty_source, ctypes.byref(empty_tape), 0, 0)
        assert equal_span(source, ctypes.byref(tape), 6, empty_source, 0, 0)
        assert not equal_span(source, ctypes.byref(tape), 0, empty_source, 0, 0)

        # Keep every ctypes allocation alive until all native calls have returned.
        assert source_storage and tape_storage and other_storage
        assert empty_storage and empty_tape_storage
        print("self-hosted source names: exact token/span comparisons and EOF behavior pass")


if __name__ == "__main__":
    main()
