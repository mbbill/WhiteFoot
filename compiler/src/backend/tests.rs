#![allow(clippy::panic)]

use std::process::{Command, Output};
use std::sync::atomic::{AtomicU64, Ordering};

use crate::lexer::{LexLimits, LexOutcome, lex_v0_11};
use crate::{
    CanonicalLimits, CanonicalOutcome, FinalizeLimits, FinalizeOutcome, KERNEL_SPEC_V0_11_HASH,
    ParseLimits, ParseOutcome, ResolutionOutcome, SemanticOutcome, SourceBundle, SourceInput,
    SourceLimits, TerminalLimits, TerminalOutcome, audit_canonical_v0_11, check_semantics_v0_11,
    classify_terminals_v0_11, compile_v0_11, emit_llvm_v0_11, finalize_v0_11, lower_checked_v0_11,
    parse_v0_11, resolve_v0_11,
};

const SOURCE_LIMITS: SourceLimits = SourceLimits {
    max_sources: 4,
    max_logical_path_bytes: 128,
    max_source_bytes: 262_144,
    max_total_source_bytes: 524_288,
    max_binding_bytes: 1_048_576,
};

const LEX_LIMITS: LexLimits = LexLimits {
    max_sources: 4,
    max_source_bytes: 262_144,
    max_total_source_bytes: 524_288,
    max_token_bytes: 16_384,
    max_tokens: 131_072,
    max_lexemes: 262_144,
};

const PARSE_LIMITS: ParseLimits = ParseLimits {
    max_work: 8_000_000,
    max_tasks: 131_072,
    max_frames: 8_192,
    max_elements: 262_144,
};

const FINALIZE_LIMITS: FinalizeLimits = FinalizeLimits {
    max_work: 8_000_000,
    max_roots: 131_072,
    max_shape_tasks: 131_072,
    max_nodes: 131_072,
    max_child_edges: 131_072,
    max_terminals: 131_072,
    max_sources: 4,
};

const CANONICAL_LIMITS: CanonicalLimits = CanonicalLimits {
    max_work: 8_000_000,
    max_source_bytes: 262_144,
    max_total_source_bytes: 524_288,
    max_gaps: 131_072,
    max_path_components: 8_192,
};

static NEXT_TEST: AtomicU64 = AtomicU64::new(0);

fn emit(source: &[u8]) -> String {
    let inputs = [SourceInput::new("test.wf", source)];
    let bundle = SourceBundle::with_limits(&inputs, SOURCE_LIMITS).expect("valid test bundle");
    let LexOutcome::Complete(lexed) = lex_v0_11(&bundle, LEX_LIMITS) else {
        panic!("backend test source must lex");
    };
    let TerminalOutcome::Complete(classified) = classify_terminals_v0_11(
        &lexed,
        KERNEL_SPEC_V0_11_HASH,
        TerminalLimits {
            max_tokens: LEX_LIMITS.max_tokens,
        },
    ) else {
        panic!("backend test source must classify");
    };
    let ParseOutcome::Complete(parsed) = parse_v0_11(&classified, PARSE_LIMITS) else {
        panic!("backend test source must parse");
    };
    let FinalizeOutcome::Complete(finalized) = finalize_v0_11(parsed, FINALIZE_LIMITS) else {
        panic!("backend test source must finalize");
    };
    let CanonicalOutcome::Complete(canonical) = audit_canonical_v0_11(finalized, CANONICAL_LIMITS)
    else {
        panic!("backend test source must be canonical");
    };
    let ResolutionOutcome::Complete(resolved) = resolve_v0_11(canonical) else {
        panic!("backend test source must resolve");
    };
    let SemanticOutcome::Complete(checked) = check_semantics_v0_11(resolved) else {
        panic!("backend test source must check");
    };
    let ir = lower_checked_v0_11(*checked).expect("checked program must lower");
    emit_llvm_v0_11(&ir)
        .expect("lowered program must emit")
        .into_string()
}

fn compile(source: &[u8]) -> String {
    compile_v0_11(
        &[SourceInput::new("test.wf", source)],
        crate::CompilerLimits::default(),
    )
    .expect("normal compiler pipeline must emit")
}

fn compile_and_run(llvm: &str) -> Output {
    let sequence = NEXT_TEST.fetch_add(1, Ordering::Relaxed);
    let directory =
        std::env::temp_dir().join(format!("whitefoot-v011-{}-{sequence}", std::process::id()));
    std::fs::create_dir(&directory).expect("unique backend test directory");
    let module = directory.join("program.ll");
    let executable = directory.join("program");
    std::fs::write(&module, llvm).expect("write backend test module");
    let compile = Command::new("/usr/bin/clang")
        .arg("-x")
        .arg("ir")
        .arg(&module)
        .arg("-o")
        .arg(&executable)
        .output()
        .expect("invoke host clang");
    if !compile.status.success() {
        panic!(
            "clang rejected emitted LLVM:\n{}\n{}",
            String::from_utf8_lossy(&compile.stderr),
            llvm
        );
    }
    let output = Command::new(&executable)
        .output()
        .expect("run backend test executable");
    std::fs::remove_file(&executable).expect("remove backend test executable");
    std::fs::remove_file(&module).expect("remove backend test module");
    std::fs::remove_dir(&directory).expect("remove backend test directory");
    output
}

#[test]
fn emitted_module_retains_checks_and_avoids_undefined_overflow_flags() {
    let source = br#"fn add(x: own i32, y: own i32) -> own i32 traps {
  return iadd.trap<i32>(x, y);
}

fn main() -> own unit traps {
  let answer: own i32 = add(x: 40_i32, y: 2_i32);
  check ieq<i32>(answer, 42_i32) else trap "wrong answer";
  return unit;
}
"#;
    let llvm = emit(source);
    assert!(llvm.contains("@llvm.sadd.with.overflow.i32"));
    assert!(llvm.contains("br i1"));
    assert!(llvm.contains("call void @wf_trap"));
    assert!(!llvm.contains(" nsw "));
    assert!(!llvm.contains(" nuw "));
    assert!(!llvm.contains("llvm.assume"));
}

#[test]
fn compiler_independent_scalar_cases_execute_through_host_llvm() {
    for source in [
        include_bytes!("../../../tests/conformance/cases/scope3-pos-defined-run.wf").as_slice(),
        include_bytes!("../../../tests/conformance/cases/type5-pos-explicit.wf").as_slice(),
        include_bytes!("../../../tests/conformance/cases/gram11-pos-named-args.wf").as_slice(),
        include_bytes!("../../../tests/conformance/cases/form7-pos-in-range.wf").as_slice(),
        include_bytes!("../../../tests/conformance/cases/op1-pos-table-op.wf").as_slice(),
        include_bytes!("../../../tests/conformance/cases/x-const-scalar-u64-width.wf").as_slice(),
        include_bytes!(
            "../../../tests/conformance/cases/x-arith-iadd-wrap-overflow-to-negative.wf"
        )
        .as_slice(),
        include_bytes!("../../../tests/conformance/cases/x-arith-isub-wrap-min-roundtrip-runs.wf")
            .as_slice(),
    ] {
        let output = compile_and_run(&compile(source));
        assert!(output.status.success());
        assert!(output.stdout.is_empty());
        assert!(output.stderr.is_empty());
    }
}

#[test]
fn every_lowered_integer_mode_and_comparison_executes_with_exact_width_and_sign() {
    let source = br#"fn main() -> own unit traps {
  let aw: own i8 = iadd.wrap<i8>(127_i8, 1_i8);
  let sw: own u8 = isub.wrap<u8>(0_u8, 1_u8);
  let mw: own u16 = imul.wrap<u16>(65535_u16, 2_u16);
  let ast: own i16 = iadd.trap<i16>(-10_i16, 3_i16);
  let aut: own u16 = iadd.trap<u16>(10_u16, 3_u16);
  let sst: own i32 = isub.trap<i32>(10_i32, 3_i32);
  let sut: own u32 = isub.trap<u32>(10_u32, 3_u32);
  let mst: own i64 = imul.trap<i64>(6_i64, 7_i64);
  let mut: own u64 = imul.trap<u64>(6_u64, 7_u64);
  check ieq<i8>(aw, -128_i8) else trap "signed add wrap drift";
  check ieq<u8>(sw, 255_u8) else trap "unsigned subtract wrap drift";
  check ieq<u16>(mw, 65534_u16) else trap "unsigned multiply wrap drift";
  check ieq<i16>(ast, -7_i16) else trap "signed add trap drift";
  check ieq<u16>(aut, 13_u16) else trap "unsigned add trap drift";
  check ieq<i32>(sst, 7_i32) else trap "signed subtract trap drift";
  check ieq<u32>(sut, 7_u32) else trap "unsigned subtract trap drift";
  check ieq<i64>(mst, 42_i64) else trap "signed multiply trap drift";
  check ieq<u64>(mut, 42_u64) else trap "unsigned multiply trap drift";
  check ine<i32>(1_i32, 2_i32) else trap "ine drift";
  check ilt<i32>(-1_i32, 0_i32) else trap "signed ilt drift";
  check ile<u32>(1_u32, 1_u32) else trap "unsigned ile drift";
  check igt<i32>(1_i32, -1_i32) else trap "signed igt drift";
  check ige<u32>(1_u32, 1_u32) else trap "unsigned ige drift";
  return unit;
}
"#;
    let output = compile_and_run(&compile(source));
    assert!(output.status.success());
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}

#[test]
fn unit_is_a_first_class_parameter_result_and_local() {
    let source = br#"fn identity(value: own unit) -> own unit pure {
  return value;
}

fn main() -> own unit pure {
  let value: own unit = identity(value: unit);
  return value;
}
"#;
    let output = compile_and_run(&compile(source));
    assert!(output.status.success());
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}

#[test]
fn explicit_check_failure_emits_the_exact_mandatory_record_shape() {
    let source = b"fn main() -> own unit traps {\n  check False() else trap \"bad \\\"quote\\\"\\nline\";\n  return unit;\n}\n";
    let output = compile_and_run(&compile(source));
    assert!(!output.status.success());
    let stderr = String::from_utf8(output.stderr).expect("trap record is UTF-8");
    assert!(stderr.starts_with(
        "{\"rule_id\":\"OP-5\",\"message\":\"bad \\\"quote\\\"\\nline\",\"function\":\"main\",\"node_path\":["
    ));
    assert!(stderr.ends_with("]}\n"));
    assert_eq!(stderr.lines().count(), 1);
}

#[test]
fn integer_overflow_reports_op2_before_abort() {
    let source = br#"fn main() -> own unit traps {
  let overflow: own i8 = iadd.trap<i8>(127_i8, 1_i8);
  return unit;
}
"#;
    let output = compile_and_run(&compile(source));
    assert!(!output.status.success());
    let stderr = String::from_utf8(output.stderr).expect("trap record is UTF-8");
    assert!(stderr.starts_with(
        "{\"rule_id\":\"OP-2\",\"message\":\"integer overflow\",\"function\":\"main\",\"node_path\":["
    ));
    assert!(stderr.ends_with("]}\n"));
}
