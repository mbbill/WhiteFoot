#![forbid(unsafe_code)]
#![deny(missing_docs)]

//! The Whitefoot research compiler.
//!
//! The crate currently contains the v0.10 source frontend and direct lexical
//! resolver. Lower-level stages remain private implementation APIs, not
//! protocols; semantic checking and code generation come next.

mod lexer;
mod resolution;
mod source;
mod spec;
mod syntax;

pub use lexer::*;
pub use resolution::*;
pub use source::*;
pub use spec::*;
pub use syntax::grammar::*;
pub use syntax::terminal::*;
pub use syntax::*;
