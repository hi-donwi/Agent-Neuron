# Spike E: pure-Go inference parity

- **Date:** 2026-11-14
- **Status:** Measured
- **Informs:** [ADR-0005](../adr/0005-pure-go-runtime-python-lab-external-engine.md), still Proposed
- **Implementation:** [`internal/router/static`](../../internal/router/static)
- **Reference exporter:** [`lab/spikes/export_static.py`](../../lab/spikes/export_static.py)

## Question and result

Does a pure-Go implementation of static token lookup, mean pooling, normalization, and
centroid scoring reproduce the Python reference closely enough to support the runtime
boundary in ADR-0005?

Yes for the measured model and frozen query sets. Across 178 queries and all 68 centroids,
the maximum absolute error was `5.75e-8` for any normalized embedding coordinate and
`3.59e-8` for any cosine score. The acceptance tolerance was `1e-5` for both. All 178
top-ranked labels matched Python.

The Go implementation routes in 31.0 us p50 / 60.6 us p95 in the local reference run,
compared with 51.4 us / 68.7 us for Python under the same harness. These microbenchmarks
are not a claim about the `nano` profile; tail latency varied between runs.

## Method

- **Model:** `potion-base-8M`, pinned in Spike D at
  `minishlab/potion-base-8M@bf8b056651a2c21b8d2565580b8569da283cab23` (MIT). It has 256
  dimensions and 29,528 token rows. The model and tokenizer were already cached by Spike D;
  this spike downloaded nothing.
- **Python reference:** `model2vec` 0.10.0 with `tokenizers` 0.23.3 and NumPy 2.5.4.
  Label vectors are produced by the same `StaticModel.encode`, `unit_rows`, and `centroids`
  functions used by Spike D. Query outputs are the normalized encoder vectors and their dot
  products against those 68 centroids.
- **Go implementation:** pure-Go BERT normalization, punctuation splitting, greedy
  WordPiece lookup, model2vec input/token limits and unknown-token omission, mean pooling,
  L2 normalization, and ordered centroid dot products. `golang.org/x/text` supplies Unicode
  canonical decomposition for the BERT accent-stripping behavior; inference and model
  loading use no CGO.
- **Queries:** the frozen 89 public Agent-Skills scenarios and 89 paraphrases from Spike D.
  Their catalogue commit and dataset hashes are recorded in
  [the Spike D report](d-router-quality.md). No query or model file is added to git.
- **Acceptance:** maximum absolute difference no greater than `1e-5` for each embedding
  coordinate and each of the 68 scores, with an identical top-ranked label for every
  query.
- **Latency:** one warm-up pass followed by 20 serial passes over the 89 public queries
  (1,780 timed calls per implementation); nearest-rank percentiles. A call includes text
  tokenization, lookup, pooling, normalization, and all 68 centroid scores.
- **Library versions:** `model2vec` 0.10.0; `tokenizers` 0.23.3; NumPy 2.5.4;
  `golang.org/x/text` 0.44.0.

## Measurements

| Metric | Go | Python reference |
|---|---:|---:|
| Maximum absolute embedding-coordinate error | 5.75e-8 | reference |
| Maximum absolute centroid-score error | 3.59e-8 | reference |
| Top-ranked labels matching | 178 / 178 | reference |
| Route latency p50 | 31.0 us | 51.4 us |
| Route latency p95 | 60.6 us | 68.7 us |

The portable local model uses a 30,236,672-byte float32 embedding table, a 69,632-byte
float32 centroid table, and about 455 kB of vocabulary/label metadata. The generated
artifact and numeric references stay under the git-ignored `.neuron/` cache.

## Reproduce

From the repository root, using the already-populated Spike D cache:

```bash
cd lab && uv run --locked --group spikes python -I spikes/export_static.py
cd ..
NEURON_PARITY_DIR="$(pwd)/.neuron/spikes/go-parity/potion-base-8M" go test -count=1 -v ./internal/router/static
```

The first command fails rather than downloading if the pinned model or catalogue snapshot
is absent. Without `NEURON_PARITY_DIR`, the ordinary Go test suite runs deterministic unit
fixtures and skips only the model-backed comparison.

## Limits and implications

This measures one 8M static encoder, English software-skill labels, and 178 queries. It
does not measure the 2M/32M variants, classifier training, retrieval, resource use on a
two-core `nano` host, or production routing quality. The result supports the feasibility
of the pure-Go inference boundary in ADR-0005; it does not settle the ADR or change its
status. No N1 router API or CLI was introduced by this spike.
