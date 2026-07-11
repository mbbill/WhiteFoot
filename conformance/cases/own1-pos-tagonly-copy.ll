declare {i32, i1} @llvm.sadd.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.ssub.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.smul.with.overflow.i32(i32, i32)
declare void @llvm.trap()

define i32 @main() nounwind memory(none) {
entry:
  %t1 = alloca i32
  store i32 1, ptr %t1
  %t2 = load i32, ptr %t1
  %t6 = icmp eq i32 %t2, 0
  br i1 %t6, label %L4, label %L5
L4:
  br label %L3
L5:
  %t9 = icmp eq i32 %t2, 1
  br i1 %t9, label %L7, label %L8
L7:
  br label %L3
L8:
  %t12 = icmp eq i32 %t2, 2
  br i1 %t12, label %L10, label %L11
L10:
  br label %L3
L11:
  unreachable
L3:
  %t13 = load i32, ptr %t1
  %t17 = icmp eq i32 %t13, 0
  br i1 %t17, label %L15, label %L16
L15:
  br label %L14
L16:
  %t20 = icmp eq i32 %t13, 1
  br i1 %t20, label %L18, label %L19
L18:
  br label %L14
L19:
  %t23 = icmp eq i32 %t13, 2
  br i1 %t23, label %L21, label %L22
L21:
  br label %L14
L22:
  unreachable
L14:
  %t24 = icmp eq i64 1, 1
  %t25 = alloca i1
  store i1 %t24, ptr %t25
  %t26 = load i1, ptr %t25
  %t27 = load i1, ptr %t25
  %t28 = and i1 %t26, %t27
  %t29 = alloca i1
  store i1 %t28, ptr %t29
  %t30 = load i1, ptr %t29
  %t31 = xor i1 %t30, true
  %t32 = alloca i1
  store i1 %t31, ptr %t32
  %t33 = alloca i64
  store i64 0, ptr %t33
  br label %L34
L34:
  %t36 = load i64, ptr %t33
  %t37 = icmp uge i64 %t36, 3
  br i1 %t37, label %L39, label %L40
L39:
  br label %L35
L40:
  br label %L38
L38:
  %t41 = load i1, ptr %t32
  br i1 %t41, label %L43, label %L44
L43:
  br label %L42
L44:
  br label %L42
L42:
  %t45 = load i64, ptr %t33
  %t46 = add i64 %t45, 1
  store i64 %t46, ptr %t33
  br label %L34
L35:
  ret i32 0
}
