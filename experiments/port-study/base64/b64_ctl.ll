declare {i32, i1} @llvm.sadd.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.ssub.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.smul.with.overflow.i32(i32, i32)
declare void @llvm.trap()

@__const_b64 = private unnamed_addr constant [64 x i8] [i8 65, i8 66, i8 67, i8 68, i8 69, i8 70, i8 71, i8 72, i8 73, i8 74, i8 75, i8 76, i8 77, i8 78, i8 79, i8 80, i8 81, i8 82, i8 83, i8 84, i8 85, i8 86, i8 87, i8 88, i8 89, i8 90, i8 97, i8 98, i8 99, i8 100, i8 101, i8 102, i8 103, i8 104, i8 105, i8 106, i8 107, i8 108, i8 109, i8 110, i8 111, i8 112, i8 113, i8 114, i8 115, i8 116, i8 117, i8 118, i8 119, i8 120, i8 121, i8 122, i8 48, i8 49, i8 50, i8 51, i8 52, i8 53, i8 54, i8 55, i8 56, i8 57, i8 43, i8 47]

define i64 @encode({ptr, i64} %out, {ptr, i64} %src) {
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
  %t8 = and i32 2, 63
  %t9 = zext i32 %t8 to i64
  %t10 = lshr i64 %t7, %t9
  %t11 = alloca i64
  store i64 %t10, ptr %t11
  %t12 = load i64, ptr %t11
  %t13 = mul i64 %t12, 3
  %t14 = alloca i64
  store i64 %t13, ptr %t14
  %t15 = load i64, ptr %t6
  %t16 = load i64, ptr %t14
  %t17 = icmp ule i64 %t15, %t16
  %t19 = alloca i1
  store volatile i1 %t17, ptr %t19
  %t20 = load volatile i1, ptr %t19
  br i1 %t20, label %L18, label %trap
L18:
  %t21 = alloca i64
  store i64 %t4, ptr %t21
  %t22 = alloca i64
  store i64 0, ptr %t22
  %t23 = alloca i64
  store i64 0, ptr %t23
  br label %L24
L24:
  %t26 = load i64, ptr %t21
  %t27 = load i64, ptr %t22
  %t28 = sub i64 %t26, %t27
  %t29 = alloca i64
  store i64 %t28, ptr %t29
  %t30 = load i64, ptr %t29
  %t31 = icmp ult i64 %t30, 3
  br i1 %t31, label %L33, label %L34
L33:
  br label %L25
L34:
  br label %L32
L32:
  %t35 = load i64, ptr %t22
  %t36 = add i64 %t35, 1
  %t37 = alloca i64
  store i64 %t36, ptr %t37
  %t38 = load i64, ptr %t22
  %t39 = add i64 %t38, 2
  %t40 = alloca i64
  store i64 %t39, ptr %t40
  %t41 = load i64, ptr %t22
  %t42 = icmp ult i64 %t41, %t4
  br i1 %t42, label %L43, label %trap
L43:
  %t44 = getelementptr i8, ptr %t3, i64 %t41
  %t45 = load i8, ptr %t44
  %t46 = alloca i8
  store i8 %t45, ptr %t46
  %t47 = load i64, ptr %t37
  %t48 = icmp ult i64 %t47, %t4
  br i1 %t48, label %L49, label %trap
L49:
  %t50 = getelementptr i8, ptr %t3, i64 %t47
  %t51 = load i8, ptr %t50
  %t52 = alloca i8
  store i8 %t51, ptr %t52
  %t53 = load i64, ptr %t40
  %t54 = icmp ult i64 %t53, %t4
  br i1 %t54, label %L55, label %trap
L55:
  %t56 = getelementptr i8, ptr %t3, i64 %t53
  %t57 = load i8, ptr %t56
  %t58 = alloca i8
  store i8 %t57, ptr %t58
  %t59 = load i8, ptr %t46
  %t60 = zext i8 %t59 to i32
  %t61 = alloca i32
  store i32 %t60, ptr %t61
  %t62 = load i8, ptr %t52
  %t63 = zext i8 %t62 to i32
  %t64 = alloca i32
  store i32 %t63, ptr %t64
  %t65 = load i8, ptr %t58
  %t66 = zext i8 %t65 to i32
  %t67 = alloca i32
  store i32 %t66, ptr %t67
  %t68 = load i32, ptr %t61
  %t69 = and i32 16, 31
  %t70 = shl i32 %t68, %t69
  %t71 = alloca i32
  store i32 %t70, ptr %t71
  %t72 = load i32, ptr %t64
  %t73 = and i32 8, 31
  %t74 = shl i32 %t72, %t73
  %t75 = alloca i32
  store i32 %t74, ptr %t75
  %t76 = load i32, ptr %t71
  %t77 = load i32, ptr %t75
  %t78 = or i32 %t76, %t77
  %t79 = alloca i32
  store i32 %t78, ptr %t79
  %t80 = load i32, ptr %t79
  %t81 = load i32, ptr %t67
  %t82 = or i32 %t80, %t81
  %t83 = alloca i32
  store i32 %t82, ptr %t83
  %t84 = load i32, ptr %t83
  %t85 = and i32 18, 31
  %t86 = lshr i32 %t84, %t85
  %t87 = alloca i32
  store i32 %t86, ptr %t87
  %t88 = load i32, ptr %t87
  %t89 = and i32 %t88, 63
  %t90 = alloca i32
  store i32 %t89, ptr %t90
  %t91 = load i32, ptr %t90
  %t92 = zext i32 %t91 to i64
  %t93 = alloca i64
  store i64 %t92, ptr %t93
  %t94 = load i32, ptr %t83
  %t95 = and i32 12, 31
  %t96 = lshr i32 %t94, %t95
  %t97 = alloca i32
  store i32 %t96, ptr %t97
  %t98 = load i32, ptr %t97
  %t99 = and i32 %t98, 63
  %t100 = alloca i32
  store i32 %t99, ptr %t100
  %t101 = load i32, ptr %t100
  %t102 = zext i32 %t101 to i64
  %t103 = alloca i64
  store i64 %t102, ptr %t103
  %t104 = load i32, ptr %t83
  %t105 = and i32 6, 31
  %t106 = lshr i32 %t104, %t105
  %t107 = alloca i32
  store i32 %t106, ptr %t107
  %t108 = load i32, ptr %t107
  %t109 = and i32 %t108, 63
  %t110 = alloca i32
  store i32 %t109, ptr %t110
  %t111 = load i32, ptr %t110
  %t112 = zext i32 %t111 to i64
  %t113 = alloca i64
  store i64 %t112, ptr %t113
  %t114 = load i32, ptr %t83
  %t115 = and i32 %t114, 63
  %t116 = alloca i32
  store i32 %t115, ptr %t116
  %t117 = load i32, ptr %t116
  %t118 = zext i32 %t117 to i64
  %t119 = alloca i64
  store i64 %t118, ptr %t119
  %t120 = load i64, ptr %t93
  %t121 = icmp ult i64 %t120, 64
  br i1 %t121, label %L122, label %trap
L122:
  %t123 = getelementptr [64 x i8], ptr @__const_b64, i64 0, i64 %t120
  %t124 = load i8, ptr %t123
  %t125 = alloca i8
  store i8 %t124, ptr %t125
  %t126 = load i64, ptr %t103
  %t127 = icmp ult i64 %t126, 64
  br i1 %t127, label %L128, label %trap
L128:
  %t129 = getelementptr [64 x i8], ptr @__const_b64, i64 0, i64 %t126
  %t130 = load i8, ptr %t129
  %t131 = alloca i8
  store i8 %t130, ptr %t131
  %t132 = load i64, ptr %t113
  %t133 = icmp ult i64 %t132, 64
  br i1 %t133, label %L134, label %trap
L134:
  %t135 = getelementptr [64 x i8], ptr @__const_b64, i64 0, i64 %t132
  %t136 = load i8, ptr %t135
  %t137 = alloca i8
  store i8 %t136, ptr %t137
  %t138 = load i64, ptr %t119
  %t139 = icmp ult i64 %t138, 64
  br i1 %t139, label %L140, label %trap
L140:
  %t141 = getelementptr [64 x i8], ptr @__const_b64, i64 0, i64 %t138
  %t142 = load i8, ptr %t141
  %t143 = alloca i8
  store i8 %t142, ptr %t143
  %t144 = load i64, ptr %t23
  %t145 = add i64 %t144, 1
  %t146 = alloca i64
  store i64 %t145, ptr %t146
  %t147 = load i64, ptr %t23
  %t148 = add i64 %t147, 2
  %t149 = alloca i64
  store i64 %t148, ptr %t149
  %t150 = load i64, ptr %t23
  %t151 = add i64 %t150, 3
  %t152 = alloca i64
  store i64 %t151, ptr %t152
  %t153 = load i8, ptr %t125
  %t154 = load i64, ptr %t23
  %t155 = icmp ult i64 %t154, %t2
  br i1 %t155, label %L156, label %trap
L156:
  %t157 = getelementptr i8, ptr %t1, i64 %t154
  store i8 %t153, ptr %t157
  %t158 = load i8, ptr %t131
  %t159 = load i64, ptr %t146
  %t160 = icmp ult i64 %t159, %t2
  br i1 %t160, label %L161, label %trap
L161:
  %t162 = getelementptr i8, ptr %t1, i64 %t159
  store i8 %t158, ptr %t162
  %t163 = load i8, ptr %t137
  %t164 = load i64, ptr %t149
  %t165 = icmp ult i64 %t164, %t2
  br i1 %t165, label %L166, label %trap
L166:
  %t167 = getelementptr i8, ptr %t1, i64 %t164
  store i8 %t163, ptr %t167
  %t168 = load i8, ptr %t143
  %t169 = load i64, ptr %t152
  %t170 = icmp ult i64 %t169, %t2
  br i1 %t170, label %L171, label %trap
L171:
  %t172 = getelementptr i8, ptr %t1, i64 %t169
  store i8 %t168, ptr %t172
  %t173 = load i64, ptr %t22
  %t174 = add i64 %t173, 3
  store i64 %t174, ptr %t22
  %t175 = load i64, ptr %t23
  %t176 = add i64 %t175, 4
  store i64 %t176, ptr %t23
  br label %L24
L25:
  %t177 = load i64, ptr %t21
  %t178 = load i64, ptr %t22
  %t179 = sub i64 %t177, %t178
  %t180 = alloca i64
  store i64 %t179, ptr %t180
  %t181 = load i64, ptr %t180
  %t182 = icmp eq i64 %t181, 1
  br i1 %t182, label %L184, label %L185
L184:
  %t186 = load i64, ptr %t22
  %t187 = icmp ult i64 %t186, %t4
  br i1 %t187, label %L188, label %trap
L188:
  %t189 = getelementptr i8, ptr %t3, i64 %t186
  %t190 = load i8, ptr %t189
  %t191 = alloca i8
  store i8 %t190, ptr %t191
  %t192 = load i8, ptr %t191
  %t193 = zext i8 %t192 to i32
  %t194 = alloca i32
  store i32 %t193, ptr %t194
  %t195 = load i32, ptr %t194
  %t196 = and i32 2, 31
  %t197 = lshr i32 %t195, %t196
  %t198 = alloca i32
  store i32 %t197, ptr %t198
  %t199 = load i32, ptr %t198
  %t200 = and i32 %t199, 63
  %t201 = alloca i32
  store i32 %t200, ptr %t201
  %t202 = load i32, ptr %t201
  %t203 = zext i32 %t202 to i64
  %t204 = alloca i64
  store i64 %t203, ptr %t204
  %t205 = load i32, ptr %t194
  %t206 = and i32 4, 31
  %t207 = shl i32 %t205, %t206
  %t208 = alloca i32
  store i32 %t207, ptr %t208
  %t209 = load i32, ptr %t208
  %t210 = and i32 %t209, 63
  %t211 = alloca i32
  store i32 %t210, ptr %t211
  %t212 = load i32, ptr %t211
  %t213 = zext i32 %t212 to i64
  %t214 = alloca i64
  store i64 %t213, ptr %t214
  %t215 = load i64, ptr %t204
  %t216 = icmp ult i64 %t215, 64
  br i1 %t216, label %L217, label %trap
L217:
  %t218 = getelementptr [64 x i8], ptr @__const_b64, i64 0, i64 %t215
  %t219 = load i8, ptr %t218
  %t220 = alloca i8
  store i8 %t219, ptr %t220
  %t221 = load i64, ptr %t214
  %t222 = icmp ult i64 %t221, 64
  br i1 %t222, label %L223, label %trap
L223:
  %t224 = getelementptr [64 x i8], ptr @__const_b64, i64 0, i64 %t221
  %t225 = load i8, ptr %t224
  %t226 = alloca i8
  store i8 %t225, ptr %t226
  %t227 = load i64, ptr %t23
  %t228 = add i64 %t227, 1
  %t229 = alloca i64
  store i64 %t228, ptr %t229
  %t230 = load i64, ptr %t23
  %t231 = add i64 %t230, 2
  %t232 = alloca i64
  store i64 %t231, ptr %t232
  %t233 = load i64, ptr %t23
  %t234 = add i64 %t233, 3
  %t235 = alloca i64
  store i64 %t234, ptr %t235
  %t236 = load i8, ptr %t220
  %t237 = load i64, ptr %t23
  %t238 = icmp ult i64 %t237, %t2
  br i1 %t238, label %L239, label %trap
L239:
  %t240 = getelementptr i8, ptr %t1, i64 %t237
  store i8 %t236, ptr %t240
  %t241 = load i8, ptr %t226
  %t242 = load i64, ptr %t229
  %t243 = icmp ult i64 %t242, %t2
  br i1 %t243, label %L244, label %trap
L244:
  %t245 = getelementptr i8, ptr %t1, i64 %t242
  store i8 %t241, ptr %t245
  %t246 = load i64, ptr %t232
  %t247 = icmp ult i64 %t246, %t2
  br i1 %t247, label %L248, label %trap
L248:
  %t249 = getelementptr i8, ptr %t1, i64 %t246
  store i8 61, ptr %t249
  %t250 = load i64, ptr %t235
  %t251 = icmp ult i64 %t250, %t2
  br i1 %t251, label %L252, label %trap
L252:
  %t253 = getelementptr i8, ptr %t1, i64 %t250
  store i8 61, ptr %t253
  %t254 = load i64, ptr %t23
  %t255 = add i64 %t254, 4
  store i64 %t255, ptr %t23
  br label %L183
L185:
  br label %L183
L183:
  %t256 = load i64, ptr %t180
  %t257 = icmp eq i64 %t256, 2
  br i1 %t257, label %L259, label %L260
L259:
  %t261 = load i64, ptr %t22
  %t262 = add i64 %t261, 1
  %t263 = alloca i64
  store i64 %t262, ptr %t263
  %t264 = load i64, ptr %t22
  %t265 = icmp ult i64 %t264, %t4
  br i1 %t265, label %L266, label %trap
L266:
  %t267 = getelementptr i8, ptr %t3, i64 %t264
  %t268 = load i8, ptr %t267
  %t269 = alloca i8
  store i8 %t268, ptr %t269
  %t270 = load i64, ptr %t263
  %t271 = icmp ult i64 %t270, %t4
  br i1 %t271, label %L272, label %trap
L272:
  %t273 = getelementptr i8, ptr %t3, i64 %t270
  %t274 = load i8, ptr %t273
  %t275 = alloca i8
  store i8 %t274, ptr %t275
  %t276 = load i8, ptr %t269
  %t277 = zext i8 %t276 to i32
  %t278 = alloca i32
  store i32 %t277, ptr %t278
  %t279 = load i8, ptr %t275
  %t280 = zext i8 %t279 to i32
  %t281 = alloca i32
  store i32 %t280, ptr %t281
  %t282 = load i32, ptr %t278
  %t283 = and i32 8, 31
  %t284 = shl i32 %t282, %t283
  %t285 = alloca i32
  store i32 %t284, ptr %t285
  %t286 = load i32, ptr %t285
  %t287 = load i32, ptr %t281
  %t288 = or i32 %t286, %t287
  %t289 = alloca i32
  store i32 %t288, ptr %t289
  %t290 = load i32, ptr %t289
  %t291 = and i32 10, 31
  %t292 = lshr i32 %t290, %t291
  %t293 = alloca i32
  store i32 %t292, ptr %t293
  %t294 = load i32, ptr %t293
  %t295 = and i32 %t294, 63
  %t296 = alloca i32
  store i32 %t295, ptr %t296
  %t297 = load i32, ptr %t296
  %t298 = zext i32 %t297 to i64
  %t299 = alloca i64
  store i64 %t298, ptr %t299
  %t300 = load i32, ptr %t289
  %t301 = and i32 4, 31
  %t302 = lshr i32 %t300, %t301
  %t303 = alloca i32
  store i32 %t302, ptr %t303
  %t304 = load i32, ptr %t303
  %t305 = and i32 %t304, 63
  %t306 = alloca i32
  store i32 %t305, ptr %t306
  %t307 = load i32, ptr %t306
  %t308 = zext i32 %t307 to i64
  %t309 = alloca i64
  store i64 %t308, ptr %t309
  %t310 = load i32, ptr %t289
  %t311 = and i32 2, 31
  %t312 = shl i32 %t310, %t311
  %t313 = alloca i32
  store i32 %t312, ptr %t313
  %t314 = load i32, ptr %t313
  %t315 = and i32 %t314, 63
  %t316 = alloca i32
  store i32 %t315, ptr %t316
  %t317 = load i32, ptr %t316
  %t318 = zext i32 %t317 to i64
  %t319 = alloca i64
  store i64 %t318, ptr %t319
  %t320 = load i64, ptr %t299
  %t321 = icmp ult i64 %t320, 64
  br i1 %t321, label %L322, label %trap
L322:
  %t323 = getelementptr [64 x i8], ptr @__const_b64, i64 0, i64 %t320
  %t324 = load i8, ptr %t323
  %t325 = alloca i8
  store i8 %t324, ptr %t325
  %t326 = load i64, ptr %t309
  %t327 = icmp ult i64 %t326, 64
  br i1 %t327, label %L328, label %trap
L328:
  %t329 = getelementptr [64 x i8], ptr @__const_b64, i64 0, i64 %t326
  %t330 = load i8, ptr %t329
  %t331 = alloca i8
  store i8 %t330, ptr %t331
  %t332 = load i64, ptr %t319
  %t333 = icmp ult i64 %t332, 64
  br i1 %t333, label %L334, label %trap
L334:
  %t335 = getelementptr [64 x i8], ptr @__const_b64, i64 0, i64 %t332
  %t336 = load i8, ptr %t335
  %t337 = alloca i8
  store i8 %t336, ptr %t337
  %t338 = load i64, ptr %t23
  %t339 = add i64 %t338, 1
  %t340 = alloca i64
  store i64 %t339, ptr %t340
  %t341 = load i64, ptr %t23
  %t342 = add i64 %t341, 2
  %t343 = alloca i64
  store i64 %t342, ptr %t343
  %t344 = load i64, ptr %t23
  %t345 = add i64 %t344, 3
  %t346 = alloca i64
  store i64 %t345, ptr %t346
  %t347 = load i8, ptr %t325
  %t348 = load i64, ptr %t23
  %t349 = icmp ult i64 %t348, %t2
  br i1 %t349, label %L350, label %trap
L350:
  %t351 = getelementptr i8, ptr %t1, i64 %t348
  store i8 %t347, ptr %t351
  %t352 = load i8, ptr %t331
  %t353 = load i64, ptr %t340
  %t354 = icmp ult i64 %t353, %t2
  br i1 %t354, label %L355, label %trap
L355:
  %t356 = getelementptr i8, ptr %t1, i64 %t353
  store i8 %t352, ptr %t356
  %t357 = load i8, ptr %t337
  %t358 = load i64, ptr %t343
  %t359 = icmp ult i64 %t358, %t2
  br i1 %t359, label %L360, label %trap
L360:
  %t361 = getelementptr i8, ptr %t1, i64 %t358
  store i8 %t357, ptr %t361
  %t362 = load i64, ptr %t346
  %t363 = icmp ult i64 %t362, %t2
  br i1 %t363, label %L364, label %trap
L364:
  %t365 = getelementptr i8, ptr %t1, i64 %t362
  store i8 61, ptr %t365
  %t366 = load i64, ptr %t23
  %t367 = add i64 %t366, 4
  store i64 %t367, ptr %t23
  br label %L258
L260:
  br label %L258
L258:
  %t368 = load i64, ptr %t23
  ret i64 %t368
trap:
  call void @llvm.trap()
  unreachable
}
