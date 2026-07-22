// Sealed-table clone constant: measure HashMap<u64,u64>::clone() cost per entry.
// Flag closed: "assumed ~50-100 ns/entry; must be measured before the COW-republish
// M7 band is a meaningful falsifier."
// Platform: Apple M4, macOS (indicative constant; deploy target is Linux x86-64).
// std only (no external crates) so it runs offline.

use hashbrown::HashMap as HbMap;
use std::collections::HashMap;
use std::hint::black_box;
use std::time::Instant;

// SplitMix64: deterministic, uniform-ish pseudo-random u64 keys without a crate.
struct SplitMix64(u64);
impl SplitMix64 {
    #[inline]
    fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
}

fn build(n: usize) -> HashMap<u64, u64> {
    let mut m = HashMap::with_capacity(n);
    let mut r = SplitMix64(0x1234_5678_9ABC_DEF0);
    while m.len() < n {
        let k = r.next();
        m.insert(k, k ^ 0xA5A5_A5A5_A5A5_A5A5);
    }
    m
}

fn median(mut v: Vec<f64>) -> f64 {
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = v.len();
    if n % 2 == 1 { v[n / 2] } else { (v[n / 2 - 1] + v[n / 2]) / 2.0 }
}

fn bench(n: usize, runs: usize) {
    let m = build(n);
    // warmup (also warms the allocator's large-block path)
    for _ in 0..3 {
        let c = m.clone();
        black_box(c.len());
        drop(black_box(c));
    }
    let mut t_ns = Vec::with_capacity(runs);
    for _ in 0..runs {
        let start = Instant::now();
        let c = black_box(m.clone());
        let el = start.elapsed(); // time ONLY the clone
        black_box(c.len());
        drop(c); // drop happens after the timing window
        t_ns.push(el.as_nanos() as f64);
    }
    let med = median(t_ns.clone());
    let min = t_ns.iter().cloned().fold(f64::INFINITY, f64::min);
    println!(
        "n={:>9}  median_clone = {:>12.0} ns  =>  {:>6.2} ns/entry   (min {:>12.0} ns = {:.2} ns/entry)  [{} runs]",
        n, med, med / n as f64, min, min / n as f64, runs
    );
}

fn build_hb(n: usize) -> HbMap<u64, u64> {
    let mut m = HbMap::with_capacity(n);
    let mut r = SplitMix64(0x1234_5678_9ABC_DEF0);
    while m.len() < n {
        let k = r.next();
        m.insert(k, k ^ 0xA5A5_A5A5_A5A5_A5A5);
    }
    m
}

fn bench_hb(n: usize, runs: usize) {
    let m = build_hb(n);
    for _ in 0..3 {
        let c = m.clone();
        black_box(c.len());
        drop(black_box(c));
    }
    let mut t_ns = Vec::with_capacity(runs);
    for _ in 0..runs {
        let start = Instant::now();
        let c = black_box(m.clone());
        let el = start.elapsed();
        black_box(c.len());
        drop(c);
        t_ns.push(el.as_nanos() as f64);
    }
    let med = median(t_ns.clone());
    let min = t_ns.iter().cloned().fold(f64::INFINITY, f64::min);
    println!(
        "n={:>9}  median_clone = {:>12.0} ns  =>  {:>6.2} ns/entry   (min {:>12.0} ns = {:.2} ns/entry)  [{} runs]",
        n, med, med / n as f64, min, min / n as f64, runs
    );
}

// Owning-value clone: HashMap<u64, V> where V deep-clones (1 alloc + payload
// memcpy per entry). `mk` builds each stored value; the clone under test
// deep-clones all of them.
fn bench_owning<V: Clone>(label: &str, n: usize, runs: usize, mk: impl Fn() -> V) {
    let mut m: HashMap<u64, V> = HashMap::with_capacity(n);
    let mut r = SplitMix64(0x1234_5678_9ABC_DEF0);
    while m.len() < n {
        let k = r.next();
        m.insert(k, mk());
    }
    for _ in 0..3 {
        let c = m.clone();
        black_box(c.len());
        drop(black_box(c));
    }
    let mut t_ns = Vec::with_capacity(runs);
    for _ in 0..runs {
        let start = Instant::now();
        let c = black_box(m.clone());
        let el = start.elapsed(); // time ONLY the deep clone
        black_box(c.len());
        drop(c); // free the N allocations AFTER timing
        t_ns.push(el.as_nanos() as f64);
    }
    let med = median(t_ns.clone());
    let min = t_ns.iter().cloned().fold(f64::INFINITY, f64::min);
    println!(
        "{:<26} n={:>9}  median = {:>13.0} ns  =>  {:>7.1} ns/entry   (min {:>7.1} ns/entry)  [{} runs]",
        label, n, med, med / n as f64, min / n as f64, runs
    );
}

fn main() {
    println!("== sealed-table clone constant ==");
    println!("platform: Apple M4, macOS aarch64 (indicative; deploy target Linux x86-64)");
    println!("clone does NOT rehash; K,V = u64 (Copy); keys uniform SplitMix64; --release\n");
    println!("-- std::collections::HashMap<u64,u64> (SipHash-1-3 default; hashbrown-backed) --");
    bench(100_000, 15);
    bench(1_000_000, 12);
    bench(10_000_000, 10);
    println!("\n-- hashbrown::HashMap<u64,u64> v0.17.1 (foldhash default) --");
    bench_hb(100_000, 15);
    bench_hb(1_000_000, 12);
    bench_hb(10_000_000, 10);

    println!("\n== owning-value tables (deep clone: 1 alloc + payload memcpy per entry) ==");
    let s24: String = "a".repeat(24);
    let s200: String = "a".repeat(200);
    let v4k: Vec<u8> = vec![0u8; 4096];
    println!("-- HashMap<u64, String> 24-byte values --");
    bench_owning("String/24B", 100_000, 12, || s24.clone());
    bench_owning("String/24B", 1_000_000, 10, || s24.clone());
    bench_owning("String/24B", 10_000_000, 10, || s24.clone());
    println!("-- HashMap<u64, String> 200-byte values --");
    bench_owning("String/200B", 100_000, 12, || s200.clone());
    bench_owning("String/200B", 1_000_000, 10, || s200.clone());
    bench_owning("String/200B", 10_000_000, 10, || s200.clone());
    println!("-- HashMap<u64, Vec<u8>> 4096-byte values (10M omitted: ~40GB) --");
    bench_owning("Vec<u8>/4KB", 100_000, 12, || v4k.clone());
    bench_owning("Vec<u8>/4KB", 1_000_000, 10, || v4k.clone());
}
