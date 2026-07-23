use super::support::{compile_and_run, compile_program, emitted_function};

#[test]
fn recursively_boxed_tree_executes_with_derived_cleanup() {
    let llvm = compile_program("recursive_tree.wf");
    let count = emitted_function(&llvm, "count");
    assert!(count.contains("call i64 @wf_count"));
    assert!(llvm.contains("call ptr @malloc"));
    assert!(llvm.contains("icmp ne ptr"));
    assert!(llvm.contains("call void @free"));
    let drop_start = llvm
        .find("define private void @wf.drop")
        .expect("recursive enum must have a derived drop helper");
    let drop_end = llvm[drop_start..]
        .find("\n}\n\n")
        .map(|offset| drop_start + offset)
        .expect("drop helper must be complete");
    let drop_helper = &llvm[drop_start..drop_end];
    assert!(drop_helper.contains("call void @wf.drop"));
    assert_eq!(drop_helper.matches("call void @free").count(), 2);

    let output = compile_and_run(&llvm);
    assert!(output.status.success());
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}
