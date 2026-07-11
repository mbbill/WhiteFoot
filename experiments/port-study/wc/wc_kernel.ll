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
  %t7 = icmp eq i64 0, 0
  %t8 = alloca i1
  store i1 %t7, ptr %t8
  br label %L9
L9:
  %t11 = load i64, ptr %t4
  %t12 = load i64, ptr %t3
  %t13 = icmp uge i64 %t11, %t12
  br i1 %t13, label %L15, label %L16
L15:
  br label %L10
L16:
  br label %L14
L14:
  %t17 = load i64, ptr %t4
  %t18 = icmp ult i64 %t17, %t2
  br i1 %t18, label %L19, label %trap
L19:
  %t20 = getelementptr i8, ptr %t1, i64 %t17
  %t21 = load i8, ptr %t20, !alias.scope !5, !noalias !6
  %t22 = alloca i8
  store i8 %t21, ptr %t22
  %t23 = load i8, ptr %t22
  %t24 = icmp eq i8 %t23, 10
  %t25 = alloca i1
  store i1 %t24, ptr %t25
  %t26 = alloca i64
  %t27 = load i1, ptr %t25
  br i1 %t27, label %L29, label %L30
L29:
  store i64 1, ptr %t26
  br label %L28
L30:
  store i64 0, ptr %t26
  br label %L28
L28:
  %t31 = load i64, ptr %t5
  %t32 = load i64, ptr %t26
  %t33 = add i64 %t31, %t32
  store i64 %t33, ptr %t5
  %t34 = load i8, ptr %t22
  %t35 = icmp uge i8 %t34, 9
  %t36 = alloca i1
  store i1 %t35, ptr %t36
  %t37 = load i8, ptr %t22
  %t38 = icmp ule i8 %t37, 13
  %t39 = alloca i1
  store i1 %t38, ptr %t39
  %t40 = load i1, ptr %t36
  %t41 = load i1, ptr %t39
  %t42 = and i1 %t40, %t41
  %t43 = alloca i1
  store i1 %t42, ptr %t43
  %t44 = load i8, ptr %t22
  %t45 = icmp eq i8 %t44, 32
  %t46 = alloca i1
  store i1 %t45, ptr %t46
  %t47 = load i1, ptr %t43
  %t48 = load i1, ptr %t46
  %t49 = or i1 %t47, %t48
  %t50 = alloca i1
  store i1 %t49, ptr %t50
  %t51 = load i1, ptr %t50
  %t52 = xor i1 %t51, true
  %t53 = alloca i1
  store i1 %t52, ptr %t53
  %t54 = load i1, ptr %t8
  %t55 = load i1, ptr %t53
  %t56 = and i1 %t54, %t55
  %t57 = alloca i1
  store i1 %t56, ptr %t57
  %t58 = alloca i64
  %t59 = load i1, ptr %t57
  br i1 %t59, label %L61, label %L62
L61:
  store i64 1, ptr %t58
  br label %L60
L62:
  store i64 0, ptr %t58
  br label %L60
L60:
  %t63 = load i64, ptr %t6
  %t64 = load i64, ptr %t58
  %t65 = add i64 %t63, %t64
  store i64 %t65, ptr %t6
  %t66 = load i1, ptr %t50
  store i1 %t66, ptr %t8
  %t67 = load i64, ptr %t4
  %t68 = add i64 %t67, 1
  store i64 %t68, ptr %t4
  br label %L9
L10:
  %t69 = load i64, ptr %t5
  %t70 = getelementptr %Counts, ptr %out, i32 0, i32 0
  store i64 %t69, ptr %t70, !alias.scope !3, !noalias !4
  %t71 = load i64, ptr %t6
  %t72 = getelementptr %Counts, ptr %out, i32 0, i32 1
  store i64 %t71, ptr %t72, !alias.scope !3, !noalias !4
  %t73 = load i64, ptr %t3
  %t74 = getelementptr %Counts, ptr %out, i32 0, i32 2
  store i64 %t73, ptr %t74, !alias.scope !3, !noalias !4
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
