trait SourceOnlySat: Copy {
    fn saturating_add(self, rhs: Self) -> Self;
}

fn sequential_unsigned(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    for &x in xs {
        acc = acc.saturating_add(x);
    }
    acc
}

fn manual_lanes(xs: &[u64]) -> u64 {
    let mut lanes = [0u64; 4];
    for chunk in xs.chunks_exact(4) {
        lanes[0] = lanes[0].saturating_add(chunk[0]);
        lanes[1] = lanes[1].saturating_add(chunk[1]);
        lanes[2] = lanes[2].saturating_add(chunk[2]);
        lanes[3] = lanes[3].saturating_add(chunk[3]);
    }
    lanes[0]
        .saturating_add(lanes[1])
        .saturating_add(lanes[2].saturating_add(lanes[3]))
}

fn address_math(offset: usize, len: usize) -> usize {
    offset.saturating_add(len)
}

fn source_type_unresolved<T: SourceOnlySat>(xs: &[T], zero: T) -> T {
    let mut acc = zero;
    for &x in xs {
        acc = acc.saturating_add(x);
    }
    acc
}

fn indexed_array_accumulator(xs: &[u64]) -> u64 {
    let mut acc = [0u64; 1];
    for &x in xs {
        acc[0] = acc[0].saturating_add(x);
    }
    acc[0]
}

struct StructAccumulator {
    value: u64,
}

fn struct_field_accumulator(xs: &[u64]) -> u64 {
    let mut acc = StructAccumulator { value: 0 };
    for &x in xs {
        acc.value = acc.value.saturating_add(x);
    }
    acc.value
}

#[derive(Clone, Copy)]
struct CustomAccumulator(u64);

impl CustomAccumulator {
    fn saturating_add(self, rhs: Self) -> Self {
        Self(self.0.saturating_add(rhs.0))
    }
}

fn custom_method_accumulator(xs: &[CustomAccumulator]) -> CustomAccumulator {
    let mut acc = CustomAccumulator(0);
    for &x in xs {
        acc = acc.saturating_add(x);
    }
    acc
}

fn manual_without_merge(xs: &[u64]) -> (u64, u64) {
    let mut a0 = 0u64;
    let mut a1 = 0u64;
    for chunk in xs.chunks_exact(2) {
        a0 = a0.saturating_add(chunk[0]);
        a1 = a1.saturating_add(chunk[1]);
    }
    (a0, a1)
}

fn signed_is_not_a_law_candidate(xs: &[i64]) -> i64 {
    let mut acc = 0i64;
    for &x in xs {
        acc = acc.saturating_add(x);
    }
    acc
}

fn constant_induction(xs: &[u8]) -> u64 {
    let mut count = 0u64;
    for _ in xs {
        count = count.saturating_add(1);
    }
    count
}

fn fold_needs_semantic_resolution(xs: &[u64]) -> u64 {
    xs.iter().copied().fold(0u64, |acc, x| acc.saturating_add(x))
}

fn shadowed_accumulator(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    for mut acc in xs.iter().copied() {
        acc = acc.saturating_add(acc);
    }
    acc
}

fn body_binding_shadows_accumulator(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    for &x in xs {
        acc = acc.saturating_add(x);
        let acc = x;
        let _ = acc;
    }
    acc
}

fn preloop_write_replaces_initializer(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    acc = 7;
    for &x in xs {
        acc = acc.saturating_add(x);
    }
    acc
}

fn prior_recurrence_replaces_initializer(xs: &[u64], ys: &[u64]) -> u64 {
    let mut acc = 0u64;
    for &x in xs {
        acc = acc.saturating_add(x);
    }
    for &y in ys {
        acc = acc.saturating_add(y);
    }
    acc
}

fn preloop_nested_shadow_is_unproved(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    {
        let acc = 9u64;
        let _ = acc;
    }
    for &x in xs {
        acc = acc.saturating_add(x);
    }
    acc
}

fn iterable_expression_mutates_accumulator(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    for x in {
        acc = 100;
        xs.iter().copied()
    } {
        acc = acc.saturating_add(x);
    }
    acc
}

struct CustomDeref(u64);

impl std::ops::Deref for CustomDeref {
    type Target = u64;

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

fn overloaded_deref_operand(xs: &[&CustomDeref]) -> u64 {
    let mut acc = 0u64;
    for &x in xs {
        acc = acc.saturating_add(**x);
    }
    acc
}

struct CustomIndex([u64; 1]);

impl std::ops::Index<usize> for CustomIndex {
    type Output = u64;

    fn index(&self, index: usize) -> &Self::Output {
        &self.0[index]
    }
}

fn overloaded_index_operand(xs: &[CustomIndex]) -> u64 {
    let mut acc = 0u64;
    for x in xs {
        acc = acc.saturating_add(x[0]);
    }
    acc
}

fn reset_inside_loop(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    for &x in xs {
        acc = acc.saturating_add(x);
        acc = 0;
    }
    acc
}

macro_rules! touch_accumulator {
    ($acc:expr) => {
        let _ = &$acc;
    };
}

fn macro_inside_loop(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    for &x in xs {
        acc = acc.saturating_add(x);
        touch_accumulator!(acc);
    }
    acc
}

fn observe(_value: u64) {}

fn opaque_call_inside_loop(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    for &x in xs {
        acc = acc.saturating_add(x);
        observe(x);
    }
    acc
}

fn observe_ref(_value: &u64) {}

fn escaped_accumulator(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    for &x in xs {
        acc = acc.saturating_add(x);
        observe_ref(&acc);
    }
    acc
}

fn other_write_inside_loop(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    let mut side = 0u64;
    for &x in xs {
        acc = acc.saturating_add(x);
        side = side.wrapping_add(1);
    }
    acc.saturating_add(side)
}

fn opaque_item_transform(x: u64) -> u64 {
    x
}

fn name_mention_is_not_item_derivation(xs: &[u64], external: u64) -> u64 {
    let mut acc = 0u64;
    for &_ignored in xs {
        acc = acc.saturating_add(external);
    }
    acc
}

fn called_item_transform_is_opaque(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    for &x in xs {
        acc = acc.saturating_add(opaque_item_transform(x));
    }
    acc
}

fn overwritten_before_observation(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    for &x in xs {
        acc = acc.saturating_add(x);
    }
    acc = 0;
    acc
}

fn destructuring_shadow_before_observation(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    for &x in xs {
        acc = acc.saturating_add(x);
    }
    let (acc,) = (0u64,);
    acc
}

fn tuple_assignment_before_observation(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    let mut other = 1u64;
    for &x in xs {
        acc = acc.saturating_add(x);
    }
    (acc, other) = (0, 0);
    acc.saturating_add(other)
}

fn method_mutation_before_observation(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    for &x in xs {
        acc = acc.saturating_add(x);
    }
    acc.clone_from(&0u64);
    acc
}

fn mutate(value: &mut u64) {
    *value = 0;
}

fn mutable_escape_before_observation(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    for &x in xs {
        acc = acc.saturating_add(x);
    }
    mutate(&mut acc);
    acc
}

macro_rules! reset_value {
    ($value:ident) => {
        $value = 0;
    };
}

fn macro_reset_before_observation(xs: &[u64]) -> u64 {
    let mut acc = 0u64;
    for &x in xs {
        acc = acc.saturating_add(x);
    }
    reset_value!(acc);
    acc
}

struct Statistics {
    value: u64,
    weight: u64,
}

fn multiple_statistics(rows: &[Statistics]) -> u64 {
    let mut sum = 0u64;
    let mut weight = 0u64;
    for row in rows {
        sum = sum.saturating_add(row.value);
        weight = weight.saturating_add(row.weight);
    }
    sum.saturating_add(weight)
}

fn duplicate_merge_leaf(xs: &[u64]) -> u64 {
    let mut a0 = 0u64;
    let mut a1 = 0u64;
    for chunk in xs.chunks_exact(2) {
        a0 = a0.saturating_add(chunk[0]);
        a1 = a1.saturating_add(chunk[1]);
    }
    a0.saturating_add(a1).saturating_add(a1)
}

fn destructuring_shadow_before_manual_merge(xs: &[u64]) -> u64 {
    let mut a0 = 0u64;
    let mut a1 = 0u64;
    for chunk in xs.chunks_exact(2) {
        a0 = a0.saturating_add(chunk[0]);
        a1 = a1.saturating_add(chunk[1]);
    }
    let (a0, a1) = (0u64, 0u64);
    a0.saturating_add(a1)
}

fn macro_reset_before_manual_merge(xs: &[u64]) -> u64 {
    let mut a0 = 0u64;
    let mut a1 = 0u64;
    for chunk in xs.chunks_exact(2) {
        a0 = a0.saturating_add(chunk[0]);
        a1 = a1.saturating_add(chunk[1]);
    }
    reset_value!(a0);
    a0.saturating_add(a1)
}

fn whole_array_used_before_merge(xs: &[u64]) -> u64 {
    let mut lanes = [0u64; 2];
    for chunk in xs.chunks_exact(2) {
        lanes[0] = lanes[0].saturating_add(chunk[0]);
        lanes[1] = lanes[1].saturating_add(chunk[1]);
    }
    let _snapshot = lanes;
    lanes[0].saturating_add(lanes[1])
}

fn outer_does_not_own_nested_hits() -> u64 {
    fn nested(xs: &[u64]) -> u64 {
        let mut acc = 0u64;
        for &x in xs {
            acc = acc.saturating_add(x);
        }
        acc
    }
    nested(&[1, 2, 3])
}

fn closure_is_a_separate_unresolved_boundary(xs: &[u64]) -> u64 {
    let reduce = || {
        let mut acc = 0u64;
        for &x in xs {
            acc = acc.saturating_add(x);
        }
        acc
    };
    reduce()
}

macro_rules! hidden_reassociation {
    ($xs:expr) => {{
        let mut acc = 0u64;
        for x in $xs {
            acc = acc.saturating_add(x);
        }
        acc
    }};
}
