use super::*;

const RAW_DEFLATE: &[u8] = include_bytes!("../../../../tests/programs/raw_deflate.wf");
const RAW_DEFLATE_DYNAMIC: &[u8] =
    include_bytes!("../../../../tests/programs/raw_deflate_dynamic.wf");
const RAW_DEFLATE_DYNAMIC_DECODE: &[u8] =
    include_bytes!("../../../../tests/programs/raw_deflate_dynamic_decode.wf");
const RAW_DEFLATE_VECTORS: &[u8] =
    include_bytes!("../../../../tests/programs/raw_deflate_vectors.wf");

#[test]
fn raw_deflate_stored_fixed_and_dynamic_blocks_execute_with_data_failures() {
    let llvm = compile_sources(&[
        ("raw_deflate.wf", RAW_DEFLATE),
        ("raw_deflate_dynamic.wf", RAW_DEFLATE_DYNAMIC),
        ("raw_deflate_dynamic_decode.wf", RAW_DEFLATE_DYNAMIC_DECODE),
        ("raw_deflate_vectors.wf", RAW_DEFLATE_VECTORS),
    ]);
    let inflate = emitted_function(&llvm, "inflate");
    assert!(inflate.contains("call void @free"));
    let length = emitted_function(&llvm, "decode_length");
    let distance = emitted_function(&llvm, "copy_distance");
    assert!(length.contains("icmp ult i64"));
    assert!(length.contains("call void @wf_trap"));
    assert!(distance.contains("icmp ult i64"));
    assert!(distance.contains("call void @wf_trap"));
    let table = emitted_function(&llvm, "build_huffman_table");
    assert!(table.contains("call ptr @malloc"));
    assert!(table.contains("call void @wf_trap"));
    let dynamic = emitted_function(&llvm, "decode_dynamic");
    assert!(dynamic.contains("call void @free"));

    let output = compile_and_run(&llvm);
    assert!(output.status.success());
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}
