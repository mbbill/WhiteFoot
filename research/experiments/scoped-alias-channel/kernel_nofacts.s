	.build_version macos, 26, 0
	.section	__TEXT,__text,regular,pure_instructions
	.globl	_kernel                         ; -- Begin function kernel
	.p2align	2
_kernel:                                ; @kernel
; %bb.0:                                ; %entry
	ldr	x8, [x0, #8]
	ldr	x9, [x0, #24]
	ldr	x10, [x0, #40]
	ldr	x11, [x0, #56]
	ldr	x12, [x0, #72]
	ldr	x13, [x0, #88]
	ldr	x14, [x0, #104]
	ldr	x15, [x0, #120]
	cmp	x8, x9
	csel	x8, x8, x9, lo
	cmp	x8, x10
	csel	x8, x8, x10, lo
	cmp	x8, x11
	csel	x8, x8, x11, lo
	cmp	x8, x12
	csel	x8, x8, x12, lo
	cmp	x8, x13
	csel	x8, x8, x13, lo
	cmp	x8, x14
	csel	x8, x8, x14, lo
	cmp	x8, x15
	csel	x8, x8, x15, lo
	cbz	x8, LBB0_11
; %bb.1:                                ; %L83.preheader
	mov	x9, #0                          ; =0x0
LBB0_2:                                 ; %L83
                                        ; =>This Inner Loop Header: Depth=1
	ldr	x10, [x0, #8]
	cmp	x9, x10
	b.hs	LBB0_12
; %bb.3:                                ; %L93
                                        ;   in Loop: Header=BB0_2 Depth=1
	ldr	x10, [x0, #40]
	cmp	x9, x10
	b.hs	LBB0_12
; %bb.4:                                ; %L104
                                        ;   in Loop: Header=BB0_2 Depth=1
	ldr	x10, [x0, #56]
	cmp	x9, x10
	b.hs	LBB0_12
; %bb.5:                                ; %L115
                                        ;   in Loop: Header=BB0_2 Depth=1
	ldr	x10, [x0, #72]
	cmp	x9, x10
	b.hs	LBB0_12
; %bb.6:                                ; %L126
                                        ;   in Loop: Header=BB0_2 Depth=1
	ldr	x10, [x0, #88]
	cmp	x9, x10
	b.hs	LBB0_12
; %bb.7:                                ; %L165
                                        ;   in Loop: Header=BB0_2 Depth=1
	ldr	x12, [x0]
	ldr	x13, [x12, x9, lsl #3]
	ldr	x10, [x0, #32]
	ldr	x14, [x10, x9, lsl #3]
	ldr	x10, [x0, #48]
	ldr	x15, [x10, x9, lsl #3]
	ldr	x10, [x0, #64]
	ldr	x10, [x10, x9, lsl #3]
	ldr	x11, [x0, #80]
	ldr	x11, [x11, x9, lsl #3]
	add	x13, x14, x13
	add	x14, x15, x10
	add	x13, x13, x14
	add	x13, x13, x11
	str	x13, [x12, x9, lsl #3]
	ldr	x12, [x0, #24]
	cmp	x9, x12
	b.hs	LBB0_12
; %bb.8:                                ; %L174
                                        ;   in Loop: Header=BB0_2 Depth=1
	ldr	x12, [x0, #104]
	cmp	x9, x12
	b.hs	LBB0_12
; %bb.9:                                ; %L185
                                        ;   in Loop: Header=BB0_2 Depth=1
	ldr	x12, [x0, #120]
	cmp	x9, x12
	b.hs	LBB0_12
; %bb.10:                               ; %L224
                                        ;   in Loop: Header=BB0_2 Depth=1
	ldr	x12, [x0, #16]
	ldr	x13, [x12, x9, lsl #3]
	ldr	x14, [x0, #96]
	ldr	x14, [x14, x9, lsl #3]
	ldr	x15, [x0, #112]
	ldr	x15, [x15, x9, lsl #3]
	add	x10, x11, x10
	add	x11, x13, x14
	add	x10, x10, x11
	add	x10, x10, x15
	str	x10, [x12, x9, lsl #3]
	add	x9, x9, #1
	cmp	x8, x9
	b.ne	LBB0_2
LBB0_11:                                ; %L79
	ret
LBB0_12:                                ; %trap
	brk	#0x1
                                        ; -- End function
.subsections_via_symbols
