#![forbid(unsafe_code)]

use std::env;
use std::fs::File;
use std::io::Read;
use std::path::PathBuf;
use std::process::ExitCode;

use whitefoot_contract::{KERNEL_SPEC_V0_9_HASH, SourceBundle, SourceInput, SourceLimits};
use whitefoot_lexer::{LexLimits, LexOutcome, lex_v0_9};
use whitefoot_syntax::{
    CanonicalLimits, CanonicalOutcome, FinalizeLimits, FinalizeOutcome, ParseLimits, ParseOutcome,
    TerminalLimits, TerminalOutcome, audit_canonical_v0_9, classify_terminals_v0_9, finalize_v0_9,
    parse_v0_9,
};

const SOURCE_LIMITS: SourceLimits = SourceLimits {
    max_sources: 4_096,
    max_logical_path_bytes: 4_096,
    max_source_bytes: 16_777_216,
    max_total_source_bytes: 67_108_864,
    max_binding_bytes: 134_217_728,
};

const LEX_LIMITS: LexLimits = LexLimits {
    max_sources: 4_096,
    max_source_bytes: 16_777_216,
    max_total_source_bytes: 67_108_864,
    max_token_bytes: 1_048_576,
    max_tokens: 2_097_152,
    max_lexemes: 4_194_304,
};

const PARSE_LIMITS: ParseLimits = ParseLimits {
    max_work: 4_294_967_296,
    max_tasks: 4_194_304,
    max_frames: 65_536,
    max_elements: 8_388_608,
};

const FINALIZE_LIMITS: FinalizeLimits = FinalizeLimits {
    max_work: 4_294_967_296,
    max_roots: 8_388_608,
    max_shape_tasks: 131_072,
    max_nodes: 8_388_608,
    max_child_edges: 8_388_608,
    max_terminals: 2_097_152,
    max_sources: 4_096,
};

const CANONICAL_LIMITS: CanonicalLimits = CanonicalLimits {
    max_work: 4_294_967_296,
    max_source_bytes: 16_777_216,
    max_total_source_bytes: 67_108_864,
    max_gaps: 2_097_152,
    max_path_components: 65_536,
};

struct OwnedInput {
    logical_path: String,
    bytes: Vec<u8>,
}

fn read_bounded(path: &PathBuf) -> Result<Vec<u8>, String> {
    let mut file =
        File::open(path).map_err(|error| format!("could not open {}: {error}", path.display()))?;
    let metadata = file
        .metadata()
        .map_err(|error| format!("could not inspect {}: {error}", path.display()))?;
    if !metadata.is_file() {
        return Err(format!("input is not a regular file: {}", path.display()));
    }
    if metadata.len() > SOURCE_LIMITS.max_source_bytes {
        return Err(format!(
            "observer source-byte cap exceeded by {}",
            path.display()
        ));
    }
    let hinted = usize::try_from(metadata.len())
        .map_err(|_| format!("input length is not addressable: {}", path.display()))?;
    let mut bytes = Vec::new();
    bytes
        .try_reserve_exact(hinted)
        .map_err(|_| format!("could not reserve input bytes: {}", path.display()))?;
    let mut buffer = [0_u8; 8_192];
    loop {
        let read = file
            .read(&mut buffer)
            .map_err(|error| format!("could not read {}: {error}", path.display()))?;
        if read == 0 {
            break;
        }
        let next = bytes
            .len()
            .checked_add(read)
            .ok_or_else(|| format!("input length overflow: {}", path.display()))?;
        let next_u64 = u64::try_from(next)
            .map_err(|_| format!("input length is not representable: {}", path.display()))?;
        if next_u64 > SOURCE_LIMITS.max_source_bytes {
            return Err(format!(
                "observer source-byte cap exceeded while reading {}",
                path.display()
            ));
        }
        bytes
            .try_reserve(read)
            .map_err(|_| format!("could not extend input bytes: {}", path.display()))?;
        bytes.extend_from_slice(&buffer[..read]);
    }
    Ok(bytes)
}

fn load_inputs(paths: &[PathBuf]) -> Result<Vec<OwnedInput>, String> {
    let mut inputs = Vec::new();
    inputs
        .try_reserve_exact(paths.len())
        .map_err(|_| "could not reserve evidence input list".to_owned())?;
    let mut total = 0_u64;
    for (index, path) in paths.iter().enumerate() {
        let bytes = read_bounded(path)?;
        let length = u64::try_from(bytes.len())
            .map_err(|_| format!("input length does not fit u64: {}", path.display()))?;
        total = total
            .checked_add(length)
            .ok_or_else(|| "observer total-source-byte count overflow".to_owned())?;
        if total > SOURCE_LIMITS.max_total_source_bytes {
            return Err("observer total-source-byte cap exceeded".to_owned());
        }
        inputs.push(OwnedInput {
            logical_path: format!("source-{index:08}.wf"),
            bytes,
        });
    }
    Ok(inputs)
}

fn observe(paths: &[PathBuf]) -> Result<String, String> {
    if paths.is_empty() {
        return Err("at least one source path is required".to_owned());
    }
    if paths.len() > SOURCE_LIMITS.max_sources as usize {
        return Err("observer source-count cap exceeded".to_owned());
    }
    let owned = load_inputs(paths)?;
    let mut borrowed = Vec::new();
    borrowed
        .try_reserve_exact(owned.len())
        .map_err(|_| "could not reserve borrowed input views".to_owned())?;
    for input in &owned {
        borrowed.push(SourceInput::new(&input.logical_path, &input.bytes));
    }
    let source = SourceBundle::with_limits(&borrowed, SOURCE_LIMITS)
        .map_err(|error| format!("source:{error}"))?;
    let total_source_bytes = source.total_bytes();
    let lexed = match lex_v0_9(&source, LEX_LIMITS) {
        LexOutcome::Complete(value) => value,
        outcome => return Err(format!("lex:{outcome:?}")),
    };
    let lexemes = u64::try_from(lexed.lexemes().len())
        .map_err(|_| "lexeme count does not fit u64".to_owned())?;
    let tokens = lexed.token_count();
    let classified = match classify_terminals_v0_9(
        &lexed,
        KERNEL_SPEC_V0_9_HASH,
        TerminalLimits {
            max_tokens: LEX_LIMITS.max_tokens,
        },
    ) {
        TerminalOutcome::Complete(value) => value,
        outcome => return Err(format!("classify:{outcome:?}")),
    };
    let parsed = match parse_v0_9(&classified, PARSE_LIMITS) {
        ParseOutcome::Complete(value) => value,
        outcome => return Err(format!("parse:{outcome:?}")),
    };
    let parsed_elements = u64::try_from(parsed.element_count())
        .map_err(|_| "parsed element count does not fit u64".to_owned())?;
    let finalized = match finalize_v0_9(parsed, FINALIZE_LIMITS) {
        FinalizeOutcome::Complete(value) => value,
        outcome => return Err(format!("finalize:{outcome:?}")),
    };
    let canonical = match audit_canonical_v0_9(finalized, CANONICAL_LIMITS) {
        CanonicalOutcome::Complete(value) => value,
        outcome => return Err(format!("canonical:{outcome:?}")),
    };
    let nodes = u64::try_from(canonical.node_count())
        .map_err(|_| "node count does not fit u64".to_owned())?;
    let terminals = u64::try_from(canonical.terminal_count())
        .map_err(|_| "terminal count does not fit u64".to_owned())?;
    let mixed_elements = nodes
        .checked_sub(1)
        .and_then(|value| value.checked_add(terminals))
        .ok_or_else(|| "mixed-element count overflow".to_owned())?;
    let sources =
        u64::try_from(source.len()).map_err(|_| "source count does not fit u64".to_owned())?;
    Ok(format!(
        "{{\"evidence_scope\":\"v0.9-dependent-topology-cross-check\",\"specification\":\"{KERNEL_SPEC_V0_9_HASH}\",\"sources\":{sources},\"source_bytes\":{total_source_bytes},\"lexemes\":{lexemes},\"tokens\":{tokens},\"classified_tokens\":{tokens},\"parsed_elements\":{parsed_elements},\"production_nodes\":{nodes},\"terminals\":{terminals},\"projected_mixed_elements\":{mixed_elements}}}"
    ))
}

fn collect_paths() -> Result<Vec<PathBuf>, String> {
    let mut paths = Vec::new();
    for argument in env::args_os().skip(1) {
        if paths.len() >= SOURCE_LIMITS.max_sources as usize {
            return Err("observer source-count cap exceeded".to_owned());
        }
        paths
            .try_reserve(1)
            .map_err(|_| "could not reserve observer path list".to_owned())?;
        paths.push(PathBuf::from(argument));
    }
    Ok(paths)
}

fn main() -> ExitCode {
    let paths = match collect_paths() {
        Ok(value) => value,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::from(2);
        }
    };
    match observe(&paths) {
        Ok(report) => {
            println!("{report}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("{error}");
            ExitCode::from(2)
        }
    }
}
