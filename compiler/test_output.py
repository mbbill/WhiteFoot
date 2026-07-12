#!/usr/bin/env python3
"""Exercise xlc's first capacity-aware byte output primitive through its C ABI."""

import ctypes
import tempfile
from pathlib import Path

from test_lexer import Buffer, build_library


BYTE_CLEAN = 0
BYTE_NEED_CAPACITY = 1
PREFIX = b"xlc "
U64_MAX = 18446744073709551615


class ByteTape(ctypes.Structure):
    _fields_ = [
        ("bytes", Buffer),
        ("count", ctypes.c_uint64),
        ("status", ctypes.c_int32),
    ]


def expected(value):
    return PREFIX + str(value).encode("ascii")


def make_tape(capacity):
    storage = (ctypes.c_uint8 * (capacity + 1))()
    for index in range(capacity):
        storage[index] = 0xA5
    storage[capacity] = 0xD3
    tape = ByteTape(
        Buffer(ctypes.cast(storage, ctypes.c_void_p), capacity),
        U64_MAX,
        2,
    )
    return storage, tape


def call(library, value, capacity):
    storage, tape = make_tape(capacity)
    library.byte_tape_emit_probe(ctypes.byref(tape), value)
    written = bytes(storage[:capacity])
    guard = storage[capacity]
    return storage, tape, written, guard


def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))
        library.byte_tape_emit_probe.argtypes = [ctypes.POINTER(ByteTape), ctypes.c_uint64]
        library.byte_tape_emit_probe.restype = None

        for value in (0, 42, U64_MAX):
            want = expected(value)
            _, tape, observed, guard = call(library, value, len(want) + 8)
            assert tape.status == BYTE_CLEAN, (value, tape.status)
            assert tape.count == len(want), (value, tape.count)
            assert observed[:tape.count] == want, (value, observed[:tape.count])
            assert guard == 0xD3, (value, guard)

        want = expected(42)
        _, exact, observed, guard = call(library, 42, len(want))
        assert exact.status == BYTE_CLEAN
        assert exact.count == len(want)
        assert observed == want
        assert guard == 0xD3

        short_capacity = len(expected(U64_MAX)) - 1
        _, short, observed, guard = call(library, U64_MAX, short_capacity)
        assert short.status == BYTE_NEED_CAPACITY
        assert short.count == len(expected(U64_MAX))
        assert observed == expected(U64_MAX)[:short_capacity]
        assert guard == 0xD3

        storage, repeat = make_tape(len(expected(U64_MAX)))
        library.byte_tape_emit_probe(ctypes.byref(repeat), U64_MAX)
        first = (repeat.count, repeat.status, bytes(storage[:repeat.count]))
        for index in range(len(storage) - 1):
            storage[index] = 0x7E
        repeat.count = 7
        repeat.status = 2
        library.byte_tape_emit_probe(ctypes.byref(repeat), U64_MAX)
        second = (repeat.count, repeat.status, bytes(storage[:repeat.count]))
        assert second == first
        assert storage[len(storage) - 1] == 0xD3

        print("self-hosted output: canonical u64 decimal, exact/short capacity, OOB guard, and repeat pass")


if __name__ == "__main__":
    main()
