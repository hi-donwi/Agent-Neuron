# evals/router

Query sets for measuring the router. Every file listed in `SHA256SUMS` is frozen: a test in
`lab/tests` fails when one of them changes. A corrected set gets a new version and a new
file; the old one stays.

## skills-paraphrase-v1.json

Eighty-nine routing queries over the public
[Agent-Skills](https://github.com/hi-donwi/Agent-Skills) catalogue, one for each scenario
in that repository's `tests/scenarios.json` at commit
`70eaef555bf907b1a105c0f0e828300541637b50`. Each entry keeps the `id`, `expected_skill`,
and `pack` of the scenario it paraphrases, so the two sets line up one to one.

**Why it exists.** The public scenarios reuse the vocabulary of the skills they expect: the
median query shares 67% of its content words with its skill's own name, description,
keywords, and "when to use" bullets. A keyword scorer is close to perfect on such queries,
so they cannot show whether an embedding router adds anything. This set asks for the same
things in words the catalogue does not use.

**How it was written.**

- Each query describes the same task as its public scenario, the way a developer who has
  not read the catalogue might put it.
- Words from the expected skill's name, description, and keywords are avoided wherever
  ordinary English offers another way to say it. Names of products with no other name stay
  (`Quarkus`, `UIDL`, `Redis`, `React`).
- A different word was chosen, not a different inflection of the same word.
- Measured result: the median query shares none of its content words with its skill's text
  (75th percentile 9%, maximum 50%).

**What it is not.** It is the hard end of vocabulary mismatch, by construction, and it is
not a sample of real requests. A keyword scorer is expected to do badly on it; that drop is
a property of how the set was written, not a finding. Real requests fall somewhere between
this set and the public one.

**Provenance.** Synthetic. Written on 2026-11-14 by an AI coding agent (Claude Fable 5.2)
from the public scenario queries, before any embedding router was measured on either set.
Not yet reviewed by a human: sample it before relying on a number measured with it. It is
evaluation data and must not be used for training.

**Audience and licence.** Public. Apache-2.0, as the rest of this repository. The scenarios
it derives from are MIT-licensed.
