#!/usr/bin/env python3
"""Exercise the kind-agnostic structural validator against hostile AST tapes."""

import ctypes
import tempfile
from pathlib import Path

from test_lexer import Buffer, build_library
from test_parser import AST_NONE, AstTape, make_ast, parse


AST_VALIDATION_CLEAN = 0
AST_VALIDATION_COLUMN_CAPACITY = 1
AST_VALIDATION_SCRATCH_CAPACITY = 2
AST_VALIDATION_COUNT_EXCEEDS_TOKENS = 3
AST_VALIDATION_EMPTY = 4
AST_VALIDATION_ROOT_REFERENCE = 5
AST_VALIDATION_HEAD_REFERENCE = 6
AST_VALIDATION_DUPLICATE_HEAD = 7
AST_VALIDATION_SPAN = 8
AST_VALIDATION_CHILD_PAIR = 9
AST_VALIDATION_CHILD_REFERENCE = 10
AST_VALIDATION_SIBLING_REFERENCE = 11
AST_VALIDATION_LAST_CHILD = 12
AST_VALIDATION_DUPLICATE_REACH = 13
AST_VALIDATION_UNREACHABLE = 14

SCRATCH_GUARD = 0xA7A7A7A7A7A7A7A7


class AstValidationReport(ctypes.Structure):
    _fields_ = [
        ("marks", Buffer),
        ("stack", Buffer),
        ("status", ctypes.c_int32),
        ("node", ctypes.c_uint64),
        ("related", ctypes.c_uint64),
    ]


def validate(
    library,
    source_length,
    token_count,
    ast,
    marks_capacity=None,
    stack_capacity=None,
):
    if marks_capacity is None:
        marks_capacity = token_count
    if stack_capacity is None:
        stack_capacity = ast.count
    marks = (ctypes.c_uint64 * (marks_capacity + 1))()
    stack = (ctypes.c_uint64 * (stack_capacity + 1))()
    marks[marks_capacity] = SCRATCH_GUARD
    stack[stack_capacity] = SCRATCH_GUARD
    report = AstValidationReport(
        Buffer(ctypes.cast(marks, ctypes.c_void_p), marks_capacity),
        Buffer(ctypes.cast(stack, ctypes.c_void_p), stack_capacity),
        99,
        99,
        99,
    )
    library.ast_validate(
        source_length,
        token_count,
        ctypes.byref(ast),
        ctypes.byref(report),
    )
    assert marks[marks_capacity] == SCRATCH_GUARD
    assert stack[stack_capacity] == SCRATCH_GUARD
    return report


def assert_clean_parser_output(library):
    cases = [
        b"fn main () -> own unit pure { return unit; }\n",
        (Path(__file__).resolve().parent / "examples" / "scalar_add.xl").read_bytes(),
    ]
    for data in cases:
        _, _, tokens, columns, ast = parse(library, data)
        report = validate(library, len(data), tokens.count, ast)
        assert report.status == AST_VALIDATION_CLEAN
        assert (report.node, report.related) == (AST_NONE, AST_NONE)

        columns[0][0] = 0x7FFFFFFF
        report = validate(library, len(data), tokens.count, ast)
        assert report.status == AST_VALIDATION_CLEAN


def basic_tree(library):
    data = b"fn main () -> own unit pure { return unit; }\n"
    _, _, tokens, columns, ast = parse(library, data)
    return data, tokens, columns, ast


def assert_capacity_failures(library):
    column_fields = (
        "kinds",
        "heads",
        "starts",
        "ends",
        "first_children",
        "last_children",
        "next_siblings",
    )
    for field in column_fields:
        data, tokens, _, ast = basic_tree(library)
        getattr(ast, field).length = ast.count - 1
        report = validate(library, len(data), tokens.count, ast)
        assert report.status == AST_VALIDATION_COLUMN_CAPACITY, field

    data, tokens, _, ast = basic_tree(library)
    report = validate(
        library,
        len(data),
        tokens.count,
        ast,
        marks_capacity=tokens.count - 1,
    )
    assert report.status == AST_VALIDATION_SCRATCH_CAPACITY

    data, tokens, _, ast = basic_tree(library)
    report = validate(
        library,
        len(data),
        tokens.count,
        ast,
        stack_capacity=ast.count - 1,
    )
    assert report.status == AST_VALIDATION_SCRATCH_CAPACITY


def assert_scalar_failures(library):
    data, tokens, _, ast = basic_tree(library)
    report = validate(library, len(data), ast.count - 1, ast)
    assert report.status == AST_VALIDATION_COUNT_EXCEEDS_TOKENS

    _, _, empty = make_ast(1)
    empty.count = 0
    empty.root = AST_NONE
    report = validate(library, 0, 0, empty)
    assert report.status == AST_VALIDATION_EMPTY

    data, tokens, _, ast = basic_tree(library)
    ast.root = ast.count
    report = validate(library, len(data), tokens.count, ast)
    assert report.status == AST_VALIDATION_ROOT_REFERENCE

    data, tokens, columns, ast = basic_tree(library)
    columns[6][ast.root] = 1
    report = validate(library, len(data), tokens.count, ast)
    assert report.status == AST_VALIDATION_ROOT_REFERENCE

    data, tokens, columns, ast = basic_tree(library)
    columns[1][2] = tokens.count
    report = validate(library, len(data), tokens.count, ast)
    assert (report.status, report.node) == (AST_VALIDATION_HEAD_REFERENCE, 2)

    data, tokens, columns, ast = basic_tree(library)
    columns[1][2] = columns[1][1]
    report = validate(library, len(data), tokens.count, ast)
    assert (report.status, report.node) == (AST_VALIDATION_DUPLICATE_HEAD, 2)

    data, tokens, columns, ast = basic_tree(library)
    columns[2][3] = columns[3][3] + 1
    report = validate(library, len(data), tokens.count, ast)
    assert (report.status, report.node) == (AST_VALIDATION_SPAN, 3)

    data, tokens, columns, ast = basic_tree(library)
    columns[4][2] = AST_NONE
    columns[5][2] = 3
    report = validate(library, len(data), tokens.count, ast)
    assert (report.status, report.node) == (AST_VALIDATION_CHILD_PAIR, 2)

    data, tokens, columns, ast = basic_tree(library)
    columns[4][2] = ast.count
    columns[5][2] = 3
    report = validate(library, len(data), tokens.count, ast)
    assert (report.status, report.node) == (AST_VALIDATION_CHILD_REFERENCE, 2)

    data, tokens, columns, ast = basic_tree(library)
    columns[6][2] = ast.count
    report = validate(library, len(data), tokens.count, ast)
    assert (report.status, report.node) == (AST_VALIDATION_SIBLING_REFERENCE, 2)


def assert_topology_failures(library):
    data, tokens, columns, ast = basic_tree(library)
    columns[5][1] = 5
    report = validate(library, len(data), tokens.count, ast)
    assert (report.status, report.node) == (AST_VALIDATION_LAST_CHILD, 1)

    data, tokens, columns, ast = basic_tree(library)
    columns[4][2] = 8
    columns[5][2] = 8
    report = validate(library, len(data), tokens.count, ast)
    assert report.status == AST_VALIDATION_DUPLICATE_REACH
    assert report.node == 8

    data, tokens, columns, ast = basic_tree(library)
    columns[6][6] = 2
    report = validate(library, len(data), tokens.count, ast)
    assert report.status == AST_VALIDATION_DUPLICATE_REACH

    data, tokens, columns, ast = basic_tree(library)
    columns[4][6] = AST_NONE
    columns[5][6] = AST_NONE
    report = validate(library, len(data), tokens.count, ast)
    assert (report.status, report.node) == (AST_VALIDATION_UNREACHABLE, 7)


def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))
        library.ast_validate.argtypes = [
            ctypes.c_uint64,
            ctypes.c_uint64,
            ctypes.POINTER(AstTape),
            ctypes.POINTER(AstValidationReport),
        ]
        library.ast_validate.restype = None
        assert_clean_parser_output(library)
        assert_capacity_failures(library)
        assert_scalar_failures(library)
        assert_topology_failures(library)
        print(
            "AST validator: kind-agnostic columns, heads, spans, topology, "
            "reachability, and scratch guards pass"
        )


if __name__ == "__main__":
    main()
