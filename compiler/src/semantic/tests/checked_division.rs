use crate::SemanticOutcome;

use super::super::model::{
    CheckedExpression, CheckedIntegerOperation, CheckedStatement, CheckedType,
};
use super::with_semantics;

#[test]
fn produces_div_error_results() {
    let source = br#"fn main() -> own unit pure {
  let quotient: own Result<i32, DivError> = idiv.checked<i32>(-2147483648_i32, -1_i32);
  let remainder: own Result<u64, DivError> = irem.checked<u64>(42_u64, 5_u64);
  return unit;
}
"#;
    with_semantics(source, |outcome| {
        let SemanticOutcome::Complete(checked) = outcome else {
            panic!("checked division family must check: {outcome:?}");
        };
        let body = &checked.data.functions[0].body;
        let [
            CheckedStatement::Let {
                value:
                    CheckedExpression::IntegerOperation {
                        operation: CheckedIntegerOperation::DivideChecked,
                        result: CheckedType::Nominal(quotient_result),
                        ..
                    },
                ..
            },
            CheckedStatement::Let {
                value:
                    CheckedExpression::IntegerOperation {
                        operation: CheckedIntegerOperation::RemainderChecked,
                        result: CheckedType::Nominal(remainder_result),
                        ..
                    },
                ..
            },
            CheckedStatement::Return { .. },
        ] = body.as_slice()
        else {
            panic!("checked division and remainder must retain distinct operations");
        };
        assert_eq!(
            checked.data.nominals[quotient_result.0 as usize].name,
            "Result<i32, DivError>"
        );
        assert_eq!(
            checked.data.nominals[remainder_result.0 as usize].name,
            "Result<u64, DivError>"
        );
    });
}
