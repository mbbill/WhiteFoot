//! Conservative textual LLVM emission for exact Whitefoot v0.11.

mod emitter;

#[cfg(test)]
mod tests;

pub use emitter::{BackendFailure, emit_llvm_v0_11};
