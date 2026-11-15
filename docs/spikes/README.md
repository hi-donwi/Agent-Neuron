# Spikes

A spike measures one risky assumption before the design that rests on it is treated as
settled. Milestone N0 has six ([ROADMAP](../../ROADMAP.md)). Each write-up states its
method, data pins, measured runtime profile where available, results, limitations, and
implications for the ADR it informs. A spike changes no ADR's status; the decider does that.

| Spike | Question | Status | Informs |
|---|---|---|---|
| [A](a-model-preselection.md) | Which base models fit each profile, and under which licences? | Preselection + repeated CPU/RSS profile; full matrix blocked | ADR-0003, ADR-0008 |
| [B](b-training-preflight.md) | Which training path yields a GGUF adapter from an 8 GB machine? | No-install preflight only; measurements blocked | ADR-0003, ADR-0008 |
| [C](c-adapter-api-preflight.md) | Is per-request adapter selection reliable in the pinned engine? | Source preflight + empty-adapter live probe; valid adapter tests blocked | ADR-0003 |
| [D](d-router-quality.md) | Are static embeddings accurate enough to route, and where do they need help? | Measured 2026-11-14 | ADR-0004, ADR-0005 |
| [E](e-go-inference-parity.md) | Does pure-Go router inference match the Python reference? | Measured 2026-11-14 | ADR-0005 |
| [F](f-retrieval-preview.md) | How much retrieval quality do static vectors give up? | Partial preview only; transformer arm blocked | ADR-0002 |
