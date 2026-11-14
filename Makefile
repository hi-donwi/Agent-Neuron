.PHONY: build install test race vet fmt fmt-check tidy-check cross static-check vulncheck smoke check lab-check clean

BINARY  := neuron
PKG     := github.com/hi-donwi/Agent-Neuron
VERSION ?= 0.0.0-dev
COMMIT  ?= $(shell git rev-parse --short=12 HEAD 2>/dev/null || echo unknown)
DATE    ?= $(shell date -u +%Y-%m-%dT%H:%M:%SZ)

LDFLAGS := -s -w \
           -X $(PKG)/internal/buildinfo.Version=$(VERSION) \
           -X $(PKG)/internal/buildinfo.Commit=$(COMMIT) \
           -X $(PKG)/internal/buildinfo.Date=$(DATE)

# neuron ships as one static binary per platform (ADR-0005). CGO stays off so a
# dependency that needs a C toolchain fails the build here, not on a user's machine.
export CGO_ENABLED := 0

# Pinned: govulncheck is a security gate; a floating @latest would let the scanner
# itself change without review. The pin moves with the newest Go release CI uses.
GOVULNCHECK := golang.org/x/vuln/cmd/govulncheck@v1.8.0

PLATFORMS := darwin/arm64 darwin/amd64 linux/amd64 linux/arm64 windows/amd64

build:
	go build -trimpath -ldflags '$(LDFLAGS)' -o bin/$(BINARY) ./cmd/neuron

install:
	go install -trimpath -ldflags '$(LDFLAGS)' ./cmd/neuron

test:
	go test -count=1 ./...

# -race needs cgo; it is the only target that turns it back on.
race:
	CGO_ENABLED=1 go test -race -count=1 ./...

vet:
	go vet ./...

fmt:
	gofmt -w .

fmt-check:
	@unformatted="$$(gofmt -l .)"; \
	if [ -n "$$unformatted" ]; then echo "Not gofmt-formatted:"; echo "$$unformatted"; exit 1; fi

tidy-check:
	go mod tidy
	git diff --exit-code -- go.mod go.sum

cross:
	@for p in $(PLATFORMS); do \
		os=$${p%/*}; arch=$${p#*/}; ext=; [ "$$os" = windows ] && ext=.exe; \
		echo "-> $$os/$$arch"; \
		GOOS=$$os GOARCH=$$arch go build -trimpath -ldflags '$(LDFLAGS)' \
			-o bin/$(BINARY)-$$os-$$arch$$ext ./cmd/neuron || exit 1; \
	done

static-check: cross
	file bin/$(BINARY)-linux-amd64 | grep -q "statically linked"
	file bin/$(BINARY)-linux-arm64 | grep -q "statically linked"

vulncheck:
	go run $(GOVULNCHECK) ./...

smoke: build
	./bin/$(BINARY) version
	./bin/$(BINARY) version --json

# The Go gate: the same steps CI runs on every push, in the same order. It needs
# only a Go toolchain (and a C compiler for the race detector).
check: fmt-check tidy-check vet race smoke

# The lab gate: Python under uv with a lock file (ADR-0005). --locked fails when
# uv.lock no longer matches pyproject.toml instead of rewriting it. A machine that
# only builds or serves neurons never needs to run this.
lab-check:
	cd lab && uv sync --locked
	cd lab && uv run --locked ruff check .
	cd lab && uv run --locked ruff format --check .
	cd lab && uv run --locked pytest -q

clean:
	rm -rf bin dist coverage.out
