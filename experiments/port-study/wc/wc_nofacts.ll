%Counts = type { i64, i64, i64 }
declare {i32, i1} @llvm.sadd.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.ssub.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.smul.with.overflow.i32(i32, i32)
declare void @llvm.trap()

define i64 @count_lines({ptr, i64} %b) {
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
  %t8 = load i64, ptr %t4
  %t9 = load i64, ptr %t3
  %t10 = icmp uge i64 %t8, %t9
  br i1 %t10, label %L12, label %L13
L12:
  br label %L7
L13:
  br label %L11
L11:
  %t14 = load i64, ptr %t4
  %t15 = icmp ult i64 %t14, %t2
  br i1 %t15, label %L16, label %trap
L16:
  %t17 = getelementptr i8, ptr %t1, i64 %t14
  %t18 = load i8, ptr %t17
  %t19 = alloca i8
  store i8 %t18, ptr %t19
  %t20 = load i8, ptr %t19
  %t21 = icmp eq i8 %t20, 10
  br i1 %t21, label %L23, label %L24
L23:
  %t25 = load i64, ptr %t5
  %t26 = add i64 %t25, 1
  store i64 %t26, ptr %t5
  br label %L22
L24:
  br label %L22
L22:
  %t27 = load i64, ptr %t4
  %t28 = add i64 %t27, 1
  store i64 %t28, ptr %t4
  br label %L6
L7:
  %t29 = load i64, ptr %t5
  ret i64 %t29
trap:
  call void @llvm.trap()
  unreachable
}

define void @count_all(ptr %out, {ptr, i64} %b) {
entry:
  %t1 = extractvalue {ptr, i64} %b, 0
  %t2 = extractvalue {ptr, i64} %b, 1
  %t3 = alloca i64
  store i64 %t2, ptr %t3
  %t4 = alloca i64
  store i64 0, ptr %t4
  %t5 = alloca i64
  store i64 0, ptr %t5
  %t6 = alloca i64
  store i64 0, ptr %t6
  %t7 = alloca i64
  store i64 1, ptr %t7
  br label %L8
L8:
  %t10 = load i64, ptr %t4
  %t11 = load i64, ptr %t3
  %t12 = icmp uge i64 %t10, %t11
  br i1 %t12, label %L14, label %L15
L14:
  br label %L9
L15:
  br label %L13
L13:
  %t16 = load i64, ptr %t4
  %t17 = icmp ult i64 %t16, %t2
  br i1 %t17, label %L18, label %trap
L18:
  %t19 = getelementptr i8, ptr %t1, i64 %t16
  %t20 = load i8, ptr %t19
  %t21 = alloca i8
  store i8 %t20, ptr %t21
  %t22 = load i8, ptr %t21
  %t23 = icmp eq i8 %t22, 10
  br i1 %t23, label %L25, label %L26
L25:
  %t27 = load i64, ptr %t5
  %t28 = add i64 %t27, 1
  store i64 %t28, ptr %t5
  br label %L24
L26:
  br label %L24
L24:
  %t29 = load i8, ptr %t21
  %t30 = icmp uge i8 %t29, 9
  %t31 = load i8, ptr %t21
  %t32 = icmp ule i8 %t31, 13
  %t33 = alloca i1
  br i1 %t30, label %L35, label %L36
L35:
  store i1 %t32, ptr %t33
  br label %L34
L36:
  store i1 false, ptr %t33
  br label %L34
L34:
  %t37 = alloca i1
  %t38 = load i1, ptr %t33
  br i1 %t38, label %L40, label %L41
L40:
  store i1 true, ptr %t37
  br label %L39
L41:
  %t42 = load i8, ptr %t21
  %t43 = icmp eq i8 %t42, 32
  store i1 %t43, ptr %t37
  br label %L39
L39:
  %t44 = load i1, ptr %t37
  br i1 %t44, label %L46, label %L47
L46:
  store i64 1, ptr %t7
  br label %L45
L47:
  %t48 = load i64, ptr %t7
  %t49 = icmp eq i64 %t48, 1
  br i1 %t49, label %L51, label %L52
L51:
  %t53 = load i64, ptr %t6
  %t54 = add i64 %t53, 1
  store i64 %t54, ptr %t6
  br label %L50
L52:
  br label %L50
L50:
  store i64 0, ptr %t7
  br label %L45
L45:
  %t55 = load i64, ptr %t4
  %t56 = add i64 %t55, 1
  store i64 %t56, ptr %t4
  br label %L8
L9:
  %t57 = load i64, ptr %t5
  %t58 = getelementptr %Counts, ptr %out, i32 0, i32 0
  store i64 %t57, ptr %t58
  %t59 = load i64, ptr %t6
  %t60 = getelementptr %Counts, ptr %out, i32 0, i32 1
  store i64 %t59, ptr %t60
  %t61 = load i64, ptr %t3
  %t62 = getelementptr %Counts, ptr %out, i32 0, i32 2
  store i64 %t61, ptr %t62
  ret void
trap:
  call void @llvm.trap()
  unreachable
}
