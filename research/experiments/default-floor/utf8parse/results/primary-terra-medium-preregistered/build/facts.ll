declare {i32, i1} @llvm.sadd.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.ssub.with.overflow.i32(i32, i32)
declare {i32, i1} @llvm.smul.with.overflow.i32(i32, i32)
declare void @llvm.trap()

define i64 @xlang_parse_facts({ptr, i64} %out, {ptr, i64} %src) nounwind memory(argmem: readwrite, inaccessiblemem: write) {
entry:
  %t1 = extractvalue {ptr, i64} %out, 0
  %t2 = extractvalue {ptr, i64} %out, 1
  %t3 = extractvalue {ptr, i64} %src, 0
  %t4 = extractvalue {ptr, i64} %src, 1
  %t5 = alloca i64
  store i64 %t4, ptr %t5
  %t6 = alloca i64
  store i64 %t2, ptr %t6
  %t7 = load i64, ptr %t6
  %t8 = load i64, ptr %t5
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
  %t18 = alloca i8
  store i8 0, ptr %t18
  %t19 = alloca i32
  store i32 0, ptr %t19
  br label %L20
L20:
  %t22 = load i64, ptr %t16
  %t23 = load i64, ptr %t15
  %t24 = icmp eq i64 %t22, %t23
  %t25 = alloca i1
  store i1 %t24, ptr %t25
  %t26 = load i1, ptr %t25
  br i1 %t26, label %L28, label %L29
L28:
  br label %L21
L29:
  br label %L27
L27:
  %t30 = load i64, ptr %t16
  %t31 = icmp ult i64 %t30, %t4
  br i1 %t31, label %L32, label %trap
L32:
  %t33 = getelementptr i8, ptr %t3, i64 %t30
  %t34 = load i8, ptr %t33
  %t35 = alloca i8
  store i8 %t34, ptr %t35
  %t36 = load i8, ptr %t18
  %t37 = icmp eq i8 %t36, 0
  %t38 = alloca i1
  store i1 %t37, ptr %t38
  %t39 = load i1, ptr %t38
  br i1 %t39, label %L41, label %L42
L41:
  %t43 = load i8, ptr %t35
  %t44 = icmp ule i8 %t43, 127
  %t45 = alloca i1
  store i1 %t44, ptr %t45
  %t46 = load i1, ptr %t45
  br i1 %t46, label %L48, label %L49
L48:
  %t50 = load i8, ptr %t35
  %t51 = zext i8 %t50 to i32
  %t52 = alloca i32
  store i32 %t51, ptr %t52
  %t53 = load i32, ptr %t52
  %t54 = load i64, ptr %t17
  %t55 = icmp ult i64 %t54, %t2
  br i1 %t55, label %L56, label %trap
L56:
  %t57 = getelementptr i32, ptr %t1, i64 %t54
  store i32 %t53, ptr %t57
  %t58 = load i64, ptr %t17
  %t59 = add i64 %t58, 1
  store i64 %t59, ptr %t17
  br label %L47
L49:
  %t60 = load i8, ptr %t35
  %t61 = icmp uge i8 %t60, 194
  %t62 = alloca i1
  store i1 %t61, ptr %t62
  %t63 = load i8, ptr %t35
  %t64 = icmp ule i8 %t63, 223
  %t65 = alloca i1
  store i1 %t64, ptr %t65
  %t66 = load i1, ptr %t62
  %t67 = load i1, ptr %t65
  %t68 = and i1 %t66, %t67
  %t69 = alloca i1
  store i1 %t68, ptr %t69
  %t70 = load i1, ptr %t69
  br i1 %t70, label %L72, label %L73
L72:
  %t74 = load i8, ptr %t35
  %t75 = sub i8 %t74, 192
  %t76 = alloca i8
  store i8 %t75, ptr %t76
  %t77 = load i8, ptr %t76
  %t78 = zext i8 %t77 to i32
  store i32 %t78, ptr %t19
  store i8 1, ptr %t18
  br label %L71
L73:
  %t79 = load i8, ptr %t35
  %t80 = icmp eq i8 %t79, 224
  %t81 = alloca i1
  store i1 %t80, ptr %t81
  %t82 = load i1, ptr %t81
  br i1 %t82, label %L84, label %L85
L84:
  %t86 = load i8, ptr %t35
  %t87 = sub i8 %t86, 224
  %t88 = alloca i8
  store i8 %t87, ptr %t88
  %t89 = load i8, ptr %t88
  %t90 = zext i8 %t89 to i32
  store i32 %t90, ptr %t19
  store i8 3, ptr %t18
  br label %L83
L85:
  %t91 = load i8, ptr %t35
  %t92 = icmp uge i8 %t91, 225
  %t93 = alloca i1
  store i1 %t92, ptr %t93
  %t94 = load i8, ptr %t35
  %t95 = icmp ule i8 %t94, 239
  %t96 = alloca i1
  store i1 %t95, ptr %t96
  %t97 = load i1, ptr %t93
  %t98 = load i1, ptr %t96
  %t99 = and i1 %t97, %t98
  %t100 = alloca i1
  store i1 %t99, ptr %t100
  %t101 = load i8, ptr %t35
  %t102 = icmp ne i8 %t101, 237
  %t103 = alloca i1
  store i1 %t102, ptr %t103
  %t104 = load i1, ptr %t100
  %t105 = load i1, ptr %t103
  %t106 = and i1 %t104, %t105
  %t107 = alloca i1
  store i1 %t106, ptr %t107
  %t108 = load i1, ptr %t107
  br i1 %t108, label %L110, label %L111
L110:
  %t112 = load i8, ptr %t35
  %t113 = sub i8 %t112, 224
  %t114 = alloca i8
  store i8 %t113, ptr %t114
  %t115 = load i8, ptr %t114
  %t116 = zext i8 %t115 to i32
  store i32 %t116, ptr %t19
  store i8 2, ptr %t18
  br label %L109
L111:
  %t117 = load i8, ptr %t35
  %t118 = icmp eq i8 %t117, 237
  %t119 = alloca i1
  store i1 %t118, ptr %t119
  %t120 = load i1, ptr %t119
  br i1 %t120, label %L122, label %L123
L122:
  %t124 = load i8, ptr %t35
  %t125 = sub i8 %t124, 224
  %t126 = alloca i8
  store i8 %t125, ptr %t126
  %t127 = load i8, ptr %t126
  %t128 = zext i8 %t127 to i32
  store i32 %t128, ptr %t19
  store i8 4, ptr %t18
  br label %L121
L123:
  %t129 = load i8, ptr %t35
  %t130 = icmp eq i8 %t129, 240
  %t131 = alloca i1
  store i1 %t130, ptr %t131
  %t132 = load i1, ptr %t131
  br i1 %t132, label %L134, label %L135
L134:
  %t136 = load i8, ptr %t35
  %t137 = sub i8 %t136, 240
  %t138 = alloca i8
  store i8 %t137, ptr %t138
  %t139 = load i8, ptr %t138
  %t140 = zext i8 %t139 to i32
  store i32 %t140, ptr %t19
  store i8 6, ptr %t18
  br label %L133
L135:
  %t141 = load i8, ptr %t35
  %t142 = icmp uge i8 %t141, 241
  %t143 = alloca i1
  store i1 %t142, ptr %t143
  %t144 = load i8, ptr %t35
  %t145 = icmp ule i8 %t144, 243
  %t146 = alloca i1
  store i1 %t145, ptr %t146
  %t147 = load i1, ptr %t143
  %t148 = load i1, ptr %t146
  %t149 = and i1 %t147, %t148
  %t150 = alloca i1
  store i1 %t149, ptr %t150
  %t151 = load i1, ptr %t150
  br i1 %t151, label %L153, label %L154
L153:
  %t155 = load i8, ptr %t35
  %t156 = sub i8 %t155, 240
  %t157 = alloca i8
  store i8 %t156, ptr %t157
  %t158 = load i8, ptr %t157
  %t159 = zext i8 %t158 to i32
  store i32 %t159, ptr %t19
  store i8 5, ptr %t18
  br label %L152
L154:
  %t160 = load i8, ptr %t35
  %t161 = icmp eq i8 %t160, 244
  %t162 = alloca i1
  store i1 %t161, ptr %t162
  %t163 = load i1, ptr %t162
  br i1 %t163, label %L165, label %L166
L165:
  %t167 = load i8, ptr %t35
  %t168 = sub i8 %t167, 240
  %t169 = alloca i8
  store i8 %t168, ptr %t169
  %t170 = load i8, ptr %t169
  %t171 = zext i8 %t170 to i32
  store i32 %t171, ptr %t19
  store i8 7, ptr %t18
  br label %L164
L166:
  %t172 = load i64, ptr %t17
  %t173 = icmp ult i64 %t172, %t2
  br i1 %t173, label %L174, label %trap
L174:
  %t175 = getelementptr i32, ptr %t1, i64 %t172
  store i32 1114112, ptr %t175
  %t176 = load i64, ptr %t17
  %t177 = add i64 %t176, 1
  store i64 %t177, ptr %t17
  br label %L164
L164:
  br label %L152
L152:
  br label %L133
L133:
  br label %L121
L121:
  br label %L109
L109:
  br label %L83
L83:
  br label %L71
L71:
  br label %L47
L47:
  br label %L40
L42:
  %t178 = load i8, ptr %t35
  %t179 = icmp uge i8 %t178, 128
  %t180 = alloca i1
  store i1 %t179, ptr %t180
  %t181 = load i8, ptr %t35
  %t182 = icmp ule i8 %t181, 191
  %t183 = alloca i1
  store i1 %t182, ptr %t183
  %t184 = load i1, ptr %t180
  %t185 = load i1, ptr %t183
  %t186 = and i1 %t184, %t185
  %t187 = alloca i1
  store i1 %t186, ptr %t187
  %t188 = load i8, ptr %t18
  %t189 = icmp eq i8 %t188, 1
  %t190 = alloca i1
  store i1 %t189, ptr %t190
  %t191 = load i1, ptr %t190
  br i1 %t191, label %L193, label %L194
L193:
  %t195 = load i1, ptr %t187
  br i1 %t195, label %L197, label %L198
L197:
  %t199 = load i8, ptr %t35
  %t200 = sub i8 %t199, 128
  %t201 = alloca i8
  store i8 %t200, ptr %t201
  %t202 = load i8, ptr %t201
  %t203 = zext i8 %t202 to i32
  %t204 = alloca i32
  store i32 %t203, ptr %t204
  %t205 = load i32, ptr %t19
  %t206 = mul i32 %t205, 64
  %t207 = alloca i32
  store i32 %t206, ptr %t207
  %t208 = load i32, ptr %t207
  %t209 = load i32, ptr %t204
  %t210 = add i32 %t208, %t209
  %t211 = alloca i32
  store i32 %t210, ptr %t211
  %t212 = load i32, ptr %t211
  %t213 = load i64, ptr %t17
  %t214 = icmp ult i64 %t213, %t2
  br i1 %t214, label %L215, label %trap
L215:
  %t216 = getelementptr i32, ptr %t1, i64 %t213
  store i32 %t212, ptr %t216
  %t217 = load i64, ptr %t17
  %t218 = add i64 %t217, 1
  store i64 %t218, ptr %t17
  store i8 0, ptr %t18
  br label %L196
L198:
  %t219 = load i64, ptr %t17
  %t220 = icmp ult i64 %t219, %t2
  br i1 %t220, label %L221, label %trap
L221:
  %t222 = getelementptr i32, ptr %t1, i64 %t219
  store i32 1114112, ptr %t222
  %t223 = load i64, ptr %t17
  %t224 = add i64 %t223, 1
  store i64 %t224, ptr %t17
  store i8 0, ptr %t18
  br label %L196
L196:
  br label %L192
L194:
  %t225 = load i8, ptr %t18
  %t226 = icmp eq i8 %t225, 2
  %t227 = alloca i1
  store i1 %t226, ptr %t227
  %t228 = load i1, ptr %t227
  br i1 %t228, label %L230, label %L231
L230:
  %t232 = load i1, ptr %t187
  br i1 %t232, label %L234, label %L235
L234:
  %t236 = load i8, ptr %t35
  %t237 = sub i8 %t236, 128
  %t238 = alloca i8
  store i8 %t237, ptr %t238
  %t239 = load i8, ptr %t238
  %t240 = zext i8 %t239 to i32
  %t241 = alloca i32
  store i32 %t240, ptr %t241
  %t242 = load i32, ptr %t19
  %t243 = mul i32 %t242, 64
  %t244 = alloca i32
  store i32 %t243, ptr %t244
  %t245 = load i32, ptr %t244
  %t246 = load i32, ptr %t241
  %t247 = add i32 %t245, %t246
  store i32 %t247, ptr %t19
  store i8 1, ptr %t18
  br label %L233
L235:
  %t248 = load i64, ptr %t17
  %t249 = icmp ult i64 %t248, %t2
  br i1 %t249, label %L250, label %trap
L250:
  %t251 = getelementptr i32, ptr %t1, i64 %t248
  store i32 1114112, ptr %t251
  %t252 = load i64, ptr %t17
  %t253 = add i64 %t252, 1
  store i64 %t253, ptr %t17
  store i8 0, ptr %t18
  br label %L233
L233:
  br label %L229
L231:
  %t254 = load i8, ptr %t18
  %t255 = icmp eq i8 %t254, 3
  %t256 = alloca i1
  store i1 %t255, ptr %t256
  %t257 = load i1, ptr %t256
  br i1 %t257, label %L259, label %L260
L259:
  %t261 = load i8, ptr %t35
  %t262 = icmp uge i8 %t261, 160
  %t263 = alloca i1
  store i1 %t262, ptr %t263
  %t264 = load i8, ptr %t35
  %t265 = icmp ule i8 %t264, 191
  %t266 = alloca i1
  store i1 %t265, ptr %t266
  %t267 = load i1, ptr %t263
  %t268 = load i1, ptr %t266
  %t269 = and i1 %t267, %t268
  %t270 = alloca i1
  store i1 %t269, ptr %t270
  %t271 = load i1, ptr %t270
  br i1 %t271, label %L273, label %L274
L273:
  %t275 = load i8, ptr %t35
  %t276 = sub i8 %t275, 128
  %t277 = alloca i8
  store i8 %t276, ptr %t277
  %t278 = load i8, ptr %t277
  %t279 = zext i8 %t278 to i32
  %t280 = alloca i32
  store i32 %t279, ptr %t280
  %t281 = load i32, ptr %t19
  %t282 = mul i32 %t281, 64
  %t283 = alloca i32
  store i32 %t282, ptr %t283
  %t284 = load i32, ptr %t283
  %t285 = load i32, ptr %t280
  %t286 = add i32 %t284, %t285
  store i32 %t286, ptr %t19
  store i8 1, ptr %t18
  br label %L272
L274:
  %t287 = load i64, ptr %t17
  %t288 = icmp ult i64 %t287, %t2
  br i1 %t288, label %L289, label %trap
L289:
  %t290 = getelementptr i32, ptr %t1, i64 %t287
  store i32 1114112, ptr %t290
  %t291 = load i64, ptr %t17
  %t292 = add i64 %t291, 1
  store i64 %t292, ptr %t17
  store i8 0, ptr %t18
  br label %L272
L272:
  br label %L258
L260:
  %t293 = load i8, ptr %t18
  %t294 = icmp eq i8 %t293, 4
  %t295 = alloca i1
  store i1 %t294, ptr %t295
  %t296 = load i1, ptr %t295
  br i1 %t296, label %L298, label %L299
L298:
  %t300 = load i8, ptr %t35
  %t301 = icmp uge i8 %t300, 128
  %t302 = alloca i1
  store i1 %t301, ptr %t302
  %t303 = load i8, ptr %t35
  %t304 = icmp ule i8 %t303, 159
  %t305 = alloca i1
  store i1 %t304, ptr %t305
  %t306 = load i1, ptr %t302
  %t307 = load i1, ptr %t305
  %t308 = and i1 %t306, %t307
  %t309 = alloca i1
  store i1 %t308, ptr %t309
  %t310 = load i1, ptr %t309
  br i1 %t310, label %L312, label %L313
L312:
  %t314 = load i8, ptr %t35
  %t315 = sub i8 %t314, 128
  %t316 = alloca i8
  store i8 %t315, ptr %t316
  %t317 = load i8, ptr %t316
  %t318 = zext i8 %t317 to i32
  %t319 = alloca i32
  store i32 %t318, ptr %t319
  %t320 = load i32, ptr %t19
  %t321 = mul i32 %t320, 64
  %t322 = alloca i32
  store i32 %t321, ptr %t322
  %t323 = load i32, ptr %t322
  %t324 = load i32, ptr %t319
  %t325 = add i32 %t323, %t324
  store i32 %t325, ptr %t19
  store i8 1, ptr %t18
  br label %L311
L313:
  %t326 = load i64, ptr %t17
  %t327 = icmp ult i64 %t326, %t2
  br i1 %t327, label %L328, label %trap
L328:
  %t329 = getelementptr i32, ptr %t1, i64 %t326
  store i32 1114112, ptr %t329
  %t330 = load i64, ptr %t17
  %t331 = add i64 %t330, 1
  store i64 %t331, ptr %t17
  store i8 0, ptr %t18
  br label %L311
L311:
  br label %L297
L299:
  %t332 = load i8, ptr %t18
  %t333 = icmp eq i8 %t332, 5
  %t334 = alloca i1
  store i1 %t333, ptr %t334
  %t335 = load i1, ptr %t334
  br i1 %t335, label %L337, label %L338
L337:
  %t339 = load i1, ptr %t187
  br i1 %t339, label %L341, label %L342
L341:
  %t343 = load i8, ptr %t35
  %t344 = sub i8 %t343, 128
  %t345 = alloca i8
  store i8 %t344, ptr %t345
  %t346 = load i8, ptr %t345
  %t347 = zext i8 %t346 to i32
  %t348 = alloca i32
  store i32 %t347, ptr %t348
  %t349 = load i32, ptr %t19
  %t350 = mul i32 %t349, 64
  %t351 = alloca i32
  store i32 %t350, ptr %t351
  %t352 = load i32, ptr %t351
  %t353 = load i32, ptr %t348
  %t354 = add i32 %t352, %t353
  store i32 %t354, ptr %t19
  store i8 2, ptr %t18
  br label %L340
L342:
  %t355 = load i64, ptr %t17
  %t356 = icmp ult i64 %t355, %t2
  br i1 %t356, label %L357, label %trap
L357:
  %t358 = getelementptr i32, ptr %t1, i64 %t355
  store i32 1114112, ptr %t358
  %t359 = load i64, ptr %t17
  %t360 = add i64 %t359, 1
  store i64 %t360, ptr %t17
  store i8 0, ptr %t18
  br label %L340
L340:
  br label %L336
L338:
  %t361 = load i8, ptr %t18
  %t362 = icmp eq i8 %t361, 6
  %t363 = alloca i1
  store i1 %t362, ptr %t363
  %t364 = load i1, ptr %t363
  br i1 %t364, label %L366, label %L367
L366:
  %t368 = load i8, ptr %t35
  %t369 = icmp uge i8 %t368, 144
  %t370 = alloca i1
  store i1 %t369, ptr %t370
  %t371 = load i8, ptr %t35
  %t372 = icmp ule i8 %t371, 191
  %t373 = alloca i1
  store i1 %t372, ptr %t373
  %t374 = load i1, ptr %t370
  %t375 = load i1, ptr %t373
  %t376 = and i1 %t374, %t375
  %t377 = alloca i1
  store i1 %t376, ptr %t377
  %t378 = load i1, ptr %t377
  br i1 %t378, label %L380, label %L381
L380:
  %t382 = load i8, ptr %t35
  %t383 = sub i8 %t382, 128
  %t384 = alloca i8
  store i8 %t383, ptr %t384
  %t385 = load i8, ptr %t384
  %t386 = zext i8 %t385 to i32
  %t387 = alloca i32
  store i32 %t386, ptr %t387
  %t388 = load i32, ptr %t19
  %t389 = mul i32 %t388, 64
  %t390 = alloca i32
  store i32 %t389, ptr %t390
  %t391 = load i32, ptr %t390
  %t392 = load i32, ptr %t387
  %t393 = add i32 %t391, %t392
  store i32 %t393, ptr %t19
  store i8 2, ptr %t18
  br label %L379
L381:
  %t394 = load i64, ptr %t17
  %t395 = icmp ult i64 %t394, %t2
  br i1 %t395, label %L396, label %trap
L396:
  %t397 = getelementptr i32, ptr %t1, i64 %t394
  store i32 1114112, ptr %t397
  %t398 = load i64, ptr %t17
  %t399 = add i64 %t398, 1
  store i64 %t399, ptr %t17
  store i8 0, ptr %t18
  br label %L379
L379:
  br label %L365
L367:
  %t400 = load i8, ptr %t35
  %t401 = icmp uge i8 %t400, 128
  %t402 = alloca i1
  store i1 %t401, ptr %t402
  %t403 = load i8, ptr %t35
  %t404 = icmp ule i8 %t403, 143
  %t405 = alloca i1
  store i1 %t404, ptr %t405
  %t406 = load i1, ptr %t402
  %t407 = load i1, ptr %t405
  %t408 = and i1 %t406, %t407
  %t409 = alloca i1
  store i1 %t408, ptr %t409
  %t410 = load i1, ptr %t409
  br i1 %t410, label %L412, label %L413
L412:
  %t414 = load i8, ptr %t35
  %t415 = sub i8 %t414, 128
  %t416 = alloca i8
  store i8 %t415, ptr %t416
  %t417 = load i8, ptr %t416
  %t418 = zext i8 %t417 to i32
  %t419 = alloca i32
  store i32 %t418, ptr %t419
  %t420 = load i32, ptr %t19
  %t421 = mul i32 %t420, 64
  %t422 = alloca i32
  store i32 %t421, ptr %t422
  %t423 = load i32, ptr %t422
  %t424 = load i32, ptr %t419
  %t425 = add i32 %t423, %t424
  store i32 %t425, ptr %t19
  store i8 2, ptr %t18
  br label %L411
L413:
  %t426 = load i64, ptr %t17
  %t427 = icmp ult i64 %t426, %t2
  br i1 %t427, label %L428, label %trap
L428:
  %t429 = getelementptr i32, ptr %t1, i64 %t426
  store i32 1114112, ptr %t429
  %t430 = load i64, ptr %t17
  %t431 = add i64 %t430, 1
  store i64 %t431, ptr %t17
  store i8 0, ptr %t18
  br label %L411
L411:
  br label %L365
L365:
  br label %L336
L336:
  br label %L297
L297:
  br label %L258
L258:
  br label %L229
L229:
  br label %L192
L192:
  br label %L40
L40:
  %t432 = load i64, ptr %t16
  %t433 = add i64 %t432, 1
  store i64 %t433, ptr %t16
  br label %L20
L21:
  %t434 = load i64, ptr %t17
  ret i64 %t434
trap:
  call void @llvm.trap()
  unreachable
}
