"""Tests for the independent raw-DEFLATE oracle.

The primary fixtures are literal wire bytes or streams emitted by the small
hand encoder below.  Python's zlib binding is used only as an external
agreement check on streams whose expected plaintext is already known.
"""

import unittest
import zlib

from oracle import DONE, MALFORMED, NEED_OUTPUT, decode_raw


LENGTH_BASE = (
    3, 4, 5, 6, 7, 8, 9, 10,
    11, 13, 15, 17,
    19, 23, 27, 31,
    35, 43, 51, 59,
    67, 83, 99, 115,
    131, 163, 195, 227,
    258,
)

LENGTH_EXTRA = (
    0, 0, 0, 0, 0, 0, 0, 0,
    1, 1, 1, 1,
    2, 2, 2, 2,
    3, 3, 3, 3,
    4, 4, 4, 4,
    5, 5, 5, 5,
    0,
)

DISTANCE_BASE = (
    1, 2, 3, 4,
    5, 7, 9, 13,
    17, 25, 33, 49,
    65, 97, 129, 193,
    257, 385, 513, 769,
    1025, 1537, 2049, 3073,
    4097, 6145, 8193, 12289,
    16385, 24577,
)

DISTANCE_EXTRA = (
    0, 0, 0, 0,
    1, 1, 2, 2,
    3, 3, 4, 4,
    5, 5, 6, 6,
    7, 7, 8, 8,
    9, 9, 10, 10,
    11, 11, 12, 12,
    13, 13,
)

CODE_LENGTH_ORDER = (
    16, 17, 18, 0, 8, 7, 9, 6, 10, 5,
    11, 4, 12, 3, 13, 2, 14, 1, 15,
)


class _BitWriter:
    def __init__(self):
        self.bits = []

    def write_bits(self, value, width):
        """Write an ordinary RFC 1951 integer field, low bit first."""
        for offset in range(width):
            self.bits.append((value >> offset) & 1)

    def write_code(self, code, width):
        """Write a canonical Huffman code, high code bit first."""
        for offset in range(width - 1, -1, -1):
            self.bits.append((code >> offset) & 1)

    def align_to_byte(self):
        while len(self.bits) & 7:
            self.bits.append(0)

    def finish(self):
        result = bytearray((len(self.bits) + 7) // 8)
        for position, bit in enumerate(self.bits):
            result[position >> 3] |= bit << (position & 7)
        return bytes(result)


def _canonical_codes(lengths):
    maximum = max(lengths) if lengths else 0
    counts = [0] * (maximum + 1)
    for width in lengths:
        if width:
            counts[width] += 1

    next_code = [0] * (maximum + 1)
    code = 0
    for width in range(1, maximum + 1):
        code = (code + counts[width - 1]) << 1
        next_code[width] = code

    result = {}
    for symbol, width in enumerate(lengths):
        if width:
            result[symbol] = (next_code[width], width)
            next_code[width] += 1
    return result


def _fixed_codes():
    literal_lengths = [0] * 288
    literal_lengths[0:144] = [8] * 144
    literal_lengths[144:256] = [9] * 112
    literal_lengths[256:280] = [7] * 24
    literal_lengths[280:288] = [8] * 8
    return _canonical_codes(literal_lengths), _canonical_codes([5] * 32)


FIXED_LITERAL_CODES, FIXED_DISTANCE_CODES = _fixed_codes()


def _write_symbol(writer, codes, symbol):
    code, width = codes[symbol]
    writer.write_code(code, width)


def _range_symbol(value, bases, extras):
    for symbol, (base, extra) in enumerate(zip(bases, extras)):
        maximum = base + ((1 << extra) - 1 if extra else 0)
        if base <= value <= maximum:
            return symbol, value - base, extra
    raise ValueError("value has no RFC 1951 code")


def _write_fixed_block(writer, tokens, final=True):
    writer.write_bits(1 if final else 0, 1)
    writer.write_bits(1, 2)
    for token in tokens:
        if isinstance(token, int):
            _write_symbol(writer, FIXED_LITERAL_CODES, token)
            continue

        length, distance = token
        length_symbol, length_delta, length_extra = _range_symbol(
            length, LENGTH_BASE, LENGTH_EXTRA
        )
        _write_symbol(writer, FIXED_LITERAL_CODES, length_symbol + 257)
        writer.write_bits(length_delta, length_extra)

        distance_symbol, distance_delta, distance_extra = _range_symbol(
            distance, DISTANCE_BASE, DISTANCE_EXTRA
        )
        _write_symbol(writer, FIXED_DISTANCE_CODES, distance_symbol)
        writer.write_bits(distance_delta, distance_extra)

    _write_symbol(writer, FIXED_LITERAL_CODES, 256)


def _fixed_stream(tokens):
    writer = _BitWriter()
    _write_fixed_block(writer, tokens)
    return writer.finish()


def _write_stored_block(writer, payload, final):
    if len(payload) > 65535:
        raise ValueError("stored block is too large")
    writer.write_bits(1 if final else 0, 1)
    writer.write_bits(0, 2)
    writer.align_to_byte()
    writer.write_bits(len(payload), 16)
    writer.write_bits(len(payload) ^ 0xFFFF, 16)
    for value in payload:
        writer.write_bits(value, 8)


def _dynamic_literal_stream(payload):
    """Emit a complete dynamic tree containing only literal A and EOB."""
    if any(value != 65 for value in payload):
        raise ValueError("this deliberately small tree encodes only A")

    writer = _BitWriter()
    writer.write_bits(1, 1)
    writer.write_bits(2, 2)
    writer.write_bits(0, 5)   # HLIT: 257 literal/length entries
    writer.write_bits(0, 5)   # HDIST: one (zero-length) distance entry
    writer.write_bits(14, 4)  # HCLEN: first 18 entries in permutation

    code_length_lengths = [0] * 19
    code_length_lengths[18] = 1
    code_length_lengths[0] = 2
    code_length_lengths[1] = 3
    code_length_lengths[16] = 4
    code_length_lengths[17] = 4
    for index in range(18):
        writer.write_bits(code_length_lengths[CODE_LENGTH_ORDER[index]], 3)
    code_length_codes = _canonical_codes(code_length_lengths)

    # Build the 65- and 190-zero runs with all three repeat opcodes.  Repeating
    # a previous zero with opcode 16 is legal and is worth exercising directly.
    _write_symbol(writer, code_length_codes, 0)
    _write_symbol(writer, code_length_codes, 16)
    writer.write_bits(6 - 3, 2)
    _write_symbol(writer, code_length_codes, 17)
    writer.write_bits(10 - 3, 3)
    _write_symbol(writer, code_length_codes, 18)
    writer.write_bits(48 - 11, 7)
    _write_symbol(writer, code_length_codes, 1)

    _write_symbol(writer, code_length_codes, 0)
    _write_symbol(writer, code_length_codes, 16)
    writer.write_bits(6 - 3, 2)
    _write_symbol(writer, code_length_codes, 17)
    writer.write_bits(10 - 3, 3)
    _write_symbol(writer, code_length_codes, 18)
    writer.write_bits(138 - 11, 7)
    _write_symbol(writer, code_length_codes, 18)
    writer.write_bits(35 - 11, 7)
    _write_symbol(writer, code_length_codes, 1)
    _write_symbol(writer, code_length_codes, 0)

    literal_codes = _canonical_codes(
        [1 if symbol in (65, 256) else 0 for symbol in range(257)]
    )
    for value in payload:
        _write_symbol(writer, literal_codes, value)
    _write_symbol(writer, literal_codes, 256)
    return writer.finish()


def _dynamic_one_distance_stream():
    """Emit A followed by a length-three, distance-one overlapping match."""
    writer = _BitWriter()
    writer.write_bits(1, 1)
    writer.write_bits(2, 2)
    writer.write_bits(1, 5)   # HLIT: entries through length symbol 257
    writer.write_bits(0, 5)   # HDIST: one distance symbol
    writer.write_bits(14, 4)

    code_length_lengths = [0] * 19
    code_length_lengths[18] = 1
    code_length_lengths[0] = 2
    code_length_lengths[1] = 3
    code_length_lengths[2] = 3
    for index in range(18):
        writer.write_bits(code_length_lengths[CODE_LENGTH_ORDER[index]], 3)
    code_length_codes = _canonical_codes(code_length_lengths)

    # Literal/length lengths: zero[65], 1, zero[190], 2, 2.  The sole
    # distance symbol then has length one.
    _write_symbol(writer, code_length_codes, 18)
    writer.write_bits(65 - 11, 7)
    _write_symbol(writer, code_length_codes, 1)
    _write_symbol(writer, code_length_codes, 18)
    writer.write_bits(138 - 11, 7)
    _write_symbol(writer, code_length_codes, 18)
    writer.write_bits(52 - 11, 7)
    _write_symbol(writer, code_length_codes, 2)
    _write_symbol(writer, code_length_codes, 2)
    _write_symbol(writer, code_length_codes, 1)

    literal_lengths = [0] * 258
    literal_lengths[65] = 1
    literal_lengths[256] = 2
    literal_lengths[257] = 2
    literal_codes = _canonical_codes(literal_lengths)
    distance_codes = _canonical_codes([1])
    _write_symbol(writer, literal_codes, 65)
    _write_symbol(writer, literal_codes, 257)
    _write_symbol(writer, distance_codes, 0)
    _write_symbol(writer, literal_codes, 256)
    return writer.finish()


def _dynamic_two_empty_distances_stream():
    """Emit an otherwise-valid tree with two declared zero-length distances."""
    writer = _BitWriter()
    writer.write_bits(1, 1)
    writer.write_bits(2, 2)
    writer.write_bits(0, 5)   # HLIT: 257 literal/length entries
    writer.write_bits(1, 5)   # HDIST: two distance entries
    writer.write_bits(14, 4)  # HCLEN: first 18 entries in permutation

    code_length_lengths = [0] * 19
    code_length_lengths[0] = 1
    code_length_lengths[1] = 1
    for index in range(18):
        writer.write_bits(code_length_lengths[CODE_LENGTH_ORDER[index]], 3)
    code_length_codes = _canonical_codes(code_length_lengths)

    for _ in range(256):
        _write_symbol(writer, code_length_codes, 0)
    _write_symbol(writer, code_length_codes, 1)
    _write_symbol(writer, code_length_codes, 0)
    _write_symbol(writer, code_length_codes, 0)

    literal_codes = _canonical_codes([0] * 256 + [1])
    _write_symbol(writer, literal_codes, 256)
    return writer.finish()


def _dynamic_missing_end_stream():
    """Emit a dynamic header whose decoded literal tree omits symbol 256."""
    writer = _BitWriter()
    writer.write_bits(1, 1)
    writer.write_bits(2, 2)
    writer.write_bits(0, 5)
    writer.write_bits(0, 5)
    writer.write_bits(14, 4)

    code_length_lengths = [0] * 19
    code_length_lengths[18] = 1
    code_length_lengths[0] = 2
    code_length_lengths[1] = 2
    for index in range(18):
        writer.write_bits(code_length_lengths[CODE_LENGTH_ORDER[index]], 3)
    codes = _canonical_codes(code_length_lengths)

    _write_symbol(writer, codes, 18)
    writer.write_bits(65 - 11, 7)
    _write_symbol(writer, codes, 1)
    _write_symbol(writer, codes, 18)
    writer.write_bits(138 - 11, 7)
    _write_symbol(writer, codes, 18)
    writer.write_bits(54 - 11, 7)
    return writer.finish()


def _dynamic_first_repeat_stream():
    writer = _BitWriter()
    writer.write_bits(1, 1)
    writer.write_bits(2, 2)
    writer.write_bits(0, 5)
    writer.write_bits(0, 5)
    writer.write_bits(0, 4)  # Four code-length-code entries.
    writer.write_bits(1, 3)  # Symbol 16.
    writer.write_bits(0, 3)  # Symbol 17.
    writer.write_bits(0, 3)  # Symbol 18.
    writer.write_bits(1, 3)  # Symbol 0.
    codes = _canonical_codes([1] + [0] * 15 + [1, 0, 0])
    _write_symbol(writer, codes, 16)
    writer.write_bits(0, 2)
    return writer.finish()


def _dynamic_oversubscribed_code_lengths():
    writer = _BitWriter()
    writer.write_bits(1, 1)
    writer.write_bits(2, 2)
    writer.write_bits(0, 5)
    writer.write_bits(0, 5)
    writer.write_bits(0, 4)
    writer.write_bits(1, 3)  # Symbol 16.
    writer.write_bits(1, 3)  # Symbol 17.
    writer.write_bits(1, 3)  # Symbol 18: three one-bit codes cannot fit.
    writer.write_bits(0, 3)
    return writer.finish()


def _append_overlap(output, length, distance):
    for _ in range(length):
        output.append(output[-distance])


class RawDeflateOracleTests(unittest.TestCase):
    def assert_valid(self, stream, expected):
        result = decode_raw(stream)
        self.assertEqual(DONE, result.status, result.error)
        self.assertEqual(expected, result.output)
        # External agreement only: expected was supplied independently of zlib.
        self.assertEqual(expected, zlib.decompress(stream, -15))
        return result

    def test_literal_known_wire_vectors(self):
        self.assert_valid(bytes.fromhex("0300"), b"")
        result = self.assert_valid(bytes.fromhex("730400"), b"A")
        self.assertEqual((1,), result.unit_boundaries)

    def test_stored_known_wire_vector(self):
        stream = bytes.fromhex("010300fcff414243")
        result = self.assert_valid(stream, b"ABC")
        self.assertEqual((1, 2, 3), result.unit_boundaries)

    def test_stored_length_boundaries(self):
        self.assert_valid(bytes.fromhex("010000ffff"), b"")

        payload = bytes((index * 17 + 3) & 0xFF for index in range(65535))
        writer = _BitWriter()
        _write_stored_block(writer, payload, final=True)
        result = self.assert_valid(writer.finish(), payload)
        self.assertEqual(65535, result.unit_boundaries[-1])

    def test_every_literal_byte(self):
        expected = bytes(range(256))
        self.assert_valid(_fixed_stream(list(expected)), expected)

    def test_dynamic_no_distance_tree(self):
        stream = _dynamic_literal_stream(b"AAA")
        result = self.assert_valid(stream, b"AAA")
        self.assertEqual((1, 2, 3), result.unit_boundaries)

    def test_dynamic_one_symbol_distance_tree_and_match(self):
        stream = _dynamic_one_distance_stream()
        result = self.assert_valid(stream, b"AAAA")
        self.assertEqual((1, 4), result.unit_boundaries)

    def test_reserved_hlit_values_and_multiple_empty_distances(self):
        for hlit in (30, 31):
            writer = _BitWriter()
            writer.write_bits(1, 1)
            writer.write_bits(2, 2)
            writer.write_bits(hlit, 5)
            result = decode_raw(writer.finish())
            self.assertEqual(MALFORMED, result.status)
            self.assertIn("HLIT", result.error)

        stream = _dynamic_two_empty_distances_stream()
        result = decode_raw(stream)
        self.assertEqual(DONE, result.status)
        self.assertEqual(b"", result.output)
        self.assertEqual(b"", zlib.decompress(stream, wbits=-15))

    def test_every_length_code_at_both_boundaries(self):
        tokens = [65]
        expected = bytearray(b"A")
        for base, extra in zip(LENGTH_BASE, LENGTH_EXTRA):
            values = [base]
            maximum = base + ((1 << extra) - 1 if extra else 0)
            if maximum != base:
                values.append(maximum)
            for length in values:
                tokens.append((length, 1))
                expected.extend(b"A" * length)

        result = self.assert_valid(_fixed_stream(tokens), bytes(expected))
        self.assertEqual(len(tokens), len(result.unit_boundaries))

    def test_every_distance_code_at_both_boundaries(self):
        seed = bytes((index * 29 + 7) & 0xFF for index in range(32768))
        expected = bytearray(seed)
        match_tokens = []
        for base, extra in zip(DISTANCE_BASE, DISTANCE_EXTRA):
            values = [base]
            maximum = base + ((1 << extra) - 1 if extra else 0)
            if maximum != base:
                values.append(maximum)
            for distance in values:
                match_tokens.append((3, distance))
                _append_overlap(expected, 3, distance)

        writer = _BitWriter()
        _write_stored_block(writer, seed, final=False)
        _write_fixed_block(writer, match_tokens, final=True)
        result = self.assert_valid(writer.finish(), bytes(expected))
        self.assertEqual(32768 + len(match_tokens), len(result.unit_boundaries))

    def test_overlap_and_whole_match_output_capacity(self):
        stream = _fixed_stream([65, (258, 1), 66])
        expected = b"A" * 259 + b"B"
        self.assert_valid(stream, expected)

        cases = (
            (0, NEED_OUTPUT, b""),
            (1, NEED_OUTPUT, b"A"),
            (2, NEED_OUTPUT, b"A"),
            (258, NEED_OUTPUT, b"A"),
            (259, NEED_OUTPUT, b"A" * 259),
            (260, DONE, expected),
            (300, DONE, expected),
        )
        for capacity, status, prefix in cases:
            with self.subTest(capacity=capacity):
                result = decode_raw(stream, capacity)
                self.assertEqual(status, result.status)
                self.assertEqual(prefix, result.output)
                self.assertNotIn(2, result.unit_boundaries)
                self.assertNotIn(258, result.unit_boundaries)

    def test_stored_bytes_are_individual_capacity_units(self):
        stream = bytes.fromhex("010300fcff414243")
        for capacity, expected in enumerate((b"", b"A", b"AB", b"ABC")):
            with self.subTest(capacity=capacity):
                result = decode_raw(stream, capacity)
                self.assertEqual(DONE if capacity == 3 else NEED_OUTPUT, result.status)
                self.assertEqual(expected, result.output)

    def test_multiple_block_types(self):
        writer = _BitWriter()
        _write_stored_block(writer, b"ABC", final=False)
        _write_fixed_block(writer, [68, 69, 70], final=True)
        self.assert_valid(writer.finish(), b"ABCDEF")

    def test_final_padding_and_trailing_bytes_are_ignored(self):
        self.assert_valid(bytes.fromhex("03fc"), b"")
        result = decode_raw(bytes.fromhex("0300deadbeef"))
        self.assertEqual(DONE, result.status)
        self.assertEqual(b"", result.output)
        self.assertEqual(10, result.input_bits_consumed)

    def test_reserved_and_stored_block_errors(self):
        cases = (
            bytes.fromhex("07"),
            bytes.fromhex("010100000041"),
            b"",
            bytes.fromhex("01"),
        )
        for stream in cases:
            with self.subTest(stream=stream.hex()):
                result = decode_raw(stream)
                self.assertEqual(MALFORMED, result.status)

        truncated_payload = bytes.fromhex("010500faff68656c6c")
        result = decode_raw(truncated_payload)
        self.assertEqual(MALFORMED, result.status)
        self.assertEqual(b"hell", result.output)
        self.assertEqual((1, 2, 3, 4), result.unit_boundaries)

    def test_impossible_distance_and_reserved_symbols(self):
        # A legal fixed length code followed by distance one, before any output.
        impossible = _fixed_stream([(3, 1)])
        self.assertEqual(MALFORMED, decode_raw(impossible).status)

        writer = _BitWriter()
        writer.write_bits(1, 1)
        writer.write_bits(1, 2)
        _write_symbol(writer, FIXED_LITERAL_CODES, 286)
        self.assertEqual(MALFORMED, decode_raw(writer.finish()).status)

        writer = _BitWriter()
        writer.write_bits(1, 1)
        writer.write_bits(1, 2)
        _write_symbol(writer, FIXED_LITERAL_CODES, 65)
        _write_symbol(writer, FIXED_LITERAL_CODES, 257)
        _write_symbol(writer, FIXED_DISTANCE_CODES, 30)
        self.assertEqual(MALFORMED, decode_raw(writer.finish()).status)

    def test_dynamic_tree_validation(self):
        cases = (
            _dynamic_missing_end_stream(),
            _dynamic_first_repeat_stream(),
            _dynamic_oversubscribed_code_lengths(),
        )
        for stream in cases:
            with self.subTest(stream=stream.hex()):
                result = decode_raw(stream)
                self.assertEqual(MALFORMED, result.status)

    def test_every_truncation_of_dynamic_stream_is_malformed(self):
        stream = _dynamic_literal_stream(b"AAA")
        for end in range(len(stream)):
            with self.subTest(end=end):
                result = decode_raw(stream[:end])
                self.assertEqual(MALFORMED, result.status)

    def test_malformed_precedes_output_capacity(self):
        stream = _fixed_stream([65, (3, 1)])[:-1]
        result = decode_raw(stream, 0)
        self.assertEqual(MALFORMED, result.status)
        self.assertEqual(b"", result.output)

    def test_argument_validation(self):
        self.assertEqual(DONE, decode_raw(bytearray.fromhex("0300")).status)
        self.assertEqual(DONE, decode_raw(memoryview(bytes.fromhex("0300"))).status)
        with self.assertRaises(TypeError):
            decode_raw("0300")
        with self.assertRaises(ValueError):
            decode_raw(bytes.fromhex("0300"), -1)


if __name__ == "__main__":
    unittest.main()
