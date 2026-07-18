PYTHON ?= python3
CARGO ?= cargo
CARGO_TARGET_DIR ?= /tmp/whitefoot-frequency-reassociation-target

.PHONY: check pilot bounds alias effect reassociation clean

check: pilot bounds alias effect reassociation

pilot:
	$(PYTHON) -B -m unittest discover -s tests -p 'test_*.py' -v

bounds:
	$(PYTHON) -B -m unittest discover -s bounds-ir -p 'test_*.py' -v

alias:
	$(PYTHON) -B -m unittest discover -s alias-versioning -p 'test_*.py' -v

effect:
	$(PYTHON) -B -m unittest discover -s effect-attrs/tests -p 'test_*.py' -v

reassociation:
	CARGO_TARGET_DIR=$(CARGO_TARGET_DIR) $(CARGO) test --offline --locked --manifest-path reassociation/Cargo.toml
	CARGO_TARGET_DIR=$(CARGO_TARGET_DIR) $(CARGO) clippy --offline --locked --manifest-path reassociation/Cargo.toml -- -D warnings
	$(CARGO) fmt --manifest-path reassociation/Cargo.toml -- --check

clean:
	CARGO_TARGET_DIR=$(CARGO_TARGET_DIR) $(CARGO) clean --manifest-path reassociation/Cargo.toml
