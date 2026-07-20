#!/usr/bin/env python3
"""Focused correctness gates for stage-0 aggregate code generation."""

import subprocess
import tempfile
from pathlib import Path

import democ


CLANG = "/usr/bin/clang" if Path("/usr/bin/clang").exists() else "clang"
ROOT = Path(__file__).resolve().parents[2]


def compile_native(source, run=False):
    ir = democ.compile_program(source, alias=False)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        ll = root / "program.ll"
        output = root / ("program" if run else "program.o")
        ll.write_text(ir)
        command = [CLANG, "-O2", str(ll), "-o", str(output)]
        if not run:
            command.insert(2, "-c")
        built = subprocess.run(command, capture_output=True, text=True)
        assert built.returncode == 0, built.stderr
        if run:
            executed = subprocess.run([str(output)], capture_output=True)
            assert executed.returncode == 0, executed.returncode
    return ir


recursive_projection = (
    ROOT / "conformance" / "cases" / "gram5-pos-recursive-place-projection.wf"
).read_text()
_, _, projection_functions, _, _, _ = democ.parse_program(recursive_projection)
projection_reader = next(
    function
    for function in projection_functions
    if function["name"] == "read_projection"
)
projection_place = projection_reader["body"][0]["e"]["p"]
assert projection_place["post"] == ["inner", "value"]
projection_ir = compile_native(recursive_projection, run=True)
assert "getelementptr %OuterProjection" in projection_ir
assert "getelementptr %InnerProjection" in projection_ir


local_result = """fn main () -> own unit traps {
  let result: own Result<u64,u64> = match True() {
    True() => {
      give Ok(value: 7_u64);
    }
    False() => {
      give Err(error: 9_u64);
    }
  }
  match move result {
    Ok(value: value) => {
      check ieq<u64>(value, 7_u64) else trap "wrong local Result";
    }
    Err(error: error) => {
      check ieq<u64>(0_u64, 1_u64) else trap "unexpected Err";
    }
  }
  return unit;
}
"""
local_ir = compile_native(local_result, run=True)
assert "%Result = type { i32, i64 }" in local_ir


local_option = """fn main () -> own unit pure {
  let option: own Option<u64> = match True() {
    True() => {
      give Some(value: 7_u64);
    }
    False() => {
      give None();
    }
  }
  match move option {
    None() => {
    }
    Some(value: value) => {
    }
  }
  return unit;
}
"""
option_ir = compile_native(local_option, run=True)
assert "%Option = type { i32, i64 }" in option_ir


terminating_buffer = """fn choose_buffer (flag: own Bool) -> own buffer<u8> allocates(heap), traps {
  let unreachable: own buffer<u8> = match flag {
    True() => {
      let left: own buffer<u8> = buffer_new<u8>(1_u64, 1_u8);
      return move left;
    }
    False() => {
      let right: own buffer<u8> = buffer_new<u8>(1_u64, 2_u8);
      return move right;
    }
  }
  return move unreachable;
}

fn main () -> own unit allocates(heap), traps {
  let flag: own Bool = True();
  let value: own buffer<u8> = choose_buffer(flag: flag);
  let size: own u64 = len<u8>(value);
  check ieq<u64>(size, 1_u64) else trap "wrong buffer";
  return unit;
}
"""
compile_native(terminating_buffer, run=True)


nested_field_borrow = """struct Inner {
  value: u64;
}

struct Outer {
  inner: Inner;
  values: buffer<u64>;
}

fn increment ['i] (inner: &uniq 'i Inner) -> own unit reads('i), writes('i), traps {
  let before: own u64 = deref(inner).value;
  set deref(inner).value = iadd.trap<u64>(before, 1_u64);
  return unit;
}

fn write_first ['v] (values: &uniq 'v buffer<u64>) -> own unit reads('v), writes('v), traps {
  set index<u64>(deref(values), 0_u64) = 9_u64;
  return unit;
}

fn route ['o] (outer: &uniq 'o Outer) -> own unit reads('o), writes('o), traps {
  region 'inner_field {
    increment<'inner_field>(inner: &uniq 'inner_field deref(outer).inner);
  }
  region 'buffer_field {
    write_first<'buffer_field>(values: &uniq 'buffer_field deref(outer).values);
  }
  return unit;
}

fn main () -> own unit allocates(heap), traps {
  let inner: own Inner = Inner(value: 6_u64);
  let values: own buffer<u64> = buffer_new<u64>(1_u64, 0_u64);
  let outer: own Outer = Outer(inner: move inner, values: move values);
  region 'outer_borrow {
    route<'outer_borrow>(outer: &uniq 'outer_borrow outer);
  }
  check ieq<u64>(outer.inner.value, 7_u64) else trap "nested field borrow used the root pointer";
  let first: own u64 = index<u64>(outer.values, 0_u64);
  check ieq<u64>(first, 9_u64) else trap "buffer field borrow lost its checked header";
  return unit;
}
"""
nested_field_ir = compile_native(nested_field_borrow, run=True)
assert "getelementptr %Outer" in nested_field_ir
legacy_nested_field_borrow = (
    nested_field_borrow
    .replace("increment<'inner_field>", "increment")
    .replace("write_first<'buffer_field>", "write_first")
    .replace("route<'outer_borrow>", "route")
)
assert democ.compile_program(legacy_nested_field_borrow, alias=False) == nested_field_ir


region_argument_ast = """fn target ['first, 'second] () -> own unit pure {
  return unit;
}

fn caller ['outer] () -> own unit pure {
  region 'inner {
    target<'outer, 'inner>();
    target();
  }
  return unit;
}
"""
ast_parts = democ.parse_program(region_argument_ast)
raw_caller = next(function for function in ast_parts[2] if function["name"] == "caller")
raw_calls = [statement["e"] for statement in raw_caller["body"][0]["body"]]
assert raw_calls[0]["region_args"] == ["outer", "inner"]
assert raw_calls[1]["region_args"] is None
mapped_caller = democ.build_prog(ast_parts[0], ast_parts[1], ast_parts[2], ast_parts[5])["fns"]["caller"]
mapped_calls = [statement["expr"] for statement in mapped_caller["body"][0]["body"]]
assert mapped_calls[0]["region_args"] == ["outer", "inner"]
assert mapped_calls[1]["region_args"] is None

literal_index_ast = """fn probe ['r] (items: &'r buffer<u8>) -> own unit reads('r), traps {
  let item: &'r u8 = &'r index<u8>(deref(items), 3_u64);
  return unit;
}
"""
literal_parts = democ.parse_program(literal_index_ast)
literal_probe = democ.build_prog(
    literal_parts[0], literal_parts[1], literal_parts[2], literal_parts[5]
)["fns"]["probe"]
literal_atom = literal_probe["body"][0]["init"]["place"]["atom"]
assert literal_atom["kind"] == "lit"
assert literal_atom["value"] == 3
assert literal_atom["ty"] == {"kind": "prim", "name": "u64"}

table_call_precedence = """fn probe ['r] (value: own u64) -> own unit pure {
  arena_new<'r, u64>(value);
  len<u64>(value);
  return unit;
}
"""
table_parts = democ.parse_program(table_call_precedence)
table_body = table_parts[2][0]["body"]
assert table_body[0]["e"] == {
    "e": "op", "op": "arena_new", "args": [{"e": "place", "p": {
        "base": "value", "path": [], "deref": 0}}], "tyargs": ["'r", "u64"]}
assert table_body[1]["e"]["e"] == "op"
assert table_body[1]["e"]["op"] == "len"


def expect_rule(source, rule):
    try:
        democ.parse_program(source)
    except democ.CheckError as error:
        assert error.rule == rule, error
    else:
        raise AssertionError(f"malformed call syntax parsed without {rule}")


def expect_stage0_unsupported(source):
    message = ("democ: user-call type/const/mixed targs are outside the "
               "stage-0 profile; only explicit REGIONID arguments are supported")
    try:
        democ.parse_program(source)
    except SystemExit as error:
        assert str(error) == message, error
    except democ.CheckError as error:
        raise AssertionError(
            f"stage-0 profile boundary was misreported as language rule {error.rule}") from error
    else:
        raise AssertionError("mixed user-call targs crossed the stage-0 profile boundary")


expect_rule("""fn bad [scope] () -> own unit pure {
  return unit;
}
""", "FORM-3")
expect_rule("""fn bad () -> own unit pure {
  region scope {
  }
  return unit;
}
""", "FORM-3")
expect_rule("""fn bad (value: & scope u64) -> own unit pure {
  return unit;
}
""", "FORM-3")
expect_rule("""fn bad () -> own unit pure {
  let value: own u64 = 1_u64;
  region 'scope {
    let borrowed: & 'scope u64 = & scope value;
  }
  return unit;
}
""", "FORM-3")
expect_rule("""fn target ['first, 'second] () -> own unit pure {
  return unit;
}

fn bad () -> own unit pure {
  target<>();
  return unit;
}
""", "GRAM-5")
expect_rule("""fn target ['first, 'second] () -> own unit pure {
  return unit;
}

fn bad ['outer] () -> own unit pure {
  target<'outer,>();
  return unit;
}
""", "GRAM-5")
expect_rule("""fn target ['first, 'second] () -> own unit pure {
  return unit;
}

fn bad ['outer, 'inner] () -> own unit pure {
  target<'outer 'inner>();
  return unit;
}
""", "GRAM-5")
expect_rule("""fn target ['outer] () -> own unit pure {
  return unit;
}

fn bad ['outer] () -> own unit pure {
  target<'outer();
  return unit;
}
""", "GRAM-5")
expect_rule("""fn target ['outer] () -> own unit pure {
  return unit;
}

fn bad ['outer] () -> own unit pure {
  target<'outer>;
  return unit;
}
""", "GRAM-5")
expect_rule("""fn target ['outer] (value: own u64) -> own unit pure {
  return unit;
}

fn bad () -> own unit pure {
  let value: own u64 = 1_u64;
  target<'outer,
""", "GRAM-5")
expect_rule("""fn bad ['outer] () -> own unit pure {
  target<'outer,,
""", "GRAM-5")
expect_rule("""fn bad () -> own unit pure {
  target<
""", "GRAM-5")
expect_rule("""fn target ['outer] (value: own u64) -> own unit pure {
  return unit;
}

fn bad ['outer] (value: own u64) -> own unit pure {
  target<'outer>(value: value
""", "GRAM-11")
expect_rule("""fn target ['outer] (value: own u64) -> own unit pure {
  return unit;
}

fn bad ['outer] (value: own u64) -> own unit pure {
  target<'outer>(value: value,);
  return unit;
}
""", "GRAM-11")
expect_rule("""fn target ['outer] (value: own u64) -> own unit pure {
  return unit;
}

fn bad ['outer] (value: own u64) -> own unit pure {
  target<'outer>(value: value extra: value);
  return unit;
}
""", "GRAM-11")
expect_stage0_unsupported("""fn target ['outer] () -> own unit pure {
  return unit;
}

fn bad () -> own unit pure {
  target<outer>();
  return unit;
}
""")


aggregate_payloads = [
    """struct Pair {
  value: u64;
}

fn make () -> own Result<Pair,u64> pure {
  let pair: own Pair = Pair(value: 1_u64);
  return Ok(value: move pair);
}
""",
    """struct Pair {
  value: u64;
}

fn make () -> own Option<Pair> pure {
  let pair: own Pair = Pair(value: 1_u64);
  return Some(value: move pair);
}
""",
]
for source in aggregate_payloads:
    try:
        democ.compile_program(source, alias=False)
    except SystemExit as error:
        assert "outside the stage-0 word-erased profile" in str(error)
    else:
        raise AssertionError("aggregate prelude payload reached stage-0 LLVM codegen")


def test_enum_equality_direct_lowering_and_truth_tables():
    enum_specs = [
        ("EmptyEq", []),
        ("OneEq", ["OneOnly"]),
        ("PairEq", ["PairFirst", "PairSecond"]),
        ("TrioEq", ["TrioFirst", "TrioSecond", "TrioThird"]),
        ("ManyEq", ["ManyZero", "ManyOne", "ManyTwo", "ManyThree", "ManyFour"]),
    ]
    declarations = []
    for enum_name, variants in enum_specs:
        body = "\n".join(f"  {variant}();" for variant in variants)
        declarations.append(f"enum {enum_name} {{\n{body}\n}}")

    comparison_functions = []
    for enum_name, _variants in enum_specs:
        for operation in ("eeq", "ene"):
            comparison_functions.append(
                f"fn compare_{enum_name.lower()}_{operation} "
                f"(left: own {enum_name}, right: own {enum_name}) -> own Bool pure {{\n"
                f"  return {operation}<{enum_name}>(left, right);\n"
                "}"
            )

    main_lines = []
    value_sets = [("Bool", ["False", "True"])] + enum_specs[1:]
    value_names = {}
    for enum_name, variants in value_sets:
        for index, variant in enumerate(variants):
            local = f"value_{enum_name.lower()}_{index}"
            value_names[(enum_name, index)] = local
            main_lines.append(f"  let {local}: own {enum_name} = {variant}();")

    comparison_index = 0
    for enum_name, variants in value_sets:
        for left_index in range(len(variants)):
            for right_index in range(len(variants)):
                left = value_names[(enum_name, left_index)]
                right = value_names[(enum_name, right_index)]
                eq_name = f"eq_result_{comparison_index}"
                ne_name = f"ne_result_{comparison_index}"
                main_lines.append(
                    f"  let {eq_name}: own Bool = eeq<{enum_name}>({left}, {right});")
                main_lines.append(
                    f"  let {ne_name}: own Bool = ene<{enum_name}>({left}, {right});")
                if left_index == right_index:
                    main_lines.append(
                        f"  check {eq_name} else trap \"eeq diagonal mismatch\";")
                    complement = f"not_ne_result_{comparison_index}"
                    main_lines.append(
                        f"  let {complement}: own Bool = bnot<Bool>({ne_name});")
                    main_lines.append(
                        f"  check {complement} else trap \"ene diagonal mismatch\";")
                else:
                    complement = f"not_eq_result_{comparison_index}"
                    main_lines.append(
                        f"  let {complement}: own Bool = bnot<Bool>({eq_name});")
                    main_lines.append(
                        f"  check {complement} else trap \"eeq off-diagonal mismatch\";")
                    main_lines.append(
                        f"  check {ne_name} else trap \"ene off-diagonal mismatch\";")
                comparison_index += 1
    main_lines.append("  return unit;")
    main_function = "fn main () -> own unit traps {\n" + "\n".join(main_lines) + "\n}"
    source = "\n\n".join(declarations + comparison_functions + [main_function]) + "\n"

    ir = compile_native(source, run=True)

    def function_ir(name):
        return ir.split(f" @{name}(", 1)[1].split("\n}", 1)[0]

    assert "icmp eq i1" in function_ir("compare_paireq_eeq")
    assert "icmp ne i1" in function_ir("compare_paireq_ene")
    assert "icmp eq i32" in function_ir("compare_trioeq_eeq")
    assert "icmp ne i32" in function_ir("compare_manyeq_ene")
    assert "icmp eq i32" in function_ir("compare_emptyeq_eeq")
    assert "icmp ne i32" in function_ir("compare_oneeq_ene")


def test_enum_equality_domain_rejections():
    declarations = """enum AlphaEq {
  AlphaFirst();
  AlphaSecond();
}

enum BetaEq {
  BetaFirst();
  BetaSecond();
}

enum PayloadEq {
  PayloadEmpty();
  PayloadValue(value: u32);
}
"""

    def compare_source(operation, type_argument, left_type, right_type=None):
        right = right_type or left_type
        return declarations + f"""
fn compare (left: own {left_type}, right: own {right}) -> own Bool pure {{
  return {operation}<{type_argument}>(left, right);
}}
"""

    cases = [
        ("OP-1", compare_source("ieq", "AlphaEq", "AlphaEq")),
        ("OP-1", compare_source("ine", "Bool", "Bool")),
        ("OP-1", compare_source("ilt", "AlphaEq", "AlphaEq")),
        ("OP-1", compare_source("eeq", "u32", "u32")),
        ("OP-1", compare_source("ene", "u32", "u32")),
        ("OP-1", compare_source("eeq", "PayloadEq", "PayloadEq")),
        ("OP-1", compare_source("eeq", "MissingEq", "MissingEq")),
        ("TYPE-5", compare_source("eeq", "AlphaEq", "AlphaEq", "BetaEq")),
    ]
    for expected_rule, source in cases:
        try:
            democ.compile_program(source, alias=False)
        except democ.CheckError as error:
            assert error.rule == expected_rule, error
        else:
            raise AssertionError(
                f"enum comparison outside its exact domain escaped {expected_rule}")


def test_fn8_enum_equality_exact_domain():
    positive = """enum ClauseEq {
  ClauseFirst();
  ClauseSecond();
  ClauseThird();
}

fn guarded (left: own ClauseEq, right: own ClauseEq) -> own unit traps requires {
  let same: own Bool = eeq<ClauseEq>(left, right);
  check same else trap "enum precondition failed";
} {
  return unit;
}

fn main () -> own unit traps {
  let left: own ClauseEq = ClauseSecond();
  let right: own ClauseEq = ClauseSecond();
  guarded(left: left, right: right);
  return unit;
}
"""
    ir = compile_native(positive, run=True)
    guarded_ir = ir.split(" @guarded(", 1)[1].split("\n}", 1)[0]
    assert "icmp eq i32" in guarded_ir

    negative_integer = """fn guarded (left: own u32, right: own u32) -> own unit traps requires {
  let same: own Bool = eeq<u32>(left, right);
  check same else trap "integer precondition escaped";
} {
  return unit;
}
"""
    negative_payload = """enum ClausePayloadEq {
  ClausePayloadValue(value: u32);
}

fn guarded (left: own ClausePayloadEq, right: own ClausePayloadEq) -> own unit traps requires {
  let different: own Bool = ene<ClausePayloadEq>(left, right);
  check different else trap "payload precondition escaped";
} {
  return unit;
}
"""
    for source in (negative_integer, negative_payload):
        try:
            democ.compile_program(source, alias=False)
        except democ.CheckError as error:
            assert error.rule == "OP-1", error
        else:
            raise AssertionError("out-of-domain enum equality entered an FN-8 clause")


def test_enum_equality_missing_type_argument_precedence():
    source = """enum MissingTypeEq {
  MissingTypeFirst();
  MissingTypeSecond();
}

fn compare (left: own MissingTypeEq, right: own MissingTypeEq) -> own Bool pure {
  return eeq(left, right);
}
"""
    try:
        democ.compile_program(source, alias=False)
    except democ.CheckError as error:
        assert error.rule == "FN-2", error
    else:
        raise AssertionError("eeq without its explicit type argument escaped FN-2")


def test_enum_equality_type_namespace_cannot_replace_nominal_metadata():
    sources = [
        """enum Bool {
  Rebound();
}
""",
        """struct Result {
}
""",
        """enum CollisionEq {
  CollisionOnly();
}

struct CollisionEq {
}
""",
        """struct ReverseCollisionEq {
}

enum ReverseCollisionEq {
  ReverseCollisionOnly();
}
""",
    ]
    for source in sources:
        try:
            democ.compile_program(source, alias=False)
        except democ.CheckError as error:
            assert error.rule == "TYPE-6", error
        else:
            raise AssertionError("a colliding type declaration replaced nominal metadata")


test_enum_equality_direct_lowering_and_truth_tables()
test_enum_equality_domain_rejections()
test_enum_equality_missing_type_argument_precedence()
test_enum_equality_type_namespace_cannot_replace_nominal_metadata()
test_fn8_enum_equality_exact_domain()

print("stage-0 codegen: aggregates, region-call retention, native fixtures, and payload profile pass")
