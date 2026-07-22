define i32 @type_mismatch(i64 %x) #0 {
  ret i32 0
}

define i64 @convention_mismatch(i64 %x) #0 {
  ret i64 %x
}

define i64 @address_mismatch(i64 %x) #0 {
  ret i64 %x
}

define x86_amx @unsupported_signature() #0 {
  ret x86_amx zeroinitializer
}

define i64 @call_mismatch(i64 %x) #0 {
  ret i64 %x
}

attributes #0 = { nounwind willreturn memory(none) }
