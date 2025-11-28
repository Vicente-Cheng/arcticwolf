EARTHLY ?= earthly

.PHONY: build test lint image clean

build:
	$(EARTHLY) +build

test:
	$(EARTHLY) +test

lint:
	$(EARTHLY) +lint

image:
	$(EARTHLY) +dev-image

clean:
	rm -rf target build
