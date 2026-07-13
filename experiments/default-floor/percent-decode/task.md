# Generation task

Return only a complete xlang source file, with no Markdown fences or prose.

Implement a function named `decode` with this exact public declaration shape:

```text
fn decode ['r] (out: &uniq 'r buffer<u8>, src: own buffer<u8>) -> own u64 reads('r), writes('r), traps requires { ... } { ... }
```

`src` is an arbitrary byte sequence.  In the result, a `%` byte followed by two
ASCII hexadecimal digits represents the byte named by those two digits.
Hexadecimal letters are case-insensitive.  Such a three-byte sequence produces
one result byte.  A `%` that is not followed by two hexadecimal digits remains
unchanged and does not remove either following byte.  All other bytes remain
unchanged and in order.

The required entry condition is that the visible output length is at least the
source length.  Violation must trap before writing output.  On success, write
the result starting at output index zero and return its byte length.  Do not
change the source or any output byte at or after the returned length.

The file may contain helper functions, but it must contain the required
`decode` function and must not contain `main`.
