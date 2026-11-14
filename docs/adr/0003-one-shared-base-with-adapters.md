# ADR-0003: One shared base model with an adapter per sub-domain

- **Date:** 2026-11-14
- **Status:** Proposed
- **Deciders:** Doni Wicaksono

## Context

The plan is many specialists, split by domain and sub-domain. If each one is a complete
model, memory decides how many can exist. Agent-Brain measured a 0.6B model at four bits
at about 800 MB resident with a 4k context (Agent-Brain ADR-0002). Ten such specialists
do not fit an 8 GB machine, and loading and unloading them per request costs seconds
each time.

Low-rank adapters change a model's behaviour with a small set of extra weights, typically
a few tens of megabytes, and are also much cheaper to train than a full model.

## Decision

Each profile keeps one base model resident. A generative neuron is a low-rank adapter
over that base. Serving a different sub-domain selects a different adapter; it does not
load a different model.

An adapter is a build output. Its sources are the spec and the dataset, so when the base
changes, every adapter is rebuilt from them by the pipeline.

A neuron may ship as a fused, quantized model only as a declared exception, when
measurement shows an adapter is insufficient for its task or that the engine cannot
switch adapters reliably. The manifest states it and the profile's memory budget
accounts for it. Neurons that are not generative (`route`, `extract`, `verify`) are
separate small artifacts and unaffected.

## Consequences

### Positive
- Memory grows by tens of megabytes per sub-domain instead of hundreds.
- Training an adapter is feasible on the 8 GB target, where training a full model is not.
- Adding a sub-domain does not change any existing neuron.

### Negative
- Every specialist inherits the base model's limits and its licence.
- Changing the base invalidates every adapter; all of them must be retrained and
  re-evaluated.
- Switching adapters may discard the engine's prompt cache, and requests that name
  different adapters cannot be batched together. Spike C measures both.
- Neurons that need two different bases double the resident memory.

### Neutral
- The adapter rank, the target modules, and the base per profile are chosen from Spikes A
  and B, not fixed by this ADR.

## Alternatives considered

| Option | Why rejected |
|---|---|
| A fully fine-tuned small model per sub-domain | Memory and disk grow linearly with sub-domains; training a full model exceeds the 8 GB target |
| One general model steered only by prompts | Tiny models follow long instructions poorly; the prompt tokens are paid on every request |
| A mixture-of-experts architecture trained from scratch | Needs pretraining, which is out of scope and out of reach for the target hardware |
| Soft prompts or prefix tuning | The serving engine has an established path for low-rank adapters and none we could confirm for soft prompts; not evaluated further |
