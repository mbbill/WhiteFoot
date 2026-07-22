use std::collections::HashMap;

use crate::syntax::NodeId;
use crate::syntax::terminal::{FixedTerminalV0_11, TerminalPredicateV0_11};
use crate::{
    DeclarationClass, DeclarationId, LexicalUseRole, ProductionV0_11, ResolvedTarget,
    SemanticCompilerFailure, SemanticIssueKind, SemanticRuleV0_11, UnsupportedSemanticFeatureV0_11,
};

use super::super::model::{
    CheckedExpression, CheckedIntegerOperation, CheckedType, CheckedValue, TrapSite,
};
use super::{CheckStop, Checker, FunctionSignature, LocalBinding, TypedExpression};

impl<'unit, 'classified, 'lexed, 'source> Checker<'unit, 'classified, 'lexed, 'source> {
    pub(super) fn check_expression(
        &self,
        function: &FunctionSignature,
        node: NodeId,
        bindings: &HashMap<DeclarationId, LocalBinding>,
    ) -> Result<TypedExpression, CheckStop> {
        let child = self.tree.only_child(node)?;
        match self.tree.production(child)? {
            ProductionV0_11::Atom => self.check_atom(function, child, bindings),
            ProductionV0_11::Call => self.check_call(function, child, bindings),
            ProductionV0_11::Construct => self.check_construct(child),
            _ => Err(SemanticCompilerFailure::InvalidCanonicalTree.into()),
        }
    }

    pub(super) fn check_atom(
        &self,
        function: &FunctionSignature,
        node: NodeId,
        bindings: &HashMap<DeclarationId, LocalBinding>,
    ) -> Result<TypedExpression, CheckStop> {
        if let Some(literal) = self
            .tree
            .direct_token_with(node, TerminalPredicateV0_11::Literal)?
        {
            return Ok(TypedExpression {
                expression: CheckedExpression::Constant(
                    self.parse_literal(node, self.tree.token_bytes(literal)?)?,
                ),
                exhibits_traps: false,
            });
        }
        if let Some(place) = self.tree.first_child_with(node, ProductionV0_11::Place)? {
            let value = self.check_place(place, bindings)?;
            if self.has_fixed(node, FixedTerminalV0_11::Move)? {
                return self.issue_node(
                    SemanticRuleV0_11::Own1,
                    node,
                    SemanticIssueKind::MoveOfCopy,
                );
            }
            return Ok(TypedExpression {
                expression: value,
                exhibits_traps: false,
            });
        }
        if let Some(borrow) = self
            .tree
            .first_child_with(node, ProductionV0_11::BorrowExpr)?
        {
            return self.unsupported(UnsupportedSemanticFeatureV0_11::RegionsAndBorrows, borrow);
        }
        let _ = function;
        Err(SemanticCompilerFailure::InvalidCanonicalTree.into())
    }

    pub(super) fn check_place(
        &self,
        node: NodeId,
        bindings: &HashMap<DeclarationId, LocalBinding>,
    ) -> Result<CheckedExpression, CheckStop> {
        if !self
            .tree
            .children_with(node, ProductionV0_11::Psuffix)?
            .is_empty()
        {
            return self.unsupported(UnsupportedSemanticFeatureV0_11::CompositeValues, node);
        }
        let pbase = self
            .tree
            .first_child_with(node, ProductionV0_11::Pbase)?
            .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
        if !self.tree.children(pbase)?.is_empty() {
            return self.unsupported(UnsupportedSemanticFeatureV0_11::CompositeValues, pbase);
        }
        let usage = self.use_at(pbase, LexicalUseRole::PlaceBase)?;
        let ResolvedTarget::Source { declaration, class } = usage.target() else {
            return Err(SemanticCompilerFailure::InvalidResolution.into());
        };
        match class {
            DeclarationClass::Value => {
                let local = bindings
                    .get(&declaration)
                    .ok_or(SemanticCompilerFailure::InvalidResolution)?;
                Ok(CheckedExpression::Binding {
                    binding: local.binding,
                    ty: local.ty,
                })
            }
            DeclarationClass::NamedConst => self
                .constants
                .get(&declaration)
                .copied()
                .map(CheckedExpression::Constant)
                .ok_or(SemanticCompilerFailure::InvalidResolution.into()),
            _ => Err(SemanticCompilerFailure::InvalidResolution.into()),
        }
    }

    pub(super) fn check_construct(&self, node: NodeId) -> Result<TypedExpression, CheckStop> {
        if self
            .tree
            .first_child_with(node, ProductionV0_11::Targs)?
            .is_some()
            || self
                .tree
                .first_child_with(node, ProductionV0_11::FieldinitList)?
                .is_some()
        {
            return self.unsupported(UnsupportedSemanticFeatureV0_11::CompositeValues, node);
        }
        let usage = self.use_at(node, LexicalUseRole::Construct)?;
        let value = match usage.target() {
            ResolvedTarget::Prelude(id) if id.ordinal() == 1 => CheckedValue::Bool(true),
            ResolvedTarget::Prelude(id) if id.ordinal() == 2 => CheckedValue::Bool(false),
            _ => return self.unsupported(UnsupportedSemanticFeatureV0_11::CompositeValues, node),
        };
        Ok(TypedExpression {
            expression: CheckedExpression::Constant(value),
            exhibits_traps: false,
        })
    }

    pub(super) fn check_call(
        &self,
        function: &FunctionSignature,
        node: NodeId,
        bindings: &HashMap<DeclarationId, LocalBinding>,
    ) -> Result<TypedExpression, CheckStop> {
        let callee = self
            .tree
            .first_child_with(node, ProductionV0_11::Callee)?
            .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
        let callee_path = self.tree.path(callee)?;
        let usage = self
            .resolved
            .lexical_uses()
            .iter()
            .find(|usage| {
                usage.origin().node() == callee_path
                    && matches!(
                        usage.role(),
                        LexicalUseRole::IdentifierCallee | LexicalUseRole::OperationCallee
                    )
            })
            .ok_or(SemanticCompilerFailure::InvalidResolution)?;
        match usage.target() {
            ResolvedTarget::Source {
                declaration,
                class: DeclarationClass::Function,
            } => self.check_user_call(node, declaration, function, bindings),
            ResolvedTarget::Operation(operation) => {
                self.check_integer_operation(node, operation, function, bindings)
            }
            _ => Err(SemanticCompilerFailure::InvalidResolution.into()),
        }
    }

    pub(super) fn check_user_call(
        &self,
        node: NodeId,
        declaration: DeclarationId,
        function: &FunctionSignature,
        bindings: &HashMap<DeclarationId, LocalBinding>,
    ) -> Result<TypedExpression, CheckStop> {
        if let Some(targs) = self.tree.first_child_with(node, ProductionV0_11::Targs)? {
            return self.unsupported(UnsupportedSemanticFeatureV0_11::Generics, targs);
        }
        let target = *self
            .functions_by_declaration
            .get(&declaration)
            .ok_or(SemanticCompilerFailure::InvalidResolution)?;
        let signature = self
            .signatures
            .get(target.0 as usize)
            .ok_or(SemanticCompilerFailure::InvalidResolution)?;
        let fields = if let Some(list) = self
            .tree
            .first_child_with(node, ProductionV0_11::FieldinitList)?
        {
            self.tree.children_with(list, ProductionV0_11::Fieldinit)?
        } else {
            Vec::new()
        };
        if self
            .tree
            .first_child_with(node, ProductionV0_11::AtomList)?
            .is_some()
            || fields.len() != signature.parameters.len()
        {
            return self.issue_node(
                SemanticRuleV0_11::Gram11,
                node,
                SemanticIssueKind::InvalidNamedArguments,
            );
        }
        let mut arguments = Vec::with_capacity(fields.len());
        let mut exhibits_traps = signature.declared_traps;
        for (field, parameter) in fields.into_iter().zip(&signature.parameters) {
            let name = self.identifier(field)?;
            if name != parameter.name {
                return self.issue_node(
                    SemanticRuleV0_11::Gram11,
                    field,
                    SemanticIssueKind::InvalidNamedArguments,
                );
            }
            let atom = self
                .tree
                .first_child_with(field, ProductionV0_11::Atom)?
                .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
            let argument = self.check_atom(function, atom, bindings)?;
            if argument.expression.ty() != parameter.ty {
                return self.issue_node(
                    SemanticRuleV0_11::Type5,
                    atom,
                    SemanticIssueKind::TypeMismatch,
                );
            }
            exhibits_traps |= argument.exhibits_traps;
            arguments.push(argument.expression);
        }
        Ok(TypedExpression {
            expression: CheckedExpression::UserCall {
                function: target,
                arguments,
                result: signature.result,
            },
            exhibits_traps,
        })
    }

    pub(super) fn check_integer_operation(
        &self,
        node: NodeId,
        operation_id: crate::OperationFamilyId,
        function: &FunctionSignature,
        bindings: &HashMap<DeclarationId, LocalBinding>,
    ) -> Result<TypedExpression, CheckStop> {
        let spelling = crate::operation_family_spelling_v0_11(operation_id)
            .ok_or(SemanticCompilerFailure::InvalidResolution)?;
        let operation = match spelling {
            "iadd.wrap" => CheckedIntegerOperation::AddWrap,
            "isub.wrap" => CheckedIntegerOperation::SubtractWrap,
            "imul.wrap" => CheckedIntegerOperation::MultiplyWrap,
            "iadd.trap" => CheckedIntegerOperation::AddTrap,
            "isub.trap" => CheckedIntegerOperation::SubtractTrap,
            "imul.trap" => CheckedIntegerOperation::MultiplyTrap,
            "ieq" => CheckedIntegerOperation::Equal,
            "ine" => CheckedIntegerOperation::NotEqual,
            "ilt" => CheckedIntegerOperation::Less,
            "ile" => CheckedIntegerOperation::LessEqual,
            "igt" => CheckedIntegerOperation::Greater,
            "ige" => CheckedIntegerOperation::GreaterEqual,
            _ => {
                return self.unsupported(UnsupportedSemanticFeatureV0_11::OperationFamily, node);
            }
        };
        if self
            .tree
            .first_child_with(node, ProductionV0_11::FieldinitList)?
            .is_some()
        {
            return self.issue_node(
                SemanticRuleV0_11::Gram11,
                node,
                SemanticIssueKind::InvalidNamedArguments,
            );
        }
        let targs = self
            .tree
            .first_child_with(node, ProductionV0_11::Targs)?
            .ok_or_else(|| {
                self.issue_value(
                    SemanticRuleV0_11::Fn2,
                    node,
                    SemanticIssueKind::InvalidOperation,
                )
            })?;
        let targs = self.tree.children_with(targs, ProductionV0_11::Targ)?;
        if targs.len() != 1 {
            return self.issue_node(
                SemanticRuleV0_11::Op1,
                node,
                SemanticIssueKind::InvalidOperation,
            );
        }
        let type_node = self
            .tree
            .first_child_with(targs[0], ProductionV0_11::Type)?
            .ok_or_else(|| {
                self.issue_value(
                    SemanticRuleV0_11::Op1,
                    node,
                    SemanticIssueKind::InvalidOperation,
                )
            })?;
        let Some(operand_type) = self.integer_type(type_node)? else {
            return self.issue_node(
                SemanticRuleV0_11::Op1,
                node,
                SemanticIssueKind::InvalidOperation,
            );
        };
        let list = self
            .tree
            .first_child_with(node, ProductionV0_11::AtomList)?
            .ok_or_else(|| {
                self.issue_value(
                    SemanticRuleV0_11::Op1,
                    node,
                    SemanticIssueKind::InvalidOperation,
                )
            })?;
        let atoms = self.tree.children_with(list, ProductionV0_11::Atom)?;
        if atoms.len() < 2 {
            return self.issue_node(
                SemanticRuleV0_11::Op1,
                node,
                SemanticIssueKind::InvalidOperation,
            );
        }
        if atoms.len() > 2 {
            return self.issue_node(
                SemanticRuleV0_11::Op1,
                atoms[2],
                SemanticIssueKind::InvalidOperation,
            );
        }
        let mut arguments = Vec::with_capacity(2);
        let mut exhibits_traps = operation.traps();
        for atom in atoms {
            let argument = self.check_atom(function, atom, bindings)?;
            if argument.expression.ty() != CheckedType::Integer(operand_type) {
                return self.issue_node(
                    SemanticRuleV0_11::Type5,
                    atom,
                    SemanticIssueKind::TypeMismatch,
                );
            }
            exhibits_traps |= argument.exhibits_traps;
            arguments.push(argument.expression);
        }
        let trap = if operation.traps() {
            Some(TrapSite {
                rule_id: "OP-2",
                message: "integer overflow".to_owned(),
                function: function.name.clone(),
                node_path: self.tree.path(node)?.clone(),
            })
        } else {
            None
        };
        Ok(TypedExpression {
            expression: CheckedExpression::IntegerOperation {
                operation,
                operand_type,
                arguments,
                trap,
            },
            exhibits_traps,
        })
    }
}
