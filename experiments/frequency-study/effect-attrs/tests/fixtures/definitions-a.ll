define i64 @pure_total(i64 %x) #0 {
  ret i64 %x
}

define i64 @read_target(ptr %p) #1 {
  %x = load i64, ptr %p
  ret i64 %x
}

define i64 @already_visible(i64 %x) #0 {
  ret i64 %x
}

define i64 @non_total(i64 %x) #2 {
  ret i64 %x
}

define i64 @ambiguous(i64 %x) #0 {
  ret i64 %x
}

define i64 @legacy_pure(i64 %x) #3 {
  ret i64 %x
}

define i64 @"quoted target"(i64 %x) nounwind speculatable memory(none) {
  ret i64 %x
}

define internal i64 @private_only(i64 %x) #0 {
  ret i64 %x
}

define i64 @external_with_internal_collision(i64 %x) #0 {
  ret i64 %x
}

define i64 @spec_only(i64 %x) #4 {
  ret i64 %x
}

define i64 @unsupported_definition(i64 %x) #5 {
  ret i64 %x
}

define i64 @unsupported_caller(i64 %x) #0 {
  ret i64 %x
}

define i64 @explicit_write_caller(i64 %x) #0 {
  ret i64 %x
}

define i64 @fake_quoted_attrs(i64 %x) #6 {
  ret i64 %x
}

attributes #0 = { mustprogress nounwind willreturn memory(none) }
attributes #1 = { nounwind willreturn memory(read, argmem: none) }
attributes #2 = { nounwind memory(none) }
attributes #3 = { nounwind willreturn readnone }
attributes #4 = { nounwind speculatable memory(none) }
attributes #5 = { nounwind willreturn memory(unknownmem: read) }
attributes #6 = { nounwind willreturn memory(none) "target-cpu"="} memory(write)" }
