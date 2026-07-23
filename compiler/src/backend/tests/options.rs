use super::{compile, compile_and_run};

#[test]
fn concrete_option_and_result_instances_share_the_nominal_backend() {
    let source =
        include_bytes!("../../../../tests/conformance/cases/x-enum-twostate-result-payload.wf");
    let output = compile_and_run(&compile(source));
    assert!(
        output.status.success(),
        "Option and Result program failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}

#[test]
fn compiler_independent_byte_scanner_returns_option_offsets() {
    let source = include_bytes!("../../../../tests/conformance/cases/x-option-byte-scanner-run.wf");
    let output = compile_and_run(&compile(source));
    assert!(
        output.status.success(),
        "Option byte scanner failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}
