#![forbid(unsafe_code)]
#![deny(missing_docs)]

//! Resource-bounded canonical syntax construction for Whitefoot v0.9.
//!
//! The current implementation performs complete, context-free terminal
//! membership over a lossless lexer result. It does not yet parse, construct a
//! tree, audit canonical formatting, or publish `CanonicalSyntaxUnit`.

mod classifier;
mod outcome;

pub use classifier::classify_terminals_v0_9;
pub use outcome::{
    ClassifiedBundle, ClassifiedToken, TerminalCompilerFailure, TerminalInvocationFailure,
    TerminalIssue, TerminalIssueOwner, TerminalLimit, TerminalLimits, TerminalOutcome,
    TerminalResourceFailure, TerminalStorage,
};

#[cfg(test)]
mod tests;
