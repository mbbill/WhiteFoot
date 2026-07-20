#!/usr/bin/env python3
"""Audit the exact reset, prefix, and recursive-number probe wrapper."""

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
from test_semantic_reborrow_chunk import REBORROW_CHUNK, replace_last
from test_semantic_reborrow_u64 import DIGITS, EMITTER
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


RESET = (
    b"fn reset_tape ['o] (out: &uniq 'o PushTape) "
    b"-> own unit writes('o) {\n"
    b"  set deref(out).count = 0_u64;\n"
    b"  set deref(out).status = PushClean();\n"
    b"  return unit;\n"
    b"}\n"
)
PREFIX = (
    b"fn emit_prefix ['o] (out: &uniq 'o PushTape) "
    b"-> own unit reads('o), writes('o), traps {\n"
    b"  region 'prefix_chunk {\n"
    b"    emit_chunk(out: &uniq 'prefix_chunk deref(out), count: 4_u64, "
    b"b0: 119_u8, b1: 102_u8, b2: 99_u8, b3: 32_u8, "
    b"b4: 32_u8, b5: 32_u8, b6: 32_u8, b7: 32_u8);\n"
    b"  }\n"
    b"  return unit;\n"
    b"}\n"
)
PROBE_HEAD = (
    b"fn emit_probe ['o] (out: &uniq 'o PushTape, value: own u64) "
    b"-> own unit reads('o), writes('o), traps {\n"
)
RESET_REGION = (
    b"  region 'reset_scope {\n"
    b"    reset_tape(out: &uniq 'reset_scope deref(out));\n"
    b"  }\n"
)
PREFIX_REGION = (
    b"  region 'prefix_scope {\n"
    b"    emit_prefix(out: &uniq 'prefix_scope deref(out));\n"
    b"  }\n"
)
NUMBER_REGION = (
    b"  region 'number_scope {\n"
    b"    emit_u64(out: &uniq 'number_scope deref(out), value: value);\n"
    b"  }\n"
)
PROBE_TAIL = b"  return unit;\n}\n"
PROBE = PROBE_HEAD + RESET_REGION + PREFIX_REGION + NUMBER_REGION + PROBE_TAIL
REBORROW_PROBE = REBORROW_CHUNK + RESET + PREFIX + DIGITS + EMITTER + PROBE


def assert_reborrow_probe_boundary(library):
    def classify(source=REBORROW_PROBE):
        case = parsed(library, source)
        function = top_level_functions(case)[-1]
        work = make_work(library, case[5].count)
        kind, report = invoke_dispatch(library, case, function, work)
        return case, function, work, kind, report

    def assert_clean(source=REBORROW_PROBE):
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
        REBORROW_PROBE.replace(b"push_byte", b"put_octet")
        .replace(b"emit_chunk", b"send_octets")
        .replace(b"reset_tape", b"clear_tape")
        .replace(b"emit_prefix", b"write_prefix")
        .replace(b"decimal_digits", b"number_glyphs")
        .replace(b"emit_u64", b"write_number")
        .replace(b"emit_probe", b"write_probe")
        .replace(b"'reset_scope", b"'clear_scope")
        .replace(b"'prefix_scope", b"'header_scope")
        .replace(b"'number_scope", b"'decimal_scope")
    )
    renamed = replace_last(renamed, b"value: own u64", b"number: own u64")
    renamed = replace_last(renamed, b"value: value", b"value: number")
    assert_clean(renamed)

    reset_prefix_swapped = (
        REBORROW_CHUNK
        + RESET
        + PREFIX
        + DIGITS
        + EMITTER
        + PROBE_HEAD
        + PREFIX_REGION
        + RESET_REGION
        + NUMBER_REGION
        + PROBE_TAIL
    )
    prefix_number_swapped = (
        REBORROW_CHUNK
        + RESET
        + PREFIX
        + DIGITS
        + EMITTER
        + PROBE_HEAD
        + RESET_REGION
        + NUMBER_REGION
        + PREFIX_REGION
        + PROBE_TAIL
    )
    extra_region = replace_last(
        REBORROW_PROBE,
        PROBE_TAIL,
        RESET_REGION.replace(b"reset_scope", b"extra_scope") + PROBE_TAIL,
    )
    for source in (
        replace_last(
            REBORROW_PROBE,
            b"out: &uniq 'o PushTape",
            b"out: &'o PushTape",
        ),
        replace_last(REBORROW_PROBE, b"value: own u64", b"value: own u8"),
        replace_last(
            REBORROW_PROBE,
            b"reads('o), writes('o), traps {",
            b"writes('o), traps {",
        ),
        replace_last(
            REBORROW_PROBE,
            b"reads('o), writes('o), traps {",
            b"reads('o), traps {",
        ),
        replace_last(
            REBORROW_PROBE,
            b"reads('o), writes('o), traps {",
            b"reads('o), writes('o) {",
        ),
        reset_prefix_swapped,
        prefix_number_swapped,
        REBORROW_PROBE.replace(
            b"&uniq 'reset_scope deref(out)", b"&'reset_scope deref(out)", 1
        ),
        REBORROW_PROBE.replace(
            b"&uniq 'reset_scope deref(out)",
            b"&uniq 'reset_scope deref(out).count",
            1,
        ),
        replace_last(
            REBORROW_PROBE,
            b"reset_tape(out:",
            b"reset_tape<'reset_scope>(out:",
        ),
        replace_last(
            REBORROW_PROBE,
            b"    reset_tape(out:",
            b"    let ignored: own unit = reset_tape(out:",
        ),
        replace_last(REBORROW_PROBE, b"reset_tape(out:", b"missing_reset(out:"),
        REBORROW_PROBE.replace(
            b"&uniq 'prefix_scope deref(out)", b"&'prefix_scope deref(out)", 1
        ),
        REBORROW_PROBE.replace(
            b"&uniq 'prefix_scope deref(out)",
            b"&uniq 'prefix_scope deref(out).count",
            1,
        ),
        replace_last(
            REBORROW_PROBE,
            b"emit_prefix(out:",
            b"emit_prefix<'prefix_scope>(out:",
        ),
        replace_last(
            REBORROW_PROBE,
            b"    emit_prefix(out:",
            b"    let ignored: own unit = emit_prefix(out:",
        ),
        replace_last(REBORROW_PROBE, b"emit_prefix(out:", b"missing_prefix(out:"),
        REBORROW_PROBE.replace(
            b"&uniq 'number_scope deref(out)", b"&'number_scope deref(out)", 1
        ),
        REBORROW_PROBE.replace(
            b"&uniq 'number_scope deref(out)",
            b"&uniq 'number_scope deref(out).count",
            1,
        ),
        replace_last(
            REBORROW_PROBE,
            b"emit_u64(out:",
            b"emit_u64<'number_scope>(out:",
        ),
        replace_last(
            REBORROW_PROBE,
            b"    emit_u64(out:",
            b"    let ignored: own unit = emit_u64(out:",
        ),
        replace_last(REBORROW_PROBE, b"value: value", b"value: out"),
        replace_last(REBORROW_PROBE, b"emit_u64(out:", b"missing_number(out:"),
        REBORROW_PROBE.replace(b"'prefix_scope", b"'reset_scope"),
        REBORROW_PROBE.replace(b"'number_scope", b"'reset_scope"),
        REBORROW_PROBE.replace(b"'number_scope", b"'o"),
        extra_region,
        replace_last(
            REBORROW_PROBE,
            PROBE_TAIL,
            b"  let extra: own u64 = 0_u64;\n" + PROBE_TAIL,
        ),
        replace_last(REBORROW_PROBE, PROBE_TAIL, b"  return value;\n}\n"),
    ):
        assert_unsupported(source)

    # Each dependency is independently re-proven at its use site.
    renamed_reset = RESET.replace(b"(out:", b"(sink:", 1).replace(
        b"deref(out)", b"deref(sink)"
    )
    renamed_prefix = PREFIX.replace(b"(out:", b"(sink:", 1).replace(
        b"deref(out)", b"deref(sink)"
    )
    for source in (
        REBORROW_CHUNK + renamed_reset + PREFIX + DIGITS + EMITTER + PROBE,
        REBORROW_CHUNK + RESET + renamed_prefix + DIGITS + EMITTER + PROBE,
        REBORROW_PROBE.replace(
            b"fn reset_tape ['o] (out: &uniq 'o PushTape)",
            b"fn reset_tape ['o] (out: &'o PushTape)",
            1,
        ),
        REBORROW_PROBE.replace(b"count: 4_u64", b"count: 04_u64", 1),
        REBORROW_PROBE.replace(
            b"ile<u64>(count, 8_u64)", b"ilt<u64>(count, 8_u64)", 1
        ),
        REBORROW_PROBE.replace(
            b"ilt<u64>(slot, capacity)", b"ile<u64>(slot, capacity)", 1
        ),
        REBORROW_PROBE.replace(
            b"irem.trap<u64>(value, 10_u64)",
            b"idiv.trap<u64>(value, 10_u64)",
            1,
        ),
        REBORROW_PROBE.replace(b"array<u8, 10>", b"array<u8, 9>", 1),
    ):
        assert_unsupported(source)

    def nodes(case, function):
        columns = case[4]
        direct = children_of(columns, function)
        body = direct[9]
        reset_region, prefix_region, numeric_region, _ = children_of(columns, body)

        def region_nodes(region):
            local, inner = children_of(columns, region)
            expression = children_of(columns, inner)[0]
            call = children_of(columns, expression)[0]
            arguments = children_of(columns, call)
            output = arguments[0]
            borrow = children_of(columns, output)[0]
            child, deref_place = children_of(columns, borrow)
            parent = children_of(columns, deref_place)[0]
            return local, call, output, borrow, child, parent, arguments

        reset = region_nodes(reset_region)
        prefix = region_nodes(prefix_region)
        numeric = region_nodes(numeric_region)
        callees = top_level_functions(case)
        return {
            "outer_region": children_of(columns, direct[1])[0],
            "output_parameter": direct[2],
            "value_parameter": direct[3],
            "reset_region": reset_region,
            "reset_local": reset[0],
            "reset_call": reset[1],
            "reset_output": reset[2],
            "reset_borrow": reset[3],
            "reset_child": reset[4],
            "reset_parent": reset[5],
            "prefix_local": prefix[0],
            "prefix_call": prefix[1],
            "prefix_output": prefix[2],
            "prefix_borrow": prefix[3],
            "prefix_child": prefix[4],
            "prefix_parent": prefix[5],
            "numeric_local": numeric[0],
            "numeric_call": numeric[1],
            "numeric_output": numeric[2],
            "numeric_borrow": numeric[3],
            "numeric_child": numeric[4],
            "numeric_parent": numeric[5],
            "numeric_value": children_of(columns, numeric[6][1])[0],
            "reset_callee": children_of(columns, callees[2])[0],
            "prefix_callee": children_of(columns, callees[3])[0],
            "numeric_callee": children_of(columns, callees[4])[0],
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

    def shared_prefix_borrow(case, function):
        selected = nodes(case, function)
        case[4][0][selected["prefix_borrow"]] = AST["AstSharedBorrow"]

    def argument_cycle(case, function):
        selected = nodes(case, function)
        case[4][6][selected["numeric_output"]] = selected["numeric_output"]

    def region_cycle(case, function):
        selected = nodes(case, function)
        case[4][6][selected["reset_region"]] = selected["reset_region"]

    for mutate in (
        redirect_head("reset_local", "reset_child"),
        redirect_head("reset_child", "reset_local"),
        redirect_head("reset_call", "reset_callee"),
        redirect_head("reset_output", "output_parameter"),
        redirect_head("reset_borrow", "prefix_borrow"),
        redirect_head("reset_parent", "output_parameter"),
        redirect_head("prefix_local", "prefix_child"),
        redirect_head("prefix_call", "prefix_callee"),
        redirect_head("prefix_output", "output_parameter"),
        redirect_head("prefix_parent", "output_parameter"),
        redirect_head("numeric_local", "numeric_child"),
        redirect_head("numeric_call", "numeric_callee"),
        redirect_head("numeric_output", "output_parameter"),
        redirect_head("numeric_parent", "output_parameter"),
        redirect_head("numeric_value", "value_parameter"),
        redirect_head("numeric_local", "outer_region"),
        shared_prefix_borrow,
        argument_cycle,
        region_cycle,
    ):
        assert_direct_mutation_rejected(mutate)


def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))
        configure(library)
        assert_reborrow_probe_boundary(library)
    print(
        "semantic output probe: exact reset, fixed prefix, and owned u64 "
        "sequence, independent nested proofs, source anchoring, topology, "
        "and closed nearby shapes pass"
    )


if __name__ == "__main__":
    main()
