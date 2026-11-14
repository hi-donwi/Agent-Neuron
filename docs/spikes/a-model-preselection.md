# Spike A preselection: CPU model candidates

- **Date:** 2026-11-14
- **Status:** Desk preselection only; Spike A is not complete
- **Scope:** official model-card and public GGUF metadata review; no weights or runtimes
  downloaded

## Recommendation

Carry two candidates into the later CPU measurements:

1. **Small:** `HuggingFaceTB/SmolLM2-135M-Instruct` (134,515,008 parameters).
2. **Medium:** `Qwen/Qwen3-0.6B` (0.6B parameters; 0.44B excluding embeddings).

Both upstream model cards state Apache-2.0. Published Q4 artifacts are about 91.9 MB and
429.0 MB respectively. The small candidate is substantially below the 8 GB memory target;
the Qwen model offers a useful upper comparison near the requested 0.5B class, but its
28-layer architecture and KV cache make it the likely limiting case.

An optional middle candidate is `HuggingFaceTB/SmolLM2-360M-Instruct`: its published
`Q4_K_M` derivative is 270.6 MB and it shares the SmolLM2 family. Use it if Qwen3 exceeds
the actual `tiny` RSS or latency budget. Do not infer task quality from the model cards'
benchmarks; their reported evaluations are not this project's schema-constrained workload.

## Published metadata

| Candidate | Upstream licence and context | Published 4-bit GGUF | File size | Provenance |
|---|---|---|---:|---|
| SmolLM2-135M-Instruct | Apache-2.0; 134,515,008 parameters; config max positions 8,192 | `SmolLM2-135M-Instruct-Q4_0.gguf` | 91,893,088 bytes | `bartowski` conversion of the Hugging Face model; LFS SHA-256 `bcc3af2849ad6095af57e9b5cd43775256efdc66e306acb529172f92d0c04b03` |
| Qwen3-0.6B | Apache-2.0; 0.6B total, 0.44B non-embedding; config max positions 40,960 | `Qwen3-0.6B-Q4_0.gguf` | 428,970,080 bytes | `ggml-org` automated conversion; LFS SHA-256 `da2572f16c06133561ce56accaa822216f2391ef4d37fba427801cd6736417d4` |
| SmolLM2-360M-Instruct (optional) | Apache-2.0; 360M class; GGUF metadata reports 8,192 context | `SmolLM2-360M-Instruct-Q4_K_M.gguf` | 270,590,880 bytes | `bartowski` conversion; LFS SHA-256 `2fa3f013dcdd7b99f9b237717fa0b12d75bbb89984cc1274be1471a465bac9c2` |

Model-card parameter counts and licences are upstream statements. GGUF file sizes and
checksums are third-party file metadata, not locally verified artifacts. The primary Q4
file for SmolLM2-135M is a third-party conversion; for a measured run, either verify it
against the pinned upstream weights or convert from those weights with a pinned
`llama.cpp` toolchain.

The selected A candidates are **instruction-tuned runtime variants**. Spike B's adapter
training must start from the corresponding pre-trained base checkpoints if that is what its
design requires; do not silently substitute these instruct weights. GGUF availability and
conversion for the base checkpoints have not been measured. For B's cross-path comparison,
the no-install preflight recommends SmolLM2-135M and SmolLM2-360M base-family checkpoints
instead of Qwen3: current MLX-LM documents Llama-style GGUF fusion, not a standalone Qwen3
adapter. See [the Spike B preflight](b-training-preflight.md).

## Memory estimate, not measurement

For a rough lower bound, assume an F16 KV cache and calculate
`2 * layers * kv_heads * head_dim * context_tokens * 2 bytes`:

| Candidate | KV cache at 2k | KV cache at 4k | Q4 weights + 4k KV |
|---|---:|---:|---:|
| SmolLM2-135M | about 45 MiB | about 90 MiB | about 178 MiB |
| Qwen3-0.6B | about 224 MiB | about 448 MiB | about 857 MiB |

This excludes runtime buffers, temporary activations, allocator overhead, mmap residency,
tokenizer state, and OS memory. It is not resident-memory evidence and cannot replace the
required `llama-server` RSS measurement. The SmolLM2-135M config sets three KV heads; the
estimate uses that grouped-query count. The Qwen model card says 32,768 context while its
current `config.json` and GGUF metadata say 40,960; pin the tested revision and resolve
that discrepancy before any longer-context claims. It does not change the required 2k/4k
measurements.

## Supply-chain note

Hugging Face file metadata for the listed Q4 GGUFs shows a ProtectAI `PAIT-GGUF-100`
warning. The same metadata reports no VirusTotal detections; JFrog marks the Qwen GGUF as
safe. These scanner results conflict and have not been independently resolved. Do not
consume a downloaded GGUF until its origin and the warning are reviewed. A matching LFS
SHA-256 only verifies bytes against the hosting metadata; it does not establish trust.

## Local free-model smoke

After the owner asked to start with a free model that runs on this device, one bounded
smoke test used the existing Ollama 0.30.8 runtime and the Ollama Library tag
`smollm2:135m` (135M, F16, Apache-2.0). The published size is 271 MB; the local API
manifest digest was
`9077fe9d2ae1a4a41a868836b56b8163731a8fe16621397028c2c76f838c6907`, and the API-reported
weight size was 270,898,672 bytes. Model files were stored only in the ignored
`.neuron/spikes/ollama-store` cache.

Three synthetic `/api/chat` requests used Ollama's JSON Schema `format`, temperature 0,
and 512-token context: one on Ollama's default device selection and two with `num_gpu=0`.
All three returned the schema-valid object `{"status":"ok","count":1}`. The
CPU-enforced warm request completed in 344.5 ms: 33 prompt tokens in
108.3 ms and 17 generated tokens in 149.0 ms (about 114 generated tokens/s). Ollama
reported a 295 MB loaded model and `100% CPU`; this is a single smoke, not a throughput or
quality benchmark. The model and temporary server were unloaded/stopped after the test;
the ignored model files remain available locally.

The calls were local-only (`OLLAMA_NO_CLOUD=1`, bound to `127.0.0.1`). No Python/ML packages
were installed. Ollama is a free local runtime, but it is not the project's target pinned
`llama-server`; this does not complete Spike A or validate `llama-server` JSON-schema
behavior.

### Context profile (Ollama only)

Two additional CPU-only JSON Schema requests used `num_ctx=2048` and `4096`, with synthetic
prompt lengths of 2,047 and 4,095 evaluated tokens respectively. Ollama reported loaded
model allocations of 332 MB at 2k and 382 MB at 4k. One request per context returned valid
JSON; single-run prompt/generation rates were 271/30.4 tokens/s at 2k and 173.8/14.7
tokens/s at 4k, with total times 8.19 s and 25.58 s. This is not a p50/p95 benchmark.
`ollama ps` allocation is not OS process RSS, the model is F16 rather than Q4, and none of
these figures substitute for the required `llama-server`/two-host Spike A measurements.

Re-run the same local tag with:

```bash
OLLAMA_MODELS="$(pwd)/.neuron/spikes/ollama-store" OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 ollama serve
OLLAMA_HOST=127.0.0.1:11434 ollama run smollm2:135m
```

## Still required for Spike A

- Pin exact model revisions, GGUF files, and `llama-server` version; verify downloaded
  hashes and review the GGUF scan warning.
- On an approved 8 GB laptop and two-vCPU x86 Linux VM, measure RSS at 2k/4k context and
  CPU prompt/generation tokens per second.
- Run the same schema-constrained JSON corpus for validity rate, truncation, and failure
  analysis.
- Compare the two primary candidates and, only if the medium case exceeds budgets, the
  optional 360M alternative.

The full Spike A still needs a pinned `llama-server` run, candidate measurements on the
target profiles, and measured schema validity. This preselection does not check Spike A
complete.

## Sources

- Hugging Face model card: <https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct>
- Ollama Library tag, size, and license: <https://ollama.com/library/smollm2:135m>
- Ollama chat API request/response contract: <https://docs.ollama.com/api/chat>
- Ollama structured-output JSON Schema contract: <https://docs.ollama.com/capabilities/structured-outputs>
- Hugging Face model config: <https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct/raw/main/config.json>
- SmolLM2-135M base config (three KV heads): <https://huggingface.co/HuggingFaceTB/SmolLM2-135M/raw/main/config.json>
- SmolLM2-135M GGUF file listing and metadata: <https://huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF/tree/09816acd5d99df7be770d85ea30822623dab342c>
- Hugging Face model card: <https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct>
- SmolLM2-360M GGUF file listing and metadata: <https://huggingface.co/bartowski/SmolLM2-360M-Instruct-GGUF/tree/7be6f65f1db715fe5dc5a4634c0d459b4eed42ec>
- Qwen model card: <https://huggingface.co/Qwen/Qwen3-0.6B>
- Qwen model config: <https://huggingface.co/Qwen/Qwen3-0.6B/raw/main/config.json>
- Qwen3-0.6B GGUF conversion and file listing: <https://huggingface.co/ggml-org/Qwen3-0.6B-GGUF/tree/afe8ad3577aa22500b3cd1c880f153b3b0e1cae8>
