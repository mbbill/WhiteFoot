use crate::{SemanticIssueKind, SemanticOutcome, SemanticRuleV0_14};

use super::super::model::{CheckedExpression, CheckedMode, CheckedSetTarget, CheckedStatement};
use super::{assert_rule, with_semantics};

pub(super) const BORROWED_COLUMNS: &[u8] =
    include_bytes!("../../../../tests/conformance/cases/x-buffer-borrowed-columns-run.wf");

#[test]
fn buffer_borrows_keep_modes_provenance_effects_and_distinct_field_loans() {
    with_semantics(BORROWED_COLUMNS, |outcome| {
        let SemanticOutcome::Complete(checked) = outcome else {
            panic!("borrowed buffer helpers must check: {outcome:?}");
        };
        let fill = &checked.data.functions[0];
        assert!(matches!(fill.parameters[0].mode, CheckedMode::Unique(_)));
        let CheckedStatement::Loop { body, .. } = &fill.body[1] else {
            panic!("fill must retain its loop");
        };
        let CheckedStatement::Match { arms, .. } = &body[1] else {
            panic!("fill loop must retain its terminating match");
        };
        let CheckedStatement::Set { target, .. } = &arms[1].body[0] else {
            panic!("fill must write the left borrowed buffer");
        };
        assert!(matches!(target, CheckedSetTarget::BufferIndex(_)));

        let main = &checked.data.functions[2];
        let CheckedStatement::Region { body, .. } = &main.body[4] else {
            panic!("main must retain the fill region");
        };
        assert!(matches!(
            &body[0],
            CheckedStatement::Let {
                value: CheckedExpression::BorrowBuffer { root },
                ..
            } if root.fields == [0]
        ));
        assert!(matches!(
            &body[1],
            CheckedStatement::Let {
                value: CheckedExpression::BorrowBuffer { root },
                ..
            } if root.fields == [1]
        ));
    });
}

#[test]
fn borrowed_column_effect_rows_are_exact() {
    let wrong = BORROWED_COLUMNS
        .windows(b"writes('r), traps".len())
        .position(|window| window == b"writes('r), traps")
        .expect("fixture contains fill effects");
    let mut source = BORROWED_COLUMNS.to_vec();
    source.splice(
        wrong..wrong + b"writes('r), traps".len(),
        b"traps".iter().copied(),
    );
    with_semantics(&source, |outcome| {
        let SemanticOutcome::SourceIssue { issue } = outcome else {
            panic!("missing write effect must be rejected: {outcome:?}");
        };
        assert_eq!(issue.rule(), SemanticRuleV0_14::Eff2);
    });
}

#[test]
fn borrowed_buffer_length_exhibits_a_read_of_its_storage_origin() {
    let source = br#"fn length ['r](values: &'r buffer<u8>) -> own u64 reads('r) {
  return len<u8>(deref(values));
}

fn main() -> own unit pure {
  return unit;
}
"#;
    with_semantics(source, |outcome| {
        let SemanticOutcome::Complete(_) = outcome else {
            panic!("borrowed length must exhibit its incoming region read: {outcome:?}");
        };
    });
}

#[test]
fn live_buffer_loans_reject_overlapping_borrows_and_owner_writes() {
    assert_rule(
        br#"fn main() -> own unit allocates(heap), traps {
  let values: own buffer<u8> = buffer_new<u8>(1_u64, 0_u8);
  region 'r {
    let first: &uniq 'r buffer<u8> = &uniq 'r values;
    let second: &uniq 'r buffer<u8> = &uniq 'r values;
  }
  return unit;
}
"#,
        SemanticRuleV0_14::Own5,
        SemanticIssueKind::BorrowConflict,
    );
    assert_rule(
        br#"fn main() -> own unit allocates(heap), traps {
  let values: own buffer<u8> = buffer_new<u8>(1_u64, 0_u8);
  region 'r {
    let shared: &'r buffer<u8> = &'r values;
    set index<u8>(values, 0_u64) = 1_u8;
  }
  return unit;
}
"#,
        SemanticRuleV0_14::Own5,
        SemanticIssueKind::BorrowConflict,
    );
}

#[test]
fn user_calls_reject_overlapping_unique_arguments() {
    assert_rule(
        br#"fn two ['r](first: &uniq 'r buffer<u8>, second: &uniq 'r buffer<u8>) -> own unit pure {
  return unit;
}

fn main() -> own unit allocates(heap), traps {
  let values: own buffer<u8> = buffer_new<u8>(1_u64, 0_u8);
  region 'r {
    two<'r>(first: &uniq 'r values, second: &uniq 'r values);
  }
  return unit;
}
"#,
        SemanticRuleV0_14::Own12,
        SemanticIssueKind::BorrowConflict,
    );
}

#[test]
fn own_storage_cannot_be_borrowed_into_a_caller_region() {
    assert_rule(
        br#"fn invalid ['caller](values: own buffer<u8>) -> own unit pure {
  let escaped: &'caller buffer<u8> = &'caller values;
  return unit;
}

fn main() -> own unit pure {
  return unit;
}
"#,
        SemanticRuleV0_14::Own10,
        SemanticIssueKind::InvalidBorrowLifetime,
    );
}

#[test]
fn call_effects_preserve_the_incoming_storage_origin() {
    let source = br#"fn write ['r](out: &uniq 'r buffer<u8>) -> own unit writes('r), traps {
  set index<u8>(deref(out), 0_u64) = 1_u8;
  return unit;
}

fn proxy ['r](out: &uniq 'r buffer<u8>) -> own unit writes('r), traps {
  write<'r>(out: move out);
  return unit;
}

fn main() -> own unit pure {
  return unit;
}
"#;
    with_semantics(source, |outcome| {
        let SemanticOutcome::Complete(checked) = outcome else {
            panic!("incoming call effects must retain their formal origin: {outcome:?}");
        };
        assert!(checked.data.functions[1].declared_traps);
    });
}
