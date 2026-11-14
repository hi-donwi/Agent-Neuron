# ADR-0006: Training is a declarative pipeline agents can operate; a human promotes

- **Date:** 2026-11-14
- **Status:** Proposed
- **Deciders:** Doni Wicaksono

## Context

New specialists should be cheap to make. Three kinds of operator are expected: a person,
a scheduled job, and a coding agent that is far more capable than the models it trains.
Such an agent can write a spec, generate and label data, run commands, read a report, and
iterate, but only if every step is a command with predictable input and output.

Training data comes partly from a teacher model and partly from real use. Both are
untrusted: a teacher can be wrong or leak its own evaluation, and traces can carry
instructions or poisoned examples. A model that is promoted becomes standing behaviour
for every later request in its sub-domain.

## Decision

A neuron is built from a declarative spec: task, kind, data sources with audience and
licence, teacher, budget, and gates. Every lab step is a non-interactive command that
takes the spec, prints its plan and cost on dry-run, emits JSON, uses stable exit codes,
and can resume. The same commands serve a person, a scheduler, and an agent.

A more capable model may act as teacher and write or label training examples from
supplied documents. The evaluation set is built from separate seeds, reviewed by
sampling, frozen, and hashed before training starts.

Training may be automatic. Promotion never is. A trained neuron is a candidate with a
report; it is promotable only when every gate passes, and only an explicit human command
promotes it. Rollback is one command. This mirrors Agent-Brain ADR-0005 for learned
skills.

The operator confirms that a teacher's terms allow its outputs to be used as training
data before using it. The spec records the teacher, and a dataset intended for a public
neuron is refused when its teacher is not on the operator's allow list.

## Consequences

### Positive
- Any capable agent can produce a candidate from a spec without a person at the
  keyboard, on any machine that meets the budget.
- Every neuron is reproducible from its spec and dataset hash.
- A bad training run cannot change behaviour on its own.

### Negative
- A human review step limits how fast the system can change itself.
- The command surface, JSON shapes, and exit codes become a contract that must stay
  stable.
- Building and freezing an evaluation set before training is extra work for every
  neuron.
- Teacher terms differ by provider and change; the allow list needs upkeep.

### Neutral
- Which agent or model acts as teacher is configuration, not part of this decision.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Notebooks and ad hoc scripts | Not reproducible and not operable by an agent or a scheduler |
| Fully automatic training and promotion | Untrusted data would change standing behaviour with no review |
| Human-only training | Wastes the capability of the agents available and does not scale past a few neurons |
| The teacher writes the evaluation set after training | The teacher would grade its own output; results would not mean anything |
