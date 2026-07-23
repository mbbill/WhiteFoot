use super::*;

const RAW_DEFLATE: &[u8] = include_bytes!("../../../../tests/programs/raw_deflate.wf");
const RAW_DEFLATE_VECTORS: &[u8] =
    include_bytes!("../../../../tests/programs/raw_deflate_vectors.wf");

#[test]
fn raw_deflate_stored_and_fixed_blocks_execute_with_data_failures() {
    let llvm = compile_sources(&[
        ("raw_deflate.wf", RAW_DEFLATE),
        ("raw_deflate_vectors.wf", RAW_DEFLATE_VECTORS),
    ]);
    let inflate = emitted_function(&llvm, "inflate");
    assert!(inflate.contains("call void @free"));
    let fixed = emitted_function(&llvm, "decode_fixed");
    assert!(fixed.contains("icmp ult i64"));
    assert!(fixed.contains("call void @wf_trap"));

    let output = compile_and_run(&llvm);
    assert!(output.status.success());
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}
