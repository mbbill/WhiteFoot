#!/usr/bin/env python3
"""Audit the exact loop-based indexed-writer capability and its fences."""

import ctypes
import tempfile
from pathlib import Path

from test_lexer import build_library
from test_parser import AST_NONE, children_of
from test_semantic_body import (
    AST,
    BODY_CLEAN,
    BODY_UNSUPPORTED,
    SemanticBodyReport,
    assert_output_guards,
    parsed,
)
from test_semantic_unit import (
    CAPABILITY_ACYCLIC,
    CAPABILITY_UNSUPPORTED,
    FIX_NONE,
    RULE_NONE,
    assert_no_capability_diagnostic,
    configure,
    invoke_dispatch,
    make_work,
    top_level_functions,
)


CONTROL_WRITER = (
    b"struct WriterControlRows {\n"
    b"  values: buffer<u64>;\n"
    b"  count: u64;\n"
    b"}\n"
    b"fn writer_control ['w] (rows: &uniq 'w WriterControlRows, "
    b"count: own u64) -> own unit writes('w), traps {\n"
    b"  let cursor: own u64 = 0_u64;\n"
    b"  loop @writer_control_rows {\n"
    b"    match ige<u64>(cursor, count) {\n"
    b"      True() => {\n"
    b"        break @writer_control_rows;\n"
    b"      }\n"
    b"      False() => {\n"
    b"      }\n"
    b"    }\n"
    b"    set index<u64>(deref(rows).values, cursor) = count;\n"
    b"    set cursor = iadd.trap<u64>(cursor, 1_u64);\n"
    b"  }\n"
    b"  set deref(rows).count = count;\n"
    b"  return unit;\n"
    b"}\n"
)


def assert_control_writer_boundary(library):
    def classify(source):
        case = parsed(library, source)
        function = top_level_functions(case)[-1]
        work = make_work(library, case[5].count)
        kind, report = invoke_dispatch(library, case, function, work)
        return case, function, work, kind, report

    def assert_clean(source=CONTROL_WRITER):
        case, function, work, kind, report = classify(source)
        assert (kind, report.status, report.function, report.related) == (
            CAPABILITY_ACYCLIC,
            BODY_CLEAN,
            function,
            AST_NONE,
        ), (kind, report.status, report.function, report.related)
        assert_no_capability_diagnostic(report)
        assert_output_guards(work)
        return case, function

    def assert_unsupported(source):
        _, function, work, kind, report = classify(source)
        assert (kind, report.status, report.function) == (
            CAPABILITY_UNSUPPORTED,
            BODY_UNSUPPORTED,
            function,
        ), (kind, report.status, report.function, report.related)
        assert_no_capability_diagnostic(report)
        assert_output_guards(work)

    assert_clean()

    # The profile is writes-only, trapping, and rooted in the declared region.
    assert_unsupported(CONTROL_WRITER.replace(b", traps {", b" {"))
    assert_unsupported(
        CONTROL_WRITER.replace(
            b"writes('w), traps", b"reads('w), writes('w), traps"
        )
    )
    assert_unsupported(
        CONTROL_WRITER.replace(b"['w]", b"['w, 'x]").replace(
            b"writes('w)", b"writes('x)"
        )
    )
    assert_unsupported(CONTROL_WRITER.replace(b"&uniq 'w", b"&'w"))

    # The cursor declaration, guard, indexed body, increment, and tail are an
    # exact control protocol; nearby legal programs remain outside the slice.
    assert_unsupported(
        CONTROL_WRITER.replace(
            b"let cursor: own u64 = 0_u64;",
            b"let cursor: own u64 = 1_u64;",
        )
    )
    assert_unsupported(
        CONTROL_WRITER.replace(
            b"match ige<u64>(cursor, count)",
            b"match ilt<u64>(cursor, count)",
        )
    )
    assert_unsupported(
        CONTROL_WRITER.replace(
            b"match ige<u64>(cursor, count)",
            b"match ige<u64>(cursor, cursor)",
        )
    )
    assert_unsupported(
        CONTROL_WRITER.replace(
            b"      True() => {\n"
            b"        break @writer_control_rows;\n"
            b"      }\n"
            b"      False() => {\n"
            b"      }",
            b"      True() => {\n"
            b"      }\n"
            b"      False() => {\n"
            b"        break @writer_control_rows;\n"
            b"      }",
        )
    )
    assert_unsupported(
        CONTROL_WRITER.replace(
            b"      True() => {\n"
            b"        break @writer_control_rows;\n"
            b"      }\n"
            b"      False() => {\n"
            b"      }",
            b"      False() => {\n"
            b"        break @writer_control_rows;\n"
            b"      }\n"
            b"      True() => {\n"
            b"      }",
        )
    )
    assert_unsupported(
        CONTROL_WRITER.replace(
            b"        break @writer_control_rows;",
            b"        set cursor = cursor;\n"
            b"        break @writer_control_rows;",
        )
    )
    assert_unsupported(
        CONTROL_WRITER.replace(
            b"    set index<u64>(deref(rows).values, cursor) = count;\n",
            b"",
        )
    )
    assert_unsupported(
        CONTROL_WRITER.replace(
            b"deref(rows).values, cursor", b"deref(rows).values, count"
        )
    )
    assert_unsupported(
        CONTROL_WRITER.replace(
            b"= count;\n    set cursor",
            b"= iadd.trap<u64>(count, 1_u64);\n    set cursor",
        )
    )
    assert_unsupported(
        CONTROL_WRITER.replace(b"iadd.trap<u64>(cursor", b"iadd.wrap<u64>(cursor")
    )
    assert_unsupported(
        CONTROL_WRITER.replace(
            b"iadd.trap<u64>(cursor, 1_u64)",
            b"iadd.trap<u64>(cursor, 2_u64)",
        )
    )
    assert_unsupported(
        CONTROL_WRITER.replace(
            b"  set deref(rows).count = count;\n", b""
        )
    )
    assert_unsupported(
        CONTROL_WRITER.replace(
            b"  set deref(rows).count = count;",
            b"  set index<u64>(deref(rows).values, cursor) = count;",
        )
    )
    assert_unsupported(
        CONTROL_WRITER.replace(b"  return unit;", b"  return True();")
    )

    def assert_direct_reader_mutation_rejected(mutate):
        case, function = assert_clean()
        mutate(case, function)
        work = make_work(library, case[5].count)
        report = SemanticBodyReport(99, 123, 456, 99, 99, 789)
        library.semantic_reader_run(
            case[1],
            ctypes.byref(case[3]),
            ctypes.byref(case[5]),
            ctypes.byref(case[9]),
            function,
            ctypes.byref(work[6]),
            ctypes.byref(report),
        )
        assert (report.status, report.rule, report.fix) == (
            BODY_UNSUPPORTED,
            RULE_NONE,
            FIX_NONE,
        )
        assert_output_guards(work)

    def control_nodes(case, function):
        columns = case[4]
        outer = next(
            node
            for node in children_of(columns, function)
            if columns[0][node] == AST["AstBlock"]
        )
        outer_statements = children_of(columns, outer)
        declaration = outer_statements[0]
        loop = outer_statements[1]
        loop_label, loop_block = children_of(columns, loop)
        loop_statements = children_of(columns, loop_block)
        match = loop_statements[0]
        guard, break_arm, _ = children_of(columns, match)
        break_block = children_of(columns, break_arm)[0]
        break_statement = children_of(columns, break_block)[0]
        break_label = children_of(columns, break_statement)[0]
        index_set = loop_statements[1]
        index_target = children_of(columns, index_set)[0]
        subscript = children_of(columns, index_target)[2]
        increment_set = loop_statements[-1]
        guard_left = children_of(columns, guard)[1]
        guard_type = children_of(columns, guard)[0]
        increment = children_of(columns, increment_set)[1]
        increment_type = children_of(columns, increment)[0]
        index_type = children_of(columns, index_target)[0]
        return {
            "declaration": declaration,
            "loop_label": loop_label,
            "break_label": break_label,
            "subscript": subscript,
            "guard_left": guard_left,
            "guard_type": guard_type,
            "increment_type": increment_type,
            "index_type": index_type,
            "increment_set": increment_set,
            "index_set": index_set,
        }

    def cursor_name_same_word_head(case, function):
        nodes = control_nodes(case, function)
        declaration_name = children_of(case[4], nodes["declaration"])[0]
        case[4][1][declaration_name] = case[4][1][nodes["subscript"]]

    def loop_label_same_word_head(case, function):
        nodes = control_nodes(case, function)
        case[4][1][nodes["loop_label"]] = case[4][1][nodes["break_label"]]

    def break_label_same_word_head(case, function):
        nodes = control_nodes(case, function)
        case[4][1][nodes["break_label"]] = case[4][1][nodes["loop_label"]]

    def subscript_same_word_head(case, function):
        nodes = control_nodes(case, function)
        case[4][1][nodes["subscript"]] = case[4][1][nodes["guard_left"]]

    def cursor_initializer_kind(case, function):
        nodes = control_nodes(case, function)
        initializer = children_of(case[4], nodes["declaration"])[3]
        case[4][0][initializer] = AST["AstPlaceUse"]

    def cursor_type_same_word_head(case, function):
        nodes = control_nodes(case, function)
        cursor_type = children_of(case[4], nodes["declaration"])[2]
        case[4][1][cursor_type] = case[4][1][nodes["guard_type"]]

    def guard_type_same_word_head(case, function):
        nodes = control_nodes(case, function)
        case[4][1][nodes["guard_type"]] = case[4][1][nodes["index_type"]]

    def increment_type_same_word_head(case, function):
        nodes = control_nodes(case, function)
        case[4][1][nodes["increment_type"]] = case[4][1][nodes["index_type"]]

    def loop_terminal_cycle(case, function):
        nodes = control_nodes(case, function)
        case[4][6][nodes["increment_set"]] = nodes["index_set"]

    for mutate in (
        cursor_name_same_word_head,
        loop_label_same_word_head,
        break_label_same_word_head,
        subscript_same_word_head,
        cursor_initializer_kind,
        cursor_type_same_word_head,
        guard_type_same_word_head,
        increment_type_same_word_head,
        loop_terminal_cycle,
    ):
        assert_direct_reader_mutation_rejected(mutate)


def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))
        configure(library)
        assert_control_writer_boundary(library)
    print(
        "semantic control writer: exact zero cursor, u64 threshold guard, "
        "labeled break, cursor-indexed writes, trapping increment, direct "
        "field tail, and hostile effect, provenance, binding, source "
        "anchoring, shape, topology, and deferred-profile fences pass"
    )


if __name__ == "__main__":
    main()
