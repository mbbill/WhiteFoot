define weak_odr i64 @ambiguous(i64 %x) #0 {
  ret i64 %x
}

define internal i64 @external_with_internal_collision(i64 %x) #0 {
  ret i64 %x
}

attributes #0 = { nounwind willreturn memory(none) }
