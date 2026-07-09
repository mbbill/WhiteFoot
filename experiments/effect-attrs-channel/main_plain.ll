declare {i32, i1} @llvm.sadd.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.ssub.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.smul.with.overflow.i32(i32, i32)
declare void @llvm.trap()
declare i64 @mix(i64)

define i32 @main() nounwind memory(inaccessiblemem: write) {
entry:
  %t1 = alloca i64
  store i64 42, ptr %t1
  %t2 = alloca i64
  store i64 0, ptr %t2
  %t3 = alloca i64
  store i64 0, ptr %t3
  br label %L4
L4:
  %t6 = load i64, ptr %t3
  %t7 = icmp sge i64 %t6, 2000000000
  br i1 %t7, label %L9, label %L10
L9:
  br label %L5
L10:
  br label %L8
L8:
  %t11 = load i64, ptr %t1
  %t12 = call i64 @mix(i64 %t11)
  %t13 = alloca i64
  store i64 %t12, ptr %t13
  %t14 = load i64, ptr %t2
  %t15 = load i64, ptr %t13
  %t16 = add i64 %t14, %t15
  store i64 %t16, ptr %t2
  %t17 = load i64, ptr %t3
  %t18 = add i64 %t17, 1
  store i64 %t18, ptr %t3
  br label %L4
L5:
  %t19 = load i64, ptr %t2
  %t20 = icmp ne i64 %t19, 0
  br i1 %t20, label %L21, label %trap
L21:
  ret i32 0
trap:
  call void @llvm.trap()
  unreachable
}
