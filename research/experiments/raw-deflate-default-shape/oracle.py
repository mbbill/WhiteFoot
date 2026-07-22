"""Independent bit-level oracle for one-shot raw RFC 1951 streams.

This module intentionally does not import or call zlib.  It implements the
wire format directly so that the experiment has a correctness authority which
does not share decoder logic with either native comparator.

Output capacity is applied after structural validation.  That detail matters:
``NeedOutput`` is a result only for an otherwise-valid stream, while malformed
input remains ``Malformed`` even when its first invalid item occurs beyond the
visible output capacity.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple


DONE = 0
NEED_OUTPUT = 1
MALFORMED = 2


@dataclass(frozen=True)
class DecodeResult:
    """Deterministic observable result for one oracle invocation.

    ``unit_boundaries`` contains cumulative output lengths after every visible
    stored byte, literal, or whole length-distance match.  It therefore gives
    a verifier all legal prefix lengths for the returned output.
    """

    status: int
    output: bytes
    unit_boundaries: Tuple[int, ...]
    error: Optional[str]
    input_bits_consumed: int


class _Malformed(Exception):
    pass


class _BitReader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.bit_position = 0

    def read_bits(self, width: int) -> int:
        if width < 0:
            raise ValueError("bit width must be nonnegative")
        if self.bit_position + width > len(self.data) * 8:
            raise _Malformed("truncated bit field")

        value = 0
        for offset in range(width):
            byte = self.data[self.bit_position >> 3]
            bit = (byte >> (self.bit_position & 7)) & 1
            value |= bit << offset
            self.bit_position += 1
        return value

    def align_to_byte(self) -> None:
        self.bit_position = (self.bit_position + 7) & ~7

    def require_bits(self, count: int) -> None:
        if self.bit_position + count > len(self.data) * 8:
            raise _Malformed("truncated stored block")


class _Huffman:
    def __init__(self, entries: Dict[Tuple[int, int], int], max_bits: int) -> None:
        self.entries = entries
        self.max_bits = max_bits

    def decode(self, reader: _BitReader) -> int:
        if self.max_bits == 0:
            raise _Malformed("attempted to use an empty Huffman tree")

        # RFC 1951 packs Huffman codes most-significant code bit first, even
        # though ordinary integer fields are packed least-significant bit
        # first.  The bit reader returns wire-order bits, so a left shift
        # reconstructs the canonical code directly.
        code = 0
        for width in range(1, self.max_bits + 1):
            code = (code << 1) | reader.read_bits(1)
            symbol = self.entries.get((width, code))
            if symbol is not None:
                return symbol
        raise _Malformed("invalid Huffman code")


def _build_huffman(
    lengths: Sequence[int],
    *,
    name: str,
    maximum_bits: int,
    allow_empty: bool,
    allow_single_incomplete: bool,
) -> _Huffman:
    counts = [0] * (maximum_bits + 1)
    for length in lengths:
        if length < 0 or length > maximum_bits:
            raise _Malformed("%s code length is out of range" % name)
        if length != 0:
            counts[length] += 1

    max_bits = 0
    for width in range(maximum_bits, 0, -1):
        if counts[width] != 0:
            max_bits = width
            break

    if max_bits == 0:
        if allow_empty:
            return _Huffman({}, 0)
        raise _Malformed("%s Huffman tree is empty" % name)

    # Kraft-space accounting detects over-subscribed and forbidden incomplete
    # canonical code sets without depending on a table-builder implementation.
    space = 1
    for width in range(1, max_bits + 1):
        space = (space << 1) - counts[width]
        if space < 0:
            raise _Malformed("%s Huffman tree is over-subscribed" % name)
    if space > 0 and not (allow_single_incomplete and max_bits == 1):
        raise _Malformed("%s Huffman tree is incomplete" % name)

    next_code = [0] * (max_bits + 1)
    code = 0
    for width in range(1, max_bits + 1):
        code = (code + counts[width - 1]) << 1
        next_code[width] = code

    entries: Dict[Tuple[int, int], int] = {}
    for symbol, width in enumerate(lengths):
        if width == 0:
            continue
        symbol_code = next_code[width]
        next_code[width] += 1
        entries[(width, symbol_code)] = symbol

    return _Huffman(entries, max_bits)


_LENGTH_BASE = (
    3, 4, 5, 6, 7, 8, 9, 10,
    11, 13, 15, 17,
    19, 23, 27, 31,
    35, 43, 51, 59,
    67, 83, 99, 115,
    131, 163, 195, 227,
    258,
)

_LENGTH_EXTRA = (
    0, 0, 0, 0, 0, 0, 0, 0,
    1, 1, 1, 1,
    2, 2, 2, 2,
    3, 3, 3, 3,
    4, 4, 4, 4,
    5, 5, 5, 5,
    0,
)

_DISTANCE_BASE = (
    1, 2, 3, 4,
    5, 7, 9, 13,
    17, 25, 33, 49,
    65, 97, 129, 193,
    257, 385, 513, 769,
    1025, 1537, 2049, 3073,
    4097, 6145, 8193, 12289,
    16385, 24577,
)

_DISTANCE_EXTRA = (
    0, 0, 0, 0,
    1, 1, 2, 2,
    3, 3, 4, 4,
    5, 5, 6, 6,
    7, 7, 8, 8,
    9, 9, 10, 10,
    11, 11, 12, 12,
    13, 13,
)

_CODE_LENGTH_ORDER = (
    16, 17, 18, 0, 8, 7, 9, 6, 10, 5,
    11, 4, 12, 3, 13, 2, 14, 1, 15,
)


def _fixed_trees() -> Tuple[_Huffman, _Huffman]:
    literal_lengths = [0] * 288
    for symbol in range(0, 144):
        literal_lengths[symbol] = 8
    for symbol in range(144, 256):
        literal_lengths[symbol] = 9
    for symbol in range(256, 280):
        literal_lengths[symbol] = 7
    for symbol in range(280, 288):
        literal_lengths[symbol] = 8

    distance_lengths = [5] * 32
    return (
        _build_huffman(
            literal_lengths,
            name="fixed literal/length",
            maximum_bits=15,
            allow_empty=False,
            allow_single_incomplete=True,
        ),
        _build_huffman(
            distance_lengths,
            name="fixed distance",
            maximum_bits=15,
            allow_empty=False,
            allow_single_incomplete=True,
        ),
    )


_FIXED_LITERAL_TREE, _FIXED_DISTANCE_TREE = _fixed_trees()


class _Decoder:
    def __init__(self, data: bytes) -> None:
        self.reader = _BitReader(data)
        self.output = bytearray()
        self.unit_boundaries = []  # type: list[int]

    def _commit_byte(self, value: int) -> None:
        self.output.append(value)
        self.unit_boundaries.append(len(self.output))

    def _commit_match(self, length: int, distance: int) -> None:
        if distance <= 0 or distance > 32768:
            raise _Malformed("distance is outside the RFC 1951 window")
        if distance > len(self.output):
            raise _Malformed("distance exceeds available output history")

        # Appending directly implements RFC overlap: after the first copied
        # byte, later bytes in the same match may refer to bytes just appended.
        for _ in range(length):
            self.output.append(self.output[-distance])
        self.unit_boundaries.append(len(self.output))

    def _stored_block(self) -> None:
        self.reader.align_to_byte()
        self.reader.require_bits(32)
        length = self.reader.read_bits(16)
        complement = self.reader.read_bits(16)
        if (length ^ complement) != 0xFFFF:
            raise _Malformed("stored block LEN/NLEN mismatch")

        for _ in range(length):
            self._commit_byte(self.reader.read_bits(8))

    def _dynamic_trees(self) -> Tuple[_Huffman, _Huffman]:
        literal_count_field = self.reader.read_bits(5)
        if literal_count_field > 29:
            raise _Malformed("HLIT uses a reserved value")
        literal_count = literal_count_field + 257
        distance_count = self.reader.read_bits(5) + 1
        code_length_count = self.reader.read_bits(4) + 4

        code_length_lengths = [0] * 19
        for index in range(code_length_count):
            code_length_lengths[_CODE_LENGTH_ORDER[index]] = self.reader.read_bits(3)

        code_length_tree = _build_huffman(
            code_length_lengths,
            name="code-length",
            maximum_bits=7,
            allow_empty=False,
            allow_single_incomplete=False,
        )

        total = literal_count + distance_count
        lengths = []  # type: list[int]
        while len(lengths) < total:
            symbol = code_length_tree.decode(self.reader)
            if 0 <= symbol <= 15:
                lengths.append(symbol)
            elif symbol == 16:
                if not lengths:
                    raise _Malformed("repeat-previous code has no predecessor")
                repeat = self.reader.read_bits(2) + 3
                if len(lengths) + repeat > total:
                    raise _Malformed("repeat-previous code exceeds tree lengths")
                lengths.extend([lengths[-1]] * repeat)
            elif symbol == 17:
                repeat = self.reader.read_bits(3) + 3
                if len(lengths) + repeat > total:
                    raise _Malformed("short zero repeat exceeds tree lengths")
                lengths.extend([0] * repeat)
            elif symbol == 18:
                repeat = self.reader.read_bits(7) + 11
                if len(lengths) + repeat > total:
                    raise _Malformed("long zero repeat exceeds tree lengths")
                lengths.extend([0] * repeat)
            else:
                raise _Malformed("invalid code-length symbol")

        literal_lengths = lengths[:literal_count]
        distance_lengths = lengths[literal_count:]
        if literal_lengths[256] == 0:
            raise _Malformed("literal/length tree has no end-of-block code")

        literal_tree = _build_huffman(
            literal_lengths,
            name="literal/length",
            maximum_bits=15,
            allow_empty=False,
            allow_single_incomplete=True,
        )
        distance_tree = _build_huffman(
            distance_lengths,
            name="distance",
            maximum_bits=15,
            allow_empty=True,
            allow_single_incomplete=True,
        )
        return literal_tree, distance_tree

    def _compressed_block(self, literal_tree: _Huffman, distance_tree: _Huffman) -> None:
        while True:
            symbol = literal_tree.decode(self.reader)
            if symbol < 256:
                self._commit_byte(symbol)
                continue
            if symbol == 256:
                return
            if symbol < 257 or symbol > 285:
                raise _Malformed("reserved literal/length symbol")

            length_index = symbol - 257
            length = _LENGTH_BASE[length_index]
            length += self.reader.read_bits(_LENGTH_EXTRA[length_index])

            distance_symbol = distance_tree.decode(self.reader)
            if distance_symbol < 0 or distance_symbol >= len(_DISTANCE_BASE):
                raise _Malformed("reserved distance symbol")
            distance = _DISTANCE_BASE[distance_symbol]
            distance += self.reader.read_bits(_DISTANCE_EXTRA[distance_symbol])
            self._commit_match(length, distance)

    def decode(self) -> None:
        while True:
            final = self.reader.read_bits(1)
            block_type = self.reader.read_bits(2)
            if block_type == 0:
                self._stored_block()
            elif block_type == 1:
                self._compressed_block(_FIXED_LITERAL_TREE, _FIXED_DISTANCE_TREE)
            elif block_type == 2:
                literal_tree, distance_tree = self._dynamic_trees()
                self._compressed_block(literal_tree, distance_tree)
            else:
                raise _Malformed("reserved block type")

            if final != 0:
                return


def _capacity_prefix(boundaries: Sequence[int], capacity: Optional[int]) -> int:
    if capacity is None:
        return boundaries[-1] if boundaries else 0

    end = 0
    for boundary in boundaries:
        if boundary > capacity:
            break
        end = boundary
    return end


def decode_raw(data: bytes, output_capacity: Optional[int] = None) -> DecodeResult:
    """Decode one raw RFC 1951 stream under the experiment's frozen contract.

    The accepted input types are ``bytes``, ``bytearray``, and ``memoryview``.
    A negative output capacity is an oracle-call error rather than a malformed
    stream and therefore raises ``ValueError``.
    """

    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("data must be a bytes-like object")
    if output_capacity is not None and output_capacity < 0:
        raise ValueError("output capacity must be nonnegative")

    decoder = _Decoder(bytes(data))
    status = DONE
    error = None  # type: Optional[str]
    try:
        decoder.decode()
    except _Malformed as exc:
        status = MALFORMED
        error = str(exc)

    visible_end = _capacity_prefix(decoder.unit_boundaries, output_capacity)
    visible_boundaries = tuple(
        boundary for boundary in decoder.unit_boundaries if boundary <= visible_end
    )

    if status == DONE and visible_end != len(decoder.output):
        status = NEED_OUTPUT
        error = "next output unit does not fit"

    return DecodeResult(
        status=status,
        output=bytes(decoder.output[:visible_end]),
        unit_boundaries=visible_boundaries,
        error=error,
        input_bits_consumed=decoder.reader.bit_position,
    )


__all__ = [
    "DONE",
    "NEED_OUTPUT",
    "MALFORMED",
    "DecodeResult",
    "decode_raw",
]
