#![forbid(unsafe_code)]
#![deny(missing_docs)]

//! Bounded binary observation adapter for the Whitefoot v0.8 lexer.
//!
//! This program reads one canonical source-bound request from standard input
//! and writes one lexical observation to standard output. It does not decide
//! language acceptance, emit normative diagnostics, or consume capability
//! metadata.

mod projection;
mod protocol;

use std::io::{self, Write};
use std::process::ExitCode;

use whitefoot_contract::{KERNEL_SPEC_V0_8_HASH, SourceBinding, SourceBundle, SourceInput};
use whitefoot_frontend::lex_v0_8;

use crate::projection::encode_observation;
use crate::protocol::{AdapterError, read_request};

fn observe() -> Result<(), AdapterError> {
    let input = io::stdin();
    let request = read_request(&mut input.lock())?;
    let candidate = SourceBinding::decode_canonical(&request.binding, request.source_limits)
        .map_err(|_| AdapterError::BindingInvalid)?;
    if candidate.spec_hash() != KERNEL_SPEC_V0_8_HASH {
        return Err(AdapterError::SpecificationMismatch);
    }

    let inputs = candidate
        .sources()
        .iter()
        .map(|source| SourceInput::new(source.logical_path().as_str(), source.bytes().to_vec()));
    let bundle = SourceBundle::with_limits(inputs, request.source_limits)
        .map_err(|_| AdapterError::SourceBundleInvalid)?;
    let reconstructed = SourceBinding::from_bundle(KERNEL_SPEC_V0_8_HASH, &bundle);
    if reconstructed != candidate {
        return Err(AdapterError::SourceBindingDisagreement);
    }
    let canonical = reconstructed
        .encode_canonical(request.source_limits)
        .map_err(|_| AdapterError::SourceBindingDisagreement)?;
    if canonical != request.binding {
        return Err(AdapterError::SourceBindingDisagreement);
    }

    let outcome = lex_v0_8(&bundle, request.lex_limits);
    let response = encode_observation(&bundle, outcome)?;
    io::stdout()
        .lock()
        .write_all(&response)
        .map_err(|_| AdapterError::OutputWrite)
}

fn main() -> ExitCode {
    match observe() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            let _ = writeln!(
                io::stderr().lock(),
                "whitefoot lexical observer: {}",
                error.code()
            );
            ExitCode::from(2)
        }
    }
}

#[cfg(test)]
#[allow(clippy::expect_used, clippy::unwrap_used)]
mod tests;
