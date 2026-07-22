	.build_version macos, 26, 0
	.section	__TEXT,__text,regular,pure_instructions
	.globl	_kernel                         ; -- Begin function kernel
	.p2align	2
_kernel:                                ; @kernel
; %bb.0:                                ; %entry
	ldur	q0, [x0, #88]
	ldur	q1, [x0, #72]
	ldur	q2, [x0, #24]
	ldur	q3, [x0, #8]
	add	x8, x0, #120
	ldur	q4, [x0, #104]
	ldur	q5, [x0, #56]
	ldur	q6, [x0, #40]
	zip1.2d	v5, v6, v5
	ld1.d	{ v4 }[1], [x8]
	zip1.2d	v2, v3, v2
	zip1.2d	v0, v1, v0
	cmhi.2d	v1, v0, v2
	bit.16b	v0, v2, v1
	cmhi.2d	v1, v4, v5
	bsl.16b	v1, v5, v4
	cmhi.2d	v2, v1, v0
	bif.16b	v0, v1, v2
	ext.16b	v1, v0, v0, #8
	cmhi	d2, d1, d0
	bif.8b	v0, v1, v2
	fmov	x8, d0
	cbz	x8, LBB0_9
; %bb.1:                                ; %L83.lr.ph
	stp	x20, x19, [sp, #-16]!           ; 16-byte Folded Spill
	ldr	x16, [x0]
	ldr	x15, [x0, #32]
	ldr	x14, [x0, #48]
	ldr	x13, [x0, #64]
	ldr	x12, [x0, #80]
	ldr	x11, [x0, #16]
	ldr	x10, [x0, #96]
	ldr	x9, [x0, #112]
	cmp	x8, #1
	b.ne	LBB0_3
; %bb.2:
	mov	x17, #0                         ; =0x0
	b	LBB0_6
LBB0_3:                                 ; %vector.ph
	and	x17, x8, #0xfffffffffffffffe
	mov	x0, x16
	mov	x1, x15
	mov	x2, x14
	mov	x3, x13
	mov	x4, x12
	mov	x5, x11
	mov	x6, x10
	mov	x7, x9
	mov	x19, x17
LBB0_4:                                 ; %vector.body
                                        ; =>This Inner Loop Header: Depth=1
	ldr	q0, [x0]
	ldr	q1, [x1], #16
	ldr	q2, [x2], #16
	ldr	q3, [x3], #16
	ldr	q4, [x4], #16
	add.2d	v0, v1, v0
	add.2d	v1, v2, v3
	add.2d	v0, v0, v1
	add.2d	v0, v0, v4
	str	q0, [x0], #16
	ldr	q0, [x5]
	ldr	q1, [x6], #16
	ldr	q2, [x7], #16
	add.2d	v3, v4, v3
	add.2d	v0, v0, v1
	add.2d	v0, v3, v0
	add.2d	v0, v0, v2
	str	q0, [x5], #16
	subs	x19, x19, #2
	b.ne	LBB0_4
; %bb.5:                                ; %middle.block
	cmp	x8, x17
	b.eq	LBB0_8
LBB0_6:                                 ; %L83.preheader
	mov	x0, #0                          ; =0x0
	lsl	x1, x17, #3
	add	x16, x16, x1
	add	x15, x15, x1
	add	x14, x14, x1
	add	x13, x13, x1
	add	x12, x12, x1
	add	x11, x11, x1
	add	x10, x10, x1
	add	x9, x9, x1
	sub	x8, x8, x17
LBB0_7:                                 ; %L83
                                        ; =>This Inner Loop Header: Depth=1
	ldr	x17, [x16, x0, lsl #3]
	ldr	x1, [x15, x0, lsl #3]
	ldr	x2, [x14, x0, lsl #3]
	ldr	x3, [x13, x0, lsl #3]
	ldr	x4, [x12, x0, lsl #3]
	add	x17, x1, x17
	add	x1, x2, x3
	add	x17, x17, x1
	add	x17, x17, x4
	str	x17, [x16, x0, lsl #3]
	ldr	x17, [x11, x0, lsl #3]
	ldr	x1, [x10, x0, lsl #3]
	ldr	x2, [x9, x0, lsl #3]
	add	x3, x4, x3
	add	x17, x17, x1
	add	x17, x3, x17
	add	x17, x17, x2
	str	x17, [x11, x0, lsl #3]
	add	x0, x0, #1
	cmp	x8, x0
	b.ne	LBB0_7
LBB0_8:
	ldp	x20, x19, [sp], #16             ; 16-byte Folded Reload
LBB0_9:                                 ; %L79
	ret
                                        ; -- End function
.subsections_via_symbols
