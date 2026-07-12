; Synthetic caller module. Records are direct IR calls, not bare declarations.

declare i64 @pure_total(i64)
declare i64 @read_target(ptr readonly) #0
declare i64 @already_visible(i64) #1
declare i64 @non_total(i64)
declare i64 @unresolved_native(i64)
declare i64 @ambiguous(i64)
declare i64 @legacy_pure(i64)
declare i64 @"quoted target"(i64)
declare i64 @private_only(i64)
declare i64 @external_with_internal_collision(i64)
declare i64 @spec_only(i64)
declare i64 @unsupported_definition(i64)
declare i64 @unsupported_caller(i64)
declare i64 @explicit_write_caller(i64)
declare i64 @fake_quoted_attrs(i64) #4

define i64 @caller(ptr %p) {
entry:
  %a = call i64 @pure_total(i64 1) #10
  %b = call i64 @pure_total(i64 2)
  %c = call i64 @read_target(ptr %p) #11
  %d = call i64 @read_target(ptr %p)
  %e = call i64 @already_visible(i64 3)
  %f = call i64 @non_total(i64 4)
  %g = call i64 @unresolved_native(i64 5)
  %h = call i64 @ambiguous(i64 6)
  %i = call i64 @legacy_pure(i64 7)
  %j = call i64 @"quoted target"(i64 8)
  %k = call i64 @private_only(i64 9)
  %l = call i64 @external_with_internal_collision(i64 10)
  %m = call i64 @spec_only(i64 11)
  %n = call i64 @unsupported_definition(i64 12)
  %o = call i64 @unsupported_caller(i64 13) #12
  %p2 = call i64 @explicit_write_caller(i64 14) #13
  %q = call i64 @fake_quoted_attrs(i64 15)
  %indirect = call i64 %p(i64 16)
  ret i64 %q
}

attributes #0 = { nounwind }
attributes #1 = { nounwind willreturn memory(none) }
attributes #4 = { "fake"="memory(none) nounwind willreturn #99 }" }
attributes #10 = { nounwind willreturn memory(none) "noise"="} memory(write)" }
attributes #11 = { willreturn memory(read, argmem: none) }
attributes #12 = { memory(argmem: frobnicate) }
attributes #13 = { nounwind willreturn memory(write) }
