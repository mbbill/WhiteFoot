#!/usr/bin/env python3
"""Lower lexer_match3 with XL's internal ABI and test it on the current host."""

import ctypes
import random
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from test_lexer import Buffer, TokenTape, compiler_source
from test_parser import AstTape, children_of
from test_semantic_buffer import (
    BODY_CLEAN,
    NodeFacts,
    TypeTape,
    configure as configure_semantic_buffer,
    invoke_run,
    make_buffer_outputs,
    match3_nodes,
    semantic_case,
)
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


HERE = Path(__file__).resolve().parent
U64_MAX = (1 << 64) - 1
PREFIX = b"checked-prefix:"

EXPECTED_PRELUDE = b"""declare { i64, i1 } @llvm.uadd.with.overflow.i64(i64, i64)
declare void @llvm.trap()

"""

EXPECTED_FUNCTION = b"""define i1 @lexer_match3({ ptr, i64 } %p0, i64 %p1, i8 %p2, i8 %p3, i8 %p4) {
entry:
  %v0 = extractvalue { ptr, i64 } %p0, 0
  %v1 = extractvalue { ptr, i64 } %p0, 1
  %v2 = call { i64, i1 } @llvm.uadd.with.overflow.i64(i64 %p1, i64 1)
  %v3 = extractvalue { i64, i1 } %v2, 0
  %v4 = extractvalue { i64, i1 } %v2, 1
  br i1 %v4, label %bb3, label %bb0
bb0:
  %v5 = call { i64, i1 } @llvm.uadd.with.overflow.i64(i64 %p1, i64 2)
  %v6 = extractvalue { i64, i1 } %v5, 0
  %v7 = extractvalue { i64, i1 } %v5, 1
  br i1 %v7, label %bb3, label %bb1
bb1:
  %v8 = icmp ult i64 %v6, %v1
  br i1 %v8, label %bb2, label %bb3
bb2:
  %v9 = getelementptr i8, ptr %v0, i64 %p1
  %v10 = load i8, ptr %v9
  %v11 = getelementptr i8, ptr %v0, i64 %v3
  %v12 = load i8, ptr %v11
  %v13 = getelementptr i8, ptr %v0, i64 %v6
  %v14 = load i8, ptr %v13
  %v15 = icmp eq i8 %v10, %p2
  %v16 = icmp eq i8 %v12, %p3
  %v17 = icmp eq i8 %v14, %p4
  %v18 = and i1 %v15, %v16
  %v19 = and i1 %v18, %v17
  ret i1 %v19
bb3:
  call void @llvm.trap()
  unreachable
}
"""

EXPECTED = EXPECTED_PRELUDE + EXPECTED_FUNCTION


def build_focused_library(directory):
    source = compiler_source()
    wired = {
        line.strip()
        for line in (HERE / "sources.txt").read_text().splitlines()
        if line.strip()
    }
    if "src/llvm_buffer.xl" not in wired:
        source += "\n" + (HERE / "src" / "llvm_buffer.xl").read_text()
    ir = democ.compile_program(source, alias=False)
    ll = directory / "llvm_buffer_compiler.ll"
    library_path = directory / (
        "llvm_buffer_compiler.dylib"
        if sys.platform == "darwin"
        else "llvm_buffer_compiler.so"
    )
    ll.write_text(ir)
    compile_shared(ll, library_path, optimize="-O2")
    return ctypes.CDLL(str(library_path))


def compile_shared(ll, library_path, optimize="-O3"):
    cc = "/usr/bin/clang" if Path("/usr/bin/clang").exists() else "clang"
    command = [cc, optimize]
    command += ["-dynamiclib"] if sys.platform == "darwin" else ["-shared", "-fPIC"]
    command += [str(ll), "-o", str(library_path)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f"clang rejected LLVM buffer IR:\n{result.stderr}")


def configure(library):
    configure_semantic_buffer(library)
    arguments = [
        Buffer,
        ctypes.POINTER(TokenTape),
        ctypes.POINTER(AstTape),
        ctypes.c_uint64,
        ctypes.POINTER(TypeTape),
        ctypes.POINTER(NodeFacts),
    ]
    library.llvm_buffer_match3_facts_valid.argtypes = arguments
    library.llvm_buffer_match3_facts_valid.restype = ctypes.c_bool
    library.llvm_buffer_emit_prelude.argtypes = [ctypes.POINTER(ByteTape)]
    library.llvm_buffer_emit_prelude.restype = None
    for name in ("llvm_buffer_emit_match3", "llvm_buffer_append_match3"):
        function = getattr(library, name)
        function.argtypes = arguments + [ctypes.POINTER(ByteTape)]
        function.restype = None


def analyzed(library):
    case = semantic_case(library)
    (function,) = children_of(case[4], case[5].root)
    outputs = make_buffer_outputs(library, case[5].count)
    report = invoke_run(library, case, function, outputs)
    assert (report.status, report.node, report.related) == (
        BODY_CLEAN,
        U64_MAX,
        U64_MAX,
    )
    valid = library.llvm_buffer_match3_facts_valid(
        case[1],
        ctypes.byref(case[3]),
        ctypes.byref(case[5]),
        function,
        ctypes.byref(outputs["types"]),
        ctypes.byref(outputs["facts"]),
    )
    assert valid
    return case, function, outputs


def call(library, analyzed_case, out, *, append=False):
    case, function, outputs = analyzed_case
    emitter = (
        library.llvm_buffer_append_match3
        if append
        else library.llvm_buffer_emit_match3
    )
    emitter(
        case[1],
        ctypes.byref(case[3]),
        ctypes.byref(case[5]),
        function,
        ctypes.byref(outputs["types"]),
        ctypes.byref(outputs["facts"]),
        ctypes.byref(out),
    )


def output_bytes(storage, out):
    return bytes(storage[: min(out.count, len(storage) - 1)])


def assert_output_modes(library, analyzed_case):
    measured_storage, measured = make_output(0)
    call(library, analyzed_case, measured)
    assert (measured.status, measured.count) == (
        BYTE_NEED_CAPACITY,
        len(EXPECTED),
    )
    assert measured_storage[0] == GUARD

    exact_storage, exact = make_output(len(EXPECTED))
    call(library, analyzed_case, exact)
    assert (exact.status, exact.count) == (BYTE_CLEAN, len(EXPECTED))
    assert output_bytes(exact_storage, exact) == EXPECTED
    assert exact_storage[len(EXPECTED)] == GUARD

    short_storage, short = make_output(len(EXPECTED) - 1)
    call(library, analyzed_case, short)
    assert (short.status, short.count) == (
        BYTE_NEED_CAPACITY,
        len(EXPECTED),
    )
    assert output_bytes(short_storage, short) == EXPECTED[:-1]
    assert short_storage[len(EXPECTED) - 1] == GUARD

    for index in range(len(EXPECTED)):
        exact_storage[index] = POISON
    exact.count = U64_MAX
    exact.status = BYTE_INVALID_STATE
    call(library, analyzed_case, exact)
    assert (exact.status, exact.count) == (BYTE_CLEAN, len(EXPECTED))
    assert output_bytes(exact_storage, exact) == EXPECTED
    assert exact_storage[len(EXPECTED)] == GUARD

    append_measured_storage, append_measured = make_output(0)
    call(library, analyzed_case, append_measured, append=True)
    assert (append_measured.status, append_measured.count) == (
        BYTE_NEED_CAPACITY,
        len(EXPECTED_FUNCTION),
    )
    assert append_measured_storage[0] == GUARD

    append_storage, append = make_output(len(EXPECTED_FUNCTION))
    call(library, analyzed_case, append, append=True)
    assert (append.status, append.count) == (
        BYTE_CLEAN,
        len(EXPECTED_FUNCTION),
    )
    assert output_bytes(append_storage, append) == EXPECTED_FUNCTION
    assert b"declare " not in output_bytes(append_storage, append)
    assert append_storage[len(EXPECTED_FUNCTION)] == GUARD

    composed_storage, composed = make_output(len(EXPECTED))
    library.llvm_buffer_emit_prelude(ctypes.byref(composed))
    assert (composed.status, composed.count) == (
        BYTE_CLEAN,
        len(EXPECTED_PRELUDE),
    )
    assert output_bytes(composed_storage, composed) == EXPECTED_PRELUDE
    call(library, analyzed_case, composed, append=True)
    assert (composed.status, composed.count) == (BYTE_CLEAN, len(EXPECTED))
    composed_bytes = output_bytes(composed_storage, composed)
    assert composed_bytes == EXPECTED
    assert composed_bytes.count(b"declare void @llvm.trap()") == 1
    assert composed_storage[len(EXPECTED)] == GUARD
    return output_bytes(exact_storage, exact), composed_bytes


def assert_ir_shape(analyzed_case):
    case, function, outputs = analyzed_case
    nodes = match3_nodes(case[4], function)
    facts = outputs["fact_storage"]
    assert [facts[2][node] for node in nodes["lets"]] == list(range(9))
    assert [facts[2][node] for node in nodes["values"]] == list(range(9))
    assert facts[2][nodes["return_value"]] == 9
    assert facts[2][nodes["return"]] == 9

    assert EXPECTED.startswith(
        b"declare { i64, i1 } @llvm.uadd.with.overflow.i64(i64, i64)\n"
    )
    assert (
        b"define i1 @lexer_match3({ ptr, i64 } %p0, i64 %p1, "
        b"i8 %p2, i8 %p3, i8 %p4) {\n"
    ) in EXPECTED
    assert EXPECTED.count(
        b"call { i64, i1 } @llvm.uadd.with.overflow.i64"
    ) == 2
    assert EXPECTED.count(b" = icmp ult i64 ") == 1
    assert EXPECTED.count(b" = getelementptr i8, ptr ") == 3
    assert b"getelementptr inbounds" not in EXPECTED
    assert EXPECTED.count(b" = load i8, ptr ") == 3
    assert EXPECTED.count(b" = icmp eq i8 ") == 3
    assert EXPECTED.count(b" = and i1 ") == 2
    assert EXPECTED.count(b"label %bb3") == 3
    assert EXPECTED.count(b"\nbb3:\n") == 1
    assert EXPECTED.count(b"call void @llvm.trap()") == 1
    assert b" alloca " not in EXPECTED
    assert b" store " not in EXPECTED
    assert b"%v20" not in EXPECTED


def assert_atomic_failure(library, analyzed_case, label):
    storage, out = make_output(len(PREFIX))
    for index, value in enumerate(PREFIX):
        storage[index] = value
    out.count = len(PREFIX)
    call(library, analyzed_case, out, append=True)
    assert (out.status, out.count) == (
        BYTE_INVALID_STATE,
        len(PREFIX),
    ), label
    assert bytes(storage[: len(PREFIX)]) == PREFIX, label
    assert storage[len(PREFIX)] == GUARD, label


def assert_atomic_emit_failure(library, analyzed_case, label):
    storage, out = make_output(len(EXPECTED))
    call(library, analyzed_case, out)
    assert (out.status, out.count) == (BYTE_INVALID_STATE, 0), label
    assert bytes(storage[: len(EXPECTED)]) == bytes([POISON]) * len(EXPECTED), label
    assert storage[len(EXPECTED)] == GUARD, label


def alternate(value):
    return 1 if int(value) == 0 else 0


def assert_every_fact_cell_is_checked(library, analyzed_case):
    case, _, outputs = analyzed_case
    first_column = outputs["fact_storage"][0]
    previous = first_column[case[5].root]
    first_column[case[5].root] = alternate(previous)
    assert_atomic_emit_failure(library, analyzed_case, "emit validates facts first")
    first_column[case[5].root] = previous

    for column, storage in enumerate(outputs["fact_storage"]):
        for node in range(case[5].count):
            previous = storage[node]
            storage[node] = alternate(previous)
            assert_atomic_failure(
                library,
                analyzed_case,
                f"fact column {column}, node {node}",
            )
            storage[node] = previous

    for column, storage in enumerate(outputs["type_storage"]):
        for row in range(4):
            previous = storage[row]
            storage[row] = alternate(previous)
            assert_atomic_failure(
                library,
                analyzed_case,
                f"type column {column}, row {row}",
            )
            storage[row] = previous

    mutations = (
        (outputs["facts"], "count", case[5].count - 1),
        (outputs["facts"], "status", 1),
        (outputs["facts"], "node", 0),
        (outputs["facts"], "related", 0),
        (outputs["types"], "count", 3),
        (outputs["types"], "status", 1),
        (outputs["types"], "node", 0),
        (outputs["types"], "related", 0),
    )
    for owner, field, replacement in mutations:
        previous = getattr(owner, field)
        setattr(owner, field, replacement)
        assert_atomic_failure(library, analyzed_case, f"{type(owner).__name__}.{field}")
        setattr(owner, field, previous)


def assert_hostile_ast_is_checked(library, analyzed_case):
    case, function, _ = analyzed_case
    nodes = match3_nodes(case[4], function)

    p1_value = nodes["values"][0]
    previous_kind = case[4][0][p1_value]
    case[4][0][p1_value] = case[4][0][nodes["return"]]
    assert_atomic_emit_failure(library, analyzed_case, "emit validates AST first")
    assert_atomic_failure(library, analyzed_case, "body kind")
    case[4][0][p1_value] = previous_kind

    p1_let = nodes["lets"][0]
    previous_next = case[4][6][p1_let]
    case[4][6][p1_let] = p1_let
    assert_atomic_failure(library, analyzed_case, "body sibling cycle")
    case[4][6][p1_let] = previous_next

    source_storage = case[0]
    source_bytes = bytes(source_storage)
    operation = source_bytes.index(b"iadd.trap")
    previous_byte = source_storage[operation]
    source_storage[operation] = ord("x")
    assert_atomic_failure(library, analyzed_case, "body spelling")
    source_storage[operation] = previous_byte

    original_function = analyzed_case[1]
    analyzed_case = (case, case[5].count, analyzed_case[2])
    assert_atomic_failure(library, analyzed_case, "function ordinal")
    assert original_function == function


def compile_emitted_ir(directory, ir):
    ll = directory / "lexer_match3.ll"
    library_path = directory / (
        "lexer_match3.dylib" if sys.platform == "darwin" else "lexer_match3.so"
    )
    ll.write_bytes(ir)
    compile_shared(ll, library_path)
    return library_path


def native_function(library_path):
    library = ctypes.CDLL(str(library_path))
    function = library.lexer_match3
    function.argtypes = [
        Buffer,
        ctypes.c_uint64,
        ctypes.c_uint8,
        ctypes.c_uint8,
        ctypes.c_uint8,
    ]
    function.restype = ctypes.c_bool
    return library, function


def invoke_native(function, payload, start, expected):
    storage = (ctypes.c_uint8 * len(payload))(*payload)
    source = Buffer(ctypes.cast(storage, ctypes.c_void_p), len(payload))
    result = function(source, start, *expected)
    return bool(result)


def assert_runtime_differential(library_path):
    native_library, function = native_function(library_path)
    rng = random.Random(0x584C414E47)
    calls = 0
    for size in range(3, 65):
        payload = bytes(
            ((index * 73 + size * 29) ^ (index >> 1)) & 0xFF
            for index in range(size)
        )
        for start in range(size - 2):
            exact = tuple(payload[start : start + 3])
            candidates = (
                exact,
                (exact[0] ^ 1, exact[1], exact[2]),
                (exact[0], exact[1] ^ 1, exact[2]),
                (exact[0], exact[1], exact[2] ^ 1),
                tuple(rng.randrange(256) for _ in range(3)),
            )
            for candidate in candidates:
                observed = invoke_native(function, payload, start, candidate)
                expected = payload[start : start + 3] == bytes(candidate)
                assert observed == expected, (size, start, candidate)
                calls += 1
    assert calls > 9000
    assert native_library


TRAP_SCRIPT = r"""
import ctypes
import sys

class Buffer(ctypes.Structure):
    _fields_ = [("data", ctypes.c_void_p), ("length", ctypes.c_uint64)]

library = ctypes.CDLL(sys.argv[1])
function = library.lexer_match3
function.argtypes = [
    Buffer,
    ctypes.c_uint64,
    ctypes.c_uint8,
    ctypes.c_uint8,
    ctypes.c_uint8,
]
function.restype = ctypes.c_bool
size = int(sys.argv[2])
start = int(sys.argv[3])
storage = (ctypes.c_uint8 * max(size, 1))()
source = Buffer(ctypes.cast(storage, ctypes.c_void_p), size)
function(source, start, 0, 0, 0)
"""


def trap_process(library_path, size, start):
    return subprocess.run(
        [sys.executable, "-c", TRAP_SCRIPT, str(library_path), str(size), str(start)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
    )


def assert_runtime_traps(library_path):
    assert trap_process(library_path, 3, 0).returncode == 0
    trap_signal = signal.SIGTRAP if sys.platform == "darwin" else signal.SIGILL
    expected_returncode = -int(trap_signal)
    for size, start in (
        (0, 0),
        (1, 0),
        (2, 0),
        (3, 1),
        (3, U64_MAX - 1),
        (3, U64_MAX),
    ):
        result = trap_process(library_path, size, start)
        assert result.returncode == expected_returncode, (
            size,
            start,
            result.returncode,
            expected_returncode,
        )


def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        directory = Path(raw_directory)
        library = build_focused_library(directory)
        configure(library)
        analyzed_case = analyzed(library)
        emitted, composed = assert_output_modes(library, analyzed_case)
        assert emitted == composed
        assert_ir_shape(analyzed_case)
        assert_every_fact_cell_is_checked(library, analyzed_case)
        assert_hostile_ast_is_checked(library, analyzed_case)
        native_path = compile_emitted_ir(directory, composed)
        assert_runtime_differential(native_path)
        assert_runtime_traps(native_path)
    print(
        "llvm buffer: composable checked SSA, exact emit/function-only append, "
        "108x8 fact-cell rejection, clang/runtime differential, and traps pass"
    )


if __name__ == "__main__":
    main()
