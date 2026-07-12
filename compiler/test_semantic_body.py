#!/usr/bin/env python3
"""Type and resolve the first scalar self-hosted function body."""

import ctypes
import tempfile
from pathlib import Path

from test_ast_validate import AstValidationReport, validate
from test_lexer import Buffer, TokenTape, build_library, compiler_source
from test_parser import AST_NONE, AstTape, children_of, parse
from test_parser_expressions import enum_ordinals
from test_semantic_facts import (
    NODE_COLUMNS,
    TYPE_COLUMNS,
    NodeFacts,
    TypeTape,
    assert_guards,
    make_tape,
    snapshot,
)
from test_semantic_globals import SemanticGlobalsReport
from test_symbols import (
    SYMBOL_CLEAN,
    SYMBOL_NONE,
    SYMBOL_VALUE,
    SymbolTape,
    find,
    make_symbols,
    reset,
)


AST = enum_ordinals("AstKind")
U64_MAX = (1 << 64) - 1
U64_POISON = 0x7777777777777777
U64_GUARD = 0x8888888888888888
ENUM_POISON = 0x55555555
ENUM_GUARD = 0x66666666

BODY_CLEAN = 0
BODY_INVALID_TOKEN_TAPE = 1
BODY_INVALID_AST_TAPE = 2
BODY_INVALID_VALIDATION = 3
BODY_INVALID_FUNCTION = 4
BODY_INVALID_TYPE_TAPE = 5
BODY_INVALID_NODE_FACTS = 6
BODY_INVALID_SCRATCH = 7
BODY_CAPACITY = 8
BODY_MALFORMED = 9
BODY_UNSUPPORTED = 10
BODY_UNKNOWN_NAME = 11
BODY_TYPE_MISMATCH = 12
BODY_INVALID_LITERAL = 13

FACTS_CLEAN = 0
FACTS_INVALID_SHAPE = 1
FACTS_CAPACITY = 2
TYPE_U8 = 2
TYPE_BOOL = 4
MODE_NONE = 0
MODE_OWN = 1
OP_NONE = 0
OP_ILE = 7
OP_IGE = 9
OP_BAND = 10
PRELUDE_TYPE_UNKNOWN = 0
PRELUDE_TYPE_BOOL = 1


class SemanticBodyScratch(ctypes.Structure):
    _fields_ = [
        ("name_tokens", Buffer),
        ("declarations", Buffer),
        ("type_ids", Buffer),
        ("modes", Buffer),
        ("count", ctypes.c_uint64),
    ]


class SemanticBodyReport(ctypes.Structure):
    _fields_ = [
        ("status", ctypes.c_int32),
        ("node", ctypes.c_uint64),
        ("related", ctypes.c_uint64),
    ]


SCRATCH_COLUMNS = (
    (ctypes.c_uint64, U64_POISON, U64_GUARD),
    (ctypes.c_uint64, U64_POISON, U64_GUARD),
    (ctypes.c_uint64, U64_POISON, U64_GUARD),
    (ctypes.c_int32, ENUM_POISON, ENUM_GUARD),
)


def fixture(
    parameter=b"c",
    first_operand=b"c",
    first_literal=b"97_u8",
    first_binding_type=b"Bool",
    return_op=b"band",
    first_binding=b"ge",
    second_binding=b"le",
):
    return (
        b"fn lexer_is_lower ("
        + parameter
        + b": own u8) -> own Bool pure {\n"
        b"  let "
        + first_binding
        + b": own "
        + first_binding_type
        + b" = ige<u8>("
        + first_operand
        + b", "
        + first_literal
        + b");\n"
        b"  let "
        + second_binding
        + b": own Bool = ile<u8>("
        + parameter
        + b", 122_u8);\n"
        b"  return "
        + return_op
        + b"<Bool>("
        + first_binding
        + b", "
        + second_binding
        + b");\n"
        b"}\n"
    )


def configure(library):
    library.semantic_body_run.argtypes = [
        Buffer,
        ctypes.POINTER(TokenTape),
        ctypes.POINTER(AstTape),
        ctypes.c_uint64,
        ctypes.POINTER(AstValidationReport),
        ctypes.POINTER(TypeTape),
        ctypes.POINTER(NodeFacts),
        ctypes.POINTER(SemanticBodyScratch),
        ctypes.POINTER(SemanticBodyReport),
    ]
    library.semantic_body_run.restype = None
    library.semantic_type_tape_reset.argtypes = [ctypes.POINTER(TypeTape)]
    library.semantic_type_tape_reset.restype = None
    library.semantic_node_facts_reset.argtypes = [ctypes.POINTER(NodeFacts)]
    library.semantic_node_facts_reset.restype = None
    library.semantic_index_globals.argtypes = [
        Buffer,
        ctypes.POINTER(TokenTape),
        ctypes.POINTER(AstTape),
        ctypes.POINTER(SymbolTape),
        ctypes.POINTER(SemanticGlobalsReport),
    ]
    library.semantic_index_globals.restype = None
    library.symbol_tape_reset.argtypes = [ctypes.POINTER(SymbolTape)]
    library.symbol_tape_reset.restype = None
    library.symbol_find_in_scope.argtypes = [
        Buffer,
        ctypes.POINTER(TokenTape),
        ctypes.POINTER(SymbolTape),
        ctypes.c_int32,
        ctypes.c_uint64,
        ctypes.c_uint64,
    ]
    library.symbol_find_in_scope.restype = None


def make_scratch(capacities):
    storage = []
    buffers = []
    for (ctype, poison, guard), capacity in zip(SCRATCH_COLUMNS, capacities):
        column = (ctype * (capacity + 1))()
        for slot in range(capacity):
            column[slot] = poison
        column[capacity] = guard
        storage.append(column)
        buffers.append(Buffer(ctypes.cast(column, ctypes.c_void_p), capacity))
    return tuple(storage), tuple(capacities), SemanticBodyScratch(*buffers, 0)


def assert_scratch_guards(storage, capacities):
    for column, (_, _, guard), capacity in zip(
        storage, SCRATCH_COLUMNS, capacities
    ):
        assert column[capacity] == guard


def source_buffer(storage, length):
    return Buffer(ctypes.cast(storage, ctypes.c_void_p), length)


def parsed(library, data):
    source_storage, token_storage, tokens, columns, ast = parse(library, data)
    assert ast.status == 0
    validation = validate(library, len(data), tokens.count, ast)
    assert validation.status == 0
    source = source_buffer(source_storage, len(data))
    return (
        source_storage,
        source,
        token_storage,
        tokens,
        columns,
        ast,
        validation,
    )


def find_function_by_text(data, columns, ast, text):
    kinds, _, starts, ends, _, _, _ = columns
    matches = [
        node
        for node in children_of(columns, ast.root)
        if kinds[node] == AST["AstFunction"]
        and any(
            kinds[child] == AST["AstFunctionName"]
            and data[starts[child] : ends[child]] == text
            for child in children_of(columns, node)
        )
    ]
    assert len(matches) == 1, (text, matches)
    return matches[0]


def make_outputs(library, ast_count, type_caps=None, fact_caps=None, scratch_caps=None):
    if type_caps is None:
        type_caps = (2,) * len(TYPE_COLUMNS)
    if fact_caps is None:
        fact_caps = (ast_count,) * len(NODE_COLUMNS)
    if scratch_caps is None:
        scratch_caps = (3,) * len(SCRATCH_COLUMNS)
    type_storage, types = make_tape(TypeTape, TYPE_COLUMNS, type_caps)
    fact_storage, facts = make_tape(NodeFacts, NODE_COLUMNS, fact_caps)
    library.semantic_type_tape_reset(ctypes.byref(types))
    library.semantic_node_facts_reset(ctypes.byref(facts))
    scratch_storage, scratch_physical, scratch = make_scratch(scratch_caps)
    return (
        type_storage,
        types,
        fact_storage,
        facts,
        scratch_storage,
        scratch_physical,
        scratch,
        type_caps,
        fact_caps,
    )


def invoke(library, parsed_case, function, outputs):
    _, source, _, tokens, _, ast, validation = parsed_case
    (
        _,
        types,
        _,
        facts,
        _,
        _,
        scratch,
        _,
        _,
    ) = outputs
    report = SemanticBodyReport(99, 123, 456)
    library.semantic_body_run(
        source,
        ctypes.byref(tokens),
        ctypes.byref(ast),
        function,
        ctypes.byref(validation),
        ctypes.byref(types),
        ctypes.byref(facts),
        ctypes.byref(scratch),
        ctypes.byref(report),
    )
    return report


def assert_output_guards(outputs):
    (
        type_storage,
        _,
        fact_storage,
        _,
        scratch_storage,
        scratch_physical,
        _,
        type_caps,
        fact_caps,
    ) = outputs
    assert_guards(type_storage, TYPE_COLUMNS, type_caps)
    assert_guards(fact_storage, NODE_COLUMNS, fact_caps)
    assert_scratch_guards(scratch_storage, scratch_physical)


def output_snapshot(outputs):
    (
        type_storage,
        types,
        fact_storage,
        facts,
        scratch_storage,
        scratch_physical,
        scratch,
        type_caps,
        fact_caps,
    ) = outputs
    return (
        snapshot(type_storage, type_caps),
        (types.count, types.status, types.node, types.related),
        snapshot(fact_storage, fact_caps),
        (facts.count, facts.status, facts.node, facts.related),
        tuple(
            tuple(column[:capacity])
            for column, capacity in zip(scratch_storage, scratch_physical)
        ),
        scratch.count,
    )


def report_tuple(report):
    return (report.status, report.node, report.related)


def body_nodes(columns, function):
    direct = children_of(columns, function)
    assert len(direct) == 6
    parameter = direct[1]
    block = direct[5]
    statements = children_of(columns, block)
    assert len(statements) == 3
    first_let, second_let, return_node = statements
    first_call = children_of(columns, first_let)[3]
    second_call = children_of(columns, second_let)[3]
    return_call = children_of(columns, return_node)[0]
    first_call_children = children_of(columns, first_call)
    second_call_children = children_of(columns, second_call)
    return_call_children = children_of(columns, return_call)
    return {
        "parameter": parameter,
        "parameter_mode": children_of(columns, parameter)[0],
        "parameter_type": children_of(columns, parameter)[1],
        "return_mode": direct[2],
        "return_type": direct[3],
        "first_let": first_let,
        "second_let": second_let,
        "return": return_node,
        "first_call": first_call,
        "second_call": second_call,
        "return_call": return_call,
        "first_type_arg": first_call_children[0],
        "second_type_arg": second_call_children[0],
        "return_type_arg": return_call_children[0],
        "first_c": first_call_children[1],
        "first_literal": first_call_children[2],
        "second_c": second_call_children[1],
        "second_literal": second_call_children[2],
        "ge_use": return_call_children[1],
        "le_use": return_call_children[2],
    }


def assert_clean_facts(library):
    data = fixture()
    case = parsed(library, data)
    function = find_function_by_text(data, case[4], case[5], b"lexer_is_lower")
    first = make_outputs(library, case[5].count)
    first_report = invoke(library, case, function, first)
    assert (first_report.status, first_report.node, first_report.related) == (
        BODY_CLEAN,
        U64_MAX,
        U64_MAX,
    )
    assert_output_guards(first)

    type_storage, types, fact_storage, facts, _, _, scratch, _, _ = first
    assert (types.count, types.status, types.node, types.related) == (
        2,
        FACTS_CLEAN,
        U64_MAX,
        U64_MAX,
    )
    assert list(type_storage[0][:2]) == [TYPE_U8, TYPE_BOOL]
    assert list(type_storage[1][:2]) == [U64_MAX, U64_MAX]
    assert list(type_storage[2][:2]) == [U64_MAX, U64_MAX]
    assert list(type_storage[3][:2]) == [U64_MAX, U64_MAX]
    assert list(type_storage[4][:2]) == [U64_MAX, U64_MAX]
    assert list(type_storage[5][:2]) == [PRELUDE_TYPE_UNKNOWN, PRELUDE_TYPE_BOOL]
    assert (facts.count, facts.status, facts.node, facts.related) == (
        case[5].count,
        FACTS_CLEAN,
        U64_MAX,
        U64_MAX,
    )
    assert scratch.count == 3

    nodes = body_nodes(case[4], function)
    type_ids = fact_storage[0]
    resolved = fact_storage[1]
    ordinals = fact_storage[2]
    operations = fact_storage[3]
    constants = fact_storage[4]
    modes = fact_storage[6]
    assert (type_ids[nodes["parameter"]], ordinals[nodes["parameter"]], modes[nodes["parameter"]]) == (0, 0, MODE_OWN)
    assert (type_ids[nodes["first_let"]], ordinals[nodes["first_let"]], modes[nodes["first_let"]]) == (1, 0, MODE_OWN)
    assert (type_ids[nodes["second_let"]], ordinals[nodes["second_let"]], modes[nodes["second_let"]]) == (1, 1, MODE_OWN)
    assert operations[nodes["first_call"]] == OP_IGE
    assert operations[nodes["second_call"]] == OP_ILE
    assert operations[nodes["return_call"]] == OP_BAND
    assert constants[nodes["first_literal"]] == 97
    assert constants[nodes["second_literal"]] == 122
    assert resolved[nodes["first_c"]] == nodes["parameter"]
    assert resolved[nodes["second_c"]] == nodes["parameter"]
    assert resolved[nodes["ge_use"]] == nodes["first_let"]
    assert resolved[nodes["le_use"]] == nodes["second_let"]
    for name in ("first_call", "second_call", "return_call", "first_let", "second_let", "return"):
        assert type_ids[nodes[name]] == 1
        assert modes[nodes[name]] == MODE_OWN
    for name in ("first_literal", "second_literal", "first_c", "second_c"):
        assert type_ids[nodes[name]] == 0
        assert modes[nodes[name]] == MODE_OWN
    for name in ("ge_use", "le_use"):
        assert type_ids[nodes[name]] == 1
        assert modes[nodes[name]] == MODE_OWN
    for name in ("parameter_type", "first_type_arg", "second_type_arg"):
        assert type_ids[nodes[name]] == 0
    for name in ("return_type", "return_type_arg"):
        assert type_ids[nodes[name]] == 1

    second = make_outputs(library, case[5].count)
    second_report = invoke(library, case, function, second)
    assert report_tuple(first_report) == report_tuple(second_report)
    assert output_snapshot(first) == output_snapshot(second)
    assert_output_guards(second)
    assert case[0]
    return case[5].count


def assert_semantic_failures(library):
    cases = (
        (fixture(first_operand=b"missing"), BODY_UNKNOWN_NAME),
        (fixture(first_binding_type=b"u8"), BODY_TYPE_MISMATCH),
        (fixture(return_op=b"bor"), BODY_UNSUPPORTED),
        (fixture(first_literal=b"097_u8"), BODY_INVALID_LITERAL),
        (fixture(first_binding=b"c"), BODY_MALFORMED),
        (fixture(second_binding=b"ge"), BODY_MALFORMED),
    )
    for data, expected in cases:
        parsed_case = parsed(library, data)
        function = find_function_by_text(
            data, parsed_case[4], parsed_case[5], b"lexer_is_lower"
        )
        outputs = make_outputs(library, parsed_case[5].count)
        report = invoke(library, parsed_case, function, outputs)
        assert report.status == expected, (data, report.status, expected)
        assert report.node != U64_MAX
        assert outputs[1].status == FACTS_INVALID_SHAPE
        assert outputs[3].status == FACTS_INVALID_SHAPE
        assert_output_guards(outputs)

    poison_data = fixture(first_operand=b"missing")
    poison_case = parsed(library, poison_data)
    poison_function = find_function_by_text(
        poison_data, poison_case[4], poison_case[5], b"lexer_is_lower"
    )
    poison_results = []
    for poison in (0x1234, 0xABCDEF):
        poison_outputs = make_outputs(library, poison_case[5].count)
        for tape in (poison_outputs[1], poison_outputs[3]):
            tape.status = 99
            tape.node = poison
            tape.related = poison + 1
        poison_report = invoke(
            library, poison_case, poison_function, poison_outputs
        )
        poison_results.append(
            (
                report_tuple(poison_report),
                (
                    poison_outputs[1].status,
                    poison_outputs[1].node,
                    poison_outputs[1].related,
                ),
                (
                    poison_outputs[3].status,
                    poison_outputs[3].node,
                    poison_outputs[3].related,
                ),
            )
        )
        assert_output_guards(poison_outputs)
    assert poison_results[0] == poison_results[1]


def assert_capacity_and_input_guards(library):
    data = fixture()
    case = parsed(library, data)
    function = find_function_by_text(data, case[4], case[5], b"lexer_is_lower")

    for short in range(len(TYPE_COLUMNS)):
        capacities = [2] * len(TYPE_COLUMNS)
        capacities[short] = 1
        outputs = make_outputs(library, case[5].count, type_caps=tuple(capacities))
        report = invoke(library, case, function, outputs)
        assert report.status == BODY_CAPACITY, ("type", short, report.status)
        assert outputs[1].count == 0
        assert outputs[1].status == FACTS_CAPACITY
        assert_output_guards(outputs)

    for short in range(len(NODE_COLUMNS)):
        capacities = [case[5].count] * len(NODE_COLUMNS)
        capacities[short] -= 1
        outputs = make_outputs(library, case[5].count, fact_caps=tuple(capacities))
        report = invoke(library, case, function, outputs)
        assert report.status == BODY_CAPACITY, ("fact", short, report.status)
        assert outputs[3].count == 0
        assert outputs[3].status == FACTS_CAPACITY
        assert_output_guards(outputs)

    for short in range(len(SCRATCH_COLUMNS)):
        capacities = [3] * len(SCRATCH_COLUMNS)
        capacities[short] = 2
        outputs = make_outputs(library, case[5].count, scratch_caps=tuple(capacities))
        report = invoke(library, case, function, outputs)
        assert report.status == BODY_CAPACITY, ("scratch", short, report.status)
        assert outputs[1].count == 0
        assert outputs[3].count == 0
        assert_output_guards(outputs)

    outputs = make_outputs(library, case[5].count)
    report = invoke(library, case, case[5].count, outputs)
    assert report.status == BODY_INVALID_FUNCTION
    assert_output_guards(outputs)

    outputs = make_outputs(library, case[5].count)
    case[6].status = 1
    report = invoke(library, case, function, outputs)
    assert report.status == BODY_INVALID_VALIDATION
    case[6].status = 0
    assert_output_guards(outputs)

    outputs = make_outputs(library, case[5].count)
    case[3].kinds.length = case[3].count - 1
    report = invoke(library, case, function, outputs)
    assert report.status == BODY_INVALID_TOKEN_TAPE
    case[3].kinds.length += 1
    assert_output_guards(outputs)

    outputs = make_outputs(library, case[5].count)
    outputs[1].count = 1
    report = invoke(library, case, function, outputs)
    assert report.status == BODY_INVALID_TYPE_TAPE
    assert_output_guards(outputs)

    outputs = make_outputs(library, case[5].count)
    outputs[3].count = 1
    report = invoke(library, case, function, outputs)
    assert report.status == BODY_INVALID_NODE_FACTS
    assert_output_guards(outputs)

    outputs = make_outputs(library, case[5].count)
    outputs[6].count = 4
    report = invoke(library, case, function, outputs)
    assert report.status == BODY_INVALID_SCRATCH
    assert_output_guards(outputs)

    outputs = make_outputs(library, case[5].count)
    original_first = case[4][4][function]
    case[4][4][function] = case[5].count
    report = invoke(library, case, function, outputs)
    assert report.status == BODY_INVALID_FUNCTION
    case[4][4][function] = original_first
    assert_output_guards(outputs)

    outputs = make_outputs(library, case[5].count)
    return_node = body_nodes(case[4], function)["return"]
    original_return_next = case[4][6][return_node]
    case[4][6][return_node] = return_node
    report = invoke(library, case, function, outputs)
    assert report.status == BODY_MALFORMED
    assert report.node == return_node
    case[4][6][return_node] = original_return_next
    assert_output_guards(outputs)


def global_lookup_function(library, data, parsed_case, name):
    _, source, token_storage, tokens, _, ast, _ = parsed_case
    top_level_count = len(children_of(parsed_case[4], ast.root))
    symbol_storage, symbol_physical, symbols = make_symbols(
        (top_level_count,) * 4
    )
    reset(library, symbols)
    globals_report = SemanticGlobalsReport(99, 99, 99)
    library.semantic_index_globals(
        source,
        ctypes.byref(tokens),
        ctypes.byref(ast),
        ctypes.byref(symbols),
        ctypes.byref(globals_report),
    )
    assert globals_report.status == 0
    _, starts, ends = token_storage
    candidates = [
        token
        for token in range(tokens.count)
        if data[starts[token] : ends[token]] == name
    ]
    assert candidates
    found = None
    for token in candidates:
        status, slot = find(
            library,
            source,
            tokens,
            symbols,
            SYMBOL_VALUE,
            SYMBOL_NONE,
            token,
        )
        if status == SYMBOL_CLEAN:
            found = symbol_storage[3][slot]
            break
    assert found is not None
    assert symbol_storage[3][slot] == found
    assert symbol_storage[0][symbol_physical] != 0
    return found


def assert_current_compiler(library):
    data = compiler_source().encode("ascii")
    case = parsed(library, data)
    function = global_lookup_function(library, data, case, b"lexer_is_lower")
    assert case[4][0][function] == AST["AstFunction"]
    outputs = make_outputs(library, case[5].count)
    report = invoke(library, case, function, outputs)
    assert (report.status, report.node, report.related) == (
        BODY_CLEAN,
        U64_MAX,
        U64_MAX,
    )
    nodes = body_nodes(case[4], function)
    assert outputs[2][3][nodes["first_call"]] == OP_IGE
    assert outputs[2][3][nodes["second_call"]] == OP_ILE
    assert outputs[2][3][nodes["return_call"]] == OP_BAND
    assert outputs[2][4][nodes["first_literal"]] == 97
    assert outputs[2][4][nodes["second_literal"]] == 122
    assert_output_guards(outputs)
    return (case[3].count, case[5].count)


def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))
        configure(library)
        focused_nodes = assert_clean_facts(library)
        assert_semantic_failures(library)
        assert_capacity_and_input_guards(library)
        compiler_counts = assert_current_compiler(library)
        print(
            "semantic body: lexer_is_lower typed/resolved deterministically; "
            f"focused nodes={focused_nodes}; compiler tokens/nodes={compiler_counts}; "
            "hostile names/types/ops/literals/capacities fail closed"
        )


if __name__ == "__main__":
    main()
