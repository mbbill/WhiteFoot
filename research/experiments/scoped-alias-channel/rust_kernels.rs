// Rust adversaries for the scoped-alias channel benchmark. Same semantics as
// kernel.wf: two written columns, six read columns, loop to the min length.
// Three shapes: the obvious one, the header-rebind one, and the expert
// inner-fn-with-slice-params one (the only shape that hands LLVM noalias).
use std::time::Instant;

struct Cols { a: Vec<u64>, b: Vec<u64>, c: Vec<u64>, d: Vec<u64>,
              e: Vec<u64>, f: Vec<u64>, g: Vec<u64>, h: Vec<u64> }

fn m8(s: &Cols) -> usize {
    s.a.len().min(s.b.len()).min(s.c.len()).min(s.d.len())
       .min(s.e.len()).min(s.f.len()).min(s.g.len()).min(s.h.len())
}

#[inline(never)]
fn kernel_obvious(s: &mut Cols) {
    let m = m8(s);
    for i in 0..m {
        s.a[i] = s.a[i].wrapping_add(s.c[i]).wrapping_add(s.d[i])
                       .wrapping_add(s.e[i]).wrapping_add(s.f[i]);
        s.b[i] = s.b[i].wrapping_add(s.e[i]).wrapping_add(s.f[i])
                       .wrapping_add(s.g[i]).wrapping_add(s.h[i]);
    }
}

#[inline(never)]
fn kernel_rebind(s: &mut Cols) {
    let m = m8(s);
    let Cols { a, b, c, d, e, f, g, h } = s;
    let (a, b) = (&mut a[..m], &mut b[..m]);
    let (c, d, e, f, g, h) = (&c[..m], &d[..m], &e[..m], &f[..m], &g[..m], &h[..m]);
    for i in 0..m {
        a[i] = a[i].wrapping_add(c[i]).wrapping_add(d[i])
                   .wrapping_add(e[i]).wrapping_add(f[i]);
        b[i] = b[i].wrapping_add(e[i]).wrapping_add(f[i])
                   .wrapping_add(g[i]).wrapping_add(h[i]);
    }
}

#[inline(never)]
fn inner(a: &mut [u64], b: &mut [u64], c: &[u64], d: &[u64],
         e: &[u64], f: &[u64], g: &[u64], h: &[u64]) {
    let m = a.len().min(b.len()).min(c.len()).min(d.len())
             .min(e.len()).min(f.len()).min(g.len()).min(h.len());
    for i in 0..m {
        a[i] = a[i].wrapping_add(c[i]).wrapping_add(d[i])
                   .wrapping_add(e[i]).wrapping_add(f[i]);
        b[i] = b[i].wrapping_add(e[i]).wrapping_add(f[i])
                   .wrapping_add(g[i]).wrapping_add(h[i]);
    }
}

#[inline(never)]
fn kernel_innerfn(s: &mut Cols) {
    let Cols { a, b, c, d, e, f, g, h } = s;
    inner(a, b, c, d, e, f, g, h);
}

fn mk(n: usize, seed: u64) -> Vec<u64> { (0..n as u64).map(|i| seed + i).collect() }

fn run(name: &str, n: usize, k: usize, f: fn(&mut Cols)) {
    let mut s = Cols { a: mk(n,1), b: mk(n,2), c: mk(n,3), d: mk(n,4),
                       e: mk(n,5), f: mk(n,6), g: mk(n,7), h: mk(n,8) };
    for _ in 0..100 { f(&mut s); }
    let t0 = Instant::now();
    for _ in 0..k { f(std::hint::black_box(&mut s)); }
    let ns = t0.elapsed().as_nanos() as f64;
    let sum: u64 = (0..n).map(|i| s.a[i] ^ s.b[i]).fold(0, u64::wrapping_add);
    println!("{name}: n={n} k={k} ns/elem={:.3} checksum={sum}", ns / (n as f64 * k as f64));
}

fn main() {
    let n: usize = std::env::args().nth(1).and_then(|s| s.parse().ok()).unwrap_or(4096);
    let k: usize = std::env::args().nth(2).and_then(|s| s.parse().ok()).unwrap_or(100000);
    run("rust-obvious", n, k, kernel_obvious);
    run("rust-rebind", n, k, kernel_rebind);
    run("rust-innerfn", n, k, kernel_innerfn);
}
