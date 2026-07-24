CARGO := cargo

check: format lint test docs spec
	@echo "== WHITEFOOT COMPILER GATE GREEN =="

format:
	$(CARGO) fmt --all -- --check

lint:
	$(CARGO) clippy --all-targets --locked --offline -- -D warnings

test:
	$(CARGO) test --all-targets --locked --offline

docs:
	RUSTDOCFLAGS="-D warnings" $(CARGO) doc --no-deps --locked --offline

spec:
	$(CARGO) run --bin whitefoot-spec --locked --offline

.PHONY: check format lint test docs spec
