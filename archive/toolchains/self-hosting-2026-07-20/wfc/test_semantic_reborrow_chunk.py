#!/usr/bin/env python3
"""Audit the exact guarded eight-byte chunk reborrow slice."""

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
from test_semantic_reborrow_rw import REBORROW_RW
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


PUSH_ONLY = REBORROW_RW.split(b"fn emit_mark", 1)[0]
CHUNK = (
    b"fn emit_chunk ['o] (out: &uniq 'o PushTape, count: own u64, "
    b"b0: own u8, b1: own u8, b2: own u8, b3: own u8, "
    b"b4: own u8, b5: own u8, b6: own u8, b7: own u8) "
    b"-> own unit reads('o), writes('o), traps {\n"
    b"  let chunk_count_valid: own Bool = ile<u64>(count, 8_u64);\n"
    b"  match chunk_count_valid {\n"
    b"    True() => {\n"
    b"    }\n"
    b"    False() => {\n"
    b"      set deref(out).status = PushClean();\n"
    b"      return unit;\n"
    b"    }\n"
    b"  }\n"
    b"  match ige<u64>(count, 1_u64) {\n"
    b"    True() => {\n"
    b"      region 'chunk_b0 {\n"
    b"        push_byte(out: &uniq 'chunk_b0 deref(out), byte: b0);\n"
    b"      }\n"
    b"    }\n"
    b"    False() => {\n"
    b"      return unit;\n"
    b"    }\n"
    b"  }\n"
    b"  match ige<u64>(count, 2_u64) {\n"
    b"    True() => {\n"
    b"      region 'chunk_b1 {\n"
    b"        push_byte(out: &uniq 'chunk_b1 deref(out), byte: b1);\n"
    b"      }\n"
    b"    }\n"
    b"    False() => {\n"
    b"      return unit;\n"
    b"    }\n"
    b"  }\n"
    b"  match ige<u64>(count, 3_u64) {\n"
    b"    True() => {\n"
    b"      region 'chunk_b2 {\n"
    b"        push_byte(out: &uniq 'chunk_b2 deref(out), byte: b2);\n"
    b"      }\n"
    b"    }\n"
    b"    False() => {\n"
    b"      return unit;\n"
    b"    }\n"
    b"  }\n"
    b"  match ige<u64>(count, 4_u64) {\n"
    b"    True() => {\n"
    b"      region 'chunk_b3 {\n"
    b"        push_byte(out: &uniq 'chunk_b3 deref(out), byte: b3);\n"
    b"      }\n"
    b"    }\n"
    b"    False() => {\n"
    b"      return unit;\n"
    b"    }\n"
    b"  }\n"
    b"  match ige<u64>(count, 5_u64) {\n"
    b"    True() => {\n"
    b"      region 'chunk_b4 {\n"
    b"        push_byte(out: &uniq 'chunk_b4 deref(out), byte: b4);\n"
    b"      }\n"
    b"    }\n"
    b"    False() => {\n"
    b"      return unit;\n"
    b"    }\n"
    b"  }\n"
    b"  match ige<u64>(count, 6_u64) {\n"
    b"    True() => {\n"
    b"      region 'chunk_b5 {\n"
    b"        push_byte(out: &uniq 'chunk_b5 deref(out), byte: b5);\n"
    b"      }\n"
    b"    }\n"
    b"    False() => {\n"
    b"      return unit;\n"
    b"    }\n"
    b"  }\n"
    b"  match ige<u64>(count, 7_u64) {\n"
    b"    True() => {\n"
    b"      region 'chunk_b6 {\n"
    b"        push_byte(out: &uniq 'chunk_b6 deref(out), byte: b6);\n"
    b"      }\n"
    b"    }\n"
    b"    False() => {\n"
    b"      return unit;\n"
    b"    }\n"
    b"  }\n"
    b"  match ige<u64>(count, 8_u64) {\n"
    b"    True() => {\n"
    b"      region 'chunk_b7 {\n"
    b"        push_byte(out: &uniq 'chunk_b7 deref(out), byte: b7);\n"
    b"      }\n"
    b"    }\n"
    b"    False() => {\n"
    b"    }\n"
    b"  }\n"
    b"  return unit;\n"
    b"}\n"
)
REBORROW_CHUNK = PUSH_ONLY + CHUNK


def replace_last(source, old, new):
    before, separator, after = source.rpartition(old)
    assert separator, old
    return before + new + after


def assert_reborrow_chunk_boundary(library):
    def classify(source=REBORROW_CHUNK):
        case = parsed(library, source)
        function = top_level_functions(case)[-1]
        work = make_work(library, case[5].count)
        kind, report = invoke_dispatch(library, case, function, work)
        return case, function, work, kind, report

    def assert_clean(source=REBORROW_CHUNK):
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
    assert_clean(
        REBORROW_CHUNK.replace(b"push_byte", b"put_octet")
        .replace(b"emit_chunk", b"send_octets")
        .replace(b"chunk_count_valid", b"within_limit")
        .replace(b"'chunk_b", b"'octet_scope_")
    )

    # The ten-parameter signature and its same-region rows are exact.
    for source in (
        replace_last(REBORROW_CHUNK, b"out: &uniq 'o PushTape", b"out: &'o PushTape"),
        REBORROW_CHUNK.replace(b"count: own u64, b0", b"count: own u8, b0", 1),
        REBORROW_CHUNK.replace(b"b7: own u8) ->", b"b7: own u64) ->", 1),
        replace_last(
            REBORROW_CHUNK,
            b"reads('o), writes('o), traps {",
            b"writes('o), traps {",
        ),
        replace_last(
            REBORROW_CHUNK,
            b"reads('o), writes('o), traps {",
            b"reads('o), traps {",
        ),
        replace_last(
            REBORROW_CHUNK,
            b"reads('o), writes('o), traps {",
            b"reads('o), writes('o) {",
        ),
    ):
        assert_unsupported(source)

    # Count validation, invalid-state handling, and the ordered thresholds are
    # fixed structurally; nearby control bodies remain outside the profile.
    for old, new in (
        (b"ile<u64>(count, 8_u64)", b"ilt<u64>(count, 8_u64)"),
        (b"ile<u64>(count, 8_u64)", b"ile<u64>(count, 7_u64)"),
        (b"chunk_count_valid: own Bool", b"chunk_count_valid: own u64"),
        (b"set deref(out).status = PushClean();", b"set deref(out).count = 0_u64;"),
        (b"set deref(out).status = PushClean();", b"set deref(out).status = True();"),
        (b"match ige<u64>(count, 1_u64)", b"match igt<u64>(count, 1_u64)"),
        (b"match ige<u64>(count, 1_u64)", b"match ige<u64>(count, 2_u64)"),
        (b"byte: b0", b"byte: b1"),
        (b"&uniq 'chunk_b0 deref(out)", b"&'chunk_b0 deref(out)"),
        (b"&uniq 'chunk_b0 deref(out)", b"&uniq 'other deref(out)"),
        (b"&uniq 'chunk_b0 deref(out)", b"&uniq 'chunk_b0 deref(out).count"),
        (b"push_byte(out: &uniq 'chunk_b0", b"push_byte<'chunk_b0>(out: &uniq 'chunk_b0"),
        (
            b"out: &uniq 'chunk_b0 deref(out), byte: b0",
            b"byte: b0, out: &uniq 'chunk_b0 deref(out)",
        ),
    ):
        assert_unsupported(REBORROW_CHUNK.replace(old, new, 1))
    assert_unsupported(
        REBORROW_CHUNK.replace(
            b"    False() => {\n      return unit;\n    }\n  }\n"
            b"  match ige<u64>(count, 2_u64)",
            b"    False() => {\n    }\n  }\n"
            b"  match ige<u64>(count, 2_u64)",
            1,
        )
    )
    assert_unsupported(
        REBORROW_CHUNK.replace(
            b"match ige<u64>(count, 8_u64)",
            b"match ige<u64>(count, 7_u64)",
            1,
        )
    )
    assert_unsupported(
        REBORROW_CHUNK.replace(
            b"ilt<u64>(slot, capacity)", b"ile<u64>(slot, capacity)", 1
        )
    )

    def nodes(case, function):
        columns = case[4]
        direct = children_of(columns, function)
        outer_region = children_of(columns, direct[1])[0]
        output_parameter = direct[2]
        count_parameter = direct[3]
        byte_parameter = direct[4]
        reads_region = children_of(columns, direct[14])[0]
        writes_region = children_of(columns, direct[15])[0]
        body = direct[17]
        valid_let, invalid_match, first_threshold = children_of(columns, body)[:3]
        valid_name, _, _, valid_compare = children_of(columns, valid_let)
        count_use = children_of(columns, valid_compare)[1]
        invalid_false = children_of(columns, invalid_match)[2]
        invalid_false_block = children_of(columns, invalid_false)[0]
        invalid_set = children_of(columns, invalid_false_block)[0]
        status_target = children_of(columns, invalid_set)[0]
        true_arm = children_of(columns, first_threshold)[1]
        true_block = children_of(columns, true_arm)[0]
        region_block = children_of(columns, true_block)[0]
        local_region, inner_block = children_of(columns, region_block)
        expression = children_of(columns, inner_block)[0]
        call = children_of(columns, expression)[0]
        output_argument, byte_argument = children_of(columns, call)
        borrow = children_of(columns, output_argument)[0]
        child_region, deref_place = children_of(columns, borrow)
        parent = children_of(columns, deref_place)[0]
        byte_use = children_of(columns, byte_argument)[0]
        callee = top_level_functions(case)[0]
        callee_direct = children_of(columns, callee)
        struct_decl = next(
            node
            for node in children_of(columns, case[5].root)
            if columns[0][node] == AST["AstStructDecl"]
        )
        status_field = next(
            node
            for node in children_of(columns, struct_decl)
            if columns[0][node] == AST["AstField"]
            and bytes(case[0][columns[2][node] : columns[3][node]]).startswith(
                b"status:"
            )
        )
        return {
            "outer_region": outer_region,
            "output_parameter": output_parameter,
            "count_parameter": count_parameter,
            "byte_parameter": byte_parameter,
            "reads_region": reads_region,
            "writes_region": writes_region,
            "valid_name": valid_name,
            "count_use": count_use,
            "local_region": local_region,
            "child_region": child_region,
            "call": call,
            "callee_name": callee_direct[0],
            "output_argument": output_argument,
            "callee_output": callee_direct[2],
            "byte_argument": byte_argument,
            "callee_byte": callee_direct[3],
            "parent": parent,
            "byte_use": byte_use,
            "status_target": status_target,
            "status_field": status_field,
            "borrow": borrow,
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

    def shared_borrow(case, function):
        selected = nodes(case, function)
        case[4][0][selected["borrow"]] = AST["AstSharedBorrow"]

    def argument_cycle(case, function):
        selected = nodes(case, function)
        case[4][6][selected["output_argument"]] = selected["output_argument"]

    for mutate in (
        redirect_head("reads_region", "outer_region"),
        redirect_head("writes_region", "outer_region"),
        redirect_head("count_use", "count_parameter"),
        redirect_head("valid_name", "count_parameter"),
        redirect_head("local_region", "child_region"),
        redirect_head("child_region", "local_region"),
        redirect_head("call", "callee_name"),
        redirect_head("callee_name", "call"),
        redirect_head("output_argument", "callee_output"),
        redirect_head("callee_output", "output_argument"),
        redirect_head("byte_argument", "callee_byte"),
        redirect_head("callee_byte", "byte_argument"),
        redirect_head("parent", "output_parameter"),
        redirect_head("output_parameter", "parent"),
        redirect_head("byte_use", "byte_parameter"),
        redirect_head("byte_parameter", "byte_use"),
        redirect_head("status_target", "status_field"),
        shared_borrow,
        argument_cycle,
    ):
        assert_direct_mutation_rejected(mutate)


def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))
        configure(library)
        assert_reborrow_chunk_boundary(library)
    print(
        "semantic reborrow chunk: exact ten-parameter signature, guarded "
        "eight-step whole-parent push sequence, independent callee proof, "
        "source anchoring, topology, and closed nearby control shapes pass"
    )


if __name__ == "__main__":
    main()
