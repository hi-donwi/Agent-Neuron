# ADR-0002: Knowledge lives in retrieval, behaviour lives in weights

- **Date:** 2026-11-14
- **Status:** Proposed
- **Deciders:** Doni Wicaksono

## Context

A domain specialist needs two things: the domain's facts, and the domain's way of
answering (format, terminology, procedure, when to decline). There are two places to put
them: an index searched at request time, or the model's weights.

Models under one billion parameters store facts poorly and state wrong ones fluently.
Facts also change, and retraining on every change is slow on a small machine. On the
other hand, an untuned tiny model given retrieved text often ignores it, mixes it with
what it half remembers, or drifts from the requested format.

## Decision

Facts are never trained into weights. Every domain carries a knowledge pack, and a
request that needs facts retrieves them at request time and cites them.

Weights learn behaviour only: output format, domain vocabulary, the procedure for one
task, how to use supplied passages, how to ignore irrelevant ones, and how to decline when
the passages do not contain the answer. Generative neurons are therefore trained with
retrieval in the loop: examples contain supporting passages mixed with distractors, and a
declared share has no supporting passage and an abstention as its target (the approach
described as retrieval-augmented fine-tuning, RAFT, arXiv 2403.10131).

A new or changed fact triggers `neuron knowledge build`. Only a behaviour gap justifies a
training job, and the tool enforces that distinction in the growth loop.

## Consequences

### Positive
- Knowledge updates take a rebuild of an index, not a training run.
- Answers carry citations, and a deterministic verifier can check them.
- The same adapter keeps working when the documents change.

### Negative
- Every factual request pays for retrieval and for the prompt tokens of the passages,
  and prompt evaluation is the expensive part on a CPU.
- Quality is capped by retrieval: a passage that was not found cannot be used.
- Training data is more work to build, because each example needs passages and
  distractors, not just a question and an answer.

### Neutral
- The published RAFT results were obtained on larger models than the ones used here.
  Whether the gain holds below one billion parameters is measured in milestone N5, and
  retrieval quality with static vectors in Spike F.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Fine-tune facts into the weights | Stale after every change, no citations, and tiny models state memorised facts unreliably |
| Retrieval with an untuned base model | Tiny models use supplied context inconsistently and drift from the required format |
| Put all domain documents in a long context | Prompt evaluation time and memory grow with every token on a CPU; small models degrade in long contexts |
| A larger general model without retrieval | Does not meet the CPU-only, low-memory target |
