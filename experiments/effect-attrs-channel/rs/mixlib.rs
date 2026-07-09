#[inline(never)]
pub fn mix(x: i64) -> i64 {
    let a = x.wrapping_mul(2862933555777941757);
    let b = a.wrapping_add(3037000493);
    let c = b.wrapping_mul(b);
    c.wrapping_add(b)
}
