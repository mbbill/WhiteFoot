mod expressions;
mod support;
mod types;

use std::collections::HashMap;

use crate::syntax::NodeId;
use crate::{
    DeclarationId, DeclarationRole, ProductionV0_11, ResolvedSyntaxUnit, SemanticCompilerFailure,
    SemanticIssue, SemanticIssueKind, SemanticLocation, SemanticOutcome, SemanticRuleV0_11,
    UnsupportedSemanticFeatureV0_11,
};

use super::model::{
    BindingId, CheckedExpression, CheckedFunction, CheckedParameter, CheckedProgramData,
    CheckedStatement, CheckedType, CheckedValue, FunctionId, TrapSite,
};
use super::tree::TreeView;
use super::{CheckStop, CheckedProgram};

#[derive(Clone)]
struct ParameterSignature {
    declaration: DeclarationId,
    name: String,
    ty: CheckedType,
}

#[derive(Clone)]
struct FunctionSignature {
    id: FunctionId,
    declaration: DeclarationId,
    node: NodeId,
    name: String,
    parameters: Vec<ParameterSignature>,
    result: CheckedType,
    effects_node: NodeId,
    declared_traps: bool,
}

#[derive(Clone, Copy)]
struct LocalBinding {
    binding: BindingId,
    ty: CheckedType,
}

struct TypedExpression {
    expression: CheckedExpression,
    exhibits_traps: bool,
}

struct Checker<'unit, 'classified, 'lexed, 'source> {
    resolved: &'unit ResolvedSyntaxUnit<'classified, 'lexed, 'source>,
    tree: TreeView<'unit, 'classified, 'lexed, 'source>,
    signatures: Vec<FunctionSignature>,
    functions_by_declaration: HashMap<DeclarationId, FunctionId>,
    constants: HashMap<DeclarationId, CheckedValue>,
}

/// Checks the currently implemented exact-v0.11 semantic family.
///
/// Unsupported language families remain explicit compiler capability results;
/// only a proved numbered-rule violation becomes [`SemanticOutcome::SourceIssue`].
#[must_use]
pub fn check_semantics_v0_11<'classified, 'lexed, 'source>(
    resolved: ResolvedSyntaxUnit<'classified, 'lexed, 'source>,
) -> SemanticOutcome<'classified, 'lexed, 'source> {
    let result = Checker::new(&resolved).and_then(|mut checker| checker.check_program());
    match result {
        Ok(data) => SemanticOutcome::Complete(Box::new(CheckedProgram {
            _resolved: resolved,
            data,
        })),
        Err(CheckStop::Issue(issue)) => SemanticOutcome::SourceIssue { issue },
        Err(CheckStop::Unsupported(unsupported)) => SemanticOutcome::Unsupported { unsupported },
        Err(CheckStop::Compiler(failure)) => SemanticOutcome::CompilerFailure { failure },
    }
}

impl<'unit, 'classified, 'lexed, 'source> Checker<'unit, 'classified, 'lexed, 'source> {
    fn new(
        resolved: &'unit ResolvedSyntaxUnit<'classified, 'lexed, 'source>,
    ) -> Result<Self, CheckStop> {
        Ok(Self {
            resolved,
            tree: TreeView::new(resolved)?,
            signatures: Vec::new(),
            functions_by_declaration: HashMap::new(),
            constants: HashMap::new(),
        })
    }

    fn check_program(&mut self) -> Result<CheckedProgramData, CheckStop> {
        let items = self.item_declarations()?;
        self.check_main_header(&items)?;
        self.reject_unimplemented_items(&items)?;
        self.collect_function_signatures(&items)?;
        self.collect_constants(&items)?;
        let main = self.main_id()?;

        let mut functions = Vec::with_capacity(self.signatures.len());
        for index in 0..self.signatures.len() {
            functions.push(self.check_function(index)?);
        }
        Ok(CheckedProgramData { functions, main })
    }

    fn item_declarations(&self) -> Result<Vec<NodeId>, CheckStop> {
        let mut declarations = Vec::new();
        for item in self.tree.children(self.tree.root())? {
            if self.tree.production(*item)? != ProductionV0_11::Item {
                return Err(SemanticCompilerFailure::InvalidCanonicalTree.into());
            }
            declarations.push(self.tree.only_child(*item)?);
        }
        Ok(declarations)
    }

    fn reject_unimplemented_items(&self, items: &[NodeId]) -> Result<(), CheckStop> {
        for item in items {
            let feature = match self.tree.production(*item)? {
                ProductionV0_11::FnDecl | ProductionV0_11::ConstDecl => continue,
                ProductionV0_11::StructDecl
                | ProductionV0_11::EnumDecl
                | ProductionV0_11::ContractDecl
                | ProductionV0_11::ConformDecl => {
                    UnsupportedSemanticFeatureV0_11::UserNominalDeclarations
                }
                _ => return Err(SemanticCompilerFailure::InvalidCanonicalTree.into()),
            };
            return self.unsupported(feature, *item);
        }
        Ok(())
    }

    fn collect_function_signatures(&mut self, items: &[NodeId]) -> Result<(), CheckStop> {
        for node in items.iter().copied().filter(|node| {
            self.tree
                .production(*node)
                .is_ok_and(|production| production == ProductionV0_11::FnDecl)
        }) {
            if let Some(generics) = self
                .tree
                .first_child_with(node, ProductionV0_11::Generics)?
            {
                return self.unsupported(UnsupportedSemanticFeatureV0_11::Generics, generics);
            }
            if let Some(regions) = self
                .tree
                .first_child_with(node, ProductionV0_11::RegionParams)?
            {
                return self
                    .unsupported(UnsupportedSemanticFeatureV0_11::RegionsAndBorrows, regions);
            }
            if let Some(requires) = self
                .tree
                .first_child_with(node, ProductionV0_11::RequiresBlock)?
            {
                return self.unsupported(UnsupportedSemanticFeatureV0_11::RequiresBlocks, requires);
            }

            let declaration = self.declaration_at(node, DeclarationRole::Function)?;
            let declaration_id = declaration.id();
            let name = declaration.spelling().to_owned();
            let id = FunctionId(
                u32::try_from(self.signatures.len())
                    .map_err(|_| SemanticCompilerFailure::CounterOverflow)?,
            );
            let parameters = self.parse_parameters(node)?;
            let rtype = self
                .tree
                .first_child_with(node, ProductionV0_11::Rtype)?
                .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
            let result = self.parse_rtype(rtype)?;
            let effects = self
                .tree
                .first_child_with(node, ProductionV0_11::Effects)?
                .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
            let declared_traps = self.parse_effects(effects)?;
            self.functions_by_declaration.insert(declaration_id, id);
            self.signatures.push(FunctionSignature {
                id,
                declaration: declaration_id,
                node,
                name,
                parameters,
                result,
                effects_node: effects,
                declared_traps,
            });
        }
        Ok(())
    }

    fn collect_constants(&mut self, items: &[NodeId]) -> Result<(), CheckStop> {
        for node in items.iter().copied().filter(|node| {
            self.tree
                .production(*node)
                .is_ok_and(|production| production == ProductionV0_11::ConstDecl)
        }) {
            let declaration = self.declaration_at(node, DeclarationRole::NamedConst)?;
            let ty_node = self
                .tree
                .first_child_with(node, ProductionV0_11::Type)?
                .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
            let ty = self.parse_type(ty_node)?;
            let value_node = self
                .tree
                .first_child_with(node, ProductionV0_11::Cvalue)?
                .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
            let value = self.parse_const_value(value_node)?;
            if value.ty() != ty {
                return self.issue_node(
                    SemanticRuleV0_11::Const2,
                    value_node,
                    SemanticIssueKind::InvalidConstValue,
                );
            }
            self.constants.insert(declaration.id(), value);
        }
        Ok(())
    }

    fn check_main_header(&self, items: &[NodeId]) -> Result<(), CheckStop> {
        let mut main = None;
        for node in items.iter().copied().filter(|node| {
            self.tree
                .production(*node)
                .is_ok_and(|production| production == ProductionV0_11::FnDecl)
        }) {
            if self
                .declaration_at(node, DeclarationRole::Function)?
                .spelling()
                == "main"
            {
                main = Some(node);
                break;
            }
        }
        let Some(node) = main else {
            return Err(CheckStop::Issue(SemanticIssue {
                rule: SemanticRuleV0_11::Fn7,
                location: SemanticLocation::BundleRoot(
                    self.resolved.syntax().root_extent().to_vec(),
                ),
                kind: SemanticIssueKind::MissingMain,
            }));
        };

        let generics = self
            .tree
            .first_child_with(node, ProductionV0_11::Generics)?;
        let regions = self
            .tree
            .first_child_with(node, ProductionV0_11::RegionParams)?;
        let parameters = self
            .tree
            .first_child_with(node, ProductionV0_11::ParamList)?;
        let rtype = self
            .tree
            .first_child_with(node, ProductionV0_11::Rtype)?
            .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
        let mode = self
            .tree
            .first_child_with(rtype, ProductionV0_11::Mode)?
            .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
        let ty = self
            .tree
            .first_child_with(rtype, ProductionV0_11::Type)?
            .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
        let effects = self
            .tree
            .first_child_with(node, ProductionV0_11::Effects)?
            .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
        if generics.is_some()
            || regions.is_some()
            || parameters.is_some()
            || !self.has_fixed(mode, crate::FixedTerminalV0_11::Own)?
            || !self.has_fixed(ty, crate::FixedTerminalV0_11::Unit)?
            || !self.main_effects_allowed(effects)?
        {
            return self.issue_node(SemanticRuleV0_11::Fn7, node, SemanticIssueKind::InvalidMain);
        }
        Ok(())
    }

    fn main_effects_allowed(&self, effects: NodeId) -> Result<bool, CheckStop> {
        if self.has_fixed(effects, crate::FixedTerminalV0_11::Pure)? {
            return Ok(true);
        }
        let effects = self.tree.children_with(effects, ProductionV0_11::Effect)?;
        let spellings = effects
            .iter()
            .map(|effect| self.tree.direct_spelling(*effect))
            .collect::<Result<Vec<_>, _>>()?;
        Ok(matches!(
            spellings.as_slice(),
            [one] if one == b"traps" || one == b"allocates(heap)"
        ) || matches!(
            spellings.as_slice(),
            [first, second] if first == b"allocates(heap)" && second == b"traps"
        ))
    }

    fn main_id(&self) -> Result<FunctionId, CheckStop> {
        self.signatures
            .iter()
            .find(|signature| signature.name == "main")
            .map(|signature| signature.id)
            .ok_or_else(|| SemanticCompilerFailure::InvalidResolution.into())
    }

    fn check_function(&self, index: usize) -> Result<CheckedFunction, CheckStop> {
        let signature = self
            .signatures
            .get(index)
            .ok_or(SemanticCompilerFailure::InvalidResolution)?;
        let mut bindings = HashMap::new();
        let mut parameters = Vec::with_capacity(signature.parameters.len());
        let mut next_binding = 0_u32;
        for parameter in &signature.parameters {
            let binding = BindingId(next_binding);
            next_binding = next_binding
                .checked_add(1)
                .ok_or(SemanticCompilerFailure::CounterOverflow)?;
            bindings.insert(
                parameter.declaration,
                LocalBinding {
                    binding,
                    ty: parameter.ty,
                },
            );
            parameters.push(CheckedParameter {
                name: parameter.name.clone(),
                binding,
                ty: parameter.ty,
            });
        }

        let mut body = Vec::new();
        let mut terminated = false;
        let mut exhibits_traps = false;
        for statement_wrapper in self
            .tree
            .children_with(signature.node, ProductionV0_11::Stmt)?
        {
            let statement = self.tree.only_child(statement_wrapper)?;
            if terminated {
                return self.issue_node(
                    SemanticRuleV0_11::Fn1,
                    statement,
                    SemanticIssueKind::UnreachableStatement,
                );
            }
            let checked =
                self.check_statement(signature, statement, &mut bindings, &mut next_binding)?;
            exhibits_traps |= checked.exhibits_traps;
            terminated = checked.terminates;
            body.push(checked.statement);
        }
        if !terminated {
            return Err(CheckStop::Issue(SemanticIssue {
                rule: SemanticRuleV0_11::Fn1,
                location: SemanticLocation::SourceNode(
                    self.tree.path(signature.node)?.clone(),
                    self.tree.closing_brace_coordinate(signature.node)?,
                ),
                kind: SemanticIssueKind::FunctionFallthrough,
            }));
        }
        if exhibits_traps != signature.declared_traps {
            return self.issue_node(
                SemanticRuleV0_11::Eff2,
                signature.effects_node,
                SemanticIssueKind::EffectMismatch,
            );
        }
        Ok(CheckedFunction {
            id: signature.id,
            declaration: signature.declaration,
            name: signature.name.clone(),
            parameters,
            result: signature.result,
            declared_traps: signature.declared_traps,
            body,
        })
    }

    fn check_statement(
        &self,
        function: &FunctionSignature,
        node: NodeId,
        bindings: &mut HashMap<DeclarationId, LocalBinding>,
        next_binding: &mut u32,
    ) -> Result<StatementResult, CheckStop> {
        match self.tree.production(node)? {
            ProductionV0_11::LetStmt => {
                let Some(rhs) = self
                    .tree
                    .first_child_with(node, ProductionV0_11::OrdinaryLetRhs)?
                else {
                    if let Some(propagate) = self
                        .tree
                        .first_child_with(node, ProductionV0_11::PropagateLetRhs)?
                    {
                        return self.unsupported(
                            UnsupportedSemanticFeatureV0_11::ResultPropagation,
                            propagate,
                        );
                    }
                    return self
                        .unsupported(UnsupportedSemanticFeatureV0_11::StructuredControlFlow, node);
                };
                let mode = self
                    .tree
                    .first_child_with(node, ProductionV0_11::Mode)?
                    .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
                self.require_own_mode(mode)?;
                let ty_node = self
                    .tree
                    .first_child_with(node, ProductionV0_11::Type)?
                    .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
                let expected = self.parse_type(ty_node)?;
                let expression_node = self
                    .tree
                    .first_child_with(rhs, ProductionV0_11::Expr)?
                    .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
                let value = self.check_expression(function, expression_node, bindings)?;
                if value.expression.ty() != expected {
                    return self.issue_node(
                        SemanticRuleV0_11::Type5,
                        node,
                        SemanticIssueKind::TypeMismatch,
                    );
                }
                let declaration = self.declaration_at(node, DeclarationRole::Let)?;
                let binding = BindingId(*next_binding);
                *next_binding = next_binding
                    .checked_add(1)
                    .ok_or(SemanticCompilerFailure::CounterOverflow)?;
                bindings.insert(
                    declaration.id(),
                    LocalBinding {
                        binding,
                        ty: expected,
                    },
                );
                Ok(StatementResult {
                    statement: CheckedStatement::Let {
                        binding,
                        value: value.expression,
                    },
                    terminates: false,
                    exhibits_traps: value.exhibits_traps,
                })
            }
            ProductionV0_11::ExprStmt => {
                let call = self
                    .tree
                    .first_child_with(node, ProductionV0_11::Call)?
                    .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
                let value = self.check_call(function, call, bindings)?;
                Ok(StatementResult {
                    statement: CheckedStatement::Evaluate(value.expression),
                    terminates: false,
                    exhibits_traps: value.exhibits_traps,
                })
            }
            ProductionV0_11::ReturnStmt => {
                let expression_node = self
                    .tree
                    .first_child_with(node, ProductionV0_11::Expr)?
                    .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
                let value = self.check_expression(function, expression_node, bindings)?;
                if value.expression.ty() != function.result {
                    return Err(CheckStop::Issue(SemanticIssue {
                        rule: SemanticRuleV0_11::Fn1,
                        location: SemanticLocation::SourceNode(
                            self.tree.path(node)?.clone(),
                            self.tree.coordinate(expression_node)?,
                        ),
                        kind: SemanticIssueKind::ReturnMismatch,
                    }));
                }
                Ok(StatementResult {
                    statement: CheckedStatement::Return(value.expression),
                    terminates: true,
                    exhibits_traps: value.exhibits_traps,
                })
            }
            ProductionV0_11::CheckStmt => {
                let expression_node = self
                    .tree
                    .first_child_with(node, ProductionV0_11::Expr)?
                    .ok_or(SemanticCompilerFailure::InvalidCanonicalTree)?;
                let condition = self.check_expression(function, expression_node, bindings)?;
                if condition.expression.ty() != CheckedType::Bool {
                    return Err(CheckStop::Issue(SemanticIssue {
                        rule: SemanticRuleV0_11::Op5,
                        location: SemanticLocation::SourceNode(
                            self.tree.path(node)?.clone(),
                            self.tree.coordinate(expression_node)?,
                        ),
                        kind: SemanticIssueKind::InvalidCheckCondition,
                    }));
                }
                let message = self.check_message(node)?;
                Ok(StatementResult {
                    statement: CheckedStatement::Check {
                        condition: condition.expression,
                        trap: TrapSite {
                            rule_id: "OP-5",
                            message,
                            function: function.name.clone(),
                            node_path: self.tree.path(node)?.clone(),
                        },
                    },
                    terminates: false,
                    exhibits_traps: true,
                })
            }
            ProductionV0_11::SetStmt => {
                self.unsupported(UnsupportedSemanticFeatureV0_11::Mutation, node)
            }
            ProductionV0_11::LoopStmt
            | ProductionV0_11::BreakStmt
            | ProductionV0_11::MatchStmt
            | ProductionV0_11::GiveStmt => {
                self.unsupported(UnsupportedSemanticFeatureV0_11::StructuredControlFlow, node)
            }
            ProductionV0_11::RegionStmt => {
                self.unsupported(UnsupportedSemanticFeatureV0_11::RegionsAndBorrows, node)
            }
            _ => Err(SemanticCompilerFailure::InvalidCanonicalTree.into()),
        }
    }
}

struct StatementResult {
    statement: CheckedStatement,
    terminates: bool,
    exhibits_traps: bool,
}
