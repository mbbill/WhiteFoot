#!/usr/bin/env python3
"""Audit the exact four-region fixed-literal chunk wrapper."""

import ctypes
import tempfile
from pathlib import Path

from test_lexer import build_library
from test_parser import AST_NONE, children_of
from test_semantic_body import (
    BODY_CLEAN,
    BODY_UNSUPPORTED,
    SemanticBodyReport,
    assert_output_guards,
    parsed,
)
from test_semantic_reborrow_chunk import REBORROW_CHUNK, replace_last
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


REGION_0 = (
    b"  region 'quad_0 {\n"
    b"    emit_chunk(out: &uniq 'quad_0 deref(out), count: 8_u64, "
    b"b0: 64_u8, b1: 108_u8, b2: 108_u8, b3: 118_u8, "
    b"b4: 109_u8, b5: 46_u8, b6: 117_u8, b7: 97_u8);\n"
    b"  }\n"
)
REGION_1 = (
    b"  region 'quad_1 {\n"
    b"    emit_chunk(out: &uniq 'quad_1 deref(out), count: 8_u64, "
    b"b0: 100_u8, b1: 100_u8, b2: 46_u8, b3: 119_u8, "
    b"b4: 105_u8, b5: 116_u8, b6: 104_u8, b7: 46_u8);\n"
    b"  }\n"
)
REGION_2 = (
    b"  region 'quad_2 {\n"
    b"    emit_chunk(out: &uniq 'quad_2 deref(out), count: 8_u64, "
    b"b0: 111_u8, b1: 118_u8, b2: 101_u8, b3: 114_u8, "
    b"b4: 102_u8, b5: 108_u8, b6: 111_u8, b7: 119_u8);\n"
    b"  }\n"
)
REGION_3 = (
    b"  region 'quad_3 {\n"
    b"    emit_chunk(out: &uniq 'quad_3 deref(out), count: 4_u64, "
    b"b0: 46_u8, b1: 105_u8, b2: 54_u8, b3: 52_u8, "
    b"b4: 32_u8, b5: 32_u8, b6: 32_u8, b7: 32_u8);\n"
    b"  }\n"
)
REGION_4 = (
    b"  region 'quad_4 {\n"
    b"    emit_chunk(out: &uniq 'quad_4 deref(out), count: 0_u64, "
    b"b0: 0_u8, b1: 0_u8, b2: 0_u8, b3: 0_u8, "
    b"b4: 0_u8, b5: 0_u8, b6: 0_u8, b7: 0_u8);\n"
    b"  }\n"
)
QUAD_WRAPPER = (
    b"fn emit_quad ['o] (out: &uniq 'o PushTape) "
    b"-> own unit reads('o), writes('o), traps {\n"
    + REGION_0
    + REGION_1
    + REGION_2
    + REGION_3
    + b"  return unit;\n}\n"
)
REBORROW_CHUNK_QUAD_WRAPPER = REBORROW_CHUNK + QUAD_WRAPPER


def assert_reborrow_chunk_wrapper_quad_boundary(library):
    def classify(source=REBORROW_CHUNK_QUAD_WRAPPER):
        case = parsed(library, source)
        function = top_level_functions(case)[-1]
        work = make_work(library, case[5].count)
        kind, report = invoke_dispatch(library, case, function, work)
        return case, function, work, kind, report

    def assert_clean(source=REBORROW_CHUNK_QUAD_WRAPPER):
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
        REBORROW_CHUNK_QUAD_WRAPPER.replace(b"push_byte", b"put_octet")
        .replace(b"emit_chunk", b"send_octets")
        .replace(b"emit_quad", b"send_quad")
        .replace(b"'quad_", b"'scope_")
    )
    assert_clean(
        REBORROW_CHUNK_QUAD_WRAPPER.replace(
            b"count: 4_u64", b"count: 9_u64", 1
        )
    )

    for source in (
        replace_last(
            REBORROW_CHUNK_QUAD_WRAPPER,
            b"out: &uniq 'o PushTape",
            b"out: &'o PushTape",
        ),
        REBORROW_CHUNK_QUAD_WRAPPER.replace(
            b"count: 4_u64", b"count: 04_u64", 1
        ),
        REBORROW_CHUNK_QUAD_WRAPPER.replace(
            b"b0: 46_u8", b"b0: 256_u8", 1
        ),
        REBORROW_CHUNK_QUAD_WRAPPER.replace(
            b"count: 4_u64, b0: 46_u8",
            b"b0: 46_u8, count: 4_u64",
            1,
        ),
        REBORROW_CHUNK_QUAD_WRAPPER.replace(
            b"&uniq 'quad_1 deref(out)", b"&'quad_1 deref(out)", 1
        ),
        REBORROW_CHUNK_QUAD_WRAPPER.replace(
            b"&uniq 'quad_2 deref(out)",
            b"&uniq 'quad_2 deref(out).count",
            1,
        ),
        REBORROW_CHUNK_QUAD_WRAPPER.replace(
            b"emit_chunk(out: &uniq 'quad_2",
            b"emit_chunk<'quad_2>(out: &uniq 'quad_2",
            1,
        ),
        REBORROW_CHUNK_QUAD_WRAPPER.replace(
            b"    emit_chunk(out: &uniq 'quad_3",
            b"    let ignored: own unit = emit_chunk(out: &uniq 'quad_3",
            1,
        ),
        REBORROW_CHUNK_QUAD_WRAPPER.replace(
            b"emit_chunk(out: &uniq 'quad_1",
            b"missing_chunk(out: &uniq 'quad_1",
            1,
        ),
        REBORROW_CHUNK_QUAD_WRAPPER.replace(
            b"emit_chunk(out: &uniq 'quad_2",
            b"push_byte(out: &uniq 'quad_2",
            1,
        ),
        REBORROW_CHUNK_QUAD_WRAPPER.replace(b"'quad_3", b"'quad_1"),
        REBORROW_CHUNK_QUAD_WRAPPER.replace(b"'quad_2", b"'o"),
        REBORROW_CHUNK_QUAD_WRAPPER.replace(REGION_2, b"", 1),
        replace_last(
            REBORROW_CHUNK_QUAD_WRAPPER,
            b"  return unit;\n}\n",
            REGION_4 + b"  return unit;\n}\n",
        ),
        REBORROW_CHUNK_QUAD_WRAPPER.replace(
            b"b7: 32_u8);\n  }\n  return unit;",
            b"b7: 32_u8);\n    return unit;\n  }\n  return unit;",
            1,
        ),
        REBORROW_CHUNK_QUAD_WRAPPER.replace(
            b"ile<u64>(count, 8_u64)", b"ilt<u64>(count, 8_u64)", 1
        ),
        REBORROW_CHUNK_QUAD_WRAPPER.replace(
            b"ilt<u64>(slot, capacity)", b"ile<u64>(slot, capacity)", 1
        ),
    ):
        assert_unsupported(source)

    case, function = assert_clean()
    block = children_of(case[4], function)[8]
    first_region = children_of(case[4], block)[0]
    case[4][6][first_region] = first_region
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


def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))
        configure(library)
        assert_reborrow_chunk_wrapper_quad_boundary(library)
    print(
        "semantic reborrow chunk wrapper quad: exact four sequential "
        "fixed-literal calls, pairwise-fresh locals, independent nested "
        "callee proof, topology, and closed three/five/composite shapes pass"
    )


if __name__ == "__main__":
    main()
