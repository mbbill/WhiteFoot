declare i64 @type_mismatch(i64)
declare fastcc i64 @convention_mismatch(i64)
declare i64 @address_mismatch(i64) addrspace(1)
declare x86_amx @unsupported_signature()
declare i64 @call_mismatch(i64)

define i64 @abi_caller(i64 %x) {
entry:
  %a = call i64 @type_mismatch(i64 %x)
  %b = call fastcc i64 @convention_mismatch(i64 %a)
  %c = call i64 @address_mismatch(i64 %b)
  %d = call x86_amx @unsupported_signature()
  %e = call i32 @call_mismatch(i32 1)
  ret i64 %c
}
