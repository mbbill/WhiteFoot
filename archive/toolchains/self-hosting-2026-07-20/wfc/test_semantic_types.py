#!/usr/bin/env python3
"""Exercise fail-closed, exact structural comparison of parsed type shapes."""

import ctypes
import tempfile
from contextlib import contextmanager
from pathlib import Path

from test_lexer import Buffer, TokenTape, build_library
from test_parser import AST_NONE, AstTape, parse


AST_RETURN_TYPE = 4
AST_PARAMETER_TYPE = 10
AST_BINDING_TYPE = 13
AST_TYPE_ARGUMENT = 17
AST_NESTED_TYPE = 23
AST_FIELD_TYPE = 35
AST_CONST_TYPE = 38
PARSE_CLEAN = 0
U64_GUARD = 0xA5A5A5A5A5A5A5A5


class TypeShapeScratch(ctypes.Structure):
    _fields_ = [
        ("left_stack", Buffer),
        ("right_stack", Buffer),
        ("left_marks", Buffer),
        ("right_marks", Buffer),
        ("generation", ctypes.c_uint64),
    ]


def fixture():
    return (
        b"struct Shapes {\n"
        b"  byte: u8;\n"
        b"  wide: u64;\n"
        b"  bytes: buffer<u8>;\n"
        b"  words: buffer<u64>;\n"
        b"  ten: array<u8, 10>;\n"
        b"  eleven: array<u8, 11>;\n"
        b"  named: Thing;\n"
        b"  other: Other;\n"
        b"}\n"
        b"const byte_buffer: buffer<u8> = 0_u64;\n"
        b"const ten_array: array<u8, 10> = [0_u8];\n"
        b"fn compare (param: own buffer<u8>, arr: own array<u8, 10>, named: own Thing) -> own buffer<u8> pure {\n"
        b"  let local: own buffer<u8> = param;\n"
        b"  let other_array: own array<u8, 11> = arr;\n"
        b"  let size: own u64 = len<u8>(param);\n"
        b"  return param;\n"
        b"}\n"
    )


def make_scratch(count, advertised=None):
    if advertised is None:
        advertised = (count, count, count, count)
    physical = max(1, count)
    arrays = tuple((ctypes.c_uint64 * (physical + 1))() for _ in range(4))
    for array in arrays:
        array[physical] = U64_GUARD
    scratch = TypeShapeScratch(
        *(
            Buffer(ctypes.cast(array, ctypes.c_void_p), length)
            for array, length in zip(arrays, advertised)
        ),
        0,
    )
    return arrays, physical, scratch


def assert_scratch_guards(arrays, physical):
    assert all(array[physical] == U64_GUARD for array in arrays)


def find_node(data, columns, kind, text, occurrence=0):
    kinds, _, starts, ends, _, _, _ = columns
    matches = [
        node
        for node in range(len(kinds) - 1)
        if kinds[node] == kind and data[starts[node] : ends[node]] == text
    ]
    assert len(matches) > occurrence, (kind, text, matches)
    return matches[occurrence]


@contextmanager
def changed(column, index, value):
    before = column[index]
    column[index] = value
    try:
        yield
    finally:
        column[index] = before


def assert_valid_shapes(library):
    data = fixture()
    source_storage, _, tokens, columns, ast = parse(library, data)
    assert ast.status == PARSE_CLEAN
    source = Buffer(ctypes.cast(source_storage, ctypes.c_void_p), len(data))
    arrays, physical, scratch = make_scratch(ast.count)

    field_u8 = find_node(data, columns, AST_FIELD_TYPE, b"u8")
    field_u64 = find_node(data, columns, AST_FIELD_TYPE, b"u64")
    field_buffer = find_node(data, columns, AST_FIELD_TYPE, b"buffer<u8>")
    field_words = find_node(data, columns, AST_FIELD_TYPE, b"buffer<u64>")
    field_ten = find_node(data, columns, AST_FIELD_TYPE, b"array<u8, 10>")
    field_eleven = find_node(data, columns, AST_FIELD_TYPE, b"array<u8, 11>")
    field_named = find_node(data, columns, AST_FIELD_TYPE, b"Thing")
    field_other = find_node(data, columns, AST_FIELD_TYPE, b"Other")
    const_buffer = find_node(data, columns, AST_CONST_TYPE, b"buffer<u8>")
    const_ten = find_node(data, columns, AST_CONST_TYPE, b"array<u8, 10>")
    param_buffer = find_node(data, columns, AST_PARAMETER_TYPE, b"buffer<u8>")
    param_ten = find_node(data, columns, AST_PARAMETER_TYPE, b"array<u8, 10>")
    param_named = find_node(data, columns, AST_PARAMETER_TYPE, b"Thing")
    return_buffer = find_node(data, columns, AST_RETURN_TYPE, b"buffer<u8>")
    binding_buffer = find_node(data, columns, AST_BINDING_TYPE, b"buffer<u8>")
    binding_eleven = find_node(data, columns, AST_BINDING_TYPE, b"array<u8, 11>")
    type_argument_u8 = find_node(data, columns, AST_TYPE_ARGUMENT, b"u8")
    nested_u8 = find_node(data, columns, AST_NESTED_TYPE, b"u8")

    equal = library.semantic_types_equal

    def same(left, right):
        result = equal(
            source,
            ctypes.byref(tokens),
            ctypes.byref(ast),
            left,
            right,
            ctypes.byref(scratch),
        )
        assert_scratch_guards(arrays, physical)
        return result

    # Contextual AstKinds do not affect type identity.
    for left, right in (
        (field_buffer, const_buffer),
        (field_buffer, param_buffer),
        (field_buffer, return_buffer),
        (field_buffer, binding_buffer),
        (field_ten, const_ten),
        (field_ten, param_ten),
        (field_eleven, binding_eleven),
        (field_named, param_named),
        (field_u8, nested_u8),
        (field_u8, type_argument_u8),
        (field_buffer, field_buffer),
    ):
        assert same(left, right), (left, right)

    # Every spelling and every ordered generic child participates in identity.
    for left, right in (
        (field_u8, field_u64),
        (field_buffer, field_words),
        (field_buffer, field_ten),
        (field_ten, field_eleven),
        (field_named, field_other),
    ):
        assert not same(left, right), (left, right)

    # Invalid roots and insufficient caller-owned work space fail closed.
    assert not same(AST_NONE, field_buffer)
    assert not same(field_buffer, ast.count)
    short_arrays, short_physical, short = make_scratch(
        ast.count, (ast.count, ast.count, ast.count - 1, ast.count)
    )
    assert not equal(
        source,
        ctypes.byref(tokens),
        ctypes.byref(ast),
        field_buffer,
        const_buffer,
        ctypes.byref(short),
    )
    assert_scratch_guards(short_arrays, short_physical)

    kinds, heads, _, _, first, last, next_ = columns
    del kinds
    field_child = first[field_buffer]
    assert field_child != AST_NONE and field_child == last[field_buffer]

    # Each malformed reference/chain is rejected before an unsafe walk.
    with changed(heads, field_buffer, tokens.count):
        assert not same(field_buffer, const_buffer)
    with changed(first, field_buffer, AST_NONE):
        assert not same(field_buffer, const_buffer)
    with changed(first, field_buffer, ast.count):
        assert not same(field_buffer, const_buffer)
    with changed(last, field_buffer, field_ten):
        assert not same(field_buffer, const_buffer)
    with changed(next_, field_child, field_child):
        assert not same(field_buffer, const_buffer)
    with changed(first, field_buffer, field_buffer):
        with changed(last, field_buffer, field_buffer):
            assert not same(field_buffer, const_buffer)

    old_heads_length = ast.heads.length
    ast.heads.length = ast.count - 1
    try:
        assert not same(field_buffer, const_buffer)
    finally:
        ast.heads.length = old_heads_length

    # Repeated calls after hostile inputs are deterministic and clean their marks.
    assert same(field_buffer, const_buffer)
    assert scratch.generation > 1
    scratch.generation = AST_NONE
    for array in arrays[2:]:
        for index in range(ast.count):
            array[index] = AST_NONE
    assert same(field_buffer, const_buffer)
    assert scratch.generation == 1
    assert source_storage and arrays


def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))
        library.semantic_types_equal.argtypes = [
            Buffer,
            ctypes.POINTER(TokenTape),
            ctypes.POINTER(AstTape),
            ctypes.c_uint64,
            ctypes.c_uint64,
            ctypes.POINTER(TypeShapeScratch),
        ]
        library.semantic_types_equal.restype = ctypes.c_bool
        assert_valid_shapes(library)
        print(
            "self-hosted semantic types: exact cross-context shapes and "
            "fail-closed malformed links pass"
        )


if __name__ == "__main__":
    main()
