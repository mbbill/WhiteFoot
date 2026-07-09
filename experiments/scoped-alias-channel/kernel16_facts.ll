%Wide = type { {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64}, {ptr, i64} }
declare {i32, i1} @llvm.sadd.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.ssub.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.smul.with.overflow.i32(i32, i32)
declare void @llvm.trap()
declare i64 @llvm.umin.i64(i64, i64)
declare {i64, i1} @llvm.uadd.with.overflow.i64(i64, i64)

define void @kernel(ptr noalias dereferenceable(256) align 8 %s) nounwind memory(argmem: readwrite, inaccessiblemem: write) {
entry:
  %t1 = getelementptr %Wide, ptr %s, i32 0, i32 0
  %t2 = getelementptr {ptr, i64}, ptr %t1, i32 0, i32 0
  %t3 = load ptr, ptr %t2, !alias.scope !18, !noalias !19
  %t4 = getelementptr {ptr, i64}, ptr %t1, i32 0, i32 1
  %t5 = load i64, ptr %t4, !alias.scope !18, !noalias !19
  %t6 = alloca i64
  store i64 %t5, ptr %t6
  %t7 = getelementptr %Wide, ptr %s, i32 0, i32 1
  %t8 = getelementptr {ptr, i64}, ptr %t7, i32 0, i32 0
  %t9 = load ptr, ptr %t8, !alias.scope !18, !noalias !19
  %t10 = getelementptr {ptr, i64}, ptr %t7, i32 0, i32 1
  %t11 = load i64, ptr %t10, !alias.scope !18, !noalias !19
  %t12 = alloca i64
  store i64 %t11, ptr %t12
  %t13 = getelementptr %Wide, ptr %s, i32 0, i32 2
  %t14 = getelementptr {ptr, i64}, ptr %t13, i32 0, i32 0
  %t15 = load ptr, ptr %t14, !alias.scope !18, !noalias !19
  %t16 = getelementptr {ptr, i64}, ptr %t13, i32 0, i32 1
  %t17 = load i64, ptr %t16, !alias.scope !18, !noalias !19
  %t18 = alloca i64
  store i64 %t17, ptr %t18
  %t19 = getelementptr %Wide, ptr %s, i32 0, i32 3
  %t20 = getelementptr {ptr, i64}, ptr %t19, i32 0, i32 0
  %t21 = load ptr, ptr %t20, !alias.scope !18, !noalias !19
  %t22 = getelementptr {ptr, i64}, ptr %t19, i32 0, i32 1
  %t23 = load i64, ptr %t22, !alias.scope !18, !noalias !19
  %t24 = alloca i64
  store i64 %t23, ptr %t24
  %t25 = getelementptr %Wide, ptr %s, i32 0, i32 4
  %t26 = getelementptr {ptr, i64}, ptr %t25, i32 0, i32 0
  %t27 = load ptr, ptr %t26, !alias.scope !18, !noalias !19
  %t28 = getelementptr {ptr, i64}, ptr %t25, i32 0, i32 1
  %t29 = load i64, ptr %t28, !alias.scope !18, !noalias !19
  %t30 = alloca i64
  store i64 %t29, ptr %t30
  %t31 = getelementptr %Wide, ptr %s, i32 0, i32 5
  %t32 = getelementptr {ptr, i64}, ptr %t31, i32 0, i32 0
  %t33 = load ptr, ptr %t32, !alias.scope !18, !noalias !19
  %t34 = getelementptr {ptr, i64}, ptr %t31, i32 0, i32 1
  %t35 = load i64, ptr %t34, !alias.scope !18, !noalias !19
  %t36 = alloca i64
  store i64 %t35, ptr %t36
  %t37 = getelementptr %Wide, ptr %s, i32 0, i32 6
  %t38 = getelementptr {ptr, i64}, ptr %t37, i32 0, i32 0
  %t39 = load ptr, ptr %t38, !alias.scope !18, !noalias !19
  %t40 = getelementptr {ptr, i64}, ptr %t37, i32 0, i32 1
  %t41 = load i64, ptr %t40, !alias.scope !18, !noalias !19
  %t42 = alloca i64
  store i64 %t41, ptr %t42
  %t43 = getelementptr %Wide, ptr %s, i32 0, i32 7
  %t44 = getelementptr {ptr, i64}, ptr %t43, i32 0, i32 0
  %t45 = load ptr, ptr %t44, !alias.scope !18, !noalias !19
  %t46 = getelementptr {ptr, i64}, ptr %t43, i32 0, i32 1
  %t47 = load i64, ptr %t46, !alias.scope !18, !noalias !19
  %t48 = alloca i64
  store i64 %t47, ptr %t48
  %t49 = getelementptr %Wide, ptr %s, i32 0, i32 8
  %t50 = getelementptr {ptr, i64}, ptr %t49, i32 0, i32 0
  %t51 = load ptr, ptr %t50, !alias.scope !18, !noalias !19
  %t52 = getelementptr {ptr, i64}, ptr %t49, i32 0, i32 1
  %t53 = load i64, ptr %t52, !alias.scope !18, !noalias !19
  %t54 = alloca i64
  store i64 %t53, ptr %t54
  %t55 = getelementptr %Wide, ptr %s, i32 0, i32 9
  %t56 = getelementptr {ptr, i64}, ptr %t55, i32 0, i32 0
  %t57 = load ptr, ptr %t56, !alias.scope !18, !noalias !19
  %t58 = getelementptr {ptr, i64}, ptr %t55, i32 0, i32 1
  %t59 = load i64, ptr %t58, !alias.scope !18, !noalias !19
  %t60 = alloca i64
  store i64 %t59, ptr %t60
  %t61 = getelementptr %Wide, ptr %s, i32 0, i32 10
  %t62 = getelementptr {ptr, i64}, ptr %t61, i32 0, i32 0
  %t63 = load ptr, ptr %t62, !alias.scope !18, !noalias !19
  %t64 = getelementptr {ptr, i64}, ptr %t61, i32 0, i32 1
  %t65 = load i64, ptr %t64, !alias.scope !18, !noalias !19
  %t66 = alloca i64
  store i64 %t65, ptr %t66
  %t67 = getelementptr %Wide, ptr %s, i32 0, i32 11
  %t68 = getelementptr {ptr, i64}, ptr %t67, i32 0, i32 0
  %t69 = load ptr, ptr %t68, !alias.scope !18, !noalias !19
  %t70 = getelementptr {ptr, i64}, ptr %t67, i32 0, i32 1
  %t71 = load i64, ptr %t70, !alias.scope !18, !noalias !19
  %t72 = alloca i64
  store i64 %t71, ptr %t72
  %t73 = getelementptr %Wide, ptr %s, i32 0, i32 12
  %t74 = getelementptr {ptr, i64}, ptr %t73, i32 0, i32 0
  %t75 = load ptr, ptr %t74, !alias.scope !18, !noalias !19
  %t76 = getelementptr {ptr, i64}, ptr %t73, i32 0, i32 1
  %t77 = load i64, ptr %t76, !alias.scope !18, !noalias !19
  %t78 = alloca i64
  store i64 %t77, ptr %t78
  %t79 = getelementptr %Wide, ptr %s, i32 0, i32 13
  %t80 = getelementptr {ptr, i64}, ptr %t79, i32 0, i32 0
  %t81 = load ptr, ptr %t80, !alias.scope !18, !noalias !19
  %t82 = getelementptr {ptr, i64}, ptr %t79, i32 0, i32 1
  %t83 = load i64, ptr %t82, !alias.scope !18, !noalias !19
  %t84 = alloca i64
  store i64 %t83, ptr %t84
  %t85 = getelementptr %Wide, ptr %s, i32 0, i32 14
  %t86 = getelementptr {ptr, i64}, ptr %t85, i32 0, i32 0
  %t87 = load ptr, ptr %t86, !alias.scope !18, !noalias !19
  %t88 = getelementptr {ptr, i64}, ptr %t85, i32 0, i32 1
  %t89 = load i64, ptr %t88, !alias.scope !18, !noalias !19
  %t90 = alloca i64
  store i64 %t89, ptr %t90
  %t91 = getelementptr %Wide, ptr %s, i32 0, i32 15
  %t92 = getelementptr {ptr, i64}, ptr %t91, i32 0, i32 0
  %t93 = load ptr, ptr %t92, !alias.scope !18, !noalias !19
  %t94 = getelementptr {ptr, i64}, ptr %t91, i32 0, i32 1
  %t95 = load i64, ptr %t94, !alias.scope !18, !noalias !19
  %t96 = alloca i64
  store i64 %t95, ptr %t96
  %t97 = load i64, ptr %t6
  %t98 = load i64, ptr %t12
  %t99 = call i64 @llvm.umin.i64(i64 %t97, i64 %t98)
  %t100 = alloca i64
  store i64 %t99, ptr %t100
  %t101 = load i64, ptr %t100
  %t102 = load i64, ptr %t18
  %t103 = call i64 @llvm.umin.i64(i64 %t101, i64 %t102)
  %t104 = alloca i64
  store i64 %t103, ptr %t104
  %t105 = load i64, ptr %t104
  %t106 = load i64, ptr %t24
  %t107 = call i64 @llvm.umin.i64(i64 %t105, i64 %t106)
  %t108 = alloca i64
  store i64 %t107, ptr %t108
  %t109 = load i64, ptr %t108
  %t110 = load i64, ptr %t30
  %t111 = call i64 @llvm.umin.i64(i64 %t109, i64 %t110)
  %t112 = alloca i64
  store i64 %t111, ptr %t112
  %t113 = load i64, ptr %t112
  %t114 = load i64, ptr %t36
  %t115 = call i64 @llvm.umin.i64(i64 %t113, i64 %t114)
  %t116 = alloca i64
  store i64 %t115, ptr %t116
  %t117 = load i64, ptr %t116
  %t118 = load i64, ptr %t42
  %t119 = call i64 @llvm.umin.i64(i64 %t117, i64 %t118)
  %t120 = alloca i64
  store i64 %t119, ptr %t120
  %t121 = load i64, ptr %t120
  %t122 = load i64, ptr %t48
  %t123 = call i64 @llvm.umin.i64(i64 %t121, i64 %t122)
  %t124 = alloca i64
  store i64 %t123, ptr %t124
  %t125 = load i64, ptr %t124
  %t126 = load i64, ptr %t54
  %t127 = call i64 @llvm.umin.i64(i64 %t125, i64 %t126)
  %t128 = alloca i64
  store i64 %t127, ptr %t128
  %t129 = load i64, ptr %t128
  %t130 = load i64, ptr %t60
  %t131 = call i64 @llvm.umin.i64(i64 %t129, i64 %t130)
  %t132 = alloca i64
  store i64 %t131, ptr %t132
  %t133 = load i64, ptr %t132
  %t134 = load i64, ptr %t66
  %t135 = call i64 @llvm.umin.i64(i64 %t133, i64 %t134)
  %t136 = alloca i64
  store i64 %t135, ptr %t136
  %t137 = load i64, ptr %t136
  %t138 = load i64, ptr %t72
  %t139 = call i64 @llvm.umin.i64(i64 %t137, i64 %t138)
  %t140 = alloca i64
  store i64 %t139, ptr %t140
  %t141 = load i64, ptr %t140
  %t142 = load i64, ptr %t78
  %t143 = call i64 @llvm.umin.i64(i64 %t141, i64 %t142)
  %t144 = alloca i64
  store i64 %t143, ptr %t144
  %t145 = load i64, ptr %t144
  %t146 = load i64, ptr %t84
  %t147 = call i64 @llvm.umin.i64(i64 %t145, i64 %t146)
  %t148 = alloca i64
  store i64 %t147, ptr %t148
  %t149 = load i64, ptr %t148
  %t150 = load i64, ptr %t90
  %t151 = call i64 @llvm.umin.i64(i64 %t149, i64 %t150)
  %t152 = alloca i64
  store i64 %t151, ptr %t152
  %t153 = load i64, ptr %t152
  %t154 = load i64, ptr %t96
  %t155 = call i64 @llvm.umin.i64(i64 %t153, i64 %t154)
  %t156 = alloca i64
  store i64 %t155, ptr %t156
  %t157 = load i64, ptr %t156
  %t158 = alloca i64
  store i64 %t157, ptr %t158
  %t159 = alloca i64
  store i64 0, ptr %t159
  br label %L160
L160:
  %t162 = load i64, ptr %t159
  %t163 = load i64, ptr %t158
  %t164 = icmp uge i64 %t162, %t163
  br i1 %t164, label %L166, label %L167
L166:
  br label %L161
L167:
  br label %L165
L165:
  %t168 = getelementptr %Wide, ptr %s, i32 0, i32 0
  %t169 = getelementptr {ptr, i64}, ptr %t168, i32 0, i32 0
  %t170 = load ptr, ptr %t169, !alias.scope !18, !noalias !19
  %t171 = getelementptr {ptr, i64}, ptr %t168, i32 0, i32 1
  %t172 = load i64, ptr %t171, !alias.scope !18, !noalias !19
  %t173 = load i64, ptr %t159
  %t174 = icmp ult i64 %t173, %t172
  br i1 %t174, label %L175, label %trap
L175:
  %t176 = getelementptr i64, ptr %t170, i64 %t173
  %t177 = load i64, ptr %t176, !alias.scope !20, !noalias !21
  %t178 = alloca i64
  store i64 %t177, ptr %t178
  %t179 = getelementptr %Wide, ptr %s, i32 0, i32 4
  %t180 = getelementptr {ptr, i64}, ptr %t179, i32 0, i32 0
  %t181 = load ptr, ptr %t180, !alias.scope !18, !noalias !19
  %t182 = getelementptr {ptr, i64}, ptr %t179, i32 0, i32 1
  %t183 = load i64, ptr %t182, !alias.scope !18, !noalias !19
  %t184 = load i64, ptr %t159
  %t185 = icmp ult i64 %t184, %t183
  br i1 %t185, label %L186, label %trap
L186:
  %t187 = getelementptr i64, ptr %t181, i64 %t184
  %t188 = load i64, ptr %t187, !alias.scope !28, !noalias !29
  %t189 = alloca i64
  store i64 %t188, ptr %t189
  %t190 = getelementptr %Wide, ptr %s, i32 0, i32 5
  %t191 = getelementptr {ptr, i64}, ptr %t190, i32 0, i32 0
  %t192 = load ptr, ptr %t191, !alias.scope !18, !noalias !19
  %t193 = getelementptr {ptr, i64}, ptr %t190, i32 0, i32 1
  %t194 = load i64, ptr %t193, !alias.scope !18, !noalias !19
  %t195 = load i64, ptr %t159
  %t196 = icmp ult i64 %t195, %t194
  br i1 %t196, label %L197, label %trap
L197:
  %t198 = getelementptr i64, ptr %t192, i64 %t195
  %t199 = load i64, ptr %t198, !alias.scope !30, !noalias !31
  %t200 = alloca i64
  store i64 %t199, ptr %t200
  %t201 = getelementptr %Wide, ptr %s, i32 0, i32 6
  %t202 = getelementptr {ptr, i64}, ptr %t201, i32 0, i32 0
  %t203 = load ptr, ptr %t202, !alias.scope !18, !noalias !19
  %t204 = getelementptr {ptr, i64}, ptr %t201, i32 0, i32 1
  %t205 = load i64, ptr %t204, !alias.scope !18, !noalias !19
  %t206 = load i64, ptr %t159
  %t207 = icmp ult i64 %t206, %t205
  br i1 %t207, label %L208, label %trap
L208:
  %t209 = getelementptr i64, ptr %t203, i64 %t206
  %t210 = load i64, ptr %t209, !alias.scope !32, !noalias !33
  %t211 = alloca i64
  store i64 %t210, ptr %t211
  %t212 = load i64, ptr %t178
  %t213 = load i64, ptr %t189
  %t214 = add i64 %t212, %t213
  %t215 = alloca i64
  store i64 %t214, ptr %t215
  %t216 = load i64, ptr %t215
  %t217 = load i64, ptr %t200
  %t218 = add i64 %t216, %t217
  %t219 = alloca i64
  store i64 %t218, ptr %t219
  %t220 = load i64, ptr %t219
  %t221 = load i64, ptr %t211
  %t222 = add i64 %t220, %t221
  %t223 = alloca i64
  store i64 %t222, ptr %t223
  %t224 = load i64, ptr %t223
  %t225 = getelementptr %Wide, ptr %s, i32 0, i32 0
  %t226 = getelementptr {ptr, i64}, ptr %t225, i32 0, i32 0
  %t227 = load ptr, ptr %t226, !alias.scope !18, !noalias !19
  %t228 = getelementptr {ptr, i64}, ptr %t225, i32 0, i32 1
  %t229 = load i64, ptr %t228, !alias.scope !18, !noalias !19
  %t230 = load i64, ptr %t159
  %t231 = icmp ult i64 %t230, %t229
  br i1 %t231, label %L232, label %trap
L232:
  %t233 = getelementptr i64, ptr %t227, i64 %t230
  store i64 %t224, ptr %t233, !alias.scope !20, !noalias !21
  %t234 = getelementptr %Wide, ptr %s, i32 0, i32 1
  %t235 = getelementptr {ptr, i64}, ptr %t234, i32 0, i32 0
  %t236 = load ptr, ptr %t235, !alias.scope !18, !noalias !19
  %t237 = getelementptr {ptr, i64}, ptr %t234, i32 0, i32 1
  %t238 = load i64, ptr %t237, !alias.scope !18, !noalias !19
  %t239 = load i64, ptr %t159
  %t240 = icmp ult i64 %t239, %t238
  br i1 %t240, label %L241, label %trap
L241:
  %t242 = getelementptr i64, ptr %t236, i64 %t239
  %t243 = load i64, ptr %t242, !alias.scope !22, !noalias !23
  %t244 = alloca i64
  store i64 %t243, ptr %t244
  %t245 = getelementptr %Wide, ptr %s, i32 0, i32 7
  %t246 = getelementptr {ptr, i64}, ptr %t245, i32 0, i32 0
  %t247 = load ptr, ptr %t246, !alias.scope !18, !noalias !19
  %t248 = getelementptr {ptr, i64}, ptr %t245, i32 0, i32 1
  %t249 = load i64, ptr %t248, !alias.scope !18, !noalias !19
  %t250 = load i64, ptr %t159
  %t251 = icmp ult i64 %t250, %t249
  br i1 %t251, label %L252, label %trap
L252:
  %t253 = getelementptr i64, ptr %t247, i64 %t250
  %t254 = load i64, ptr %t253, !alias.scope !34, !noalias !35
  %t255 = alloca i64
  store i64 %t254, ptr %t255
  %t256 = getelementptr %Wide, ptr %s, i32 0, i32 8
  %t257 = getelementptr {ptr, i64}, ptr %t256, i32 0, i32 0
  %t258 = load ptr, ptr %t257, !alias.scope !18, !noalias !19
  %t259 = getelementptr {ptr, i64}, ptr %t256, i32 0, i32 1
  %t260 = load i64, ptr %t259, !alias.scope !18, !noalias !19
  %t261 = load i64, ptr %t159
  %t262 = icmp ult i64 %t261, %t260
  br i1 %t262, label %L263, label %trap
L263:
  %t264 = getelementptr i64, ptr %t258, i64 %t261
  %t265 = load i64, ptr %t264, !alias.scope !36, !noalias !37
  %t266 = alloca i64
  store i64 %t265, ptr %t266
  %t267 = getelementptr %Wide, ptr %s, i32 0, i32 9
  %t268 = getelementptr {ptr, i64}, ptr %t267, i32 0, i32 0
  %t269 = load ptr, ptr %t268, !alias.scope !18, !noalias !19
  %t270 = getelementptr {ptr, i64}, ptr %t267, i32 0, i32 1
  %t271 = load i64, ptr %t270, !alias.scope !18, !noalias !19
  %t272 = load i64, ptr %t159
  %t273 = icmp ult i64 %t272, %t271
  br i1 %t273, label %L274, label %trap
L274:
  %t275 = getelementptr i64, ptr %t269, i64 %t272
  %t276 = load i64, ptr %t275, !alias.scope !38, !noalias !39
  %t277 = alloca i64
  store i64 %t276, ptr %t277
  %t278 = load i64, ptr %t244
  %t279 = load i64, ptr %t255
  %t280 = add i64 %t278, %t279
  %t281 = alloca i64
  store i64 %t280, ptr %t281
  %t282 = load i64, ptr %t281
  %t283 = load i64, ptr %t266
  %t284 = add i64 %t282, %t283
  %t285 = alloca i64
  store i64 %t284, ptr %t285
  %t286 = load i64, ptr %t285
  %t287 = load i64, ptr %t277
  %t288 = add i64 %t286, %t287
  %t289 = alloca i64
  store i64 %t288, ptr %t289
  %t290 = load i64, ptr %t289
  %t291 = getelementptr %Wide, ptr %s, i32 0, i32 1
  %t292 = getelementptr {ptr, i64}, ptr %t291, i32 0, i32 0
  %t293 = load ptr, ptr %t292, !alias.scope !18, !noalias !19
  %t294 = getelementptr {ptr, i64}, ptr %t291, i32 0, i32 1
  %t295 = load i64, ptr %t294, !alias.scope !18, !noalias !19
  %t296 = load i64, ptr %t159
  %t297 = icmp ult i64 %t296, %t295
  br i1 %t297, label %L298, label %trap
L298:
  %t299 = getelementptr i64, ptr %t293, i64 %t296
  store i64 %t290, ptr %t299, !alias.scope !22, !noalias !23
  %t300 = getelementptr %Wide, ptr %s, i32 0, i32 2
  %t301 = getelementptr {ptr, i64}, ptr %t300, i32 0, i32 0
  %t302 = load ptr, ptr %t301, !alias.scope !18, !noalias !19
  %t303 = getelementptr {ptr, i64}, ptr %t300, i32 0, i32 1
  %t304 = load i64, ptr %t303, !alias.scope !18, !noalias !19
  %t305 = load i64, ptr %t159
  %t306 = icmp ult i64 %t305, %t304
  br i1 %t306, label %L307, label %trap
L307:
  %t308 = getelementptr i64, ptr %t302, i64 %t305
  %t309 = load i64, ptr %t308, !alias.scope !24, !noalias !25
  %t310 = alloca i64
  store i64 %t309, ptr %t310
  %t311 = getelementptr %Wide, ptr %s, i32 0, i32 10
  %t312 = getelementptr {ptr, i64}, ptr %t311, i32 0, i32 0
  %t313 = load ptr, ptr %t312, !alias.scope !18, !noalias !19
  %t314 = getelementptr {ptr, i64}, ptr %t311, i32 0, i32 1
  %t315 = load i64, ptr %t314, !alias.scope !18, !noalias !19
  %t316 = load i64, ptr %t159
  %t317 = icmp ult i64 %t316, %t315
  br i1 %t317, label %L318, label %trap
L318:
  %t319 = getelementptr i64, ptr %t313, i64 %t316
  %t320 = load i64, ptr %t319, !alias.scope !40, !noalias !41
  %t321 = alloca i64
  store i64 %t320, ptr %t321
  %t322 = getelementptr %Wide, ptr %s, i32 0, i32 11
  %t323 = getelementptr {ptr, i64}, ptr %t322, i32 0, i32 0
  %t324 = load ptr, ptr %t323, !alias.scope !18, !noalias !19
  %t325 = getelementptr {ptr, i64}, ptr %t322, i32 0, i32 1
  %t326 = load i64, ptr %t325, !alias.scope !18, !noalias !19
  %t327 = load i64, ptr %t159
  %t328 = icmp ult i64 %t327, %t326
  br i1 %t328, label %L329, label %trap
L329:
  %t330 = getelementptr i64, ptr %t324, i64 %t327
  %t331 = load i64, ptr %t330, !alias.scope !42, !noalias !43
  %t332 = alloca i64
  store i64 %t331, ptr %t332
  %t333 = getelementptr %Wide, ptr %s, i32 0, i32 12
  %t334 = getelementptr {ptr, i64}, ptr %t333, i32 0, i32 0
  %t335 = load ptr, ptr %t334, !alias.scope !18, !noalias !19
  %t336 = getelementptr {ptr, i64}, ptr %t333, i32 0, i32 1
  %t337 = load i64, ptr %t336, !alias.scope !18, !noalias !19
  %t338 = load i64, ptr %t159
  %t339 = icmp ult i64 %t338, %t337
  br i1 %t339, label %L340, label %trap
L340:
  %t341 = getelementptr i64, ptr %t335, i64 %t338
  %t342 = load i64, ptr %t341, !alias.scope !44, !noalias !45
  %t343 = alloca i64
  store i64 %t342, ptr %t343
  %t344 = load i64, ptr %t310
  %t345 = load i64, ptr %t321
  %t346 = add i64 %t344, %t345
  %t347 = alloca i64
  store i64 %t346, ptr %t347
  %t348 = load i64, ptr %t347
  %t349 = load i64, ptr %t332
  %t350 = add i64 %t348, %t349
  %t351 = alloca i64
  store i64 %t350, ptr %t351
  %t352 = load i64, ptr %t351
  %t353 = load i64, ptr %t343
  %t354 = add i64 %t352, %t353
  %t355 = alloca i64
  store i64 %t354, ptr %t355
  %t356 = load i64, ptr %t355
  %t357 = getelementptr %Wide, ptr %s, i32 0, i32 2
  %t358 = getelementptr {ptr, i64}, ptr %t357, i32 0, i32 0
  %t359 = load ptr, ptr %t358, !alias.scope !18, !noalias !19
  %t360 = getelementptr {ptr, i64}, ptr %t357, i32 0, i32 1
  %t361 = load i64, ptr %t360, !alias.scope !18, !noalias !19
  %t362 = load i64, ptr %t159
  %t363 = icmp ult i64 %t362, %t361
  br i1 %t363, label %L364, label %trap
L364:
  %t365 = getelementptr i64, ptr %t359, i64 %t362
  store i64 %t356, ptr %t365, !alias.scope !24, !noalias !25
  %t366 = getelementptr %Wide, ptr %s, i32 0, i32 3
  %t367 = getelementptr {ptr, i64}, ptr %t366, i32 0, i32 0
  %t368 = load ptr, ptr %t367, !alias.scope !18, !noalias !19
  %t369 = getelementptr {ptr, i64}, ptr %t366, i32 0, i32 1
  %t370 = load i64, ptr %t369, !alias.scope !18, !noalias !19
  %t371 = load i64, ptr %t159
  %t372 = icmp ult i64 %t371, %t370
  br i1 %t372, label %L373, label %trap
L373:
  %t374 = getelementptr i64, ptr %t368, i64 %t371
  %t375 = load i64, ptr %t374, !alias.scope !26, !noalias !27
  %t376 = alloca i64
  store i64 %t375, ptr %t376
  %t377 = getelementptr %Wide, ptr %s, i32 0, i32 13
  %t378 = getelementptr {ptr, i64}, ptr %t377, i32 0, i32 0
  %t379 = load ptr, ptr %t378, !alias.scope !18, !noalias !19
  %t380 = getelementptr {ptr, i64}, ptr %t377, i32 0, i32 1
  %t381 = load i64, ptr %t380, !alias.scope !18, !noalias !19
  %t382 = load i64, ptr %t159
  %t383 = icmp ult i64 %t382, %t381
  br i1 %t383, label %L384, label %trap
L384:
  %t385 = getelementptr i64, ptr %t379, i64 %t382
  %t386 = load i64, ptr %t385, !alias.scope !46, !noalias !47
  %t387 = alloca i64
  store i64 %t386, ptr %t387
  %t388 = getelementptr %Wide, ptr %s, i32 0, i32 14
  %t389 = getelementptr {ptr, i64}, ptr %t388, i32 0, i32 0
  %t390 = load ptr, ptr %t389, !alias.scope !18, !noalias !19
  %t391 = getelementptr {ptr, i64}, ptr %t388, i32 0, i32 1
  %t392 = load i64, ptr %t391, !alias.scope !18, !noalias !19
  %t393 = load i64, ptr %t159
  %t394 = icmp ult i64 %t393, %t392
  br i1 %t394, label %L395, label %trap
L395:
  %t396 = getelementptr i64, ptr %t390, i64 %t393
  %t397 = load i64, ptr %t396, !alias.scope !48, !noalias !49
  %t398 = alloca i64
  store i64 %t397, ptr %t398
  %t399 = getelementptr %Wide, ptr %s, i32 0, i32 15
  %t400 = getelementptr {ptr, i64}, ptr %t399, i32 0, i32 0
  %t401 = load ptr, ptr %t400, !alias.scope !18, !noalias !19
  %t402 = getelementptr {ptr, i64}, ptr %t399, i32 0, i32 1
  %t403 = load i64, ptr %t402, !alias.scope !18, !noalias !19
  %t404 = load i64, ptr %t159
  %t405 = icmp ult i64 %t404, %t403
  br i1 %t405, label %L406, label %trap
L406:
  %t407 = getelementptr i64, ptr %t401, i64 %t404
  %t408 = load i64, ptr %t407, !alias.scope !50, !noalias !51
  %t409 = alloca i64
  store i64 %t408, ptr %t409
  %t410 = load i64, ptr %t376
  %t411 = load i64, ptr %t387
  %t412 = add i64 %t410, %t411
  %t413 = alloca i64
  store i64 %t412, ptr %t413
  %t414 = load i64, ptr %t413
  %t415 = load i64, ptr %t398
  %t416 = add i64 %t414, %t415
  %t417 = alloca i64
  store i64 %t416, ptr %t417
  %t418 = load i64, ptr %t417
  %t419 = load i64, ptr %t409
  %t420 = add i64 %t418, %t419
  %t421 = alloca i64
  store i64 %t420, ptr %t421
  %t422 = load i64, ptr %t421
  %t423 = getelementptr %Wide, ptr %s, i32 0, i32 3
  %t424 = getelementptr {ptr, i64}, ptr %t423, i32 0, i32 0
  %t425 = load ptr, ptr %t424, !alias.scope !18, !noalias !19
  %t426 = getelementptr {ptr, i64}, ptr %t423, i32 0, i32 1
  %t427 = load i64, ptr %t426, !alias.scope !18, !noalias !19
  %t428 = load i64, ptr %t159
  %t429 = icmp ult i64 %t428, %t427
  br i1 %t429, label %L430, label %trap
L430:
  %t431 = getelementptr i64, ptr %t425, i64 %t428
  store i64 %t422, ptr %t431, !alias.scope !26, !noalias !27
  %t432 = load i64, ptr %t159
  %t433 = call {i64, i1} @llvm.uadd.with.overflow.i64(i64 %t432, i64 1)
  %t434 = extractvalue {i64, i1} %t433, 0
  %t435 = extractvalue {i64, i1} %t433, 1
  br i1 %t435, label %trap, label %L436
L436:
  store i64 %t434, ptr %t159
  br label %L160
L161:
  ret void
trap:
  call void @llvm.trap()
  unreachable
}

!0 = distinct !{!0, !"kernel"}
!1 = distinct !{!1, !0, !"kernel.s"}
!2 = distinct !{!2, !0, !"kernel.s.c0"}
!3 = distinct !{!3, !0, !"kernel.s.c1"}
!4 = distinct !{!4, !0, !"kernel.s.c2"}
!5 = distinct !{!5, !0, !"kernel.s.c3"}
!6 = distinct !{!6, !0, !"kernel.s.c4"}
!7 = distinct !{!7, !0, !"kernel.s.c5"}
!8 = distinct !{!8, !0, !"kernel.s.c6"}
!9 = distinct !{!9, !0, !"kernel.s.c7"}
!10 = distinct !{!10, !0, !"kernel.s.c8"}
!11 = distinct !{!11, !0, !"kernel.s.c9"}
!12 = distinct !{!12, !0, !"kernel.s.c10"}
!13 = distinct !{!13, !0, !"kernel.s.c11"}
!14 = distinct !{!14, !0, !"kernel.s.c12"}
!15 = distinct !{!15, !0, !"kernel.s.c13"}
!16 = distinct !{!16, !0, !"kernel.s.c14"}
!17 = distinct !{!17, !0, !"kernel.s.c15"}
!18 = !{!1}
!19 = !{!2, !3, !4, !5, !6, !7, !8, !9, !10, !11, !12, !13, !14, !15, !16, !17}
!20 = !{!2}
!21 = !{!1, !3, !4, !5, !6, !7, !8, !9, !10, !11, !12, !13, !14, !15, !16, !17}
!22 = !{!3}
!23 = !{!1, !2, !4, !5, !6, !7, !8, !9, !10, !11, !12, !13, !14, !15, !16, !17}
!24 = !{!4}
!25 = !{!1, !2, !3, !5, !6, !7, !8, !9, !10, !11, !12, !13, !14, !15, !16, !17}
!26 = !{!5}
!27 = !{!1, !2, !3, !4, !6, !7, !8, !9, !10, !11, !12, !13, !14, !15, !16, !17}
!28 = !{!6}
!29 = !{!1, !2, !3, !4, !5, !7, !8, !9, !10, !11, !12, !13, !14, !15, !16, !17}
!30 = !{!7}
!31 = !{!1, !2, !3, !4, !5, !6, !8, !9, !10, !11, !12, !13, !14, !15, !16, !17}
!32 = !{!8}
!33 = !{!1, !2, !3, !4, !5, !6, !7, !9, !10, !11, !12, !13, !14, !15, !16, !17}
!34 = !{!9}
!35 = !{!1, !2, !3, !4, !5, !6, !7, !8, !10, !11, !12, !13, !14, !15, !16, !17}
!36 = !{!10}
!37 = !{!1, !2, !3, !4, !5, !6, !7, !8, !9, !11, !12, !13, !14, !15, !16, !17}
!38 = !{!11}
!39 = !{!1, !2, !3, !4, !5, !6, !7, !8, !9, !10, !12, !13, !14, !15, !16, !17}
!40 = !{!12}
!41 = !{!1, !2, !3, !4, !5, !6, !7, !8, !9, !10, !11, !13, !14, !15, !16, !17}
!42 = !{!13}
!43 = !{!1, !2, !3, !4, !5, !6, !7, !8, !9, !10, !11, !12, !14, !15, !16, !17}
!44 = !{!14}
!45 = !{!1, !2, !3, !4, !5, !6, !7, !8, !9, !10, !11, !12, !13, !15, !16, !17}
!46 = !{!15}
!47 = !{!1, !2, !3, !4, !5, !6, !7, !8, !9, !10, !11, !12, !13, !14, !16, !17}
!48 = !{!16}
!49 = !{!1, !2, !3, !4, !5, !6, !7, !8, !9, !10, !11, !12, !13, !14, !15, !17}
!50 = !{!17}
!51 = !{!1, !2, !3, !4, !5, !6, !7, !8, !9, !10, !11, !12, !13, !14, !15, !16}
