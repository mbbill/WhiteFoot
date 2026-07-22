#![allow(clippy::panic)]

use crate::lexer::{LexLimits, LexOutcome, lex_v0_11};
use crate::{
    CanonicalLimits, CanonicalOutcome, FinalizeLimits, FinalizeOutcome, KERNEL_SPEC_V0_11_HASH,
    ParseLimits, ParseOutcome, ResolutionOutcome, SemanticIssueKind, SemanticLocation,
    SemanticOutcome, SemanticRuleV0_11, SourceBundle, SourceInput, SourceLimits, TerminalLimits,
    TerminalOutcome, UnsupportedSemanticFeatureV0_11, audit_canonical_v0_11, check_semantics_v0_11,
    classify_terminals_v0_11, finalize_v0_11, parse_v0_11, resolve_v0_11,
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

fn with_semantics<ResultValue>(
    source: &[u8],
    run: impl for<'classified, 'lexed, 'source> FnOnce(
        SemanticOutcome<'classified, 'lexed, 'source>,
    ) -> ResultValue,
) -> ResultValue {
    let inputs = [SourceInput::new("test.wf", source)];
    let Ok(bundle) = SourceBundle::with_limits(&inputs, SOURCE_LIMITS) else {
        panic!("semantic test bundle must be valid");
    };
    let LexOutcome::Complete(lexed) = lex_v0_11(&bundle, LEX_LIMITS) else {
        panic!("semantic test source must lex");
    };
    let TerminalOutcome::Complete(classified) = classify_terminals_v0_11(
        &lexed,
        KERNEL_SPEC_V0_11_HASH,
        TerminalLimits {
            max_tokens: LEX_LIMITS.max_tokens,
        },
    ) else {
        panic!("semantic test source must classify");
    };
    let ParseOutcome::Complete(parsed) = parse_v0_11(&classified, PARSE_LIMITS) else {
        panic!("semantic test source must parse");
    };
    let FinalizeOutcome::Complete(finalized) = finalize_v0_11(parsed, FINALIZE_LIMITS) else {
        panic!("semantic test derivation must finalize");
    };
    let CanonicalOutcome::Complete(canonical) = audit_canonical_v0_11(finalized, CANONICAL_LIMITS)
    else {
        panic!("semantic test source must be canonical");
    };
    let ResolutionOutcome::Complete(resolved) = resolve_v0_11(canonical) else {
        panic!("semantic test source must resolve");
    };
    run(check_semantics_v0_11(resolved))
}

fn assert_rule(source: &[u8], rule: SemanticRuleV0_11, kind: SemanticIssueKind) {
    with_semantics(source, |outcome| {
        let SemanticOutcome::SourceIssue { issue, .. } = outcome else {
            panic!("expected {rule:?}/{kind:?}, got {outcome:?}");
        };
        assert_eq!(issue.rule(), rule);
        assert_eq!(issue.kind(), &kind);
    });
}

#[test]
fn scalar_constants_calls_operations_and_checks_publish_one_checked_program() {
    let source = br#"const base: i32 = 40_i32;

fn add(x: own i32, y: own i32) -> own i32 pure {
  return iadd.wrap<i32>(x, y);
}

fn main() -> own unit traps {
  let result: own i32 = add(x: base, y: 2_i32);
  check ieq<i32>(result, 42_i32) else trap "wrong answer";
  return unit;
}
"#;
    with_semantics(source, |outcome| {
        let SemanticOutcome::Complete(checked) = outcome else {
            panic!("complete scalar family must check: {outcome:?}");
        };
        assert_eq!(checked.function_count(), 2);
        assert_eq!(checked.entry_function_name(), "main");
    });
}

#[test]
fn semantic_rule_owners_remain_distinct() {
    assert_rule(
        b"fn main() -> own unit pure {\n  let value: own i8 = 128_i8;\n  return unit;\n}\n",
        SemanticRuleV0_11::Form7,
        SemanticIssueKind::InvalidIntegerLiteral,
    );
    assert_rule(
        b"fn main() -> own unit pure {\n  return 0_i32;\n}\n",
        SemanticRuleV0_11::Fn1,
        SemanticIssueKind::ReturnMismatch,
    );
    assert_rule(
        b"fn main() -> own unit traps {\n  check 1_i32 else trap \"bad\";\n  return unit;\n}\n",
        SemanticRuleV0_11::Op5,
        SemanticIssueKind::InvalidCheckCondition,
    );
    assert_rule(
        b"fn main() -> own unit pure {\n  check True() else trap \"bad\";\n  return unit;\n}\n",
        SemanticRuleV0_11::Eff2,
        SemanticIssueKind::EffectMismatch,
    );
    assert_rule(
        b"fn main() -> own unit traps {\n  return unit;\n}\n",
        SemanticRuleV0_11::Eff2,
        SemanticIssueKind::EffectMismatch,
    );
}

#[test]
fn function_control_and_main_contract_are_checked_before_lowering() {
    assert_rule(
        b"fn main() -> own unit pure {\n}\n",
        SemanticRuleV0_11::Fn1,
        SemanticIssueKind::FunctionFallthrough,
    );
    assert_rule(
        b"fn main() -> own unit pure {\n  return unit;\n  return unit;\n}\n",
        SemanticRuleV0_11::Fn1,
        SemanticIssueKind::UnreachableStatement,
    );
    assert_rule(
        b"fn main(value: own i32) -> own unit pure {\n  return unit;\n}\n",
        SemanticRuleV0_11::Fn7,
        SemanticIssueKind::InvalidMain,
    );
}

#[test]
fn named_arguments_and_copy_move_spelling_are_checked_generally() {
    let wrong_name = br#"fn take(value: own i32) -> own unit pure {
  return unit;
}

fn main() -> own unit pure {
  take(other: 1_i32);
  return unit;
}
"#;
    assert_rule(
        wrong_name,
        SemanticRuleV0_11::Gram11,
        SemanticIssueKind::InvalidNamedArguments,
    );
    assert_rule(
        b"fn main() -> own unit pure {\n  let a: own i32 = 1_i32;\n  let b: own i32 = move a;\n  return unit;\n}\n",
        SemanticRuleV0_11::Own1,
        SemanticIssueKind::MoveOfCopy,
    );
}

#[test]
fn operation_call_shapes_keep_their_exact_rule_owners() {
    assert_rule(
        b"fn main() -> own unit pure {\n  let value: own i32 = iadd.wrap(1_i32, 2_i32);\n  return unit;\n}\n",
        SemanticRuleV0_11::Fn2,
        SemanticIssueKind::InvalidOperation,
    );
    assert_rule(
        b"fn main() -> own unit pure {\n  let value: own i32 = iadd.wrap<i32>(left: 1_i32, right: 2_i32);\n  return unit;\n}\n",
        SemanticRuleV0_11::Gram11,
        SemanticIssueKind::InvalidNamedArguments,
    );
}

#[test]
fn effect_mismatch_is_located_at_the_written_effect_row() {
    let source =
        b"fn main() -> own unit pure {\n  check True() else trap \"bad\";\n  return unit;\n}\n";
    with_semantics(source, |outcome| {
        let SemanticOutcome::SourceIssue { issue, .. } = outcome else {
            panic!("expected EFF-2 mismatch, got {outcome:?}");
        };
        assert_eq!(issue.rule(), SemanticRuleV0_11::Eff2);
        let SemanticLocation::SourceNode(_, coordinate) = issue.location() else {
            panic!("EFF-2 must use the source effects node");
        };
        let start = usize::try_from(coordinate.start().value()).expect("test offset fits usize");
        let end = usize::try_from(coordinate.end().value()).expect("test offset fits usize");
        assert_eq!(&source[start..end], b"pure");
    });
}

#[test]
fn invalid_generic_main_is_fn7_not_an_unsupported_generic() {
    assert_rule(
        b"fn main<T>() -> own unit pure {\n  return unit;\n}\n",
        SemanticRuleV0_11::Fn7,
        SemanticIssueKind::InvalidMain,
    );
}

#[test]
fn unimplemented_language_families_are_not_source_rejections() {
    let source =
        b"struct Pair {\n  value: i32;\n}\n\nfn main() -> own unit pure {\n  return unit;\n}\n";
    with_semantics(source, |outcome| {
        let SemanticOutcome::Unsupported { unsupported, .. } = outcome else {
            panic!("aggregate semantics must be explicitly unsupported: {outcome:?}");
        };
        assert_eq!(
            unsupported.feature(),
            UnsupportedSemanticFeatureV0_11::UserNominalDeclarations
        );
    });
}
