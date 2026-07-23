use std::collections::HashMap;

use crate::syntax::NodeId;
use crate::{DeclarationId, SemanticIssueKind, SemanticRule};

use super::super::super::super::model::{
    CheckedExpression, CheckedFloatOperation, CheckedMode, CheckedType,
};
use super::super::super::{
    CheckStop, Checker, EffectSet, FunctionSignature, LocalBinding, TypedExpression,
};

pub(super) fn is_float_operation(spelling: &str) -> bool {
    float_operation(spelling).is_some()
}

fn float_operation(spelling: &str) -> Option<CheckedFloatOperation> {
    Some(match spelling {
        "fadd.strict" => CheckedFloatOperation::AddStrict,
        "fsub.strict" => CheckedFloatOperation::SubtractStrict,
        "fmul.strict" => CheckedFloatOperation::MultiplyStrict,
        "fdiv.strict" => CheckedFloatOperation::DivideStrict,
        "feq" => CheckedFloatOperation::Equal,
        "flt" => CheckedFloatOperation::Less,
        "fle" => CheckedFloatOperation::LessEqual,
        "fgt" => CheckedFloatOperation::Greater,
        "fge" => CheckedFloatOperation::GreaterEqual,
        "fne" => CheckedFloatOperation::NotEqual,
        "fneg" => CheckedFloatOperation::Negate,
        "fabs" => CheckedFloatOperation::Absolute,
        "fcopysign" => CheckedFloatOperation::CopySign,
        "fmin" => CheckedFloatOperation::Minimum,
        "fmax" => CheckedFloatOperation::Maximum,
        "ffloor" => CheckedFloatOperation::Floor,
        "fceil" => CheckedFloatOperation::Ceil,
        "ftrunc" => CheckedFloatOperation::Truncate,
        "froundeven" => CheckedFloatOperation::RoundEven,
        "frem" => CheckedFloatOperation::Remainder,
        "fsqrt.strict" => CheckedFloatOperation::SquareRootStrict,
        "ffma.strict" => CheckedFloatOperation::FusedMultiplyAddStrict,
        "finf" => CheckedFloatOperation::Infinity,
        "fnan" => CheckedFloatOperation::Nan,
        _ => return None,
    })
}

impl<'unit, 'classified, 'lexed, 'source> Checker<'unit, 'classified, 'lexed, 'source> {
    pub(super) fn check_float_operation(
        &self,
        node: NodeId,
        spelling: &str,
        function: &FunctionSignature,
        bindings: &mut HashMap<DeclarationId, LocalBinding>,
        loop_depth: usize,
    ) -> Result<TypedExpression, CheckStop> {
        let operation = float_operation(spelling)
            .expect("caller dispatches only closed floating-point operation names");
        let operand_type = self.operation_type_argument(node, spelling, function)?;
        if !matches!(
            operand_type,
            CheckedType::Float(_) | CheckedType::GenericFloat(_)
        ) {
            return self.issue_node(SemanticRule::Op1, node, SemanticIssueKind::InvalidOperation);
        }
        let atoms = self.operation_atoms(node, operation.operand_count())?;
        let mut arguments = Vec::with_capacity(atoms.len());
        let mut effects = EffectSet::NONE;
        for atom in atoms {
            let argument = self.check_atom(function, atom, bindings, loop_depth)?;
            if argument.mode != CheckedMode::Own || argument.expression.ty() != operand_type {
                return self.issue_node(SemanticRule::Type5, atom, SemanticIssueKind::TypeMismatch);
            }
            effects = effects.union(argument.effects);
            arguments.push(argument.expression);
        }
        Ok(TypedExpression::owned(
            CheckedExpression::FloatOperation {
                operation,
                operand_type,
                arguments,
            },
            effects,
        ))
    }
}
