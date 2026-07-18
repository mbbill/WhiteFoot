#!/usr/bin/env python3
"""Require wfc's permanent lexer/parser to reproduce its complete source unit."""

import ctypes
import tempfile
from pathlib import Path

from test_ast_validate import (
    AST_VALIDATION_CLEAN,
    AstValidationReport,
    validate,
)
from test_lexer import Buffer, TokenTape, build_library, compiler_source
from test_parser import AstTape, parse


PARSE_CLEAN = 0
HERE = Path(__file__).resolve().parent


def source_location(offset):
    cursor = 0
    entries = [
        entry.strip()
        for entry in (HERE / "sources.txt").read_text().splitlines()
        if entry.strip()
    ]
    for index, entry in enumerate(entries):
        data = (HERE / entry).read_text().rstrip("\n").encode("ascii")
        if offset <= cursor + len(data):
            local = max(0, offset - cursor)
            line = data.count(b"\n", 0, local) + 1
            previous_newline = data.rfind(b"\n", 0, local)
            column = local - previous_newline
            return entry, line, column
        cursor += len(data) + (2 if index + 1 < len(entries) else 1)
    return "<end-of-unit>", 1, 1


def parse_error(source, ast):
    start = min(ast.error_start, len(source))
    end = min(ast.error_end, len(source))
    path, line, column = source_location(start)
    context_start = max(0, start - 80)
    context_end = min(len(source), max(end, start + 1) + 120)
    context = source[context_start:context_end].decode("ascii", errors="replace")
    return (
        f"self-parse status {ast.status} at {path}:{line}:{column}, "
        f"bytes [{ast.error_start},{ast.error_end}) "
        f"{source[start:end]!r}\n{context}"
    )


def snapshot(token_storage, tokens, ast_storage, ast):
    token_columns = tuple(
        tuple(column[: tokens.count]) for column in token_storage
    )
    ast_columns = tuple(tuple(column[: ast.count]) for column in ast_storage)
    token_scalars = (
        tokens.count,
        tokens.status,
        tokens.error_start,
        tokens.error_end,
    )
    ast_scalars = (
        ast.count,
        ast.root,
        ast.status,
        ast.error_start,
        ast.error_end,
    )
    return token_columns, token_scalars, ast_columns, ast_scalars


def main():
    source = compiler_source().encode("ascii")
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))
        library.parser_run.argtypes = [
            Buffer,
            ctypes.POINTER(TokenTape),
            ctypes.POINTER(AstTape),
        ]
        library.parser_run.restype = None
        library.ast_validate.argtypes = [
            ctypes.c_uint64,
            ctypes.c_uint64,
            ctypes.POINTER(AstTape),
            ctypes.POINTER(AstValidationReport),
        ]
        library.ast_validate.restype = None

        first = parse(library, source)
        _, first_tokens_storage, first_tokens, first_ast_storage, first_ast = first
        if first_ast.status != PARSE_CLEAN:
            raise AssertionError(parse_error(source, first_ast))
        assert first_tokens.status == 0
        assert first_tokens.count <= len(source) + 1
        assert first_ast.count <= first_tokens.count
        report = validate(
            library,
            len(source),
            first_tokens.count,
            first_ast,
        )
        assert report.status == AST_VALIDATION_CLEAN, (
            report.status,
            report.node,
            report.related,
        )

        second = parse(library, source)
        _, second_tokens_storage, second_tokens, second_ast_storage, second_ast = second
        if second_ast.status != PARSE_CLEAN:
            raise AssertionError(parse_error(source, second_ast))
        assert snapshot(
            first_tokens_storage,
            first_tokens,
            first_ast_storage,
            first_ast,
        ) == snapshot(
            second_tokens_storage,
            second_tokens,
            second_ast_storage,
            second_ast,
        )

        print(
            "self-parse: "
            f"{len(source)} source bytes, {first_tokens.count} tokens, "
            f"{first_ast.count} unique-head AST nodes, deterministic and valid"
        )


if __name__ == "__main__":
    main()
