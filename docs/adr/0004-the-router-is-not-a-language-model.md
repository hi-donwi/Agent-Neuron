# ADR-0004: The router is not a language model

- **Date:** 2026-11-14
- **Status:** Proposed
- **Deciders:** Doni Wicaksono

## Context

Every request passes through the router, so its latency and memory are paid every time,
and its mistakes send a request to a specialist that cannot answer it. A common design
asks a language model which specialist to use. On the target hardware that costs a model
load, hundreds of milliseconds to seconds, and a tiny model is an unreliable judge.

Choosing among known labels is classification. Classifiers over text embeddings are small
and fast, and static embeddings (a token table and a mean, with no transformer layers)
make the embedding step a lookup. One static embedding family's own benchmark puts it at
roughly four fifths of a small transformer encoder's retrieval quality at a small
fraction of the CPU cost. That is a vendor figure for retrieval, not a measurement of
routing in these domains, which is not known until Spike D.

The set of specialists grows over time. A flat classifier over all labels must be
retrained whenever any domain adds one.

## Decision

The router is a hierarchical classifier, not a generative model. It decides domain, then
sub-domain, then task, with one small head per level and per domain. It runs in three
tiers: explicit rules declared by a pack, nearest label centroid over static embeddings
for labels with few examples, and a trained head for established labels.

Confidence is calibrated on held-out data that includes out-of-domain inputs. Each level
has an abstention threshold, and "none of these" is a normal answer. The router may
return a domain and stop when the sub-domain is uncertain.

Adding a sub-domain retrains only the affected head.

## Consequences

### Positive
- Routing costs milliseconds and no model load, on any profile.
- Adding or changing one domain does not disturb the others.
- Abstention gives the system an honest way to say it has no specialist, and gives the
  growth loop its signal.

### Negative
- A classifier knows only the labels it was trained on; it cannot reason about a request
  that combines two domains. Such requests abstain or take the first domain.
- Static embeddings miss distinctions that depend on word order or negation. A domain
  where that matters needs a small transformer encoder for its head, served by the
  engine, at a latency and memory cost.
- Calibration needs out-of-domain data, which must be collected and maintained.

### Neutral
- Whether static embeddings are enough, and for which domains, is the question Spike D
  answers.

## Alternatives considered

| Option | Why rejected |
|---|---|
| A language model as the router | A model load and seconds of latency on every request; unreliable at this size |
| One flat classifier over all labels | Every new sub-domain retrains and re-evaluates everything |
| Nearest-neighbour routing with no held-out OOD calibration | A cosine score is not a probability. Spike D found a held-out threshold could control far-OOD false accepts for centroids, but did not measure k-nearest-neighbour density or broader domains; calibration remains required |
| Rules only | Does not generalise to paraphrases; kept as the first tier for unambiguous cases |
| Let the client choose the specialist | Still allowed (`model: <pack>/<neuron>`), but most clients cannot know the catalogue |
