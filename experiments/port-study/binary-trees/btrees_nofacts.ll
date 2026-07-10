%Pool = type { {ptr, i64}, {ptr, i64}, i64 }
declare {i32, i1} @llvm.sadd.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.ssub.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.smul.with.overflow.i32(i32, i32)
declare void @llvm.trap()
declare ptr @malloc(i64)
declare {i64, i1} @llvm.uadd.with.overflow.i64(i64, i64)
declare {i64, i1} @llvm.umul.with.overflow.i64(i64, i64)
declare {i64, i1} @llvm.usub.with.overflow.i64(i64, i64)

define i64 @build(ptr %s, i64 %d) {
entry:
  %t1 = and i64 %d, 63
  %t2 = shl i64 1, %t1
  %t3 = alloca i64
  store i64 %t2, ptr %t3
  %t4 = getelementptr %Pool, ptr %s, i32 0, i32 2
  %t5 = load i64, ptr %t4
  %t6 = alloca i64
  store i64 %t5, ptr %t6
  %t7 = alloca i64
  store i64 0, ptr %t7
  br label %L8
L8:
  %t10 = load i64, ptr %t7
  %t11 = load i64, ptr %t3
  %t12 = icmp uge i64 %t10, %t11
  br i1 %t12, label %L14, label %L15
L14:
  br label %L9
L15:
  br label %L13
L13:
  %t16 = getelementptr %Pool, ptr %s, i32 0, i32 2
  %t17 = load i64, ptr %t16
  %t18 = alloca i64
  store i64 %t17, ptr %t18
  %t19 = getelementptr %Pool, ptr %s, i32 0, i32 0
  %t20 = getelementptr {ptr, i64}, ptr %t19, i32 0, i32 0
  %t21 = load ptr, ptr %t20
  %t22 = getelementptr {ptr, i64}, ptr %t19, i32 0, i32 1
  %t23 = load i64, ptr %t22
  %t24 = load i64, ptr %t18
  %t25 = icmp ult i64 %t24, %t23
  br i1 %t25, label %L26, label %trap
L26:
  %t27 = getelementptr i64, ptr %t21, i64 %t24
  store i64 0, ptr %t27
  %t28 = getelementptr %Pool, ptr %s, i32 0, i32 1
  %t29 = getelementptr {ptr, i64}, ptr %t28, i32 0, i32 0
  %t30 = load ptr, ptr %t29
  %t31 = getelementptr {ptr, i64}, ptr %t28, i32 0, i32 1
  %t32 = load i64, ptr %t31
  %t33 = load i64, ptr %t18
  %t34 = icmp ult i64 %t33, %t32
  br i1 %t34, label %L35, label %trap
L35:
  %t36 = getelementptr i64, ptr %t30, i64 %t33
  store i64 0, ptr %t36
  %t37 = load i64, ptr %t18
  %t38 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t37, i64 1)
  %t39 = extractvalue {i64, i1} %t38, 0
  %t40 = extractvalue {i64, i1} %t38, 1
  br i1 %t40, label %trap, label %L41
L41:
  %t42 = getelementptr %Pool, ptr %s, i32 0, i32 2
  store i64 %t39, ptr %t42
  %t43 = load i64, ptr %t7
  %t44 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t43, i64 1)
  %t45 = extractvalue {i64, i1} %t44, 0
  %t46 = extractvalue {i64, i1} %t44, 1
  br i1 %t46, label %trap, label %L47
L47:
  store i64 %t45, ptr %t7
  br label %L8
L9:
  %t48 = load i64, ptr %t3
  %t49 = alloca i64
  store i64 %t48, ptr %t49
  br label %L50
L50:
  %t52 = load i64, ptr %t49
  %t53 = icmp ule i64 %t52, 1
  br i1 %t53, label %L55, label %L56
L55:
  br label %L51
L56:
  br label %L54
L54:
  %t57 = load i64, ptr %t49
  %t58 = and i64 1, 63
  %t59 = lshr i64 %t57, %t58
  %t60 = alloca i64
  store i64 %t59, ptr %t60
  %t61 = getelementptr %Pool, ptr %s, i32 0, i32 2
  %t62 = load i64, ptr %t61
  %t63 = alloca i64
  store i64 %t62, ptr %t63
  %t64 = alloca i64
  store i64 0, ptr %t64
  br label %L65
L65:
  %t67 = load i64, ptr %t64
  %t68 = load i64, ptr %t60
  %t69 = icmp uge i64 %t67, %t68
  br i1 %t69, label %L71, label %L72
L71:
  br label %L66
L72:
  br label %L70
L70:
  %t73 = load i64, ptr %t64
  %t74 = call {i64, i1} @llvm.umul.with.overflow.i64(i64 %t73, i64 2)
  %t75 = extractvalue {i64, i1} %t74, 0
  %t76 = extractvalue {i64, i1} %t74, 1
  br i1 %t76, label %trap, label %L77
L77:
  %t78 = alloca i64
  store i64 %t75, ptr %t78
  %t79 = load i64, ptr %t6
  %t80 = load i64, ptr %t78
  %t81 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t79, i64 %t80)
  %t82 = extractvalue {i64, i1} %t81, 0
  %t83 = extractvalue {i64, i1} %t81, 1
  br i1 %t83, label %trap, label %L84
L84:
  %t85 = alloca i64
  store i64 %t82, ptr %t85
  %t86 = load i64, ptr %t85
  %t87 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t86, i64 1)
  %t88 = extractvalue {i64, i1} %t87, 0
  %t89 = extractvalue {i64, i1} %t87, 1
  br i1 %t89, label %trap, label %L90
L90:
  %t91 = alloca i64
  store i64 %t88, ptr %t91
  %t92 = getelementptr %Pool, ptr %s, i32 0, i32 2
  %t93 = load i64, ptr %t92
  %t94 = alloca i64
  store i64 %t93, ptr %t94
  %t95 = load i64, ptr %t85
  %t96 = getelementptr %Pool, ptr %s, i32 0, i32 0
  %t97 = getelementptr {ptr, i64}, ptr %t96, i32 0, i32 0
  %t98 = load ptr, ptr %t97
  %t99 = getelementptr {ptr, i64}, ptr %t96, i32 0, i32 1
  %t100 = load i64, ptr %t99
  %t101 = load i64, ptr %t94
  %t102 = icmp ult i64 %t101, %t100
  br i1 %t102, label %L103, label %trap
L103:
  %t104 = getelementptr i64, ptr %t98, i64 %t101
  store i64 %t95, ptr %t104
  %t105 = load i64, ptr %t91
  %t106 = getelementptr %Pool, ptr %s, i32 0, i32 1
  %t107 = getelementptr {ptr, i64}, ptr %t106, i32 0, i32 0
  %t108 = load ptr, ptr %t107
  %t109 = getelementptr {ptr, i64}, ptr %t106, i32 0, i32 1
  %t110 = load i64, ptr %t109
  %t111 = load i64, ptr %t94
  %t112 = icmp ult i64 %t111, %t110
  br i1 %t112, label %L113, label %trap
L113:
  %t114 = getelementptr i64, ptr %t108, i64 %t111
  store i64 %t105, ptr %t114
  %t115 = load i64, ptr %t94
  %t116 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t115, i64 1)
  %t117 = extractvalue {i64, i1} %t116, 0
  %t118 = extractvalue {i64, i1} %t116, 1
  br i1 %t118, label %trap, label %L119
L119:
  %t120 = getelementptr %Pool, ptr %s, i32 0, i32 2
  store i64 %t117, ptr %t120
  %t121 = load i64, ptr %t64
  %t122 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t121, i64 1)
  %t123 = extractvalue {i64, i1} %t122, 0
  %t124 = extractvalue {i64, i1} %t122, 1
  br i1 %t124, label %trap, label %L125
L125:
  store i64 %t123, ptr %t64
  br label %L65
L66:
  %t126 = load i64, ptr %t63
  store i64 %t126, ptr %t6
  %t127 = load i64, ptr %t60
  store i64 %t127, ptr %t49
  br label %L50
L51:
  %t128 = load i64, ptr %t6
  ret i64 %t128
trap:
  call void @llvm.trap()
  unreachable
}

define i64 @chk(ptr %s, i64 %i) {
entry:
  %t1 = getelementptr %Pool, ptr %s, i32 0, i32 0
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
  ret i64 1
L15:
  br label %L13
L13:
  %t16 = getelementptr %Pool, ptr %s, i32 0, i32 1
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
  %t26 = load i64, ptr %t10
  %t27 = call i64 @chk(ptr %s, i64 %t26)
  %t28 = alloca i64
  store i64 %t27, ptr %t28
  %t29 = load i64, ptr %t25
  %t30 = call i64 @chk(ptr %s, i64 %t29)
  %t31 = alloca i64
  store i64 %t30, ptr %t31
  %t32 = load i64, ptr %t28
  %t33 = load i64, ptr %t31
  %t34 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t32, i64 %t33)
  %t35 = extractvalue {i64, i1} %t34, 0
  %t36 = extractvalue {i64, i1} %t34, 1
  br i1 %t36, label %trap, label %L37
L37:
  %t38 = alloca i64
  store i64 %t35, ptr %t38
  %t39 = load i64, ptr %t38
  %t40 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t39, i64 1)
  %t41 = extractvalue {i64, i1} %t40, 0
  %t42 = extractvalue {i64, i1} %t40, 1
  br i1 %t42, label %trap, label %L43
L43:
  ret i64 %t41
trap:
  call void @llvm.trap()
  unreachable
}

define i32 @main() {
entry:
  %t1 = alloca i64
  store i64 21, ptr %t1
  %t2 = alloca i64
  store i64 4, ptr %t2
  %t3 = load i64, ptr %t1
  %t4 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t3, i64 2)
  %t5 = extractvalue {i64, i1} %t4, 0
  %t6 = extractvalue {i64, i1} %t4, 1
  br i1 %t6, label %trap, label %L7
L7:
  %t8 = alloca i64
  store i64 %t5, ptr %t8
  %t9 = load i64, ptr %t8
  %t10 = and i64 %t9, 63
  %t11 = shl i64 1, %t10
  %t12 = alloca i64
  store i64 %t11, ptr %t12
  %t13 = load i64, ptr %t12
  %t14 = call {i64, i1} @llvm.umul.with.overflow.i64(i64 %t13, i64 8)
  %t15 = extractvalue {i64, i1} %t14, 0
  %t16 = extractvalue {i64, i1} %t14, 1
  br i1 %t16, label %trap, label %L17
L17:
  %t18 = call ptr @malloc(i64 %t15)
  %t19 = alloca i64
  store i64 0, ptr %t19
  br label %L20
L20:
  %t23 = load i64, ptr %t19
  %t24 = icmp ult i64 %t23, %t13
  br i1 %t24, label %L21, label %L22
L21:
  %t25 = getelementptr i64, ptr %t18, i64 %t23
  store i64 0, ptr %t25
  %t26 = add i64 %t23, 1
  store i64 %t26, ptr %t19
  br label %L20
L22:
  %t27 = load i64, ptr %t12
  %t28 = call {i64, i1} @llvm.umul.with.overflow.i64(i64 %t27, i64 8)
  %t29 = extractvalue {i64, i1} %t28, 0
  %t30 = extractvalue {i64, i1} %t28, 1
  br i1 %t30, label %trap, label %L31
L31:
  %t32 = call ptr @malloc(i64 %t29)
  %t33 = alloca i64
  store i64 0, ptr %t33
  br label %L34
L34:
  %t37 = load i64, ptr %t33
  %t38 = icmp ult i64 %t37, %t27
  br i1 %t38, label %L35, label %L36
L35:
  %t39 = getelementptr i64, ptr %t32, i64 %t37
  store i64 0, ptr %t39
  %t40 = add i64 %t37, 1
  store i64 %t40, ptr %t33
  br label %L34
L36:
  %t41 = alloca %Pool
  %t42 = getelementptr %Pool, ptr %t41, i32 0, i32 0
  %t43 = insertvalue {ptr, i64} undef, ptr %t18, 0
  %t44 = insertvalue {ptr, i64} %t43, i64 %t13, 1
  store {ptr, i64} %t44, ptr %t42
  %t45 = getelementptr %Pool, ptr %t41, i32 0, i32 1
  %t46 = insertvalue {ptr, i64} undef, ptr %t32, 0
  %t47 = insertvalue {ptr, i64} %t46, i64 %t27, 1
  store {ptr, i64} %t47, ptr %t45
  %t48 = getelementptr %Pool, ptr %t41, i32 0, i32 2
  store i64 1, ptr %t48
  %t49 = load i64, ptr %t12
  %t50 = call {i64, i1} @llvm.umul.with.overflow.i64(i64 %t49, i64 8)
  %t51 = extractvalue {i64, i1} %t50, 0
  %t52 = extractvalue {i64, i1} %t50, 1
  br i1 %t52, label %trap, label %L53
L53:
  %t54 = call ptr @malloc(i64 %t51)
  %t55 = alloca i64
  store i64 0, ptr %t55
  br label %L56
L56:
  %t59 = load i64, ptr %t55
  %t60 = icmp ult i64 %t59, %t49
  br i1 %t60, label %L57, label %L58
L57:
  %t61 = getelementptr i64, ptr %t54, i64 %t59
  store i64 0, ptr %t61
  %t62 = add i64 %t59, 1
  store i64 %t62, ptr %t55
  br label %L56
L58:
  %t63 = load i64, ptr %t12
  %t64 = call {i64, i1} @llvm.umul.with.overflow.i64(i64 %t63, i64 8)
  %t65 = extractvalue {i64, i1} %t64, 0
  %t66 = extractvalue {i64, i1} %t64, 1
  br i1 %t66, label %trap, label %L67
L67:
  %t68 = call ptr @malloc(i64 %t65)
  %t69 = alloca i64
  store i64 0, ptr %t69
  br label %L70
L70:
  %t73 = load i64, ptr %t69
  %t74 = icmp ult i64 %t73, %t63
  br i1 %t74, label %L71, label %L72
L71:
  %t75 = getelementptr i64, ptr %t68, i64 %t73
  store i64 0, ptr %t75
  %t76 = add i64 %t73, 1
  store i64 %t76, ptr %t69
  br label %L70
L72:
  %t77 = alloca %Pool
  %t78 = getelementptr %Pool, ptr %t77, i32 0, i32 0
  %t79 = insertvalue {ptr, i64} undef, ptr %t54, 0
  %t80 = insertvalue {ptr, i64} %t79, i64 %t49, 1
  store {ptr, i64} %t80, ptr %t78
  %t81 = getelementptr %Pool, ptr %t77, i32 0, i32 1
  %t82 = insertvalue {ptr, i64} undef, ptr %t68, 0
  %t83 = insertvalue {ptr, i64} %t82, i64 %t63, 1
  store {ptr, i64} %t83, ptr %t81
  %t84 = getelementptr %Pool, ptr %t77, i32 0, i32 2
  store i64 1, ptr %t84
  %t85 = load i64, ptr %t1
  %t86 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t85, i64 1)
  %t87 = extractvalue {i64, i1} %t86, 0
  %t88 = extractvalue {i64, i1} %t86, 1
  br i1 %t88, label %trap, label %L89
L89:
  %t90 = alloca i64
  store i64 %t87, ptr %t90
  %t91 = load i64, ptr %t90
  %t92 = call i64 @build(ptr %t41, i64 %t91)
  %t93 = alloca i64
  store i64 %t92, ptr %t93
  %t94 = load i64, ptr %t93
  %t95 = call i64 @chk(ptr %t41, i64 %t94)
  %t96 = alloca i64
  store i64 %t95, ptr %t96
  %t97 = load i64, ptr %t90
  %t98 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t97, i64 1)
  %t99 = extractvalue {i64, i1} %t98, 0
  %t100 = extractvalue {i64, i1} %t98, 1
  br i1 %t100, label %trap, label %L101
L101:
  %t102 = alloca i64
  store i64 %t99, ptr %t102
  %t103 = load i64, ptr %t102
  %t104 = and i64 %t103, 63
  %t105 = shl i64 1, %t104
  %t106 = alloca i64
  store i64 %t105, ptr %t106
  %t107 = load i64, ptr %t106
  %t108 = call {i64, i1} @llvm.usub.with.overflow.i64(i64 %t107, i64 1)
  %t109 = extractvalue {i64, i1} %t108, 0
  %t110 = extractvalue {i64, i1} %t108, 1
  br i1 %t110, label %trap, label %L111
L111:
  %t112 = alloca i64
  store i64 %t109, ptr %t112
  %t113 = load i64, ptr %t96
  %t114 = load i64, ptr %t112
  %t115 = icmp eq i64 %t113, %t114
  br i1 %t115, label %L116, label %trap
L116:
  %t117 = getelementptr %Pool, ptr %t41, i32 0, i32 2
  store i64 1, ptr %t117
  %t118 = load i64, ptr %t1
  %t119 = call i64 @build(ptr %t41, i64 %t118)
  %t120 = alloca i64
  store i64 %t119, ptr %t120
  %t121 = load i64, ptr %t2
  %t122 = alloca i64
  store i64 %t121, ptr %t122
  br label %L123
L123:
  %t125 = load i64, ptr %t122
  %t126 = load i64, ptr %t1
  %t127 = icmp ugt i64 %t125, %t126
  br i1 %t127, label %L129, label %L130
L129:
  br label %L124
L130:
  br label %L128
L128:
  %t131 = load i64, ptr %t1
  %t132 = load i64, ptr %t122
  %t133 = call {i64, i1} @llvm.usub.with.overflow.i64(i64 %t131, i64 %t132)
  %t134 = extractvalue {i64, i1} %t133, 0
  %t135 = extractvalue {i64, i1} %t133, 1
  br i1 %t135, label %trap, label %L136
L136:
  %t137 = alloca i64
  store i64 %t134, ptr %t137
  %t138 = load i64, ptr %t137
  %t139 = load i64, ptr %t2
  %t140 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t138, i64 %t139)
  %t141 = extractvalue {i64, i1} %t140, 0
  %t142 = extractvalue {i64, i1} %t140, 1
  br i1 %t142, label %trap, label %L143
L143:
  %t144 = alloca i64
  store i64 %t141, ptr %t144
  %t145 = load i64, ptr %t144
  %t146 = and i64 %t145, 63
  %t147 = shl i64 1, %t146
  %t148 = alloca i64
  store i64 %t147, ptr %t148
  %t149 = load i64, ptr %t122
  %t150 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t149, i64 1)
  %t151 = extractvalue {i64, i1} %t150, 0
  %t152 = extractvalue {i64, i1} %t150, 1
  br i1 %t152, label %trap, label %L153
L153:
  %t154 = alloca i64
  store i64 %t151, ptr %t154
  %t155 = load i64, ptr %t154
  %t156 = and i64 %t155, 63
  %t157 = shl i64 1, %t156
  %t158 = alloca i64
  store i64 %t157, ptr %t158
  %t159 = load i64, ptr %t158
  %t160 = call {i64, i1} @llvm.usub.with.overflow.i64(i64 %t159, i64 1)
  %t161 = extractvalue {i64, i1} %t160, 0
  %t162 = extractvalue {i64, i1} %t160, 1
  br i1 %t162, label %trap, label %L163
L163:
  %t164 = alloca i64
  store i64 %t161, ptr %t164
  %t165 = alloca i64
  store i64 0, ptr %t165
  %t166 = alloca i64
  store i64 0, ptr %t166
  br label %L167
L167:
  %t169 = load i64, ptr %t166
  %t170 = load i64, ptr %t148
  %t171 = icmp uge i64 %t169, %t170
  br i1 %t171, label %L173, label %L174
L173:
  br label %L168
L174:
  br label %L172
L172:
  %t175 = getelementptr %Pool, ptr %t77, i32 0, i32 2
  store i64 1, ptr %t175
  %t176 = load i64, ptr %t122
  %t177 = call i64 @build(ptr %t77, i64 %t176)
  %t178 = alloca i64
  store i64 %t177, ptr %t178
  %t179 = load i64, ptr %t178
  %t180 = call i64 @chk(ptr %t77, i64 %t179)
  %t181 = alloca i64
  store i64 %t180, ptr %t181
  %t182 = load i64, ptr %t165
  %t183 = load i64, ptr %t181
  %t184 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t182, i64 %t183)
  %t185 = extractvalue {i64, i1} %t184, 0
  %t186 = extractvalue {i64, i1} %t184, 1
  br i1 %t186, label %trap, label %L187
L187:
  store i64 %t185, ptr %t165
  %t188 = load i64, ptr %t166
  %t189 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t188, i64 1)
  %t190 = extractvalue {i64, i1} %t189, 0
  %t191 = extractvalue {i64, i1} %t189, 1
  br i1 %t191, label %trap, label %L192
L192:
  store i64 %t190, ptr %t166
  br label %L167
L168:
  %t193 = load i64, ptr %t148
  %t194 = load i64, ptr %t164
  %t195 = call {i64, i1} @llvm.umul.with.overflow.i64(i64 %t193, i64 %t194)
  %t196 = extractvalue {i64, i1} %t195, 0
  %t197 = extractvalue {i64, i1} %t195, 1
  br i1 %t197, label %trap, label %L198
L198:
  %t199 = alloca i64
  store i64 %t196, ptr %t199
  %t200 = load i64, ptr %t165
  %t201 = load i64, ptr %t199
  %t202 = icmp eq i64 %t200, %t201
  br i1 %t202, label %L203, label %trap
L203:
  %t204 = load i64, ptr %t122
  %t205 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t204, i64 2)
  %t206 = extractvalue {i64, i1} %t205, 0
  %t207 = extractvalue {i64, i1} %t205, 1
  br i1 %t207, label %trap, label %L208
L208:
  store i64 %t206, ptr %t122
  br label %L123
L124:
  %t209 = load i64, ptr %t120
  %t210 = call i64 @chk(ptr %t41, i64 %t209)
  %t211 = alloca i64
  store i64 %t210, ptr %t211
  %t212 = load i64, ptr %t1
  %t213 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t212, i64 1)
  %t214 = extractvalue {i64, i1} %t213, 0
  %t215 = extractvalue {i64, i1} %t213, 1
  br i1 %t215, label %trap, label %L216
L216:
  %t217 = alloca i64
  store i64 %t214, ptr %t217
  %t218 = load i64, ptr %t217
  %t219 = and i64 %t218, 63
  %t220 = shl i64 1, %t219
  %t221 = alloca i64
  store i64 %t220, ptr %t221
  %t222 = load i64, ptr %t221
  %t223 = call {i64, i1} @llvm.usub.with.overflow.i64(i64 %t222, i64 1)
  %t224 = extractvalue {i64, i1} %t223, 0
  %t225 = extractvalue {i64, i1} %t223, 1
  br i1 %t225, label %trap, label %L226
L226:
  %t227 = alloca i64
  store i64 %t224, ptr %t227
  %t228 = load i64, ptr %t211
  %t229 = load i64, ptr %t227
  %t230 = icmp eq i64 %t228, %t229
  br i1 %t230, label %L231, label %trap
L231:
  ret i32 0
trap:
  call void @llvm.trap()
  unreachable
}
