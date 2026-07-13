//! Correctness oracle for a generated xlang percent decoder.

use std::env;
use std::io::{self, Write};
use std::os::unix::process::ExitStatusExt as _;
use std::process::{Command, ExitCode};
use std::str;

use xlang_percent_decode_rust_baseline::decode_into;

#[repr(C)]
#[derive(Clone, Copy)]
struct Buf {
    p: *mut u8,
    n: i64,
}

unsafe extern "C" {
    fn xlang_decode_facts(out: Buf, src: Buf) -> u64;
    fn xlang_decode_nofacts(out: Buf, src: Buf) -> u64;
}

type Decoder = unsafe extern "C" fn(Buf, Buf) -> u64;
const CANARY: u8 = 0xA5;
const GUARD: usize = 32;
const EXPECTED_CASES: usize = 153_014;

fn hex_value(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        b'A'..=b'F' => Some(byte - b'A' + 10),
        _ => None,
    }
}

fn independent_oracle(src: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(src.len());
    let mut index = 0;
    while index < src.len() {
        if src[index] == b'%' && index + 2 < src.len() {
            if let (Some(high), Some(low)) = (hex_value(src[index + 1]), hex_value(src[index + 2]))
            {
                out.push((high << 4) | low);
                index += 3;
                continue;
            }
        }
        out.push(src[index]);
        index += 1;
    }
    out
}

fn hex_bytes(bytes: &[u8]) -> String {
    let mut text = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        use std::fmt::Write as _;
        let _ = write!(text, "{byte:02x}");
    }
    text
}

struct XlangObservation {
    returned: u64,
    actual: Vec<u8>,
    sentinel_unchanged: bool,
    source_unchanged: bool,
}

fn call_xlang(decoder: Decoder, src: &[u8]) -> XlangObservation {
    // The ABI permits a writable source pointer even though the contract
    // forbids mutation. Give the foreign function genuinely mutable backing
    // storage so that an illegal write is detected rather than invoking Rust
    // aliasing UB or faulting on a read-only static input.
    let mut source = src.to_vec();
    let source_before = source.clone();
    let visible_len = src.len() + 32;
    let mut storage = vec![CANARY; GUARD + visible_len + GUARD];
    let out = &mut storage[GUARD..GUARD + visible_len];
    let returned = unsafe {
        decoder(
            Buf {
                p: out.as_mut_ptr(),
                n: i64::try_from(out.len()).expect("bounded corpus output length fits i64"),
            },
            Buf {
                p: source.as_mut_ptr(),
                n: i64::try_from(source.len()).expect("bounded corpus source length fits i64"),
            },
        )
    };
    let produced = usize::try_from(returned).ok();
    let actual_len = produced.unwrap_or(visible_len).min(visible_len);
    let sentinel_unchanged = storage[..GUARD].iter().all(|&byte| byte == CANARY)
        && produced.is_some_and(|length| {
            length <= visible_len && storage[GUARD + length..].iter().all(|&byte| byte == CANARY)
        });

    XlangObservation {
        returned,
        actual: storage[GUARD..GUARD + actual_len].to_vec(),
        sentinel_unchanged,
        source_unchanged: source == source_before,
    }
}

fn check_rust_case(label: &str, src: &[u8]) -> Result<(), String> {
    let expected = independent_oracle(src);
    let source = src.to_vec();
    let source_before = source.clone();

    let visible_len = src.len() + 32;
    let mut rust_storage = vec![CANARY; GUARD + visible_len + GUARD];
    let rust_out = &mut rust_storage[GUARD..GUARD + visible_len];
    let rust_produced = decode_into(rust_out, &source)
        .map_err(|_| format!("{label}: shipped Rust rejected input-sized capacity"))?;
    if rust_produced != expected.len() || rust_out[..rust_produced] != expected {
        return Err(format!(
            "{label}: independent oracle disagrees with shipped Rust"
        ));
    }
    if rust_storage[..GUARD].iter().any(|&byte| byte != CANARY)
        || rust_storage[GUARD + rust_produced..]
            .iter()
            .any(|&byte| byte != CANARY)
    {
        return Err(format!(
            "{label}: shipped Rust modified a guard or unused suffix"
        ));
    }
    if source != source_before {
        return Err(format!("{label}: shipped Rust mutated the source buffer"));
    }
    Ok(())
}

fn check_xlang_variant(
    label: &str,
    name: &str,
    decoder: Decoder,
    src: &[u8],
    expected: &[u8],
) -> Result<(), String> {
    let observed = call_xlang(decoder, src);
    let returned_matches =
        usize::try_from(observed.returned).is_ok_and(|returned| returned == expected.len());
    if !returned_matches
        || observed.actual != expected
        || !observed.sentinel_unchanged
        || !observed.source_unchanged
    {
        return Err(format!(
            "{label}/{name}: input={} expected={} actual={} returned={} expected_length={} sentinel_unchanged={} source_unchanged={}",
            hex_bytes(src),
            hex_bytes(expected),
            hex_bytes(&observed.actual),
            observed.returned,
            expected.len(),
            observed.sentinel_unchanged,
            observed.source_unchanged,
        ));
    }
    Ok(())
}

#[derive(Clone, Copy)]
struct XorShift64Star(u64);

impl XorShift64Star {
    fn next(&mut self) -> u64 {
        let mut value = self.0;
        value ^= value >> 12;
        value ^= value << 25;
        value ^= value >> 27;
        self.0 = value;
        value.wrapping_mul(2_685_821_657_736_338_717)
    }
}

fn visit_cases<E>(mut visit: impl FnMut(&str, &[u8]) -> Result<(), E>) -> Result<usize, E> {
    let mut cases = 0;
    visit("empty", b"")?;
    cases += 1;
    for byte in 0_u16..=255 {
        visit(&format!("one-byte-{byte:02x}"), &[byte as u8])?;
        cases += 1;
    }
    visit("truncated-percent", b"%")?;
    cases += 1;
    for byte in 0_u16..=255 {
        visit(
            &format!("truncated-percent-{byte:02x}"),
            &[b'%', byte as u8],
        )?;
        cases += 1;
    }

    for high in 0_u16..=255 {
        for low in 0_u16..=255 {
            let case = [b'%', high as u8, low as u8];
            visit(&format!("percent-pair-{high:02x}-{low:02x}"), &case)?;
            cases += 1;
        }
    }

    const HEX: &[u8; 16] = b"0123456789ABCDEF";
    for first in 0_u16..=255 {
        for second in 0_u16..=255 {
            let case = [
                b'%',
                HEX[(first >> 4) as usize],
                HEX[(first & 15) as usize],
                b'%',
                HEX[(second >> 4) as usize],
                HEX[(second & 15) as usize],
            ];
            visit(&format!("adjacent-{first:02x}-{second:02x}"), &case)?;
            cases += 1;
        }
    }
    for byte in 0_u16..=255 {
        let high = HEX[(byte >> 4) as usize];
        let low = HEX[(byte & 15) as usize];
        for (name, case) in [
            ("escape-percent", vec![b'%', high, low, b'%']),
            ("percent-escape", vec![b'%', b'%', high, low]),
            ("double-percent-escape", vec![b'%', b'%', b'%', high, low]),
        ] {
            visit(&format!("{name}-{byte:02x}"), &case)?;
            cases += 1;
        }
    }
    const ALL_HEX: &[u8; 22] = b"0123456789ABCDEFabcdef";
    for &first in ALL_HEX {
        for &second in ALL_HEX {
            for &third in ALL_HEX {
                let case = [b'%', first, b'%', second, third];
                visit(
                    &format!("split-hex-{first:02x}-{second:02x}-{third:02x}"),
                    &case,
                )?;
                cases += 1;
            }
        }
    }

    let static_cases: &[&[u8]] = &[
        b"plain",
        b"100%",
        b"%GG",
        b"%4Z",
        b"%00",
        b"%ff",
        b"%41%42%43",
        b"a%%41b",
        b"%2%30",
        b"%%%",
        b"%25%32%35",
        &[0x00, 0x25, 0x46, 0x46, 0xFF],
    ];
    for (index, case) in static_cases.iter().enumerate() {
        visit(&format!("static-{index}"), case)?;
        cases += 1;
    }

    let mut rng = XorShift64Star(0x5045_5243_454E_5432);
    for index in 0..10_000 {
        let size = (rng.next() % 4097) as usize;
        let mut case = Vec::with_capacity(size);
        for _ in 0..size {
            let random = rng.next();
            case.push(if random & 7 == 0 {
                b'%'
            } else {
                (random >> 8) as u8
            });
        }
        visit(&format!("fuzz-{index}-len-{size}"), &case)?;
        cases += 1;
    }
    Ok(cases)
}

#[derive(Debug, Eq, PartialEq)]
struct ProgressSummary {
    calls: usize,
    last_case_index: usize,
    last_variant: &'static str,
}

fn parse_worker_progress(stdout: &[u8]) -> Result<ProgressSummary, String> {
    let text = str::from_utf8(stdout).map_err(|error| format!("progress is not UTF-8: {error}"))?;
    if text.is_empty() {
        return Err("worker emitted no progress".to_string());
    }
    if !text.ends_with('\n') {
        return Err("worker progress lacks its final newline".to_string());
    }

    let mut calls = 0;
    let mut last_case_index = 0;
    let mut last_variant = "";
    for (ordinal, line) in text.split_terminator('\n').enumerate() {
        let (case_text, variant) = line
            .split_once('\t')
            .ok_or_else(|| format!("progress row {ordinal} lacks one tab"))?;
        if variant.contains('\t') {
            return Err(format!("progress row {ordinal} contains extra fields"));
        }
        let expected_case = ordinal / 2;
        if expected_case >= EXPECTED_CASES {
            return Err("worker emitted progress past the frozen corpus".to_string());
        }
        if case_text != expected_case.to_string() {
            return Err(format!(
                "progress row {ordinal} names case {case_text}, expected {expected_case}"
            ));
        }
        let expected_variant = if ordinal % 2 == 0 {
            "facts-on"
        } else {
            "facts-off"
        };
        if variant != expected_variant {
            return Err(format!(
                "progress row {ordinal} names variant {variant:?}, expected {expected_variant:?}"
            ));
        }
        calls += 1;
        last_case_index = expected_case;
        last_variant = expected_variant;
    }

    Ok(ProgressSummary {
        calls,
        last_case_index,
        last_variant,
    })
}

enum CaseLookupStop {
    Found { label: String, src: Vec<u8> },
}

fn corpus_case_at(target: usize) -> Result<(String, Vec<u8>), String> {
    let mut index = 0;
    let outcome: Result<usize, CaseLookupStop> = visit_cases(|label, src| {
        if index == target {
            return Err(CaseLookupStop::Found {
                label: label.to_string(),
                src: src.to_vec(),
            });
        }
        index += 1;
        Ok(())
    });
    match outcome {
        Err(CaseLookupStop::Found { label, src }) => Ok((label, src)),
        Ok(cases) => Err(format!(
            "case index {target} is outside the generated corpus of {cases} cases"
        )),
    }
}

fn signal_termination_message(label: &str, src: &[u8], variant: &str, signal: i32) -> String {
    let expected = independent_oracle(src);
    format!(
        "{label}/{variant}: input={} expected={} expected_length={} expected_termination=success actual=unavailable actual_termination=signal-{signal} returned=unavailable sentinel_unchanged=unavailable source_unchanged=unavailable",
        hex_bytes(src),
        hex_bytes(&expected),
        expected.len(),
    )
}

enum WorkerFailure {
    Candidate(String),
    Harness(String),
}

fn run_xlang_worker() -> ExitCode {
    let stdout = io::stdout();
    let mut progress = stdout.lock();
    let mut case_index = 0;
    let outcome = visit_cases(|label, src| {
        let expected = independent_oracle(src);
        for (name, decoder) in [
            ("facts-on", xlang_decode_facts as Decoder),
            ("facts-off", xlang_decode_nofacts as Decoder),
        ] {
            writeln!(progress, "{case_index}\t{name}")
                .and_then(|()| progress.flush())
                .map_err(|error| {
                    WorkerFailure::Harness(format!("write worker progress: {error}"))
                })?;
            check_xlang_variant(label, name, decoder, src, &expected)
                .map_err(WorkerFailure::Candidate)?;
        }
        case_index += 1;
        Ok::<(), WorkerFailure>(())
    });

    match outcome {
        Ok(cases) if cases == EXPECTED_CASES && case_index == EXPECTED_CASES => ExitCode::SUCCESS,
        Ok(cases) => {
            eprintln!(
                "HARNESS: xlang worker generated {cases} cases and completed {case_index}, expected {EXPECTED_CASES}"
            );
            ExitCode::from(2)
        }
        Err(WorkerFailure::Candidate(error)) => {
            eprintln!("{error}");
            ExitCode::from(1)
        }
        Err(WorkerFailure::Harness(error)) => {
            eprintln!("HARNESS: {error}");
            ExitCode::from(2)
        }
    }
}

fn harness_worker_failure(message: &str, stderr: &[u8]) -> ExitCode {
    eprintln!("harness xlang worker failure: {message}");
    if !stderr.is_empty() {
        eprintln!("worker stderr:\n{}", String::from_utf8_lossy(stderr));
    }
    ExitCode::from(2)
}

fn run_parent() -> ExitCode {
    let preflight_cases = match visit_cases(check_rust_case) {
        Ok(cases) if cases == EXPECTED_CASES => cases,
        Ok(cases) => {
            eprintln!("harness preflight generated {cases} cases, expected {EXPECTED_CASES}");
            return ExitCode::from(2);
        }
        Err(error) => {
            eprintln!("harness Rust/oracle preflight failed: {error}");
            return ExitCode::from(2);
        }
    };
    debug_assert_eq!(preflight_cases, EXPECTED_CASES);

    let executable = match env::current_exe() {
        Ok(executable) => executable,
        Err(error) => {
            eprintln!("harness could not locate the verifier executable: {error}");
            return ExitCode::from(2);
        }
    };
    let worker = match Command::new(executable).arg("--xlang-worker").output() {
        Ok(worker) => worker,
        Err(error) => {
            eprintln!("harness could not start the xlang worker: {error}");
            return ExitCode::from(2);
        }
    };

    let progress = match parse_worker_progress(&worker.stdout) {
        Ok(progress) => progress,
        Err(error) => {
            return harness_worker_failure(&format!("invalid progress: {error}"), &worker.stderr);
        }
    };

    match worker.status.code() {
        Some(0) => {
            if !worker.stderr.is_empty() {
                return harness_worker_failure("successful worker emitted stderr", &worker.stderr);
            }
            if progress.calls != EXPECTED_CASES * 2
                || progress.last_case_index != EXPECTED_CASES - 1
                || progress.last_variant != "facts-off"
            {
                return harness_worker_failure(
                    "successful worker did not complete the frozen progress sequence",
                    &worker.stderr,
                );
            }
            println!("correct cases={EXPECTED_CASES}");
            ExitCode::SUCCESS
        }
        Some(1) => {
            let stderr = match str::from_utf8(&worker.stderr) {
                Ok(stderr) if !stderr.is_empty() => stderr,
                Ok(_) => {
                    return harness_worker_failure(
                        "candidate-failure worker emitted no diagnostic",
                        &worker.stderr,
                    );
                }
                Err(error) => {
                    return harness_worker_failure(
                        &format!("candidate diagnostic is not UTF-8: {error}"),
                        &worker.stderr,
                    );
                }
            };
            let (label, src) = match corpus_case_at(progress.last_case_index) {
                Ok(case) => case,
                Err(error) => return harness_worker_failure(&error, &worker.stderr),
            };
            let expected_prefix = format!(
                "{label}/{}: input={}",
                progress.last_variant,
                hex_bytes(&src)
            );
            if !stderr.starts_with(&expected_prefix) || !stderr.ends_with('\n') {
                return harness_worker_failure(
                    "candidate diagnostic does not bind the last progress record",
                    &worker.stderr,
                );
            }
            if let Err(error) = io::stderr().write_all(&worker.stderr) {
                eprintln!("harness could not forward the candidate diagnostic: {error}");
                return ExitCode::from(2);
            }
            ExitCode::from(1)
        }
        Some(code) => harness_worker_failure(
            &format!("worker exited with unexpected status {code}"),
            &worker.stderr,
        ),
        None => {
            let Some(signal) = worker.status.signal() else {
                return harness_worker_failure(
                    "worker terminated without an exit code or signal",
                    &worker.stderr,
                );
            };
            let (label, src) = match corpus_case_at(progress.last_case_index) {
                Ok(case) => case,
                Err(error) => return harness_worker_failure(&error, &worker.stderr),
            };
            eprintln!(
                "{}",
                signal_termination_message(&label, &src, progress.last_variant, signal,)
            );
            ExitCode::from(1)
        }
    }
}

fn main() -> ExitCode {
    let mut arguments = env::args_os().skip(1);
    match (arguments.next(), arguments.next()) {
        (None, None) => run_parent(),
        (Some(flag), None) if flag == "--xlang-worker" => run_xlang_worker(),
        _ => {
            eprintln!("harness verifier accepts only the internal --xlang-worker flag");
            ExitCode::from(2)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{
        corpus_case_at, hex_bytes, parse_worker_progress, signal_termination_message,
        ProgressSummary,
    };

    #[test]
    fn diagnostic_hex_includes_the_complete_case() {
        let bytes: Vec<u8> = (0..=255).cycle().take(4_096).collect();
        let encoded = hex_bytes(&bytes);
        assert_eq!(encoded.len(), bytes.len() * 2);
        assert_eq!(&encoded[..8], "00010203");
        assert_eq!(&encoded[encoded.len() - 8..], "fcfdfeff");
    }

    #[test]
    fn corpus_index_lookup_uses_the_frozen_order() {
        assert_eq!(corpus_case_at(0).unwrap(), ("empty".to_string(), vec![]));
        assert_eq!(
            corpus_case_at(257).unwrap(),
            ("truncated-percent".to_string(), b"%".to_vec())
        );
        assert_eq!(
            corpus_case_at(258).unwrap(),
            ("truncated-percent-00".to_string(), vec![b'%', 0])
        );
    }

    #[test]
    fn progress_parser_accepts_only_a_stable_sequence_prefix() {
        assert_eq!(
            parse_worker_progress(b"0\tfacts-on\n0\tfacts-off\n1\tfacts-on\n").unwrap(),
            ProgressSummary {
                calls: 3,
                last_case_index: 1,
                last_variant: "facts-on",
            }
        );
        assert!(parse_worker_progress(b"0\tfacts-off\n").is_err());
        assert!(parse_worker_progress(b"0\tfacts-on").is_err());
        assert!(parse_worker_progress(b"0\tfacts-on\n2\tfacts-off\n").is_err());
    }

    #[test]
    fn signal_diagnostic_marks_every_unobservable_field() {
        assert_eq!(
            signal_termination_message("probe", b"%41\xff", "facts-off", 4),
            "probe/facts-off: input=253431ff expected=41ff expected_length=2 expected_termination=success actual=unavailable actual_termination=signal-4 returned=unavailable sentinel_unchanged=unavailable source_unchanged=unavailable"
        );
    }
}
