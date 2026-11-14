# Roadmap

Agent-Neuron is built in nine milestones. Each one ships something usable on its own and
ends with explicit exit criteria. Milestones are sequential; work inside a milestone is
split into small commits, one concern each, with tests first for logic.

Status: **N0 in progress.** The repository layout, the Makefile gates, CI, and
`neuron version` are in place; the six spikes are not started. The ADRs are Proposed
until N0 measures the assumptions they rest on.

| Milestone | Release | Theme | Status |
|---|---|---|---|
| [N0](#n0-foundation-and-measurement) | - | Foundation: repository, CI, ADRs, six spikes | In progress |
| [N1](#n1-neuron-format-and-the-cortex-router) | v0.1 | Neuron format and the cortex router | Planned |
| [N2](#n2-the-lab-for-small-encoders) | v0.2 | Lab: datasets, training, evaluation for router and extraction neurons | Planned |
| [N3](#n3-knowledge-packs) | v0.3 | Knowledge packs and extractive answers | Planned |
| [N4](#n4-generative-neurons-serving) | v0.4 | Generative neurons: serving | Planned |
| [N5](#n5-generative-neurons-training) | v0.5 | Generative neurons: adapter training and distillation | Planned |
| [N6](#n6-growth-loop) | v0.6 | Growth loop: proposing and training new neurons | Planned |
| [N7](#n7-suite-integration) | v0.7 | Suite integration | Planned |
| [N8](#n8-v10) | v1.0 | Distribution, published packs, stability | Planned |

The order is deliberate: classification before generation, serving before training,
manual training before automatic training. Each step is useful alone, and each one
produces the measurements the next one needs.

## Principles

- **The smallest profile is the bar.** Every feature must work on a two-core machine
  without a GPU. Larger machines get a larger base model, not a different code path.
- **Split the work, not just the model.** Route, look up, extract, generate, and verify
  are separate parts, and each goes to the cheapest part that can do it.
- **Knowledge in retrieval, behaviour in weights.** A new fact rebuilds an index. Only a
  behaviour gap justifies training.
- **Measure, then claim.** A base model enters the catalogue when it was measured on the
  target profile. A neuron is promoted when its evaluation beats the baseline on a frozen
  set. Budgets in this file are replaced by measured numbers as milestones close.
- **Fail loudly.** Over-budget prompts, missing artifacts, a full disk, and a failed
  verifier are explicit errors or abstentions, never quiet degradation.
- **A human promotes.** Training may be automatic; promotion never is.
- **Provenance travels with the artifact.** Every neuron names its spec, dataset, base
  model, licences, and audience.
- **Local by default.** Loopback only, no telemetry, no egress unless the operator
  configures a teacher or an escalation endpoint.
- **Orchestrate the engine, do not reimplement it.** A pinned external engine generates;
  the runtime routes, retrieves, composes, and verifies.

## Provisional budgets

These are design targets. N0 replaces them with measured numbers per profile.

| Stage | Budget on the `tiny` profile, CPU threads only |
|---|---|
| Route (three levels) | 10 ms p95 |
| Retrieve from a pack of 100k chunks | 50 ms p95 |
| First generated token, warm base and cached static prefix | 1 s |
| Complete answer of about 100 tokens | 5 s |
| Resident memory: runtime, one base, loaded adapters, one knowledge pack | 1.5 GB |
| Disk for one pack without the base model | 200 MB |

## N0: Foundation and measurement

Goal: a repository that builds, tests, and gates itself, with the riskiest assumptions
measured before any design is treated as settled.

Deliverables:

- [x] Layout: `cmd/neuron`, `internal/` (Go runtime), `lab/` (Python, managed by uv with a
  lock file), `evals/`, `docs/`. Makefile targets `check`, `static-check`, `lab-check`.
- [x] CI: gofmt, `go mod tidy` check, vet, tests on Linux and macOS, static cross-compile for
  five platforms, Python lint and tests under uv, the Agent-Secure secret and dependency
  gate, one aggregate check.
- [x] `neuron version` (`--json`).
- [ ] Spike A, base model shortlist. Open-weight candidates between roughly 100M and 1B
  parameters. Per candidate: licence as written on the model card, 4-bit GGUF size,
  resident memory at 2k and 4k context, prompt and generation tokens per second with CPU
  threads only, and validity rate under JSON-schema-constrained decoding. Measured on an
  8 GB laptop and on a two-vCPU x86 Linux VM.
- [ ] Spike B, adapter training on 8 GB. Train a low-rank adapter on a base near 150M and one
  near 0.5B parameters through two paths (PyTorch with PEFT on CPU, and MLX on Apple
  Silicon). Record peak memory, wall time per thousand examples, and whether the result
  becomes a GGUF adapter the engine loads. Known risk to check: GGUF export from MLX is
  limited and does not work from a quantized base.
- [ ] Spike C, adapter switching in the engine. Against a pinned `llama-server`: preload
  several adapters, select one per request, and measure switch latency, the effect on the
  prompt cache, and behaviour when concurrent requests name different adapters.
- [ ] Spike D, router quality. Static embeddings with a linear head, against a keyword
  baseline and a small transformer encoder, on the public Agent-Skills scenario set:
  accuracy, abstention calibration on out-of-domain inputs, p95 latency, artifact size.
- [ ] Spike E, pure-Go inference parity. The static embedding lookup and the router head
  implemented in Go reproduce the Python reference outputs within a stated tolerance.
- [ ] Spike F, retrieval quality. SQLite FTS5 plus static vectors with reciprocal rank fusion
  on a public documentation corpus, against a transformer embedder: recall@5 and MRR on a
  golden set.

Exit criteria: CI green on `main`; every spike has a recorded result; each ADR is
Accepted, amended, or superseded in light of them; the provisional budgets above and the
profile table in the README carry measured numbers.

## N1: Neuron format and the cortex router

Goal: classify a request into domain, sub-domain, and task on a CPU in milliseconds, and
answer "none of these" when that is the truth.

Deliverables:

- Manifest schemas, version 0: `neuron.yaml` and `pack.yaml`, validated by JSON Schema.
  Identity by content hash. A local store under the neuron home.
- `internal/router`: tiered routing (explicit rules, nearest centroid over static
  embeddings, trained head), hierarchical labels, calibrated confidence, an abstention
  threshold per level.
- `neuron route "<text>" [--json]`, `neuron packs ls|add|rm|verify`, `neuron doctor`
  (hardware, detected profile, store integrity; every failed check prints its fix).
- First pack, `skills`: a router neuron over the public Agent-Skills catalogue, trained
  by a reference script that N2 turns into the pipeline.

Tests: schema fixtures, valid and invalid; router fixtures for a direct request, a
paraphrase, a near miss that must route elsewhere, and an out-of-domain input that must
abstain; Go and Python parity fixtures; `packs verify` fails on a tampered artifact.

Exit criteria: on the public scenario set the router beats the keyword baseline by a
recorded margin, with out-of-domain abstention measured; p95 route latency meets the
N0 budget on the `nano` profile; static binaries build for five platforms.

## N2: The lab for small encoders

Goal: a declared spec becomes a promoted router or extraction neuron on an 8 GB machine,
through commands an agent can run without a person at the keyboard.

Deliverables:

- `lab/`: a Python package with locked dependencies. The `neuron` binary calls it through
  a documented, versioned JSON contract. The runtime never needs Python; training does.
- Neuron spec (`spec.yaml`): task, kind, labels or output schema, data sources with their
  audience and licence, teacher, budget (wall time, peak memory, disk), gates (metric,
  threshold, baseline).
- `neuron data build|inspect|freeze`: collect from files, synthesize through a teacher
  endpoint, deduplicate, split. The evaluation set is frozen and hashed before any
  training starts. Every example carries its source and audience.
- `neuron train` for kinds `route` and `extract`.
- `neuron eval`: metrics against the baseline and the previous version; a JSON and a
  Markdown report. Cases that did not run count as failures.
- Candidates: `neuron candidates ls|show`, `neuron promote`, `neuron rollback`. Promotion
  is always an explicit human command.
- Budget guard: a job that would exceed its declared memory, disk, or time stops with an
  explicit error; a job that would leave less than a safety margin of free disk refuses
  to start.
- Agent-operable surface: `--json` everywhere, stable exit codes, no prompts, resumable
  jobs, and a dry-run that prints the plan and its cost before anything runs.

Tests: spec validation; seeded training on a small fixture dataset with an expected
metric range; a frozen evaluation set cannot change (hash test); budget guard tests with
fake meters; an example without provenance is rejected; promotion refuses a candidate
with a failing gate.

Exit criteria: an agent given only a spec file and the command reference produces a
promoted router neuron on the 8 GB reference machine; the result is reproducible from
the spec and the dataset hash.

## N3: Knowledge packs

Goal: answer from a domain's documents with citations and no generation, so that new
knowledge never requires training.

Deliverables:

- `internal/store`: pure-Go SQLite with FTS5; chunks, static vectors, sources, licences.
- `neuron knowledge build <pack> <path>`: chunkers (Markdown by heading, plain text by
  paragraph), a chunk size chosen for small context windows, content hashing, incremental
  rebuild, removal of deleted sources.
- Hybrid retrieval: bm25 plus a static-vector scan, fused by reciprocal rank; an optional
  rerank step when a pack ships one.
- `neuron ask "<question>" --extractive`: the best supporting passages with `path:line`
  citations, and an explicit "not found in this pack".
- Retrieval port: the built-in store, or an external provider such as an Agent-Brain
  collection, behind one interface.
- `evals/retrieval`: a golden set over public documentation; recall@5 and MRR.

Tests: chunker fixtures; incremental rebuild touches only changed files; retrieval
fixtures with a deterministic fake embedder in CI; the not-found path.

Exit criteria: baseline recall@5 and MRR recorded for the built-in store; a fact added to
a source file is answerable after `knowledge build` with no training step.

## N4: Generative neurons: serving

Goal: one endpoint that routes, retrieves, generates with the right adapter, verifies,
and answers on a CPU inside the measured budget.

Deliverables:

- Engine supervisor for a pinned `llama-server`: detect, start, health, stop. Weights are
  never loaded in-process.
- One resident base model per profile. Adapters preloaded and selected per request, in
  the way Spike C found reliable. A fused model is a declared exception in the manifest.
- Composer: a static, cacheable prefix per neuron; retrieved context inside a token
  budget; a hard cap on output tokens.
- Constrained decoding: the JSON Schema or grammar named by the neuron manifest.
- Verifiers declared by the neuron: schema validation, cited spans exist in the supplied
  context, allowed values, numeric and unit checks. One bounded retry, then abstention.
- `neuron serve`: loopback bind, per-process bearer token, Host header check;
  `GET /v1/models`, `POST /v1/chat/completions` (streaming) with `model: auto` or
  `<pack>/<neuron>`, `GET /healthz`. Responses name the route taken, the neuron version,
  and whether the answer is an abstention.
- Token guard: a request over the context budget fails with an explicit error.
- Escalation hook: off by default; when configured, an abstention may be forwarded to a
  named upstream, and the response says so.
- Agent-Brain connection, documented and tested: a `local` account pointing at
  `neuron serve`.

Tests: engine contract tests against a fake engine; composer budget tests; verifier
fixtures; authentication and Host header tests; abstention and escalation labelling.

Exit criteria: on the `tiny` profile with CPU threads only, a request is routed,
grounded, generated with an adapter, verified, and returned inside the N0 budget; two
sub-domains alternate without reloading the base; Agent-Brain serves the endpoint through
a local account.

## N5: Generative neurons: training

Goal: an adapter trained on the 8 GB reference machine measurably beats its base model on
a narrow task.

Deliverables:

- `neuron train` for kind `generate`: a low-rank adapter over the shared base, through
  the path Spike B selected; export to a GGUF adapter; quantization for fused exceptions.
- Retrieval-augmented training data: each example pairs a question with supporting and
  distractor passages; a declared share has no supporting passage and its target is an
  abstention.
- Distillation: a teacher endpoint writes candidate answers from supplied documents.
  Each example records the teacher, the source documents, and the audience. Automatic
  filters (schema validity, citation check, duplicates), then sampled human review before
  the set is frozen.
- Generation metrics: structured validity, groundedness by citation check, task
  validators, abstention precision and recall; comparison with the base without the
  adapter and with a larger reference model.
- First generative pack, `uidl`: sub-domains by document type, judged by the public UIDL
  schema validator.
- Second generative pack, `ops`: plain-language explanations of findings from the public
  OPS-Toolkit and DBA-Toolkit rule catalogues.

Tests: data builder fixtures (distractor and abstention shares honoured); seeded training
on a toy base in CI with a fake trainer for the heavy path; export round trip; gate tests.

Exit criteria: an adapter trained inside its declared budget on the reference machine
beats the base on the frozen set by a recorded margin; UIDL documents validate at a
recorded rate under constrained decoding; no step needed a GPU.

## N6: Growth loop

Goal: the system notices what it cannot do, proposes a new neuron or a retrain with
evidence, and trains candidates in idle time. A person decides what is promoted.

Deliverables:

- Observation log, opt-in and local: route, confidence, verifier outcome, abstention.
  Request content is hashed or redacted by default.
- `neuron growth report`: clusters of abstained or failed requests, decay of promoted
  neurons, drift of router confidence.
- `neuron growth propose`: a draft spec for a new sub-domain or a retrain, stored as a
  candidate spec with its evidence.
- `neuron growth run`: scheduled, idle-only, budget-bound jobs for approved specs; the
  results land as candidates.
- Rule enforced by the tool: new facts trigger a knowledge rebuild, not a training job.
- Decay report and demotion proposals; never automatic removal.

Tests: clustering fixtures; proposal provenance; scheduler respects idle and budget
limits under fake clocks and meters; a log with planted injected instructions yields a
flagged candidate.

Exit criteria: from a seeded log the loop proposes a sub-domain, trains a candidate
within budget, and the candidate passes its gates; a candidate built from a log with
planted instructions is flagged and cannot be promoted without the flag being shown.

## N7: Suite integration

Goal: the rest of the suite uses neurons and feeds the lab, each through its own
boundary.

Deliverables:

- Agent-Brain: packs as a catalogue and backend entry (needs an Agent-Brain ADR); opt-in,
  redacted trace export as a lab data source; reuse of its evaluation runner where it
  fits.
- Agent-Skills: `design-a-neuron-spec` and `train-a-neuron` skills, so any coding agent
  can operate the lab from the command reference.
- Agent-Control: a review surface for candidates (provenance, evaluation report,
  promote) over typed job endpoints. No endpoint executes arbitrary commands.
- MCP: read-only inventory tools `list_packs`, `get_neuron`, `route_preview`.
- Agent-Workspace: `ws route` may use the `skills` router neuron when it is installed.

Exit criteria: a coding agent following the published skill trains and proposes a neuron
from a spec; Agent-Control shows the candidate with its report; Agent-Brain serves a
promoted pack to a client.

## N8: v1.0

Goal: easy to install, stable to depend on, verified on real low-end hardware.

Deliverables:

- Release workflow: binaries for five platforms, checksums, build provenance attestation,
  SBOM, signed tags. `install.sh` that verifies checksums.
- Published packs: weights as release assets or on a model hub, never in git; a model
  card per neuron generated from its manifest and evaluation report.
- Stable surfaces declared and pinned by tests: CLI commands and flags, `--json` shapes,
  the manifest and spec schema versions, the endpoints, the lab contract.
- Verification matrix: a two-vCPU x86 Linux VM, an ARM single-board computer, an 8 GB
  laptop. Each profile's budgets recorded.
- Documentation per command, troubleshooting by doctor check ID, and a guide for adding
  a domain.

Exit criteria: one-command install on macOS and Linux; `neuron doctor` green on all three
machines; a new domain goes from spec to promoted pack by following the guide alone.

## Not planned for v1

- Pretraining a language model from scratch.
- Running model weights in-process or writing inference kernels.
- Anything that requires a GPU to work. A GPU may speed up training elsewhere; no path
  depends on one.
- Automatic promotion of a trained neuron.
- An agent loop, tools, approvals, or a web console.
- A multi-user or networked server deployment.
- Model weights in git.

## Candidates after v1

Recorded so they are not lost; each needs its own evaluation before it is planned.

- Agent-Brain importing the router as a Go package instead of calling it over HTTP.
- Vision and speech neurons.
- Micro models trained from scratch for single structured tasks.
- Speculative decoding with a smaller draft model.
- Sharing packs between machines with signed manifests.
- Continual adapter updates from accepted corrections.
