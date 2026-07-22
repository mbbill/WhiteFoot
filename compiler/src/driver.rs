//! One ordinary exact-v0.11 compilation pipeline.
//!
//! The driver keeps source failures, unsupported compiler capabilities,
//! resource failures, invariant failures, lowering failures, and backend
//! failures distinct while returning owned LLVM assembly to callers.

use core::fmt;

use crate::{
    BackendFailure, CanonicalLimits, CanonicalOutcome, FinalizeLimits, FinalizeOutcome,
    KERNEL_SPEC_V0_11_HASH, LexLimits, LexOutcome, LoweringFailure, ParseLimits, ParseOutcome,
    ResolutionOutcome, SemanticOutcome, SourceBundle, SourceInput, SourceLimits, TerminalLimits,
    TerminalOutcome, audit_canonical_v0_11, check_semantics_v0_11, classify_terminals_v0_11,
    emit_llvm_v0_11, finalize_v0_11, lex_v0_11, lower_checked_v0_11, parse_v0_11, resolve_v0_11,
};

/// Explicit implementation ceilings for one compiler invocation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CompilerLimits {
    /// Ordered source-envelope limits.
    pub source: SourceLimits,
    /// Lossless lexical limits.
    pub lexer: LexLimits,
    /// Terminal-classification limits.
    pub terminals: TerminalLimits,
    /// Predictive parser limits.
    pub parser: ParseLimits,
    /// Finalized-tree limits.
    pub finalizer: FinalizeLimits,
    /// Canonical-source audit limits.
    pub canonical: CanonicalLimits,
}

impl Default for CompilerLimits {
    fn default() -> Self {
        Self {
            source: SourceLimits {
                max_sources: 1_024,
                max_logical_path_bytes: 4_096,
                max_source_bytes: 16 * 1_024 * 1_024,
                max_total_source_bytes: 64 * 1_024 * 1_024,
                max_binding_bytes: 128 * 1_024 * 1_024,
            },
            lexer: LexLimits {
                max_sources: 1_024,
                max_source_bytes: 16 * 1_024 * 1_024,
                max_total_source_bytes: 64 * 1_024 * 1_024,
                max_token_bytes: 1_024 * 1_024,
                max_tokens: 8 * 1_024 * 1_024,
                max_lexemes: 16 * 1_024 * 1_024,
            },
            terminals: TerminalLimits {
                max_tokens: 8 * 1_024 * 1_024,
            },
            parser: ParseLimits {
                max_work: 256 * 1_024 * 1_024,
                max_tasks: 8 * 1_024 * 1_024,
                max_frames: 65_536,
                max_elements: 16 * 1_024 * 1_024,
            },
            finalizer: FinalizeLimits {
                max_work: 256 * 1_024 * 1_024,
                max_roots: 8 * 1_024 * 1_024,
                max_shape_tasks: 8 * 1_024 * 1_024,
                max_nodes: 8 * 1_024 * 1_024,
                max_child_edges: 8 * 1_024 * 1_024,
                max_terminals: 8 * 1_024 * 1_024,
                max_sources: 1_024,
            },
            canonical: CanonicalLimits {
                max_work: 256 * 1_024 * 1_024,
                max_source_bytes: 16 * 1_024 * 1_024,
                max_total_source_bytes: 64 * 1_024 * 1_024,
                max_gaps: 8 * 1_024 * 1_024,
                max_path_components: 65_536,
            },
        }
    }
}

/// Compiler stage at which one invocation stopped.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CompilationStage {
    /// PROG-2 source envelope.
    SourceEnvelope,
    /// Raw lossless lexing.
    Lexing,
    /// Context-free terminal membership.
    TerminalClassification,
    /// Strong-LL(2) grammar derivation.
    Parsing,
    /// Finalized production topology.
    Finalization,
    /// Exact FORM-2 source audit.
    CanonicalSource,
    /// Declaration and lexical-use resolution.
    Resolution,
    /// Target-independent semantic checking.
    Semantics,
    /// Checked-program to target-independent IR lowering.
    Lowering,
    /// Conservative textual LLVM emission.
    Backend,
}

/// Category of compiler stop, independent of the stage that reported it.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CompilationFailureKind {
    /// A numbered source-language rule was violated.
    Source,
    /// Valid source requires an unimplemented compiler capability.
    Unsupported,
    /// An explicit implementation ceiling or host storage stopped work.
    Resource,
    /// The caller supplied an invalid compilation envelope or stage identity.
    Invocation,
    /// A trusted compiler invariant failed.
    Compiler,
    /// Checked-program to IR lowering failed internally.
    Lowering,
    /// LLVM emission failed internally.
    Backend,
}

/// One compiler stop with its category preserved in the detail text.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CompilationFailure {
    stage: CompilationStage,
    kind: CompilationFailureKind,
    detail: String,
}

impl CompilationFailure {
    fn new(stage: CompilationStage, kind: CompilationFailureKind, detail: impl fmt::Debug) -> Self {
        Self {
            stage,
            kind,
            detail: format!("{detail:?}"),
        }
    }

    /// Returns the stage that did not produce a complete result.
    #[must_use]
    pub const fn stage(&self) -> CompilationStage {
        self.stage
    }

    /// Returns the source/unsupported/resource/invocation/internal category.
    #[must_use]
    pub const fn kind(&self) -> CompilationFailureKind {
        self.kind
    }

    /// Returns the structured debug detail retained by that stage.
    #[must_use]
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for CompilationFailure {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "{:?}/{:?}: {}",
            self.stage, self.kind, self.detail
        )
    }
}

impl std::error::Error for CompilationFailure {}

/// Compiles one ordered closed source bundle to conservative textual LLVM.
pub fn compile_v0_11(
    inputs: &[SourceInput<'_>],
    limits: CompilerLimits,
) -> Result<String, CompilationFailure> {
    let bundle = SourceBundle::with_limits(inputs, limits.source).map_err(|failure| {
        CompilationFailure::new(
            CompilationStage::SourceEnvelope,
            CompilationFailureKind::Invocation,
            failure,
        )
    })?;
    let lexed = match lex_v0_11(&bundle, limits.lexer) {
        LexOutcome::Complete(complete) => complete,
        LexOutcome::SourceIssue(issue) => {
            return Err(CompilationFailure::new(
                CompilationStage::Lexing,
                CompilationFailureKind::Source,
                issue,
            ));
        }
        LexOutcome::ResourceFailure(failure) => {
            return Err(CompilationFailure::new(
                CompilationStage::Lexing,
                CompilationFailureKind::Resource,
                failure,
            ));
        }
        LexOutcome::CompilerFailure(failure) => {
            return Err(CompilationFailure::new(
                CompilationStage::Lexing,
                CompilationFailureKind::Compiler,
                failure,
            ));
        }
    };
    let classified =
        match classify_terminals_v0_11(&lexed, KERNEL_SPEC_V0_11_HASH, limits.terminals) {
            TerminalOutcome::Complete(complete) => complete,
            TerminalOutcome::SourceIssue(issue) => {
                return Err(CompilationFailure::new(
                    CompilationStage::TerminalClassification,
                    CompilationFailureKind::Source,
                    issue,
                ));
            }
            TerminalOutcome::ResourceFailure(failure) => {
                return Err(CompilationFailure::new(
                    CompilationStage::TerminalClassification,
                    CompilationFailureKind::Resource,
                    failure,
                ));
            }
            TerminalOutcome::InvocationFailure(failure) => {
                return Err(CompilationFailure::new(
                    CompilationStage::TerminalClassification,
                    CompilationFailureKind::Invocation,
                    failure,
                ));
            }
            TerminalOutcome::CompilerFailure(failure) => {
                return Err(CompilationFailure::new(
                    CompilationStage::TerminalClassification,
                    CompilationFailureKind::Compiler,
                    failure,
                ));
            }
        };
    let parsed = match parse_v0_11(&classified, limits.parser) {
        ParseOutcome::Complete(complete) => complete,
        ParseOutcome::SourceIssue(issue) => {
            return Err(CompilationFailure::new(
                CompilationStage::Parsing,
                CompilationFailureKind::Source,
                issue,
            ));
        }
        ParseOutcome::ResourceFailure(failure) => {
            return Err(CompilationFailure::new(
                CompilationStage::Parsing,
                CompilationFailureKind::Resource,
                failure,
            ));
        }
        ParseOutcome::InvocationFailure(failure) => {
            return Err(CompilationFailure::new(
                CompilationStage::Parsing,
                CompilationFailureKind::Invocation,
                failure,
            ));
        }
        ParseOutcome::CompilerFailure(failure) => {
            return Err(CompilationFailure::new(
                CompilationStage::Parsing,
                CompilationFailureKind::Compiler,
                failure,
            ));
        }
    };
    let finalized = match finalize_v0_11(parsed, limits.finalizer) {
        FinalizeOutcome::Complete(complete) => complete,
        FinalizeOutcome::ResourceFailure(failure) => {
            return Err(CompilationFailure::new(
                CompilationStage::Finalization,
                CompilationFailureKind::Resource,
                failure,
            ));
        }
        FinalizeOutcome::CompilerFailure(failure) => {
            return Err(CompilationFailure::new(
                CompilationStage::Finalization,
                CompilationFailureKind::Compiler,
                failure,
            ));
        }
    };
    let canonical = match audit_canonical_v0_11(finalized, limits.canonical) {
        CanonicalOutcome::Complete(complete) => complete,
        CanonicalOutcome::SourceIssue(issue) => {
            return Err(CompilationFailure::new(
                CompilationStage::CanonicalSource,
                CompilationFailureKind::Source,
                issue,
            ));
        }
        CanonicalOutcome::ResourceFailure(failure) => {
            return Err(CompilationFailure::new(
                CompilationStage::CanonicalSource,
                CompilationFailureKind::Resource,
                failure,
            ));
        }
        CanonicalOutcome::CompilerFailure(failure) => {
            return Err(CompilationFailure::new(
                CompilationStage::CanonicalSource,
                CompilationFailureKind::Compiler,
                failure,
            ));
        }
    };
    let resolved = match resolve_v0_11(canonical) {
        ResolutionOutcome::Complete(complete) => complete,
        ResolutionOutcome::SourceIssue { issue, .. } => {
            return Err(CompilationFailure::new(
                CompilationStage::Resolution,
                CompilationFailureKind::Source,
                issue,
            ));
        }
        ResolutionOutcome::CompilerFailure { failure, .. } => {
            return Err(CompilationFailure::new(
                CompilationStage::Resolution,
                CompilationFailureKind::Compiler,
                failure,
            ));
        }
    };
    let checked = match check_semantics_v0_11(resolved) {
        SemanticOutcome::Complete(complete) => *complete,
        SemanticOutcome::SourceIssue { issue, .. } => {
            return Err(CompilationFailure::new(
                CompilationStage::Semantics,
                CompilationFailureKind::Source,
                issue,
            ));
        }
        SemanticOutcome::Unsupported { unsupported, .. } => {
            return Err(CompilationFailure::new(
                CompilationStage::Semantics,
                CompilationFailureKind::Unsupported,
                unsupported,
            ));
        }
        SemanticOutcome::CompilerFailure { failure, .. } => {
            return Err(CompilationFailure::new(
                CompilationStage::Semantics,
                CompilationFailureKind::Compiler,
                failure,
            ));
        }
    };
    let ir = lower_checked_v0_11(checked).map_err(|failure: LoweringFailure| {
        CompilationFailure::new(
            CompilationStage::Lowering,
            CompilationFailureKind::Lowering,
            failure,
        )
    })?;
    emit_llvm_v0_11(&ir)
        .map(|module| module.into_string())
        .map_err(|failure: BackendFailure| {
            CompilationFailure::new(
                CompilationStage::Backend,
                CompilationFailureKind::Backend,
                failure,
            )
        })
}

#[cfg(test)]
mod tests {
    use super::{CompilationFailureKind, CompilationStage, CompilerLimits, compile_v0_11};
    use crate::SourceInput;

    #[test]
    fn driver_preserves_semantic_unsupported_as_a_semantic_stop() {
        let source = b"struct Value {\n}\n\nfn main() -> own unit pure {\n  return unit;\n}\n";
        let failure = compile_v0_11(
            &[SourceInput::new("value.wf", source)],
            CompilerLimits::default(),
        )
        .expect_err("aggregate family is not implemented yet");
        assert_eq!(failure.stage(), CompilationStage::Semantics);
        assert_eq!(failure.kind(), CompilationFailureKind::Unsupported);
        assert!(failure.detail().contains("Unsupported"));
    }

    #[test]
    fn compiler_independent_negative_cases_keep_their_semantic_rule() {
        for (name, source, rule) in [
            (
                "gram11-neg-misspelled.wf",
                include_bytes!("../../tests/conformance/cases/gram11-neg-misspelled.wf").as_slice(),
                "Gram11",
            ),
            (
                "eff2-neg-declared-unexhibited.wf",
                include_bytes!("../../tests/conformance/cases/eff2-neg-declared-unexhibited.wf")
                    .as_slice(),
                "Eff2",
            ),
            (
                "fn2-neg-implicit-instantiation.wf",
                include_bytes!("../../tests/conformance/cases/fn2-neg-implicit-instantiation.wf")
                    .as_slice(),
                "Fn2",
            ),
            (
                "form7-neg-out-of-range.wf",
                include_bytes!("../../tests/conformance/cases/form7-neg-out-of-range.wf")
                    .as_slice(),
                "Form7",
            ),
            (
                "type5-neg-arg-mismatch.wf",
                include_bytes!("../../tests/conformance/cases/type5-neg-arg-mismatch.wf")
                    .as_slice(),
                "Type5",
            ),
        ] {
            let failure =
                compile_v0_11(&[SourceInput::new(name, source)], CompilerLimits::default())
                    .expect_err("negative conformance case must reject");
            assert_eq!(failure.stage(), CompilationStage::Semantics);
            assert_eq!(failure.kind(), CompilationFailureKind::Source);
            assert!(failure.detail().contains(rule));
        }
    }
}
