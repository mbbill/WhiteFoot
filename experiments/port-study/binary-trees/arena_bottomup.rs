// Shape-isolating control: the EXACT xlang algorithm (bottom-up levels,
// preallocated columns, manual count) written in Rust.
struct Pool { l: Vec<u64>, r: Vec<u64>, cnt: usize }

fn build(s: &mut Pool, d: u32) -> u64 {
    let leaves = 1usize << d;
    let mut start = s.cnt;
    for _ in 0..leaves {
        s.l[s.cnt] = 0; s.r[s.cnt] = 0; s.cnt += 1;
    }
    let mut width = leaves;
    while width > 1 {
        let half = width >> 1;
        let newstart = s.cnt;
        for j in 0..half {
            let li = (start + 2 * j) as u64;
            s.l[s.cnt] = li; s.r[s.cnt] = li + 1; s.cnt += 1;
        }
        start = newstart;
        width = half;
    }
    start as u64
}

fn chk(s: &Pool, i: u64) -> u64 {
    let li = s.l[i as usize];
    if li == 0 { return 1; }
    1 + chk(s, li) + chk(s, s.r[i as usize])
}

fn main() {
    let (mind, maxd) = (4u32, 21u32);
    let cap = 1usize << (maxd + 2);
    let mut pa = Pool { l: vec![0; cap], r: vec![0; cap], cnt: 1 };
    let sroot = build(&mut pa, maxd + 1);
    assert_eq!(chk(&pa, sroot), (1u64 << (maxd + 2)) - 1);
    pa.cnt = 1;
    let lroot = build(&mut pa, maxd);
    let mut pb = Pool { l: vec![0; cap], r: vec![0; cap], cnt: 1 };
    let mut d = mind;
    while d <= maxd {
        let iters = 1u64 << (maxd - d + mind);
        let exp = (1u64 << (d + 1)) - 1;
        let mut sum = 0u64;
        for _ in 0..iters {
            pb.cnt = 1;
            let root = build(&mut pb, d);
            sum += chk(&pb, root);
        }
        assert_eq!(sum, iters * exp);
        d += 2;
    }
    assert_eq!(chk(&pa, lroot), (1u64 << (maxd + 1)) - 1);
}
