#!/usr/bin/env python3
"""Exercise xlc's first non-function top-level item slice."""

import ctypes
import tempfile
from pathlib import Path

from test_lexer import Buffer, TokenTape, build_library
from test_parser import (
    AST_NONE,
    AST_NUMERIC_LITERAL,
    AST_PROGRAM,
    AstTape,
    assert_head_invariant,
    children_of,
    parse,
    span,
)


AST_FUNCTION = 1
AST_NESTED_TYPE = 23
AST_CONST_ARGUMENT = 24
AST_ENUM_DECL = 29
AST_ENUM_NAME = 30
AST_VARIANT = 31
AST_STRUCT_DECL = 32
AST_STRUCT_NAME = 33
AST_FIELD = 34
AST_FIELD_TYPE = 35
AST_CONST_DECL = 36
AST_CONST_NAME = 37
AST_CONST_TYPE = 38
AST_CONST_ARRAY_VALUE = 39

PARSE_CLEAN = 0
PARSE_EXPECTED_NAME = 3
PARSE_EXPECTED_RIGHT_PAREN = 5
PARSE_EXPECTED_SEMICOLON = 13
PARSE_TRAILING_TOKEN = 15
PARSE_EXPECTED_COLON = 19
PARSE_EXPECTED_EQUALS = 22
PARSE_EXPECTED_TYPE = 27
PARSE_EXPECTED_TOP_LEVEL_ITEM = 33
PARSE_EXPECTED_TYPE_NAME = 34
PARSE_EXPECTED_CONST_VALUE = 35
PARSE_EXPECTED_COMMA_OR_RIGHT_SQUARE = 36


def item_fixture():
    return (
        b"enum TokenKind {\n"
        b"  TokEnd();\n"
        b"  TokWord();\n"
        b"}\n"
        b"struct TokenTape {\n"
        b"  kinds: buffer<TokenKind>;\n"
        b"  count: u64;\n"
        b"}\n"
        b"const maximum: u64 = 18446744073709551615_u64;\n"
        b"const digits: array<u8, 3> = [48_u8, 49_u8, 50_u8];\n"
        b"fn main () -> own unit pure { return unit; }\n"
    )


def token_text(data, token_storage, token):
    _, starts, ends = token_storage
    return data[starts[token]:ends[token]]


def assert_item_tree(library):
    data = item_fixture()
    _, token_storage, tokens, columns, ast = parse(library, data)
    kinds, heads, starts, ends, _, _, _ = columns
    assert ast.status == PARSE_CLEAN
    assert ast.root == 0
    assert ast.count == 33
    assert kinds[0] == AST_PROGRAM
    assert_head_invariant(tokens, columns, ast)

    top = children_of(columns, ast.root)
    assert top == [1, 5, 12, 16, 25]
    assert [kinds[node] for node in top] == [
        AST_ENUM_DECL,
        AST_STRUCT_DECL,
        AST_CONST_DECL,
        AST_CONST_DECL,
        AST_FUNCTION,
    ]

    assert children_of(columns, 1) == [2, 3, 4]
    assert [kinds[node] for node in children_of(columns, 1)] == [
        AST_ENUM_NAME,
        AST_VARIANT,
        AST_VARIANT,
    ]
    assert children_of(columns, 5) == [6, 7, 10]
    assert kinds[6] == AST_STRUCT_NAME
    assert kinds[7] == AST_FIELD
    assert children_of(columns, 7) == [8]
    assert kinds[8] == AST_FIELD_TYPE
    assert children_of(columns, 8) == [9]
    assert kinds[9] == AST_NESTED_TYPE
    assert children_of(columns, 10) == [11]
    assert kinds[11] == AST_FIELD_TYPE

    assert children_of(columns, 12) == [13, 14, 15]
    assert (kinds[13], kinds[14], kinds[15]) == (
        AST_CONST_NAME,
        AST_CONST_TYPE,
        AST_NUMERIC_LITERAL,
    )
    assert children_of(columns, 16) == [17, 18, 21]
    assert (kinds[17], kinds[18], kinds[21]) == (
        AST_CONST_NAME,
        AST_CONST_TYPE,
        AST_CONST_ARRAY_VALUE,
    )
    assert children_of(columns, 18) == [19, 20]
    assert (kinds[19], kinds[20]) == (AST_NESTED_TYPE, AST_CONST_ARGUMENT)
    assert children_of(columns, 21) == [22, 23, 24]
    assert [kinds[node] for node in children_of(columns, 21)] == [AST_NUMERIC_LITERAL] * 3

    expected_spans = {
        1: b"enum TokenKind {\n  TokEnd();\n  TokWord();\n}",
        3: b"TokEnd();",
        5: b"struct TokenTape {\n  kinds: buffer<TokenKind>;\n  count: u64;\n}",
        7: b"kinds: buffer<TokenKind>;",
        8: b"buffer<TokenKind>",
        12: b"const maximum: u64 = 18446744073709551615_u64;",
        16: b"const digits: array<u8, 3> = [48_u8, 49_u8, 50_u8];",
        18: b"array<u8, 3>",
        21: b"[48_u8, 49_u8, 50_u8]",
    }
    for node, expected in expected_spans.items():
        assert data[starts[node]:ends[node]] == expected

    expected_heads = {
        1: b"enum",
        2: b"TokenKind",
        3: b"TokEnd",
        5: b"struct",
        7: b"kinds",
        8: b"buffer",
        9: b"TokenKind",
        12: b"const",
        14: b"u64",
        15: b"18446744073709551615_u64",
        18: b"array",
        20: b"3",
        21: b"[",
        24: b"50_u8",
    }
    for node, expected in expected_heads.items():
        assert token_text(data, token_storage, heads[node]) == expected


def assert_item_failures(library):
    cases = []
    data = b"enum sign { A(); }"
    cases.append((data, PARSE_EXPECTED_TYPE_NAME, span(data, b"sign")))
    data = b"enum E { A(,); }"
    cases.append((data, PARSE_EXPECTED_RIGHT_PAREN, span(data, b",")))
    data = b"enum E { A() B(); }"
    cases.append((data, PARSE_EXPECTED_SEMICOLON, span(data, b"B")))
    data = b"struct S { field u64; }"
    cases.append((data, PARSE_EXPECTED_COLON, span(data, b"u64")))
    data = b"struct S { field: thing; }"
    cases.append((data, PARSE_EXPECTED_TYPE, span(data, b"thing")))
    data = b"struct S { field: u64, }"
    cases.append((data, PARSE_EXPECTED_SEMICOLON, span(data, b",")))
    data = b"const value: u64 1_u64;"
    cases.append((data, PARSE_EXPECTED_EQUALS, span(data, b"1_u64")))
    data = b"const value: u64 = nope;"
    cases.append((data, PARSE_EXPECTED_CONST_VALUE, span(data, b"nope")))
    data = b"const values: array<u8, 2> = [1_u8, 2_u8,];"
    cases.append((data, PARSE_EXPECTED_CONST_VALUE, span(data, b"]")))
    data = b"const values: array<u8, 2> = [1_u8 2_u8];"
    cases.append((data, PARSE_EXPECTED_COMMA_OR_RIGHT_SQUARE, span(data, b"2_u8")))
    data = b"wat"
    cases.append((data, PARSE_EXPECTED_TOP_LEVEL_ITEM, span(data, b"wat")))

    for data, expected_status, expected_span in cases:
        _, _, tokens, columns, ast = parse(library, data)
        assert ast.status == expected_status, (data, ast.status, expected_status)
        assert (ast.error_start, ast.error_end) == expected_span, data
        assert_head_invariant(tokens, columns, ast)

    trailing = b"enum E { A(); } junk"
    _, _, _, _, ast = parse(library, trailing)
    assert ast.status == PARSE_TRAILING_TOKEN
    assert (ast.error_start, ast.error_end) == span(trailing, b"junk")


def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))
        library.parser_run.argtypes = [Buffer, ctypes.POINTER(TokenTape), ctypes.POINTER(AstTape)]
        library.parser_run.restype = None
        assert_item_tree(library)
        assert_item_failures(library)
        print("self-hosted parser items: enum, struct, const, mixed-item trees and diagnostics pass")


if __name__ == "__main__":
    main()
