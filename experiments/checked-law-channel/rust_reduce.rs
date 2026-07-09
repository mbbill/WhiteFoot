// Rust adversaries for the checked-law reduction. The language has no channel
// to state (let alone check) that saturating_add is associative, so:
// - obvious: the natural fold — LLVM must keep it serial.
// - expert: hand-reassociated 4 accumulators — the HUMAN asserts associativity;
//   nothing checks it (write the same shape with saturating_sub and it silently
//   computes garbage — that is the W3 contrast).
use std::time::Instant;

#[inline(never)]
fn reduce_obvious(b: &[u64]) -> u64 {
    b.iter().fold(0u64, |acc, &x| acc.saturating_add(x))
}

#[inline(never)]
fn reduce_expert(b: &[u64]) -> u64 {
    let mut a = [0u64; 4];
    let chunks = b.chunks_exact(4);
    let rem = chunks.remainder();
    for c in chunks {
        a[0] = a[0].saturating_add(c[0]);
        a[1] = a[1].saturating_add(c[1]);
        a[2] = a[2].saturating_add(c[2]);
        a[3] = a[3].saturating_add(c[3]);
    }
    let mut acc = a[0].saturating_add(a[1]).saturating_add(a[2].saturating_add(a[3]));
    for &x in rem { acc = acc.saturating_add(x); }
    acc
}

fn run(name: &str, n: usize, k: usize, f: fn(&[u64]) -> u64) {
    let b: Vec<u64> = (0..n as u64).map(|i| i.wrapping_mul(2654435761)).collect();
    let mut sink = 0u64;
    for _ in 0..20 { sink ^= f(&b); }
    let t0 = Instant::now();
    for _ in 0..k { sink ^= f(std::hint::black_box(&b)); }
    let ns = t0.elapsed().as_nanos() as f64;
    println!("{name}: n={n} k={k} ns/elem={:.4} sink={sink}", ns / (n as f64 * k as f64));
}

fn main() {
    let n: usize = std::env::args().nth(1).and_then(|s| s.parse().ok()).unwrap_or(65536);
    let k: usize = std::env::args().nth(2).and_then(|s| s.parse().ok()).unwrap_or(20000);
    run("rust-obvious", n, k, reduce_obvious);
    run("rust-expert", n, k, reduce_expert);
}
