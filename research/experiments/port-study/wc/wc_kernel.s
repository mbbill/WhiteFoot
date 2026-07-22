	.build_version macos, 26, 0
	.section	__TEXT,__text,regular,pure_instructions
	.globl	_count_lines                    ; -- Begin function count_lines
	.p2align	2
_count_lines:                           ; @count_lines
; %bb.0:                                ; %entry
	cbz	x1, LBB0_3
; %bb.1:                                ; %iter.check
	cmp	x1, #8
	b.hs	LBB0_4
; %bb.2:
	mov	x8, #0                          ; =0x0
	mov	x9, #0                          ; =0x0
	b	LBB0_13
LBB0_3:
	mov	x8, #0                          ; =0x0
	mov	x0, x8
	ret
LBB0_4:                                 ; %vector.main.loop.iter.check
	cmp	x1, #32
	b.hs	LBB0_6
; %bb.5:
	mov	x9, #0                          ; =0x0
	mov	x8, #0                          ; =0x0
	b	LBB0_10
LBB0_6:                                 ; %vector.ph
	movi.2d	v0, #0000000000000000
	movi.16b	v1, #10
	mov	w8, #1                          ; =0x1
	dup.2d	v2, x8
	and	x9, x1, #0xffffffffffffffe0
	movi.2d	v3, #0000000000000000
	add	x8, x0, #16
	movi.2d	v4, #0000000000000000
	mov	x10, x9
	movi.2d	v17, #0000000000000000
	movi.2d	v5, #0000000000000000
	movi.2d	v7, #0000000000000000
	movi.2d	v6, #0000000000000000
	movi.2d	v19, #0000000000000000
	movi.2d	v16, #0000000000000000
	movi.2d	v21, #0000000000000000
	movi.2d	v20, #0000000000000000
	movi.2d	v24, #0000000000000000
	movi.2d	v18, #0000000000000000
	movi.2d	v23, #0000000000000000
	movi.2d	v22, #0000000000000000
	movi.2d	v25, #0000000000000000
LBB0_7:                                 ; %vector.body
                                        ; =>This Inner Loop Header: Depth=1
	ldp	q27, q26, [x8, #-16]
	cmeq.16b	v28, v27, v1
	ushll.8h	v27, v28, #0
	ushll2.8h	v28, v28, #0
	ushll2.4s	v29, v28, #0
	ushll2.2d	v30, v29, #0
	and.16b	v30, v30, v2
	add.2d	v19, v19, v30
	ushll2.4s	v30, v27, #0
	ushll.4s	v28, v28, #0
	ushll.2d	v29, v29, #0
	and.16b	v29, v29, v2
	add.2d	v6, v6, v29
	ushll2.2d	v29, v28, #0
	and.16b	v29, v29, v2
	add.2d	v7, v7, v29
	ushll2.2d	v29, v30, #0
	and.16b	v29, v29, v2
	add.2d	v17, v17, v29
	ushll.4s	v27, v27, #0
	ushll.2d	v28, v28, #0
	and.16b	v28, v28, v2
	add.2d	v5, v5, v28
	ushll.2d	v28, v27, #0
	and.16b	v28, v28, v2
	ushll2.2d	v27, v27, #0
	and.16b	v27, v27, v2
	ushll.2d	v29, v30, #0
	and.16b	v29, v29, v2
	cmeq.16b	v26, v26, v1
	add.2d	v4, v4, v29
	ushll.8h	v29, v26, #0
	ushll2.8h	v26, v26, #0
	add.2d	v3, v3, v27
	ushll2.4s	v27, v26, #0
	add.2d	v0, v0, v28
	ushll2.2d	v28, v27, #0
	and.16b	v28, v28, v2
	add.2d	v25, v25, v28
	ushll2.4s	v28, v29, #0
	ushll.4s	v26, v26, #0
	ushll.2d	v27, v27, #0
	and.16b	v27, v27, v2
	add.2d	v22, v22, v27
	ushll2.2d	v27, v26, #0
	and.16b	v27, v27, v2
	add.2d	v23, v23, v27
	ushll2.2d	v27, v28, #0
	and.16b	v27, v27, v2
	add.2d	v24, v24, v27
	ushll.2d	v26, v26, #0
	and.16b	v26, v26, v2
	add.2d	v18, v18, v26
	ushll.4s	v26, v29, #0
	ushll.2d	v27, v28, #0
	and.16b	v27, v27, v2
	add.2d	v20, v20, v27
	ushll2.2d	v27, v26, #0
	and.16b	v27, v27, v2
	add.2d	v21, v21, v27
	ushll.2d	v26, v26, #0
	and.16b	v26, v26, v2
	add.2d	v16, v16, v26
	add	x8, x8, #32
	subs	x10, x10, #32
	b.ne	LBB0_7
; %bb.8:                                ; %middle.block
	add.2d	v1, v24, v17
	add.2d	v2, v25, v19
	add.2d	v3, v21, v3
	add.2d	v7, v23, v7
	add.2d	v4, v20, v4
	add.2d	v6, v22, v6
	add.2d	v0, v16, v0
	add.2d	v5, v18, v5
	add.2d	v0, v0, v5
	add.2d	v4, v4, v6
	add.2d	v0, v0, v4
	add.2d	v3, v3, v7
	add.2d	v1, v1, v2
	add.2d	v1, v3, v1
	add.2d	v0, v0, v1
	addp.2d	d0, v0
	fmov	x8, d0
	cmp	x1, x9
	b.eq	LBB0_15
; %bb.9:                                ; %vec.epilog.iter.check
	tst	x1, #0x18
	b.eq	LBB0_13
LBB0_10:                                ; %vec.epilog.ph
	mov	x10, x9
	and	x9, x1, #0xfffffffffffffff8
	movi.2d	v0, #0000000000000000
	movi.2d	v1, #0000000000000000
	mov.d	v1[0], x8
	sub	x8, x10, x9
	add	x10, x0, x10
	movi.8b	v2, #10
	mov	w11, #1                         ; =0x1
	dup.2d	v3, x11
	movi.2d	v4, #0000000000000000
	movi.2d	v5, #0000000000000000
LBB0_11:                                ; %vec.epilog.vector.body
                                        ; =>This Inner Loop Header: Depth=1
	ldr	d6, [x10], #8
	cmeq.8b	v6, v6, v2
	ushll.8h	v6, v6, #0
	ushll.4s	v7, v6, #0
	ushll.2d	v16, v7, #0
	and.16b	v16, v16, v3
	ushll2.2d	v7, v7, #0
	and.16b	v7, v7, v3
	ushll2.4s	v6, v6, #0
	ushll.2d	v17, v6, #0
	and.16b	v17, v17, v3
	ushll2.2d	v6, v6, #0
	and.16b	v6, v6, v3
	add.2d	v5, v5, v6
	add.2d	v4, v4, v17
	add.2d	v0, v0, v7
	add.2d	v1, v1, v16
	adds	x8, x8, #8
	b.ne	LBB0_11
; %bb.12:                               ; %vec.epilog.middle.block
	add.2d	v1, v1, v4
	add.2d	v0, v0, v5
	add.2d	v0, v1, v0
	addp.2d	d0, v0
	fmov	x8, d0
	cmp	x1, x9
	b.eq	LBB0_15
LBB0_13:                                ; %L16.preheader
	sub	x10, x1, x9
	add	x9, x0, x9
LBB0_14:                                ; %L16
                                        ; =>This Inner Loop Header: Depth=1
	ldrb	w11, [x9], #1
	cmp	w11, #10
	cinc	x8, x8, eq
	subs	x10, x10, #1
	b.ne	LBB0_14
LBB0_15:                                ; %L7
	mov	x0, x8
	ret
                                        ; -- End function
	.globl	_count_all                      ; -- Begin function count_all
	.p2align	2
_count_all:                             ; @count_all
; %bb.0:                                ; %entry
	cbz	x2, LBB1_3
; %bb.1:                                ; %L18.preheader
	cmp	x2, #8
	b.hs	LBB1_4
; %bb.2:
	mov	x9, #0                          ; =0x0
	mov	x10, #0                         ; =0x0
	mov	x8, #0                          ; =0x0
	mov	w11, #1                         ; =0x1
	b	LBB1_8
LBB1_3:
	mov	x10, #0                         ; =0x0
	mov	x9, #0                          ; =0x0
	b	LBB1_10
LBB1_4:                                 ; %vector.ph
	mov	w9, #1                          ; =0x1
	dup.2d	v20, x9
	movi.2d	v0, #0000000000000000
	movi.2s	v1, #10
	and	x8, x2, #0xfffffffffffffff8
	movi.2s	v2, #247
	add	x10, x1, #4
	movi.2s	v3, #5
	movi.2s	v4, #32
	mov	x11, x8
	movi.2d	v17, #0000000000000000
	movi.2d	v18, #0000000000000000
	movi.2d	v19, #0000000000000000
	movi.2d	v5, #0000000000000000
	movi.2d	v6, #0000000000000000
	movi.2d	v7, #0000000000000000
	movi.2d	v16, #0000000000000000
LBB1_5:                                 ; %vector.body
                                        ; =>This Inner Loop Header: Depth=1
	ldurb	w12, [x10, #-4]
	fmov	s21, w12
	ldurb	w12, [x10, #-3]
	mov.s	v21[1], w12
	ldurb	w12, [x10, #-2]
	fmov	s22, w12
	ldurb	w12, [x10, #-1]
	mov.s	v22[1], w12
	ldrb	w12, [x10]
	fmov	s23, w12
	ldrb	w12, [x10, #1]
	mov.s	v23[1], w12
	ldrb	w12, [x10, #2]
	fmov	s24, w12
	ldrb	w12, [x10, #3]
	mov.s	v24[1], w12
	cmeq.2s	v25, v21, v1
	ushll.2d	v25, v25, #0
	dup.2d	v26, x9
	and.16b	v25, v25, v26
	cmeq.2s	v27, v22, v1
	ushll.2d	v27, v27, #0
	and.16b	v27, v27, v26
	cmeq.2s	v28, v23, v1
	ushll.2d	v28, v28, #0
	and.16b	v28, v28, v26
	cmeq.2s	v29, v24, v1
	ushll.2d	v29, v29, #0
	and.16b	v29, v29, v26
	add.2d	v5, v5, v25
	add.2d	v6, v6, v27
	add.2d	v7, v7, v28
	add.2d	v16, v16, v29
	add.2s	v25, v21, v2
	bic.2s	v25, #1, lsl #8
	add.2s	v27, v22, v2
	bic.2s	v27, #1, lsl #8
	add.2s	v28, v23, v2
	bic.2s	v28, #1, lsl #8
	add.2s	v29, v24, v2
	bic.2s	v29, #1, lsl #8
	cmhi.2s	v25, v3, v25
	cmhi.2s	v27, v3, v27
	cmhi.2s	v28, v3, v28
	cmhi.2s	v29, v3, v29
	cmeq.2s	v21, v21, v4
	cmeq.2s	v22, v22, v4
	cmeq.2s	v23, v23, v4
	cmeq.2s	v24, v24, v4
	orr.8b	v21, v21, v25
	sshll.2d	v25, v21, #0
	orr.8b	v22, v22, v27
	sshll.2d	v27, v22, #0
	orr.8b	v23, v23, v28
	sshll.2d	v28, v23, #0
	orr.8b	v24, v24, v29
	sshll.2d	v29, v24, #0
	ushll.2d	v21, v21, #0
	and.16b	v21, v21, v26
	ushll.2d	v22, v22, #0
	and.16b	v22, v22, v26
	ushll.2d	v23, v23, #0
	and.16b	v23, v23, v26
	ushll.2d	v24, v24, #0
	ext.16b	v30, v20, v21, #8
	and.16b	v20, v24, v26
	ext.16b	v21, v21, v22, #8
	ext.16b	v22, v22, v23, #8
	ext.16b	v23, v23, v20, #8
	bic.16b	v24, v30, v25
	bic.16b	v21, v21, v27
	bic.16b	v22, v22, v28
	bic.16b	v23, v23, v29
	add.2d	v0, v24, v0
	add.2d	v17, v21, v17
	add.2d	v18, v22, v18
	add.2d	v19, v23, v19
	add	x10, x10, #8
	subs	x11, x11, #8
	b.ne	LBB1_5
; %bb.6:                                ; %middle.block
	add.2d	v0, v17, v0
	add.2d	v0, v18, v0
	add.2d	v0, v19, v0
	addp.2d	d0, v0
	fmov	x9, d0
	add.2d	v0, v6, v5
	add.2d	v0, v7, v0
	add.2d	v0, v16, v0
	addp.2d	d0, v0
	fmov	x10, d0
	cmp	x2, x8
	b.eq	LBB1_10
; %bb.7:
	mov.d	x11, v20[1]
LBB1_8:                                 ; %L18.preheader47
	sub	x12, x2, x8
	add	x8, x1, x8
LBB1_9:                                 ; %L18
                                        ; =>This Inner Loop Header: Depth=1
	ldrb	w13, [x8], #1
	cmp	w13, #10
	cinc	x10, x10, eq
	sub	w14, w13, #9
	cmp	w13, #32
	ccmp	w14, #5, #0, ne
	cset	w13, lo
	cmp	w13, #0
	csel	x11, xzr, x11, ne
	add	x9, x11, x9
	mov	x11, x13
	subs	x12, x12, #1
	b.ne	LBB1_9
LBB1_10:                                ; %L9
	stp	x10, x9, [x0]
	str	x2, [x0, #16]
	ret
                                        ; -- End function
.subsections_via_symbols
