#!/usr/bin/env python3
"""Audit the exact guarded shared-input span emitter."""

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
from test_semantic_reborrow_chunk import PUSH_ONLY, replace_last
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


SPAN = (
    b"fn emit_span ['s, 'o] (source: &'s buffer<u8>, start: own u64, "
    b"end: own u64, out: &uniq 'o PushTape) -> own unit "
    b"reads('s 'o), writes('o), traps {\n"
    b"  let ordered: own Bool = ile<u64>(start, end);\n"
    b"  let source_size: own u64 = len<u8>(deref(source));\n"
    b"  let in_source: own Bool = ile<u64>(end, source_size);\n"
    b"  let valid: own Bool = band<Bool>(ordered, in_source);\n"
    b"  match valid {\n"
    b"    True() => {\n"
    b"    }\n"
    b"    False() => {\n"
    b"      set deref(out).status = PushFull();\n"
    b"      return unit;\n"
    b"    }\n"
    b"  }\n"
    b"  let cursor: own u64 = start;\n"
    b"  loop @span_bytes {\n"
    b"    let done: own Bool = ieq<u64>(cursor, end);\n"
    b"    match done {\n"
    b"      True() => {\n"
    b"        return unit;\n"
    b"      }\n"
    b"      False() => {\n"
    b"      }\n"
    b"    }\n"
    b"    let byte: own u8 = index<u8>(deref(source), cursor);\n"
    b"    region 'span_byte {\n"
    b"      push_byte(out: &uniq 'span_byte deref(out), byte: byte);\n"
    b"    }\n"
    b"    set cursor = iadd.trap<u64>(cursor, 1_u64);\n"
    b"  }\n"
    b"}\n"
)
REBORROW_SPAN = PUSH_ONLY + SPAN


def assert_reborrow_span_boundary(library):
    def classify(source=REBORROW_SPAN):
        case = parsed(library, source)
        function = top_level_functions(case)[-1]
        work = make_work(library, case[5].count)
        kind, report = invoke_dispatch(library, case, function, work)
        return case, function, work, kind, report

    def assert_clean(source=REBORROW_SPAN):
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
    renamed = (
        REBORROW_SPAN.replace(b"PushStatus", b"WriteState")
        .replace(b"PushTape", b"WriteTape")
        .replace(b"PushClean", b"WriteReady")
        .replace(b"PushFull", b"WriteStopped")
        .replace(b"push_byte", b"put_octet")
        .replace(b"emit_span", b"send_range")
        .replace(b"source", b"input_bytes")
        .replace(b"start", b"begin_at")
        .replace(b"end", b"stop_at")
        .replace(b"out", b"sink")
        .replace(b"ordered", b"forward")
        .replace(b"in_input_bytes", b"within_input")
        .replace(b"input_bytes_size", b"input_length")
        .replace(b"valid", b"range_valid")
        .replace(b"cursor", b"position")
        .replace(b"done", b"finished")
        .replace(b"byte", b"octet")
        .replace(b"'span_octet", b"'item_scope")
        .replace(b"@span_octets", b"@range_loop")
        .replace(b"'s", b"'input")
        .replace(b"'o", b"'output")
    )
    assert_clean(renamed)

    # The two-region signature fixes parameter modes, types, row order, and
    # the one shared-input plus one exclusive-output topology.
    for source in (
        replace_last(REBORROW_SPAN, b"source: &'s buffer<u8>", b"source: &uniq 's buffer<u8>"),
        replace_last(REBORROW_SPAN, b"source: &'s buffer<u8>", b"source: &'s buffer<u64>"),
        replace_last(REBORROW_SPAN, b"start: own u64", b"start: own u8"),
        replace_last(REBORROW_SPAN, b"end: own u64", b"end: &'s u64"),
        replace_last(REBORROW_SPAN, b"out: &uniq 'o PushTape", b"out: &'o PushTape"),
        replace_last(REBORROW_SPAN, b"-> own unit", b"-> own u64"),
        replace_last(REBORROW_SPAN, b"reads('s 'o)", b"reads('o 's)"),
        replace_last(REBORROW_SPAN, b"reads('s 'o)", b"reads('s)"),
        replace_last(REBORROW_SPAN, b"writes('o)", b"writes('s)"),
        replace_last(REBORROW_SPAN, b", traps {", b" {"),
        replace_last(REBORROW_SPAN, b"['s, 'o]", b"['o, 's]"),
    ):
        assert_unsupported(source)

    # Entry validation must prove start <= end <= len(source) in the exact
    # order before the cursor and loop are introduced.
    for source in (
        replace_last(REBORROW_SPAN, b"ile<u64>(start, end)", b"ilt<u64>(start, end)"),
        replace_last(REBORROW_SPAN, b"ile<u64>(start, end)", b"ile<u64>(end, start)"),
        replace_last(REBORROW_SPAN, b"len<u8>(deref(source))", b"len<u64>(deref(source))"),
        replace_last(REBORROW_SPAN, b"len<u8>(deref(source))", b"len<u8>(source)"),
        replace_last(REBORROW_SPAN, b"ile<u64>(end, source_size)", b"ilt<u64>(end, source_size)"),
        replace_last(REBORROW_SPAN, b"ile<u64>(end, source_size)", b"ile<u64>(source_size, end)"),
        replace_last(REBORROW_SPAN, b"band<Bool>(ordered, in_source)", b"bor<Bool>(ordered, in_source)"),
        replace_last(REBORROW_SPAN, b"band<Bool>(ordered, in_source)", b"band<Bool>(in_source, ordered)"),
        replace_last(REBORROW_SPAN, b"match valid", b"match ordered"),
        replace_last(REBORROW_SPAN, b"set deref(out).status", b"set deref(out).count"),
        replace_last(REBORROW_SPAN, b"let cursor: own u64 = start", b"let cursor: own u64 = end"),
    ):
        assert_unsupported(source)

    # The loop exits exactly at end, reads source[cursor], lends the whole
    # output for one push, and advances by canonical trapping one.
    for source in (
        replace_last(REBORROW_SPAN, b"ieq<u64>(cursor, end)", b"ine<u64>(cursor, end)"),
        replace_last(REBORROW_SPAN, b"ieq<u64>(cursor, end)", b"ieq<u64>(end, cursor)"),
        replace_last(REBORROW_SPAN, b"match done", b"match valid"),
        replace_last(REBORROW_SPAN, b"True() => {\n        return unit;", b"False() => {\n        return unit;"),
        replace_last(REBORROW_SPAN, b"index<u8>(deref(source), cursor)", b"index<u64>(deref(source), cursor)"),
        replace_last(REBORROW_SPAN, b"index<u8>(deref(source), cursor)", b"index<u8>(deref(source), end)"),
        replace_last(REBORROW_SPAN, b"index<u8>(deref(source), cursor)", b"index<u8>(deref(out).bytes, cursor)"),
        replace_last(REBORROW_SPAN, b"region 'span_byte", b"region 's"),
        replace_last(REBORROW_SPAN, b"region 'span_byte", b"region 'o"),
        replace_last(REBORROW_SPAN, b"&uniq 'span_byte deref(out)", b"&'span_byte deref(out)"),
        replace_last(REBORROW_SPAN, b"&uniq 'span_byte deref(out)", b"&uniq 'span_byte deref(out).count"),
        replace_last(REBORROW_SPAN, b"push_byte(out:", b"push_byte<'span_byte>(out:"),
        replace_last(REBORROW_SPAN, b"push_byte(out:", b"missing_push(out:"),
        replace_last(
            REBORROW_SPAN,
            b"push_byte(out: &uniq 'span_byte deref(out), byte: byte)",
            b"push_byte(byte: byte, out: &uniq 'span_byte deref(out))",
        ),
        replace_last(REBORROW_SPAN, b"byte: byte", b"byte: cursor"),
        replace_last(REBORROW_SPAN, b"    push_byte(out:", b"    let ignored: own unit = push_byte(out:"),
        replace_last(
            REBORROW_SPAN,
            b"      push_byte(out:",
            b"      let extra: own u64 = 0_u64;\n      push_byte(out:",
        ),
        replace_last(REBORROW_SPAN, b"set cursor =", b"set end ="),
        replace_last(REBORROW_SPAN, b"iadd.trap<u64>(cursor, 1_u64)", b"iadd.wrap<u64>(cursor, 1_u64)"),
        replace_last(REBORROW_SPAN, b"iadd.trap<u64>(cursor, 1_u64)", b"iadd.trap<u64>(cursor, 2_u64)"),
        replace_last(REBORROW_SPAN, b"  loop @span_bytes", b"  let extra: own u64 = 0_u64;\n  loop @span_bytes"),
        replace_last(REBORROW_SPAN, b"    set cursor =", b"    return unit;\n    set cursor ="),
    ):
        assert_unsupported(source)

    # The push dependency is resolved structurally and re-proven at the call.
    renamed_output_callee = PUSH_ONLY.replace(b"(out:", b"(sink:", 1).replace(
        b"deref(out)", b"deref(sink)"
    )
    renamed_byte_callee = PUSH_ONLY.replace(
        b"byte: own u8", b"item: own u8", 1
    ).replace(b" = byte;", b" = item;", 1)
    for source in (
        REBORROW_SPAN.replace(b"out: &uniq 'o PushTape, byte: own u8", b"out: &'o PushTape, byte: own u8", 1),
        REBORROW_SPAN.replace(b"len<u8>(deref(out).bytes)", b"len<u8>(deref(out).count)", 1),
        REBORROW_SPAN.replace(b"ilt<u64>(slot, capacity)", b"ile<u64>(slot, capacity)", 1),
        REBORROW_SPAN.replace(b"index<u8>(deref(out).bytes, slot)", b"index<u8>(deref(out).bytes, capacity)", 1),
        REBORROW_SPAN.replace(b"iadd.trap<u64>(slot, 1_u64)", b"iadd.wrap<u64>(slot, 1_u64)", 1),
        REBORROW_SPAN.replace(b"byte: own u8", b"byte: own u64", 1),
        REBORROW_SPAN.replace(b"-> own unit reads('o), writes('o), traps", b"-> own u64 reads('o), writes('o), traps", 1),
        REBORROW_SPAN.replace(b"reads('o), writes('o), traps", b"writes('o), traps", 1),
        renamed_output_callee + SPAN,
        renamed_byte_callee + SPAN,
    ):
        assert_unsupported(source)

    def nodes(case, function):
        columns = case[4]
        direct = children_of(columns, function)
        regions = children_of(columns, direct[1])
        body = children_of(columns, direct[11])
        ordered = children_of(columns, body[0])
        size = children_of(columns, body[1])
        in_source = children_of(columns, body[2])
        valid = children_of(columns, body[3])
        cursor = children_of(columns, body[5])
        loop_label, loop_block = children_of(columns, body[6])
        loop = children_of(columns, loop_block)
        done = children_of(columns, loop[0])
        byte = children_of(columns, loop[2])
        cursor_set = children_of(columns, loop[4])
        cursor_increment = children_of(columns, cursor_set[1])
        local_region, inner = children_of(columns, loop[3])
        expression = children_of(columns, inner)[0]
        call = children_of(columns, expression)[0]
        arguments = children_of(columns, call)
        output_argument = arguments[0]
        borrow = children_of(columns, output_argument)[0]
        child_region, deref_place = children_of(columns, borrow)
        parent = children_of(columns, deref_place)[0]
        callees = top_level_functions(case)
        return {
            "function_name": direct[0],
            "source_region": regions[0],
            "output_region": regions[1],
            "source_parameter": direct[2],
            "start_parameter": direct[3],
            "end_parameter": direct[4],
            "output_parameter": direct[5],
            "reads_source": children_of(columns, direct[8])[0],
            "reads_output": children_of(columns, direct[8])[1],
            "writes_output": children_of(columns, direct[9])[0],
            "ordered_name": ordered[0],
            "ordered_start": children_of(columns, ordered[3])[1],
            "size_source": children_of(columns, children_of(columns, size[3])[1])[0],
            "size_name": size[0],
            "in_source_name": in_source[0],
            "in_source_size": children_of(columns, in_source[3])[2],
            "valid_name": valid[0],
            "valid_ordered": children_of(columns, valid[3])[1],
            "valid_in_source": children_of(columns, valid[3])[2],
            "cursor_name": cursor[0],
            "cursor_start": cursor[3],
            "loop_label": loop_label,
            "done_name": done[0],
            "done_cursor": children_of(columns, done[3])[1],
            "done_end": children_of(columns, done[3])[2],
            "byte_name": byte[0],
            "byte_source": children_of(columns, children_of(columns, byte[3])[1])[0],
            "byte_cursor": children_of(columns, byte[3])[2],
            "cursor_set_target": cursor_set[0],
            "increment_cursor": cursor_increment[1],
            "local_region": local_region,
            "call": call,
            "output_argument": output_argument,
            "borrow": borrow,
            "child_region": child_region,
            "parent": parent,
            "callee_name": children_of(columns, callees[0])[0],
        }

    def assert_direct_mutation_rejected(mutate):
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

    def redirect_head(target, source):
        def mutate(case, function):
            selected = nodes(case, function)
            case[4][1][selected[target]] = case[4][1][selected[source]]

        return mutate

    def shared_output_borrow(case, function):
        selected = nodes(case, function)
        case[4][0][selected["borrow"]] = AST["AstSharedBorrow"]

    def argument_cycle(case, function):
        selected = nodes(case, function)
        case[4][6][selected["output_argument"]] = selected["output_argument"]

    def region_cycle(case, function):
        selected = nodes(case, function)
        case[4][6][selected["local_region"]] = selected["local_region"]

    def loop_sibling_cycle(case, function):
        columns = case[4]
        direct = children_of(columns, function)
        body = children_of(columns, direct[11])
        _, loop_block = children_of(columns, body[6])
        first_loop_statement = children_of(columns, loop_block)[0]
        columns[6][first_loop_statement] = first_loop_statement

    for mutate in (
        redirect_head("reads_source", "source_region"),
        redirect_head("reads_output", "output_region"),
        redirect_head("writes_output", "output_region"),
        redirect_head("end_parameter", "start_parameter"),
        redirect_head("ordered_start", "start_parameter"),
        redirect_head("size_source", "source_parameter"),
        redirect_head("in_source_size", "size_name"),
        redirect_head("valid_ordered", "ordered_name"),
        redirect_head("valid_in_source", "in_source_name"),
        redirect_head("cursor_name", "start_parameter"),
        redirect_head("cursor_start", "start_parameter"),
        redirect_head("done_cursor", "cursor_name"),
        redirect_head("done_end", "end_parameter"),
        redirect_head("byte_source", "source_parameter"),
        redirect_head("byte_cursor", "cursor_name"),
        redirect_head("cursor_set_target", "cursor_name"),
        redirect_head("increment_cursor", "cursor_name"),
        redirect_head("local_region", "child_region"),
        redirect_head("child_region", "local_region"),
        redirect_head("local_region", "source_region"),
        redirect_head("call", "callee_name"),
        redirect_head("output_argument", "output_parameter"),
        redirect_head("parent", "output_parameter"),
        redirect_head("done_name", "valid_name"),
        shared_output_borrow,
        argument_cycle,
        region_cycle,
        loop_sibling_cycle,
    ):
        assert_direct_mutation_rejected(mutate)


def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))
        configure(library)
        assert_reborrow_span_boundary(library)
    print(
        "semantic span reborrow: exact guarded shared range, terminating "
        "cursor loop, whole-output byte push, source anchoring, topology, "
        "and closed nearby shapes pass"
    )


if __name__ == "__main__":
    main()
