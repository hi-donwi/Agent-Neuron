# evals

Evaluation sets and the fixtures that tests and spikes measure against. Nothing is here
yet: the first sets arrive with the N0 spikes and with `evals/retrieval` in N3
([ROADMAP](../ROADMAP.md)).

Rules for anything added to this directory:

- **Public or synthetic sources only.** Each set records where its data came from and
  under which licence. No private material, real traces, credentials, or hostnames
  ([ADR-0007](../docs/adr/0007-data-provenance-and-audience.md)).
- **Frozen before training.** An evaluation set is built, reviewed by sampling, frozen,
  and hashed before any training run uses it, and it does not change afterwards
  ([ADR-0006](../docs/adr/0006-agent-operable-training-human-promotion.md)).
- **Small enough for git.** Model weights and large datasets never enter the repository.
- **No model, network, or GPU in CI.** Tests that read these sets run against fixtures.
