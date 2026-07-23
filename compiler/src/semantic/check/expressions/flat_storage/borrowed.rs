use std::collections::HashMap;

use crate::syntax::NodeId;
use crate::{
    DeclarationClass, DeclarationId, LexicalUseRole, ProductionV0_14, ResolvedTarget,
    SemanticCompilerFailure, SemanticIssueKind, SemanticRuleV0_14, UnsupportedSemanticFeatureV0_14,
};

use super::super::super::super::model::{CheckedBufferRoot, CheckedType};
use super::super::super::{CheckStop, Checker, LocalBinding};
use super::{CheckedBufferPlace, CheckedIndexedPlace};

impl<'unit, 'classified, 'lexed, 'source> Checker<'unit, 'classified, 'lexed, 'source> {
    pub(super) fn check_dereferenced_buffer_place(
        &self,
        node: NodeId,
        pbase: NodeId,
        bindings: &HashMap<DeclarationId, LocalBinding>,
    ) -> Result<CheckedIndexedPlace, CheckStop> {
        if !self
            .tree
            .children_with(node, ProductionV0_14::Psuffix)?
            .is_empty()
        {
            return self.unsupported(UnsupportedSemanticFeatureV0_14::RegionsAndBorrows, node);
        }
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
        let Some(borrow) = &local.borrow else {
            return self.issue_node(
                SemanticRuleV0_14::Type7,
                node,
                SemanticIssueKind::MissingDereference {
                    mechanical_fix: "deref requires a borrow holder",
                },
            );
        };
        let CheckedType::Buffer { element } = local.ty else {
            return self.unsupported(UnsupportedSemanticFeatureV0_14::RegionsAndBorrows, node);
        };
        Ok(CheckedIndexedPlace::Buffer(CheckedBufferPlace {
            root: CheckedBufferRoot {
                binding: local.binding,
                fields: Vec::new(),
                element,
            },
            declaration,
            element_type: element.ty(),
            holder: Some(declaration),
            resolved: borrow.place.clone(),
            origin_region: borrow.origin_region,
            borrow_kind: Some(borrow.kind),
        }))
    }
}
