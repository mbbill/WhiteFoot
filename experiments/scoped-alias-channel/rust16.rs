use std::time::Instant;
struct Wide { c0: Vec<u64>, c1: Vec<u64>, c2: Vec<u64>, c3: Vec<u64>, c4: Vec<u64>, c5: Vec<u64>, c6: Vec<u64>, c7: Vec<u64>, c8: Vec<u64>, c9: Vec<u64>, c10: Vec<u64>, c11: Vec<u64>, c12: Vec<u64>, c13: Vec<u64>, c14: Vec<u64>, c15: Vec<u64> }
#[inline(never)]
fn kernel_obvious(s: &mut Wide) {
    let m = s.c0.len().min(s.c1.len().min(s.c2.len().min(s.c3.len().min(s.c4.len().min(s.c5.len().min(s.c6.len().min(s.c7.len().min(s.c8.len().min(s.c9.len().min(s.c10.len().min(s.c11.len().min(s.c12.len().min(s.c13.len().min(s.c14.len().min(s.c15.len())))))))))))))));
    for i in 0..m {
        s.c0[i] = s.c0[i].wrapping_add(s.c4[i]).wrapping_add(s.c5[i]).wrapping_add(s.c6[i]);
        s.c1[i] = s.c1[i].wrapping_add(s.c7[i]).wrapping_add(s.c8[i]).wrapping_add(s.c9[i]);
        s.c2[i] = s.c2[i].wrapping_add(s.c10[i]).wrapping_add(s.c11[i]).wrapping_add(s.c12[i]);
        s.c3[i] = s.c3[i].wrapping_add(s.c13[i]).wrapping_add(s.c14[i]).wrapping_add(s.c15[i]);
    }
}
fn mk(n: usize, seed: u64) -> Vec<u64> { (0..n as u64).map(|i| seed + i).collect() }
fn main() {
    let n: usize = std::env::args().nth(1).and_then(|s| s.parse().ok()).unwrap_or(4096);
    let k: usize = std::env::args().nth(2).and_then(|s| s.parse().ok()).unwrap_or(20000);
    let mut s = Wide { c0: mk(n,1), c1: mk(n,2), c2: mk(n,3), c3: mk(n,4), c4: mk(n,5), c5: mk(n,6), c6: mk(n,7), c7: mk(n,8), c8: mk(n,9), c9: mk(n,10), c10: mk(n,11), c11: mk(n,12), c12: mk(n,13), c13: mk(n,14), c14: mk(n,15), c15: mk(n,16) };
    for _ in 0..50 { kernel_obvious(&mut s); }
    let t0 = Instant::now();
    for _ in 0..k { kernel_obvious(std::hint::black_box(&mut s)); }
    let ns = t0.elapsed().as_nanos() as f64;
    let sum: u64 = (0..n).map(|i| s.c0[i] ^ s.c3[i]).fold(0, u64::wrapping_add);
    println!("rust16-obvious: n={n} k={k} ns/elem={:.3} checksum={sum}", ns / (n as f64 * k as f64));
}
