	.build_version macos, 26, 0
	.section	__TEXT,__text,regular,pure_instructions
	.globl	_kernel                         ; -- Begin function kernel
	.p2align	2
_kernel:                                ; @kernel
; %bb.0:                                ; %entry
	ldur	q0, [x0, #152]
	ldur	q1, [x0, #136]
	ldur	q2, [x0, #24]
	ldur	q3, [x0, #8]
	ldur	q4, [x0, #216]
	ldur	q5, [x0, #200]
	ldur	q6, [x0, #88]
	ldur	q7, [x0, #72]
	ldur	q16, [x0, #184]
	ldur	q17, [x0, #168]
	ldur	q18, [x0, #56]
	ldur	q19, [x0, #40]
	add	x8, x0, #248
	ldur	q20, [x0, #232]
	ldur	q21, [x0, #120]
	ldur	q22, [x0, #104]
	zip1.2d	v21, v22, v21
	ld1.d	{ v20 }[1], [x8]
	zip1.2d	v18, v19, v18
	zip1.2d	v16, v17, v16
	zip1.2d	v6, v7, v6
	zip1.2d	v4, v5, v4
	zip1.2d	v2, v3, v2
	zip1.2d	v0, v1, v0
	cmhi.2d	v1, v0, v2
	bit.16b	v0, v2, v1
	cmhi.2d	v1, v4, v6
	bsl.16b	v1, v6, v4
	cmhi.2d	v2, v1, v0
	bif.16b	v0, v1, v2
	cmhi.2d	v1, v16, v18
	bsl.16b	v1, v18, v16
	cmhi.2d	v2, v20, v21
	bsl.16b	v2, v21, v20
	cmhi.2d	v3, v2, v1
	bif.16b	v1, v2, v3
	cmhi.2d	v2, v1, v0
	bif.16b	v0, v1, v2
	ext.16b	v1, v0, v0, #8
	cmhi	d2, d1, d0
	bif.8b	v0, v1, v2
	fmov	x8, d0
	cbz	x8, LBB0_9
; %bb.1:                                ; %L165.lr.ph
	stp	x24, x23, [sp, #-48]!           ; 16-byte Folded Spill
	stp	x22, x21, [sp, #16]             ; 16-byte Folded Spill
	stp	x20, x19, [sp, #32]             ; 16-byte Folded Spill
	ldr	x7, [x0]
	ldr	x6, [x0, #64]
	ldr	x5, [x0, #80]
	ldr	x4, [x0, #96]
	ldr	x3, [x0, #16]
	ldr	x2, [x0, #112]
	ldr	x1, [x0, #128]
	ldr	x17, [x0, #144]
	ldr	x16, [x0, #32]
	ldr	x15, [x0, #160]
	ldr	x14, [x0, #176]
	ldr	x13, [x0, #192]
	ldr	x12, [x0, #48]
	ldr	x11, [x0, #208]
	ldr	x10, [x0, #224]
	ldr	x9, [x0, #240]
	cmp	x8, #1
	b.ne	LBB0_3
; %bb.2:
	mov	x0, #0                          ; =0x0
	b	LBB0_6
LBB0_3:                                 ; %vector.ph
	mov	x19, #0                         ; =0x0
	and	x0, x8, #0xfffffffffffffffe
	mov	x20, x0
LBB0_4:                                 ; %vector.body
                                        ; =>This Inner Loop Header: Depth=1
	ldr	q0, [x7, x19]
	ldr	q1, [x6, x19]
	ldr	q2, [x5, x19]
	add.2d	v0, v1, v0
	ldr	q1, [x4, x19]
	add.2d	v1, v2, v1
	add.2d	v0, v0, v1
	str	q0, [x7, x19]
	ldr	q0, [x3, x19]
	ldr	q1, [x2, x19]
	ldr	q2, [x1, x19]
	add.2d	v0, v1, v0
	ldr	q1, [x17, x19]
	add.2d	v1, v2, v1
	add.2d	v0, v0, v1
	str	q0, [x3, x19]
	ldr	q0, [x16, x19]
	ldr	q1, [x15, x19]
	ldr	q2, [x14, x19]
	add.2d	v0, v1, v0
	ldr	q1, [x13, x19]
	add.2d	v1, v2, v1
	add.2d	v0, v0, v1
	str	q0, [x16, x19]
	ldr	q0, [x12, x19]
	ldr	q1, [x11, x19]
	ldr	q2, [x10, x19]
	add.2d	v0, v1, v0
	ldr	q1, [x9, x19]
	add.2d	v1, v2, v1
	add.2d	v0, v0, v1
	str	q0, [x12, x19]
	add	x19, x19, #16
	subs	x20, x20, #2
	b.ne	LBB0_4
; %bb.5:                                ; %middle.block
	cmp	x8, x0
	b.eq	LBB0_8
LBB0_6:                                 ; %L165.preheader
	mov	x19, #0                         ; =0x0
	lsl	x20, x0, #3
	add	x7, x7, x20
	add	x6, x6, x20
	add	x5, x5, x20
	add	x4, x4, x20
	add	x3, x3, x20
	add	x2, x2, x20
	add	x1, x1, x20
	add	x17, x17, x20
	add	x16, x16, x20
	add	x15, x15, x20
	add	x14, x14, x20
	add	x13, x13, x20
	add	x12, x12, x20
	add	x11, x11, x20
	add	x10, x10, x20
	add	x9, x9, x20
	sub	x8, x8, x0
LBB0_7:                                 ; %L165
                                        ; =>This Inner Loop Header: Depth=1
	ldr	x0, [x7, x19, lsl #3]
	ldr	x20, [x6, x19, lsl #3]
	ldr	x21, [x5, x19, lsl #3]
	add	x0, x20, x0
	ldr	x20, [x4, x19, lsl #3]
	add	x20, x21, x20
	add	x0, x0, x20
	str	x0, [x7, x19, lsl #3]
	ldr	x0, [x3, x19, lsl #3]
	ldr	x20, [x2, x19, lsl #3]
	ldr	x21, [x1, x19, lsl #3]
	add	x0, x20, x0
	ldr	x20, [x17, x19, lsl #3]
	add	x20, x21, x20
	add	x0, x0, x20
	ldr	x20, [x16, x19, lsl #3]
	ldr	x21, [x15, x19, lsl #3]
	ldr	x22, [x14, x19, lsl #3]
	add	x20, x21, x20
	ldr	x21, [x13, x19, lsl #3]
	ldr	x23, [x12, x19, lsl #3]
	add	x21, x22, x21
	add	x20, x20, x21
	ldr	x21, [x11, x19, lsl #3]
	ldr	x22, [x10, x19, lsl #3]
	add	x21, x21, x23
	ldr	x23, [x9, x19, lsl #3]
	add	x22, x22, x23
	add	x21, x21, x22
	str	x0, [x3, x19, lsl #3]
	str	x20, [x16, x19, lsl #3]
	str	x21, [x12, x19, lsl #3]
	add	x19, x19, #1
	cmp	x8, x19
	b.ne	LBB0_7
LBB0_8:
	ldp	x20, x19, [sp, #32]             ; 16-byte Folded Reload
	ldp	x22, x21, [sp, #16]             ; 16-byte Folded Reload
	ldp	x24, x23, [sp], #48             ; 16-byte Folded Reload
LBB0_9:                                 ; %L161
	ret
                                        ; -- End function
.subsections_via_symbols
