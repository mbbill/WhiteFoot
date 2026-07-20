#!/usr/bin/env python3
"""Audit the bounded exclusive-root writer capability and its fail-closed fences."""

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

def assert_reader_flat_report_writer(library):
    # F3 bounded slices: exactly one exclusive struct borrow, one matching
    # writes(region) row, a nonempty flat sequence of direct field assignments
    # from own parameters or exact scalar/tag literals, and a final `return unit`.
    # The declared write row is an optimizer fact, so every broader or malformed
    # shape stays fail-closed.
    report_writer = (
        b"enum WriterStatus {\n  WriterIdle();\n  WriterFailed();\n}\n\n"
        b"struct WriterReport {\n  status: WriterStatus;\n  node: u64;\n"
        b"  related: u64;\n}\n\n"
        b"fn writer_set_report ['w] (report: &uniq 'w WriterReport, "
        b"status: own WriterStatus, node: own u64, related: own u64) "
        b"-> own unit writes('w) {\n"
        b"  set deref(report).status = status;\n"
        b"  set deref(report).node = node;\n"
        b"  set deref(report).related = related;\n"
        b"  return unit;\n"
        b"}\n"
    )
    literal_writer = (
        b"enum WriterStatus {\n  WriterIdle();\n  WriterFailed();\n}\n\n"
        b"struct WriterLiteralReport {\n  status: WriterStatus;\n"
        b"  count: u64;\n  byte: u8;\n  ready: Bool;\n}\n\n"
        b"fn writer_reset ['w] (report: &uniq 'w WriterLiteralReport) "
        b"-> own unit writes('w) {\n"
        b"  set deref(report).status = WriterIdle();\n"
        b"  set deref(report).count = 0_u64;\n"
        b"  set deref(report).byte = 7_u8;\n"
        b"  set deref(report).ready = False();\n"
        b"  return unit;\n"
        b"}\n"
    )

    def classify(source):
        case = parsed(library, source)
        function = top_level_functions(case)[-1]
        work = make_work(library, case[5].count)
        kind, report = invoke_dispatch(library, case, function, work)
        return case, function, work, kind, report

    def assert_clean(source):
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

    assert_clean(report_writer)
    assert_clean(literal_writer)

    # `unit` and exclusive borrows do not become general reader capabilities.
    assert_unsupported(
        b"fn writer_noop () -> own unit pure {\n  return unit;\n}\n"
    )
    assert_unsupported(
        b"struct WriterCell {\n  value: u64;\n}\n"
        b"fn writer_read ['w] (cell: &uniq 'w WriterCell) -> own u64 "
        b"reads('w) {\n  return deref(cell).value;\n}\n"
    )

    # EFF-2 is bidirectional for writes: missing, spurious, or wrong-region
    # declarations never admit a body.
    assert_unsupported(report_writer.replace(b"writes('w)", b"pure"))
    assert_unsupported(
        b"struct WriterCell {\n  value: u64;\n}\n"
        b"fn writer_spurious ['w] (cell: &uniq 'w WriterCell, "
        b"value: own u64) -> own unit writes('w) {\n"
        b"  return unit;\n}\n"
    )
    assert_unsupported(
        report_writer.replace(b"['w]", b"['w, 'x]").replace(
            b"writes('w)", b"writes('x)"
        )
    )

    # The target must be one direct field of exactly one exclusive struct
    # parameter. Shared targets and multiple exclusive roots stay deferred.
    assert_unsupported(report_writer.replace(b"&uniq 'w", b"&'w"))
    assert_unsupported(
        b"struct WriterCell {\n  value: u64;\n}\n"
        b"fn writer_two ['w] (left: &uniq 'w WriterCell, "
        b"right: &uniq 'w WriterCell, value: own u64) -> own unit "
        b"writes('w) {\n"
        b"  set deref(left).value = value;\n"
        b"  return unit;\n}\n"
    )

    # Reads through the exclusive root, local mutation, and nested control are
    # separate future tranches.
    assert_unsupported(
        b"struct WriterCell {\n  value: u64;\n  other: u64;\n}\n"
        b"fn writer_reads ['w] (cell: &uniq 'w WriterCell) -> own unit "
        b"writes('w) {\n"
        b"  set deref(cell).value = deref(cell).other;\n"
        b"  return unit;\n}\n"
    )
    assert_unsupported(
        b"struct WriterCell {\n  value: u64;\n}\n"
        b"fn writer_local ['w] (cell: &uniq 'w WriterCell, value: own u64) "
        b"-> own unit writes('w) {\n"
        b"  let local: own u64 = value;\n"
        b"  set local = value;\n"
        b"  set deref(cell).value = local;\n"
        b"  return unit;\n}\n"
    )
    assert_unsupported(
        b"struct WriterCell {\n  value: u64;\n}\n"
        b"fn writer_nested ['w] (cell: &uniq 'w WriterCell, value: own u64, "
        b"flag: own Bool) -> own unit writes('w) {\n"
        b"  match flag {\n"
        b"    True() => { set deref(cell).value = value; }\n"
        b"    False() => { set deref(cell).value = value; }\n"
        b"  }\n"
        b"  return unit;\n}\n"
    )
    assert_unsupported(
        b"struct WriterCell {\n  value: u64;\n}\n"
        b"fn writer_value ['w] (cell: &uniq 'w WriterCell, value: own u64) "
        b"-> own u64 writes('w) {\n"
        b"  set deref(cell).value = value;\n"
        b"  return value;\n}\n"
    )

    # Constructor resolution is confined to the field-writer RHS. It proves a
    # globally unique, direct, nullary tag variant and exact nominal field type;
    # it does not widen constructors in pure returns or local expression typing.
    assert_unsupported(
        b"enum WriterStatus {\n  WriterIdle();\n  WriterFailed();\n}\n"
        b"fn writer_make () -> own WriterStatus pure {\n"
        b"  return WriterIdle();\n}\n"
    )
    assert_unsupported(
        b"enum WriterStatus {\n  WriterIdle();\n  WriterFailed();\n}\n"
        b"enum WriterOther {\n  WriterOtherIdle();\n  WriterOtherFailed();\n}\n"
        b"struct WriterCell {\n  status: WriterStatus;\n}\n"
        b"fn writer_wrong_tag ['w] (cell: &uniq 'w WriterCell) -> own unit "
        b"writes('w) {\n"
        b"  set deref(cell).status = WriterOtherIdle();\n"
        b"  return unit;\n}\n"
    )
    assert_unsupported(
        b"enum WriterStatus {\n  WriterIdle();\n  WriterFailed();\n}\n"
        b"enum WriterOther {\n  WriterIdle();\n  WriterOtherFailed();\n}\n"
        b"struct WriterCell {\n  status: WriterStatus;\n}\n"
        b"fn writer_duplicate_tag ['w] (cell: &uniq 'w WriterCell) "
        b"-> own unit writes('w) {\n"
        b"  set deref(cell).status = WriterIdle();\n"
        b"  return unit;\n}\n"
    )

    # Numeric RHS values retain FORM-5 canonicality and exact width. Global
    # scalar constants remain the next explicit tranche rather than being
    # treated as local places by accident.
    assert_unsupported(literal_writer.replace(b"0_u64", b"00_u64"))
    assert_unsupported(literal_writer.replace(b"7_u8", b"256_u8"))
    assert_unsupported(
        b"const writer_zero: u64 = 0_u64;\n"
        b"struct WriterCell {\n  value: u64;\n}\n"
        b"fn writer_global ['w] (cell: &uniq 'w WriterCell) -> own unit "
        b"writes('w) {\n"
        b"  set deref(cell).value = writer_zero;\n"
        b"  return unit;\n}\n"
    )

    def assert_mutation_unsupported(source, mutate):
        case, function = assert_clean(source)
        mutate(case)
        work = make_work(library, case[5].count)
        kind, report = invoke_dispatch(library, case, function, work)
        assert (kind, report.status, report.function) == (
            CAPABILITY_UNSUPPORTED,
            BODY_UNSUPPORTED,
            function,
        ), (kind, report.status, report.function, report.related)
        assert_output_guards(work)

    def assert_direct_constructor_mutation_rejected(mutate):
        case, function = assert_clean(literal_writer)
        mutate(case)
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

    def field_target_kind(case):
        statement = next(
            node
            for node in range(case[5].count)
            if case[4][0][node] == AST["AstSet"]
        )
        target = children_of(case[4], statement)[0]
        case[4][0][target] = AST["AstPlaceUse"]

    def deref_base_kind(case):
        statement = next(
            node
            for node in range(case[5].count)
            if case[4][0][node] == AST["AstSet"]
        )
        target = children_of(case[4], statement)[0]
        base = children_of(case[4], target)[0]
        case[4][0][base] = AST["AstPlaceUse"]

    def uniq_mode_kind(case):
        mode = next(
            node
            for node in range(case[5].count)
            if case[4][0][node] == AST["AstUniqMode"]
        )
        case[4][0][mode] = AST["AstSharedMode"]

    def writes_effect_kind(case):
        effect = next(
            node
            for node in range(case[5].count)
            if case[4][0][node] == AST["AstWritesEffect"]
        )
        case[4][0][effect] = AST["AstReadsEffect"]

    def constructor_payload_shape(case):
        enum_declaration = next(
            node
            for node in children_of(case[4], case[5].root)
            if case[4][0][node] == AST["AstEnumDecl"]
        )
        enum_children = children_of(case[4], enum_declaration)
        enum_name = next(
            node for node in enum_children if case[4][0][node] == AST["AstEnumName"]
        )
        variant = next(
            node
            for node in enum_children
            if case[4][0][node] == AST["AstVariant"]
            and literal_writer[
                case[4][2][node] : case[4][3][node]
            ].startswith(b"WriterIdle")
        )
        case[4][4][variant] = enum_name
        case[4][5][variant] = enum_name

    def constructor_enum_header(case):
        enum_declaration = next(
            node
            for node in children_of(case[4], case[5].root)
            if case[4][0][node] == AST["AstEnumDecl"]
        )
        function = top_level_functions(case)[-1]
        case[4][1][enum_declaration] = case[4][1][function]

    def constructor_root_terminal(case):
        last = case[4][5][case[5].root]
        first = case[4][4][case[5].root]
        case[4][6][last] = first

    assert_mutation_unsupported(report_writer, field_target_kind)
    assert_mutation_unsupported(report_writer, deref_base_kind)
    assert_mutation_unsupported(report_writer, uniq_mode_kind)
    assert_mutation_unsupported(report_writer, writes_effect_kind)
    assert_direct_constructor_mutation_rejected(constructor_payload_shape)
    assert_direct_constructor_mutation_rejected(constructor_enum_header)
    assert_direct_constructor_mutation_rejected(constructor_root_terminal)

def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))
        configure(library)
        assert_reader_flat_report_writer(library)
    print(
        "semantic writer: exact exclusive-root flat writes from own values, "
        "canonical integers, and nullary tags; effect, nominal, shape, "
        "topology, and deferred-profile fences pass"
    )


if __name__ == "__main__":
    main()
