//! Frozen shipped-Rust baseline for the percent-decode default-floor study.
//!
//! The decoding algorithm is not reimplemented here. [`decode_into`] consumes
//! the public `percent_encoding::percent_decode` iterator and writes each item
//! sequentially into a caller-owned output slice.

use percent_encoding::percent_decode;

/// The output buffer cannot hold percent-decode's worst-case 1:1 output.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct OutputTooSmall;

/// Percent-decode `src` into caller-owned storage.
///
/// The wrapper requires `out.len() >= src.len()` before writing. A valid
/// `%HH` escape contracts three input bytes to one output byte, while ordinary,
/// invalid, and truncated escape bytes are preserved by the upstream iterator.
/// The returned count identifies the written prefix; the remaining suffix is
/// left untouched.
///
/// This is the entry point intended for the timed Rust path.
pub fn decode_into(out: &mut [u8], src: &[u8]) -> Result<usize, OutputTooSmall> {
    if out.len() < src.len() {
        return Err(OutputTooSmall);
    }

    let mut produced = 0;
    for byte in percent_decode(src) {
        out[produced] = byte;
        produced += 1;
    }
    Ok(produced)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn decoded(src: &[u8]) -> Vec<u8> {
        let mut out = vec![0xA5; src.len()];
        let produced = decode_into(&mut out, src).expect("input-sized output is sufficient");
        out.truncate(produced);
        out
    }

    #[test]
    fn decodes_valid_upper_and_lowercase_escapes() {
        assert_eq!(decoded(b"foo%20bar%3f"), b"foo bar?");
        assert_eq!(decoded(b"%00%7F%80%FF"), [0x00, 0x7F, 0x80, 0xFF]);
        assert_eq!(decoded(b"plain"), b"plain");
    }

    #[test]
    fn preserves_invalid_and_truncated_escapes() {
        let cases: &[&[u8]] = &[b"%", b"%2", b"%GG", b"%4Z", b"left%2Gright", b"100%"];
        for &case in cases {
            assert_eq!(decoded(case), case);
        }
    }

    #[test]
    fn leaves_unused_output_suffix_untouched() {
        let src = b"A%20B%2fC";
        let mut out = [0xA5; 32];
        let produced = decode_into(&mut out, src).unwrap();

        assert_eq!(&out[..produced], b"A B/C");
        assert!(out[produced..].iter().all(|&byte| byte == 0xA5));
    }

    #[test]
    fn rejects_less_than_worst_case_capacity_before_writing() {
        let src = b"%41";
        let mut out = [0xA5; 2];
        assert_eq!(decode_into(&mut out, src), Err(OutputTooSmall));
        assert_eq!(out, [0xA5; 2]);
    }

    #[test]
    fn exact_capacity_handles_binary_output() {
        let src = b"%00hello%20world%ff";
        let mut out = vec![0xA5; src.len()];
        let produced = decode_into(&mut out, src).unwrap();
        assert_eq!(&out[..produced], b"\0hello world\xff");
        assert!(out[produced..].iter().all(|&byte| byte == 0xA5));
    }

    #[test]
    fn accepts_empty_input_and_output() {
        assert_eq!(decode_into(&mut [], &[]), Ok(0));
    }
}
