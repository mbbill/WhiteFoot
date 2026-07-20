#![forbid(unsafe_code)]
#![deny(missing_docs)]

//! Judgment-free data contracts shared by the Whitefoot compiler and verifier.
//!
//! This crate does not decide whether source is legal Whitefoot. In particular,
//! source bundles retain arbitrary bytes so the frontend can issue the exact
//! FORM-2 diagnostic for invalid UTF-8 or noncanonical formatting.

mod binding;
mod digest;
mod source;

pub use binding::{
    BoundSource, DecodeError, EncodeError, SOURCE_BINDING_CODEC_VERSION, SourceBinding,
};
pub use digest::{KERNEL_SPEC_V0_8_HASH, Sha256Digest, SpecHash};
pub use source::{
    ByteOffset, LogicalPath, LogicalPathError, SourceBundle, SourceBundleError, SourceFile,
    SourceId, SourceInput, SourceLimit, SourceLimits, SourceSpan, SpanError,
};
