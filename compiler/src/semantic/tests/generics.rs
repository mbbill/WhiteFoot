use crate::{
    SemanticIssueKind, SemanticOutcome, SemanticRuleV0_14, UnsupportedSemanticFeatureV0_14,
};

use super::{assert_rule, assert_unsupported, with_semantics};

#[test]
fn explicit_int_generic_function_builds_each_reachable_concrete_instance() {
    let source = br#"fn identity<T: Int>(value: own T) -> own T pure {
  return value;
}

fn main() -> own unit traps {
  let first: own u32 = identity<u32>(value: 7_u32);
  let second: own i64 = identity<i64>(value: -9_i64);
  check ieq<u32>(first, 7_u32) else trap "u32 generic instance";
  check ieq<i64>(second, -9_i64) else trap "i64 generic instance";
  return unit;
}
"#;
    with_semantics(source, |outcome| {
        let SemanticOutcome::Complete(checked) = outcome else {
            panic!("explicit generic instances must check: {outcome:?}");
        };
        assert_eq!(checked.function_count(), 3);
        assert_eq!(checked.entry_function_name(), "main");
    });
}

#[test]
fn int_bound_selects_the_same_operation_row_for_every_concrete_instance() {
    let source = br#"fn maximum<T: Int>(left: own T, right: own T) -> own T pure {
  return imax<T>(left, right);
}

fn main() -> own unit traps {
  let small: own u8 = maximum<u8>(left: 4_u8, right: 9_u8);
  let signed: own i64 = maximum<i64>(left: -7_i64, right: -2_i64);
  check ieq<u8>(small, 9_u8) else trap "u8 generic maximum";
  check ieq<i64>(signed, -2_i64) else trap "i64 generic maximum";
  return unit;
}
"#;
    with_semantics(source, |outcome| {
        let SemanticOutcome::Complete(checked) = outcome else {
            panic!("Int-bound operation must check for each instance: {outcome:?}");
        };
        assert_eq!(checked.function_count(), 3);
    });
}

#[test]
fn int_bound_rejects_a_non_integer_explicit_argument_under_fn3() {
    let source = br#"fn identity<T: Int>(value: own T) -> own T pure {
  return value;
}

fn main() -> own unit pure {
  let input: own Bool = True();
  let invalid: own Bool = identity<Bool>(value: input);
  return unit;
}
"#;
    assert_rule(
        source,
        SemanticRuleV0_14::Fn3,
        SemanticIssueKind::TypeMismatch,
    );
}

#[test]
fn generic_call_cycle_stops_before_concrete_instance_enumeration() {
    let source = br#"fn recursive<T: Int>(value: own T) -> own T pure {
  return recursive<T>(value: value);
}

fn main() -> own unit pure {
  return unit;
}
"#;
    assert_unsupported(source, UnsupportedSemanticFeatureV0_14::Generics);
}

#[test]
fn unused_int_generic_body_is_checked_for_the_complete_bound_domain() {
    let source = br#"fn invalid<T: Int>(value: own T) -> own T pure {
  return 0_u8;
}

fn main() -> own unit pure {
  return unit;
}
"#;
    assert_rule(
        source,
        SemanticRuleV0_14::Fn1,
        SemanticIssueKind::ReturnMismatch,
    );
}

#[test]
fn nested_generic_calls_discover_reachable_instances_after_template_checking() {
    let source = br#"fn select<T: Int>(value: own T) -> own T pure {
  return imax<T>(value, value);
}

fn forward<T: Int>(value: own T) -> own T pure {
  return select<T>(value: value);
}

fn main() -> own unit traps {
  let small: own u8 = forward<u8>(value: 7_u8);
  let signed: own i64 = forward<i64>(value: -9_i64);
  check ieq<u8>(small, 7_u8) else trap "nested u8 instance";
  check ieq<i64>(signed, -9_i64) else trap "nested i64 instance";
  return unit;
}
"#;
    with_semantics(source, |outcome| {
        let SemanticOutcome::Complete(checked) = outcome else {
            panic!("nested generic calls must check: {outcome:?}");
        };
        assert_eq!(checked.function_count(), 5);
    });
}

#[test]
fn const_parameters_forward_symbolically_and_instantiate_at_reachable_sizes() {
    let source = br#"fn preserve<const n: u64>(value: own array<u8, n>) -> own array<u8, n> pure {
  let size: own u64 = len<u8>(value);
  return move value;
}

fn forward<const n: u64>(value: own array<u8, n>) -> own array<u8, n> pure {
  return preserve<n>(value: move value);
}

fn main() -> own unit traps {
  let small_input: own array<u8, 2> = array_new<u8, 2>(7_u8);
  let small: own array<u8, 2> = forward<2>(value: move small_input);
  let large_input: own array<u8, 5> = array_new<u8, 5>(9_u8);
  let large: own array<u8, 5> = forward<5>(value: move large_input);
  let first: own u8 = index<u8>(small, 1_u64);
  let second: own u8 = index<u8>(large, 4_u64);
  check ieq<u8>(first, 7_u8) else trap "small const instance";
  check ieq<u8>(second, 9_u8) else trap "large const instance";
  return unit;
}
"#;
    with_semantics(source, |outcome| {
        let SemanticOutcome::Complete(checked) = outcome else {
            panic!("forwarded const instances must check: {outcome:?}");
        };
        assert_eq!(checked.function_count(), 5);
    });
}

#[test]
fn unbounded_type_parameters_build_only_explicit_reachable_instances() {
    let source = br#"fn marker<T>() -> own unit pure {
  return unit;
}

fn main() -> own unit pure {
  marker<u8>();
  marker<Bool>();
  return unit;
}
"#;
    with_semantics(source, |outcome| {
        let SemanticOutcome::Complete(checked) = outcome else {
            panic!("unbounded marker instances must check: {outcome:?}");
        };
        assert_eq!(checked.function_count(), 3);
    });
}

#[test]
fn generic_argument_kinds_and_const_parameter_types_are_checked() {
    assert_rule(
        br#"fn marker<T>() -> own unit pure {
  return unit;
}

fn main() -> own unit pure {
  marker<4>();
  return unit;
}
"#,
        SemanticRuleV0_14::Type5,
        SemanticIssueKind::TypeMismatch,
    );
    assert_rule(
        br#"fn sized<const n: u64>() -> own unit pure {
  return unit;
}

fn main() -> own unit pure {
  sized<u8>();
  return unit;
}
"#,
        SemanticRuleV0_14::Type5,
        SemanticIssueKind::TypeMismatch,
    );
    assert_rule(
        br#"fn invalid<const n: Bool>() -> own unit pure {
  return unit;
}

fn main() -> own unit pure {
  return unit;
}
"#,
        SemanticRuleV0_14::Const1,
        SemanticIssueKind::InvalidConstValue,
    );
}
