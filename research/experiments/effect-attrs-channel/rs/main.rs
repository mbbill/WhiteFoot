use mixlib::mix;
fn main() {
    let k = 42i64; let mut acc = 0i64; let mut i = 0i64;
    while i < 2_000_000_000 { acc = acc.wrapping_add(mix(k)); i += 1; }
    assert!(acc != 0);
}
