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
    # F3 bounded slices: one or more same-region exclusive struct borrows, one matching
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
    global_writer = (
        b"const writer_zero: u64 = 18446744073709551615_u64;\n"
        b"struct WriterCell {\n  value: u64;\n}\n"
        b"fn writer_global ['w] (cell: &uniq 'w WriterCell) -> own unit "
        b"writes('w) {\n"
        b"  set deref(cell).value = writer_zero;\n"
        b"  return unit;\n}\n"
    )
    mixed_writer = (
        b"struct WriterInput {\n  values: buffer<u64>;\n}\n"
        b"struct WriterMixedReport {\n  status: u64;\n  start: u64;\n"
        b"  end: u64;\n}\n"
        b"fn writer_load ['s] (input: &'s WriterInput, token: own u64) "
        b"-> own u64 reads('s), traps {\n"
        b"  return index<u64>(deref(input).values, token);\n}\n"
        b"fn writer_mixed ['s, 'w] (input: &'s WriterInput, "
        b"report: &uniq 'w WriterMixedReport, status: own u64, "
        b"token: own u64) -> own unit reads('s), writes('w), traps {\n"
        b"  set deref(report).status = status;\n"
        b"  set deref(report).start = writer_load<'s>(input: input, "
        b"token: token);\n"
        b"  set deref(report).end = writer_load<'s>(input: input, "
        b"token: token);\n"
        b"  return unit;\n}\n"
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
    assert_clean(global_writer)
    assert_clean(mixed_writer)

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

    # Every target must be one direct field of an exclusive struct parameter.
    # Multiple roots are admitted only when every root belongs to the one write
    # region; shared and cross-region roots stay deferred.
    assert_unsupported(report_writer.replace(b"&uniq 'w", b"&'w"))
    assert_clean(
        b"struct WriterCell {\n  value: u64;\n}\n"
        b"fn writer_two ['w] (left: &uniq 'w WriterCell, "
        b"right: &uniq 'w WriterCell, value: own u64) -> own unit "
        b"writes('w) {\n"
        b"  set deref(left).value = value;\n"
        b"  set deref(right).value = value;\n"
        b"  return unit;\n}\n"
    )
    assert_unsupported(
        b"struct WriterCell {\n  value: u64;\n}\n"
        b"fn writer_cross ['w, 'x] (left: &uniq 'w WriterCell, "
        b"right: &uniq 'x WriterCell, value: own u64) -> own unit "
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

    # The mixed profile is exact: two distinct regions, one shared read root,
    # one exclusive write root, exact rows, traps, and explicit call-region
    # attribution. Existing writes-only writers do not inherit call RHS values.
    assert_unsupported(mixed_writer.replace(b"writer_load<'s>", b"writer_load"))
    assert_unsupported(mixed_writer.replace(b"writer_load<'s>", b"writer_load<'w>"))
    assert_unsupported(mixed_writer.replace(b"reads('s), writes", b"writes"))
    assert_unsupported(mixed_writer.replace(b"reads('s), writes", b"reads('w), writes"))
    assert_unsupported(mixed_writer.replace(b", traps {", b" {"))
    assert_unsupported(mixed_writer.replace(b"writes('w)", b"writes('s)"))
    assert_unsupported(mixed_writer.replace(b"['s, 'w]", b"['s, 'w, 'x]"))
    assert_unsupported(
        mixed_writer.replace(
            b"report: &uniq 'w WriterMixedReport,",
            b"other: &'s WriterInput, report: &uniq 'w WriterMixedReport,",
        )
    )
    assert_unsupported(
        mixed_writer.replace(
            b"report: &uniq 'w WriterMixedReport,",
            b"report: &uniq 'w WriterMixedReport, "
            b"other: &uniq 'w WriterMixedReport,",
        )
    )
    assert_unsupported(
        mixed_writer.replace(
            b"-> own u64 reads('s), traps",
            b"-> own Bool reads('s), traps",
        )
    )
    assert_unsupported(
        b"fn writer_identity (value: own u64) -> own u64 pure {\n"
        b"  return value;\n}\n"
        b"struct WriterCell {\n  value: u64;\n}\n"
        b"fn writer_call ['w] (cell: &uniq 'w WriterCell, value: own u64) "
        b"-> own unit writes('w) {\n"
        b"  set deref(cell).value = writer_identity(value: value);\n"
        b"  return unit;\n}\n"
    )
    assert_unsupported(
        b"fn writer_hidden ['x] (value: own u64) -> own u64 writes('x) {\n"
        b"  return value;\n}\n"
        b"struct WriterInput {\n  values: buffer<u64>;\n}\n"
        b"struct WriterCell {\n  value: u64;\n}\n"
        b"fn writer_mixed ['s, 'w] (input: &'s WriterInput, "
        b"cell: &uniq 'w WriterCell, value: own u64) -> own unit "
        b"reads('s), writes('w), traps {\n"
        b"  set deref(cell).value = writer_hidden<'s>(value: value);\n"
        b"  return unit;\n}\n"
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

    # Numeric RHS values retain FORM-5 canonicality and exact width. The only
    # admitted global form is a prior, exact u64 constant whose initializer is
    # itself a canonical u64 literal.
    assert_unsupported(literal_writer.replace(b"0_u64", b"00_u64"))
    assert_unsupported(literal_writer.replace(b"7_u8", b"256_u8"))
    assert_unsupported(
        global_writer.replace(
            b"const writer_zero: u64 = 18446744073709551615_u64;",
            b"const writer_zero: u8 = 0_u8;",
        )
    )
    assert_unsupported(
        global_writer.replace(
            b"18446744073709551615_u64",
            b"018446744073709551615_u64",
        )
    )
    assert_unsupported(
        global_writer.replace(
            b"18446744073709551615_u64",
            b"18446744073709551616_u64",
        )
    )
    assert_unsupported(
        b"struct WriterCell {\n  value: u64;\n}\n"
        b"fn writer_global ['w] (cell: &uniq 'w WriterCell) -> own unit "
        b"writes('w) {\n"
        b"  set deref(cell).value = writer_zero;\n"
        b"  return unit;\n}\n"
        b"const writer_zero: u64 = 0_u64;\n"
    )
    assert_unsupported(
        b"fn writer_zero () -> own u64 pure {\n  return 0_u64;\n}\n"
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

    def assert_direct_reader_mutation_rejected(source, mutate):
        case, function = assert_clean(source)
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

    def assert_direct_constructor_mutation_rejected(mutate):
        assert_direct_reader_mutation_rejected(literal_writer, mutate)

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

    def mixed_shared_mode_kind(case):
        mode = next(
            node
            for node in range(case[5].count)
            if case[4][0][node] == AST["AstSharedMode"]
        )
        case[4][0][mode] = AST["AstOwnMode"]

    def mixed_reads_region_kind(case):
        effect = next(
            node
            for node in range(case[5].count)
            if case[4][0][node] == AST["AstReadsEffect"]
            and node > top_level_functions(case)[-1]
        )
        region = children_of(case[4], effect)[0]
        case[4][0][region] = AST["AstPlaceUse"]

    def mixed_call_terminal(case):
        call = next(
            node
            for node in range(case[5].count)
            if case[4][0][node] == AST["AstUserCall"]
        )
        children = children_of(case[4], call)
        case[4][6][children[-1]] = children[0]

    def mixed_duplicate_traps_node(case):
        helper, writer = top_level_functions(case)[-2:]
        helper_block = next(
            node
            for node in children_of(case[4], helper)
            if case[4][0][node] == AST["AstBlock"]
        )
        duplicate = children_of(case[4], helper_block)[0]
        writer_children = children_of(case[4], writer)
        traps = next(
            node
            for node in writer_children
            if case[4][0][node] == AST["AstTrapsEffect"]
        )
        block = next(
            node
            for node in writer_children
            if case[4][0][node] == AST["AstBlock"]
        )
        case[4][0][duplicate] = AST["AstTrapsEffect"]
        case[4][6][traps] = duplicate
        case[4][6][duplicate] = block

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

    def global_const_header(case):
        declaration = next(
            node
            for node in children_of(case[4], case[5].root)
            if case[4][0][node] == AST["AstConstDecl"]
        )
        function = top_level_functions(case)[-1]
        case[4][1][declaration] = case[4][1][function]

    def global_const_value_kind(case):
        declaration = next(
            node
            for node in children_of(case[4], case[5].root)
            if case[4][0][node] == AST["AstConstDecl"]
        )
        value = children_of(case[4], declaration)[2]
        case[4][0][value] = AST["AstPlaceUse"]

    def global_const_name_head(case):
        declaration = next(
            node
            for node in children_of(case[4], case[5].root)
            if case[4][0][node] == AST["AstConstDecl"]
        )
        name = children_of(case[4], declaration)[0]
        function = top_level_functions(case)[-1]
        statement = next(
            node
            for node in range(case[5].count)
            if case[4][0][node] == AST["AstSet"]
            and function <= node
        )
        value = children_of(case[4], statement)[1]
        case[4][1][name] = case[4][1][value]

    def assert_redirected_global_rejected():
        source = (
            b"const writer_zero: u64 = 0_u64;\n"
            b"const writer_one: u64 = 1_u64;\n"
            + global_writer.split(b"\n", 1)[1]
        )
        case, function = assert_clean(source)
        constants = [
            node
            for node in children_of(case[4], case[5].root)
            if case[4][0][node] == AST["AstConstDecl"]
        ]
        slot = next(
            index
            for index in range(case[9].count)
            if case[7][3][index] == constants[0]
        )
        case[7][3][slot] = constants[1]
        work = make_work(library, case[5].count)
        kind, report = invoke_dispatch(library, case, function, work)
        assert (kind, report.status, report.function) == (
            CAPABILITY_UNSUPPORTED,
            BODY_UNSUPPORTED,
            function,
        ), (kind, report.status, report.function, report.related)
        assert_output_guards(work)

    assert_mutation_unsupported(report_writer, field_target_kind)
    assert_mutation_unsupported(report_writer, deref_base_kind)
    assert_mutation_unsupported(report_writer, uniq_mode_kind)
    assert_mutation_unsupported(report_writer, writes_effect_kind)
    assert_mutation_unsupported(mixed_writer, mixed_shared_mode_kind)
    assert_mutation_unsupported(mixed_writer, mixed_reads_region_kind)
    assert_direct_reader_mutation_rejected(mixed_writer, mixed_call_terminal)
    assert_direct_reader_mutation_rejected(mixed_writer, mixed_duplicate_traps_node)
    assert_direct_constructor_mutation_rejected(constructor_payload_shape)
    assert_direct_constructor_mutation_rejected(constructor_enum_header)
    assert_direct_constructor_mutation_rejected(constructor_root_terminal)
    assert_direct_reader_mutation_rejected(global_writer, global_const_header)
    assert_direct_reader_mutation_rejected(global_writer, global_const_value_kind)
    assert_direct_reader_mutation_rejected(global_writer, global_const_name_head)
    assert_redirected_global_rejected()

def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))
        configure(library)
        assert_reader_flat_report_writer(library)
    print(
        "semantic writer: same-region multi-root writes-only and exact two-region "
        "mixed flat writers; "
        "own values, canonical integers, prior direct u64 constants, nullary "
        "tags, attributed call RHS values, and hostile effect, nominal, binding, "
        "shape, topology, and deferred-profile fences pass"
    )


if __name__ == "__main__":
    main()
