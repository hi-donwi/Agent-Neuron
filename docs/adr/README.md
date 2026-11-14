# Architecture decision records

Decisions that are expensive to reverse. A change that contradicts one starts with a new
ADR that supersedes it, not with a pull request. Old ADRs are never deleted.

All ADRs below are **Proposed**. Milestone N0 measures the assumptions they rest on; each
one is then Accepted, amended, or superseded (see [ROADMAP.md](../../ROADMAP.md)).

| ADR | Decision | Status | Informed by |
|---|---|---|---|
| [0001](0001-separate-repository-beside-agent-brain.md) | A separate repository beside Agent-Brain; they meet at the OpenAI-compatible API | Proposed | - |
| [0002](0002-knowledge-in-retrieval-behaviour-in-weights.md) | Knowledge lives in retrieval, behaviour lives in weights | Proposed | Spike F |
| [0003](0003-one-shared-base-with-adapters.md) | One shared base model with an adapter per sub-domain | Proposed | Spikes A, B, C |
| [0004](0004-the-router-is-not-a-language-model.md) | The router is not a language model | Proposed | Spike D |
| [0005](0005-pure-go-runtime-python-lab-external-engine.md) | Pure-Go runtime, Python lab, external inference engine | Proposed | Spikes D, E |
| [0006](0006-agent-operable-training-human-promotion.md) | Training is a declarative pipeline agents can operate; a human promotes | Proposed | - |
| [0007](0007-data-provenance-and-audience.md) | Provenance and audience decide what a neuron may learn from and where it may go | Proposed | - |
| [0008](0008-resource-budgets-are-part-of-the-contract.md) | Resource budgets are part of the contract | Proposed | Spikes A, B |
