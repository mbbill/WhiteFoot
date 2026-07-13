#!/usr/bin/env python3
"""Audit the pure semantic capability frontier across a complete source unit."""

import ctypes
import tempfile
from pathlib import Path

from test_lexer import Buffer, TokenTape, build_library, compiler_source
from test_parser import (
    AST_FUNCTION,
    AST_FUNCTION_NAME,
    AST_NONE,
    AstTape,
    children_of,
)
from test_ast_validate import AstValidationReport
from test_semantic_body import (
    BODY_CLEAN,
    BODY_UNKNOWN_NAME,
    BODY_UNSUPPORTED,
    SemanticBodyScratch,
    assert_output_guards,
    configure as configure_semantic_body,
    fixture,
    make_outputs,
    parsed,
)
from test_semantic_facts import NodeFacts, TypeTape
from test_symbols import SymbolTape


UNIT_CLEAN = 0
UNIT_INVALID_TOKEN_TAPE = 1
UNIT_INVALID_AST_TAPE = 2
UNIT_INVALID_VALIDATION = 3
UNIT_INVALID_SYMBOL_TAPE = 4
UNIT_CAPACITY = 6

CAPABILITY_UNSUPPORTED = 4
CAPABILITY_FAILED = 0
CAPABILITY_LINEAR = 3


class SemanticCapabilityReport(ctypes.Structure):
    _fields_ = [
        ("status", ctypes.c_int32),
        ("function", ctypes.c_uint64),
        ("related", ctypes.c_uint64),
    ]


class SemanticUnitReport(ctypes.Structure):
    _fields_ = [
        ("status", ctypes.c_int32),
        ("total", ctypes.c_uint64),
        ("clean", ctypes.c_uint64),
        ("unsupported", ctypes.c_uint64),
        ("rejected", ctypes.c_uint64),
        ("first_unsupported", ctypes.c_uint64),
        ("first_rejected", ctypes.c_uint64),
    ]


def configure(library):
    configure_semantic_body(library)
    common = [
        Buffer,
        ctypes.POINTER(TokenTape),
        ctypes.POINTER(AstTape),
        ctypes.POINTER(AstValidationReport),
        ctypes.POINTER(SymbolTape),
    ]
    work = [
        ctypes.POINTER(TypeTape),
        ctypes.POINTER(NodeFacts),
        ctypes.POINTER(SemanticBodyScratch),
    ]
    library.semantic_unit_dispatch.argtypes = (
        common
        + [ctypes.c_uint64]
        + work
        + [ctypes.POINTER(SemanticCapabilityReport)]
    )
    library.semantic_unit_dispatch.restype = ctypes.c_int32
    library.semantic_unit_run.argtypes = (
        common + work + [ctypes.POINTER(SemanticUnitReport)]
    )
    library.semantic_unit_run.restype = None


def make_work(
    library,
    ast_count,
    *,
    type_capacity=4,
    fact_capacity=None,
    scratch_capacity=34,
):
    if fact_capacity is None:
        fact_capacity = ast_count
    return make_outputs(
        library,
        ast_count,
        type_caps=(type_capacity,) * 6,
        fact_caps=(fact_capacity,) * 8,
        scratch_caps=(scratch_capacity,) * 4,
    )


def unit_report_tuple(report):
    return tuple(getattr(report, field) for field, _ in report._fields_)


def invoke_unit(
    library,
    case,
    work,
    *,
    tokens=None,
    ast=None,
    validation=None,
    symbols=None,
):
    if tokens is None:
        tokens = case[3]
    if ast is None:
        ast = case[5]
    if validation is None:
        validation = case[6]
    if symbols is None:
        symbols = case[9]
    report = SemanticUnitReport(*([0x5A] * 7))
    library.semantic_unit_run(
        case[1],
        ctypes.byref(tokens),
        ctypes.byref(ast),
        ctypes.byref(validation),
        ctypes.byref(symbols),
        ctypes.byref(work[1]),
        ctypes.byref(work[3]),
        ctypes.byref(work[6]),
        ctypes.byref(report),
    )
    return report


def invoke_dispatch(library, case, function, work):
    report = SemanticCapabilityReport(99, 123, 456)
    kind = library.semantic_unit_dispatch(
        case[1],
        ctypes.byref(case[3]),
        ctypes.byref(case[5]),
        ctypes.byref(case[6]),
        ctypes.byref(case[9]),
        function,
        ctypes.byref(work[1]),
        ctypes.byref(work[3]),
        ctypes.byref(work[6]),
        ctypes.byref(report),
    )
    return kind, report


def clone_structure(value, **changes):
    fields = {
        name: getattr(value, name)
        for name, _ in value._fields_
    }
    fields.update(changes)
    return type(value)(*(fields[name] for name, _ in value._fields_))


def top_level_functions(case):
    columns = case[4]
    ast = case[5]
    return tuple(
        node
        for node in children_of(columns, ast.root)
        if columns[0][node] == AST_FUNCTION
    )


def function_name(data, case, function):
    columns = case[4]
    names = [
        node
        for node in children_of(columns, function)
        if columns[0][node] == AST_FUNCTION_NAME
    ]
    assert len(names) == 1, (function, names)
    name = names[0]
    return data[columns[2][name] : columns[3][name]]


def assert_compiler_coverage(library):
    data = compiler_source().encode("ascii")
    case = parsed(library, data)
    functions = top_level_functions(case)
    assert len(functions) == 477

    work = make_work(library, case[5].count)
    first = invoke_unit(library, case, work)
    expected = (
        UNIT_CLEAN,
        477,
        15,
        462,
        0,
        functions[14],
        AST_NONE,
    )
    assert unit_report_tuple(first) == expected
    assert function_name(data, case, first.first_unsupported) == (
        b"lexer_scan_op_suffix"
    )

    clean_ordinals = []
    for ordinal, function in enumerate(functions):
        _, report = invoke_dispatch(library, case, function, work)
        if report.status == BODY_CLEAN:
            clean_ordinals.append(ordinal)
        else:
            assert report.status == BODY_UNSUPPORTED, (
                ordinal,
                function_name(data, case, function),
                report.status,
                report.function,
                report.related,
            )
    assert tuple(clean_ordinals) == tuple(range(14)) + (16,)

    second = invoke_unit(library, case, work)
    assert unit_report_tuple(second) == unit_report_tuple(first)
    assert_output_guards(work)
    return case, work


def assert_legal_nonprofile_is_unsupported(library):
    data = (
        b"fn passthrough (value: own u64) -> own u64 pure {\n"
        b"  return value;\n"
        b"}\n"
    )
    case = parsed(library, data)
    (function,) = top_level_functions(case)
    assert len(children_of(case[4], function)) == 6
    work = make_work(library, case[5].count)

    kind, report = invoke_dispatch(library, case, function, work)
    assert (kind, report.status, report.function, report.related) == (
        CAPABILITY_UNSUPPORTED,
        BODY_UNSUPPORTED,
        function,
        function,
    )
    unit = invoke_unit(library, case, work)
    assert unit_report_tuple(unit) == (
        UNIT_CLEAN,
        1,
        0,
        1,
        0,
        function,
        AST_NONE,
    )
    assert_output_guards(work)

    name_collision = data.replace(b"passthrough", b"lexer_match3")
    collision_case = parsed(library, name_collision)
    (collision_function,) = top_level_functions(collision_case)
    collision_work = make_work(library, collision_case[5].count)
    kind, report = invoke_dispatch(
        library, collision_case, collision_function, collision_work
    )
    assert (kind, report.status, report.function) == (
        CAPABILITY_UNSUPPORTED,
        BODY_UNSUPPORTED,
        collision_function,
    )

    wrong_fixed_body = (
        b"fn lexer_match3 ['s] (source: &'s buffer<u8>, start: own u64, "
        b"a: own u8, b: own u8, c: own u8) -> own Bool "
        b"reads('s), traps {\n"
        b"  return True();\n"
        b"}\n"
    )
    wrong_case = parsed(library, wrong_fixed_body)
    (wrong_function,) = top_level_functions(wrong_case)
    wrong_work = make_work(library, wrong_case[5].count)
    kind, report = invoke_dispatch(
        library, wrong_case, wrong_function, wrong_work
    )
    assert (kind, report.status, report.function) == (
        CAPABILITY_UNSUPPORTED,
        BODY_UNSUPPORTED,
        wrong_function,
    )
    assert_output_guards(collision_work)
    assert_output_guards(wrong_work)


def assert_structural_profile_and_real_reject(library):
    renamed = fixture().replace(b"lexer_is_lower", b"arbitrary_predicate")
    renamed_case = parsed(library, renamed)
    (renamed_function,) = top_level_functions(renamed_case)
    renamed_work = make_work(library, renamed_case[5].count)
    kind, report = invoke_dispatch(
        library, renamed_case, renamed_function, renamed_work
    )
    assert (kind, report.status, report.function) == (
        CAPABILITY_LINEAR,
        BODY_CLEAN,
        renamed_function,
    )

    rejected = fixture(first_operand=b"missing")
    rejected_case = parsed(library, rejected)
    (rejected_function,) = top_level_functions(rejected_case)
    rejected_work = make_work(library, rejected_case[5].count)
    kind, report = invoke_dispatch(
        library, rejected_case, rejected_function, rejected_work
    )
    assert (kind, report.status, report.function) == (
        CAPABILITY_FAILED,
        BODY_UNKNOWN_NAME,
        rejected_function,
    )
    unit = invoke_unit(library, rejected_case, rejected_work)
    assert unit_report_tuple(unit) == (
        UNIT_CLEAN,
        1,
        0,
        0,
        1,
        AST_NONE,
        rejected_function,
    )
    assert_output_guards(renamed_work)
    assert_output_guards(rejected_work)


def assert_dynamic_linear_capacity(library):
    statements = [
        b"  let value0: own Bool = ige<u8>(c, 0_u8);\n"
    ]
    for ordinal in range(1, 34):
        previous = ordinal - 1
        statements.append(
            f"  let value{ordinal}: own Bool = bor<Bool>("
            f"value{previous}, value{previous});\n".encode("ascii")
        )
    data = (
        b"fn many_values (c: own u8) -> own Bool pure {\n"
        + b"".join(statements)
        + b"  return value33;\n"
        + b"}\n"
    )
    case = parsed(library, data)
    short = make_work(library, case[5].count, scratch_capacity=34)
    report = invoke_unit(library, case, short)
    assert unit_report_tuple(report) == (
        UNIT_CAPACITY,
        0,
        0,
        0,
        0,
        AST_NONE,
        AST_NONE,
    )

    exact = make_work(library, case[5].count, scratch_capacity=35)
    report = invoke_unit(library, case, exact)
    assert unit_report_tuple(report) == (
        UNIT_CLEAN,
        1,
        1,
        0,
        0,
        AST_NONE,
        AST_NONE,
    )
    assert_output_guards(short)
    assert_output_guards(exact)


def assert_canonical_failure(library, case, work, status, **changes):
    report = invoke_unit(library, case, work, **changes)
    assert unit_report_tuple(report) == (
        status,
        0,
        0,
        0,
        0,
        AST_NONE,
        AST_NONE,
    )
    assert_output_guards(work)


def assert_hostile_inputs_and_capacities(library, case, full_work):
    tokens = clone_structure(
        case[3], count=case[3].kinds.length + 1
    )
    assert_canonical_failure(
        library,
        case,
        full_work,
        UNIT_INVALID_TOKEN_TAPE,
        tokens=tokens,
    )

    ast = clone_structure(case[5], count=case[5].kinds.length + 1)
    assert_canonical_failure(
        library,
        case,
        full_work,
        UNIT_INVALID_AST_TAPE,
        ast=ast,
    )

    validation = clone_structure(case[6], status=1, node=case[5].root)
    assert_canonical_failure(
        library,
        case,
        full_work,
        UNIT_INVALID_VALIDATION,
        validation=validation,
    )

    symbols = clone_structure(case[9], count=case[9].namespaces.length + 1)
    assert_canonical_failure(
        library,
        case,
        full_work,
        UNIT_INVALID_SYMBOL_TAPE,
        symbols=symbols,
    )

    short_work = (
        make_work(library, case[5].count, type_capacity=3),
        make_work(
            library,
            case[5].count,
            fact_capacity=case[5].count - 1,
        ),
        make_work(library, case[5].count, scratch_capacity=33),
    )
    for work in short_work:
        assert_canonical_failure(
            library, case, work, UNIT_CAPACITY
        )


def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))
        configure(library)
        case, work = assert_compiler_coverage(library)
        assert_legal_nonprofile_is_unsupported(library)
        assert_structural_profile_and_real_reject(library)
        assert_dynamic_linear_capacity(library)
        assert_hostile_inputs_and_capacities(library, case, work)
    print(
        "semantic unit: compiler 477 total / 15 clean / 462 unsupported / "
        "0 rejected; exact clean ordinals, source-order frontier, legal "
        "nonprofile, structural rename, real reject, deterministic repeat, "
        "dynamic/hostile capacities, inputs, and guards pass"
    )


if __name__ == "__main__":
    main()
