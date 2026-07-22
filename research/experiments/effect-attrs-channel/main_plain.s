	.build_version macos, 26, 0
	.section	__TEXT,__text,regular,pure_instructions
	.globl	_main                           ; -- Begin function main
	.p2align	2
_main:                                  ; @main
; %bb.0:                                ; %entry
	stp	x20, x19, [sp, #-32]!           ; 16-byte Folded Spill
	stp	x29, x30, [sp, #16]             ; 16-byte Folded Spill
	mov	x19, #0                         ; =0x0
	mov	w20, #49664                     ; =0xc200
	movk	w20, #3051, lsl #16
LBB0_1:                                 ; %L8
                                        ; =>This Inner Loop Header: Depth=1
	mov	w0, #42                         ; =0x2a
	bl	_mix
	add	x19, x0, x19
	subs	x20, x20, #1
	b.ne	LBB0_1
; %bb.2:                                ; %L5
	cbz	x19, LBB0_4
; %bb.3:                                ; %L21
	mov	w0, #0                          ; =0x0
	ldp	x29, x30, [sp, #16]             ; 16-byte Folded Reload
	ldp	x20, x19, [sp], #32             ; 16-byte Folded Reload
	ret
LBB0_4:                                 ; %trap
	brk	#0x1
                                        ; -- End function
.subsections_via_symbols
