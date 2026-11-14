# Spike F preview: BM25, static vectors, and RRF

- **Date:** 2026-11-14
- **Status:** Partial; Spike F remains open
- **Informs:** [ADR-0002](../adr/0002-knowledge-in-retrieval-behaviour-in-weights.md), still Proposed
- **Full spike:** SQLite FTS5 + static vectors with reciprocal rank fusion against a
  transformer embedder on a reviewed, frozen public-doc evaluation set

## Preview result

On an exploratory set of 15 synthetic questions over the public project documentation,
BM25 reached recall@5 `0.600` and MRR `0.492`. The Go `potion-base-8M` static vectors
reached `0.533` and `0.399`. Reciprocal rank fusion (RRF, `k=60`) reached recall@5
`0.800` and MRR `0.462`.

This preview suggests a possible recall benefit from fusing lexical and vector ranks, with
a lower MRR than BM25 alone. It is not sufficient to establish that hybrid retrieval
recovers transformer quality: the transformer arm was not run, the sample is small, and
the synthetic query-to-section labels were authored for this preview and have not had
human review. These figures are not an N1/N3 gate and should not be compared with the
router accuracy figures in Spike D.

| Retriever | Recall@5 | MRR |
|---|---:|---:|
| SQLite FTS5 BM25 | 0.600 | 0.492 |
| Static vector cosine (`potion-base-8M`) | 0.533 | 0.399 |
| RRF, `k=60` | 0.800 | 0.462 |
| Transformer | Not run | Not run |

## Method

- **Corpus:** 14 Markdown files from `README.md`, `ROADMAP.md`, and `docs/` at product
  commit `5f2796f`. Heading-based chunks were capped at 200 whitespace-separated words:
  144 chunks total. SHA-256 of the ordered path/content input:
  `95c70d12083d83e0bf33e9c7d0483c82c05608cc9afc7d7d37c91edc19245807`.
- **Queries:** 15 synthetic questions, each mapped to one expected source section by the
  agent. The query set and per-query results are in the private Spike F run, not committed
  as an evaluation fixture. Multiple valid supporting sections were not judged; the labels
  and results need human review before reuse.
- **Lexical:** system SQLite `3.53.2`, in-memory FTS5, `unicode61`. Queries used OR across
  non-stopword terms; results were ordered by SQLite `bm25()`.
- **Vectors:** the already-exported Go `potion-base-8M` table from Spike E. Embeddings and
  centroids were not re-exported or downloaded. Cosine scores ranked all chunks.
- **Fusion:** standard reciprocal-rank score `sum(1 / (60 + rank))` over the FTS and
  static rankings. The parameter was not tuned on the preview set.
- **Metrics:** a question is a hit when a chunk in its one labeled source section occurs in
  the top five. MRR uses the first chunk from that section in the complete ranking.

## Limits and recommendation

The local project cache contains the MiniLM tokenizer/configuration but not the pinned
`model.onnx` weights. Therefore the transformer comparison was not run and Spike F is not
complete; no transformer model or ML runtime was downloaded for this preview.

Keep RRF as a candidate, not a conclusion. Before completing F, approve or provide the
transformer model locally, review and freeze a larger golden set with all valid supporting
sections, then rerun BM25, static, RRF, and transformer under identical chunking and
retrieval cutoffs. Do not tune `k` on the evaluation queries; use a separate validation
set if tuning becomes necessary.
