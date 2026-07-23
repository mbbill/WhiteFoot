use super::*;

#[test]
fn primitive_buffers_cross_functions_update_and_free_once() {
    let source = br#"fn make(n: own u64) -> own buffer<u16> allocates(heap), traps {
  return buffer_new<u16>(n, 3_u16);
}

fn replacement() -> own u16 pure {
  return 9_u16;
}

fn main() -> own unit allocates(heap), traps {
  let values: own buffer<u16> = make(n: 4_u64);
  set index<u16>(values, 2_u64) = replacement();
  let length: own u64 = len<u16>(values);
  let stored: own u16 = index<u16>(values, 2_u64);
  check ieq<u64>(length, 4_u64) else trap "length drift";
  check ieq<u16>(stored, 9_u16) else trap "store drift";
  return unit;
}
"#;
    let llvm = compile(source);
    let main = emitted_function(&llvm, "main");
    let guard = main
        .find("buffer.bounds.cont")
        .expect("SET-1 must retain an OP-4 buffer guard");
    let rhs = main
        .find("call i16 @wf_replacement")
        .expect("SET-1 must evaluate its RHS once");
    let store = main
        .find("store i16 %v")
        .expect("SET-1 must commit one element store");
    assert!(guard < rhs && rhs < store);
    assert_eq!(main.matches("call void @free").count(), 1);
    assert!(!emitted_function(&llvm, "make").contains("call void @free"));

    let output = compile_and_run(&llvm);
    assert!(output.status.success());
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}

#[test]
fn op9_overflow_traps_before_allocation() {
    let source = br#"fn main() -> own unit allocates(heap), traps {
  let values: own buffer<u64> = buffer_new<u64>(18446744073709551615_u64, 0_u64);
  return unit;
}
"#;
    let llvm = compile(source);
    let main = emitted_function(&llvm, "main");
    let multiply = main
        .find("@llvm.umul.with.overflow.i64")
        .expect("buffer_new must retain checked byte multiplication");
    let overflow = main
        .find("buffer.fill.overflow")
        .expect("overflow must have its OP-9 trap edge");
    let allocation = main
        .find("call ptr @malloc")
        .expect("allocation must remain after the overflow branch");
    assert!(multiply < overflow && overflow < allocation);

    let output = compile_and_run(&llvm);
    assert!(!output.status.success());
    let stderr = String::from_utf8(output.stderr).expect("trap record is UTF-8");
    assert!(stderr.starts_with(
        "{\"rule_id\":\"OP-9\",\"message\":\"\",\"function\":\"main\",\"node_path\":["
    ));
    assert_eq!(stderr.lines().count(), 1);
}

#[test]
fn failing_buffer_set_target_never_evaluates_rhs() {
    let source = br#"fn replacement() -> own u8 traps {
  check False() else trap "RHS evaluated";
  return 9_u8;
}

fn main() -> own unit allocates(heap), traps {
  let values: own buffer<u8> = buffer_new<u8>(2_u64, 0_u8);
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
fn empty_buffer_has_zero_length_and_a_normal_free() {
    let source = br#"fn main() -> own unit allocates(heap), traps {
  let values: own buffer<u8> = buffer_new<u8>(0_u64, 7_u8);
  let length: own u64 = len<u8>(values);
  check ieq<u64>(length, 0_u64) else trap "length drift";
  return unit;
}
"#;
    let output = compile_and_run(&compile(source));
    assert!(output.status.success());
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}

#[test]
fn buffer_cleanup_is_explicit_on_return_and_break_edges() {
    let source = br#"fn cleanup(flag: own Bool) -> own unit allocates(heap), traps {
  let values: own buffer<u8> = buffer_new<u8>(2_u64, 0_u8);
  match flag {
    True() => {
      return unit;
    }
    False() => {
    }
  }
  loop @done {
    let scratch: own buffer<u16> = buffer_new<u16>(1_u64, 0_u16);
    break @done;
  }
  return unit;
}

fn main() -> own unit allocates(heap), traps {
  let true_value: own Bool = True();
  let false_value: own Bool = False();
  cleanup(flag: true_value);
  cleanup(flag: false_value);
  return unit;
}
"#;
    let llvm = compile(source);
    let cleanup = emitted_function(&llvm, "cleanup");
    assert_eq!(cleanup.matches("call void @free").count(), 3);
    let output = compile_and_run(&llvm);
    assert!(output.status.success());
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}

#[test]
fn compiler_independent_mutable_buffer_checksum_executes() {
    let output = compile_and_run(&compile(include_bytes!(
        "../../../../tests/conformance/cases/x-buffer-mutable-checksum-run.wf"
    )));
    assert!(output.status.success());
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}
