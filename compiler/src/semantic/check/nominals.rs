use std::collections::HashSet;

use crate::syntax::NodeId;
use crate::{
    DeclarationRole, DependentDeclarationRole, ProductionV0_11, SemanticCompilerFailure,
    SemanticIssueKind, SemanticRuleV0_11, UnsupportedSemanticFeatureV0_11,
};

use super::super::model::{
    CheckedField, CheckedNominal, CheckedNominalKind, CheckedType, CheckedVariant, NominalId,
};
use super::{CheckStop, Checker, Constructor};

impl<'unit, 'classified, 'lexed, 'source> Checker<'unit, 'classified, 'lexed, 'source> {
    pub(super) fn collect_nominals(&mut self, items: &[NodeId]) -> Result<(), CheckStop> {
        for node in items.iter().copied().filter(|node| {
            self.tree.production(*node).is_ok_and(|production| {
                matches!(
                    production,
                    ProductionV0_11::StructDecl | ProductionV0_11::EnumDecl
                )
            })
        }) {
            if let Some(generics) = self
                .tree
                .first_child_with(node, ProductionV0_11::Generics)?
            {
                return self.unsupported(UnsupportedSemanticFeatureV0_11::Generics, generics);
            }
            let role = match self.tree.production(node)? {
                ProductionV0_11::StructDecl => DeclarationRole::Struct,
                ProductionV0_11::EnumDecl => DeclarationRole::Enum,
                _ => return Err(SemanticCompilerFailure::InvalidCanonicalTree.into()),
            };
            let declaration = self.declaration_at(node, role)?;
            let declaration_id = declaration.id();
            let id = NominalId(
                u32::try_from(self.nominals.len())
                    .map_err(|_| SemanticCompilerFailure::CounterOverflow)?,
            );
            if self
                .nominals_by_declaration
                .insert(declaration_id, id)
                .is_some()
            {
                return Err(SemanticCompilerFailure::InvalidResolution.into());
            }
            if role == DeclarationRole::Struct
                && self
                    .constructors_by_declaration
                    .insert(declaration_id, Constructor::Struct(id))
                    .is_some()
            {
                return Err(SemanticCompilerFailure::InvalidResolution.into());
            }
            self.nominal_nodes.push(node);
            self.nominals.push(CheckedNominal {
                id,
                kind: match role {
                    DeclarationRole::Struct => CheckedNominalKind::Struct { fields: Vec::new() },
                    DeclarationRole::Enum => CheckedNominalKind::Enum {
                        variants: Vec::new(),
                    },
                    _ => return Err(SemanticCompilerFailure::InvalidResolution.into()),
                },
            });
        }

        for id in 0..self.nominals.len() {
            let node = *self
                .nominal_nodes
                .get(id)
                .ok_or(SemanticCompilerFailure::InvalidResolution)?;
            let kind = match self.tree.production(node)? {
                ProductionV0_11::StructDecl => CheckedNominalKind::Struct {
                    fields: self.parse_struct_fields(node)?,
                },
                ProductionV0_11::EnumDecl => CheckedNominalKind::Enum {
                    variants: self.parse_enum_variants(NominalId(id as u32), node)?,
                },
                _ => return Err(SemanticCompilerFailure::InvalidCanonicalTree.into()),
            };
            self.nominals
                .get_mut(id)
                .ok_or(SemanticCompilerFailure::InvalidResolution)?
                .kind = kind;
        }
        self.reject_recursive_nominal_layouts()
    }

    fn parse_struct_fields(&self, node: NodeId) -> Result<Vec<CheckedField>, CheckStop> {
        let nodes = self.tree.children_with(node, ProductionV0_11::Field)?;
        let mut seen = HashSet::with_capacity(nodes.len());
        let mut fields = Vec::with_capacity(nodes.len());
        for field in nodes {
            let declaration =
                self.dependent_declaration_at(field, DependentDeclarationRole::Field)?;
            let name = declaration.spelling().to_owned();
            if !seen.insert(name.clone()) {
                return self.issue_node(
                    SemanticRuleV0_11::Type6,
                    field,
                    SemanticIssueKind::DuplicateFieldLabel { label: name },
                );
            }
            let ty = self
                .tree
                .first_child_with(field, ProductionV0_11::Type)?
                .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
            fields.push(CheckedField {
                name,
                ty: self.parse_type(ty)?,
            });
        }
        Ok(fields)
    }

    fn parse_enum_variants(
        &mut self,
        nominal: NominalId,
        node: NodeId,
    ) -> Result<Vec<CheckedVariant>, CheckStop> {
        let nodes = self.tree.children_with(node, ProductionV0_11::Variant)?;
        let mut variants = Vec::with_capacity(nodes.len());
        for variant_node in nodes {
            let declaration = self.declaration_at(variant_node, DeclarationRole::Variant)?;
            let declaration_id = declaration.id();
            let name = declaration.spelling().to_owned();
            let tag = u32::try_from(variants.len())
                .map_err(|_| SemanticCompilerFailure::CounterOverflow)?;
            if self
                .constructors_by_declaration
                .insert(
                    declaration_id,
                    Constructor::Enum {
                        nominal,
                        variant: tag,
                    },
                )
                .is_some()
            {
                return Err(SemanticCompilerFailure::InvalidResolution.into());
            }
            let mut fields = Vec::new();
            let mut seen = HashSet::new();
            if let Some(list) = self
                .tree
                .first_child_with(variant_node, ProductionV0_11::VfieldList)?
            {
                for field in self.tree.children_with(list, ProductionV0_11::Vfield)? {
                    let declaration = self
                        .dependent_declaration_at(field, DependentDeclarationRole::VariantField)?;
                    let field_name = declaration.spelling().to_owned();
                    if !seen.insert(field_name.clone()) {
                        return self.issue_node(
                            SemanticRuleV0_11::Type6,
                            field,
                            SemanticIssueKind::DuplicateFieldLabel { label: field_name },
                        );
                    }
                    let ty = self
                        .tree
                        .first_child_with(field, ProductionV0_11::Type)?
                        .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
                    fields.push(CheckedField {
                        name: field_name,
                        ty: self.parse_type(ty)?,
                    });
                }
            }
            variants.push(CheckedVariant {
                name,
                constructor: declaration_id,
                tag,
                fields,
            });
        }
        Ok(variants)
    }

    fn reject_recursive_nominal_layouts(&self) -> Result<(), CheckStop> {
        let mut colors = vec![0_u8; self.nominals.len()];
        for root in 0..self.nominals.len() {
            if colors[root] != 0 {
                continue;
            }
            colors[root] = 1;
            let mut stack = vec![(root, 0_usize, self.nominal_dependencies(root)?)];
            while let Some((current, next, dependencies)) = stack.last_mut() {
                if *next == dependencies.len() {
                    colors[*current] = 2;
                    stack.pop();
                    continue;
                }
                let dependency = dependencies[*next].0 as usize;
                *next += 1;
                match colors.get(dependency).copied() {
                    Some(0) => {
                        colors[dependency] = 1;
                        stack.push((dependency, 0, self.nominal_dependencies(dependency)?));
                    }
                    Some(1) => {
                        let node = *self
                            .nominal_nodes
                            .get(root)
                            .ok_or(SemanticCompilerFailure::InvalidResolution)?;
                        return self.unsupported(
                            UnsupportedSemanticFeatureV0_11::RecursiveNominalLayout,
                            node,
                        );
                    }
                    Some(2) => {}
                    _ => return Err(SemanticCompilerFailure::InvalidResolution.into()),
                }
            }
        }
        Ok(())
    }

    fn nominal_dependencies(&self, index: usize) -> Result<Vec<NominalId>, CheckStop> {
        let nominal = self
            .nominals
            .get(index)
            .ok_or(SemanticCompilerFailure::InvalidResolution)?;
        let fields: Vec<&CheckedField> = match &nominal.kind {
            CheckedNominalKind::Struct { fields } => fields.iter().collect(),
            CheckedNominalKind::Enum { variants } => variants
                .iter()
                .flat_map(|variant| variant.fields.iter())
                .collect(),
        };
        Ok(fields
            .into_iter()
            .filter_map(|field| match field.ty {
                CheckedType::Nominal(id) => Some(id),
                _ => None,
            })
            .collect())
    }

    pub(super) fn nominal(&self, id: NominalId) -> Result<&CheckedNominal, CheckStop> {
        self.nominals
            .get(id.0 as usize)
            .ok_or(SemanticCompilerFailure::InvalidResolution.into())
    }

    pub(super) fn is_copy_type(&self, ty: CheckedType) -> Result<bool, CheckStop> {
        Ok(match ty {
            CheckedType::Nominal(id) => self.nominal(id)?.is_copy(),
            CheckedType::Unit | CheckedType::Bool | CheckedType::Integer(_) => true,
        })
    }
}
