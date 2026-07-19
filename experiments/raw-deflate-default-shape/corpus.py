#!/usr/bin/env python3
"""Build the frozen deterministic raw-DEFLATE correctness corpus.

The wire fixtures are constructed independently of either native decoder.
Pinned stock zlib is used only to add public-API compressor fixtures.  Both
pinned native implementations are agreement checks for every native-compatible
valid fixture; their explicit rejection of RFC-valid HDIST boundary fixtures is
recorded rather than promoted to semantics.  ``oracle.py`` remains the semantic
authority for all fixtures and capacity-limited calls.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
import random
import shlex
import sys
import tempfile
from typing import Any, Iterable, Sequence, Union


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from oracle import DONE, MALFORMED, DecodeResult, decode_raw  # noqa: E402
import reference  # noqa: E402
import stock_zlib  # noqa: E402


SCHEMA = "whitefoot.raw-deflate.correctness-corpus.v1"
SEED = 2026071901
DEFAULT_OUTPUT = SCRIPT_DIR / "correctness-corpus.json"

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

RFC_VALID_NATIVE_REJECTED_HDIST = (
    ("dynamic-unused-distance-hdist-field-30", 30, 31, (30,)),
    ("dynamic-unused-distance-hdist-field-31", 31, 32, (30, 31)),
)


class _BitWriter:
    def __init__(self) -> None:
        self.bits: list[int] = []

    @property
    def bit_length(self) -> int:
        return len(self.bits)

    def write_bits(self, value: int, width: int) -> None:
        if width < 0 or value < 0 or value >= (1 << width if width else 1):
            raise ValueError("integer field does not fit its bit width")
        for offset in range(width):
            self.bits.append((value >> offset) & 1)

    def write_code(self, code: int, width: int) -> None:
        if width <= 0 or code < 0 or code >= 1 << width:
            raise ValueError("invalid canonical Huffman code")
        for offset in range(width - 1, -1, -1):
            self.bits.append((code >> offset) & 1)

    def align_to_byte(self) -> None:
        while len(self.bits) & 7:
            self.bits.append(0)

    def finish(self) -> bytes:
        output = bytearray((len(self.bits) + 7) // 8)
        for position, bit in enumerate(self.bits):
            output[position >> 3] |= bit << (position & 7)
        return bytes(output)


def _canonical_codes(lengths: Sequence[int]) -> dict[int, tuple[int, int]]:
    maximum = max(lengths, default=0)
    counts = [0] * (maximum + 1)
    for width in lengths:
        if width < 0:
            raise ValueError("negative Huffman width")
        if width:
            counts[width] += 1

    next_code = [0] * (maximum + 1)
    code = 0
    for width in range(1, maximum + 1):
        code = (code + counts[width - 1]) << 1
        next_code[width] = code

    result: dict[int, tuple[int, int]] = {}
    for symbol, width in enumerate(lengths):
        if width:
            result[symbol] = (next_code[width], width)
            next_code[width] += 1
    return result


def _write_symbol(
    writer: _BitWriter, codes: dict[int, tuple[int, int]], symbol: int
) -> None:
    try:
        code, width = codes[symbol]
    except KeyError as exc:
        raise ValueError(f"symbol {symbol} has no code") from exc
    writer.write_code(code, width)


def _complete_lengths(symbol_count: int) -> list[int]:
    """Return canonical widths for a complete tree with ``symbol_count`` leaves."""

    if symbol_count < 2:
        raise ValueError("a complete tree needs at least two symbols")
    long_width = math.ceil(math.log2(symbol_count))
    short_count = (1 << long_width) - symbol_count
    return [long_width - 1] * short_count + [long_width] * (
        symbol_count - short_count
    )


def _range_symbol(
    value: int, bases: Sequence[int], extras: Sequence[int]
) -> tuple[int, int, int]:
    for symbol, (base, extra) in enumerate(zip(bases, extras)):
        maximum = base + ((1 << extra) - 1 if extra else 0)
        if base <= value <= maximum:
            return symbol, value - base, extra
    raise ValueError(f"value {value} has no RFC 1951 code")


def _fixed_codes() -> tuple[dict[int, tuple[int, int]], dict[int, tuple[int, int]]]:
    literal_lengths = [0] * 288
    literal_lengths[0:144] = [8] * 144
    literal_lengths[144:256] = [9] * 112
    literal_lengths[256:280] = [7] * 24
    literal_lengths[280:288] = [8] * 8
    return _canonical_codes(literal_lengths), _canonical_codes([5] * 32)


FIXED_LITERAL_CODES, FIXED_DISTANCE_CODES = _fixed_codes()


Token = Union[int, tuple[int, int]]


def _write_compressed_tokens(
    writer: _BitWriter,
    tokens: Sequence[Token],
    literal_codes: dict[int, tuple[int, int]],
    distance_codes: dict[int, tuple[int, int]],
) -> None:
    for token in tokens:
        if isinstance(token, int):
            if not 0 <= token <= 255:
                raise ValueError("literal token is outside byte range")
            _write_symbol(writer, literal_codes, token)
            continue

        length, distance = token
        length_symbol, length_delta, length_width = _range_symbol(
            length, LENGTH_BASE, LENGTH_EXTRA
        )
        _write_symbol(writer, literal_codes, length_symbol + 257)
        writer.write_bits(length_delta, length_width)
        distance_symbol, distance_delta, distance_width = _range_symbol(
            distance, DISTANCE_BASE, DISTANCE_EXTRA
        )
        _write_symbol(writer, distance_codes, distance_symbol)
        writer.write_bits(distance_delta, distance_width)


def _write_fixed_block(
    writer: _BitWriter, tokens: Sequence[Token], *, final: bool
) -> None:
    writer.write_bits(1 if final else 0, 1)
    writer.write_bits(1, 2)
    _write_compressed_tokens(
        writer, tokens, FIXED_LITERAL_CODES, FIXED_DISTANCE_CODES
    )
    _write_symbol(writer, FIXED_LITERAL_CODES, 256)


def _fixed_stream(tokens: Sequence[Token]) -> bytes:
    writer = _BitWriter()
    _write_fixed_block(writer, tokens, final=True)
    return writer.finish()


def _write_stored_block(
    writer: _BitWriter, payload: bytes, *, final: bool
) -> None:
    if len(payload) > 65535:
        raise ValueError("stored block exceeds RFC 1951 LEN")
    writer.write_bits(1 if final else 0, 1)
    writer.write_bits(0, 2)
    writer.align_to_byte()
    writer.write_bits(len(payload), 16)
    writer.write_bits(len(payload) ^ 0xFFFF, 16)
    for value in payload:
        writer.write_bits(value, 8)


def _stored_stream(payload: bytes) -> bytes:
    writer = _BitWriter()
    _write_stored_block(writer, payload, final=True)
    return writer.finish()


LengthToken = tuple[int, int]


def _expand_length_tokens(tokens: Sequence[LengthToken]) -> list[int]:
    result: list[int] = []
    for symbol, count in tokens:
        if 0 <= symbol <= 15:
            if count != 1:
                raise ValueError("direct code-length symbols have count one")
            result.append(symbol)
        elif symbol == 16:
            if not result or not 3 <= count <= 6:
                raise ValueError("invalid repeat-previous token")
            result.extend([result[-1]] * count)
        elif symbol == 17:
            if not 3 <= count <= 10:
                raise ValueError("invalid short-zero token")
            result.extend([0] * count)
        elif symbol == 18:
            if not 11 <= count <= 138:
                raise ValueError("invalid long-zero token")
            result.extend([0] * count)
        else:
            raise ValueError("unknown code-length token")
    return result


def _direct_length_tokens(lengths: Sequence[int]) -> list[LengthToken]:
    if any(length < 0 or length > 15 for length in lengths):
        raise ValueError("tree code length is outside RFC range")
    return [(length, 1) for length in lengths]


def _code_length_tree(
    token_symbols: Iterable[int], *, count_override: int | None = None
) -> tuple[list[int], dict[int, tuple[int, int]], int]:
    used = set(token_symbols)
    if not used or any(symbol < 0 or symbol > 18 for symbol in used):
        raise ValueError("invalid code-length alphabet")

    if len(used) == 1:
        for filler in CODE_LENGTH_ORDER:
            if filler not in used:
                used.add(filler)
                break
    ordered = sorted(used)
    widths = _complete_lengths(len(ordered))
    alphabet_lengths = [0] * 19
    for symbol, width in zip(ordered, widths):
        alphabet_lengths[symbol] = width

    required_count = max(CODE_LENGTH_ORDER.index(symbol) + 1 for symbol in ordered)
    count = count_override if count_override is not None else max(4, required_count)
    if count < 4 or count > 19 or count < required_count:
        raise ValueError("HCLEN count cannot represent the code-length tree")
    return alphabet_lengths, _canonical_codes(alphabet_lengths), count


def _write_length_tokens(
    writer: _BitWriter,
    tokens: Sequence[LengthToken],
    codes: dict[int, tuple[int, int]],
) -> None:
    for symbol, count in tokens:
        _write_symbol(writer, codes, symbol)
        if symbol == 16:
            writer.write_bits(count - 3, 2)
        elif symbol == 17:
            writer.write_bits(count - 3, 3)
        elif symbol == 18:
            writer.write_bits(count - 11, 7)


def _write_dynamic_header_and_lengths(
    writer: _BitWriter,
    literal_count: int,
    distance_count: int,
    length_tokens: Sequence[LengthToken],
    *,
    final: bool,
    code_length_count: int | None = None,
    validate_tokens: bool = True,
) -> list[int]:
    if not 257 <= literal_count <= 286:
        raise ValueError("literal count is outside the legal HLIT range")
    if not 1 <= distance_count <= 32:
        raise ValueError("distance count is outside the legal HDIST range")

    alphabet_lengths, codes, count = _code_length_tree(
        (symbol for symbol, _ in length_tokens), count_override=code_length_count
    )
    writer.write_bits(1 if final else 0, 1)
    writer.write_bits(2, 2)
    writer.write_bits(literal_count - 257, 5)
    writer.write_bits(distance_count - 1, 5)
    writer.write_bits(count - 4, 4)
    for index in range(count):
        writer.write_bits(alphabet_lengths[CODE_LENGTH_ORDER[index]], 3)
    _write_length_tokens(writer, length_tokens, codes)
    return _expand_length_tokens(length_tokens) if validate_tokens else []


def _write_dynamic_block(
    writer: _BitWriter,
    literal_lengths: Sequence[int],
    distance_lengths: Sequence[int],
    tokens: Sequence[Token],
    *,
    final: bool,
    length_tokens: Sequence[LengthToken] | None = None,
    code_length_count: int | None = None,
) -> None:
    combined = list(literal_lengths) + list(distance_lengths)
    encoded_lengths = (
        list(length_tokens)
        if length_tokens is not None
        else _direct_length_tokens(combined)
    )
    expanded = _write_dynamic_header_and_lengths(
        writer,
        len(literal_lengths),
        len(distance_lengths),
        encoded_lengths,
        final=final,
        code_length_count=code_length_count,
    )
    if expanded != combined:
        raise ValueError("code-length tokens do not reconstruct the requested trees")

    literal_codes = _canonical_codes(literal_lengths)
    distance_codes = _canonical_codes(distance_lengths)
    _write_compressed_tokens(writer, tokens, literal_codes, distance_codes)
    _write_symbol(writer, literal_codes, 256)


def _dynamic_stream(
    literal_lengths: Sequence[int],
    distance_lengths: Sequence[int],
    tokens: Sequence[Token],
    *,
    length_tokens: Sequence[LengthToken] | None = None,
    code_length_count: int | None = None,
) -> bytes:
    writer = _BitWriter()
    _write_dynamic_block(
        writer,
        literal_lengths,
        distance_lengths,
        tokens,
        final=True,
        length_tokens=length_tokens,
        code_length_count=code_length_count,
    )
    return writer.finish()


def _minimal_dynamic_lengths() -> tuple[list[int], list[int]]:
    literals = [0] * 257
    literals[65] = 1
    literals[256] = 1
    return literals, [0]


def _repeated_dynamic_length_tokens() -> list[LengthToken]:
    # 65 zeroes, literal A, 190 zeroes, EOB, and one unused distance length.
    return [
        (0, 1),
        (16, 6),
        (17, 10),
        (18, 48),
        (1, 1),
        (0, 1),
        (16, 6),
        (17, 10),
        (18, 138),
        (18, 35),
        (1, 1),
        (0, 1),
    ]


def _dynamic_one_distance_stream() -> bytes:
    literals = [0] * 258
    literals[65] = 1
    literals[256] = 2
    literals[257] = 2
    return _dynamic_stream(literals, [1], [65, (3, 1)])


def _dynamic_raw_length_stream(
    literal_count: int,
    distance_count: int,
    length_tokens: Sequence[LengthToken],
    *,
    code_length_count: int | None = None,
) -> bytes:
    writer = _BitWriter()
    _write_dynamic_header_and_lengths(
        writer,
        literal_count,
        distance_count,
        length_tokens,
        final=True,
        code_length_count=code_length_count,
        validate_tokens=False,
    )
    return writer.finish()


def _append_overlap(output: bytearray, length: int, distance: int) -> None:
    if distance <= 0 or distance > len(output):
        raise ValueError("invalid expected match distance")
    for _ in range(length):
        output.append(output[-distance])


@dataclass
class _Fixture:
    id: str
    kind: str
    data: bytes
    oracle: DecodeResult
    match_boundaries: tuple[int, ...] = ()
    forced_capacities: tuple[int, ...] = ()
    notes: dict[str, Any] = field(default_factory=dict)

    def manifest_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "input_hex": self.data.hex(),
            "oracle_output_hex": self.oracle.output.hex(),
            "unit_boundaries": list(self.oracle.unit_boundaries),
            "input_bits_consumed": self.oracle.input_bits_consumed,
            "error": self.oracle.error,
        }


class _CorpusBuilder:
    def __init__(self) -> None:
        self.fixtures: list[_Fixture] = []
        self._ids: set[str] = set()

    def add(
        self,
        fixture_id: str,
        kind: str,
        data: bytes,
        *,
        expected_output: bytes | None = None,
        valid: bool | None = None,
        match_boundaries: Sequence[int] = (),
        forced_capacities: Sequence[int] = (),
        notes: dict[str, Any] | None = None,
    ) -> _Fixture:
        if fixture_id in self._ids:
            raise ValueError(f"duplicate fixture id: {fixture_id}")
        if not fixture_id or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in fixture_id):
            raise ValueError(f"non-canonical fixture id: {fixture_id}")
        result = decode_raw(data)
        if expected_output is not None and result.output != expected_output:
            raise AssertionError(
                f"{fixture_id}: oracle output mismatch ({result.error})"
            )
        if valid is True and result.status != DONE:
            raise AssertionError(f"{fixture_id}: expected valid: {result.error}")
        if valid is False and result.status != MALFORMED:
            raise AssertionError(f"{fixture_id}: expected malformed, got {result.status}")
        if any(boundary not in result.unit_boundaries for boundary in match_boundaries):
            raise AssertionError(f"{fixture_id}: match boundary is not an output boundary")
        fixture = _Fixture(
            id=fixture_id,
            kind=kind,
            data=data,
            oracle=result,
            match_boundaries=tuple(match_boundaries),
            forced_capacities=tuple(forced_capacities),
            notes={} if notes is None else dict(notes),
        )
        self._ids.add(fixture_id)
        self.fixtures.append(fixture)
        return fixture


def _payload_pattern(size: int, salt: int) -> bytes:
    return bytes(((index * 73) ^ (index >> 3) ^ salt) & 0xFF for index in range(size))


def _mutated_padding_and_trailing(stream: bytes, marker: int) -> bytes:
    result = decode_raw(stream)
    if result.status != DONE:
        raise ValueError("padding mutation requires a valid stream")
    data = bytearray(stream)
    residue = result.input_bits_consumed & 7
    if residue:
        byte_index = result.input_bits_consumed >> 3
        high_mask = 0xFF ^ ((1 << residue) - 1)
        data[byte_index] = (data[byte_index] & ~high_mask) | (marker & high_mask)
    return bytes(data) + bytes((marker & 0xFF, marker ^ 0xFF))


def _add_hand_valid_fixtures(builder: _CorpusBuilder) -> dict[str, _Fixture]:
    selected: dict[str, _Fixture] = {}

    selected["stored-empty"] = builder.add(
        "stored-empty", "stored-minimal", _stored_stream(b""), expected_output=b"", valid=True
    )
    selected["fixed-empty"] = builder.add(
        "fixed-empty", "fixed-minimal", _fixed_stream([]), expected_output=b"", valid=True
    )

    minimal_literals, minimal_distances = _minimal_dynamic_lengths()
    selected["dynamic-empty"] = builder.add(
        "dynamic-empty",
        "dynamic-minimal",
        _dynamic_stream(minimal_literals, minimal_distances, []),
        expected_output=b"",
        valid=True,
    )
    selected["dynamic-repeat-all"] = builder.add(
        "dynamic-repeat-all",
        "dynamic-repeats-16-17-18",
        _dynamic_stream(
            minimal_literals,
            minimal_distances,
            [65, 65, 65],
            length_tokens=_repeated_dynamic_length_tokens(),
        ),
        expected_output=b"AAA",
        valid=True,
    )
    selected["dynamic-hclen-max"] = builder.add(
        "dynamic-hclen-max",
        "dynamic-hclen-boundary",
        _dynamic_stream(
            minimal_literals,
            minimal_distances,
            [65],
            code_length_count=19,
        ),
        expected_output=b"A",
        valid=True,
    )
    selected["dynamic-one-distance"] = builder.add(
        "dynamic-one-distance",
        "dynamic-one-symbol-distance",
        _dynamic_one_distance_stream(),
        expected_output=b"AAAA",
        valid=True,
        match_boundaries=(4,),
    )

    max_literal_lengths = _complete_lengths(286)
    max_distance_lengths = _complete_lengths(30)
    selected["dynamic-hlit-hdist-max"] = builder.add(
        "dynamic-hlit-hdist-max",
        "dynamic-count-boundaries",
        _dynamic_stream(max_literal_lengths, max_distance_lengths, [0]),
        expected_output=b"\x00",
        valid=True,
        notes={"hlit": 286, "hdist": 30},
    )
    selected["dynamic-empty-distance-max"] = builder.add(
        "dynamic-empty-distance-max",
        "dynamic-empty-unused-distance",
        _dynamic_stream(minimal_literals, [0] * 30, [65]),
        expected_output=b"A",
        valid=True,
        notes={"hlit": 257, "hdist": 30},
    )
    for fixture_id, hdist_field, distance_count, reserved_symbols in (
        RFC_VALID_NATIVE_REJECTED_HDIST
    ):
        selected[fixture_id] = builder.add(
            fixture_id,
            "dynamic-rfc-valid-native-rejected-hdist",
            _dynamic_stream(minimal_literals, [0] * distance_count, [65]),
            expected_output=b"A",
            valid=True,
            notes={
                "hlit": 257,
                "hdist_field": hdist_field,
                "distance_count": distance_count,
                "reserved_distance_symbols_with_zero_length": list(
                    reserved_symbols
                ),
                "native_compatible": False,
            },
        )

    every_literal = bytes(range(256))
    selected["fixed-every-literal"] = builder.add(
        "fixed-every-literal",
        "all-literals",
        _fixed_stream(list(every_literal)),
        expected_output=every_literal,
        valid=True,
    )

    seen_residues: set[int] = set()
    for literal_count in range(8):
        base = _fixed_stream([144] * literal_count)
        encoded = _mutated_padding_and_trailing(base, 0xA5 ^ literal_count)
        fixture = builder.add(
            f"fixed-final-offset-{(2 + literal_count) & 7}",
            "final-bit-offset-and-trailing",
            encoded,
            expected_output=bytes([144]) * literal_count,
            valid=True,
            notes={"final_bit_offset": (2 + literal_count) & 7},
        )
        residue = fixture.oracle.input_bits_consumed & 7
        if residue in seen_residues:
            raise AssertionError("duplicate final bit offset fixture")
        seen_residues.add(residue)
    if seen_residues != set(range(8)):
        raise AssertionError("final-block endings do not cover all bit offsets")

    length_writer = _BitWriter()
    length_writer.write_bits(1, 1)
    length_writer.write_bits(1, 2)
    _write_symbol(length_writer, FIXED_LITERAL_CODES, 65)
    length_output = bytearray(b"A")
    length_match_boundaries: list[int] = []
    length_pairs: list[tuple[int, int]] = []
    for index, (base, extra) in enumerate(zip(LENGTH_BASE, LENGTH_EXTRA)):
        maximum = base + ((1 << extra) - 1 if extra else 0)
        for length in (base,) if maximum == base else (base, maximum):
            _write_symbol(length_writer, FIXED_LITERAL_CODES, index + 257)
            length_writer.write_bits(length - base, extra)
            _write_symbol(length_writer, FIXED_DISTANCE_CODES, 0)
            _append_overlap(length_output, length, 1)
            length_match_boundaries.append(len(length_output))
            length_pairs.append((index + 257, length))
    _write_symbol(length_writer, FIXED_LITERAL_CODES, 256)
    selected["fixed-length-code-boundaries"] = builder.add(
        "fixed-length-code-boundaries",
        "length-code-boundaries",
        length_writer.finish(),
        expected_output=bytes(length_output),
        valid=True,
        match_boundaries=length_match_boundaries,
        notes={"length_pairs": length_pairs},
    )

    distance_seed = _payload_pattern(32768, 0x39)
    distance_tokens: list[Token] = []
    distance_output = bytearray(distance_seed)
    distance_match_boundaries: list[int] = []
    distance_values: list[int] = []
    for base, extra in zip(DISTANCE_BASE, DISTANCE_EXTRA):
        maximum = base + ((1 << extra) - 1 if extra else 0)
        for distance in (base,) if maximum == base else (base, maximum):
            distance_tokens.append((3, distance))
            _append_overlap(distance_output, 3, distance)
            distance_match_boundaries.append(len(distance_output))
            distance_values.append(distance)
    writer = _BitWriter()
    _write_stored_block(writer, distance_seed, final=False)
    _write_fixed_block(writer, distance_tokens, final=True)
    selected["fixed-distance-code-boundaries"] = builder.add(
        "fixed-distance-code-boundaries",
        "distance-code-boundaries",
        writer.finish(),
        expected_output=bytes(distance_output),
        valid=True,
        match_boundaries=distance_match_boundaries,
        notes={"distance_values": distance_values},
    )

    distance_exact_output = bytearray(distance_seed)
    _append_overlap(distance_exact_output, 3, 32768)
    writer = _BitWriter()
    _write_stored_block(writer, distance_seed, final=False)
    _write_fixed_block(writer, [(3, 32768)], final=True)
    builder.add(
        "fixed-distance-32768-exact-history",
        "distance-window-boundary",
        writer.finish(),
        expected_output=bytes(distance_exact_output),
        valid=True,
        match_boundaries=(32771,),
    )

    semantic_cases = (
        ("fixed-overlap-distance-1", [65, (258, 1)], b"A" * 259, 259),
        ("fixed-overlap-distance-2", [65, 66, (9, 2)], b"ABABABABABA", 11),
        ("fixed-distance-equals-produced", [65, 66, 67, (3, 3)], b"ABCABC", 6),
    )
    for fixture_id, tokens, expected, boundary in semantic_cases:
        builder.add(
            fixture_id,
            "match-semantics",
            _fixed_stream(tokens),
            expected_output=expected,
            valid=True,
            match_boundaries=(boundary,),
        )

    stored_lengths = (0, 1, 2, 255, 256, 65534, 65535)
    for length in stored_lengths:
        payload = _payload_pattern(length, length & 0xFF)
        fixture_id = f"stored-len-{length}"
        if fixture_id == "stored-len-0":
            fixture_id = "stored-len-0-boundary"
        builder.add(
            fixture_id,
            "stored-len-boundary",
            _stored_stream(payload),
            expected_output=payload,
            valid=True,
            forced_capacities=(max(0, length - 1), length),
            notes={"stored_len": length},
        )

    writer = _BitWriter()
    _write_stored_block(writer, b"ABC", final=False)
    _write_fixed_block(writer, [68, 69, (3, 3)], final=False)
    _write_dynamic_block(
        writer,
        minimal_literals,
        minimal_distances,
        [65, 65],
        final=True,
        length_tokens=_repeated_dynamic_length_tokens(),
    )
    selected["mixed-blocks"] = builder.add(
        "mixed-blocks",
        "mixed-stored-fixed-dynamic",
        writer.finish(),
        expected_output=b"ABCDECDEAA",
        valid=True,
        match_boundaries=(8,),
    )

    return selected


def _add_stock_fixtures(
    builder: _CorpusBuilder, adapter: Any
) -> dict[str, _Fixture]:
    random_source = random.Random(SEED)
    payloads = {
        "text": (b"Whitefoot raw DEFLATE default-shape corpus.\n" * 113)
        + bytes(range(64)),
        "binary": bytes(random_source.randrange(256) for _ in range(4096)),
        "runs": (b"A" * 1536) + (b"ABCD" * 512) + (b"\x00\xff" * 511),
    }
    selected: dict[str, _Fixture] = {}
    for level in stock_zlib.LEVELS:
        for strategy in stock_zlib.STRATEGIES:
            strategy_name = stock_zlib.STRATEGY_NAMES[strategy]
            strategy_id = strategy_name.removeprefix("Z_").lower().replace("_", "-")
            for payload_name, payload in payloads.items():
                compressed = stock_zlib.compress_raw(adapter, payload, level, strategy)
                repeated = stock_zlib.compress_raw(adapter, payload, level, strategy)
                if compressed != repeated:
                    raise AssertionError("pinned stock zlib emitted nondeterministic bytes")
                fixture_id = f"stock-zlib-l{level}-{strategy_id}-{payload_name}"
                fixture = builder.add(
                    fixture_id,
                    "stock-zlib",
                    compressed,
                    expected_output=payload,
                    valid=True,
                    notes={
                        "level": level,
                        "strategy": strategy_name,
                        "payload": payload_name,
                    },
                )
                selected[fixture_id] = fixture
    return selected


def _raw_dynamic_header(literal_field: int, distance_field: int, hclen_field: int) -> bytes:
    writer = _BitWriter()
    writer.write_bits(1, 1)
    writer.write_bits(2, 2)
    writer.write_bits(literal_field, 5)
    writer.write_bits(distance_field, 5)
    writer.write_bits(hclen_field, 4)
    return writer.finish()


def _bad_code_length_header(widths: dict[int, int], count: int) -> bytes:
    writer = _BitWriter()
    writer.write_bits(1, 1)
    writer.write_bits(2, 2)
    writer.write_bits(0, 5)
    writer.write_bits(0, 5)
    writer.write_bits(count - 4, 4)
    for index in range(count):
        writer.write_bits(widths.get(CODE_LENGTH_ORDER[index], 0), 3)
    return writer.finish()


def _add_malformed_fixtures(
    builder: _CorpusBuilder, valid_selected: dict[str, _Fixture]
) -> None:
    builder.add("malformed-empty-input", "truncation", b"", valid=False)
    builder.add("malformed-reserved-block", "reserved-block", b"\x07", valid=False)
    builder.add(
        "malformed-stored-len-mismatch",
        "stored-len-mismatch",
        bytes.fromhex("010100000041"),
        valid=False,
    )
    builder.add(
        "malformed-stored-truncated-payload",
        "truncation",
        bytes.fromhex("010300fcff4142"),
        valid=False,
    )

    for field in (30, 31):
        builder.add(
            f"malformed-hlit-reserved-{field}",
            "dynamic-reserved-hlit",
            _raw_dynamic_header(field, 0, 0),
            valid=False,
        )

    # Keep symbol-use violations distinct from the valid zero-length reserved
    # symbols above.  These streams actually decode distance symbol 30 or 31,
    # so the oracle reaches the symbol-level RFC violation.  The declared
    # distance counts alone are not what makes these fixtures malformed.
    reserved_literal_lengths = [0] * 258
    reserved_literal_lengths[65] = 1
    reserved_literal_lengths[256] = 2
    reserved_literal_lengths[257] = 2
    for distance_count, reserved_symbol in ((31, 30), (32, 31)):
        reserved_distance_lengths = _complete_lengths(distance_count)
        writer = _BitWriter()
        _write_dynamic_header_and_lengths(
            writer,
            len(reserved_literal_lengths),
            len(reserved_distance_lengths),
            _direct_length_tokens(
                reserved_literal_lengths + reserved_distance_lengths
            ),
            final=True,
        )
        literal_codes = _canonical_codes(reserved_literal_lengths)
        distance_codes = _canonical_codes(reserved_distance_lengths)
        _write_symbol(writer, literal_codes, 65)
        _write_symbol(writer, literal_codes, 257)
        _write_symbol(writer, distance_codes, reserved_symbol)
        builder.add(
            f"malformed-hdist-count-{distance_count}",
            "dynamic-reserved-hdist-boundary",
            writer.finish(),
            valid=False,
        )

    builder.add(
        "malformed-code-length-empty",
        "dynamic-invalid-code-length-tree",
        _bad_code_length_header({}, 4),
        valid=False,
    )
    builder.add(
        "malformed-code-length-incomplete",
        "dynamic-incomplete-code-length-tree",
        _bad_code_length_header({0: 2, 1: 2}, 18),
        valid=False,
    )
    builder.add(
        "malformed-code-length-oversubscribed",
        "dynamic-oversubscribed-code-length-tree",
        _bad_code_length_header({16: 1, 17: 1, 18: 1}, 4),
        valid=False,
    )

    missing_end_lengths = [0] * 258
    missing_end_lengths[65] = 1
    missing_end_lengths[66] = 1
    builder.add(
        "malformed-dynamic-missing-eob",
        "dynamic-missing-eob",
        _dynamic_raw_length_stream(
            257, 1, _direct_length_tokens(missing_end_lengths)
        ),
        valid=False,
    )

    incomplete_literal_lengths = [0] * 258
    incomplete_literal_lengths[65] = 2
    incomplete_literal_lengths[256] = 2
    builder.add(
        "malformed-dynamic-literal-incomplete",
        "dynamic-incomplete-literal-tree",
        _dynamic_raw_length_stream(
            257, 1, _direct_length_tokens(incomplete_literal_lengths)
        ),
        valid=False,
    )
    oversubscribed_literal_lengths = [0] * 258
    oversubscribed_literal_lengths[65] = 1
    oversubscribed_literal_lengths[66] = 1
    oversubscribed_literal_lengths[256] = 1
    builder.add(
        "malformed-dynamic-literal-oversubscribed",
        "dynamic-oversubscribed-literal-tree",
        _dynamic_raw_length_stream(
            257, 1, _direct_length_tokens(oversubscribed_literal_lengths)
        ),
        valid=False,
    )

    valid_literal_match = [0] * 258
    valid_literal_match[65] = 1
    valid_literal_match[256] = 2
    valid_literal_match[257] = 2
    for name, distances in (
        ("incomplete", [2, 2]),
        ("oversubscribed", [1, 1, 1]),
    ):
        combined = valid_literal_match + distances
        builder.add(
            f"malformed-dynamic-distance-{name}",
            f"dynamic-{name}-distance-tree",
            _dynamic_raw_length_stream(
                len(valid_literal_match),
                len(distances),
                _direct_length_tokens(combined),
            ),
            valid=False,
        )

    builder.add(
        "malformed-repeat-16-first",
        "dynamic-illegal-repeat-16",
        _dynamic_raw_length_stream(257, 1, [(16, 3)]),
        valid=False,
    )
    builder.add(
        "malformed-repeat-16-overflow",
        "dynamic-illegal-repeat-16",
        _dynamic_raw_length_stream(257, 1, [(1, 1)] + [(16, 6)] * 43),
        valid=False,
    )
    builder.add(
        "malformed-repeat-17-overflow",
        "dynamic-illegal-repeat-17",
        _dynamic_raw_length_stream(257, 1, [(17, 10)] * 26),
        valid=False,
    )
    builder.add(
        "malformed-repeat-18-overflow",
        "dynamic-illegal-repeat-18",
        _dynamic_raw_length_stream(257, 1, [(18, 138), (18, 138)]),
        valid=False,
    )

    builder.add(
        "malformed-fixed-impossible-distance",
        "impossible-distance",
        _fixed_stream([(3, 1)]),
        valid=False,
    )
    for symbol in (286, 287):
        writer = _BitWriter()
        writer.write_bits(1, 1)
        writer.write_bits(1, 2)
        _write_symbol(writer, FIXED_LITERAL_CODES, symbol)
        builder.add(
            f"malformed-fixed-reserved-length-{symbol}",
            "reserved-length-symbol",
            writer.finish(),
            valid=False,
        )
    for symbol in (30, 31):
        writer = _BitWriter()
        writer.write_bits(1, 1)
        writer.write_bits(1, 2)
        _write_symbol(writer, FIXED_LITERAL_CODES, 65)
        _write_symbol(writer, FIXED_LITERAL_CODES, 257)
        _write_symbol(writer, FIXED_DISTANCE_CODES, symbol)
        builder.add(
            f"malformed-fixed-reserved-distance-{symbol}",
            "reserved-distance-symbol",
            writer.finish(),
            valid=False,
        )

    # Complete trees followed by a truncated data code exercise missing EOB
    # independently of the dynamic-tree missing-EOB declaration above.
    literals, distances = _minimal_dynamic_lengths()
    complete = _dynamic_stream(literals, distances, [65, 65, 65])
    builder.add(
        "malformed-dynamic-data-missing-eob",
        "missing-end-of-block-data",
        complete[:-1],
        valid=False,
    )

    truncation_targets = (
        valid_selected["dynamic-repeat-all"],
        valid_selected["mixed-blocks"],
        valid_selected["fixed-empty"],
    )
    for target in truncation_targets:
        for end in range(len(target.data)):
            builder.add(
                f"truncate-{target.id}-{end}",
                "truncation-structural",
                target.data[:end],
                valid=False,
            )

    large_stored = _stored_stream(_payload_pattern(65535, 0x71))
    selected_ends = sorted(
        {0, 1, 2, 3, 4, 5, 6, 255, 256, len(large_stored) - 2, len(large_stored) - 1}
    )
    for end in selected_ends:
        builder.add(
            f"truncate-stored-len-65535-{end}",
            "truncation-stored-boundary",
            large_stored[:end],
            valid=False,
        )


def _mutation_positions(length: int, rng: random.Random, count: int) -> list[int]:
    if length <= 0:
        return [0]
    candidates = {0, length - 1, length // 2}
    while len(candidates) < min(count, length):
        candidates.add(rng.randrange(length))
    return sorted(candidates)


def _add_mutations(builder: _CorpusBuilder, bases: Sequence[_Fixture]) -> None:
    rng = random.Random(SEED ^ 0x5A17C0DE)
    for base in bases:
        data = base.data
        byte_positions = _mutation_positions(len(data), rng, 7)

        bit_candidates = {0, max(0, len(data) * 8 - 1), len(data) * 4}
        while len(bit_candidates) < min(16, max(1, len(data) * 8)):
            bit_candidates.add(rng.randrange(max(1, len(data) * 8)))
        for index, bit_position in enumerate(sorted(bit_candidates)):
            if not data:
                continue
            mutated = bytearray(data)
            mutated[bit_position >> 3] ^= 1 << (bit_position & 7)
            result = decode_raw(mutated)
            classification = "valid" if result.status == DONE else "malformed"
            builder.add(
                f"mutation-flip-{base.id}-{index}",
                f"mutation-flip-{classification}",
                bytes(mutated),
            )

        insertion_positions = sorted(set(byte_positions + [len(data)]))[:8]
        for index, position in enumerate(insertion_positions):
            value = rng.randrange(256)
            mutated = data[:position] + bytes((value,)) + data[position:]
            result = decode_raw(mutated)
            classification = "valid" if result.status == DONE else "malformed"
            builder.add(
                f"mutation-insert-{base.id}-{index}",
                f"mutation-insert-{classification}",
                mutated,
            )

        for index, position in enumerate(byte_positions):
            if not data:
                continue
            deleted = data[:position] + data[position + 1 :]
            deleted_result = decode_raw(deleted)
            deleted_class = "valid" if deleted_result.status == DONE else "malformed"
            builder.add(
                f"mutation-delete-{base.id}-{index}",
                f"mutation-delete-{deleted_class}",
                deleted,
            )

            duplicated = data[:position] + data[position : position + 1] + data[position:]
            duplicated_result = decode_raw(duplicated)
            duplicate_class = (
                "valid" if duplicated_result.status == DONE else "malformed"
            )
            builder.add(
                f"mutation-duplicate-{base.id}-{index}",
                f"mutation-duplicate-{duplicate_class}",
                duplicated,
            )

        truncate_positions = sorted(
            {0, 1, len(data) // 4, len(data) // 2, max(0, len(data) - 1)}
        )
        for index, end in enumerate(truncate_positions):
            mutated = data[:end]
            result = decode_raw(mutated)
            classification = "valid" if result.status == DONE else "malformed"
            builder.add(
                f"mutation-truncate-{base.id}-{index}",
                f"mutation-truncate-{classification}",
                mutated,
            )


def _calls_for_fixture(fixture: _Fixture) -> list[int]:
    output_length = len(fixture.oracle.output)
    capacities: set[int] = set(fixture.forced_capacities)
    if fixture.kind == "stock-zlib" or fixture.kind.startswith("mutation-"):
        capacities.update((0, min(1, output_length)))
    else:
        capacities.update(range(0, min(16, output_length) + 1))
    capacities.update((output_length, output_length + 17))
    if fixture.oracle.status == DONE:
        for boundary in fixture.match_boundaries:
            capacities.update((max(0, boundary - 1), boundary, boundary + 1))
    else:
        capacities.update((0, min(1, output_length), output_length, output_length + 17))
    return sorted(capacity for capacity in capacities if capacity >= 0)


def _cross_check_valid_fixtures(
    fixtures: Sequence[_Fixture], stock_adapter: Any, zng_adapter: Any
) -> dict[str, Any]:
    oracle_valid = 0
    compatible_checked = 0
    compatible_calls = 0
    native_calls = 0
    rejected_observations: list[dict[str, Any]] = []
    expected_rejected_ids = {
        fixture_id
        for fixture_id, _, _, _ in RFC_VALID_NATIVE_REJECTED_HDIST
    }
    observed_rejected_ids: set[str] = set()

    def observation(status: int, output: bytes) -> dict[str, Any]:
        names = {
            0: "Done",
            1: "NeedOutput",
            2: "Malformed",
            3: "AdapterError",
        }
        return {
            "status": status,
            "status_name": names.get(status, "Unknown"),
            "produced": len(output),
            "output_hex": output.hex(),
        }

    for fixture in fixtures:
        if fixture.oracle.status != DONE:
            continue
        oracle_valid += 1
        expected = fixture.oracle.output
        native_compatible = fixture.notes.get("native_compatible", True)
        # A zero-byte DEFLATE result still gets one byte of writable space for
        # the native public APIs.  No output byte is semantically visible.
        capacities = (max(1, len(expected)), len(expected) + 17)
        fixture_observations: list[dict[str, Any]] = []
        for capacity in capacities:
            stock_status, stock_output = stock_zlib.inflate_full(
                stock_adapter, fixture.data, capacity
            )
            zng_status, zng_output = reference.inflate_once(
                zng_adapter, fixture.data, capacity
            )
            native_calls += 2
            if native_compatible:
                if (
                    stock_status != stock_zlib.STOCK_DONE
                    or stock_output != expected
                ):
                    raise AssertionError(
                        f"{fixture.id}: stock zlib disagrees at capacity {capacity}: "
                        f"status={stock_status}, produced={len(stock_output)}"
                    )
                if zng_status != reference.WF_RAW_DONE or zng_output != expected:
                    raise AssertionError(
                        f"{fixture.id}: zlib-ng disagrees at capacity {capacity}: "
                        f"status={zng_status}, produced={len(zng_output)}"
                    )
                compatible_calls += 2
            else:
                if stock_status != stock_zlib.STOCK_MALFORMED or stock_output:
                    raise AssertionError(
                        f"{fixture.id}: pinned stock-zlib rejection drifted at "
                        f"capacity {capacity}: status={stock_status}, "
                        f"produced={len(stock_output)}"
                    )
                if zng_status != reference.WF_RAW_MALFORMED or zng_output:
                    raise AssertionError(
                        f"{fixture.id}: pinned zlib-ng rejection drifted at "
                        f"capacity {capacity}: status={zng_status}, "
                        f"produced={len(zng_output)}"
                    )
                fixture_observations.append(
                    {
                        "capacity": capacity,
                        "stock_zlib": observation(stock_status, stock_output),
                        "zlib_ng": observation(zng_status, zng_output),
                    }
                )
        if native_compatible:
            compatible_checked += 1
        else:
            observed_rejected_ids.add(fixture.id)
            rejected_observations.append(
                {
                    "fixture": fixture.id,
                    "oracle_status": {"name": "Done", "value": DONE},
                    "oracle_output_hex": expected.hex(),
                    "hdist_field": fixture.notes["hdist_field"],
                    "declared_distance_lengths": fixture.notes[
                        "distance_count"
                    ],
                    "reserved_distance_symbols_with_zero_length": fixture.notes[
                        "reserved_distance_symbols_with_zero_length"
                    ],
                    "native_observations": fixture_observations,
                }
            )

    if observed_rejected_ids != expected_rejected_ids:
        raise AssertionError(
            "RFC-valid native-rejected fixture set drifted: "
            f"got {sorted(observed_rejected_ids)}, "
            f"expected {sorted(expected_rejected_ids)}"
        )
    return {
        "valid_fixture_count": oracle_valid,
        "native_compatible_valid_fixture_count": compatible_checked,
        "native_rejected_rfc_valid_fixture_count": len(rejected_observations),
        "native_call_count": native_calls,
        "native_compatible_call_count": compatible_calls,
        "native_rejection_observation_call_count": (
            native_calls - compatible_calls
        ),
        "capacities": "max(1, exact output length) and output length plus 17",
        "capacity_limited_prefixes": "not compared with native implementations",
        "policy": (
            "Require Done and exact output for every native-compatible "
            "oracle-valid fixture. Record the pinned native rejection of the "
            "listed RFC-valid fixtures without reclassifying them."
        ),
        "native_rejected_rfc_valid_fixtures": rejected_observations,
    }


def _stable_provenance(
    stock_provenance: dict[str, Any], zng_provenance: dict[str, Any]
) -> dict[str, Any]:
    return {
        "stock_zlib": {
            "version": stock_provenance["version"],
            "tag": stock_provenance["tag"],
            "commit": stock_provenance["commit"],
            "tree": stock_provenance["tree"],
            "source_header_sha256": stock_provenance["source_header_sha256"],
            "generated_header_sha256": stock_provenance[
                "generated_header_sha256"
            ],
            "cmake_cache_sha256": stock_provenance["cmake_cache_sha256"],
            "shared_library_sha256": stock_provenance["shared_library_sha256"],
        },
        "zlib_ng": {
            "version": zng_provenance["version"],
            "commit": zng_provenance["commit"],
            "tree": zng_provenance["tree"],
            "generated_header_sha256": zng_provenance[
                "generated_header_sha256"
            ],
            "shared_library_sha256": zng_provenance["shared_library_sha256"],
        },
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("ascii")


def _assert_coverage(fixtures: Sequence[_Fixture], calls: Sequence[dict[str, Any]]) -> dict[str, Any]:
    kinds = Counter(fixture.kind for fixture in fixtures)
    statuses = Counter(
        "valid" if fixture.oracle.status == DONE else "malformed"
        for fixture in fixtures
    )
    by_id = {fixture.id: fixture for fixture in fixtures}

    if by_id["fixed-every-literal"].oracle.output != bytes(range(256)):
        raise AssertionError("all-literal fixture lost byte coverage")
    offsets = {
        fixture.oracle.input_bits_consumed & 7
        for fixture in fixtures
        if fixture.kind == "final-bit-offset-and-trailing"
    }
    if offsets != set(range(8)):
        raise AssertionError("final bit-offset coverage is incomplete")
    length_pairs = by_id["fixed-length-code-boundaries"].notes["length_pairs"]
    distance_values = by_id["fixed-distance-code-boundaries"].notes[
        "distance_values"
    ]
    expected_length_pairs = {
        (index + 257, value)
        for index, (base, extra) in enumerate(zip(LENGTH_BASE, LENGTH_EXTRA))
        for value in (base, base + ((1 << extra) - 1 if extra else 0))
    }
    expected_distances = {
        value
        for base, extra in zip(DISTANCE_BASE, DISTANCE_EXTRA)
        for value in (base, base + ((1 << extra) - 1 if extra else 0))
    }
    if set(length_pairs) != expected_length_pairs:
        raise AssertionError("length code base/max coverage is incomplete")
    if set(distance_values) != expected_distances:
        raise AssertionError("distance code base/max coverage is incomplete")
    stored_lengths = {
        fixture.notes["stored_len"]
        for fixture in fixtures
        if fixture.kind == "stored-len-boundary"
    }
    if stored_lengths != {0, 1, 2, 255, 256, 65534, 65535}:
        raise AssertionError("stored LEN boundary coverage is incomplete")

    native_rejected_hdist_fields: list[int] = []
    native_rejected_distance_counts: list[int] = []
    native_rejected_ids: list[str] = []
    for fixture_id, hdist_field, distance_count, reserved_symbols in (
        RFC_VALID_NATIVE_REJECTED_HDIST
    ):
        fixture = by_id.get(fixture_id)
        if fixture is None or fixture.oracle.status != DONE:
            raise AssertionError(
                f"missing RFC-valid native-rejected fixture: {fixture_id}"
            )
        if fixture.kind != "dynamic-rfc-valid-native-rejected-hdist":
            raise AssertionError(f"{fixture_id}: unexpected fixture class")
        if fixture.notes != {
            "hlit": 257,
            "hdist_field": hdist_field,
            "distance_count": distance_count,
            "reserved_distance_symbols_with_zero_length": list(
                reserved_symbols
            ),
            "native_compatible": False,
        }:
            raise AssertionError(f"{fixture_id}: HDIST boundary metadata drift")
        native_rejected_ids.append(fixture_id)
        native_rejected_hdist_fields.append(hdist_field)
        native_rejected_distance_counts.append(distance_count)

    reserved_use_ids = {
        fixture.id
        for fixture in fixtures
        if fixture.kind == "dynamic-reserved-hdist-boundary"
    }
    if reserved_use_ids != {
        "malformed-hdist-count-31",
        "malformed-hdist-count-32",
    }:
        raise AssertionError("reserved distance-symbol-use fixtures drifted")
    if any(by_id[fixture_id].oracle.status != MALFORMED for fixture_id in reserved_use_ids):
        raise AssertionError("reserved distance-symbol-use fixture became valid")

    stock_configs = {
        (fixture.notes["level"], fixture.notes["strategy"])
        for fixture in fixtures
        if fixture.kind == "stock-zlib"
    }
    expected_configs = {
        (level, stock_zlib.STRATEGY_NAMES[strategy])
        for level in stock_zlib.LEVELS
        for strategy in stock_zlib.STRATEGIES
    }
    if stock_configs != expected_configs or kinds["stock-zlib"] != 60:
        raise AssertionError("stock-zlib level/strategy coverage is incomplete")

    required_kinds = {
        "stored-minimal",
        "fixed-minimal",
        "dynamic-minimal",
        "dynamic-repeats-16-17-18",
        "dynamic-one-symbol-distance",
        "dynamic-empty-unused-distance",
        "dynamic-rfc-valid-native-rejected-hdist",
        "mixed-stored-fixed-dynamic",
        "reserved-block",
        "stored-len-mismatch",
        "dynamic-incomplete-code-length-tree",
        "dynamic-oversubscribed-code-length-tree",
        "dynamic-incomplete-literal-tree",
        "dynamic-oversubscribed-literal-tree",
        "dynamic-illegal-repeat-16",
        "dynamic-illegal-repeat-17",
        "dynamic-illegal-repeat-18",
        "reserved-length-symbol",
        "reserved-distance-symbol",
        "impossible-distance",
    }
    missing = sorted(kind for kind in required_kinds if kinds[kind] == 0)
    if missing:
        raise AssertionError(f"required fixture classes are missing: {missing}")

    mutation_operations = {
        kind.split("-")[1]
        for kind in kinds
        if kind.startswith("mutation-")
    }
    if mutation_operations != {"flip", "insert", "delete", "duplicate", "truncate"}:
        raise AssertionError("mutation operation coverage is incomplete")

    call_pairs = {(call["fixture"], call["capacity"]) for call in calls}
    if len(call_pairs) != len(calls):
        raise AssertionError("duplicate corpus calls")
    for fixture in fixtures:
        output_length = len(fixture.oracle.output)
        if (fixture.id, output_length) not in call_pairs:
            raise AssertionError(f"{fixture.id}: exact-capacity call is missing")
        if (fixture.id, output_length + 17) not in call_pairs:
            raise AssertionError(f"{fixture.id}: surplus-capacity call is missing")
        for boundary in fixture.match_boundaries:
            for capacity in (max(0, boundary - 1), boundary):
                if (fixture.id, capacity) not in call_pairs:
                    raise AssertionError(
                        f"{fixture.id}: whole-match boundary call {capacity} is missing"
                    )

    if len(fixtures) >= 1000 or len(calls) >= 3000:
        raise AssertionError(
            f"correctness corpus exceeded its size target: "
            f"{len(fixtures)} fixtures, {len(calls)} calls"
        )
    return {
        "fixture_kinds": dict(sorted(kinds.items())),
        "fixture_statuses": dict(sorted(statuses.items())),
        "final_bit_offsets": sorted(offsets),
        "length_symbol_boundary_pairs": len(expected_length_pairs),
        "unique_distance_boundary_values": len(expected_distances),
        "stored_len_values": sorted(stored_lengths),
        "rfc_valid_native_rejected_fixture_ids": native_rejected_ids,
        "rfc_valid_native_rejected_hdist_fields": native_rejected_hdist_fields,
        "rfc_valid_native_rejected_distance_counts": (
            native_rejected_distance_counts
        ),
        "stock_level_strategy_configurations": len(stock_configs),
        "mutation_operations": sorted(mutation_operations),
    }


def _build_manifest(
    stock_adapter: Any,
    zng_adapter: Any,
    stock_provenance: dict[str, Any],
    zng_provenance: dict[str, Any],
) -> dict[str, Any]:
    builder = _CorpusBuilder()
    selected = _add_hand_valid_fixtures(builder)
    stock_selected = _add_stock_fixtures(builder, stock_adapter)
    selected.update(stock_selected)
    _add_malformed_fixtures(builder, selected)

    mutation_bases = (
        selected["dynamic-repeat-all"],
        selected["mixed-blocks"],
        selected["fixed-length-code-boundaries"],
        stock_selected["stock-zlib-l6-default-strategy-text"],
    )
    _add_mutations(builder, mutation_bases)

    calls = [
        {"fixture": fixture.id, "capacity": capacity}
        for fixture in builder.fixtures
        for capacity in _calls_for_fixture(fixture)
    ]
    coverage = _assert_coverage(builder.fixtures, calls)
    cross_check = _cross_check_valid_fixtures(
        builder.fixtures, stock_adapter, zng_adapter
    )

    fixture_records = [fixture.manifest_record() for fixture in builder.fixtures]
    payload_hash = hashlib.sha256(
        _canonical_bytes({"fixtures": fixture_records, "calls": calls})
    ).hexdigest()
    input_hash = hashlib.sha256()
    for fixture in builder.fixtures:
        input_hash.update(len(fixture.data).to_bytes(8, "little"))
        input_hash.update(fixture.data)

    statuses = Counter(
        "valid" if fixture.oracle.status == DONE else "malformed"
        for fixture in builder.fixtures
    )
    manifest = {
        "schema": SCHEMA,
        "seed": SEED,
        "metadata": {
            "generator_sha256": _sha256(Path(__file__).resolve()),
            "oracle_sha256": _sha256(SCRIPT_DIR / "oracle.py"),
            "stock_adapter_source_sha256": _sha256(SCRIPT_DIR / "stock_zlib.c"),
            "stock_helper_sha256": _sha256(SCRIPT_DIR / "stock_zlib.py"),
            "zlib_ng_adapter_source_sha256": _sha256(SCRIPT_DIR / "reference.c"),
            "zlib_ng_helper_sha256": _sha256(SCRIPT_DIR / "reference.py"),
            "native_provenance": _stable_provenance(
                stock_provenance, zng_provenance
            ),
            "cross_check": cross_check,
            "coverage": coverage,
            "fixture_payload_sha256": payload_hash,
            "input_sequence_sha256": input_hash.hexdigest(),
            "capacity_policy": (
                "Structural hand fixtures use 0 through min(16, output length); "
                "stock and mutation fixtures use 0 and 1. Every fixture adds "
                "exact and plus 17; hand fixtures add forced boundaries and "
                "before/at/after every declared whole match."
            ),
        },
        "counts": {
            "fixtures": len(builder.fixtures),
            "calls": len(calls),
            "valid_fixtures": statuses["valid"],
            "malformed_fixtures": statuses["malformed"],
            "input_bytes": sum(len(fixture.data) for fixture in builder.fixtures),
            "oracle_output_bytes": sum(
                len(fixture.oracle.output) for fixture in builder.fixtures
            ),
        },
        "fixtures": fixture_records,
        "calls": calls,
    }
    return manifest


def _build_adapters(args: argparse.Namespace) -> tuple[Any, Any, dict[str, Any], dict[str, Any], tempfile.TemporaryDirectory[str]]:
    stock_checkout = args.stock_checkout.resolve()
    stock_build = args.stock_build.resolve()
    stock_library = (
        args.stock_library.resolve()
        if args.stock_library is not None
        else stock_zlib.find_library(stock_build)
    )
    zng_checkout = args.zng_checkout.resolve()
    zng_build = args.zng_build.resolve()
    zng_library = (
        args.zng_library.resolve()
        if args.zng_library is not None
        else reference.find_library(zng_build)
    )

    stock_provenance = stock_zlib.verify_provenance(
        stock_checkout, stock_build, stock_library
    )
    zng_provenance = reference.verify_provenance(
        zng_checkout, zng_build, zng_library
    )
    compiler = shlex.split(args.cc)
    temporary = tempfile.TemporaryDirectory(prefix="whitefoot-raw-deflate-corpus-")
    temporary_path = Path(temporary.name)
    suffix = ".dylib" if sys.platform == "darwin" else ".so"

    stock_output = temporary_path / f"libstock_adapter{suffix}"
    stock_zlib.build_adapter(
        SCRIPT_DIR / "stock_zlib.c",
        stock_checkout,
        stock_build,
        stock_library,
        stock_output,
        compiler,
    )
    stock_adapter = stock_zlib.load_adapter(stock_output)

    zng_output = temporary_path / f"libzng_adapter{suffix}"
    reference.build_adapter(
        SCRIPT_DIR / "reference.c",
        zng_checkout,
        zng_build,
        zng_library,
        zng_output,
        compiler,
    )
    zng_adapter = reference.load_adapter(zng_output)
    return stock_adapter, zng_adapter, stock_provenance, zng_provenance, temporary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="regenerate in memory and require byte identity with --output",
    )
    parser.add_argument(
        "--stock-checkout",
        type=Path,
        default=stock_zlib.DEFAULT_RESEARCH_ROOT / "zlib",
    )
    parser.add_argument(
        "--stock-build",
        type=Path,
        default=stock_zlib.DEFAULT_RESEARCH_ROOT / "build-zlib",
    )
    parser.add_argument("--stock-library", type=Path)
    parser.add_argument(
        "--zng-checkout",
        type=Path,
        default=reference.DEFAULT_RESEARCH_ROOT / "zlib-ng",
    )
    parser.add_argument(
        "--zng-build",
        type=Path,
        default=reference.DEFAULT_RESEARCH_ROOT / "build-zng-dispatch",
    )
    parser.add_argument("--zng-library", type=Path)
    parser.add_argument("--cc", default="cc")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    (
        stock_adapter,
        zng_adapter,
        stock_provenance,
        zng_provenance,
        temporary,
    ) = _build_adapters(args)
    try:
        manifest = _build_manifest(
            stock_adapter, zng_adapter, stock_provenance, zng_provenance
        )
        encoded = _canonical_bytes(manifest)
    finally:
        temporary.cleanup()

    if len(encoded) >= 10 * 1024 * 1024:
        raise RuntimeError(
            f"canonical corpus is {len(encoded)} bytes, exceeding the 10 MiB target"
        )
    output = args.output.resolve()
    digest = hashlib.sha256(encoded).hexdigest()
    if args.check:
        if not output.is_file():
            raise RuntimeError(f"missing corpus for --check: {output}")
        existing = output.read_bytes()
        if existing != encoded:
            raise RuntimeError(
                f"corpus is not byte-identical: existing {hashlib.sha256(existing).hexdigest()}, "
                f"regenerated {digest}"
            )
        action = "checked"
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded)
        action = "wrote"

    print(
        json.dumps(
            {
                "action": action,
                "path": str(output),
                "sha256": digest,
                "bytes": len(encoded),
                "fixtures": manifest["counts"]["fixtures"],
                "calls": manifest["counts"]["calls"],
                "valid": manifest["counts"]["valid_fixtures"],
                "malformed": manifest["counts"]["malformed_fixtures"],
                "generator_sha256": manifest["metadata"]["generator_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
