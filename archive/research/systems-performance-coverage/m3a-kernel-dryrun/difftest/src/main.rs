// Differential test: apply the SAME 1M random op sequence (insert/remove/get)
// to the C ctable (via FFI) and a Rust std HashMap oracle, comparing every
// return value and the length after every op. Any divergence stops and reports.
use std::collections::HashMap;

#[repr(C)]
struct Ctable {
    ctrl: *mut u8,
    slots: *mut u8,
    bucket_mask: u64,
    live: u64,
    occupied: u64,
    growth_left: u64,
}
impl Ctable {
    fn zeroed() -> Self {
        Ctable { ctrl: std::ptr::null_mut(), slots: std::ptr::null_mut(),
                 bucket_mask: 0, live: 0, occupied: 0, growth_left: 0 }
    }
}

extern "C" {
    fn ctable_init(t: *mut Ctable);
    fn ctable_free(t: *mut Ctable);
    fn ctable_insert(t: *mut Ctable, k: u64, v: u64, old: *mut u64) -> i32;
    fn ctable_get(t: *const Ctable, k: u64, out: *mut u64) -> i32;
    fn ctable_remove(t: *mut Ctable, k: u64, old: *mut u64) -> i32;
    fn ctable_len(t: *const Ctable) -> u64;
}

#[inline]
fn splitmix64(s: &mut u64) -> u64 {
    *s = s.wrapping_add(0x9E3779B97F4A7C15);
    let mut z = *s;
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
    z ^ (z >> 31)
}

const OPS: u64 = 1_000_000;
const KEY_DOMAIN: u64 = 200_000;  // bounded so remove/get hit meaningfully

fn main() {
    let mut t = Ctable::zeroed();
    unsafe { ctable_init(&mut t) };
    let mut oracle: HashMap<u64, u64> = HashMap::new();

    let mut rng = 0x0f0f_1234_abcd_5678u64;
    let mut inserts = 0u64;
    let mut removes = 0u64;
    let mut gets = 0u64;

    for step in 0..OPS {
        let r = splitmix64(&mut rng);
        let key = r % KEY_DOMAIN;
        let op = (r >> 40) % 4;          // 0,1 = insert ; 2 = remove ; 3 = get
        match op {
            0 | 1 => {
                let val = splitmix64(&mut rng);
                let mut c_old = 0u64;
                let c_existed = unsafe { ctable_insert(&mut t, key, val, &mut c_old) } != 0;
                let o_old = oracle.insert(key, val);
                if c_existed != o_old.is_some()
                    || (c_existed && c_old != *o_old.as_ref().unwrap()) {
                    return fail(step, "insert", key, c_existed, c_old, o_old);
                }
                inserts += 1;
            }
            2 => {
                let mut c_old = 0u64;
                let c_removed = unsafe { ctable_remove(&mut t, key, &mut c_old) } != 0;
                let o_old = oracle.remove(&key);
                if c_removed != o_old.is_some()
                    || (c_removed && c_old != o_old.unwrap()) {
                    return fail(step, "remove", key, c_removed, c_old, o_old);
                }
                removes += 1;
            }
            _ => {
                let mut c_val = 0u64;
                let c_hit = unsafe { ctable_get(&t, key, &mut c_val) } != 0;
                let o_val = oracle.get(&key).copied();
                if c_hit != o_val.is_some() || (c_hit && c_val != o_val.unwrap()) {
                    return fail(step, "get", key, c_hit, c_val, o_val);
                }
                gets += 1;
            }
        }
        // length invariant after every op
        let cl = unsafe { ctable_len(&t) };
        if cl != oracle.len() as u64 {
            eprintln!("DIVERGENCE at step {}: len ctable={} oracle={}", step, cl, oracle.len());
            std::process::exit(1);
        }
    }

    // final full-domain scan
    for key in 0..KEY_DOMAIN {
        let mut c_val = 0u64;
        let c_hit = unsafe { ctable_get(&t, key, &mut c_val) } != 0;
        let o_val = oracle.get(&key).copied();
        if c_hit != o_val.is_some() || (c_hit && c_val != o_val.unwrap()) {
            eprintln!("DIVERGENCE final-scan key {}: ctable=({},{}) oracle={:?}",
                      key, c_hit, c_val, o_val);
            std::process::exit(1);
        }
    }

    let final_len = unsafe { ctable_len(&t) };
    unsafe { ctable_free(&mut t) };
    println!("DIFFERENTIAL OK: {} ops ({} insert / {} remove / {} get), key domain {}, \
              final len {} == oracle {}; full-domain scan matches.",
             OPS, inserts, removes, gets, KEY_DOMAIN, final_len, oracle.len());
}

fn fail(step: u64, op: &str, key: u64, c_flag: bool, c_val: u64, o: Option<u64>) {
    eprintln!("DIVERGENCE at step {} op {} key {}: ctable=({},{}) oracle={:?}",
              step, op, key, c_flag, c_val, o);
    std::process::exit(1);
}
