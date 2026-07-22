# Generation task

Return only one complete Whitefoot source file, with no Markdown fences or
prose.

Implement a complete one-shot raw DEFLATE decoder. The source must contain
these public declarations, with exactly these field names, field types,
function name, region parameters, parameter names, parameter modes, parameter
order, and return type:

```text
struct InflateResult {
  status: u64;
  produced: u64;
}

fn inflate_raw ['s, 'o, 'r] (src: &'s buffer<u8>, out: &uniq 'o buffer<u8>, result: &uniq 'r InflateResult, work8: own buffer<u8>, work16: own buffer<u16>, work32: own buffer<u32>) -> own unit EFFECTS {
  ...
}
```

`EFFECTS` is a placeholder, not literal source. Replace it with a sound effect
row. The row must read `'s`, write exactly `'o` and `'r`, include `traps`, and
contain no allocation effect. It may also conservatively declare reads of `'o`
or `'r`. No function in the file may allocate. The file may contain helper
functions but must not contain `main`. `inflate_raw` must not have a `requires`
block: this task already defines its complete callable domain. If the body
relies on a supplied length guarantee, establish it with an ordinary edge
check inside the function.

The evaluator supplies pairwise-disjoint arguments. Their visible lengths are:

- `work8`: exactly 65,536 `u8` elements;
- `work16`: exactly 4,096 `u16` elements;
- `work32`: exactly 4,096 `u32` elements.

The initial contents of `out`, `result`, and all three work buffers are
unspecified. Ownership of the work buffers transfers to the call; the
implementation may change or ignore them. The visible input and output lengths
are each at most `2^31 - 1`.

## Result contract

Every normal return must overwrite both fields of `result`. The only permitted
status values are:

- `0_u64`: `Done`;
- `1_u64`: `NeedOutput`;
- `2_u64`: `Malformed`.

`Done` means that the end-of-block symbol or stored payload of a block marked
final has been completed. `result.produced` is the complete decoded byte
length, the first `result.produced` elements of `out` are the exact decoded
byte sequence, and every later visible output element is unchanged. Unused
bits in the final input byte and all later whole input bytes are ignored.

`NeedOutput` is an ordinary result for an otherwise-valid stream whose next
output unit does not fit. A stored byte and a literal are each one-byte output
units. One complete length-distance match is a single indivisible output unit.
Return before changing any output element belonging to a unit that does not
fit. `result.produced` ends at the preceding unit boundary, the written output
is the exact prefix through that boundary, and every later visible output
element is unchanged. This is a one-shot operation; a caller retries from the
start of `src` with another output buffer. A malformed stream must not return
`NeedOutput` merely because output capacity is exhausted before a later
violation.

`Malformed` covers truncated input and every format violation described below.
It returns normally. `result.produced` may be any complete output-unit boundary
from zero through the last valid unit before the first format violation. The
output before that boundary must equal the corresponding decoded prefix, and
every output element at or after that boundary must be unchanged. Thus an
implementation may validate eagerly or may retain a correctly committed
prefix, but it may not expose a partial match or bytes from an invalid unit.

The call must leave `src` unchanged. It must not access outside any visible
argument. An implicit bounds trap, explicit trap, signal, timeout, or
non-return on any argument satisfying this contract is wrong, including when
`src` is malformed. Surrounding guard storage must remain unchanged.

## Raw DEFLATE bit semantics

The input is exactly one raw RFC 1951 stream: it has no zlib or gzip wrapper,
checksum, preset dictionary, concatenated-stream interpretation, or resumable
state.

Number stream bits from zero. Stream bit `k` is bit `k mod 8` of input byte
`k / 8`, where bit zero is the least-significant bit. Fixed-width fields,
including all extra fields, take their first stream bit as numeric bit zero.
A fixed-width read past the end of `src` is malformed. Multi-byte stored-block
integers use the least-significant byte first.

Huffman codes are different from fixed-width fields: the first stream bit of
a Huffman code is the most-significant bit of its canonical code value. Codes
of one length have consecutive canonical values in increasing symbol order,
and every shorter-length group precedes every longer-length group. More
precisely, let `count[L]` be the number of nonzero code lengths equal to `L`,
let `next[1]` be zero, and for `L > 1` let
`next[L] = (next[L - 1] + count[L - 1]) * 2`. In increasing symbol order, a
symbol of nonzero length `L` receives `next[L]`, after which `next[L]`
increases by one. The assigned value is read from its most-significant code
bit to its least-significant code bit. A zero length assigns no code.

A length set is oversubscribed if, starting with one available prefix and
replacing `available` by `2 * available - count[L]` for each successive
positive length, `available` becomes negative. It is incomplete when the final
value is positive. Either condition is malformed, except that a
literal/length or distance alphabet may consist of exactly one symbol with
length one and one unused one-bit prefix. The code-length alphabet must be
complete. A distance alphabet whose declared symbols all have length zero is
permitted when the block never asks for a distance. Literal/length and
distance code lengths are at most 15; code-length-alphabet lengths are at
most 7. A
compressed block must assign a nonzero length to literal/length symbol 256.
Encountering a bit sequence that has no assigned symbol is malformed.

## Blocks

The stream is a sequence of one or more blocks. Every block starts at the
current bit position with one `BFINAL` bit followed by the two-bit `BTYPE`
value. `BFINAL` equal to one marks the last block. A non-final block must be
followed by another complete block. The block kinds are:

- `BTYPE = 0`: stored;
- `BTYPE = 1`: fixed Huffman;
- `BTYPE = 2`: dynamic Huffman;
- `BTYPE = 3`: malformed.

For a stored block, discard input bits up to the next byte boundary. Read
16-bit `LEN` and then 16-bit `NLEN`, both least-significant byte first.
`NLEN` must be the 16-bit one's complement of `LEN`. Then the next `LEN` whole
input bytes are stored output bytes. Missing header or payload bytes and a
complement mismatch are malformed. Each stored byte is a separate output
unit.

For a fixed-Huffman block, the literal/length code lengths are 8 for symbols
0 through 143, 9 for 144 through 255, 7 for 256 through 279, and 8 for 280
through 287. All distance symbols 0 through 31 have length 5. The canonical
rules above determine their code values. Decoding literal/length symbols 286
or 287, or distance symbols 30 or 31, is malformed.

For a dynamic-Huffman block, read these fixed-width values in order:

- five bits `HLIT`; values 0 through 29 mean 257 through 286
  literal/length code lengths, while values 30 and 31 are malformed;
- five bits `HDIST`; values 0 through 31 mean 1 through 32 distance code
  lengths;
- four bits `HCLEN`; values 0 through 15 mean 4 through 19 code-length code
  lengths.

Read `HCLEN + 4` three-bit lengths for code-length symbols in this exact order:
16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15. Every
unlisted code-length symbol has length zero. Construct the canonical
code-length alphabet, then use it to produce exactly
`HLIT + HDIST + 258` lengths. The first `HLIT + 257` belong, in symbol order,
to the literal/length alphabet; the remaining `HDIST + 1` belong, in symbol
order, to the distance alphabet. Their meanings are:

- symbols 0 through 15 append that literal code length;
- symbol 16 reads two extra bits and appends 3 through 6 copies of the
  immediately preceding length; it is malformed when no preceding length
  exists;
- symbol 17 reads three extra bits and appends 3 through 10 zero lengths;
- symbol 18 reads seven extra bits and appends 11 through 138 zero lengths.

A repeat may cross from the literal/length lengths into the distance lengths.
A repeat that would exceed the exact combined count is malformed. Truncation
while describing either alphabet is malformed. After applying the canonical
validity rules and the required end symbol, these two alphabets decode the
block body.

## Compressed block body

Decode literal/length symbols until the end-of-block symbol:

- symbols 0 through 255 produce that byte as one literal output unit;
- symbol 256 ends the current block without producing output;
- symbols 257 through 285 produce a match length and must be followed by one
  distance symbol and its extra bits;
- every other decoded literal/length symbol is malformed.

The exact length mapping is:

- symbols 257 through 264 mean lengths 3 through 10 with no extra bits;
- symbols 265 through 268 have bases 11, 13, 15, and 17 respectively, plus
  one extra bit;
- symbols 269 through 272 have bases 19, 23, 27, and 31 respectively, plus
  two extra bits;
- symbols 273 through 276 have bases 35, 43, 51, and 59 respectively, plus
  three extra bits;
- symbols 277 through 280 have bases 67, 83, 99, and 115 respectively, plus
  four extra bits;
- symbols 281 through 284 have bases 131, 163, 195, and 227 respectively,
  plus five extra bits;
- symbol 285 means length 258 with no extra bits.

Distance symbols 0 through 3 mean distances 1 through 4 with no extra bits.
For a distance symbol `D` from 4 through 29, let
`E = (D / 2) - 1`; its base is
`1 + (2 + (D mod 2)) * 2^E`, and it uses `E` extra bits. The distance is the
base plus the extra value. Distance symbols 30 and 31 are malformed.

A match length is therefore from 3 through 258 and a distance is from 1
through 32,768. The distance must not exceed the number of bytes already
produced in this call. History crosses block boundaries. Produce a match by
repeatedly copying the byte exactly `distance` positions before the current
output position; newly copied bytes immediately become history, so source and
destination ranges may overlap. The whole match is one output unit for the
result contract.

All stored, fixed-Huffman, and dynamic-Huffman blocks, arbitrary legal block
sequences, empty compressed blocks, the full history distance, and overlapping
matches are required.
