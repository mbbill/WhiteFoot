# ARM64 assembly snapshots

These files are textual disassemblies from the exact measured objects and
executables. They were generated on the recorded Apple M4 host with Apple LLVM
21.0.0:

```sh
xcrun llvm-objdump -m -d --dis-symname <symbol> <object-or-executable>
```

The snapshots make the key code-shape comparison durable:

- `match-ordinary.aarch64.asm.txt` contains the dependent byte
  `ldrb`/`strb` loop and surviving bounds branches.
- `match-periodic-helper.aarch64.asm.txt` contains repeated-byte duplication,
  `tbl` period permutations, and wide vector loads/stores.
- `huffman-ordinary.aarch64.asm.txt` retains the one-symbol scalar control.
- `huffman-guarded.aarch64.asm.txt` contains one 64-bit word load, six
  source-ordered mask/table/store steps, and a 16-bit scalar tail.
- The two zlib-ng wrapper snapshots preserve the pinned comparison shapes.

Addresses are link-layout details. The instruction structure is the relevant
artifact. These ARM64 snapshots do not establish x86-64 or cross-machine
portability.
