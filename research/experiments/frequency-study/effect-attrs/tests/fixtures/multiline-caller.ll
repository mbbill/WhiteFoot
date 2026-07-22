; Valid LLVM probe: declarations, call, and invoke deliberately span lines.

declare i32 @__gxx_personality_v0(...)

declare i64 @multi_call(
  i64
)
nounwind
willreturn
memory(none)

declare i64 @multi_invoke(
  i64
)

define i64 @multiline_caller(i64 %x) personality ptr @__gxx_personality_v0 {
entry:
  %called = call i64 @multi_call(
  i64 %x
  )
  nounwind
  willreturn
  memory(none)
  %invoked = invoke i64 @multi_invoke(
  i64 %called
  )
  nounwind
  willreturn
  memory(none)
  to label %normal unwind label %cleanup

normal:
  ret i64 %invoked

cleanup:
  %landing = landingpad { ptr, i32 }
    cleanup
  resume { ptr, i32 } %landing
}

; LLVM's callbr form is necessarily inline asm. It must be accumulated as one
; instruction and then rejected as an inline-asm callee.
define void @multiline_callbr() {
entry:
  callbr void asm sideeffect "", "!i"()
    to label %normal [label %indirect]

normal:
  ret void

indirect:
  ret void
}
