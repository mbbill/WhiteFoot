%Cols = type { {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64} }
declare {i32, i1} @llvm.sadd.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.ssub.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.smul.with.overflow.i32(i32, i32)
declare void @llvm.trap()
declare i64 @llvm.umin.i64(i64, i64)
declare {i64, i1} @llvm.uadd.with.overflow.i64(i64, i64)

define void @kernel(ptr noalias dereferenceable(128) align 8 %s) nounwind memory(argmem: readwrite, inaccessiblemem: write) {
entry:
  %t1 = getelementptr %Cols, ptr %s, i32 0, i32 0
  %t2 = getelementptr {ptr, i64}, ptr %t1, i32 0, i32 0
  %t3 = load ptr, ptr %t2, !alias.scope !10, !noalias !11
  %t4 = getelementptr {ptr, i64}, ptr %t1, i32 0, i32 1
  %t5 = load i64, ptr %t4, !alias.scope !10, !noalias !11
  %t6 = alloca i64
  store i64 %t5, ptr %t6
  %t7 = getelementptr %Cols, ptr %s, i32 0, i32 1
  %t8 = getelementptr {ptr, i64}, ptr %t7, i32 0, i32 0
  %t9 = load ptr, ptr %t8, !alias.scope !10, !noalias !11
  %t10 = getelementptr {ptr, i64}, ptr %t7, i32 0, i32 1
  %t11 = load i64, ptr %t10, !alias.scope !10, !noalias !11
  %t12 = alloca i64
  store i64 %t11, ptr %t12
  %t13 = getelementptr %Cols, ptr %s, i32 0, i32 2
  %t14 = getelementptr {ptr, i64}, ptr %t13, i32 0, i32 0
  %t15 = load ptr, ptr %t14, !alias.scope !10, !noalias !11
  %t16 = getelementptr {ptr, i64}, ptr %t13, i32 0, i32 1
  %t17 = load i64, ptr %t16, !alias.scope !10, !noalias !11
  %t18 = alloca i64
  store i64 %t17, ptr %t18
  %t19 = getelementptr %Cols, ptr %s, i32 0, i32 3
  %t20 = getelementptr {ptr, i64}, ptr %t19, i32 0, i32 0
  %t21 = load ptr, ptr %t20, !alias.scope !10, !noalias !11
  %t22 = getelementptr {ptr, i64}, ptr %t19, i32 0, i32 1
  %t23 = load i64, ptr %t22, !alias.scope !10, !noalias !11
  %t24 = alloca i64
  store i64 %t23, ptr %t24
  %t25 = getelementptr %Cols, ptr %s, i32 0, i32 4
  %t26 = getelementptr {ptr, i64}, ptr %t25, i32 0, i32 0
  %t27 = load ptr, ptr %t26, !alias.scope !10, !noalias !11
  %t28 = getelementptr {ptr, i64}, ptr %t25, i32 0, i32 1
  %t29 = load i64, ptr %t28, !alias.scope !10, !noalias !11
  %t30 = alloca i64
  store i64 %t29, ptr %t30
  %t31 = getelementptr %Cols, ptr %s, i32 0, i32 5
  %t32 = getelementptr {ptr, i64}, ptr %t31, i32 0, i32 0
  %t33 = load ptr, ptr %t32, !alias.scope !10, !noalias !11
  %t34 = getelementptr {ptr, i64}, ptr %t31, i32 0, i32 1
  %t35 = load i64, ptr %t34, !alias.scope !10, !noalias !11
  %t36 = alloca i64
  store i64 %t35, ptr %t36
  %t37 = getelementptr %Cols, ptr %s, i32 0, i32 6
  %t38 = getelementptr {ptr, i64}, ptr %t37, i32 0, i32 0
  %t39 = load ptr, ptr %t38, !alias.scope !10, !noalias !11
  %t40 = getelementptr {ptr, i64}, ptr %t37, i32 0, i32 1
  %t41 = load i64, ptr %t40, !alias.scope !10, !noalias !11
  %t42 = alloca i64
  store i64 %t41, ptr %t42
  %t43 = getelementptr %Cols, ptr %s, i32 0, i32 7
  %t44 = getelementptr {ptr, i64}, ptr %t43, i32 0, i32 0
  %t45 = load ptr, ptr %t44, !alias.scope !10, !noalias !11
  %t46 = getelementptr {ptr, i64}, ptr %t43, i32 0, i32 1
  %t47 = load i64, ptr %t46, !alias.scope !10, !noalias !11
  %t48 = alloca i64
  store i64 %t47, ptr %t48
  %t49 = load i64, ptr %t6
  %t50 = load i64, ptr %t12
  %t51 = call i64 @llvm.umin.i64(i64 %t49, i64 %t50)
  %t52 = alloca i64
  store i64 %t51, ptr %t52
  %t53 = load i64, ptr %t52
  %t54 = load i64, ptr %t18
  %t55 = call i64 @llvm.umin.i64(i64 %t53, i64 %t54)
  %t56 = alloca i64
  store i64 %t55, ptr %t56
  %t57 = load i64, ptr %t56
  %t58 = load i64, ptr %t24
  %t59 = call i64 @llvm.umin.i64(i64 %t57, i64 %t58)
  %t60 = alloca i64
  store i64 %t59, ptr %t60
  %t61 = load i64, ptr %t60
  %t62 = load i64, ptr %t30
  %t63 = call i64 @llvm.umin.i64(i64 %t61, i64 %t62)
  %t64 = alloca i64
  store i64 %t63, ptr %t64
  %t65 = load i64, ptr %t64
  %t66 = load i64, ptr %t36
  %t67 = call i64 @llvm.umin.i64(i64 %t65, i64 %t66)
  %t68 = alloca i64
  store i64 %t67, ptr %t68
  %t69 = load i64, ptr %t68
  %t70 = load i64, ptr %t42
  %t71 = call i64 @llvm.umin.i64(i64 %t69, i64 %t70)
  %t72 = alloca i64
  store i64 %t71, ptr %t72
  %t73 = load i64, ptr %t72
  %t74 = load i64, ptr %t48
  %t75 = call i64 @llvm.umin.i64(i64 %t73, i64 %t74)
  %t76 = alloca i64
  store i64 %t75, ptr %t76
  %t77 = alloca i64
  store i64 0, ptr %t77
  br label %L78
L78:
  %t80 = load i64, ptr %t77
  %t81 = load i64, ptr %t76
  %t82 = icmp uge i64 %t80, %t81
  br i1 %t82, label %L84, label %L85
L84:
  br label %L79
L85:
  br label %L83
L83:
  %t86 = getelementptr %Cols, ptr %s, i32 0, i32 0
  %t87 = getelementptr {ptr, i64}, ptr %t86, i32 0, i32 0
  %t88 = load ptr, ptr %t87, !alias.scope !10, !noalias !11
  %t89 = getelementptr {ptr, i64}, ptr %t86, i32 0, i32 1
  %t90 = load i64, ptr %t89, !alias.scope !10, !noalias !11
  %t91 = load i64, ptr %t77
  %t92 = icmp ult i64 %t91, %t90
  br i1 %t92, label %L93, label %trap
L93:
  %t94 = getelementptr i64, ptr %t88, i64 %t91
  %t95 = load i64, ptr %t94, !alias.scope !12, !noalias !13
  %t96 = alloca i64
  store i64 %t95, ptr %t96
  %t97 = getelementptr %Cols, ptr %s, i32 0, i32 2
  %t98 = getelementptr {ptr, i64}, ptr %t97, i32 0, i32 0
  %t99 = load ptr, ptr %t98, !alias.scope !10, !noalias !11
  %t100 = getelementptr {ptr, i64}, ptr %t97, i32 0, i32 1
  %t101 = load i64, ptr %t100, !alias.scope !10, !noalias !11
  %t102 = load i64, ptr %t77
  %t103 = icmp ult i64 %t102, %t101
  br i1 %t103, label %L104, label %trap
L104:
  %t105 = getelementptr i64, ptr %t99, i64 %t102
  %t106 = load i64, ptr %t105, !alias.scope !16, !noalias !17
  %t107 = alloca i64
  store i64 %t106, ptr %t107
  %t108 = getelementptr %Cols, ptr %s, i32 0, i32 3
  %t109 = getelementptr {ptr, i64}, ptr %t108, i32 0, i32 0
  %t110 = load ptr, ptr %t109, !alias.scope !10, !noalias !11
  %t111 = getelementptr {ptr, i64}, ptr %t108, i32 0, i32 1
  %t112 = load i64, ptr %t111, !alias.scope !10, !noalias !11
  %t113 = load i64, ptr %t77
  %t114 = icmp ult i64 %t113, %t112
  br i1 %t114, label %L115, label %trap
L115:
  %t116 = getelementptr i64, ptr %t110, i64 %t113
  %t117 = load i64, ptr %t116, !alias.scope !18, !noalias !19
  %t118 = alloca i64
  store i64 %t117, ptr %t118
  %t119 = getelementptr %Cols, ptr %s, i32 0, i32 4
  %t120 = getelementptr {ptr, i64}, ptr %t119, i32 0, i32 0
  %t121 = load ptr, ptr %t120, !alias.scope !10, !noalias !11
  %t122 = getelementptr {ptr, i64}, ptr %t119, i32 0, i32 1
  %t123 = load i64, ptr %t122, !alias.scope !10, !noalias !11
  %t124 = load i64, ptr %t77
  %t125 = icmp ult i64 %t124, %t123
  br i1 %t125, label %L126, label %trap
L126:
  %t127 = getelementptr i64, ptr %t121, i64 %t124
  %t128 = load i64, ptr %t127, !alias.scope !20, !noalias !21
  %t129 = alloca i64
  store i64 %t128, ptr %t129
  %t130 = getelementptr %Cols, ptr %s, i32 0, i32 5
  %t131 = getelementptr {ptr, i64}, ptr %t130, i32 0, i32 0
  %t132 = load ptr, ptr %t131, !alias.scope !10, !noalias !11
  %t133 = getelementptr {ptr, i64}, ptr %t130, i32 0, i32 1
  %t134 = load i64, ptr %t133, !alias.scope !10, !noalias !11
  %t135 = load i64, ptr %t77
  %t136 = icmp ult i64 %t135, %t134
  br i1 %t136, label %L137, label %trap
L137:
  %t138 = getelementptr i64, ptr %t132, i64 %t135
  %t139 = load i64, ptr %t138, !alias.scope !22, !noalias !23
  %t140 = alloca i64
  store i64 %t139, ptr %t140
  %t141 = load i64, ptr %t96
  %t142 = load i64, ptr %t107
  %t143 = add i64 %t141, %t142
  %t144 = alloca i64
  store i64 %t143, ptr %t144
  %t145 = load i64, ptr %t144
  %t146 = load i64, ptr %t118
  %t147 = add i64 %t145, %t146
  %t148 = alloca i64
  store i64 %t147, ptr %t148
  %t149 = load i64, ptr %t148
  %t150 = load i64, ptr %t129
  %t151 = add i64 %t149, %t150
  %t152 = alloca i64
  store i64 %t151, ptr %t152
  %t153 = load i64, ptr %t152
  %t154 = load i64, ptr %t140
  %t155 = add i64 %t153, %t154
  %t156 = alloca i64
  store i64 %t155, ptr %t156
  %t157 = load i64, ptr %t156
  %t158 = getelementptr %Cols, ptr %s, i32 0, i32 0
  %t159 = getelementptr {ptr, i64}, ptr %t158, i32 0, i32 0
  %t160 = load ptr, ptr %t159, !alias.scope !10, !noalias !11
  %t161 = getelementptr {ptr, i64}, ptr %t158, i32 0, i32 1
  %t162 = load i64, ptr %t161, !alias.scope !10, !noalias !11
  %t163 = load i64, ptr %t77
  %t164 = icmp ult i64 %t163, %t162
  br i1 %t164, label %L165, label %trap
L165:
  %t166 = getelementptr i64, ptr %t160, i64 %t163
  store i64 %t157, ptr %t166, !alias.scope !12, !noalias !13
  %t167 = getelementptr %Cols, ptr %s, i32 0, i32 1
  %t168 = getelementptr {ptr, i64}, ptr %t167, i32 0, i32 0
  %t169 = load ptr, ptr %t168, !alias.scope !10, !noalias !11
  %t170 = getelementptr {ptr, i64}, ptr %t167, i32 0, i32 1
  %t171 = load i64, ptr %t170, !alias.scope !10, !noalias !11
  %t172 = load i64, ptr %t77
  %t173 = icmp ult i64 %t172, %t171
  br i1 %t173, label %L174, label %trap
L174:
  %t175 = getelementptr i64, ptr %t169, i64 %t172
  %t176 = load i64, ptr %t175, !alias.scope !14, !noalias !15
  %t177 = alloca i64
  store i64 %t176, ptr %t177
  %t178 = getelementptr %Cols, ptr %s, i32 0, i32 6
  %t179 = getelementptr {ptr, i64}, ptr %t178, i32 0, i32 0
  %t180 = load ptr, ptr %t179, !alias.scope !10, !noalias !11
  %t181 = getelementptr {ptr, i64}, ptr %t178, i32 0, i32 1
  %t182 = load i64, ptr %t181, !alias.scope !10, !noalias !11
  %t183 = load i64, ptr %t77
  %t184 = icmp ult i64 %t183, %t182
  br i1 %t184, label %L185, label %trap
L185:
  %t186 = getelementptr i64, ptr %t180, i64 %t183
  %t187 = load i64, ptr %t186, !alias.scope !24, !noalias !25
  %t188 = alloca i64
  store i64 %t187, ptr %t188
  %t189 = getelementptr %Cols, ptr %s, i32 0, i32 7
  %t190 = getelementptr {ptr, i64}, ptr %t189, i32 0, i32 0
  %t191 = load ptr, ptr %t190, !alias.scope !10, !noalias !11
  %t192 = getelementptr {ptr, i64}, ptr %t189, i32 0, i32 1
  %t193 = load i64, ptr %t192, !alias.scope !10, !noalias !11
  %t194 = load i64, ptr %t77
  %t195 = icmp ult i64 %t194, %t193
  br i1 %t195, label %L196, label %trap
L196:
  %t197 = getelementptr i64, ptr %t191, i64 %t194
  %t198 = load i64, ptr %t197, !alias.scope !26, !noalias !27
  %t199 = alloca i64
  store i64 %t198, ptr %t199
  %t200 = load i64, ptr %t177
  %t201 = load i64, ptr %t129
  %t202 = add i64 %t200, %t201
  %t203 = alloca i64
  store i64 %t202, ptr %t203
  %t204 = load i64, ptr %t203
  %t205 = load i64, ptr %t140
  %t206 = add i64 %t204, %t205
  %t207 = alloca i64
  store i64 %t206, ptr %t207
  %t208 = load i64, ptr %t207
  %t209 = load i64, ptr %t188
  %t210 = add i64 %t208, %t209
  %t211 = alloca i64
  store i64 %t210, ptr %t211
  %t212 = load i64, ptr %t211
  %t213 = load i64, ptr %t199
  %t214 = add i64 %t212, %t213
  %t215 = alloca i64
  store i64 %t214, ptr %t215
  %t216 = load i64, ptr %t215
  %t217 = getelementptr %Cols, ptr %s, i32 0, i32 1
  %t218 = getelementptr {ptr, i64}, ptr %t217, i32 0, i32 0
  %t219 = load ptr, ptr %t218, !alias.scope !10, !noalias !11
  %t220 = getelementptr {ptr, i64}, ptr %t217, i32 0, i32 1
  %t221 = load i64, ptr %t220, !alias.scope !10, !noalias !11
  %t222 = load i64, ptr %t77
  %t223 = icmp ult i64 %t222, %t221
  br i1 %t223, label %L224, label %trap
L224:
  %t225 = getelementptr i64, ptr %t219, i64 %t222
  store i64 %t216, ptr %t225, !alias.scope !14, !noalias !15
  %t226 = load i64, ptr %t77
  %t227 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t226, i64 1)
  %t228 = extractvalue {i64, i1} %t227, 0
  %t229 = extractvalue {i64, i1} %t227, 1
  br i1 %t229, label %trap, label %L230
L230:
  store i64 %t228, ptr %t77
  br label %L78
L79:
  ret void
trap:
  call void @llvm.trap()
  unreachable
}

!0 = distinct !{!0, !"kernel"}
!1 = distinct !{!1, !0, !"kernel.s"}
!2 = distinct !{!2, !0, !"kernel.s.a"}
!3 = distinct !{!3, !0, !"kernel.s.b"}
!4 = distinct !{!4, !0, !"kernel.s.c"}
!5 = distinct !{!5, !0, !"kernel.s.d"}
!6 = distinct !{!6, !0, !"kernel.s.e"}
!7 = distinct !{!7, !0, !"kernel.s.f"}
!8 = distinct !{!8, !0, !"kernel.s.g"}
!9 = distinct !{!9, !0, !"kernel.s.h"}
!10 = !{!1}
!11 = !{!2, !3, !4, !5, !6, !7, !8, !9}
!12 = !{!2}
!13 = !{!1, !3, !4, !5, !6, !7, !8, !9}
!14 = !{!3}
!15 = !{!1, !2, !4, !5, !6, !7, !8, !9}
!16 = !{!4}
!17 = !{!1, !2, !3, !5, !6, !7, !8, !9}
!18 = !{!5}
!19 = !{!1, !2, !3, !4, !6, !7, !8, !9}
!20 = !{!6}
!21 = !{!1, !2, !3, !4, !5, !7, !8, !9}
!22 = !{!7}
!23 = !{!1, !2, !3, !4, !5, !6, !8, !9}
!24 = !{!8}
!25 = !{!1, !2, !3, !4, !5, !6, !7, !9}
!26 = !{!9}
!27 = !{!1, !2, !3, !4, !5, !6, !7, !8}
