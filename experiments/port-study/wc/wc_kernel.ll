%Counts = type { i64, i64, i64 }
declare {i32, i1} @llvm.sadd.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.ssub.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.smul.with.overflow.i32(i32, i32)
declare void @llvm.trap()

define i64 @count_lines({ptr, i64} %b) nounwind memory(inaccessiblemem: write) {
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

define void @count_all(ptr noalias dereferenceable(24) align 8 %out, {ptr, i64} %b) nounwind memory(argmem: readwrite, inaccessiblemem: write) {
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
  %t20 = load i8, ptr %t19, !alias.scope !5, !noalias !6
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
  %t31 = alloca i1
  store i1 %t30, ptr %t31
  %t32 = load i8, ptr %t21
  %t33 = icmp ule i8 %t32, 13
  %t34 = alloca i1
  store i1 %t33, ptr %t34
  %t35 = alloca i1
  %t36 = load i1, ptr %t31
  br i1 %t36, label %L38, label %L39
L38:
  %t40 = load i1, ptr %t34
  store i1 %t40, ptr %t35
  br label %L37
L39:
  store i1 false, ptr %t35
  br label %L37
L37:
  %t41 = alloca i1
  %t42 = load i1, ptr %t35
  br i1 %t42, label %L44, label %L45
L44:
  store i1 true, ptr %t41
  br label %L43
L45:
  %t46 = load i8, ptr %t21
  %t47 = icmp eq i8 %t46, 32
  store i1 %t47, ptr %t41
  br label %L43
L43:
  %t48 = load i1, ptr %t41
  br i1 %t48, label %L50, label %L51
L50:
  store i64 1, ptr %t7
  br label %L49
L51:
  %t52 = load i64, ptr %t7
  %t53 = icmp eq i64 %t52, 1
  br i1 %t53, label %L55, label %L56
L55:
  %t57 = load i64, ptr %t6
  %t58 = add i64 %t57, 1
  store i64 %t58, ptr %t6
  br label %L54
L56:
  br label %L54
L54:
  store i64 0, ptr %t7
  br label %L49
L49:
  %t59 = load i64, ptr %t4
  %t60 = add i64 %t59, 1
  store i64 %t60, ptr %t4
  br label %L8
L9:
  %t61 = load i64, ptr %t5
  %t62 = getelementptr %Counts, ptr %out, i32 0, i32 0
  store i64 %t61, ptr %t62, !alias.scope !3, !noalias !4
  %t63 = load i64, ptr %t6
  %t64 = getelementptr %Counts, ptr %out, i32 0, i32 1
  store i64 %t63, ptr %t64, !alias.scope !3, !noalias !4
  %t65 = load i64, ptr %t3
  %t66 = getelementptr %Counts, ptr %out, i32 0, i32 2
  store i64 %t65, ptr %t66, !alias.scope !3, !noalias !4
  ret void
trap:
  call void @llvm.trap()
  unreachable
}

!0 = distinct !{!0, !"count_all"}
!1 = distinct !{!1, !0, !"count_all.out"}
!2 = distinct !{!2, !0, !"count_all.b"}
!3 = !{!1}
!4 = !{!2}
!5 = !{!2}
!6 = !{!1}
