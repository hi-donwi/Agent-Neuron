# Spike C preflight: adapter selection and cache behavior

- **Date:** 2026-11-14
- **Status:** No-install source preflight; Spike C is not complete
- **Informs:** [ADR-0003](../adr/0003-one-shared-base-with-adapters.md), still Proposed
- **Source snapshot:** `ggml-org/llama.cpp` revision
  `32bdc3a89e6528d3e419024c833c5dabf32c7541`

## Source findings

- The server registers `GET /lora-adapters`, `POST /lora-adapters`, and
  `POST /v1/chat/completions`. Startup `--lora` flags preload adapters; the docs describe
  `--lora-init-without-apply` for loading them without setting a nonzero default scale.
- The shared completion schema has a request-level `lora` list of `{id, scale}` entries;
  adapters omitted from the list default to scale `0.0`. The OpenAI chat handler invokes the
  common completion path after chat-body parsing, but the exact request field pass-through
  still needs a `/v1/chat/completions` smoke test against the pinned server build.
- `GET /lora-adapters` exposes IDs, paths, and scales. IDs are derived from the loaded
  adapter list, so the client should map ID to path from the running server rather than
  assume an ID remains stable across startup configurations.
- `POST /lora-adapters` parses a list of IDs/scales and changes server-wide default adapter
  scales. It is a control-plane setting, not the right mechanism to route concurrent
  requests to different specialists.
- Each request slot holds its own LoRA configuration. The scheduler's `can_batch_with`
  predicate only batches slots with equal LoRA configurations, and the batch applies that
  slot configuration. This is a source-level isolation mechanism, not a measured
  cross-request correctness guarantee.
- On a normal LoRA change, `launch_slot_with_task` clears that slot's prompt state when
  `lora_should_clear_cache` returns true. aLoRA has special prefix-cache handling. Thus
  switching ordinary adapters is expected to lose prompt-cache reuse; the actual latency
  cost and cache statistics still need measurement.

These findings suggest the intended design is feasible with preloaded adapters and
request-level selection, while warning against concurrent use of the global scale endpoint.
They do not establish that every OpenAI-compatible chat parser version preserves the
extension or that mixed concurrent requests are free from cross-contamination.

## Recommended test matrix

After selecting an engine/model environment and pinning its server build:

1. Start one server with one base and at least two adapters preloaded but inactive. Record
   exact file hashes, startup order/flags, model/context, parallel slots, and build revision.
2. Call `GET /lora-adapters` and verify the runtime IDs, paths, and default scales. Test
   unknown IDs, zero scale, multiple enabled adapters, and default/no-adapter behavior.
3. Exercise `/v1/chat/completions` directly with the request-level `lora` list for A, B, and
   no adapter. Verify deterministic adapter-specific outputs and that the chat-body parser
   passes the extension into the shared schema.
4. With prompt caching on and off, measure repeated A→A, A→B, and B→A requests. Record
   `cached_tokens`/cache progress, time to first token, total latency, and output correctness.
5. Send randomized concurrent A/B requests at several `n_parallel` settings. Use prompts
   with distinctive expected responses; assert every response matches its requested
   adapter. Report throughput, p50/p95 latency, failures, and whether different-adapter
   slots were kept out of the same batch.
6. Exercise the global `POST /lora-adapters` endpoint only in serial control-plane tests;
   verify its effect on later requests and ensure production routing does not race this
   server-wide default with in-flight calls.

Pre-register the prompt/query fixtures before tuning. Repeat adapter transitions and
concurrency runs enough times to expose stale-cache or routing flakes; keep those results
separate from the synthetic routing evaluation in Spike D.

## Limits and approval

The product repository does not pin a `llama-server` release, and no server/runtime or
model was installed for this preflight. Source-level support is not a substitute for
loadability, latency, cache, or concurrency measurements. Spike C remains unchecked until
the server version is pinned and the test matrix is run in an owner-approved environment.

## Official sources

- Server API/adapter docs at pinned revision:
  <https://github.com/ggml-org/llama.cpp/blob/32bdc3a89e6528d3e419024c833c5dabf32c7541/tools/server/README.md>
- Route registration and server roles:
  <https://github.com/ggml-org/llama.cpp/blob/32bdc3a89e6528d3e419024c833c5dabf32c7541/tools/server/server.cpp>
- Request-slot, batch compatibility, cache and adapter application:
  <https://github.com/ggml-org/llama.cpp/blob/32bdc3a89e6528d3e419024c833c5dabf32c7541/tools/server/server-context.cpp>
- Request `lora` field schema:
  <https://github.com/ggml-org/llama.cpp/blob/32bdc3a89e6528d3e419024c833c5dabf32c7541/tools/server/server-schema.cpp>
