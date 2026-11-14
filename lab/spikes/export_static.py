"""Export a cached model2vec table and frozen Python references for Spike E.

    uv run --locked --group spikes python -I spikes/export_static.py

The model, tokenizer vocabulary, and reference arrays are written only to the
git-ignored .neuron cache. This script never downloads assets.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from model2vec import StaticModel

from neuron_lab.head import centroids, unit_rows
from neuron_lab.skillset import label_texts, load_catalogue, load_scenarios

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".neuron" / "spikes" / "router-quality"
MODELS = ("potion-base-2M", "potion-base-8M", "potion-base-32M")
TOLERANCE = 1e-5
LATENCY_REPEATS = 20


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", choices=MODELS, default="potion-base-8M")
    parser.add_argument(
        "--out",
        type=Path,
    )
    args = parser.parse_args()
    output = args.out or ROOT / ".neuron" / "spikes" / "go-parity" / args.model

    model_dir = CACHE / "models" / args.model
    snapshot = CACHE / "agent-skills-70eaef555bf9"
    for path in (model_dir / "model.safetensors", model_dir / "tokenizer.json", snapshot):
        if not path.exists():
            raise SystemExit(
                f"required cached asset is missing: {path}; this script does not download"
            )

    catalogue = load_catalogue(snapshot)
    labels = [skill.name for skill in catalogue]
    texts_by_skill = [label_texts(skill) for skill in catalogue]
    label_texts_flat = [text for texts in texts_by_skill for text in texts]
    label_ids = np.repeat(np.arange(len(catalogue)), [len(texts) for texts in texts_by_skill])

    public = load_scenarios(snapshot / "tests" / "scenarios.json")
    paraphrases = load_scenarios(ROOT / "evals" / "router" / "skills-paraphrase-v1.json")
    scenarios = public + paraphrases
    queries = [item.query for item in scenarios]

    model = StaticModel.from_pretrained(model_dir, force_download=False)
    label_vectors = unit_rows(
        np.asarray(model.encode(label_texts_flat, use_multiprocessing=False), dtype=np.float64)
    )
    centers = centroids(label_vectors, label_ids, len(labels))
    query_vectors = unit_rows(
        np.asarray(model.encode(queries, use_multiprocessing=False), dtype=np.float64)
    )
    scores = query_vectors @ centers.T

    public_queries = [item.query for item in public]
    for query in public_queries:
        vector = unit_rows(
            np.asarray(model.encode([query], use_multiprocessing=False), dtype=np.float64)
        )[0]
        centers @ vector
    latency_samples = []
    for _ in range(LATENCY_REPEATS):
        for query in public_queries:
            started = time.perf_counter_ns()
            vector = unit_rows(
                np.asarray(model.encode([query], use_multiprocessing=False), dtype=np.float64)
            )[0]
            centers @ vector
            latency_samples.append((time.perf_counter_ns() - started) / 1_000)
    latency_samples.sort()
    python_latency = {
        "calls": len(latency_samples),
        "p50_us": latency_samples[int(np.ceil(0.50 * len(latency_samples))) - 1],
        "p95_us": latency_samples[int(np.ceil(0.95 * len(latency_samples))) - 1],
    }

    output.mkdir(parents=True, exist_ok=True)
    np.asarray(model.embedding, dtype="<f4").tofile(output / "embeddings.f32")
    np.asarray(centers, dtype="<f4").tofile(output / "centroids.f32")
    vocabulary = model.tokenizer.get_vocab()
    (output / "model.json").write_text(
        json.dumps(
            {
                "dimension": int(model.dim),
                "max_tokens": model.max_length,
                "max_characters": model.max_length * model.median_token_length,
                "unknown_id": model.unk_token_id,
                "vocabulary": vocabulary,
                "labels": labels,
            },
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    np.asarray(query_vectors, dtype="<f8").tofile(output / "vectors.f64")
    np.asarray(scores, dtype="<f8").tofile(output / "scores.f64")
    (output / "parity.json").write_text(
        json.dumps(
            {
                "queries": queries,
                "dimension": int(model.dim),
                "labels": labels,
                "cases": len(queries),
                "public_cases": len(public),
                "tolerance": TOLERANCE,
                "python_latency": python_latency,
                "vectors_file": "vectors.f64",
                "scores_file": "scores.f64",
            },
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"exported {args.model}: {len(queries)} queries, {len(labels)} labels to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
