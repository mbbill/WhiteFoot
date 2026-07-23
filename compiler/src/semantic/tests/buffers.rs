use crate::{
    SemanticIssueKind, SemanticOutcome, SemanticRuleV0_14, UnsupportedSemanticFeatureV0_14,
};

use super::super::model::{
    CheckedExpression, CheckedFlatElement, CheckedSetTarget, CheckedStatement, CheckedType,
    IntegerType,
};
use super::{assert_rule, with_semantics};

#[test]
fn primitive_buffers_retain_allocation_checks_accesses_and_cleanup() {
    let source = br#"fn make(n: own u64) -> own buffer<u16> allocates(heap), traps {
  return buffer_new<u16>(n, 3_u16);
}

fn main() -> own unit allocates(heap), traps {
  let values: own buffer<u16> = make(n: 4_u64);
  set index<u16>(values, 2_u64) = 9_u16;
  let length: own u64 = len<u16>(values);
  let stored: own u16 = index<u16>(values, 2_u64);
  check ieq<u64>(length, 4_u64) else trap "length drift";
  check ieq<u16>(stored, 9_u16) else trap "store drift";
  return unit;
}
"#;
    with_semantics(source, |outcome| {
        let SemanticOutcome::Complete(checked) = outcome else {
            panic!("primitive buffer family must check: {outcome:?}");
        };
        let make = &checked.data.functions[0];
        assert!(make.declared_allocates_heap);
        assert!(make.declared_traps);
        assert!(matches!(
            &make.body[0],
            CheckedStatement::Return {
                value: CheckedExpression::BufferFill {
                    element: CheckedFlatElement::Integer(IntegerType::U16),
                    trap,
                    ..
                },
                ..
            } if trap.rule_id == "OP-9"
        ));

        let main = &checked.data.functions[1];
        let CheckedStatement::Set { target, .. } = &main.body[1] else {
            panic!("second main statement must be indexed SET-1");
        };
        let CheckedSetTarget::BufferIndex(target) = target else {
            panic!("SET-1 target must retain its buffer root and OP-4 check");
        };
        assert_eq!(
            target.root.element,
            CheckedFlatElement::Integer(IntegerType::U16)
        );
        assert_eq!(target.trap.rule_id, "OP-4");
        assert!(matches!(
            &main.body[2],
            CheckedStatement::Let {
                value: CheckedExpression::BufferLength { .. },
                ..
            }
        ));
        assert!(matches!(
            &main.body[3],
            CheckedStatement::Let {
                value: CheckedExpression::BufferIndex { trap, .. },
                ..
            } if trap.rule_id == "OP-4"
        ));
        let CheckedStatement::Return { drops, .. } = &main.body[6] else {
            panic!("main must end in return");
        };
        assert_eq!(drops.len(), 1);
        assert_eq!(
            drops[0].ty,
            CheckedType::Buffer {
                element: CheckedFlatElement::Integer(IntegerType::U16),
            }
        );
    });
}

#[test]
fn buffer_effect_rows_are_checked_both_ways() {
    assert_rule(
        b"fn main() -> own unit traps {\n  let values: own buffer<u8> = buffer_new<u8>(2_u64, 0_u8);\n  return unit;\n}\n",
        SemanticRuleV0_14::Eff2,
        SemanticIssueKind::EffectMismatch,
    );
    assert_rule(
        b"fn main() -> own unit allocates(heap) {\n  let values: own buffer<u8> = buffer_new<u8>(2_u64, 0_u8);\n  return unit;\n}\n",
        SemanticRuleV0_14::Eff2,
        SemanticIssueKind::EffectMismatch,
    );
    assert_rule(
        b"fn main() -> own unit allocates(heap), traps {\n  return unit;\n}\n",
        SemanticRuleV0_14::Eff2,
        SemanticIssueKind::EffectMismatch,
    );
}

#[test]
fn buffer_new_keeps_its_primitive_only_operation_domain() {
    assert_rule(
        b"fn main() -> own unit allocates(heap), traps {\n  let initial: own Bool = False();\n  let values: own buffer<Bool> = buffer_new<Bool>(2_u64, initial);\n  return unit;\n}\n",
        SemanticRuleV0_14::Op1,
        SemanticIssueKind::InvalidOperation,
    );

    with_semantics(
        b"struct Holder {\n  values: buffer<u8>;\n}\n\nfn main() -> own unit pure {\n  return unit;\n}\n",
        |outcome| {
            let SemanticOutcome::Unsupported { unsupported } = outcome else {
                panic!("nested buffer cleanup must remain explicit unsupported: {outcome:?}");
            };
            assert_eq!(
                unsupported.feature(),
                UnsupportedSemanticFeatureV0_14::CompositeValues
            );
        },
    );
}
