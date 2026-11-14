# Spike D: router quality

- **Date:** 2026-11-14
- **Status:** Measured
- **Informs:** [ADR-0004](../adr/0004-the-router-is-not-a-language-model.md) and
  [ADR-0005](../adr/0005-pure-go-runtime-python-lab-external-engine.md). Both stay Proposed;
  the decider changes a status, a spike does not.
- **Machine:** one Apple M3 laptop, 8 cores, 8 GB of memory, macOS (Darwin 27.0.0, arm64).
  Every number below was measured there, in Python. None is a vendor figure.
- **Script:** [`lab/spikes/router_quality.py`](../../lab/spikes/router_quality.py)

## The question

Are static embeddings accurate enough to choose a skill for a request, how well does the
router know when to refuse, and what does each kind of router cost?

## Answer

Static embeddings are fast enough by a wide margin, and they route requests that share no
words with the catalogue, which keyword scoring cannot do. With only the catalogue's own
text to learn from they are not accurate enough on such requests: the largest static table
got 44 of 89 right. The measurement supports a tiered router. It does not show that a
trained head earns its place yet, and it does not settle whether a transformer encoder is
needed.

- **The public scenario set cannot rank routers.** Every arm scored between 85 and 89 of
  89 on it, the untuned BM25 baseline 88. Its queries reuse the catalogue's vocabulary: the
  median query shares two thirds of its content words with its skill's own text.
- **On requests in other words, embeddings route and keywords do not.** On a paraphrase
  set written to share almost no words with the catalogue, the keyword arms got 2 and 7 of
  89, static embeddings 25, 35, and 44 by table size, and the transformer encoder 52. Each
  step up in static table size is a real gain (sign test p = 0.013 and 0.022). The step
  from the largest static table to the transformer is not distinguishable from noise at
  this sample size (9 queries against 17, p = 0.17).
- **A head trained on the catalogue's text does not beat the nearest centroid.** On every
  encoder and both sets the two are within two queries of each other. Adding the public
  scenarios from the other folds as training examples changed the outcome of at most two
  queries.
- **Refusing works out of domain.** A threshold chosen to accept 5% of the CLINC150
  validation queries accepted 2.8% to 6.1% of the CLINC150 test queries. Cosine similarity
  to the centroid separates paraphrases from out-of-domain queries better (AUROC 0.85 to
  0.93) than the head's temperature-scaled probability (0.43 to 0.73).
- **Static routing costs tens of microseconds.** One route took 43 to 75 microseconds at
  the median for the static arms, and about 2 milliseconds for the transformer: some
  thirty to forty times more.

## What was measured

Fourteen arms, three kinds of router. Each arm ranks the 68 skills of the catalogue for a
query; the top of the ranking is its answer, and the score of the top is its confidence.

| Kind | Arm | What it is |
|---|---|---|
| Keyword | `keyword-incumbent` | The Agent-Skills repository's own scorer (`bin/harness.py`), unmodified. Its keyword lists and weights are maintained against the public scenarios, so on that set it is a tuned baseline |
| Keyword | `keyword-bm25` | Okapi BM25 with the usual defaults (k1 1.5, b 0.75) over each skill's label texts. Nothing tuned |
| Static | `potion-base-2M`, `-8M`, `-32M` | A token table and a mean, no transformer layers. 64, 256, and 512 dimensions |
| Transformer | `all-MiniLM-L6-v2` | Six layers, 384 dimensions, mean pooling, at most 256 tokens. Full-precision ONNX on ONNX Runtime's CPU provider |

Each of the four encoders is measured with three scoring variants:

- `centroid`: cosine similarity to the unit mean of a skill's label texts. Nothing is
  trained.
- `head`: softmax regression over the label texts. Confidence is the top probability after
  temperature scaling.
- `head-cv`: the same head, with the public scenario queries from the other four folds
  added to its training texts. A query is always scored by a head that was trained without
  its fold.

A skill's **label texts** are its name, its description, each keyword, and each bullet
under "When to use" in its `SKILL.md`: 1229 short texts for 68 skills.

## Data

| Data | Source and pin | Licence | Role |
|---|---|---|---|
| Skill catalogue and public scenarios | [Agent-Skills](https://github.com/hi-donwi/Agent-Skills) at commit `70eaef555bf907b1a105c0f0e828300541637b50` | MIT | 68 skills; 89 scenario queries over 41 of them |
| Paraphrase set | [`evals/router/skills-paraphrase-v1.json`](../../evals/router/skills-paraphrase-v1.json), SHA-256 `162a9f50...0714` | Apache-2.0 | 89 queries, one per public scenario |
| Out-of-domain queries | [CLINC150](https://github.com/clinc/oos-eval) `data/data_full.json` at commit `828f8093932c8fe6ca7936c3d2e52903b1c523de` | CC BY 3.0 | 3100 queries to set the threshold, 5500 to test it |
| `potion-base-2M` | `minishlab/potion-base-2M` at `389b9f64be5aa4ae7a6bc6fe95ef20ce485ae5da` | MIT | Static encoder |
| `potion-base-8M` | `minishlab/potion-base-8M` at `bf8b056651a2c21b8d2565580b8569da283cab23` | MIT | Static encoder |
| `potion-base-32M` | `minishlab/potion-base-32M` at `1e5a03f8eeb2c98b928fbbd846f22f816360919f` | MIT | Static encoder |
| `all-MiniLM-L6-v2` | `sentence-transformers/all-MiniLM-L6-v2` at `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | Apache-2.0 | Transformer encoder |

Each licence is the one written on the publisher's own model card or repository at the
pinned revision. The script holds the SHA-256 of every downloaded file and checks all of
them on every run. Models and CLINC150 are downloaded into the git-ignored `.neuron/`
cache; none of them is in this repository.

The catalogue is read from a `git archive` of the pinned commit. Its content hash, over
the scenario file, the incumbent scorer, and every `SKILL.md`, is
`5a4ae1fa733f01250ccba31e421ad6ae31e3682a7a6fcb95216360db3bd1b49f`.

### Why there is a second query set

The public scenarios were written beside the catalogue and reuse its words. The share of a
query's distinct content words that also occur in its expected skill's label texts:

| Set | 25th percentile | Median | 75th percentile | Maximum | Queries at 50% or more |
|---|---|---|---|---|---|
| Public scenarios | 56% | 67% | 83% | 100% | 77 of 89 |
| Paraphrase set | 0% | 0% | 9% | 50% | 1 of 89 |

A keyword scorer is close to perfect on the first kind of query, so that set cannot show
whether an embedding adds anything. The paraphrase set asks for the same 89 things in
words the catalogue does not use. It is synthetic, written by an AI coding agent, and not
yet reviewed by a human; [its README](../../evals/router/README.md) says how it was
written. It is the hard end of vocabulary mismatch by construction, not a sample of real
requests. Real requests fall somewhere between the two sets.

### What was fixed before what

The catalogue commit and its content hash, the folds, and the paraphrase set and its hash
were fixed before any embedding arm scored a query. The paraphrase set was committed
before the models were downloaded. It was written after the keyword arms had been run on
the public set, and with the catalogue in view, which is how it avoids the catalogue's
words.

One choice was made after looking at a model's behaviour, and only on training texts: at
the usual default penalty (C = 1) the head fitted its own label texts poorly, so C is
chosen from 1, 10, and 100 by cross-fitted accuracy on the label texts. No evaluation
query takes part in that choice or in any other.

## Method

- **Split.** A scenario's fold is `sha256(id) mod 5`, so it never moves. A paraphrase has
  the id of the scenario it paraphrases, and therefore the same fold: `head-cv` never
  scores a paraphrase with a head that saw the original.
- **Accuracy.** Top-1 and top-3 over the 68 skills, with a Wilson 95% interval on top-1.
  Pack accuracy counts an answer as right when the predicted skill is in the expected
  skill's pack.
- **Near out-of-domain.** Each public scenario is scored again against a catalogue with
  its expected skill removed. The right answer is then "none of these". The AUROC is the
  chance that a query is more confident with its skill present than absent.
- **Far out-of-domain.** CLINC150 queries about banking, travel, small talk, and the like;
  none is a request for a skill. The validation and out-of-scope validation queries
  choose the threshold: the lowest one that accepts at most 5% of them. The test queries
  that do not also occur in validation report how often that threshold is wrong.
- **Head.** Softmax regression from a zero start, full-batch Adam, penalty
  l2 = 1 / (C x number of training texts). C and the temperature are chosen on cross-fitted
  training texts: each text is scored by a head fitted without its fifth of them. C came
  out as 10 for every encoder; temperatures were between 0.79 and 1.19.
- **Calibration.** Expected calibration error over ten equal-width bins, for the arms
  whose confidence is a probability.
- **Comparisons.** Two arms are compared on the same queries with an exact two-sided sign
  test over the queries exactly one of them got right.
- **Latency.** One call encodes one query, scores it against all 68 skills, and returns
  the best. After one warm-up pass, 20 passes over the 89 public queries give 1780 timed
  calls per arm, one at a time in one process. Percentiles are nearest rank.
- **Artifact size.** For a static encoder: `config.json`, `tokenizer.json`, and
  `model.safetensors`. For the transformer: `tokenizer.json` and `model.onnx`. Plus the
  centroids or the head as 32-bit floats.

The whole measurement was run twice. Every accuracy, abstention, and calibration number
was identical in both runs; only the timings differ, and both are shown.

## Results

### Public scenarios

| Arm | Top-1 | 95% interval | Top-3 | Pack |
|---|---|---|---|---|
| keyword-incumbent | 0.978 (87/89) | 0.922 to 0.994 | 1.000 | 0.989 |
| keyword-bm25 | 0.989 (88/89) | 0.939 to 0.998 | 1.000 | 0.989 |
| potion-base-2M-centroid | 0.966 (86/89) | 0.906 to 0.988 | 0.989 | 1.000 |
| potion-base-2M-head | 0.955 (85/89) | 0.890 to 0.982 | 0.989 | 1.000 |
| potion-base-2M-head-cv | 0.955 (85/89) | 0.890 to 0.982 | 0.989 | 1.000 |
| potion-base-8M-centroid | 0.989 (88/89) | 0.939 to 0.998 | 1.000 | 1.000 |
| potion-base-8M-head | 0.989 (88/89) | 0.939 to 0.998 | 0.989 | 0.989 |
| potion-base-8M-head-cv | 0.989 (88/89) | 0.939 to 0.998 | 0.989 | 0.989 |
| potion-base-32M-centroid | 0.989 (88/89) | 0.939 to 0.998 | 1.000 | 1.000 |
| potion-base-32M-head | 1.000 (89/89) | 0.959 to 1.000 | 1.000 | 1.000 |
| potion-base-32M-head-cv | 1.000 (89/89) | 0.959 to 1.000 | 1.000 | 1.000 |
| all-MiniLM-L6-v2-centroid | 0.989 (88/89) | 0.939 to 0.998 | 1.000 | 1.000 |
| all-MiniLM-L6-v2-head | 0.989 (88/89) | 0.939 to 0.998 | 0.989 | 1.000 |
| all-MiniLM-L6-v2-head-cv | 0.989 (88/89) | 0.939 to 0.998 | 0.989 | 1.000 |

The two queries the incumbent misses and the one BM25 misses are different from the one
query (`scenario-api-design-1`) that most embedding arms miss. None of the pairs compared
below differs on this set by more than two queries.

### Paraphrase set

| Arm | Top-1 | 95% interval | Top-3 | Pack |
|---|---|---|---|---|
| keyword-incumbent | 0.022 (2/89) | 0.006 to 0.078 | 0.079 | 0.573 |
| keyword-bm25 | 0.079 (7/89) | 0.039 to 0.154 | 0.169 | 0.528 |
| potion-base-2M-centroid | 0.281 (25/89) | 0.198 to 0.382 | 0.449 | 0.775 |
| potion-base-2M-head | 0.270 (24/89) | 0.188 to 0.370 | 0.461 | 0.663 |
| potion-base-2M-head-cv | 0.281 (25/89) | 0.198 to 0.382 | 0.438 | 0.708 |
| potion-base-8M-centroid | 0.393 (35/89) | 0.298 to 0.497 | 0.652 | 0.820 |
| potion-base-8M-head | 0.371 (33/89) | 0.278 to 0.475 | 0.584 | 0.652 |
| potion-base-8M-head-cv | 0.371 (33/89) | 0.278 to 0.475 | 0.618 | 0.652 |
| potion-base-32M-centroid | 0.494 (44/89) | 0.393 to 0.596 | 0.663 | 0.798 |
| potion-base-32M-head | 0.472 (42/89) | 0.372 to 0.575 | 0.640 | 0.742 |
| potion-base-32M-head-cv | 0.472 (42/89) | 0.372 to 0.575 | 0.629 | 0.775 |
| all-MiniLM-L6-v2-centroid | 0.584 (52/89) | 0.480 to 0.681 | 0.809 | 0.944 |
| all-MiniLM-L6-v2-head | 0.573 (51/89) | 0.469 to 0.671 | 0.775 | 0.843 |
| all-MiniLM-L6-v2-head-cv | 0.573 (51/89) | 0.469 to 0.671 | 0.764 | 0.843 |

### Paired comparisons on the paraphrase set

| First | Second | Only first right | Only second right | Sign test p |
|---|---|---|---|---|
| keyword-bm25 | potion-base-32M-centroid | 1 | 38 | < 0.0001 |
| potion-base-2M-centroid | potion-base-8M-centroid | 2 | 12 | 0.0129 |
| potion-base-8M-centroid | potion-base-32M-centroid | 2 | 11 | 0.0225 |
| potion-base-32M-centroid | all-MiniLM-L6-v2-centroid | 9 | 17 | 0.1686 |
| potion-base-32M-centroid | potion-base-32M-head | 7 | 5 | 0.7744 |
| all-MiniLM-L6-v2-centroid | all-MiniLM-L6-v2-head | 7 | 6 | 1.0000 |

### Abstention

"Near AUROC" is the near out-of-domain case on the public scenarios. "Far AUROC" is the
chance that a public scenario (`pub`) or a paraphrase (`para`) is more confident than a
CLINC150 test query. "False accept" is the share of the 5500 CLINC150 test queries above
the arm's threshold; the target was 0.05. "Answered" is the share of the 89 queries above
that threshold, and "right" the share of the 89 that were answered and correct. ECE is
the expected calibration error.

| Arm | Near AUROC | Far AUROC pub | Far AUROC para | False accept | Pub answered | Pub right | Para answered | Para right | ECE pub | ECE para |
|---|---|---|---|---|---|---|---|---|---|---|
| keyword-incumbent | 0.961 | 1.000 | 0.849 | 0.028 | 1.000 | 0.978 | 0.281 | 0.011 | - | - |
| keyword-bm25 | 0.987 | 1.000 | 0.937 | 0.040 | 1.000 | 0.989 | 0.607 | 0.045 | - | - |
| potion-base-2M-centroid | 0.925 | 0.991 | 0.851 | 0.043 | 0.944 | 0.910 | 0.303 | 0.146 | - | - |
| potion-base-2M-head | 0.941 | 0.924 | 0.425 | 0.056 | 0.764 | 0.753 | 0.034 | 0.011 | 0.311 | 0.111 |
| potion-base-2M-head-cv | 0.948 | 0.933 | 0.431 | 0.054 | 0.764 | 0.753 | 0.034 | 0.011 | 0.265 | 0.107 |
| potion-base-8M-centroid | 0.977 | 0.999 | 0.904 | 0.048 | 1.000 | 0.989 | 0.348 | 0.225 | - | - |
| potion-base-8M-head | 0.976 | 0.987 | 0.558 | 0.056 | 0.944 | 0.944 | 0.112 | 0.079 | 0.086 | 0.116 |
| potion-base-8M-head-cv | 0.976 | 0.987 | 0.554 | 0.054 | 0.944 | 0.944 | 0.101 | 0.079 | 0.076 | 0.106 |
| potion-base-32M-centroid | 0.979 | 1.000 | 0.906 | 0.047 | 1.000 | 0.989 | 0.404 | 0.281 | - | - |
| potion-base-32M-head | 0.977 | 0.992 | 0.601 | 0.059 | 0.989 | 0.989 | 0.157 | 0.146 | 0.056 | 0.148 |
| potion-base-32M-head-cv | 0.977 | 0.992 | 0.600 | 0.059 | 0.989 | 0.989 | 0.146 | 0.135 | 0.050 | 0.135 |
| all-MiniLM-L6-v2-centroid | 0.944 | 0.992 | 0.929 | 0.054 | 0.955 | 0.944 | 0.618 | 0.404 | - | - |
| all-MiniLM-L6-v2-head | 0.968 | 0.991 | 0.732 | 0.060 | 0.978 | 0.978 | 0.315 | 0.303 | 0.060 | 0.142 |
| all-MiniLM-L6-v2-head-cv | 0.970 | 0.991 | 0.734 | 0.061 | 0.978 | 0.978 | 0.303 | 0.303 | 0.050 | 0.143 |

Read together with the accuracy tables: at its threshold the `potion-base-32M` centroid
answers 36 paraphrases and is right on 25; its head answers 14 and is right on 13. For
`all-MiniLM-L6-v2` the centroid answers 55 and is right on 36; the head answers 28 and is
right on 27. The head refuses more and is rarely wrong when it answers. The centroid
answers more and is right more often in total.

### Cost

| Arm | Artifact | Of which centroids or head | p50, run 1 | p95, run 1 | p50, run 2 | p95, run 2 |
|---|---|---|---|---|---|---|
| keyword-incumbent | none | - | 1.24 ms | 2.63 ms | 1.15 ms | 1.22 ms |
| keyword-bm25 | none | - | 49 us | 103 us | 44 us | 53 us |
| potion-base-2M-centroid | 8.3 MB | 17.4 kB | 53 us | 249 us | 43 us | 48 us |
| potion-base-2M-head | 8.3 MB | 17.7 kB | 75 us | 372 us | 49 us | 56 us |
| potion-base-2M-head-cv | 8.3 MB | 17.7 kB | 64 us | 210 us | 47 us | 53 us |
| potion-base-8M-centroid | 31.0 MB | 69.6 kB | 64 us | 215 us | 50 us | 59 us |
| potion-base-8M-head | 31.0 MB | 69.9 kB | 66 us | 200 us | 54 us | 63 us |
| potion-base-8M-head-cv | 31.0 MB | 69.9 kB | 74 us | 420 us | 53 us | 58 us |
| potion-base-32M-centroid | 130.8 MB | 139.3 kB | 75 us | 333 us | 51 us | 61 us |
| potion-base-32M-head | 130.8 MB | 139.5 kB | 60 us | 100 us | 57 us | 80 us |
| potion-base-32M-head-cv | 130.8 MB | 139.5 kB | 60 us | 120 us | 55 us | 66 us |
| all-MiniLM-L6-v2-centroid | 91.0 MB | 104.4 kB | 2.19 ms | 3.84 ms | 2.16 ms | 4.17 ms |
| all-MiniLM-L6-v2-head | 91.0 MB | 104.7 kB | 1.96 ms | 2.53 ms | 2.12 ms | 4.30 ms |
| all-MiniLM-L6-v2-head-cv | 91.0 MB | 104.7 kB | 1.93 ms | 2.46 ms | 2.01 ms | 2.91 ms |

Times are per route; `us` is microseconds. The static arms' tail was several times longer
in the first run than in the second, and the transformer's tail varied in both: the
machine was running other work and nothing isolated the measurement. Encoding all 9931
distinct texts of the experiment took 0.1 to 0.4 seconds for a static encoder and 17 to 22
seconds for the transformer.

## What the numbers mean

### For ADR-0004

| Claim in the ADR | What this spike found |
|---|---|
| Routing costs milliseconds and no model load | Supported for the Python reference on this machine. Static routing is under half a millisecond at p95 in the worse run; the transformer is under 5 ms |
| Rules only do not generalise to paraphrases | Supported: 2 and 7 of 89. The converse also holds: when a request uses the catalogue's words, BM25 gets 88 of 89 at about 45 microseconds, so the first tier earns its place |
| A tier of nearest centroid over static embeddings | Supported as the tier that handles other wording, and it is the best static variant measured. At 25 to 44 of 89 on the hard set it is not sufficient alone |
| A trained head for established labels | Not shown. Trained on label texts, the head is no more accurate than the centroid. This catalogue has no query-shaped training data beyond the 89 scenarios (19 skills have exactly one), so the head's case is untested, not refuted |
| Nearest neighbour only has no calibrated confidence, so no trustworthy abstention | Not supported as written. Only nearest centroid was measured, not nearest neighbour. A threshold on its cosine similarity held the far out-of-domain false-accept rate (4.3% to 5.4% against a 5% target) and separated skill requests from far out-of-domain queries at least as well as the head's probability on every encoder. Near out-of-domain the head was ahead on two encoders (AUROC 0.94 against 0.92, and 0.97 against 0.94) and level on the other two. A cosine is not a probability, but refusing needed only a threshold |
| Confidence is calibrated on held-out data that includes out-of-domain inputs | Partly. The threshold transferred from validation to test within about one point. The head's probability is not well calibrated on queries (expected calibration error 0.05 to 0.31 on the public set, 0.11 to 0.15 on paraphrases): label texts are not shaped like queries |
| A domain where static embeddings are not enough needs a small transformer encoder | Its cost is now known: 91 MB and about 2 ms per route. Whether this catalogue needs it is not settled: 52 against 44 of 89 is within sampling noise |
| Hierarchical routing: domain, then sub-domain, then task | Not measured. All arms classify flat over 68 skills. Pack accuracy is reported but says little here: 73 of 89 scenarios expect the `core` pack, so always answering `core` scores 82%, and the static centroids score 78% to 82% on paraphrases |

The ADR's context quotes a vendor figure of roughly four fifths of a small transformer's
retrieval quality. On the paraphrase set the static tables reached 85% (32M), 67% (8M),
and 48% (2M) of the transformer's hits. The intervals are wide and this is routing in one
catalogue, not retrieval, so the figures do not confirm or contradict the vendor's.

Two things the decider may want to weigh that the ADR does not mention:

- The 32M table is 131 MB as shipped, larger than the transformer's 91 MB. Static wins on
  latency and on needing no inference engine, not on size. A quantised table was not
  measured.
- Table size matters more than the scoring variant. Going from 2M to 32M parameters
  gained 19 paraphrase queries; going from centroid to head gained none on any encoder.

### For ADR-0005

The Python reference that Spike E must reproduce in Go is small: tokenise, look up and
average rows of one table, normalise, and take a dot product with 68 centroids. No arm
that did well needs more than that, except the transformer.

### For the budgets and N1

- **Route, 10 ms p95.** One static encode and score took at most 0.42 ms at p95 across
  both runs in Python on this machine. One encoding can serve all three levels, so the
  budget looks loose by more than an order of magnitude, but it is a budget for the
  `tiny` profile and nothing was measured on that hardware or in Go. It stays provisional.
- **N1 exit criterion.** "On the public scenario set the router beats the keyword baseline
  by a recorded margin" cannot be met as written: BM25 is already at 88 of 89, and the
  best router here is at 89. The criterion needs a set on which the baseline can lose,
  such as a reviewed successor to the paraphrase set. That amendment is the owner's
  decision and is not made here.

## Limits of this measurement

- **Eighty-nine queries per set.** The intervals are 10 points wide on either side at 50%.
  Differences of a few queries mean nothing.
- **The paraphrase set is synthetic and unreviewed**, written by the same agent that ran
  the spike, and built to defeat keyword overlap. The keyword arms' collapse on it is a
  property of its construction. It was written before any embedding arm was measured, but
  it favours no arm only to the extent that avoiding the catalogue's words does not favour
  one embedding over another.
- **Twenty-seven of the 68 skills have no scenario.** They are distractors only; nothing
  here measures whether a request for one of them is routed correctly.
- **One catalogue, in English**, about software engineering. Nothing is known yet about
  other domains or languages.
- **The head never saw real queries** in bulk. Its result says what label texts alone can
  teach, not what a head trained on a few hundred real requests would do.
- **Far out-of-domain is one dataset.** CLINC150 is far from software engineering. The
  near out-of-domain case, a plausible request for a skill that does not exist, has an
  AUROC between 0.92 and 0.99 but no threshold was set from it.
- **One transformer model, full precision only.** A quantised or smaller encoder was not
  measured.
- **Latency is a Python reference on a laptop** with 8 GB of memory that was also running
  other work. It bounds what Go must match; it is not a measurement of the runtime or of
  any profile. Memory per router was not measured: the peak resident size of the whole
  process, which holds every encoder in turn and all the CLINC150 vectors, was 389 MB and
  438 MB in the two runs.

## Reproduce

```bash
cd lab && uv run --locked --group spikes python -I spikes/router_quality.py --skills-repo <path> --download
```

`<path>` is a clone of Agent-Skills at any commit; the script extracts the commit it pins
and checks its content hash. `--download` fetches about 265 MB on the first run. The
tables above are the script's own output; per-query results are written to
`.neuron/spikes/router-quality/results.json`. A full run took 246 and 300 seconds.

Versions: Python 3.13.14, numpy 2.5.4, model2vec 0.10.0, tokenizers 0.23.3,
onnxruntime 1.32.0, all pinned by `lab/uv.lock`.
