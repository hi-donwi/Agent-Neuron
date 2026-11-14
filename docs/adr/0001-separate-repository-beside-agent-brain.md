# ADR-0001: A separate repository beside Agent-Brain; they meet at the OpenAI-compatible API

- **Date:** 2026-11-14
- **Status:** Proposed
- **Deciders:** Doni Wicaksono

## Context

The suite already has a local AI platform. Agent-Brain is a gateway: provider accounts,
routing between accounts, local engines, retrieval, a skills runtime, traces, evaluation,
and a skill forge. Building, packaging, and training small models could be added to it as
a feature, or live in a repository of its own.

Agent-Brain has decided three things that this work would contradict:

- one static Go binary without cgo (Agent-Brain ADR-0001);
- engines run models, Agent-Brain never loads weights or runs them in-process
  (Agent-Brain ADR-0002);
- fine-tuning and adapter training are listed under "Not planned for v1" in its roadmap.

Training needs the Python machine-learning toolchain. Model weights and datasets have
their own licences, sizes, audiences, and release cadence, none of which match a gateway
binary.

## Decision

Agent-Neuron is its own repository. It owns small models: their format, the router that
chooses between them, the runtime that serves them on a CPU, and the lab that trains them.

It is a backend, not a second gateway. It has no provider accounts, no skills runtime, no
agent loop, and no console. Agent-Brain reaches `neuron serve` through its existing
`local` account type, over the OpenAI-compatible chat API on loopback. The two also meet
at two optional seams: Agent-Brain as the teacher endpoint for the lab, and Agent-Brain
traces as an opt-in data source.

## Consequences

### Positive
- No Agent-Brain decision is reversed, and Agent-Brain needs no change for Agent-Neuron
  to be useful.
- A low-end device can run `neuron serve` alone, with nothing else installed.
- Weights, datasets, and their licences are handled by a project designed for them.

### Negative
- One more repository to maintain, release, and keep in CI.
- Two processes on machines that run both, and one more hop for a request.
- Some concepts exist twice in a small form: a loopback API with a bearer token, a
  retrieval store. They must stay small here and not grow into gateway features.

### Neutral
- A later Agent-Brain ADR may add packs to its catalogue, or import the router as a Go
  package. Neither is required by this decision.

## Alternatives considered

| Option | Why rejected |
|---|---|
| A feature inside Agent-Brain | Reverses its ADR-0001 and ADR-0002 and a stated roadmap exclusion; brings Python and model weights into a static Go gateway |
| A feature inside Agent-Control | It is the agent host and UI, written in TypeScript; it must not call or run models directly |
| A private research project first | Nothing reusable would exist for the public suite; the first domains use only public data, so there is no reason to keep it private |
| One monorepo for the whole suite | Contradicts the existing one-repository-per-component model and its separate licences |
