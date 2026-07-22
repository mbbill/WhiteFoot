//! Target-independent semantic checking for exact Whitefoot v0.11.
//!
//! This stage consumes complete lexical resolution and is the sole producer of
//! the private checked-program value that may later authorize lowering. A
//! language feature not implemented yet is reported as an unsupported compiler
//! capability, never as a source-language rejection.

mod check;
mod model;
mod tree;

#[cfg(test)]
mod tests;

use crate::{BundleSourceExtent, NodePath, ResolvedSyntaxUnit, SyntaxCoordinate};

pub use check::check_semantics_v0_11;

pub(crate) use model::{
    BindingId, CheckedExpression, CheckedFunction, CheckedIntegerOperation, CheckedProgramData,
    CheckedStatement, CheckedType, CheckedValue, TrapSite,
};

/// Numbered rule owning one post-resolution semantic rejection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SemanticRuleV0_11 {
    /// Numeric literal range or canonicality.
    Form7,
    /// Named-constant type and value formation.
    Const2,
    /// Exact mode/type agreement.
    Type5,
    /// Copy-versus-affine use spelling.
    Own1,
    /// Operation-table row selection.
    Op1,
    /// Exact `own Bool` explicit-check condition.
    Op5,
    /// Function result, reachability, or completion.
    Fn1,
    /// Explicit generic-instantiation argument presence.
    Fn2,
    /// Closed-program `main` contract.
    Fn7,
    /// Exact declared-order named user-call arguments.
    Gram11,
    /// Effect-row canonicality.
    Eff1,
    /// Exact exhibited-versus-declared effect row.
    Eff2,
}

/// Exact checked location selected for a semantic rejection.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum SemanticLocation {
    /// One source-backed production node and its rule-selected coordinate.
    SourceNode(NodePath, SyntaxCoordinate),
    /// The closed compilation-unit root when no source declaration exists.
    BundleRoot(Vec<BundleSourceExtent>),
}

/// Structured reason for one semantic rejection.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum SemanticIssueKind {
    /// A literal is not the unique in-range FORM-7 spelling.
    InvalidIntegerLiteral,
    /// A named constant value does not exactly inhabit its written type.
    InvalidConstValue,
    /// Two exact written modes or types disagree.
    TypeMismatch,
    /// `move` was written for a copy value.
    MoveOfCopy,
    /// The selected operation family has no row for the written arguments.
    InvalidOperation,
    /// An explicit check condition is not exactly `own Bool`.
    InvalidCheckCondition,
    /// A return expression disagrees with the written function result.
    ReturnMismatch,
    /// A statement follows a structurally terminating statement.
    UnreachableStatement,
    /// The function body can reach its closing brace.
    FunctionFallthrough,
    /// The unique source `main` declaration has the wrong header or effect row.
    InvalidMain,
    /// No source `main` declaration exists.
    MissingMain,
    /// Named user-call arguments differ from the parameter list.
    InvalidNamedArguments,
    /// The effect row is not a valid exact EFF-1 row.
    InvalidEffectRow,
    /// The written effect row differs from syntactically exhibited effects.
    EffectMismatch,
}

/// One deterministic post-resolution source-language rejection.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SemanticIssue {
    rule: SemanticRuleV0_11,
    location: SemanticLocation,
    kind: SemanticIssueKind,
}

impl SemanticIssue {
    /// Returns the exact numbered rule established by this issue.
    #[must_use]
    #[cfg(test)]
    pub const fn rule(&self) -> SemanticRuleV0_11 {
        self.rule
    }

    /// Returns the exact DIAG-1 semantic location.
    #[must_use]
    #[cfg(test)]
    pub const fn location(&self) -> &SemanticLocation {
        &self.location
    }

    /// Returns the structured rejection premise.
    #[must_use]
    #[cfg(test)]
    pub const fn kind(&self) -> &SemanticIssueKind {
        &self.kind
    }
}

/// A language family that the current compiler has not implemented yet.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum UnsupportedSemanticFeatureV0_11 {
    /// Source aggregates, payload enums, contracts, or conformances.
    UserNominalDeclarations,
    /// Type, const, or region polymorphism.
    Generics,
    /// Borrow modes, region parameters, or local regions.
    RegionsAndBorrows,
    /// Composite types or values outside the scalar executable family.
    CompositeValues,
    /// Float types, literals, or operations.
    FloatingPoint,
    /// Requires blocks.
    RequiresBlocks,
    /// Match, loop, break, value-match, or `give` control flow.
    StructuredControlFlow,
    /// Mutation through `set`.
    Mutation,
    /// Result propagation.
    ResultPropagation,
    /// An OP-1 family outside the currently lowered integer/Bool family.
    OperationFamily,
    /// An effect other than `pure` or `traps`.
    EffectFamily,
}

/// Exact source node at which an unimplemented compiler family was required.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SemanticUnsupported {
    feature: UnsupportedSemanticFeatureV0_11,
    node: NodePath,
}

impl SemanticUnsupported {
    /// Returns the unimplemented semantic family.
    #[must_use]
    #[cfg(test)]
    pub const fn feature(&self) -> UnsupportedSemanticFeatureV0_11 {
        self.feature
    }
}

/// Trusted semantic-checker invariant failure, never a source verdict.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SemanticCompilerFailure {
    /// Canonical production topology had an impossible local shape.
    InvalidCanonicalTree,
    /// A resolved declaration or use record was missing or inconsistent.
    InvalidResolution,
    /// Exact source bytes were not representable by the required semantic form.
    InvalidSourceEncoding,
    /// A dense identity or source-coordinate calculation overflowed.
    CounterOverflow,
}

/// Whole-unit semantic success and its only lowering authority.
#[derive(Debug)]
pub struct CheckedProgram<'classified, 'lexed, 'source> {
    pub(crate) _resolved: ResolvedSyntaxUnit<'classified, 'lexed, 'source>,
    pub(crate) data: CheckedProgramData,
}

impl CheckedProgram<'_, '_, '_> {
    /// Returns the number of checked source functions.
    #[must_use]
    #[cfg(test)]
    pub fn function_count(&self) -> usize {
        self.data.functions.len()
    }

    /// Returns the exact source name of the checked entry function.
    #[must_use]
    #[cfg(test)]
    pub fn entry_function_name(&self) -> &str {
        self.data
            .functions
            .get(self.data.main.0 as usize)
            .map_or("", |function| function.name.as_str())
    }
}

/// Failure-atomic result of target-independent semantic checking.
#[derive(Debug)]
pub enum SemanticOutcome<'classified, 'lexed, 'source> {
    /// Every applicable whole-unit judgment succeeded.
    Complete(Box<CheckedProgram<'classified, 'lexed, 'source>>),
    /// A numbered language rule was violated.
    SourceIssue {
        /// Deterministically selected semantic issue.
        issue: SemanticIssue,
    },
    /// Valid source requires a language family the compiler has not implemented.
    Unsupported {
        /// Exact unimplemented family and source node.
        unsupported: SemanticUnsupported,
    },
    /// Trusted compiler invariants failed.
    CompilerFailure {
        /// Internal failure class.
        failure: SemanticCompilerFailure,
    },
}

enum CheckStop {
    Issue(SemanticIssue),
    Unsupported(SemanticUnsupported),
    Compiler(SemanticCompilerFailure),
}

impl From<SemanticCompilerFailure> for CheckStop {
    fn from(value: SemanticCompilerFailure) -> Self {
        Self::Compiler(value)
    }
}
