define i64 @multi_call(i64 %x) #0 {
  ret i64 %x
}

define i64 @multi_invoke(i64 %x) #0 {
  ret i64 %x
}

attributes #0 = { nounwind willreturn memory(none) }
