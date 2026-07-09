%Ast = type { {ptr, i64}, {ptr, i64}, {ptr, i64}, i64 }
declare {i32, i1} @llvm.sadd.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.ssub.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.smul.with.overflow.i32(i32, i32)
declare void @llvm.trap()
declare ptr @malloc(i64)
declare {i64, i1} @llvm.uadd.with.overflow.i64(i64, i64)
declare {i64, i1} @llvm.umul.with.overflow.i64(i64, i64)

define i64 @push(ptr noalias dereferenceable(56) align 8 %s, i64 %t, i64 %x, i64 %y) nounwind memory(argmem: readwrite, inaccessiblemem: write) {
entry:
  %t1 = getelementptr %Ast, ptr %s, i32 0, i32 3
  %t2 = load i64, ptr %t1, !alias.scope !5, !noalias !6
  %t3 = alloca i64
  store i64 %t2, ptr %t3
  %t4 = getelementptr %Ast, ptr %s, i32 0, i32 0
  %t5 = getelementptr {ptr, i64}, ptr %t4, i32 0, i32 0
  %t6 = load ptr, ptr %t5, !alias.scope !5, !noalias !6
  %t7 = getelementptr {ptr, i64}, ptr %t4, i32 0, i32 1
  %t8 = load i64, ptr %t7, !alias.scope !5, !noalias !6
  %t9 = load i64, ptr %t3
  %t10 = icmp ult i64 %t9, %t8
  br i1 %t10, label %L11, label %trap
L11:
  %t12 = getelementptr i64, ptr %t6, i64 %t9
  store i64 %t, ptr %t12, !alias.scope !7, !noalias !8
  %t13 = getelementptr %Ast, ptr %s, i32 0, i32 1
  %t14 = getelementptr {ptr, i64}, ptr %t13, i32 0, i32 0
  %t15 = load ptr, ptr %t14, !alias.scope !5, !noalias !6
  %t16 = getelementptr {ptr, i64}, ptr %t13, i32 0, i32 1
  %t17 = load i64, ptr %t16, !alias.scope !5, !noalias !6
  %t18 = load i64, ptr %t3
  %t19 = icmp ult i64 %t18, %t17
  br i1 %t19, label %L20, label %trap
L20:
  %t21 = getelementptr i64, ptr %t15, i64 %t18
  store i64 %x, ptr %t21, !alias.scope !9, !noalias !10
  %t22 = getelementptr %Ast, ptr %s, i32 0, i32 2
  %t23 = getelementptr {ptr, i64}, ptr %t22, i32 0, i32 0
  %t24 = load ptr, ptr %t23, !alias.scope !5, !noalias !6
  %t25 = getelementptr {ptr, i64}, ptr %t22, i32 0, i32 1
  %t26 = load i64, ptr %t25, !alias.scope !5, !noalias !6
  %t27 = load i64, ptr %t3
  %t28 = icmp ult i64 %t27, %t26
  br i1 %t28, label %L29, label %trap
L29:
  %t30 = getelementptr i64, ptr %t24, i64 %t27
  store i64 %y, ptr %t30, !alias.scope !11, !noalias !12
  %t31 = load i64, ptr %t3
  %t32 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t31, i64 1)
  %t33 = extractvalue {i64, i1} %t32, 0
  %t34 = extractvalue {i64, i1} %t32, 1
  br i1 %t34, label %trap, label %L35
L35:
  %t36 = getelementptr %Ast, ptr %s, i32 0, i32 3
  store i64 %t33, ptr %t36, !alias.scope !5, !noalias !6
  %t37 = load i64, ptr %t3
  ret i64 %t37
trap:
  call void @llvm.trap()
  unreachable
}

define i64 @eval(ptr noalias readonly dereferenceable(56) align 8 %s, i64 %i) nounwind memory(argmem: read, inaccessiblemem: write) {
entry:
  %t1 = getelementptr %Ast, ptr %s, i32 0, i32 0
  %t2 = getelementptr {ptr, i64}, ptr %t1, i32 0, i32 0
  %t3 = load ptr, ptr %t2
  %t4 = getelementptr {ptr, i64}, ptr %t1, i32 0, i32 1
  %t5 = load i64, ptr %t4
  %t6 = icmp ult i64 %i, %t5
  br i1 %t6, label %L7, label %trap
L7:
  %t8 = getelementptr i64, ptr %t3, i64 %i
  %t9 = load i64, ptr %t8
  %t10 = alloca i64
  store i64 %t9, ptr %t10
  %t11 = load i64, ptr %t10
  %t12 = icmp eq i64 %t11, 0
  br i1 %t12, label %L14, label %L15
L14:
  %t16 = getelementptr %Ast, ptr %s, i32 0, i32 1
  %t17 = getelementptr {ptr, i64}, ptr %t16, i32 0, i32 0
  %t18 = load ptr, ptr %t17
  %t19 = getelementptr {ptr, i64}, ptr %t16, i32 0, i32 1
  %t20 = load i64, ptr %t19
  %t21 = icmp ult i64 %i, %t20
  br i1 %t21, label %L22, label %trap
L22:
  %t23 = getelementptr i64, ptr %t18, i64 %i
  %t24 = load i64, ptr %t23
  %t25 = alloca i64
  store i64 %t24, ptr %t25
  %t26 = load i64, ptr %t25
  ret i64 %t26
L15:
  br label %L13
L13:
  %t27 = getelementptr %Ast, ptr %s, i32 0, i32 1
  %t28 = getelementptr {ptr, i64}, ptr %t27, i32 0, i32 0
  %t29 = load ptr, ptr %t28
  %t30 = getelementptr {ptr, i64}, ptr %t27, i32 0, i32 1
  %t31 = load i64, ptr %t30
  %t32 = icmp ult i64 %i, %t31
  br i1 %t32, label %L33, label %trap
L33:
  %t34 = getelementptr i64, ptr %t29, i64 %i
  %t35 = load i64, ptr %t34
  %t36 = alloca i64
  store i64 %t35, ptr %t36
  %t37 = getelementptr %Ast, ptr %s, i32 0, i32 2
  %t38 = getelementptr {ptr, i64}, ptr %t37, i32 0, i32 0
  %t39 = load ptr, ptr %t38
  %t40 = getelementptr {ptr, i64}, ptr %t37, i32 0, i32 1
  %t41 = load i64, ptr %t40
  %t42 = icmp ult i64 %i, %t41
  br i1 %t42, label %L43, label %trap
L43:
  %t44 = getelementptr i64, ptr %t39, i64 %i
  %t45 = load i64, ptr %t44
  %t46 = alloca i64
  store i64 %t45, ptr %t46
  %t47 = load i64, ptr %t36
  %t48 = call i64 @eval(ptr %s, i64 %t47)
  %t49 = alloca i64
  store i64 %t48, ptr %t49
  %t50 = load i64, ptr %t46
  %t51 = call i64 @eval(ptr %s, i64 %t50)
  %t52 = alloca i64
  store i64 %t51, ptr %t52
  %t53 = load i64, ptr %t49
  %t54 = load i64, ptr %t52
  %t55 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t53, i64 %t54)
  %t56 = extractvalue {i64, i1} %t55, 0
  %t57 = extractvalue {i64, i1} %t55, 1
  br i1 %t57, label %trap, label %L58
L58:
  ret i64 %t56
trap:
  call void @llvm.trap()
  unreachable
}

define i32 @main() nounwind {
entry:
  %t1 = alloca i64
  store i64 16, ptr %t1
  %t2 = load i64, ptr %t1
  %t3 = call {i64, i1} @llvm.umul.with.overflow.i64(i64 %t2, i64 8)
  %t4 = extractvalue {i64, i1} %t3, 0
  %t5 = extractvalue {i64, i1} %t3, 1
  br i1 %t5, label %trap, label %L6
L6:
  %t7 = call ptr @malloc(i64 %t4)
  %t8 = alloca i64
  store i64 0, ptr %t8
  br label %L9
L9:
  %t12 = load i64, ptr %t8
  %t13 = icmp ult i64 %t12, %t2
  br i1 %t13, label %L10, label %L11
L10:
  %t14 = getelementptr i64, ptr %t7, i64 %t12
  store i64 0, ptr %t14
  %t15 = add i64 %t12, 1
  store i64 %t15, ptr %t8
  br label %L9
L11:
  %t16 = load i64, ptr %t1
  %t17 = call {i64, i1} @llvm.umul.with.overflow.i64(i64 %t16, i64 8)
  %t18 = extractvalue {i64, i1} %t17, 0
  %t19 = extractvalue {i64, i1} %t17, 1
  br i1 %t19, label %trap, label %L20
L20:
  %t21 = call ptr @malloc(i64 %t18)
  %t22 = alloca i64
  store i64 0, ptr %t22
  br label %L23
L23:
  %t26 = load i64, ptr %t22
  %t27 = icmp ult i64 %t26, %t16
  br i1 %t27, label %L24, label %L25
L24:
  %t28 = getelementptr i64, ptr %t21, i64 %t26
  store i64 0, ptr %t28
  %t29 = add i64 %t26, 1
  store i64 %t29, ptr %t22
  br label %L23
L25:
  %t30 = load i64, ptr %t1
  %t31 = call {i64, i1} @llvm.umul.with.overflow.i64(i64 %t30, i64 8)
  %t32 = extractvalue {i64, i1} %t31, 0
  %t33 = extractvalue {i64, i1} %t31, 1
  br i1 %t33, label %trap, label %L34
L34:
  %t35 = call ptr @malloc(i64 %t32)
  %t36 = alloca i64
  store i64 0, ptr %t36
  br label %L37
L37:
  %t40 = load i64, ptr %t36
  %t41 = icmp ult i64 %t40, %t30
  br i1 %t41, label %L38, label %L39
L38:
  %t42 = getelementptr i64, ptr %t35, i64 %t40
  store i64 0, ptr %t42
  %t43 = add i64 %t40, 1
  store i64 %t43, ptr %t36
  br label %L37
L39:
  %t44 = alloca %Ast
  %t45 = getelementptr %Ast, ptr %t44, i32 0, i32 0
  %t46 = insertvalue {ptr, i64} undef, ptr %t7, 0
  %t47 = insertvalue {ptr, i64} %t46, i64 %t2, 1
  store {ptr, i64} %t47, ptr %t45
  %t48 = getelementptr %Ast, ptr %t44, i32 0, i32 1
  %t49 = insertvalue {ptr, i64} undef, ptr %t21, 0
  %t50 = insertvalue {ptr, i64} %t49, i64 %t16, 1
  store {ptr, i64} %t50, ptr %t48
  %t51 = getelementptr %Ast, ptr %t44, i32 0, i32 2
  %t52 = insertvalue {ptr, i64} undef, ptr %t35, 0
  %t53 = insertvalue {ptr, i64} %t52, i64 %t30, 1
  store {ptr, i64} %t53, ptr %t51
  %t54 = getelementptr %Ast, ptr %t44, i32 0, i32 3
  store i64 0, ptr %t54
  %t55 = call i64 @push(ptr %t44, i64 0, i64 1, i64 0)
  %t56 = alloca i64
  store i64 %t55, ptr %t56
  %t57 = call i64 @push(ptr %t44, i64 0, i64 2, i64 0)
  %t58 = alloca i64
  store i64 %t57, ptr %t58
  %t59 = load i64, ptr %t56
  %t60 = load i64, ptr %t58
  %t61 = call i64 @push(ptr %t44, i64 1, i64 %t59, i64 %t60)
  %t62 = alloca i64
  store i64 %t61, ptr %t62
  %t63 = call i64 @push(ptr %t44, i64 0, i64 3, i64 0)
  %t64 = alloca i64
  store i64 %t63, ptr %t64
  %t65 = call i64 @push(ptr %t44, i64 0, i64 4, i64 0)
  %t66 = alloca i64
  store i64 %t65, ptr %t66
  %t67 = load i64, ptr %t64
  %t68 = load i64, ptr %t66
  %t69 = call i64 @push(ptr %t44, i64 1, i64 %t67, i64 %t68)
  %t70 = alloca i64
  store i64 %t69, ptr %t70
  %t71 = load i64, ptr %t62
  %t72 = load i64, ptr %t70
  %t73 = call i64 @push(ptr %t44, i64 1, i64 %t71, i64 %t72)
  %t74 = alloca i64
  store i64 %t73, ptr %t74
  %t75 = load i64, ptr %t74
  %t76 = call i64 @eval(ptr %t44, i64 %t75)
  %t77 = alloca i64
  store i64 %t76, ptr %t77
  %t78 = load i64, ptr %t77
  %t79 = icmp eq i64 %t78, 10
  br i1 %t79, label %L80, label %trap
L80:
  ret i32 0
trap:
  call void @llvm.trap()
  unreachable
}

!0 = distinct !{!0, !"push"}
!1 = distinct !{!1, !0, !"push.s"}
!2 = distinct !{!2, !0, !"push.s.tag"}
!3 = distinct !{!3, !0, !"push.s.a"}
!4 = distinct !{!4, !0, !"push.s.b"}
!5 = !{!1}
!6 = !{!2, !3, !4}
!7 = !{!2}
!8 = !{!1, !3, !4}
!9 = !{!3}
!10 = !{!1, !2, !4}
!11 = !{!4}
!12 = !{!1, !2, !3}
