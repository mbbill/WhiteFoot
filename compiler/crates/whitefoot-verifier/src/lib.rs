#![forbid(unsafe_code)]
#![deny(missing_docs)]

//! Independent validation of Whitefoot artifact contracts.
//!
//! The verifier consumes only judgment-free types from `whitefoot-contract`.
//! It does not parse source or reproduce frontend language semantics.

mod source_binding;

pub use source_binding::{
    VerifiedSource, VerifiedSourceBinding, VerifySourceBindingError, verify_source_binding,
};
