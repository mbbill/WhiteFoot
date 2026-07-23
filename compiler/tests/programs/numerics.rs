use super::support::{compile_and_run, compile_program};

#[test]
fn feedback_controller_executes_as_a_sustained_float_workload() {
    let llvm = compile_program("feedback_controller.wf");
    assert!(llvm.contains("call double @llvm.fma.f64"));
    assert!(llvm.contains("fadd double"));
    assert!(!llvm.contains("fadd fast"));

    let output = compile_and_run(&llvm);
    assert!(output.status.success());
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}
