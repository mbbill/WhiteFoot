# Whitefoot writer's pack

This is the complete stage-0-supported subset needed for the task. Forms not
listed here are unavailable for this task.

## Lexical and file form

- Use two spaces per brace nesting level and never use tabs.
- Put one construct on each line. Terminate `let`, `set`, `check`, `return`,
  `break`, and `give` statements with `;`. Do not put a semicolon after a
  function, `requires`, `loop`, `region`, `match`, or match-initializer closing
  brace.
- Separate top-level declarations with one blank line.
- Integer literals use decimal digits and a mandatory type suffix, such as
  `0_u8`, `16_u16`, `257_u32`, and `65536_u64`. Hexadecimal and binary literal
  syntax and bare integer literals are unavailable. A fixed array length
  inside `array<T, N>` is an unsuffixed decimal type argument.
- Comments are unavailable. An optional first function-body statement may be
  `doc "text";`.
- Names cannot be redeclared or shadowed in the same function.

The primitive types used here are `u8`, `u16`, `u32`, `u64`, `Bool`, and
`unit`. The corresponding owned buffers are `buffer<u8>`, `buffer<u16>`,
`buffer<u32>`, and `buffer<u64>`.

## Structs and constant primitive arrays

A nongeneric struct lists its fields in order:

```text
struct Pair {
  left: u32;
  right: u64;
}
```

Construct one with named fields in declaration order. Read a field as a place
and change it with `set`:

```text
let pair: own Pair = Pair(left: 7_u32, right: 9_u64);
let old: own u32 = pair.left;
set pair.right = 10_u64;
```

For a borrowed struct, reach fields through `deref`:

```text
let prior: own u64 = deref(value).right;
set deref(value).right = 11_u64;
```

Struct fields may be primitive values, owned buffers, or other nongeneric
structs. A buffer moved into a struct constructor is written `move data`.
Borrow values cannot be stored in structs.

A constant may be a primitive or an `array<primitive, N>`. Array elements are
listed literally and the declared length must match:

```text
const byte_values: array<u8, 4> = [1_u8, 2_u8, 3_u8, 4_u8];
const short_values: array<u16, 2> = [5_u16, 6_u16];
const word_values: array<u32, 2> = [7_u32, 8_u32];
const wide_values: array<u64, 2> = [9_u64, 10_u64];
```

Constant arrays are read-only. Use the same `len<T>` and `index<T>` forms as
for buffers.

## Functions, borrows, regions, and effects

A function with shared and exclusive borrows has this shape:

```text
fn update ['a, 'b] (source: &'a buffer<u8>, value: &uniq 'b Pair, amount: own u64) -> own unit reads('a), writes('b), traps {
  let first: own u8 = index<u8>(deref(source), 0_u64);
  set deref(value).right = amount;
  return unit;
}
```

Parameter modes are `own T`, `&'r T` for a shared borrow, and
`&uniq 'r T` for an exclusive borrow. Declare every signature region in the
function's bracketed region list. Primitive owned values copy. Buffers and
structs containing buffers are affine; use `move` when transferring an owned
affine value.

An effect row is `pure` or the effects the function actually exhibits, in
this order: `reads(...)`, `writes(...)`, `allocates(...)`, `traps`. Multiple
regions inside one effect are separated by spaces, as in `reads('a 'b)`.
Reading through either kind of borrow exhibits `reads`. Writing through an
exclusive borrow exhibits `writes`. Checked indexing and a trapping operation
exhibit `traps`. Reading or changing an owned local or owned buffer does not
name a borrow region in the effect row. Do not declare an unexhibited effect
and do not omit an exhibited effect.

User-function calls use named arguments in declaration order. Arguments are
atoms, and an affine owned argument uses `move`:

```text
let answer: own u64 = combine(left: first, right: second);
consume(data: move owned_data);
```

A helper may receive an existing shared borrow directly. To lend an owned
place or make a bounded child borrow of an exclusive holder, introduce a
lexical region and form the borrow in the call:

```text
region 'call_scope {
  inspect(data: &'call_scope owned_data);
}

region 'write_scope {
  update(value: &uniq 'write_scope deref(holder), amount: amount);
}
```

Such a child borrow is one statement long, cannot escape, and temporarily
suspends its exclusive parent. Calls need no user type or constant arguments.
For a function called by an external driver, `main` is neither required nor
permitted by this task.

## Bindings, places, buffers, and returns

Every local has an explicit mode and type. Change a local with `set`:

```text
let position: own u64 = 0_u64;
set position = iadd.wrap<u64>(position, 1_u64);
return position;
```

Operation and constructor arguments must be atoms: literals, places,
`move place`, or borrows. Nested operation calls are rejected, so bind each
intermediate result first.

`len<T>` returns `u64`. `index<T>` takes a `u64` index and is a checked place
that may be read or assigned. Its type argument must equal the buffer or
constant-array element type. Use `deref` before operating on a borrowed
buffer:

```text
let input_size: own u64 = len<u8>(deref(input));
let a: own u8 = index<u8>(deref(input), i);
let b: own u16 = index<u16>(work16, j);
let c: own u32 = index<u32>(work32, k);
let d: own u64 = index<u64>(wide_values, m);
set index<u8>(output, i) = a;
set index<u16>(work16, j) = b;
set index<u32>(work32, k) = c;
```

An out-of-range index traps. Code must establish every index bound on all task
inputs before the access. Return an owned value with `return value;`; a unit
function ends with `return unit;`.

## Loops, matches, and `give`

There is one loop form. Exit it with a matching labeled break:

```text
loop @scan {
  match ige<u64>(i, limit) {
    True() => {
      break @scan;
    }
    False() => {
    }
  }
  set i = iadd.wrap<u64>(i, 1_u64);
}
```

Conditional control flow is an exhaustive `match`. A `Bool` match has exactly
`True()` and `False()` arms. A match may return from an arm. To bind a value
selected by a match, use a match initializer whose continuing arms end in
`give`:

```text
let selected: own u16 = match ile<u16>(left, right) {
  True() => {
    give left;
  }
  False() => {
    give right;
  }
}
```

`break` exits only its named loop. `give` supplies only the surrounding match
initializer.

## Integer, bit, Boolean, and conversion operations

All operations use call syntax with explicit type arguments. For an unsigned
type `T` among `u8`, `u16`, `u32`, and `u64`, these forms are available here:

```text
ieq<T>(a, b)  ine<T>(a, b)
ilt<T>(a, b)  ile<T>(a, b)  igt<T>(a, b)  ige<T>(a, b)

iadd.wrap<T>(a, b)  isub.wrap<T>(a, b)  imul.wrap<T>(a, b)
iadd.trap<T>(a, b)  isub.trap<T>(a, b)  imul.trap<T>(a, b)
idiv.trap<T>(a, b)  irem.trap<T>(a, b)

iand<T>(a, b)  ior<T>(a, b)  ixor<T>(a, b)
ishl.wrap<T>(a, amount_u32)  ishr.wrap<T>(a, amount_u32)
ishl.trap<T>(a, amount_u32)  ishr.trap<T>(a, amount_u32)

band<Bool>(a, b)  bor<Bool>(a, b)
bxor<Bool>(a, b)  bnot<Bool>(a)
```

Comparisons return `Bool`. `wrap` arithmetic is modular for its result width.
`trap` arithmetic returns the mathematical result or traps on overflow,
division by zero, or an out-of-range shift, as applicable. A wrapping shift
reduces its `u32` amount modulo the value width. Unsigned right shift is
logical. Bind separate `Bool` values before combining them.

`cvt<From, To>(value)` exists only when `From` and `To` are distinct numeric
types. Every widening conversion among these unsigned types is total and
returns the destination value directly:

```text
let word: own u32 = cvt<u8, u32>(byte);
let wide: own u64 = cvt<u16, u64>(short);
```

A narrowing conversion returns `Result<To, NarrowError>` and succeeds only
when the source value is exactly representable. Handle both variants with
named binders:

```text
match cvt<u32, u8>(word) {
  Ok(value: byte) => {
    set chosen = byte;
  }
  Err(error: error) => {
    set valid = False();
  }
}
```

The result can also be selected with a match initializer when all continuing
arms `give` the declared type. There is no same-type `cvt`.

## Checks and normal recoverable outcomes

`check condition else trap "message";` accepts a `Bool` atom and traps when it
is false. A `requires` block, when an actual caller contract needs one, goes
between the signature and body and may contain typed `let` bindings and
checks:

```text
fn bounded (x: own u64) -> own u64 traps requires {
  check ile<u64>(x, 100_u64) else trap "limit";
} {
  return x;
}
```

Use a requirement only for a real caller obligation. Expected capacity
shortage and invalid input are ordinary returned outcomes in this task, not
requirements or explicit traps.

## Closed writer patterns used by this subset

- Linear threading: ownership or one exclusive borrow flows explicitly down a
  call chain. A child reborrow is statement-scoped and cannot escape.
- Closed-set behavior: represent state as ordinary values or nongeneric
  structs and dispatch with exhaustive `match`. Function pointers, closures,
  and dynamic dispatch are unavailable.
- Recoverable capacity: before applying an indivisible output unit, determine
  whether that entire unit fits. If shortage is an expected result, return it
  without applying any part of the unit.

## Unavailable stage-0 forms

Do not emit any of the following:

- `if`, `while`, `for`, infix arithmetic or bit operators, indexing brackets,
  `as` casts, slices, iterators, methods, closures, function values, or dynamic
  dispatch;
- generic user functions, user-function type or constant arguments,
  generic structs, region-parameterized structs, or borrows stored in structs;
- `array_new`, `slice_of`, `box_new`, or `arena_new`;
- `inot`, `ipopcount`, `iclz`, `ictz`, `ibswap`, `imulhi`, any `ineg.*` or
  `iabs.*` form, or `imul.sat`;
- floating-point values, floating-point literals, or floating-point
  operations.

Allocation is also forbidden by the task, so no allocation operation is part
of this pack.
