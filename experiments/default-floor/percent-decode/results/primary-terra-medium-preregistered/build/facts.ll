declare {i32, i1} @llvm.sadd.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.ssub.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.smul.with.overflow.i32(i32, i32)
declare void @llvm.trap()

define i1 @xlang_facts_is_hex(i8 %byte) nounwind willreturn memory(none) {
entry:
  %t1 = icmp uge i8 %byte, 48
  %t2 = alloca i1
  store i1 %t1, ptr %t2
  %t3 = icmp ule i8 %byte, 57
  %t4 = alloca i1
  store i1 %t3, ptr %t4
  %t5 = load i1, ptr %t2
  %t6 = load i1, ptr %t4
  %t7 = and i1 %t5, %t6
  %t8 = alloca i1
  store i1 %t7, ptr %t8
  %t9 = icmp uge i8 %byte, 65
  %t10 = alloca i1
  store i1 %t9, ptr %t10
  %t11 = icmp ule i8 %byte, 70
  %t12 = alloca i1
  store i1 %t11, ptr %t12
  %t13 = load i1, ptr %t10
  %t14 = load i1, ptr %t12
  %t15 = and i1 %t13, %t14
  %t16 = alloca i1
  store i1 %t15, ptr %t16
  %t17 = icmp uge i8 %byte, 97
  %t18 = alloca i1
  store i1 %t17, ptr %t18
  %t19 = icmp ule i8 %byte, 102
  %t20 = alloca i1
  store i1 %t19, ptr %t20
  %t21 = load i1, ptr %t18
  %t22 = load i1, ptr %t20
  %t23 = and i1 %t21, %t22
  %t24 = alloca i1
  store i1 %t23, ptr %t24
  %t25 = load i1, ptr %t16
  %t26 = load i1, ptr %t24
  %t27 = or i1 %t25, %t26
  %t28 = alloca i1
  store i1 %t27, ptr %t28
  %t29 = load i1, ptr %t8
  %t30 = load i1, ptr %t28
  %t31 = or i1 %t29, %t30
  %t32 = alloca i1
  store i1 %t31, ptr %t32
  %t33 = load i1, ptr %t32
  ret i1 %t33
}

define i8 @xlang_facts_hex_value(i8 %byte) nounwind willreturn memory(none) {
entry:
  %t1 = icmp ule i8 %byte, 57
  %t2 = alloca i1
  store i1 %t1, ptr %t2
  %t3 = alloca i8
  %t4 = load i1, ptr %t2
  br i1 %t4, label %L6, label %L7
L6:
  %t8 = sub i8 %byte, 48
  %t9 = alloca i8
  store i8 %t8, ptr %t9
  %t10 = load i8, ptr %t9
  store i8 %t10, ptr %t3
  br label %L5
L7:
  %t11 = icmp ule i8 %byte, 70
  %t12 = alloca i1
  store i1 %t11, ptr %t12
  %t13 = alloca i8
  %t14 = load i1, ptr %t12
  br i1 %t14, label %L16, label %L17
L16:
  %t18 = sub i8 %byte, 65
  %t19 = alloca i8
  store i8 %t18, ptr %t19
  %t20 = load i8, ptr %t19
  %t21 = add i8 %t20, 10
  %t22 = alloca i8
  store i8 %t21, ptr %t22
  %t23 = load i8, ptr %t22
  store i8 %t23, ptr %t13
  br label %L15
L17:
  %t24 = sub i8 %byte, 97
  %t25 = alloca i8
  store i8 %t24, ptr %t25
  %t26 = load i8, ptr %t25
  %t27 = add i8 %t26, 10
  %t28 = alloca i8
  store i8 %t27, ptr %t28
  %t29 = load i8, ptr %t28
  store i8 %t29, ptr %t13
  br label %L15
L15:
  %t30 = load i8, ptr %t13
  store i8 %t30, ptr %t3
  br label %L5
L5:
  %t31 = load i8, ptr %t3
  ret i8 %t31
}

define i64 @xlang_decode_facts({ptr, i64} %out, {ptr, i64} %src) nounwind memory(argmem: readwrite, inaccessiblemem: write) {
entry:
  %t1 = extractvalue {ptr, i64} %out, 0
  %t2 = extractvalue {ptr, i64} %out, 1
  %t3 = extractvalue {ptr, i64} %src, 0
  %t4 = extractvalue {ptr, i64} %src, 1
  %t5 = alloca i64
  store i64 %t2, ptr %t5
  %t6 = alloca i64
  store i64 %t4, ptr %t6
  %t7 = load i64, ptr %t5
  %t8 = load i64, ptr %t6
  %t9 = icmp uge i64 %t7, %t8
  %t10 = alloca i1
  store i1 %t9, ptr %t10
  %t11 = load i1, ptr %t10
  %t13 = alloca i1
  store volatile i1 %t11, ptr %t13
  %t14 = load volatile i1, ptr %t13
  br i1 %t14, label %L12, label %trap
L12:
  %t15 = alloca i64
  store i64 %t4, ptr %t15
  %t16 = alloca i64
  store i64 0, ptr %t16
  %t17 = alloca i64
  store i64 0, ptr %t17
  br label %L18
L18:
  %t20 = load i64, ptr %t16
  %t21 = load i64, ptr %t15
  %t22 = icmp eq i64 %t20, %t21
  %t23 = alloca i1
  store i1 %t22, ptr %t23
  %t24 = load i1, ptr %t23
  br i1 %t24, label %L26, label %L27
L26:
  br label %L19
L27:
  br label %L25
L25:
  %t28 = load i64, ptr %t16
  %t29 = icmp ult i64 %t28, %t4
  br i1 %t29, label %L30, label %trap
L30:
  %t31 = getelementptr i8, ptr %t3, i64 %t28
  %t32 = load i8, ptr %t31
  %t33 = alloca i8
  store i8 %t32, ptr %t33
  %t34 = load i8, ptr %t33
  %t35 = icmp eq i8 %t34, 37
  %t36 = alloca i1
  store i1 %t35, ptr %t36
  %t37 = load i64, ptr %t15
  %t38 = load i64, ptr %t16
  %t39 = sub i64 %t37, %t38
  %t40 = alloca i64
  store i64 %t39, ptr %t40
  %t41 = load i64, ptr %t40
  %t42 = icmp uge i64 %t41, 3
  %t43 = alloca i1
  store i1 %t42, ptr %t43
  %t44 = load i1, ptr %t36
  %t45 = load i1, ptr %t43
  %t46 = and i1 %t44, %t45
  %t47 = alloca i1
  store i1 %t46, ptr %t47
  %t48 = load i1, ptr %t47
  br i1 %t48, label %L50, label %L51
L50:
  %t52 = load i64, ptr %t16
  %t53 = add i64 %t52, 1
  %t54 = alloca i64
  store i64 %t53, ptr %t54
  %t55 = load i64, ptr %t16
  %t56 = add i64 %t55, 2
  %t57 = alloca i64
  store i64 %t56, ptr %t57
  %t58 = load i64, ptr %t54
  %t59 = icmp ult i64 %t58, %t4
  br i1 %t59, label %L60, label %trap
L60:
  %t61 = getelementptr i8, ptr %t3, i64 %t58
  %t62 = load i8, ptr %t61
  %t63 = alloca i8
  store i8 %t62, ptr %t63
  %t64 = load i64, ptr %t57
  %t65 = icmp ult i64 %t64, %t4
  br i1 %t65, label %L66, label %trap
L66:
  %t67 = getelementptr i8, ptr %t3, i64 %t64
  %t68 = load i8, ptr %t67
  %t69 = alloca i8
  store i8 %t68, ptr %t69
  %t70 = load i8, ptr %t63
  %t71 = call i1 @xlang_facts_is_hex(i8 %t70)
  %t72 = alloca i1
  store i1 %t71, ptr %t72
  %t73 = load i8, ptr %t69
  %t74 = call i1 @xlang_facts_is_hex(i8 %t73)
  %t75 = alloca i1
  store i1 %t74, ptr %t75
  %t76 = load i1, ptr %t72
  %t77 = load i1, ptr %t75
  %t78 = and i1 %t76, %t77
  %t79 = alloca i1
  store i1 %t78, ptr %t79
  %t80 = load i1, ptr %t79
  br i1 %t80, label %L82, label %L83
L82:
  %t84 = load i8, ptr %t63
  %t85 = call i8 @xlang_facts_hex_value(i8 %t84)
  %t86 = alloca i8
  store i8 %t85, ptr %t86
  %t87 = load i8, ptr %t69
  %t88 = call i8 @xlang_facts_hex_value(i8 %t87)
  %t89 = alloca i8
  store i8 %t88, ptr %t89
  %t90 = load i8, ptr %t86
  %t91 = mul i8 %t90, 16
  %t92 = alloca i8
  store i8 %t91, ptr %t92
  %t93 = load i8, ptr %t92
  %t94 = load i8, ptr %t89
  %t95 = add i8 %t93, %t94
  %t96 = alloca i8
  store i8 %t95, ptr %t96
  %t97 = load i8, ptr %t96
  %t98 = load i64, ptr %t17
  %t99 = icmp ult i64 %t98, %t2
  br i1 %t99, label %L100, label %trap
L100:
  %t101 = getelementptr i8, ptr %t1, i64 %t98
  store i8 %t97, ptr %t101
  %t102 = load i64, ptr %t16
  %t103 = add i64 %t102, 3
  store i64 %t103, ptr %t16
  %t104 = load i64, ptr %t17
  %t105 = add i64 %t104, 1
  store i64 %t105, ptr %t17
  br label %L81
L83:
  %t106 = load i8, ptr %t33
  %t107 = load i64, ptr %t17
  %t108 = icmp ult i64 %t107, %t2
  br i1 %t108, label %L109, label %trap
L109:
  %t110 = getelementptr i8, ptr %t1, i64 %t107
  store i8 %t106, ptr %t110
  %t111 = load i64, ptr %t16
  %t112 = add i64 %t111, 1
  store i64 %t112, ptr %t16
  %t113 = load i64, ptr %t17
  %t114 = add i64 %t113, 1
  store i64 %t114, ptr %t17
  br label %L81
L81:
  br label %L49
L51:
  %t115 = load i8, ptr %t33
  %t116 = load i64, ptr %t17
  %t117 = icmp ult i64 %t116, %t2
  br i1 %t117, label %L118, label %trap
L118:
  %t119 = getelementptr i8, ptr %t1, i64 %t116
  store i8 %t115, ptr %t119
  %t120 = load i64, ptr %t16
  %t121 = add i64 %t120, 1
  store i64 %t121, ptr %t16
  %t122 = load i64, ptr %t17
  %t123 = add i64 %t122, 1
  store i64 %t123, ptr %t17
  br label %L49
L49:
  br label %L18
L19:
  %t124 = load i64, ptr %t17
  ret i64 %t124
trap:
  call void @llvm.trap()
  unreachable
}
