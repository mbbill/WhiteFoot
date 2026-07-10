// Expert Rust: index arena, recursive build via &mut reborrowing (the shape
// xlang cannot express — no reborrow), u64 indices to match the xlang port.
struct Pool { l: Vec<u64>, r: Vec<u64> }

impl Pool {
    fn new(cap: usize) -> Pool {
        let mut p = Pool { l: Vec::with_capacity(cap), r: Vec::with_capacity(cap) };
        p.l.push(0); p.r.push(0);            // index 0 = null sentinel
        p
    }
    fn reset(&mut self) { self.l.truncate(1); self.r.truncate(1); }
    fn push(&mut self, l: u64, r: u64) -> u64 {
        self.l.push(l); self.r.push(r);
        (self.l.len() - 1) as u64
    }
}

fn build(p: &mut Pool, d: u32) -> u64 {
    if d == 0 { p.push(0, 0) }
    else {
        let l = build(p, d - 1);             // implicit reborrow of p
        let r = build(p, d - 1);
        p.push(l, r)
    }
}

fn chk(p: &Pool, i: u64) -> u64 {
    let li = p.l[i as usize];
    if li == 0 { return 1; }
    1 + chk(p, li) + chk(p, p.r[i as usize])
}

fn main() {
    let (mind, maxd) = (4u32, 21u32);
    let cap = 1usize << (maxd + 2);
    let mut pa = Pool::new(cap);
    let sroot = build(&mut pa, maxd + 1);
    assert_eq!(chk(&pa, sroot), (1u64 << (maxd + 2)) - 1);
    pa.reset();
    let lroot = build(&mut pa, maxd);
    let mut pb = Pool::new(cap);
    let mut d = mind;
    while d <= maxd {
        let iters = 1u64 << (maxd - d + mind);
        let exp = (1u64 << (d + 1)) - 1;
        let mut sum = 0u64;
        for _ in 0..iters {
            pb.reset();
            let root = build(&mut pb, d);
            sum += chk(&pb, root);
        }
        assert_eq!(sum, iters * exp);
        d += 2;
    }
    assert_eq!(chk(&pa, lroot), (1u64 << (maxd + 1)) - 1);
}
