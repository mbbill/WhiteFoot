use std::collections::HashMap;

use crate::syntax::NodeId;
use crate::{
    DeclarationClass, DeclarationId, DeclarationRole, LexicalUseRole, ProductionV0_14,
    ResolvedTarget, ScopeId, SemanticCompilerFailure, SemanticIssueKind, SemanticRuleV0_14,
    UnsupportedSemanticFeatureV0_14,
};

use super::super::model::{
    CheckedBufferRoot, CheckedExpression, CheckedMode, CheckedNominalKind, CheckedType,
};
use super::{
    CheckStop, Checker, EffectSet, FunctionSignature, LocalBinding, ParameterSignature,
    TypedExpression,
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) enum BorrowKind {
    Shared,
    Unique,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(super) struct ResolvedPlace {
    pub(super) root: DeclarationId,
    pub(super) fields: Vec<u32>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(super) struct BorrowInfo {
    pub(super) kind: BorrowKind,
    pub(super) region: DeclarationId,
    pub(super) place: ResolvedPlace,
    pub(super) origin_region: Option<DeclarationId>,
}

#[derive(Clone, Copy)]
pub(super) enum AccessKind {
    Read,
    Write,
    Move,
    SharedBorrow,
    UniqueBorrow,
}

impl BorrowInfo {
    pub(super) const fn mode(&self) -> CheckedMode {
        match self.kind {
            BorrowKind::Shared => CheckedMode::Shared(self.region),
            BorrowKind::Unique => CheckedMode::Unique(self.region),
        }
    }
}

impl<'unit, 'classified, 'lexed, 'source> Checker<'unit, 'classified, 'lexed, 'source> {
    pub(super) fn parse_region_parameters(
        &self,
        function: NodeId,
    ) -> Result<Vec<DeclarationId>, CheckStop> {
        let Some(node) = self
            .tree
            .first_child_with(function, ProductionV0_14::RegionParams)?
        else {
            return Ok(Vec::new());
        };
        let path = self.tree.path(node)?;
        let mut declarations = self
            .resolved
            .declarations()
            .iter()
            .filter(|declaration| {
                declaration.role() == DeclarationRole::RegionParameter
                    && declaration.origin().node() == path
            })
            .collect::<Vec<_>>();
        declarations.sort_by_key(|declaration| declaration.origin().role_ordinal());
        Ok(declarations
            .into_iter()
            .map(|declaration| declaration.id())
            .collect())
    }

    pub(super) fn parse_mode(&self, node: NodeId) -> Result<CheckedMode, CheckStop> {
        if self.has_fixed(node, crate::FixedTerminalV0_14::Own)? {
            return Ok(CheckedMode::Own);
        }
        let usage = self.use_at(node, LexicalUseRole::ModeRegion)?;
        let ResolvedTarget::Source {
            declaration,
            class: DeclarationClass::Region,
        } = usage.target()
        else {
            return Err(SemanticCompilerFailure::InvalidResolution.into());
        };
        Ok(if self.has_fixed(node, crate::FixedTerminalV0_14::Uniq)? {
            CheckedMode::Unique(declaration)
        } else {
            CheckedMode::Shared(declaration)
        })
    }

    pub(super) fn parameter_borrow(&self, parameter: &ParameterSignature) -> Option<BorrowInfo> {
        let (kind, region) = match parameter.mode {
            CheckedMode::Own => return None,
            CheckedMode::Shared(region) => (BorrowKind::Shared, region),
            CheckedMode::Unique(region) => (BorrowKind::Unique, region),
        };
        Some(BorrowInfo {
            kind,
            region,
            place: ResolvedPlace {
                root: parameter.declaration,
                fields: Vec::new(),
            },
            origin_region: Some(region),
        })
    }

    pub(super) fn check_borrow(
        &self,
        node: NodeId,
        function: &FunctionSignature,
        bindings: &HashMap<DeclarationId, LocalBinding>,
        loop_depth: usize,
    ) -> Result<TypedExpression, CheckStop> {
        if loop_depth != 0 {
            return self.unsupported(UnsupportedSemanticFeatureV0_14::RegionsAndBorrows, node);
        }
        let usage = self.use_at(node, LexicalUseRole::BorrowRegion)?;
        let ResolvedTarget::Source {
            declaration: region,
            class: DeclarationClass::Region,
        } = usage.target()
        else {
            return Err(SemanticCompilerFailure::InvalidResolution.into());
        };
        let kind = if self.has_fixed(node, crate::FixedTerminalV0_14::Uniq)? {
            BorrowKind::Unique
        } else {
            BorrowKind::Shared
        };
        let place_node = self
            .tree
            .first_child_with(node, ProductionV0_14::Place)?
            .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
        let pbase = self
            .tree
            .first_child_with(place_node, ProductionV0_14::Pbase)?
            .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
        if !self.tree.children(pbase)?.is_empty() {
            return self.unsupported(UnsupportedSemanticFeatureV0_14::RegionsAndBorrows, pbase);
        }
        let root_use = self.use_at(pbase, LexicalUseRole::PlaceBase)?;
        let ResolvedTarget::Source {
            declaration,
            class: DeclarationClass::Value,
        } = root_use.target()
        else {
            return self.unsupported(
                UnsupportedSemanticFeatureV0_14::RegionsAndBorrows,
                place_node,
            );
        };
        let local = bindings
            .get(&declaration)
            .ok_or(SemanticCompilerFailure::InvalidResolution)?;
        if local.mode != CheckedMode::Own {
            return self.unsupported(
                UnsupportedSemanticFeatureV0_14::RegionsAndBorrows,
                place_node,
            );
        }
        if !local.live {
            return self.issue_node(
                SemanticRuleV0_14::Own1,
                place_node,
                SemanticIssueKind::UseAfterMove {
                    mechanical_fix: "introduce a new `let` binding before reuse",
                },
            );
        }
        if function.region_parameters.contains(&region)
            || !self.scope_is_within(
                self.region_declaration(region)?.scope(),
                self.declaration_scope(local.declaration)?,
            )?
        {
            return self.issue_node(
                SemanticRuleV0_14::Own10,
                node,
                SemanticIssueKind::InvalidBorrowLifetime,
            );
        }
        let (fields, ty) = self.resolve_struct_path(place_node, local.ty)?;
        let place = ResolvedPlace {
            root: declaration,
            fields: fields.clone(),
        };
        self.check_loan_access(
            bindings,
            None,
            &place,
            match kind {
                BorrowKind::Shared => AccessKind::SharedBorrow,
                BorrowKind::Unique => AccessKind::UniqueBorrow,
            },
            node,
        )?;
        let borrow = BorrowInfo {
            kind,
            region,
            place,
            origin_region: None,
        };
        let expression = match ty {
            CheckedType::Buffer { element } => CheckedExpression::BorrowBuffer {
                root: CheckedBufferRoot {
                    binding: local.binding,
                    fields,
                    element,
                },
            },
            CheckedType::Nominal(nominal)
                if fields.is_empty()
                    && matches!(
                        self.nominal(nominal)?.kind,
                        CheckedNominalKind::Struct { .. }
                    ) =>
            {
                CheckedExpression::BorrowStruct {
                    binding: local.binding,
                    nominal,
                }
            }
            _ => {
                return self.unsupported(
                    UnsupportedSemanticFeatureV0_14::RegionsAndBorrows,
                    place_node,
                );
            }
        };
        Ok(TypedExpression {
            expression,
            mode: borrow.mode(),
            borrow: Some(borrow),
            holder: None,
            effects: EffectSet::NONE,
            accesses: Vec::new(),
        })
    }

    pub(super) fn resolve_dereference_holder(
        &self,
        node: NodeId,
        pbase: NodeId,
        bindings: &HashMap<DeclarationId, LocalBinding>,
    ) -> Result<(DeclarationId, LocalBinding, BorrowInfo), CheckStop> {
        let holder_place = self
            .tree
            .first_child_with(pbase, ProductionV0_14::Place)?
            .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
        let holder_base = self
            .tree
            .first_child_with(holder_place, ProductionV0_14::Pbase)?
            .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
        if !self.tree.children(holder_base)?.is_empty()
            || !self
                .tree
                .children_with(holder_place, ProductionV0_14::Psuffix)?
                .is_empty()
        {
            return self.unsupported(
                UnsupportedSemanticFeatureV0_14::RegionsAndBorrows,
                holder_place,
            );
        }
        let usage = self.use_at(holder_base, LexicalUseRole::PlaceBase)?;
        let ResolvedTarget::Source {
            declaration,
            class: DeclarationClass::Value,
        } = usage.target()
        else {
            return Err(SemanticCompilerFailure::InvalidResolution.into());
        };
        let local = bindings
            .get(&declaration)
            .cloned()
            .ok_or(SemanticCompilerFailure::InvalidResolution)?;
        if !local.live {
            return self.issue_node(
                SemanticRuleV0_14::Own1,
                holder_place,
                SemanticIssueKind::UseAfterMove {
                    mechanical_fix: "introduce a new `let` binding before reuse",
                },
            );
        }
        let Some(borrow) = local.borrow.clone() else {
            return self.issue_node(
                SemanticRuleV0_14::Type7,
                node,
                SemanticIssueKind::MissingDereference {
                    mechanical_fix: "deref requires a borrow holder",
                },
            );
        };
        Ok((declaration, local, borrow))
    }

    pub(super) fn borrow_for_destination(
        &self,
        destination: CheckedMode,
        value: &TypedExpression,
        node: NodeId,
    ) -> Result<Option<BorrowInfo>, CheckStop> {
        if destination == CheckedMode::Own {
            if value.mode == CheckedMode::Own {
                return Ok(None);
            }
            return self.issue_node(
                SemanticRuleV0_14::Type7,
                node,
                SemanticIssueKind::MissingDereference {
                    mechanical_fix: "write `deref(holder)`",
                },
            );
        }
        let Some(mut borrow) = value.borrow.clone() else {
            return self.issue_node(
                SemanticRuleV0_14::Type5,
                node,
                SemanticIssueKind::TypeMismatch,
            );
        };
        let destination_region = match (destination, borrow.kind) {
            (CheckedMode::Shared(region), BorrowKind::Shared)
            | (CheckedMode::Unique(region), BorrowKind::Unique) => region,
            _ => {
                return self.issue_node(
                    SemanticRuleV0_14::Type5,
                    node,
                    SemanticIssueKind::TypeMismatch,
                );
            }
        };
        if !self.region_outlives(borrow.region, destination_region)? {
            return self.issue_node(
                SemanticRuleV0_14::Own4,
                node,
                SemanticIssueKind::InvalidBorrowLifetime,
            );
        }
        borrow.region = destination_region;
        Ok(Some(borrow))
    }

    pub(super) fn borrow_holder_scope_supported(
        &self,
        holder: DeclarationId,
        mode: CheckedMode,
    ) -> Result<bool, CheckStop> {
        let region = match mode {
            CheckedMode::Own => return Ok(true),
            CheckedMode::Shared(region) | CheckedMode::Unique(region) => region,
        };
        let holder_scope = self.declaration_scope(holder)?;
        let holder_scope = self
            .resolved
            .scopes()
            .get(holder_scope.index())
            .ok_or(SemanticCompilerFailure::InvalidResolution)?;
        Ok(holder_scope.parent() == Some(self.region_declaration(region)?.scope()))
    }

    pub(super) fn check_loan_access(
        &self,
        bindings: &HashMap<DeclarationId, LocalBinding>,
        through_holder: Option<DeclarationId>,
        place: &ResolvedPlace,
        access: AccessKind,
        node: NodeId,
    ) -> Result<(), CheckStop> {
        for (declaration, local) in bindings {
            let Some(loan) = &local.borrow else {
                continue;
            };
            if Some(*declaration) == through_holder || !places_overlap(&loan.place, place) {
                continue;
            }
            let conflicts = match access {
                AccessKind::Read => loan.kind == BorrowKind::Unique,
                AccessKind::Write | AccessKind::Move | AccessKind::UniqueBorrow => true,
                AccessKind::SharedBorrow => loan.kind == BorrowKind::Unique,
            };
            if conflicts {
                return self.issue_node(
                    SemanticRuleV0_14::Own5,
                    node,
                    SemanticIssueKind::BorrowConflict,
                );
            }
        }
        Ok(())
    }

    fn region_declaration(
        &self,
        id: DeclarationId,
    ) -> Result<&crate::DeclarationRecord, CheckStop> {
        self.resolved
            .declarations()
            .iter()
            .find(|declaration| declaration.id() == id)
            .ok_or(SemanticCompilerFailure::InvalidResolution.into())
    }

    fn declaration_scope(&self, id: DeclarationId) -> Result<ScopeId, CheckStop> {
        self.resolved
            .declarations()
            .iter()
            .find(|declaration| declaration.id() == id)
            .map(|declaration| declaration.scope())
            .ok_or(SemanticCompilerFailure::InvalidResolution.into())
    }

    fn scope_is_within(&self, mut scope: ScopeId, ancestor: ScopeId) -> Result<bool, CheckStop> {
        loop {
            if scope == ancestor {
                return Ok(true);
            }
            let record = self
                .resolved
                .scopes()
                .get(scope.index())
                .ok_or(SemanticCompilerFailure::InvalidResolution)?;
            let Some(parent) = record.parent() else {
                return Ok(false);
            };
            scope = parent;
        }
    }

    pub(super) fn region_outlives(
        &self,
        source: DeclarationId,
        destination: DeclarationId,
    ) -> Result<bool, CheckStop> {
        if source == destination {
            return Ok(true);
        }
        let source = self.region_declaration(source)?;
        let destination = self.region_declaration(destination)?;
        if source.role() == DeclarationRole::RegionParameter {
            return Ok(destination.role() == DeclarationRole::LocalRegion);
        }
        if destination.role() == DeclarationRole::RegionParameter {
            return Ok(false);
        }
        self.scope_is_within(destination.scope(), source.scope())
    }
}

pub(super) fn places_overlap(left: &ResolvedPlace, right: &ResolvedPlace) -> bool {
    left.root == right.root
        && (left.fields.starts_with(&right.fields) || right.fields.starts_with(&left.fields))
}
