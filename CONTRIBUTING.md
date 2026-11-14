# Contributing

Thanks for considering a contribution to Agent-Neuron. The project is in its planning
stage, so the most useful contributions right now are measurements for the N0 spikes and
review of the decisions.

## Ground rules

- **Read the ADRs first.** [docs/adr](docs/adr/README.md) records decisions that are
  expensive to reverse. A change that contradicts one starts with a new ADR, not a pull
  request.
- **The smallest profile is the bar.** Features must work on a two-core machine without a
  GPU.
- **Measure, then claim.** A number in a document or a manifest comes from a recorded
  measurement on a named profile, or it is marked as a budget.
- **Fail loudly.** Never truncate, drop, or degrade silently.
- **Tests first for logic.** Routers, planners, guards, and verifiers are tested against
  fixtures. No test in CI needs a real model, a network, or a GPU.
- **Small, atomic commits.** One concern per commit, Conventional Commits style
  (`feat(scope):`, `fix(scope):`, `docs:`, `test:`, `build:`, `chore:`).
- **No weights, no private data.** Never commit model weights, datasets built from
  private material, real traces, credentials, or hostnames. Fixtures are synthetic or
  come from public sources with their licence recorded.

## Pull request checklist

- [ ] `make check` is green (from milestone N0 on; until then, documentation changes only)
- [ ] New logic has a unit test that failed before the change
- [ ] README, ROADMAP, or docs updated when behaviour or plans changed
- [ ] Any new number names the profile and the measurement it came from
- [ ] No model weights or datasets in the diff
