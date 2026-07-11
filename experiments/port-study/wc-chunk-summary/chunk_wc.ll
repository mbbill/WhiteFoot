%Summary = type { i64, i64, i64, i64, i64 }
declare {i32, i1} @llvm.sadd.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.ssub.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.smul.with.overflow.i32(i32, i32)
declare void @llvm.trap()

define void @summarize(ptr noalias dereferenceable(40) align 8 %out, {ptr, i64} %b) nounwind memory(argmem: readwrite, inaccessiblemem: write) {
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
  %t9 = alloca i64
  store i64 1, ptr %t9
  %t10 = load i64, ptr %t3
  %t11 = icmp eq i64 %t10, 0
  br i1 %t11, label %L13, label %L14
L13:
  br label %L12
L14:
  %t15 = icmp ult i64 0, %t2
  br i1 %t15, label %L16, label %trap
L16:
  %t17 = getelementptr i8, ptr %t1, i64 0
  %t18 = load i8, ptr %t17, !alias.scope !5, !noalias !6
  %t19 = alloca i8
  store i8 %t18, ptr %t19
  %t20 = load i8, ptr %t19
  %t21 = icmp uge i8 %t20, 9
  %t22 = alloca i1
  store i1 %t21, ptr %t22
  %t23 = load i8, ptr %t19
  %t24 = icmp ule i8 %t23, 13
  %t25 = alloca i1
  store i1 %t24, ptr %t25
  %t26 = alloca i1
  %t27 = load i1, ptr %t22
  br i1 %t27, label %L29, label %L30
L29:
  %t31 = load i1, ptr %t25
  store i1 %t31, ptr %t26
  br label %L28
L30:
  store i1 false, ptr %t26
  br label %L28
L28:
  %t32 = alloca i1
  %t33 = load i1, ptr %t26
  br i1 %t33, label %L35, label %L36
L35:
  store i1 true, ptr %t32
  br label %L34
L36:
  %t37 = load i8, ptr %t19
  %t38 = icmp eq i8 %t37, 32
  store i1 %t38, ptr %t32
  br label %L34
L34:
  %t39 = load i1, ptr %t32
  br i1 %t39, label %L41, label %L42
L41:
  store i64 1, ptr %t9
  br label %L40
L42:
  store i64 0, ptr %t9
  br label %L40
L40:
  br label %L12
L12:
  br label %L43
L43:
  %t45 = load i64, ptr %t4
  %t46 = load i64, ptr %t3
  %t47 = icmp uge i64 %t45, %t46
  br i1 %t47, label %L49, label %L50
L49:
  br label %L44
L50:
  br label %L48
L48:
  %t51 = load i64, ptr %t4
  %t52 = icmp ult i64 %t51, %t2
  br i1 %t52, label %L53, label %trap
L53:
  %t54 = getelementptr i8, ptr %t1, i64 %t51
  %t55 = load i8, ptr %t54, !alias.scope !5, !noalias !6
  %t56 = alloca i8
  store i8 %t55, ptr %t56
  %t57 = load i8, ptr %t56
  %t58 = icmp eq i8 %t57, 10
  %t59 = alloca i1
  store i1 %t58, ptr %t59
  %t60 = alloca i64
  %t61 = load i1, ptr %t59
  br i1 %t61, label %L63, label %L64
L63:
  store i64 1, ptr %t60
  br label %L62
L64:
  store i64 0, ptr %t60
  br label %L62
L62:
  %t65 = load i64, ptr %t5
  %t66 = load i64, ptr %t60
  %t67 = add i64 %t65, %t66
  store i64 %t67, ptr %t5
  %t68 = load i8, ptr %t56
  %t69 = icmp uge i8 %t68, 9
  %t70 = alloca i1
  store i1 %t69, ptr %t70
  %t71 = load i8, ptr %t56
  %t72 = icmp ule i8 %t71, 13
  %t73 = alloca i1
  store i1 %t72, ptr %t73
  %t74 = load i1, ptr %t70
  %t75 = load i1, ptr %t73
  %t76 = and i1 %t74, %t75
  %t77 = alloca i1
  store i1 %t76, ptr %t77
  %t78 = load i8, ptr %t56
  %t79 = icmp eq i8 %t78, 32
  %t80 = alloca i1
  store i1 %t79, ptr %t80
  %t81 = load i1, ptr %t77
  %t82 = load i1, ptr %t80
  %t83 = or i1 %t81, %t82
  %t84 = alloca i1
  store i1 %t83, ptr %t84
  %t85 = load i1, ptr %t84
  %t86 = xor i1 %t85, true
  %t87 = alloca i1
  store i1 %t86, ptr %t87
  %t88 = load i1, ptr %t8
  %t89 = load i1, ptr %t87
  %t90 = and i1 %t88, %t89
  %t91 = alloca i1
  store i1 %t90, ptr %t91
  %t92 = alloca i64
  %t93 = load i1, ptr %t91
  br i1 %t93, label %L95, label %L96
L95:
  store i64 1, ptr %t92
  br label %L94
L96:
  store i64 0, ptr %t92
  br label %L94
L94:
  %t97 = load i64, ptr %t6
  %t98 = load i64, ptr %t92
  %t99 = add i64 %t97, %t98
  store i64 %t99, ptr %t6
  %t100 = load i1, ptr %t84
  store i1 %t100, ptr %t8
  %t101 = load i64, ptr %t4
  %t102 = add i64 %t101, 1
  store i64 %t102, ptr %t4
  br label %L43
L44:
  %t103 = load i64, ptr %t5
  %t104 = getelementptr %Summary, ptr %out, i32 0, i32 0
  store i64 %t103, ptr %t104, !alias.scope !3, !noalias !4
  %t105 = load i64, ptr %t6
  %t106 = getelementptr %Summary, ptr %out, i32 0, i32 1
  store i64 %t105, ptr %t106, !alias.scope !3, !noalias !4
  %t107 = load i64, ptr %t3
  %t108 = getelementptr %Summary, ptr %out, i32 0, i32 2
  store i64 %t107, ptr %t108, !alias.scope !3, !noalias !4
  %t109 = load i64, ptr %t9
  %t110 = getelementptr %Summary, ptr %out, i32 0, i32 3
  store i64 %t109, ptr %t110, !alias.scope !3, !noalias !4
  %t111 = alloca i64
  %t112 = load i1, ptr %t8
  br i1 %t112, label %L114, label %L115
L114:
  store i64 1, ptr %t111
  br label %L113
L115:
  store i64 0, ptr %t111
  br label %L113
L113:
  %t116 = load i64, ptr %t111
  %t117 = getelementptr %Summary, ptr %out, i32 0, i32 4
  store i64 %t116, ptr %t117, !alias.scope !3, !noalias !4
  ret void
trap:
  call void @llvm.trap()
  unreachable
}

define void @combine(ptr noalias dereferenceable(40) align 8 %out, ptr noalias readonly dereferenceable(40) align 8 %a, ptr noalias readonly dereferenceable(40) align 8 %b) nounwind willreturn memory(argmem: readwrite) {
entry:
  %t1 = getelementptr %Summary, ptr %a, i32 0, i32 2
  %t2 = load i64, ptr %t1, !alias.scope !12, !noalias !13
  %t3 = icmp eq i64 %t2, 0
  br i1 %t3, label %L5, label %L6
L5:
  %t7 = getelementptr %Summary, ptr %b, i32 0, i32 0
  %t8 = load i64, ptr %t7, !alias.scope !12, !noalias !13
  %t9 = getelementptr %Summary, ptr %out, i32 0, i32 0
  store i64 %t8, ptr %t9, !alias.scope !10, !noalias !11
  %t10 = getelementptr %Summary, ptr %b, i32 0, i32 1
  %t11 = load i64, ptr %t10, !alias.scope !12, !noalias !13
  %t12 = getelementptr %Summary, ptr %out, i32 0, i32 1
  store i64 %t11, ptr %t12, !alias.scope !10, !noalias !11
  %t13 = getelementptr %Summary, ptr %b, i32 0, i32 2
  %t14 = load i64, ptr %t13, !alias.scope !12, !noalias !13
  %t15 = getelementptr %Summary, ptr %out, i32 0, i32 2
  store i64 %t14, ptr %t15, !alias.scope !10, !noalias !11
  %t16 = getelementptr %Summary, ptr %b, i32 0, i32 3
  %t17 = load i64, ptr %t16, !alias.scope !12, !noalias !13
  %t18 = getelementptr %Summary, ptr %out, i32 0, i32 3
  store i64 %t17, ptr %t18, !alias.scope !10, !noalias !11
  %t19 = getelementptr %Summary, ptr %b, i32 0, i32 4
  %t20 = load i64, ptr %t19, !alias.scope !12, !noalias !13
  %t21 = getelementptr %Summary, ptr %out, i32 0, i32 4
  store i64 %t20, ptr %t21, !alias.scope !10, !noalias !11
  ret void
L6:
  br label %L4
L4:
  %t22 = getelementptr %Summary, ptr %b, i32 0, i32 2
  %t23 = load i64, ptr %t22, !alias.scope !12, !noalias !13
  %t24 = icmp eq i64 %t23, 0
  br i1 %t24, label %L26, label %L27
L26:
  %t28 = getelementptr %Summary, ptr %a, i32 0, i32 0
  %t29 = load i64, ptr %t28, !alias.scope !12, !noalias !13
  %t30 = getelementptr %Summary, ptr %out, i32 0, i32 0
  store i64 %t29, ptr %t30, !alias.scope !10, !noalias !11
  %t31 = getelementptr %Summary, ptr %a, i32 0, i32 1
  %t32 = load i64, ptr %t31, !alias.scope !12, !noalias !13
  %t33 = getelementptr %Summary, ptr %out, i32 0, i32 1
  store i64 %t32, ptr %t33, !alias.scope !10, !noalias !11
  %t34 = getelementptr %Summary, ptr %a, i32 0, i32 2
  %t35 = load i64, ptr %t34, !alias.scope !12, !noalias !13
  %t36 = getelementptr %Summary, ptr %out, i32 0, i32 2
  store i64 %t35, ptr %t36, !alias.scope !10, !noalias !11
  %t37 = getelementptr %Summary, ptr %a, i32 0, i32 3
  %t38 = load i64, ptr %t37, !alias.scope !12, !noalias !13
  %t39 = getelementptr %Summary, ptr %out, i32 0, i32 3
  store i64 %t38, ptr %t39, !alias.scope !10, !noalias !11
  %t40 = getelementptr %Summary, ptr %a, i32 0, i32 4
  %t41 = load i64, ptr %t40, !alias.scope !12, !noalias !13
  %t42 = getelementptr %Summary, ptr %out, i32 0, i32 4
  store i64 %t41, ptr %t42, !alias.scope !10, !noalias !11
  ret void
L27:
  br label %L25
L25:
  %t43 = getelementptr %Summary, ptr %a, i32 0, i32 0
  %t44 = load i64, ptr %t43, !alias.scope !12, !noalias !13
  %t45 = getelementptr %Summary, ptr %b, i32 0, i32 0
  %t46 = load i64, ptr %t45, !alias.scope !12, !noalias !13
  %t47 = add i64 %t44, %t46
  %t48 = alloca i64
  store i64 %t47, ptr %t48
  %t49 = getelementptr %Summary, ptr %a, i32 0, i32 1
  %t50 = load i64, ptr %t49, !alias.scope !12, !noalias !13
  %t51 = getelementptr %Summary, ptr %b, i32 0, i32 1
  %t52 = load i64, ptr %t51, !alias.scope !12, !noalias !13
  %t53 = add i64 %t50, %t52
  %t54 = alloca i64
  store i64 %t53, ptr %t54
  %t55 = alloca i64
  store i64 0, ptr %t55
  %t56 = getelementptr %Summary, ptr %a, i32 0, i32 4
  %t57 = load i64, ptr %t56, !alias.scope !12, !noalias !13
  %t58 = icmp eq i64 %t57, 0
  br i1 %t58, label %L60, label %L61
L60:
  %t62 = getelementptr %Summary, ptr %b, i32 0, i32 3
  %t63 = load i64, ptr %t62, !alias.scope !12, !noalias !13
  %t64 = icmp eq i64 %t63, 0
  br i1 %t64, label %L66, label %L67
L66:
  store i64 1, ptr %t55
  br label %L65
L67:
  br label %L65
L65:
  br label %L59
L61:
  br label %L59
L59:
  %t68 = load i64, ptr %t54
  %t69 = load i64, ptr %t55
  %t70 = sub i64 %t68, %t69
  %t71 = alloca i64
  store i64 %t70, ptr %t71
  %t72 = getelementptr %Summary, ptr %a, i32 0, i32 2
  %t73 = load i64, ptr %t72, !alias.scope !12, !noalias !13
  %t74 = getelementptr %Summary, ptr %b, i32 0, i32 2
  %t75 = load i64, ptr %t74, !alias.scope !12, !noalias !13
  %t76 = add i64 %t73, %t75
  %t77 = alloca i64
  store i64 %t76, ptr %t77
  %t78 = load i64, ptr %t48
  %t79 = getelementptr %Summary, ptr %out, i32 0, i32 0
  store i64 %t78, ptr %t79, !alias.scope !10, !noalias !11
  %t80 = load i64, ptr %t71
  %t81 = getelementptr %Summary, ptr %out, i32 0, i32 1
  store i64 %t80, ptr %t81, !alias.scope !10, !noalias !11
  %t82 = load i64, ptr %t77
  %t83 = getelementptr %Summary, ptr %out, i32 0, i32 2
  store i64 %t82, ptr %t83, !alias.scope !10, !noalias !11
  %t84 = getelementptr %Summary, ptr %a, i32 0, i32 3
  %t85 = load i64, ptr %t84, !alias.scope !12, !noalias !13
  %t86 = getelementptr %Summary, ptr %out, i32 0, i32 3
  store i64 %t85, ptr %t86, !alias.scope !10, !noalias !11
  %t87 = getelementptr %Summary, ptr %b, i32 0, i32 4
  %t88 = load i64, ptr %t87, !alias.scope !12, !noalias !13
  %t89 = getelementptr %Summary, ptr %out, i32 0, i32 4
  store i64 %t88, ptr %t89, !alias.scope !10, !noalias !11
  ret void
}

!0 = distinct !{!0, !"summarize"}
!1 = distinct !{!1, !0, !"summarize.out"}
!2 = distinct !{!2, !0, !"summarize.b"}
!3 = !{!1}
!4 = !{!2}
!5 = !{!2}
!6 = !{!1}
!7 = distinct !{!7, !"combine"}
!8 = distinct !{!8, !7, !"combine.out"}
!9 = distinct !{!9, !7, !"combine.__shared"}
!10 = !{!8}
!11 = !{!9}
!12 = !{!9}
!13 = !{!8}
