EARTHLY ?= earthly

.PHONY: build test lint image clean

build:
	$(EARTHLY) +build

test:
	$(EARTHLY) +test

lint:
	$(EARTHLY) +lint

clean:
	rm -rf target build
