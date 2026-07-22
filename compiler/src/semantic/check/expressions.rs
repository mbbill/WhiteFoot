mod calls;

use std::collections::HashMap;

use crate::syntax::NodeId;
use crate::syntax::terminal::{FixedTerminalV0_11, TerminalPredicateV0_11};
use crate::{
    DeclarationClass, DeclarationId, DeferredUseRole, LexicalUseRole, ProductionV0_11,
    ResolvedTarget, SemanticCompilerFailure, SemanticIssueKind, SemanticRuleV0_11,
    UnsupportedSemanticFeatureV0_11,
};

use super::super::model::{
    CheckedExpression, CheckedNominalKind, CheckedProjectedDrop, CheckedType, CheckedValue,
};
use super::{CheckStop, Checker, Constructor, FunctionSignature, LocalBinding, TypedExpression};

impl<'unit, 'classified, 'lexed, 'source> Checker<'unit, 'classified, 'lexed, 'source> {
    pub(super) fn check_expression(
        &self,
        function: &FunctionSignature,
        node: NodeId,
        bindings: &mut HashMap<DeclarationId, LocalBinding>,
    ) -> Result<TypedExpression, CheckStop> {
        let child = self.tree.only_child(node)?;
        match self.tree.production(child)? {
            ProductionV0_11::Atom => self.check_atom(function, child, bindings),
            ProductionV0_11::Call => self.check_call(function, child, bindings),
            ProductionV0_11::Construct => self.check_construct(function, child, bindings),
            _ => Err(SemanticCompilerFailure::InvalidCanonicalTree.into()),
        }
    }

    pub(super) fn check_atom(
        &self,
        function: &FunctionSignature,
        node: NodeId,
        bindings: &mut HashMap<DeclarationId, LocalBinding>,
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
            let value = self.check_place_use(
                node,
                place,
                bindings,
                self.has_fixed(node, FixedTerminalV0_11::Move)?,
                false,
            )?;
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

    fn check_place_use(
        &self,
        use_node: NodeId,
        node: NodeId,
        bindings: &mut HashMap<DeclarationId, LocalBinding>,
        explicit_move: bool,
        match_scrutinee: bool,
    ) -> Result<CheckedExpression, CheckStop> {
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
                let local = *bindings
                    .get(&declaration)
                    .ok_or(SemanticCompilerFailure::InvalidResolution)?;
                if !local.live {
                    return self.issue_node(
                        SemanticRuleV0_11::Own1,
                        use_node,
                        SemanticIssueKind::UseAfterMove {
                            mechanical_fix: "introduce a new `let` binding before reuse",
                        },
                    );
                }
                let mut ty = local.ty;
                let mut fields = Vec::new();
                let mut residual_drops = Vec::new();
                for suffix in self.tree.children_with(node, ProductionV0_11::Psuffix)? {
                    let name = self
                        .deferred_use_at(suffix, DeferredUseRole::ProjectedField)?
                        .spelling();
                    let CheckedType::Nominal(nominal_id) = ty else {
                        return self.issue_node(
                            SemanticRuleV0_11::Type5,
                            suffix,
                            SemanticIssueKind::TypeMismatch,
                        );
                    };
                    let CheckedNominalKind::Struct {
                        fields: declared_fields,
                    } = &self.nominal(nominal_id)?.kind
                    else {
                        return self.issue_node(
                            SemanticRuleV0_11::Type5,
                            suffix,
                            SemanticIssueKind::TypeMismatch,
                        );
                    };
                    let Some((index, field)) = declared_fields
                        .iter()
                        .enumerate()
                        .find(|(_, field)| field.name == name)
                    else {
                        return self.issue_node(
                            SemanticRuleV0_11::Type5,
                            suffix,
                            SemanticIssueKind::TypeMismatch,
                        );
                    };
                    for (sibling_index, sibling) in declared_fields.iter().enumerate().rev() {
                        if sibling_index != index && !self.is_copy_type(sibling.ty)? {
                            let mut sibling_path = fields.clone();
                            sibling_path.push(
                                u32::try_from(sibling_index)
                                    .map_err(|_| SemanticCompilerFailure::CounterOverflow)?,
                            );
                            residual_drops.push(CheckedProjectedDrop {
                                fields: sibling_path,
                                ty: sibling.ty,
                            });
                        }
                    }
                    fields.push(
                        u32::try_from(index)
                            .map_err(|_| SemanticCompilerFailure::CounterOverflow)?,
                    );
                    ty = field.ty;
                }
                let copy = self.is_copy_type(ty)?;
                if explicit_move && copy {
                    return self.issue_node(
                        SemanticRuleV0_11::Own1,
                        use_node,
                        SemanticIssueKind::MoveOfCopy {
                            mechanical_fix: "use the copy place without `move`",
                        },
                    );
                }
                if !copy && !explicit_move && !match_scrutinee {
                    return self.issue_node(
                        SemanticRuleV0_11::Own1,
                        use_node,
                        SemanticIssueKind::BareAffineUse {
                            mechanical_fix: "write `move p` for the affine place",
                        },
                    );
                }
                if !copy {
                    bindings
                        .get_mut(&declaration)
                        .ok_or(SemanticCompilerFailure::InvalidResolution)?
                        .live = false;
                }
                if fields.is_empty() {
                    Ok(CheckedExpression::Binding {
                        binding: local.binding,
                        ty,
                    })
                } else {
                    Ok(CheckedExpression::Project {
                        binding: local.binding,
                        fields,
                        ty,
                        consume_root: !copy,
                        residual_drops: if copy { Vec::new() } else { residual_drops },
                    })
                }
            }
            DeclarationClass::NamedConst => {
                if explicit_move {
                    return self.issue_node(
                        SemanticRuleV0_11::Own1,
                        use_node,
                        SemanticIssueKind::MoveOfCopy {
                            mechanical_fix: "use the copy place without `move`",
                        },
                    );
                }
                if !self
                    .tree
                    .children_with(node, ProductionV0_11::Psuffix)?
                    .is_empty()
                {
                    return self
                        .unsupported(UnsupportedSemanticFeatureV0_11::CompositeValues, node);
                }
                self.constants
                    .get(&declaration)
                    .copied()
                    .map(CheckedExpression::Constant)
                    .ok_or(SemanticCompilerFailure::InvalidResolution.into())
            }
            _ => Err(SemanticCompilerFailure::InvalidResolution.into()),
        }
    }

    pub(super) fn check_match_expression(
        &self,
        function: &FunctionSignature,
        node: NodeId,
        bindings: &mut HashMap<DeclarationId, LocalBinding>,
    ) -> Result<TypedExpression, CheckStop> {
        let child = self.tree.only_child(node)?;
        if self.tree.production(child)? == ProductionV0_11::Atom
            && let Some(place) = self.tree.first_child_with(child, ProductionV0_11::Place)?
        {
            return Ok(TypedExpression {
                expression: self.check_place_use(
                    child,
                    place,
                    bindings,
                    self.has_fixed(child, FixedTerminalV0_11::Move)?,
                    true,
                )?,
                exhibits_traps: false,
            });
        }
        self.check_expression(function, node, bindings)
    }

    pub(super) fn check_construct(
        &self,
        function: &FunctionSignature,
        node: NodeId,
        bindings: &mut HashMap<DeclarationId, LocalBinding>,
    ) -> Result<TypedExpression, CheckStop> {
        if let Some(targs) = self.tree.first_child_with(node, ProductionV0_11::Targs)? {
            return self.unsupported(UnsupportedSemanticFeatureV0_11::Generics, targs);
        }
        let usage = self.use_at(node, LexicalUseRole::Construct)?;
        let constructor_name = usage.spelling().to_owned();
        if let ResolvedTarget::Prelude(id) = usage.target() {
            let value = match id.ordinal() {
                1 => CheckedValue::Bool(true),
                2 => CheckedValue::Bool(false),
                _ => {
                    return self
                        .unsupported(UnsupportedSemanticFeatureV0_11::PreludeNominalValues, node);
                }
            };
            if self
                .tree
                .first_child_with(node, ProductionV0_11::FieldinitList)?
                .is_some()
            {
                return self.issue_node(
                    SemanticRuleV0_11::Gram8,
                    node,
                    SemanticIssueKind::InvalidConstructionFields {
                        constructor: constructor_name,
                        declared_fields: Vec::new(),
                    },
                );
            }
            return Ok(TypedExpression {
                expression: CheckedExpression::Constant(value),
                exhibits_traps: false,
            });
        }
        let ResolvedTarget::Source { declaration, .. } = usage.target() else {
            return Err(SemanticCompilerFailure::InvalidResolution.into());
        };
        let constructor = *self
            .constructors_by_declaration
            .get(&declaration)
            .ok_or(SemanticCompilerFailure::InvalidResolution)?;
        let declared_fields = match constructor {
            Constructor::Struct(nominal) => match &self.nominal(nominal)?.kind {
                CheckedNominalKind::Struct { fields } => fields.clone(),
                _ => return Err(SemanticCompilerFailure::InvalidResolution.into()),
            },
            Constructor::Enum { nominal, variant } => match &self.nominal(nominal)?.kind {
                CheckedNominalKind::Enum { variants } => variants
                    .get(variant as usize)
                    .ok_or(SemanticCompilerFailure::InvalidResolution)?
                    .fields
                    .clone(),
                _ => return Err(SemanticCompilerFailure::InvalidResolution.into()),
            },
        };
        let written_fields = if let Some(list) = self
            .tree
            .first_child_with(node, ProductionV0_11::FieldinitList)?
        {
            self.tree.children_with(list, ProductionV0_11::Fieldinit)?
        } else {
            Vec::new()
        };
        let declared_field_names = declared_fields
            .iter()
            .map(|field| field.name.clone())
            .collect::<Vec<_>>();
        if written_fields.len() != declared_fields.len() {
            return self.issue_node(
                SemanticRuleV0_11::Gram8,
                node,
                SemanticIssueKind::InvalidConstructionFields {
                    constructor: constructor_name,
                    declared_fields: declared_field_names,
                },
            );
        }
        let mut fields = Vec::with_capacity(written_fields.len());
        let mut exhibits_traps = false;
        for (written, declared) in written_fields.into_iter().zip(&declared_fields) {
            if self
                .deferred_use_at(written, DeferredUseRole::FieldInitializer)?
                .spelling()
                != declared.name
            {
                return self.issue_node(
                    SemanticRuleV0_11::Gram8,
                    written,
                    SemanticIssueKind::InvalidConstructionFields {
                        constructor: constructor_name,
                        declared_fields: declared_field_names,
                    },
                );
            }
            let atom = self
                .tree
                .first_child_with(written, ProductionV0_11::Atom)?
                .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
            let value = self.check_atom(function, atom, bindings)?;
            if value.expression.ty() != declared.ty {
                return self.issue_node(
                    SemanticRuleV0_11::Type5,
                    atom,
                    SemanticIssueKind::TypeMismatch,
                );
            }
            exhibits_traps |= value.exhibits_traps;
            fields.push(value.expression);
        }
        let expression = match constructor {
            Constructor::Struct(nominal) => CheckedExpression::ConstructStruct { nominal, fields },
            Constructor::Enum { nominal, variant } => CheckedExpression::ConstructEnum {
                nominal,
                variant,
                fields,
            },
        };
        Ok(TypedExpression {
            expression,
            exhibits_traps,
        })
    }
}
