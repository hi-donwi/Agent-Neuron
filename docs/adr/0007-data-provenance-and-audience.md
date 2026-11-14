# ADR-0007: Provenance and audience decide what a neuron may learn from and where it may go

- **Date:** 2026-11-14
- **Status:** Proposed
- **Deciders:** Doni Wicaksono

## Context

A trained model carries its training data with it in a form that cannot be inspected or
removed afterwards. This repository is public and is meant to publish packs. The same
tool will also be used on private documents and on traces of real work, which must not
leave the machine they were created on.

Base models and documents come with licences that bind what is built from them.

## Decision

Every training example and every knowledge chunk records its source, its licence, and its
audience: `public` or `private`. A dataset's audience is the most restrictive audience
among its examples, and a neuron inherits the audience of its dataset and knowledge pack.

- A `private` neuron cannot be exported for publication. The lab refuses, and the
  manifest says why.
- Traces of real use are opt-in per source, redacted before they are stored, and
  `private` by default.
- Fixtures, datasets, and packs committed to or released from this repository are built
  only from public sources or synthetic data.
- The base model's licence, as written on its model card, is recorded in every manifest
  and carried into the generated model card. A base whose licence does not allow the
  intended use is not added to the catalogue.
- An example without provenance is rejected at build time.

## Consequences

### Positive
- Private material cannot reach a published artifact through an oversight; the tool
  blocks it.
- Every published neuron can state exactly what it was built from.
- Licence obligations are visible at the point of use.

### Negative
- All data must be tagged, including synthetic data, which adds friction to quick
  experiments.
- One private example makes a whole dataset private; mixed datasets must be split to
  publish anything.
- Redaction is imperfect, so private traces stay private regardless of redaction.

### Neutral
- A finer audience model (for example per organisation) can be added later without
  changing this rule.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Rely on the operator to keep private data out of public neurons | One mistake is permanent once weights are published |
| Allow redacted private traces in public neurons | Redaction cannot be proven complete, and a model can memorise what remains |
| Track provenance per dataset only | A single unlabelled example cannot be found later |
| Publish no weights at all | Removes most of the value of a public project; public and synthetic data are enough for the first domains |
