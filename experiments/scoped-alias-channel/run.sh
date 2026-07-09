#!/bin/sh
# Channel-1 benchmark: scoped-alias metadata from ownership provenance.
# Usage: sh run.sh   (from this directory)
set -e
PY=python3; CLANG=/usr/bin/clang
$PY -c "
import sys; sys.path.insert(0, '../../prototype/democ'); sys.path.insert(0, '../../prototype/checker')
import democ
src = open('kernel.xl').read()
open('kernel_facts.ll','w').write(democ.compile_program(src))
open('kernel_nofacts.ll','w').write(democ.compile_program(src, alias=False))
"
$CLANG -O2 -c kernel_facts.ll -o kf.o
$CLANG -O2 -c kernel_nofacts.ll -o kn.o
$CLANG -O2 driver.c kf.o -o bench_facts
$CLANG -O2 driver.c kn.o -o bench_nofacts
rustc -C opt-level=3 --edition 2021 rust_kernels.rs -o bench_rust
for n in 8 16 32 64 128 512 4096; do
  k=$((80000000 / n))
  echo "--- n=$n k=$k"
  ./bench_facts $n $k; ./bench_nofacts $n $k; ./bench_rust $n $k
done
