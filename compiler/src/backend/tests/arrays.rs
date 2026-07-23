use super::{compile, compile_and_run, emitted_function};

#[test]
fn const_arrays_are_immutable_globals_and_execute_through_index_and_len() {
    let llvm = compile(include_bytes!(
        "../../../../tests/conformance/cases/const2-pos-array-lookup.wf"
    ));
    assert!(llvm.contains(
        "@.wf_const.0 = private unnamed_addr constant [4 x i8] [i8 10, i8 20, i8 30, i8 40]"
    ));
    let main = emitted_function(&llvm, "main");
    assert!(main.contains("icmp ult i64"));
    assert!(main.contains("call void @wf_trap"));
    let output = compile_and_run(&llvm);
    assert!(output.status.success());
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}

#[test]
fn filled_arrays_cross_function_boundaries_and_keep_a_checked_read() {
    let source = br#"fn make() -> own array<u16, 4> pure {
  return array_new<u16, 4>(42_u16);
}

fn read(values: own array<u16, 4>, offset: own u64) -> own u16 traps {
  let value: own u16 = index<u16>(values, offset);
  return value;
}

fn main() -> own unit traps {
  let values: own array<u16, 4> = make();
  let length: own u64 = len<u16>(values);
  check ieq<u64>(length, 4_u64) else trap "length drift";
  let value: own u16 = read(values: move values, offset: 3_u64);
  check ieq<u16>(value, 42_u16) else trap "fill drift";
  return unit;
}
"#;
    let llvm = compile(source);
    let read = emitted_function(&llvm, "read");
    let bounds = read
        .find("icmp ult i64")
        .expect("array read must compare its offset with the fixed length");
    let trap = read[bounds..]
        .find("call void @wf_trap")
        .map(|offset| bounds + offset)
        .expect("array read must retain its OP-4 trap edge");
    let load = read[trap..]
        .find("getelementptr inbounds [4 x i16]")
        .map(|offset| trap + offset)
        .expect("array read must address the element only on the safe edge");
    assert!(bounds < trap && trap < load);
    assert!(llvm.contains("array.fill.head"));
    assert!(llvm.contains("array.fill.done"));

    let output = compile_and_run(&llvm);
    assert!(output.status.success());
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}

#[test]
fn out_of_bounds_array_read_reports_op4_before_abort() {
    let source = br#"fn main() -> own unit traps {
  let values: own array<u8, 2> = array_new<u8, 2>(7_u8);
  let value: own u8 = index<u8>(values, 2_u64);
  return unit;
}
"#;
    let output = compile_and_run(&compile(source));
    assert!(!output.status.success());
    let stderr = String::from_utf8(output.stderr).expect("trap record is UTF-8");
    assert!(stderr.starts_with(
        "{\"rule_id\":\"OP-4\",\"message\":\"\",\"function\":\"main\",\"node_path\":["
    ));
    assert!(stderr.ends_with("]}\n"));
    assert_eq!(stderr.lines().count(), 1);
}

#[test]
fn compiler_independent_array_checksum_executes() {
    let output = compile_and_run(&compile(include_bytes!(
        "../../../../tests/conformance/cases/x-array-const-checksum-run.wf"
    )));
    assert!(output.status.success());
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}

#[test]
fn indexed_set_checks_before_rhs_and_updates_the_array() {
    let source = br#"fn replacement() -> own u8 traps {
  check True() else trap "replacement drift";
  return 9_u8;
}

fn main() -> own unit traps {
  let values: own array<u8, 2> = array_new<u8, 2>(0_u8);
  set index<u8>(values, 1_u64) = replacement();
  let stored: own u8 = index<u8>(values, 1_u64);
  check ieq<u8>(stored, 9_u8) else trap "set drift";
  return unit;
}
"#;
    let llvm = compile(source);
    let main = emitted_function(&llvm, "main");
    let bounds = main
        .find("icmp ult i64")
        .expect("indexed target must retain its bounds check");
    let target_trap = main[bounds..]
        .find("call void @wf_trap")
        .map(|offset| bounds + offset)
        .expect("indexed target must retain its trap edge");
    let rhs = main[target_trap..]
        .find("call i8 @wf_replacement")
        .map(|offset| target_trap + offset)
        .expect("RHS must be emitted after target evaluation");
    let store = main[rhs..]
        .find("store i8")
        .map(|offset| rhs + offset)
        .expect("array update must store only after the RHS");
    assert!(bounds < target_trap && target_trap < rhs && rhs < store);

    let output = compile_and_run(&llvm);
    assert!(output.status.success());
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}

#[test]
fn failing_indexed_set_target_never_evaluates_rhs() {
    let source = br#"fn replacement() -> own u8 traps {
  check False() else trap "RHS evaluated";
  return 9_u8;
}

fn main() -> own unit traps {
  let values: own array<u8, 2> = array_new<u8, 2>(0_u8);
  set index<u8>(values, 2_u64) = replacement();
  return unit;
}
"#;
    let output = compile_and_run(&compile(source));
    assert!(!output.status.success());
    let stderr = String::from_utf8(output.stderr).expect("trap record is UTF-8");
    assert!(stderr.starts_with(
        "{\"rule_id\":\"OP-4\",\"message\":\"\",\"function\":\"main\",\"node_path\":["
    ));
    assert!(!stderr.contains("RHS evaluated"));
    assert_eq!(stderr.lines().count(), 1);
}

#[test]
fn compiler_independent_mutable_array_checksum_executes() {
    let output = compile_and_run(&compile(include_bytes!(
        "../../../../tests/conformance/cases/x-array-mutable-checksum-run.wf"
    )));
    assert!(output.status.success());
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}

#[test]
fn nested_struct_array_updates_rebuild_every_aggregate_layer_after_the_rhs() {
    let source = br#"struct Inner {
  values: array<u8, 2>;
  sibling: u16;
}

struct Outer {
  prefix: u32;
  inner: Inner;
}

fn replacement() -> own u8 traps {
  check True() else trap "replacement drift";
  return 9_u8;
}

fn main() -> own unit traps {
  let values: own array<u8, 2> = array_new<u8, 2>(0_u8);
  let inner: own Inner = Inner(values: move values, sibling: 77_u16);
  let outer: own Outer = Outer(prefix: 123_u32, inner: move inner);
  set index<u8>(outer.inner.values, 1_u64) = replacement();
  let stored: own u8 = index<u8>(outer.inner.values, 1_u64);
  check ieq<u8>(stored, 9_u8) else trap "array update";
  check ieq<u16>(outer.inner.sibling, 77_u16) else trap "inner sibling";
  check ieq<u32>(outer.prefix, 123_u32) else trap "outer sibling";
  return unit;
}
"#;
    let llvm = compile(source);
    let main = emitted_function(&llvm, "main");
    let bounds = main
        .find("icmp ult i64")
        .expect("projected array target must retain its bounds check");
    let target_trap = main[bounds..]
        .find("call void @wf_trap")
        .map(|offset| bounds + offset)
        .expect("projected array target must retain its OP-4 trap edge");
    let rhs = main[target_trap..]
        .find("call i8 @wf_replacement")
        .map(|offset| target_trap + offset)
        .expect("RHS must follow projected target evaluation");
    let rebuild = main[rhs..]
        .find("insertvalue %wf.t")
        .map(|offset| rhs + offset)
        .expect("projected update must rebuild its enclosing structs");
    assert!(bounds < target_trap && target_trap < rhs && rhs < rebuild);

    let output = compile_and_run(&llvm);
    assert!(output.status.success());
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}
