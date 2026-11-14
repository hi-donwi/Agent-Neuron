# Spikes

A spike measures one risky assumption before the design that rests on it is treated as
settled. Milestone N0 has six ([ROADMAP](../../ROADMAP.md)). Each write-up states its
method, its data and their pins, the machine, the numbers, and what they mean for the ADR
they inform. A spike changes no ADR's status; the decider does that.

| Spike | Question | Status | Informs |
|---|---|---|---|
| A | Which base models fit each profile, and under which licences? | Not started | ADR-0003, ADR-0008 |
| B | Which training path yields a GGUF adapter from an 8 GB machine? | Not started | ADR-0003, ADR-0008 |
| C | Is per-request adapter selection reliable in the pinned engine? | Not started | ADR-0003 |
| [D](d-router-quality.md) | Are static embeddings accurate enough to route, and where do they need help? | Measured 2026-11-14 | ADR-0004, ADR-0005 |
| E | Does pure-Go router inference match the Python reference? | Not started | ADR-0005 |
| F | How much retrieval quality do static vectors give up? | Not started | ADR-0002 |
