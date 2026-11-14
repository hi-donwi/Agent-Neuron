# ADR-0005: Pure-Go runtime, Python lab, external inference engine

- **Date:** 2026-11-14
- **Status:** Proposed
- **Deciders:** Doni Wicaksono

## Context

The project has two sides with opposite needs.

The serving side must run on a low-end device with nothing to set up: no interpreter, no
package manager, no shared libraries. The sibling Go tools in the suite ship as one
static binary for that reason, and Agent-Brain keeps cgo off so its builds stay static
and cross-compile cleanly.

The training side depends on the Python machine-learning ecosystem. There is no practical
way to train adapters or distil embeddings without it.

Running a generative model efficiently on a CPU is a hard, fast-moving problem that
dedicated engines already solve.

## Decision

The runtime is one Go binary, CGO off, statically linked. It contains the router, the
retrieval store (pure-Go SQLite with FTS5), the composer, the verifiers, the API, and the
engine supervisor. Router inference is implemented directly in Go: a static embedding
table lookup, pooling, and a small head. Its artifacts use a simple documented tensor
format the lab exports.

Generation is done by a pinned external `llama-server` process over HTTP on loopback. The
runtime never loads generative weights and implements no inference kernels.

The lab is a Python package with locked dependencies, managed by uv. The binary calls it
through a documented, versioned JSON contract. A machine that only serves neurons needs
no Python.

## Consequences

### Positive
- A serving device needs two executables and the pack files, nothing else.
- Agent-Brain could later import the router as a Go package without breaking its own
  no-cgo rule.
- Engine improvements arrive by raising a pinned version.

### Negative
- Two languages in one repository, with two toolchains in CI.
- The router is limited to model families simple enough to run in pure Go. A domain that
  needs a transformer encoder for routing must serve it through the engine.
- Go and Python implementations of the same arithmetic must be kept in agreement by
  parity fixtures.
- The engine is a separate binary to install, pin, and supervise, and its behaviour
  (adapter switching, caching, constrained decoding) is not ours to control.

### Neutral
- Whether pure-Go router inference is accurate enough is decided by Spikes D and E. If it
  is not, this ADR is amended before N1, not worked around.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Everything in Python | Serving needs an interpreter and several hundred megabytes of packages on the device, and starts slowly |
| Go with cgo bindings to an ML runtime | Breaks static builds and cross-compilation; ties releases to a native library per platform |
| In-process bindings to the inference library | Same cgo cost, plus owning memory management and crashes of the model inside the runtime |
| A third language for the runtime | No sibling project uses one; nothing here needs it |
| Training implemented outside Python | Not practical with current tooling |
