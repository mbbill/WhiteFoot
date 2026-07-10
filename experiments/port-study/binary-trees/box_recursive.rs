// Obvious Rust: the classic benchmark-game shape — one Box per node.
struct Node { l: Option<Box<Node>>, r: Option<Box<Node>> }

fn build(d: u32) -> Box<Node> {
    if d == 0 { Box::new(Node { l: None, r: None }) }
    else { Box::new(Node { l: Some(build(d - 1)), r: Some(build(d - 1)) }) }
}

fn chk(n: &Node) -> u64 {
    match (&n.l, &n.r) {
        (Some(l), Some(r)) => 1 + chk(l) + chk(r),
        _ => 1,
    }
}

fn main() {
    let (mind, maxd) = (4u32, 21u32);
    let stretch = build(maxd + 1);
    assert_eq!(chk(&stretch), (1u64 << (maxd + 2)) - 1);
    drop(stretch);
    let long = build(maxd);
    let mut d = mind;
    while d <= maxd {
        let iters = 1u64 << (maxd - d + mind);
        let exp = (1u64 << (d + 1)) - 1;
        let mut sum = 0u64;
        for _ in 0..iters {
            let t = build(d);
            sum += chk(&t);
        }
        assert_eq!(sum, iters * exp);
        d += 2;
    }
    assert_eq!(chk(&long), (1u64 << (maxd + 1)) - 1);
}
