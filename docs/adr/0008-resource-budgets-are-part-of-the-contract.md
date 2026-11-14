# ADR-0008: Resource budgets are part of the contract

- **Date:** 2026-11-14
- **Status:** Proposed
- **Deciders:** Doni Wicaksono

## Context

The whole point of the project is to work on machines with little memory, little disk,
and no GPU. On such machines the failure modes are not exceptions: a model that does not
fit pushes the system into swap and stalls it, a training job fills the disk, a long
prompt takes a minute to evaluate. Tools written for large machines discover these limits
by failing.

Estimates of memory and speed for small models are unreliable. They vary with the
context size, the quantization, the thread count, and the engine version.

## Decision

Resource use is declared, measured, and enforced.

- A neuron manifest states, per profile, its resident memory, disk size, context budget,
  and expected latency. The numbers come from measurement on that profile, never from an
  estimate. A value that was not measured is marked as such and cannot be used to pass a
  gate.
- The runtime adds up what a configuration would keep resident and refuses, at load time,
  one that exceeds the profile, naming the numbers.
- A request that exceeds a neuron's context budget fails with an explicit error. Nothing
  is truncated silently.
- A lab job declares wall time, peak memory, and disk. The guard stops a job that exceeds
  them and refuses to start one that would leave less than a safety margin of free disk.
- The smallest profile is the bar: a feature that cannot work there is not merged.

## Consequences

### Positive
- A low-end machine is protected from the tool that is supposed to serve it.
- Users learn that something does not fit before it runs, with the reason.
- Published neurons carry numbers a user can trust for their own hardware class.

### Negative
- Every base model and neuron must be measured on every profile it claims, which needs
  access to that class of machine.
- Conservative limits will refuse configurations that might have worked.
- Measurement harnesses and fake meters for tests are code to write and maintain.

### Neutral
- The budget numbers themselves are set by milestone N0 and revised as engines change.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Try to load and handle the failure | On a small machine the failure is a stalled system, not a clean error |
| Estimate from parameter count | Off by a large factor once context size, quantization, and engine overhead are included |
| Leave limits to the operating system | The out-of-memory killer and a full disk are worse outcomes than a refusal |
| Budgets as documentation only | Unenforced numbers drift from reality |
