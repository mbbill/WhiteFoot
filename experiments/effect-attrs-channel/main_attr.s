	.build_version macos, 26, 0
	.section	__TEXT,__text,regular,pure_instructions
	.globl	_main                           ; -- Begin function main
	.p2align	2
_main:                                  ; @main
; %bb.0:                                ; %entry
	stp	x29, x30, [sp, #-16]!           ; 16-byte Folded Spill
	mov	w0, #42                         ; =0x2a
	bl	_mix
	mov	w8, #49664                      ; =0xc200
	movk	w8, #3051, lsl #16
	mul	x8, x0, x8
	cbz	x8, LBB0_2
; %bb.1:                                ; %L21
	mov	w0, #0                          ; =0x0
	ldp	x29, x30, [sp], #16             ; 16-byte Folded Reload
	ret
LBB0_2:                                 ; %trap
	brk	#0x1
                                        ; -- End function
.subsections_via_symbols
