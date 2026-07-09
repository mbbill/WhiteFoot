declare {i32, i1} @llvm.sadd.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.ssub.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.smul.with.overflow.i32(i32, i32)
declare void @llvm.trap()
declare i64 @llvm.uadd.sat.i64(i64, i64)
declare ptr @malloc(i64)
declare {i64, i1} @llvm.uadd.with.overflow.i64(i64, i64)
declare {i64, i1} @llvm.umul.with.overflow.i64(i64, i64)

define i64 @satadd(i64 %x, i64 %y) nounwind willreturn memory(none) {
entry:
  %t1 = call i64 @llvm.uadd.sat.i64(i64 %x, i64 %y)
  ret i64 %t1
}

define i64 @reduce({ptr, i64} %b) nounwind memory(inaccessiblemem: write) {
entry:
  %t1 = extractvalue {ptr, i64} %b, 0
  %t2 = extractvalue {ptr, i64} %b, 1
  %t3 = alloca i64
  store i64 %t2, ptr %t3
  %t4 = alloca i64
  store i64 0, ptr %t4
  %t5 = alloca i64
  store i64 0, ptr %t5
  %t6 = load i64, ptr %t5
  %t7 = load i64, ptr %t3
  %t8 = icmp ult i64 %t6, %t7
  br i1 %t8, label %L10, label %L11
L10:
  %t12 = load i64, ptr %t3
  %t13 = load i64, ptr %t5
  %t14 = sub i64 %t12, %t13
  %t15 = alloca i64
  store i64 %t14, ptr %t15
  %t16 = load i64, ptr %t15
  %t17 = icmp uge i64 %t16, 4
  br i1 %t17, label %L19, label %L20
L19:
  %t21 = load i64, ptr %t3
  %t22 = sub i64 %t21, 3
  %t23 = alloca i64
  store i64 %t22, ptr %t23
  %t24 = alloca i64
  store i64 0, ptr %t24
  %t25 = alloca i64
  store i64 0, ptr %t25
  %t26 = alloca i64
  store i64 0, ptr %t26
  %t27 = alloca i64
  store i64 0, ptr %t27
  br label %L28
L28:
  %t30 = load i64, ptr %t5
  %t31 = load i64, ptr %t23
  %t32 = icmp uge i64 %t30, %t31
  br i1 %t32, label %L34, label %L35
L34:
  br label %L29
L35:
  br label %L33
L33:
  %t36 = load i64, ptr %t5
  %t37 = icmp ult i64 %t36, %t2
  br i1 %t37, label %L38, label %trap
L38:
  %t39 = getelementptr i64, ptr %t1, i64 %t36
  %t40 = load i64, ptr %t39
  %t41 = alloca i64
  store i64 %t40, ptr %t41
  %t42 = load i64, ptr %t24
  %t43 = load i64, ptr %t41
  %t44 = call i64 @llvm.uadd.sat.i64(i64 %t42, i64 %t43)
  store i64 %t44, ptr %t24
  %t45 = load i64, ptr %t5
  %t46 = add i64 %t45, 1
  %t47 = alloca i64
  store i64 %t46, ptr %t47
  %t48 = load i64, ptr %t47
  %t49 = icmp ult i64 %t48, %t2
  br i1 %t49, label %L50, label %trap
L50:
  %t51 = getelementptr i64, ptr %t1, i64 %t48
  %t52 = load i64, ptr %t51
  %t53 = alloca i64
  store i64 %t52, ptr %t53
  %t54 = load i64, ptr %t25
  %t55 = load i64, ptr %t53
  %t56 = call i64 @llvm.uadd.sat.i64(i64 %t54, i64 %t55)
  store i64 %t56, ptr %t25
  %t57 = load i64, ptr %t5
  %t58 = add i64 %t57, 2
  %t59 = alloca i64
  store i64 %t58, ptr %t59
  %t60 = load i64, ptr %t59
  %t61 = icmp ult i64 %t60, %t2
  br i1 %t61, label %L62, label %trap
L62:
  %t63 = getelementptr i64, ptr %t1, i64 %t60
  %t64 = load i64, ptr %t63
  %t65 = alloca i64
  store i64 %t64, ptr %t65
  %t66 = load i64, ptr %t26
  %t67 = load i64, ptr %t65
  %t68 = call i64 @llvm.uadd.sat.i64(i64 %t66, i64 %t67)
  store i64 %t68, ptr %t26
  %t69 = load i64, ptr %t5
  %t70 = add i64 %t69, 3
  %t71 = alloca i64
  store i64 %t70, ptr %t71
  %t72 = load i64, ptr %t71
  %t73 = icmp ult i64 %t72, %t2
  br i1 %t73, label %L74, label %trap
L74:
  %t75 = getelementptr i64, ptr %t1, i64 %t72
  %t76 = load i64, ptr %t75
  %t77 = alloca i64
  store i64 %t76, ptr %t77
  %t78 = load i64, ptr %t27
  %t79 = load i64, ptr %t77
  %t80 = call i64 @llvm.uadd.sat.i64(i64 %t78, i64 %t79)
  store i64 %t80, ptr %t27
  %t81 = load i64, ptr %t5
  %t82 = add i64 %t81, 4
  store i64 %t82, ptr %t5
  br label %L28
L29:
  %t83 = load i64, ptr %t24
  %t84 = load i64, ptr %t25
  %t85 = call i64 @llvm.uadd.sat.i64(i64 %t83, i64 %t84)
  %t86 = alloca i64
  store i64 %t85, ptr %t86
  %t87 = load i64, ptr %t26
  %t88 = load i64, ptr %t27
  %t89 = call i64 @llvm.uadd.sat.i64(i64 %t87, i64 %t88)
  %t90 = alloca i64
  store i64 %t89, ptr %t90
  %t91 = load i64, ptr %t86
  %t92 = load i64, ptr %t90
  %t93 = call i64 @llvm.uadd.sat.i64(i64 %t91, i64 %t92)
  %t94 = alloca i64
  store i64 %t93, ptr %t94
  %t95 = load i64, ptr %t4
  %t96 = load i64, ptr %t94
  %t97 = call i64 @llvm.uadd.sat.i64(i64 %t95, i64 %t96)
  store i64 %t97, ptr %t4
  br label %L18
L20:
  br label %L18
L18:
  br label %L9
L11:
  br label %L9
L9:
  br label %L98
L98:
  %t100 = load i64, ptr %t5
  %t101 = load i64, ptr %t3
  %t102 = icmp uge i64 %t100, %t101
  br i1 %t102, label %L104, label %L105
L104:
  br label %L99
L105:
  br label %L103
L103:
  %t106 = load i64, ptr %t5
  %t107 = icmp ult i64 %t106, %t2
  br i1 %t107, label %L108, label %trap
L108:
  %t109 = getelementptr i64, ptr %t1, i64 %t106
  %t110 = load i64, ptr %t109
  %t111 = alloca i64
  store i64 %t110, ptr %t111
  %t112 = load i64, ptr %t4
  %t113 = load i64, ptr %t111
  %t114 = call i64 @satadd(i64 %t112, i64 %t113)
  store i64 %t114, ptr %t4
  %t115 = load i64, ptr %t5
  %t116 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t115, i64 1)
  %t117 = extractvalue {i64, i1} %t116, 0
  %t118 = extractvalue {i64, i1} %t116, 1
  br i1 %t118, label %trap, label %L119
L119:
  store i64 %t117, ptr %t5
  br label %L98
L99:
  %t120 = load i64, ptr %t4
  ret i64 %t120
trap:
  call void @llvm.trap()
  unreachable
}

define i32 @main() nounwind {
entry:
  %t1 = call {i64, i1} @llvm.umul.with.overflow.i64(i64 1000, i64 8)
  %t2 = extractvalue {i64, i1} %t1, 0
  %t3 = extractvalue {i64, i1} %t1, 1
  br i1 %t3, label %trap, label %L4
L4:
  %t5 = call ptr @malloc(i64 %t2)
  %t6 = alloca i64
  store i64 0, ptr %t6
  br label %L7
L7:
  %t10 = load i64, ptr %t6
  %t11 = icmp ult i64 %t10, 1000
  br i1 %t11, label %L8, label %L9
L8:
  %t12 = getelementptr i64, ptr %t5, i64 %t10
  store i64 3, ptr %t12
  %t13 = add i64 %t10, 1
  store i64 %t13, ptr %t6
  br label %L7
L9:
  %t14 = insertvalue {ptr, i64} undef, ptr %t5, 0
  %t15 = insertvalue {ptr, i64} %t14, i64 1000, 1
  %t16 = call i64 @reduce({ptr, i64} %t15)
  %t17 = alloca i64
  store i64 %t16, ptr %t17
  %t18 = load i64, ptr %t17
  %t19 = icmp eq i64 %t18, 3000
  br i1 %t19, label %L20, label %trap
L20:
  ret i32 0
trap:
  call void @llvm.trap()
  unreachable
}
