#!/usr/bin/env python3
"""Lower real linear scalar functions from retained semantic facts to LLVM."""

import ctypes
import subprocess
import sys
import tempfile
from pathlib import Path

from test_ast_validate import AstValidationReport
from test_lexer import Buffer, TokenTape
from test_parser import AstTape, children_of
from test_semantic_body import (
    BODY_CLEAN,
    configure as configure_semantic_body,
    find_function_by_text,
    invoke,
    make_outputs,
    parsed,
)
from test_semantic_facts import NodeFacts, TypeTape
from test_llvm_text import (
    BYTE_CLEAN,
    BYTE_INVALID_STATE,
    BYTE_NEED_CAPACITY,
    GUARD,
    POISON,
    ByteTape,
    make_output,
)

import democ


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "compiler"
U64_MAX = (1 << 64) - 1
OP_NONE = 0
OP_IEQ = 5


def real_profile_source():
    data = (HERE / "src" / "lexer.xl").read_bytes()
    return data[: data.index(b"\nfn lexer_is_symbol")]


SOURCE = real_profile_source()
ORDER = (
    b"lexer_is_lower",
    b"lexer_is_upper",
    b"lexer_is_digit",
    b"lexer_is_space",
)

EXPECTED = {
    b"lexer_is_lower": b"""define i1 @lexer_is_lower(i8 %p0) {
entry:
  %v0 = icmp uge i8 %p0, 97
  %v1 = icmp ule i8 %p0, 122
  %v2 = and i1 %v0, %v1
  ret i1 %v2
}
""",
    b"lexer_is_upper": b"""define i1 @lexer_is_upper(i8 %p0) {
entry:
  %v0 = icmp uge i8 %p0, 65
  %v1 = icmp ule i8 %p0, 90
  %v2 = and i1 %v0, %v1
  ret i1 %v2
}
""",
    b"lexer_is_digit": b"""define i1 @lexer_is_digit(i8 %p0) {
entry:
  %v0 = icmp uge i8 %p0, 48
  %v1 = icmp ule i8 %p0, 57
  %v2 = and i1 %v0, %v1
  ret i1 %v2
}
""",
    b"lexer_is_space": b"""define i1 @lexer_is_space(i8 %p0) {
entry:
  %v0 = icmp eq i8 %p0, 32
  %v1 = icmp uge i8 %p0, 9
  %v2 = icmp ule i8 %p0, 13
  %v3 = and i1 %v1, %v2
  %v4 = or i1 %v0, %v3
  ret i1 %v4
}
""",
}


def compiler_source_isolated():
    names = [
        line.strip()
        for line in (HERE / "sources.txt").read_text().splitlines()
        if line.strip()
    ]
    excluded = {"src/frontend.xl", "src/llvm_scalar.xl", "src/llvm_linear.xl"}
    paths = [HERE / name for name in names if name not in excluded]
    paths.append(HERE / "src" / "llvm_linear.xl")
    return "\n\n".join(path.read_text().rstrip("\n") for path in paths) + "\n"


def build_library(directory):
    source = compiler_source_isolated()
    ir = democ.compile_program(source, alias=False)
    forbidden = [
        marker
        for marker in (
            " noalias",
            " readonly",
            " dereferenceable(",
            " willreturn",
            "!alias.scope",
            "!noalias",
            " memory(",
        )
        if marker in ir
    ]
    assert not forbidden, forbidden
    ll = directory / "llvm_linear_stage0.ll"
    library_path = directory / (
        "llvm_linear_stage0.dylib" if sys.platform == "darwin" else "llvm_linear_stage0.so"
    )
    ll.write_text(ir)
    cc = "/usr/bin/clang" if Path("/usr/bin/clang").exists() else "clang"
    command = [cc, "-O2"]
    command += ["-dynamiclib"] if sys.platform == "darwin" else ["-shared", "-fPIC"]
    command += [str(ll), "-o", str(library_path)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f"clang rejected the linear emitter:\n{result.stderr}")
    return ctypes.CDLL(str(library_path))


def configure(library):
    configure_semantic_body(library)
    library.lexer_run.argtypes = [Buffer, ctypes.POINTER(TokenTape)]
    library.lexer_run.restype = None
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
    signature = [
        Buffer,
        ctypes.POINTER(TokenTape),
        ctypes.POINTER(AstTape),
        ctypes.c_uint64,
        ctypes.POINTER(TypeTape),
        ctypes.POINTER(NodeFacts),
        ctypes.POINTER(ByteTape),
    ]
    library.llvm_linear_append_function.argtypes = signature
    library.llvm_linear_append_function.restype = None
    library.llvm_linear_emit_function.argtypes = signature
    library.llvm_linear_emit_function.restype = None


def analyze(library, parsed_case, name):
    ast = parsed_case[5]
    function = find_function_by_text(SOURCE, parsed_case[4], ast, name)
    outputs = make_outputs(library, ast.count, scratch_caps=(5, 5, 5, 5))
    report = invoke(library, parsed_case, function, outputs)
    assert report.status == BODY_CLEAN, (name, report.status, report.node, report.related)
    return function, outputs


def facts_from(outputs):
    return outputs[1], outputs[3]


def call(library, parsed_case, analyzed, out, *, append):
    function, outputs = analyzed
    types, facts = facts_from(outputs)
    emitter = (
        library.llvm_linear_append_function
        if append
        else library.llvm_linear_emit_function
    )
    emitter(
        parsed_case[1],
        ctypes.byref(parsed_case[3]),
        ctypes.byref(parsed_case[5]),
        function,
        ctypes.byref(types),
        ctypes.byref(facts),
        ctypes.byref(out),
    )


def output_bytes(storage, out):
    return bytes(storage[: min(out.count, len(storage) - 1)])


def assert_single_modes(library, parsed_case, analyzed, expected):
    measured_storage, measured = make_output(0)
    call(library, parsed_case, analyzed, measured, append=False)
    assert (measured.status, measured.count) == (BYTE_NEED_CAPACITY, len(expected))
    assert measured_storage[0] == GUARD

    exact_storage, exact = make_output(len(expected))
    call(library, parsed_case, analyzed, exact, append=False)
    assert (exact.status, exact.count) == (BYTE_CLEAN, len(expected))
    assert output_bytes(exact_storage, exact) == expected
    assert exact_storage[len(expected)] == GUARD

    short_capacity = len(expected) - 1
    short_storage, short = make_output(short_capacity)
    call(library, parsed_case, analyzed, short, append=False)
    assert (short.status, short.count) == (BYTE_NEED_CAPACITY, len(expected))
    assert output_bytes(short_storage, short) == expected[:short_capacity]
    assert short_storage[short_capacity] == GUARD

    exact.count = U64_MAX
    exact.status = BYTE_INVALID_STATE
    for index in range(len(expected)):
        exact_storage[index] = POISON
    call(library, parsed_case, analyzed, exact, append=False)
    assert (exact.status, exact.count) == (BYTE_CLEAN, len(expected))
    assert output_bytes(exact_storage, exact) == expected
    assert exact_storage[len(expected)] == GUARD


def assert_append_matrix(library, parsed_case, analyzed_by_name):
    combined = b"".join(EXPECTED[name] for name in ORDER)
    analyzed = [analyzed_by_name[name] for name in ORDER]

    exact_storage, exact = make_output(len(combined))
    observed = 0
    for name, item in zip(ORDER, analyzed):
        call(library, parsed_case, item, exact, append=True)
        observed += len(EXPECTED[name])
        assert (exact.status, exact.count) == (BYTE_CLEAN, observed)
    assert output_bytes(exact_storage, exact) == combined
    assert exact_storage[len(combined)] == GUARD

    measured_storage, measured = make_output(0)
    observed = 0
    for name, item in zip(ORDER, analyzed):
        call(library, parsed_case, item, measured, append=True)
        observed += len(EXPECTED[name])
        assert (measured.status, measured.count) == (BYTE_NEED_CAPACITY, observed)
    assert measured_storage[0] == GUARD

    for capacity in range(len(combined)):
        storage, out = make_output(capacity)
        for item in analyzed:
            call(library, parsed_case, item, out, append=True)
        assert (out.status, out.count) == (BYTE_NEED_CAPACITY, len(combined))
        assert output_bytes(storage, out) == combined[:capacity]
        assert storage[capacity] == GUARD
    return combined


def first_call(parsed_case, function):
    columns = parsed_case[4]
    block = children_of(columns, function)[5]
    first_let = children_of(columns, block)[0]
    return children_of(columns, first_let)[3]


def assert_fact_driven(library, parsed_case, analyzed):
    function, outputs = analyzed
    fact_storage = outputs[2]
    call_node = first_call(parsed_case, function)
    literal = children_of(parsed_case[4], call_node)[2]
    prior_operation = fact_storage[3][call_node]
    prior_constant = fact_storage[4][literal]
    fact_storage[3][call_node] = OP_IEQ
    fact_storage[4][literal] = 42
    try:
        storage, out = make_output(len(EXPECTED[b"lexer_is_lower"]) + 8)
        call(library, parsed_case, analyzed, out, append=False)
        observed = output_bytes(storage, out)
        assert out.status == BYTE_CLEAN
        assert b"%v0 = icmp eq i8 %p0, 42\n" in observed
    finally:
        fact_storage[3][call_node] = prior_operation
        fact_storage[4][literal] = prior_constant

    source_storage = parsed_case[0]
    offset = SOURCE.index(b"ige<u8>")
    original = bytes(source_storage[offset : offset + 3])
    for index, byte in enumerate(b"zzz"):
        source_storage[offset + index] = byte
    try:
        storage, out = make_output(len(EXPECTED[b"lexer_is_lower"]))
        call(library, parsed_case, analyzed, out, append=False)
        assert (out.status, out.count) == (
            BYTE_CLEAN,
            len(EXPECTED[b"lexer_is_lower"]),
        )
        assert output_bytes(storage, out) == EXPECTED[b"lexer_is_lower"]
    finally:
        for index, byte in enumerate(original):
            source_storage[offset + index] = byte


def assert_append_atomicity(library, parsed_case, lower, upper):
    lower_expected = EXPECTED[b"lexer_is_lower"]
    capacity = len(lower_expected) + len(EXPECTED[b"lexer_is_upper"])
    storage, out = make_output(capacity)
    call(library, parsed_case, lower, out, append=True)
    assert (out.status, out.count) == (BYTE_CLEAN, len(lower_expected))
    before = bytes(storage[:capacity])

    upper_function, upper_outputs = upper
    call_node = first_call(parsed_case, upper_function)
    operations = upper_outputs[2][3]
    prior = operations[call_node]
    operations[call_node] = OP_NONE
    try:
        call(library, parsed_case, upper, out, append=True)
    finally:
        operations[call_node] = prior
    assert (out.status, out.count) == (BYTE_INVALID_STATE, len(lower_expected))
    assert bytes(storage[:capacity]) == before
    assert storage[capacity] == GUARD

    count = out.count
    snapshot = bytes(storage[:capacity])
    call(library, parsed_case, upper, out, append=True)
    assert (out.status, out.count) == (BYTE_INVALID_STATE, count)
    assert bytes(storage[:capacity]) == snapshot

    for status, count in (
        (99, 0),
        (BYTE_CLEAN, capacity + 1),
        (BYTE_NEED_CAPACITY, 0),
        (BYTE_NEED_CAPACITY, U64_MAX - 1),
    ):
        hostile_storage, hostile = make_output(capacity)
        hostile.status = status
        hostile.count = count
        call(library, parsed_case, lower, hostile, append=True)
        assert (hostile.status, hostile.count) == (BYTE_INVALID_STATE, count)
        assert all(byte == POISON for byte in hostile_storage[:capacity])
        assert hostile_storage[capacity] == GUARD


def assert_profile_boundaries(library, parsed_case, space):
    direct_source = b"""fn direct (c: own u8) -> own Bool pure {
  return ieq<u8>(c, 0_u8);
}
"""
    direct_case = parsed(library, direct_source)
    direct_function = find_function_by_text(
        direct_source, direct_case[4], direct_case[5], b"direct"
    )
    direct_outputs = make_outputs(
        library, direct_case[5].count, scratch_caps=(1, 1, 1, 1)
    )
    direct_report = invoke(
        library, direct_case, direct_function, direct_outputs
    )
    assert direct_report.status == BODY_CLEAN
    direct_storage, direct_out = make_output(256)
    call(
        library,
        direct_case,
        (direct_function, direct_outputs),
        direct_out,
        append=False,
    )
    assert (direct_out.status, direct_out.count) == (BYTE_INVALID_STATE, 0)
    assert all(byte == POISON for byte in direct_storage[:-1])
    assert direct_storage[-1] == GUARD

    function, outputs = space
    statements = children_of(
        parsed_case[4], children_of(parsed_case[4], function)[5]
    )
    control_let = statements[3]
    control_call = children_of(parsed_case[4], control_let)[3]
    control_ge_use = children_of(parsed_case[4], control_call)[1]
    resolutions = outputs[2][1]
    prior = resolutions[control_ge_use]
    resolutions[control_ge_use] = control_let
    try:
        storage, out = make_output(len(EXPECTED[b"lexer_is_space"]))
        call(library, parsed_case, space, out, append=False)
        assert (out.status, out.count) == (BYTE_INVALID_STATE, 0)
        assert all(byte == POISON for byte in storage[:-1])
        assert storage[-1] == GUARD
    finally:
        resolutions[control_ge_use] = prior


def assert_selected_hostile_facts(library, parsed_case, analyzed):
    function, outputs = analyzed
    fact_storage = outputs[2]
    call_node = first_call(parsed_case, function)
    literal = children_of(parsed_case[4], call_node)[2]

    def rejected():
        storage, out = make_output(len(EXPECTED[b"lexer_is_lower"]))
        call(library, parsed_case, analyzed, out, append=False)
        assert (out.status, out.count) == (BYTE_INVALID_STATE, 0)
        assert all(byte == POISON for byte in storage[:-1])
        assert storage[-1] == GUARD

    mutations = (
        (fact_storage[3], call_node, OP_NONE),
        (fact_storage[4], literal, 256),
        (fact_storage[2], call_node, 7),
    )
    for column, index, replacement in mutations:
        prior = column[index]
        column[index] = replacement
        try:
            rejected()
        finally:
            column[index] = prior

    facts = outputs[3]
    prior_count = facts.count
    facts.count -= 1
    try:
        rejected()
    finally:
        facts.count = prior_count


def assert_executable_ir(directory, ir):
    ll = directory / "linear_profile.ll"
    library_path = directory / (
        "linear_profile.dylib" if sys.platform == "darwin" else "linear_profile.so"
    )
    ll.write_bytes(ir)
    cc = "/usr/bin/clang" if Path("/usr/bin/clang").exists() else "clang"
    command = [cc, "-O3"]
    command += ["-dynamiclib"] if sys.platform == "darwin" else ["-shared", "-fPIC"]
    command += [str(ll), "-o", str(library_path)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f"clang rejected generated linear IR:\n{result.stderr}")
    generated = ctypes.CDLL(str(library_path))
    predicates = {
        b"lexer_is_lower": lambda value: 97 <= value <= 122,
        b"lexer_is_upper": lambda value: 65 <= value <= 90,
        b"lexer_is_digit": lambda value: 48 <= value <= 57,
        b"lexer_is_space": lambda value: value == 32 or 9 <= value <= 13,
    }
    for name, predicate in predicates.items():
        function = getattr(generated, name.decode())
        function.argtypes = [ctypes.c_uint8]
        function.restype = ctypes.c_bool
        for value in range(256):
            assert function(value) is predicate(value), (name, value)


def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        directory = Path(raw_directory)
        library = build_library(directory)
        configure(library)
        parsed_case = parsed(library, SOURCE)
        analyzed = {
            name: analyze(library, parsed_case, name)
            for name in ORDER
        }

        for name in ORDER:
            assert_single_modes(library, parsed_case, analyzed[name], EXPECTED[name])
        assert_fact_driven(library, parsed_case, analyzed[b"lexer_is_lower"])
        assert_append_atomicity(
            library,
            parsed_case,
            analyzed[b"lexer_is_lower"],
            analyzed[b"lexer_is_upper"],
        )
        assert_selected_hostile_facts(
            library, parsed_case, analyzed[b"lexer_is_lower"]
        )
        assert_profile_boundaries(
            library, parsed_case, analyzed[b"lexer_is_space"]
        )
        combined = assert_append_matrix(library, parsed_case, analyzed)
        assert_executable_ir(directory, combined)

        print(
            "linear LLVM: 4 real predicates, exact/measure/all-short/repeat, "
            "fact-driven lowering, atomic append, hostile facts/profile boundaries, "
            "clang, and all 1024 u8 cases pass"
        )


if __name__ == "__main__":
    main()
