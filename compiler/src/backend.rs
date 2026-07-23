//! Conservative textual LLVM emission for exact Whitefoot v0.12.

mod emitter;

#[cfg(test)]
mod tests;

pub use emitter::{BackendFailure, emit_llvm_v0_12};
