#![forbid(unsafe_code)]

use whitefoot::{KERNEL_SPEC_V0_11_HASH, SYNTAX_DATA_SPEC_V0_11, TERMINAL_CONTRACT_SPEC_V0_11};

const ACTIVE_SPEC: &[u8] = include_bytes!("../../../spec/kernel-spec-v0.11.md");
const APPROVED_CANDIDATE: &[u8] =
    include_bytes!("../../../governance/spec-evolution/kernel-spec-v0.11-candidate.md");

fn main() {
    if ACTIVE_SPEC != APPROVED_CANDIDATE {
        eprintln!("spec/kernel-spec-v0.11.md differs from the approved candidate");
        std::process::exit(1);
    }
    if SYNTAX_DATA_SPEC_V0_11 != KERNEL_SPEC_V0_11_HASH
        || TERMINAL_CONTRACT_SPEC_V0_11 != KERNEL_SPEC_V0_11_HASH
    {
        eprintln!("frontend data is not bound to the active v0.11 identity");
        std::process::exit(1);
    }
    println!("Whitefoot v0.11 frontend identity: {KERNEL_SPEC_V0_11_HASH}");
}
