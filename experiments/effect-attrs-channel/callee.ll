declare {i32, i1} @llvm.sadd.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.ssub.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.smul.with.overflow.i32(i32, i32)
declare void @llvm.trap()

define i64 @mix(i64 %x) nounwind willreturn memory(none) {
entry:
  %t1 = mul i64 %x, 2862933555777941757
  %t2 = alloca i64
  store i64 %t1, ptr %t2
  %t3 = load i64, ptr %t2
  %t4 = add i64 %t3, 3037000493
  %t5 = alloca i64
  store i64 %t4, ptr %t5
  %t6 = load i64, ptr %t5
  %t7 = load i64, ptr %t5
  %t8 = mul i64 %t6, %t7
  %t9 = alloca i64
  store i64 %t8, ptr %t9
  %t10 = load i64, ptr %t9
  %t11 = load i64, ptr %t5
  %t12 = add i64 %t10, %t11
  %t13 = alloca i64
  store i64 %t12, ptr %t13
  %t14 = load i64, ptr %t13
  ret i64 %t14
}
