	.build_version macos, 26, 0
	.section	__TEXT,__text,regular,pure_instructions
	.globl	_satadd                         ; -- Begin function satadd
	.p2align	2
_satadd:                                ; @satadd
; %bb.0:                                ; %entry
	adds	x8, x0, x1
	csinv	x0, x8, xzr, lo
	ret
                                        ; -- End function
	.globl	_reduce                         ; -- Begin function reduce
	.p2align	2
_reduce:                                ; @reduce
; %bb.0:                                ; %entry
	cmp	x1, #4
	b.hs	LBB1_2
; %bb.1:
	mov	x8, #0                          ; =0x0
	mov	x10, #0                         ; =0x0
	subs	x9, x1, x10
	b.hi	LBB1_5
	b	LBB1_7
LBB1_2:                                 ; %L33.preheader
	mov	x8, #0                          ; =0x0
	mov	x10, #0                         ; =0x0
	mov	x9, #0                          ; =0x0
	mov	x11, #0                         ; =0x0
	sub	x12, x1, #3
	add	x13, x0, #16
	mov	w14, #1                         ; =0x1
LBB1_3:                                 ; %L33
                                        ; =>This Inner Loop Header: Depth=1
	ldp	x15, x16, [x13, #-16]
	adds	x8, x8, x15
	csinv	x8, x8, xzr, lo
	adds	x10, x10, x16
	csinv	x10, x10, xzr, lo
	ldp	x15, x16, [x13], #32
	adds	x9, x9, x15
	csinv	x9, x9, xzr, lo
	adds	x11, x11, x16
	csinv	x11, x11, xzr, lo
	add	x15, x14, #4
	add	x16, x14, #3
	mov	x14, x15
	cmp	x16, x12
	b.lo	LBB1_3
; %bb.4:                                ; %L29
	adds	x8, x8, x10
	csinv	x8, x8, xzr, lo
	adds	x9, x9, x11
	csinv	x9, x9, xzr, lo
	adds	x8, x8, x9
	csinv	x8, x8, xzr, lo
	sub	x10, x15, #1
	subs	x9, x1, x10
	b.ls	LBB1_7
LBB1_5:                                 ; %L119.preheader
	add	x10, x0, x10, lsl #3
LBB1_6:                                 ; %L119
                                        ; =>This Inner Loop Header: Depth=1
	ldr	x11, [x10], #8
	adds	x8, x8, x11
	csinv	x8, x8, xzr, lo
	subs	x9, x9, #1
	b.ne	LBB1_6
LBB1_7:                                 ; %L99
	mov	x0, x8
	ret
                                        ; -- End function
	.globl	_main                           ; -- Begin function main
	.p2align	2
_main:                                  ; @main
; %bb.0:                                ; %entry
	stp	x20, x19, [sp, #-32]!           ; 16-byte Folded Spill
	stp	x29, x30, [sp, #16]             ; 16-byte Folded Spill
	mov	w0, #8000                       ; =0x1f40
	bl	_malloc
	mov	x19, x0
Lloh0:
	adrp	x1, l_.memset_pattern@PAGE
Lloh1:
	add	x1, x1, l_.memset_pattern@PAGEOFF
	mov	w2, #8000                       ; =0x1f40
	bl	_memset_pattern16
	mov	x8, #0                          ; =0x0
	mov	x10, #0                         ; =0x0
	mov	x9, #0                          ; =0x0
	mov	x11, #0                         ; =0x0
	add	x12, x19, #16
	mov	x13, #-4                        ; =0xfffffffffffffffc
LBB2_1:                                 ; %L33.i
                                        ; =>This Inner Loop Header: Depth=1
	ldp	x14, x15, [x12, #-16]
	adds	x8, x8, x14
	csinv	x8, x8, xzr, lo
	adds	x10, x10, x15
	csinv	x10, x10, xzr, lo
	ldp	x14, x15, [x12], #32
	adds	x9, x9, x14
	csinv	x9, x9, xzr, lo
	adds	x11, x11, x15
	csinv	x11, x11, xzr, lo
	add	x13, x13, #4
	cmp	x13, #993
	b.lo	LBB2_1
; %bb.2:                                ; %reduce.exit
	adds	x8, x8, x10
	csinv	x8, x8, xzr, lo
	adds	x9, x9, x11
	csinv	x9, x9, xzr, lo
	adds	x8, x8, x9
	csinv	x8, x8, xzr, lo
	cmp	x8, #3000
	b.ne	LBB2_4
; %bb.3:                                ; %L20
	mov	w0, #0                          ; =0x0
	ldp	x29, x30, [sp, #16]             ; 16-byte Folded Reload
	ldp	x20, x19, [sp], #32             ; 16-byte Folded Reload
	ret
LBB2_4:                                 ; %trap
	brk	#0x1
	.loh AdrpAdd	Lloh0, Lloh1
                                        ; -- End function
	.section	__TEXT,__literal16,16byte_literals
	.p2align	4, 0x0                          ; @.memset_pattern
l_.memset_pattern:
	.quad	3                               ; 0x3
	.quad	3                               ; 0x3

.subsections_via_symbols
