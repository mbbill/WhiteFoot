//! One balanced adversary block for the checked base64 encoder.
//!
//! The assert, idiomatic, and unsafe Rust candidates implement the same
//! padded-tail behavior and entry-capacity relation as the whitefoot encoder; the
//! naive candidate deliberately remains the no-entry-proof control. The
//! idiomatic candidate itself is fully safe Rust; unsafe code appears only in
//! the explicit unsafe baseline and the necessarily unsafe FFI wrapper.

use std::hint::black_box;
use std::time::Instant;

const B64: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

#[repr(C)]
#[derive(Clone, Copy)]
struct Buf {
    p: *mut u8,
    n: i64,
}

unsafe extern "C" {
    fn encode(out: Buf, src: Buf) -> u64;
}

type Kernel = fn(&mut [u8], &[u8]) -> usize;

#[inline(always)]
fn required_groups(src_len: usize) -> usize {
    src_len / 3 + usize::from(src_len % 3 != 0)
}

#[inline(always)]
fn assert_capacity(out_len: usize, src_len: usize) {
    assert!(required_groups(src_len) <= out_len / 4);
}

#[inline(always)]
fn write_tail(out: &mut [u8], tail: &[u8]) -> usize {
    match tail {
        [] => 0,
        [b0] => {
            out[0] = B64[(b0 >> 2) as usize];
            out[1] = B64[((b0 & 3) << 4) as usize];
            out[2] = b'=';
            out[3] = b'=';
            4
        }
        [b0, b1] => {
            let acc = (*b0 as u32) << 8 | *b1 as u32;
            out[0] = B64[((acc >> 10) & 63) as usize];
            out[1] = B64[((acc >> 4) & 63) as usize];
            out[2] = B64[((acc << 2) & 63) as usize];
            out[3] = b'=';
            4
        }
        _ => unreachable!(),
    }
}

#[inline(never)]
fn encode_whitefoot(out: &mut [u8], src: &[u8]) -> usize {
    let out = Buf {
        p: out.as_mut_ptr(),
        n: out.len().try_into().unwrap(),
    };
    let src = Buf {
        p: src.as_ptr().cast_mut(),
        n: src.len().try_into().unwrap(),
    };
    // SAFETY: the safe Rust caller supplies live, non-overlapping source and
    // output slices.  The retained whitefoot entry check independently establishes
    // output capacity; raw FFI itself does not establish aliasing or liveness.
    unsafe { encode(out, src) as usize }
}

#[inline(never)]
fn encode_naive(out: &mut [u8], src: &[u8]) -> usize {
    let (mut i, mut o) = (0usize, 0usize);
    while src.len() - i >= 3 {
        let acc = (src[i] as u32) << 16 | (src[i + 1] as u32) << 8 | src[i + 2] as u32;
        out[o] = B64[((acc >> 18) & 63) as usize];
        out[o + 1] = B64[((acc >> 12) & 63) as usize];
        out[o + 2] = B64[((acc >> 6) & 63) as usize];
        out[o + 3] = B64[(acc & 63) as usize];
        i += 3;
        o += 4;
    }
    o + write_tail(&mut out[o..], &src[i..])
}

#[inline(never)]
fn encode_assert(out: &mut [u8], src: &[u8]) -> usize {
    assert_capacity(out.len(), src.len());
    let (mut i, mut o) = (0usize, 0usize);
    while src.len() - i >= 3 {
        let acc = (src[i] as u32) << 16 | (src[i + 1] as u32) << 8 | src[i + 2] as u32;
        out[o] = B64[((acc >> 18) & 63) as usize];
        out[o + 1] = B64[((acc >> 12) & 63) as usize];
        out[o + 2] = B64[((acc >> 6) & 63) as usize];
        out[o + 3] = B64[(acc & 63) as usize];
        i += 3;
        o += 4;
    }
    o + write_tail(&mut out[o..], &src[i..])
}

#[inline(never)]
fn encode_idiomatic(out: &mut [u8], src: &[u8]) -> usize {
    assert_capacity(out.len(), src.len());
    let groups = src.len() / 3;
    let full_src_len = groups * 3;
    let full_out_len = groups * 4;
    let (full_src, tail) = src.split_at(full_src_len);
    let (full_out, tail_out) = out.split_at_mut(full_out_len);

    for (chunk, dst) in full_src.chunks_exact(3).zip(full_out.chunks_exact_mut(4)) {
        let acc = (chunk[0] as u32) << 16 | (chunk[1] as u32) << 8 | chunk[2] as u32;
        dst[0] = B64[((acc >> 18) & 63) as usize];
        dst[1] = B64[((acc >> 12) & 63) as usize];
        dst[2] = B64[((acc >> 6) & 63) as usize];
        dst[3] = B64[(acc & 63) as usize];
    }

    full_out_len + write_tail(tail_out, tail)
}

#[inline(never)]
fn encode_unchecked(out: &mut [u8], src: &[u8]) -> usize {
    assert_capacity(out.len(), src.len());
    let (mut i, mut o) = (0usize, 0usize);
    // SAFETY: the entry relation covers output, the loop guard covers input,
    // and every alphabet index is masked to 0..=63.
    unsafe {
        while src.len() - i >= 3 {
            let acc = (*src.get_unchecked(i) as u32) << 16
                | (*src.get_unchecked(i + 1) as u32) << 8
                | *src.get_unchecked(i + 2) as u32;
            *out.get_unchecked_mut(o) = *B64.get_unchecked(((acc >> 18) & 63) as usize);
            *out.get_unchecked_mut(o + 1) = *B64.get_unchecked(((acc >> 12) & 63) as usize);
            *out.get_unchecked_mut(o + 2) = *B64.get_unchecked(((acc >> 6) & 63) as usize);
            *out.get_unchecked_mut(o + 3) = *B64.get_unchecked((acc & 63) as usize);
            i += 3;
            o += 4;
        }
    }
    o + write_tail(&mut out[o..], &src[i..])
}

const VARIANTS: [(&str, Kernel); 5] = [
    ("whitefoot-proof", encode_whitefoot),
    ("rust-naive", encode_naive),
    ("rust-assert", encode_assert),
    ("rust-chunks-full", encode_idiomatic),
    ("rust-unsafe", encode_unchecked),
];

fn verify_equivalence() {
    for n in 0..=257usize {
        let src: Vec<u8> = (0..n)
            .map(|i| i.wrapping_mul(131).wrapping_add(7) as u8)
            .collect();
        let out_len = required_groups(n) * 4;
        let mut expected = vec![0xA5; out_len];
        let expected_len = encode_whitefoot(&mut expected, &src);
        for &(name, kernel) in &VARIANTS[1..] {
            let mut actual = vec![0x5A; out_len];
            let actual_len = kernel(&mut actual, &src);
            assert_eq!(actual_len, expected_len, "length mismatch: {name}, n={n}");
            assert_eq!(
                &actual[..actual_len],
                &expected[..expected_len],
                "output mismatch: {name}, n={n}"
            );
        }
    }
}

#[derive(Clone)]
struct Sample {
    position: usize,
    name: &'static str,
    nanos: u128,
    len: usize,
    checksum: u8,
}

fn run_one(kernel: Kernel, out: &mut [u8], src: &[u8]) -> (u128, usize, u8) {
    let start = Instant::now();
    let len = black_box(kernel(black_box(out), black_box(src)));
    let nanos = start.elapsed().as_nanos();
    let checksum = if len == 0 {
        0
    } else {
        out[0] ^ out[len / 2] ^ out[len - 1]
    };
    black_box(checksum);
    (nanos, len, checksum)
}

fn balanced_rows() -> Vec<[usize; 5]> {
    // Williams-balanced order for five treatments.  Adding each cyclic shift
    // and its reverse balances ordinal position and first-order carryover.
    let seed = [0usize, 1, 4, 2, 3];
    let mut rows = Vec::with_capacity(10);
    for shift in 0..5 {
        let row = seed.map(|value| (value + shift) % 5);
        rows.push(row);
        let mut reverse = row;
        reverse.reverse();
        rows.push(reverse);
    }
    rows
}

fn main() {
    let mut args = std::env::args().skip(1);
    let n = args
        .next()
        .map(|arg| arg.parse().expect("BYTES must be an integer"))
        .unwrap_or(384_000_000usize);
    let row_index = args
        .next()
        .map(|arg| arg.parse().expect("ROW must be an integer"))
        .unwrap_or(0usize);
    assert!(
        args.next().is_none(),
        "usage: paired_adversary [BYTES] [ROW]"
    );

    verify_equivalence();

    let src: Vec<u8> = (0..n)
        .map(|i| i.wrapping_mul(131).wrapping_add(7) as u8)
        .collect();
    let expected_len = required_groups(n) * 4;
    let mut out = vec![0u8; expected_len];

    // Equal warmup exposure, forward then reverse, before evidence collection.
    for &(_, kernel) in &VARIANTS {
        black_box(kernel(&mut out, &src));
    }
    for &(_, kernel) in VARIANTS.iter().rev() {
        black_box(kernel(&mut out, &src));
    }

    let rows = balanced_rows();
    let row = rows.get(row_index).expect("ROW must be in 0..10");
    let mut samples = Vec::with_capacity(VARIANTS.len());
    for (position, &variant) in row.iter().enumerate() {
        let (name, kernel) = VARIANTS[variant];
        let (nanos, len, checksum) = run_one(kernel, &mut out, &src);
        assert_eq!(len, expected_len, "benchmark length mismatch: {name}");
        samples.push(Sample {
            position,
            name,
            nanos,
            len,
            checksum,
        });
    }

    println!("sample,position,variant,nanos,len,checksum");
    for (ordinal, sample) in samples.iter().enumerate() {
        println!(
            "{ordinal},{},{},{},{},{}",
            sample.position, sample.name, sample.nanos, sample.len, sample.checksum
        );
    }
}
