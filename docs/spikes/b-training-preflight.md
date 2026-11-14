# Spike B preflight: LoRA training and GGUF export paths

- **Date:** 2026-11-14
- **Status:** No-install documentation preflight; Spike B is not complete
- **Informs:** [ADR-0003](../adr/0003-one-shared-base-with-adapters.md) and
  [ADR-0008](../adr/0008-resource-budgets-are-part-of-the-contract.md), both Proposed

## Recommendation

Use PyTorch + PEFT on CPU as the canonical path to produce a standalone GGUF LoRA adapter:
PEFT's documented `adapter_model.safetensors` + `adapter_config.json` output matches the
input expected by `llama.cpp/convert_lora_to_gguf.py`, which writes GGUF adapter metadata
(`type=lora`). This path aligns with ADR-0003's one-resident-base/many-adapters design.

Treat MLX-LM as an experimental **training-performance** path, not yet as an equivalent
adapter-delivery path. Its documented GGUF export is through `mlx_lm.fuse`: the adapter is
fused into the base and the output is a full GGUF model. No official direct conversion from
MLX's `adapters.safetensors` to a standalone LoRA GGUF adapter was found. A fused GGUF can
be measured as an explicitly separate deployment alternative, but it does not satisfy the
shared-base adapter contract.

For a fair two-path comparison, use a model family supported by both exporters. The
preselected Qwen3-0.6B is not in MLX-LM's documented LoRA model list, and `mlx_lm.fuse`
allows only `llama`, `mixtral`, and `mistral` GGUF export types. Prefer testing matching
pretrained SmolLM2 135M and 360M Llama-family checkpoints on both paths; 360M is smaller
than the original near-0.5B target. If that size gap is unacceptable, leave the medium
cross-path comparison unresolved rather than silently using Qwen3 on only one path.

## Documented paths

| Path | Training artifact | Documented GGUF output | Fit with one-base/many-adapters |
|---|---|---|---|
| PyTorch + PEFT | `adapter_model.safetensors`, `adapter_config.json` from `save_pretrained()` | `convert_lora_to_gguf.py` reads these adapter files and writes a GGUF with adapter type `lora`; `--base` needs `config.json` and `tokenizer.json`, not base weights | Direct fit, subject to a successful model conversion and engine load test |
| MLX-LM | `adapters.safetensors` plus adapter configuration | `mlx_lm.fuse --export-gguf` first fuses the LoRA into the base and emits a full `ggml-model-f16.gguf`; only Llama/Mistral/Mixtral style models are documented | No direct standalone GGUF adapter path documented; fused full model is a different architecture option |

MLX-LM documents LoRA and QLoRA training on quantized models. That corrects the overly
broad concern in the original roadmap: quantized-base training is documented, but the
documented GGUF *export* is a fused full model and limited to specific architectures. The
`--dequantize` option affects fusion/export, not the output being a standalone adapter.

## Fair-measurement plan

- Pin the same pretrained base revision and tokenizer for both paths. Use the base
  checkpoints for adapter training, not the instruct checkpoints preselected for runtime
  inference.
- Freeze one canonical `train.jsonl`, `valid.jsonl`, and `test.jsonl` with hashes. MLX-LM
  documents those splits and accepts chat/completion formats; adapt PEFT's dataset loader
  without changing examples or splits.
- Match trainable scope: explicitly set LoRA target modules, layer selection, rank, alpha,
  and effective batch. The MLX guide's defaults include batch size 4 and 16 trainable
  layers; do not compare them with a PEFT adapter covering every layer by accident.
- Record precision/quantization, seed, sequence truncation, optimizer, learning rate,
  steps/examples, trainable parameter count, peak RSS, wall time per 1,000 examples, adapter
  bytes, and fixed test-set schema validity. If precision differs, label it as a path-level
  trade-off rather than a controlled quality comparison.
- For the PEFT path, convert the adapter and run a round-trip check: verify base/adapter
  pairing, load both in the pinned `llama-server`, compare fixed logits or outputs against
  the Python adapter, then test JSON validity.
- For MLX, measure training only unless a standalone adapter conversion is independently
  demonstrated. If testing `fuse --export-gguf`, record it as a full-model alternative and
  compare its storage/RSS separately.

## Limits and approval

The repository pins neither PyTorch/PEFT nor MLX-LM, and `llama-server` is not installed or
pinned. No runtime, model, or dataset was installed/downloaded, and no training or memory
measurement was run. A target execution environment and resource budget must be selected
before these measurements. This preflight changes neither ADR status nor the Spike B
checkbox.

## Official sources

- PEFT LoRA usage and adapter semantics:
  <https://huggingface.co/docs/peft/main/en/developer_guides/lora>
- PEFT quicktour and saving/loading adapters:
  <https://huggingface.co/docs/peft/main/en/quicktour>
- MLX-LM LoRA/QLoRA guide at source revision `47e43a4526d42a6dcee758f07eb04b78a8439ecb`:
  <https://github.com/ml-explore/mlx-lm/blob/47e43a4526d42a6dcee758f07eb04b78a8439ecb/mlx_lm/LORA.md>
- MLX-LM fusion implementation at source revision `56230fa02b8ff8330daf26dc95c28480423ed5fe`:
  <https://github.com/ml-explore/mlx-lm/blob/56230fa02b8ff8330daf26dc95c28480423ed5fe/mlx_lm/fuse.py>
- `llama.cpp` PEFT-to-GGUF converter at revision `32bdc3a89e6528d3e419024c833c5dabf32c7541`:
  <https://github.com/ggml-org/llama.cpp/blob/32bdc3a89e6528d3e419024c833c5dabf32c7541/convert_lora_to_gguf.py>
