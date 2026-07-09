declare {i32, i1} @llvm.sadd.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.ssub.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.smul.with.overflow.i32(i32, i32)
declare void @llvm.trap()
declare i64 @llvm.uadd.sat.i64(i64, i64)
declare {i64, i1} @llvm.uadd.with.overflow.i64(i64, i64)

define i64 @satadd(i64 %x, i64 %y) {
entry:
  %t1 = call i64 @llvm.uadd.sat.i64(i64 %x, i64 %y)
  ret i64 %t1
}

define i64 @reduce({ptr, i64} %b) {
entry:
  %t1 = extractvalue {ptr, i64} %b, 0
  %t2 = extractvalue {ptr, i64} %b, 1
  %t3 = alloca i64
  store i64 %t2, ptr %t3
  %t4 = alloca i64
  store i64 0, ptr %t4
  %t5 = alloca i64
  store i64 0, ptr %t5
  br label %L6
L6:
  %t8 = load i64, ptr %t5
  %t9 = load i64, ptr %t3
  %t10 = icmp uge i64 %t8, %t9
  br i1 %t10, label %L12, label %L13
L12:
  br label %L7
L13:
  br label %L11
L11:
  %t14 = load i64, ptr %t5
  %t15 = icmp ult i64 %t14, %t2
  br i1 %t15, label %L16, label %trap
L16:
  %t17 = getelementptr i64, ptr %t1, i64 %t14
  %t18 = load i64, ptr %t17
  %t19 = alloca i64
  store i64 %t18, ptr %t19
  %t20 = load i64, ptr %t4
  %t21 = load i64, ptr %t19
  %t22 = call i64 @satadd(i64 %t20, i64 %t21)
  store i64 %t22, ptr %t4
  %t23 = load i64, ptr %t5
  %t24 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t23, i64 1)
  %t25 = extractvalue {i64, i1} %t24, 0
  %t26 = extractvalue {i64, i1} %t24, 1
  br i1 %t26, label %trap, label %L27
L27:
  store i64 %t25, ptr %t5
  br label %L6
L7:
  %t28 = load i64, ptr %t4
  ret i64 %t28
trap:
  call void @llvm.trap()
  unreachable
}
