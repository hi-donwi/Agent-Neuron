# Security

Agent-Neuron trains models from documents and traces and serves them on your machine, so
what a model may learn from, and what may leave the machine, are part of the product.

## Reporting a vulnerability

Please do **not** open a public issue for security problems. Report them privately and
include the version, the affected command, and reproduction steps you can share safely.

- Open a private security advisory:
  `https://github.com/hi-donwi/Agent-Neuron/security/advisories/new`

You will receive an acknowledgement, and we will coordinate a fix and a disclosure
timeline with you. Reporters are credited unless they prefer otherwise.

## Security properties (targets for v1)

These are design commitments recorded in the [ADRs](docs/adr/README.md); each is
implemented and tested in the milestone named in the [roadmap](ROADMAP.md).

- **Loopback only.** The API binds to `127.0.0.1` and requires a per-process bearer token
  stored in a file only the user can read.
- **No telemetry.** The only egress is a teacher or an escalation endpoint the operator
  configured, and a response that used an escalation says so.
- **Audience is enforced.** A neuron trained on private data cannot be exported for
  publication ([ADR-0007](docs/adr/0007-data-provenance-and-audience.md)).
- **Content is data.** Documents, traces, and teacher outputs are never treated as
  instructions. A candidate built from data containing instruction-like text is flagged,
  and the flag is shown at promotion.
- **Trained models cannot activate themselves.** A trained neuron is a candidate until a
  human promotes it
  ([ADR-0006](docs/adr/0006-agent-operable-training-human-promotion.md)).
- **Integrity.** Packs and artifacts are addressed by content hash and verified on load.
- **Resource limits.** Configurations and jobs that exceed a declared budget are refused
  ([ADR-0008](docs/adr/0008-resource-budgets-are-part-of-the-contract.md)).

## Supply chain

CI is planned to run the Agent-Secure gate at pinned, checksum-verified versions, with
GitHub Actions pinned by commit SHA and Python dependencies locked.
