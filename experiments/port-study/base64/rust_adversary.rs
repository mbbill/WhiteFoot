// The pre-registered honest adversary for the base64 proof-tier result:
// can safe Rust recover the check elision via the assert-up-front idiom?
// Four variants, same 3:4 algorithm as b64.xl, plus the unsafe ceiling.
use std::time::Instant;

const B64: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

#[inline(never)]
fn encode_naive(out: &mut [u8], src: &[u8]) -> usize {
    let (mut i, mut o) = (0usize, 0usize);
    while src.len() - i >= 3 {
        let acc = (src[i] as u32) << 16 | (src[i + 1] as u32) << 8 | src[i + 2] as u32;
        out[o] = B64[(acc >> 18) as usize & 63];
        out[o + 1] = B64[(acc >> 12) as usize & 63];
        out[o + 2] = B64[(acc >> 6) as usize & 63];
        out[o + 3] = B64[acc as usize & 63];
        i += 3; o += 4;
    }
    o
}

#[inline(never)]
fn encode_assert(out: &mut [u8], src: &[u8]) -> usize {
    // the requires-equivalent, hoisted for LLVM to consume
    assert!(src.len() <= 3 * (out.len() / 4));
    let (mut i, mut o) = (0usize, 0usize);
    while src.len() - i >= 3 {
        let acc = (src[i] as u32) << 16 | (src[i + 1] as u32) << 8 | src[i + 2] as u32;
        out[o] = B64[(acc >> 18) as usize & 63];
        out[o + 1] = B64[(acc >> 12) as usize & 63];
        out[o + 2] = B64[(acc >> 6) as usize & 63];
        out[o + 3] = B64[acc as usize & 63];
        i += 3; o += 4;
    }
    o
}

#[inline(never)]
fn encode_idiomatic(out: &mut [u8], src: &[u8]) -> usize {
    // the expert shape: chunk iterators, bounds checks structurally avoided
    let mut o = 0usize;
    for (chunk, dst) in src.chunks_exact(3).zip(out.chunks_exact_mut(4)) {
        let acc = (chunk[0] as u32) << 16 | (chunk[1] as u32) << 8 | chunk[2] as u32;
        dst[0] = B64[(acc >> 18) as usize & 63];
        dst[1] = B64[(acc >> 12) as usize & 63];
        dst[2] = B64[(acc >> 6) as usize & 63];
        dst[3] = B64[acc as usize & 63];
        o += 4;
    }
    o
}

#[inline(never)]
fn encode_unchecked(out: &mut [u8], src: &[u8]) -> usize {
    assert!(src.len() <= 3 * (out.len() / 4));
    let (mut i, mut o) = (0usize, 0usize);
    unsafe {
        while src.len() - i >= 3 {
            let acc = (*src.get_unchecked(i) as u32) << 16
                | (*src.get_unchecked(i + 1) as u32) << 8
                | *src.get_unchecked(i + 2) as u32;
            *out.get_unchecked_mut(o) = *B64.get_unchecked((acc >> 18) as usize & 63);
            *out.get_unchecked_mut(o + 1) = *B64.get_unchecked((acc >> 12) as usize & 63);
            *out.get_unchecked_mut(o + 2) = *B64.get_unchecked((acc >> 6) as usize & 63);
            *out.get_unchecked_mut(o + 3) = *B64.get_unchecked(acc as usize & 63);
            i += 3; o += 4;
        }
    }
    o
}

fn run(name: &str, f: fn(&mut [u8], &[u8]) -> usize, src: &[u8], out: &mut [u8]) {
    for _ in 0..2 { f(out, src); }
    let t0 = Instant::now();
    let mut sink = 0usize;
    for _ in 0..5 { sink ^= f(out, src); }
    let ns = t0.elapsed().as_nanos() as f64;
    println!("{name}: {:.3} GB/s ({:.1} ms/pass, sink={sink})",
             src.len() as f64 * 5.0 / ns, ns / 5e6);
}

fn main() {
    let n = 384_000_000usize;
    let src: Vec<u8> = (0..n).map(|i| (i.wrapping_mul(131).wrapping_add(7)) as u8).collect();
    let mut out = vec![0u8; (n + 2) / 3 * 4 + 16];
    run("rust-naive-indexed", encode_naive, &src, &mut out);
    run("rust-assert-upfront", encode_assert, &src, &mut out);
    run("rust-idiomatic-chunks", encode_idiomatic, &src, &mut out);
    run("rust-unsafe-ceiling", encode_unchecked, &src, &mut out);
}
