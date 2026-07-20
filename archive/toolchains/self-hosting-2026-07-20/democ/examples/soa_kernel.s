	.build_version macos, 26, 0
	.section	__TEXT,__text,regular,pure_instructions
	.globl	_kernel                         ; -- Begin function kernel
	.p2align	2
_kernel:                                ; @kernel
; %bb.0:                                ; %entry
	ldr	x8, [x0, #8]
	ldr	x9, [x0, #24]
	cmp	x8, x9
	csel	x8, x8, x9, lo
	cbz	x8, LBB0_5
; %bb.1:                                ; %L23.preheader
	mov	x9, #0                          ; =0x0
LBB0_2:                                 ; %L23
                                        ; =>This Inner Loop Header: Depth=1
	ldr	x10, [x0, #8]
	cmp	x9, x10
	b.hs	LBB0_6
; %bb.3:                                ; %L33
                                        ;   in Loop: Header=BB0_2 Depth=1
	ldr	x10, [x0, #24]
	cmp	x9, x10
	b.hs	LBB0_6
; %bb.4:                                ; %L60
                                        ;   in Loop: Header=BB0_2 Depth=1
	ldr	x10, [x0]
	ldr	x11, [x10, x9, lsl #3]
	ldr	x12, [x0, #16]
	ldr	x12, [x12, x9, lsl #3]
	add	x11, x12, x11
	str	x11, [x10, x9, lsl #3]
	add	x9, x9, #1
	cmp	x8, x9
	b.ne	LBB0_2
LBB0_5:                                 ; %L19
	ret
LBB0_6:                                 ; %trap
	brk	#0x1
                                        ; -- End function
.subsections_via_symbols
