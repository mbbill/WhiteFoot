#!/usr/bin/env python3
"""Audit the exact terminating recursive u64 decimal emitter."""

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
from test_semantic_reborrow_chunk import replace_last
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
DIGITS = (
    b"const decimal_digits: array<u8, 10> = "
    b"[48_u8, 49_u8, 50_u8, 51_u8, 52_u8, "
    b"53_u8, 54_u8, 55_u8, 56_u8, 57_u8];\n"
)
EMITTER = (
    b"fn emit_u64 ['o] (out: &uniq 'o PushTape, value: own u64) "
    b"-> own unit reads('o), writes('o), traps {\n"
    b"  let has_higher: own Bool = ige<u64>(value, 10_u64);\n"
    b"  match has_higher {\n"
    b"    True() => {\n"
    b"      let higher: own u64 = idiv.trap<u64>(value, 10_u64);\n"
    b"      region 'higher_digits {\n"
    b"        emit_u64(out: &uniq 'higher_digits deref(out), value: higher);\n"
    b"      }\n"
    b"    }\n"
    b"    False() => {\n"
    b"    }\n"
    b"  }\n"
    b"  let remainder: own u64 = irem.trap<u64>(value, 10_u64);\n"
    b"  let digit: own u8 = index<u8>(decimal_digits, remainder);\n"
    b"  region 'last_digit {\n"
    b"    push_byte(out: &uniq 'last_digit deref(out), byte: digit);\n"
    b"  }\n"
    b"  return unit;\n"
    b"}\n"
)
REBORROW_U64 = PUSH_ONLY + DIGITS + EMITTER


def assert_reborrow_u64_boundary(library):
    def classify(source=REBORROW_U64):
        case = parsed(library, source)
        function = top_level_functions(case)[-1]
        work = make_work(library, case[5].count)
        kind, report = invoke_dispatch(library, case, function, work)
        return case, function, work, kind, report

    def assert_clean(source=REBORROW_U64):
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
        REBORROW_U64.replace(b"push_byte", b"put_octet")
        .replace(b"decimal_digits", b"number_glyphs")
        .replace(b"emit_u64", b"write_number")
        .replace(b"has_higher", b"needs_prefix")
        .replace(b"higher_digits", b"prefix_scope")
        .replace(b"last_digit", b"suffix_scope")
    )

    # Signature, effect rows, recursive decrease, and the two local loans are
    # a single exact boundary.
    for source in (
        REBORROW_U64.replace(
            b"fn emit_u64 ['o] (out: &uniq 'o PushTape",
            b"fn emit_u64 ['o] (out: &'o PushTape",
            1,
        ),
        REBORROW_U64.replace(b"value: own u64) ->", b"value: own u8) ->", 1),
        replace_last(
            REBORROW_U64,
            b"reads('o), writes('o), traps {",
            b"writes('o), traps {",
        ),
        replace_last(
            REBORROW_U64,
            b"reads('o), writes('o), traps {",
            b"reads('o), traps {",
        ),
        replace_last(
            REBORROW_U64,
            b"reads('o), writes('o), traps {",
            b"reads('o), writes('o) {",
        ),
        REBORROW_U64.replace(b"ige<u64>(value, 10_u64)", b"igt<u64>(value, 10_u64)", 1),
        REBORROW_U64.replace(b"ige<u64>(value, 10_u64)", b"ige<u64>(value, 9_u64)", 1),
        REBORROW_U64.replace(b"has_higher: own Bool", b"has_higher: own u64", 1),
        REBORROW_U64.replace(b"idiv.trap<u64>", b"idiv.wrap<u64>", 1),
        REBORROW_U64.replace(
            b"idiv.trap<u64>(value, 10_u64)",
            b"idiv.trap<u64>(value, 11_u64)",
            1,
        ),
        REBORROW_U64.replace(b"value: higher", b"value: value", 1),
        REBORROW_U64.replace(
            b"emit_u64(out: &uniq 'higher_digits",
            b"missing_emit(out: &uniq 'higher_digits",
            1,
        ),
        REBORROW_U64.replace(
            b"&uniq 'higher_digits deref(out)",
            b"&'higher_digits deref(out)",
            1,
        ),
        REBORROW_U64.replace(
            b"&uniq 'higher_digits deref(out)",
            b"&uniq 'higher_digits deref(out).count",
            1,
        ),
        REBORROW_U64.replace(
            b"emit_u64(out: &uniq 'higher_digits",
            b"emit_u64<'higher_digits>(out: &uniq 'higher_digits",
            1,
        ),
        REBORROW_U64.replace(
            b"        emit_u64(out: &uniq 'higher_digits",
            b"        let ignored: own unit = emit_u64(out: &uniq 'higher_digits",
            1,
        ),
        REBORROW_U64.replace(
            b"  match has_higher {\n    True() => {",
            b"  match has_higher {\n    False() => {",
            1,
        ),
        REBORROW_U64.replace(
            b"    False() => {\n    }\n  }\n  let remainder",
            b"    False() => {\n      return unit;\n    }\n  }\n  let remainder",
            1,
        ),
        REBORROW_U64.replace(b"irem.trap<u64>", b"idiv.trap<u64>", 1),
        replace_last(REBORROW_U64, b"10_u64", b"11_u64"),
        replace_last(REBORROW_U64, b"index<u8>", b"index<u64>"),
        REBORROW_U64.replace(b"decimal_digits, remainder", b"decimal_digits, higher", 1),
        REBORROW_U64.replace(b"byte: digit", b"byte: 48_u8", 1),
        REBORROW_U64.replace(b"'last_digit", b"'higher_digits"),
        REBORROW_U64.replace(
            b"    push_byte(out: &uniq 'last_digit",
            b"    let ignored: own unit = push_byte(out: &uniq 'last_digit",
            1,
        ),
        replace_last(
            REBORROW_U64,
            b"  return unit;\n}\n",
            b"  let extra: own u64 = 0_u64;\n  return unit;\n}\n",
        ),
    ):
        assert_unsupported(source)

    # The global is immutable and must be the exact ten-entry decimal table.
    for source in (
        REBORROW_U64.replace(b"array<u8, 10>", b"array<u8, 9>", 1),
        REBORROW_U64.replace(b"array<u8, 10>", b"array<u64, 10>", 1),
        REBORROW_U64.replace(b"48_u8, 49_u8", b"49_u8, 48_u8", 1),
        REBORROW_U64.replace(b"57_u8]", b"58_u8]", 1),
        REBORROW_U64.replace(b"48_u8", b"048_u8", 1),
        REBORROW_U64.replace(b"decimal_digits, remainder", b"missing_digits, remainder", 1),
    ):
        assert_unsupported(source)

    # The final callee is independently re-proven, not trusted by name.
    assert_unsupported(
        REBORROW_U64.replace(b"ilt<u64>(slot, capacity)", b"ile<u64>(slot, capacity)", 1)
    )

    def nodes(case, function):
        columns = case[4]
        direct = children_of(columns, function)
        body = direct[9]
        has_let, match_node, remainder_let, digit_let, push_region, _ = children_of(
            columns, body
        )
        has_name, _, _, has_compare = children_of(columns, has_let)
        value_use = children_of(columns, has_compare)[1]
        true_arm = children_of(columns, match_node)[1]
        true_block = children_of(columns, true_arm)[0]
        higher_let, recursive_region = children_of(columns, true_block)
        higher_name = children_of(columns, higher_let)[0]
        recursive_local, recursive_block = children_of(columns, recursive_region)
        recursive_expression = children_of(columns, recursive_block)[0]
        recursive_call = children_of(columns, recursive_expression)[0]
        recursive_output, recursive_value = children_of(columns, recursive_call)
        recursive_borrow = children_of(columns, recursive_output)[0]
        recursive_child, recursive_deref = children_of(columns, recursive_borrow)
        recursive_parent = children_of(columns, recursive_deref)[0]
        recursive_value_use = children_of(columns, recursive_value)[0]
        remainder_name = children_of(columns, remainder_let)[0]
        digit_name, _, _, digit_index = children_of(columns, digit_let)
        digit_base = children_of(columns, digit_index)[1]
        push_local, push_block = children_of(columns, push_region)
        push_expression = children_of(columns, push_block)[0]
        push_call = children_of(columns, push_expression)[0]
        push_output = children_of(columns, push_call)[0]
        const_decl = next(
            node
            for node in children_of(columns, case[5].root)
            if columns[0][node] == AST["AstConstDecl"]
        )
        const_name = children_of(columns, const_decl)[0]
        return {
            "function_name": direct[0],
            "outer_region": children_of(columns, direct[1])[0],
            "output_parameter": direct[2],
            "value_parameter": direct[3],
            "has_name": has_name,
            "value_use": value_use,
            "higher_name": higher_name,
            "recursive_local": recursive_local,
            "recursive_child": recursive_child,
            "recursive_call": recursive_call,
            "recursive_output": recursive_output,
            "recursive_parent": recursive_parent,
            "recursive_value": recursive_value,
            "recursive_value_use": recursive_value_use,
            "remainder_name": remainder_name,
            "digit_name": digit_name,
            "digit_base": digit_base,
            "const_name": const_name,
            "push_local": push_local,
            "push_call": push_call,
            "push_output": push_output,
            "recursive_borrow": recursive_borrow,
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

    def shared_recursive_borrow(case, function):
        selected = nodes(case, function)
        case[4][0][selected["recursive_borrow"]] = AST["AstSharedBorrow"]

    def argument_cycle(case, function):
        selected = nodes(case, function)
        case[4][6][selected["recursive_output"]] = selected["recursive_output"]

    for mutate in (
        redirect_head("value_use", "value_parameter"),
        redirect_head("recursive_call", "function_name"),
        redirect_head("function_name", "recursive_call"),
        redirect_head("recursive_local", "recursive_child"),
        redirect_head("recursive_child", "recursive_local"),
        redirect_head("recursive_parent", "output_parameter"),
        redirect_head("recursive_value_use", "higher_name"),
        redirect_head("digit_base", "const_name"),
        redirect_head("push_local", "outer_region"),
        shared_recursive_borrow,
        argument_cycle,
    ):
        assert_direct_mutation_rejected(mutate)


def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))
        configure(library)
        assert_reborrow_u64_boundary(library)
    print(
        "semantic recursive u64 emitter: exact decreasing self-call, "
        "ten-byte immutable digit table, remainder index, proven byte push, "
        "source anchoring, topology, and closed nearby shapes pass"
    )


if __name__ == "__main__":
    main()
