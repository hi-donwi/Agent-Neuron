"""Spike D: router quality on the public Agent-Skills scenario set.

Measures how well a query is routed to one of the skills in the catalogue, and how well
the router's confidence separates queries it should refuse, for three kinds of router:
keyword scoring, static embeddings, and a small transformer encoder. Method, data, and
results are written up in docs/spikes/d-router-quality.md.

    uv run --locked --group spikes python -I spikes/router_quality.py \
        --skills-repo <clone of hi-donwi/Agent-Skills> [--download]

The clone may be at any commit and in any state: the pinned commit is extracted with
`git archive` into the git-ignored cache, and its content hash is checked before use.
Models and out-of-domain data are fetched only with --download, at pinned revisions, and
every file is checked against a pinned SHA-256 on every run.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

# The spike reads models from its own cache; nothing may reach for the network on import.
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import numpy as np  # noqa: E402

from neuron_lab.head import (  # noqa: E402
    centroids,
    fit_softmax,
    fit_temperature,
    softmax,
    unit_rows,
)
from neuron_lab.lexical import BM25, overlap_share  # noqa: E402
from neuron_lab.metrics import (  # noqa: E402
    auroc,
    expected_calibration_error,
    paired_sign_test,
    percentile,
    threshold_for_false_accept,
    wilson_interval,
)
from neuron_lab.skillset import (  # noqa: E402
    Scenario,
    Skill,
    content_hash,
    fold_of,
    label_texts,
    load_catalogue,
    load_scenarios,
)

SKILLS_COMMIT = "70eaef555bf907b1a105c0f0e828300541637b50"
DATASET_SHA256 = "5a4ae1fa733f01250ccba31e421ad6ae31e3682a7a6fcb95216360db3bd1b49f"
PARAPHRASE_SHA256 = "162a9f5013b0d894862a5cd87d22efaf42ac65fac6623bffaaa61761bd050714"
FOLDS = 5
LATENCY_REPEATS = 20
FALSE_ACCEPT_RATE = 0.05

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE = REPO_ROOT / ".neuron" / "spikes" / "router-quality"
PARAPHRASE_SET = REPO_ROOT / "evals" / "router" / "skills-paraphrase-v1.json"

STATIC_ENCODERS = ("potion-base-2M", "potion-base-8M", "potion-base-32M")
TRANSFORMER_ENCODERS = ("all-MiniLM-L6-v2",)
VARIANTS = ("centroid", "head", "head-cv")
STRENGTHS = (1.0, 10.0, 100.0)  # inverse penalty, as C in scikit-learn's LogisticRegression

_HF = "https://huggingface.co"
_POTION_2M = f"{_HF}/minishlab/potion-base-2M/resolve/389b9f64be5aa4ae7a6bc6fe95ef20ce485ae5da"
_POTION_8M = f"{_HF}/minishlab/potion-base-8M/resolve/bf8b056651a2c21b8d2565580b8569da283cab23"
_POTION_32M = f"{_HF}/minishlab/potion-base-32M/resolve/1e5a03f8eeb2c98b928fbbd846f22f816360919f"
_MINILM = (
    f"{_HF}/sentence-transformers/all-MiniLM-L6-v2/resolve/1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
)
_CLINC = "https://raw.githubusercontent.com/clinc/oos-eval/828f8093932c8fe6ca7936c3d2e52903b1c523de"

# Arms compared case by case on the same queries: best keyword against best static,
# static table sizes against each other, static against the transformer, centroid
# against head.
PAIRS = (
    ("keyword-bm25", "potion-base-32M-centroid"),
    ("potion-base-2M-centroid", "potion-base-8M-centroid"),
    ("potion-base-8M-centroid", "potion-base-32M-centroid"),
    ("potion-base-32M-centroid", "all-MiniLM-L6-v2-centroid"),
    ("potion-base-32M-centroid", "potion-base-32M-head"),
    ("all-MiniLM-L6-v2-centroid", "all-MiniLM-L6-v2-head"),
)

Ranking = list[tuple[str, float]]


@dataclass(frozen=True)
class Asset:
    path: str
    url: str
    size: int
    sha256: str


# Licences as written on each publisher's own page: potion-base-* MIT, all-MiniLM-L6-v2
# Apache-2.0, CLINC150 (clinc/oos-eval) CC BY 3.0.
ASSETS = (
    Asset(
        "models/potion-base-2M/config.json",
        f"{_POTION_2M}/config.json",
        200,
        "b2a89173391ca774c2d7323090a993a9a1553faa5b40eb37bb7cec6685fbea47",
    ),
    Asset(
        "models/potion-base-2M/tokenizer.json",
        f"{_POTION_2M}/tokenizer.json",
        683666,
        "e67e803f624fb4d67dea1c730d06e1067e1b14d830e2c2202569e3ef0f70bb50",
    ),
    Asset(
        "models/potion-base-2M/model.safetensors",
        f"{_POTION_2M}/model.safetensors",
        7559256,
        "f95ffde02ad06f63ae38eb9d400038cd5ccaf8411ec3cb650c6025113f96cbb8",
    ),
    Asset(
        "models/potion-base-8M/config.json",
        f"{_POTION_8M}/config.json",
        202,
        "2a6ac0e9aaa356a68a5688070db78fc3a464fefe85d2f06a1905ce3718687553",
    ),
    Asset(
        "models/potion-base-8M/tokenizer.json",
        f"{_POTION_8M}/tokenizer.json",
        683666,
        "e67e803f624fb4d67dea1c730d06e1067e1b14d830e2c2202569e3ef0f70bb50",
    ),
    Asset(
        "models/potion-base-8M/model.safetensors",
        f"{_POTION_8M}/model.safetensors",
        30236760,
        "f65d0f325faadc1e121c319e2faa41170d3fa07d8c89abd48ca5358d9a223de2",
    ),
    Asset(
        "models/potion-base-32M/config.json",
        f"{_POTION_32M}/config.json",
        202,
        "63c00d90824c832c04ec1d02b6a983fb90489bf049f29fbff15ba481b8a432ee",
    ),
    Asset(
        "models/potion-base-32M/tokenizer.json",
        f"{_POTION_32M}/tokenizer.json",
        1493150,
        "7d75cbc54318138807c401b0f0c9721117c628b39de8e8e0edb6cb17e0ee7d18",
    ),
    Asset(
        "models/potion-base-32M/model.safetensors",
        f"{_POTION_32M}/model.safetensors",
        129210456,
        "99f6c33204c9231a7391871b7a3c91409b532c8f587a9ea44fc282303d8dec28",
    ),
    Asset(
        "models/all-MiniLM-L6-v2/tokenizer.json",
        f"{_MINILM}/tokenizer.json",
        466247,
        "be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037",
    ),
    Asset(
        "models/all-MiniLM-L6-v2/model.onnx",
        f"{_MINILM}/onnx/model.onnx",
        90405214,
        "6fd5d72fe4589f189f8ebc006442dbb529bb7ce38f8082112682524616046452",
    ),
    Asset(
        "data/clinc150/data_full.json",
        f"{_CLINC}/data/data_full.json",
        2495390,
        "36923c3705a59e08fe9c3883d8bc2dd966ef93e22cb78ac41171782a698d56e0",
    ),
)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_assets(download: bool) -> None:
    """Check every asset against its pinned hash; fetch the missing ones if allowed."""
    missing = [asset for asset in ASSETS if not (CACHE / asset.path).is_file()]
    if missing and not download:
        total = sum(asset.size for asset in missing) / 1e6
        names = "\n  ".join(asset.path for asset in missing)
        raise SystemExit(
            f"{len(missing)} asset(s) are not in the cache ({total:.1f} MB to fetch):\n  {names}\n"
            "Run again with --download to fetch them."
        )
    for asset in missing:
        target = CACHE / asset.path
        target.parent.mkdir(parents=True, exist_ok=True)
        part = target.with_name(target.name + ".part")
        request = urllib.request.Request(asset.url, headers={"User-Agent": "neuron-lab-spike"})
        with urllib.request.urlopen(request, timeout=120) as response, open(part, "wb") as handle:
            while chunk := response.read(1 << 20):
                handle.write(chunk)
        part.rename(target)
    for asset in ASSETS:
        found = sha256_of(CACHE / asset.path)
        if found != asset.sha256:
            raise SystemExit(f"{asset.path}: expected SHA-256 {asset.sha256}, found {found}")


def snapshot(skills_repo: Path) -> Path:
    """Extract the pinned commit of the skills repository and verify its content."""
    target = CACHE / f"agent-skills-{SKILLS_COMMIT[:12]}"
    if not target.is_dir():
        target.mkdir(parents=True)
        archive = subprocess.run(
            ["git", "-C", str(skills_repo), "archive", SKILLS_COMMIT],
            check=True,
            capture_output=True,
        )
        subprocess.run(["tar", "-x", "-C", str(target)], input=archive.stdout, check=True)
    files = [
        target / "tests" / "scenarios.json",
        target / "bin" / "harness.py",
        *sorted(target.glob("skills/*/SKILL.md")),
    ]
    found = content_hash(target, files)
    if found != DATASET_SHA256:
        raise SystemExit(f"dataset hash mismatch: expected {DATASET_SHA256}, found {found}")
    return target


def load_far_ood() -> tuple[list[str], list[str]]:
    """CLINC150 queries (banking, travel, small talk, ...): none is a skill request.

    The validation queries choose the abstention threshold; the test queries, minus any
    that also appear in validation, report how often that threshold is wrong.
    """
    data = json.loads((CACHE / "data" / "clinc150" / "data_full.json").read_text("utf-8"))
    calibration = list(dict.fromkeys(text for text, _ in data["val"] + data["oos_val"]))
    seen = set(calibration)
    test = list(dict.fromkeys(text for text, _ in data["test"] + data["oos_test"]))
    return calibration, [text for text in test if text not in seen]


class IncumbentKeyword:
    """The skills repository's own lexical scorer, unmodified, at the pinned commit.

    Its keyword lists and weights are maintained against the public scenario set, so on
    that set it is a tuned baseline, not a blind one.
    """

    name = "keyword-incumbent"
    family = "keyword"
    artifact_bytes = 0
    calibrated = False

    def __init__(self, root: Path) -> None:
        spec = importlib.util.spec_from_file_location("skills_harness", root / "bin" / "harness.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        self._score = module.score_skill
        self._skills = module.load_all_skills(root / "skills")

    def rank(self, query: str, exclude: str | None = None, fold: int | None = None) -> Ranking:
        scored = [
            (name, float(self._score(query, skill)))
            for name, skill in self._skills.items()
            if name != exclude
        ]
        # The harness drops zero scores and keeps catalogue order among ties.
        scored = [item for item in scored if item[1] > 0]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored

    def route(self, query: str) -> Ranking:
        return self.rank(query)[:1]


class Bm25Keyword:
    """Untuned BM25 over each skill's name, description, keywords, and bullets."""

    name = "keyword-bm25"
    family = "keyword"
    artifact_bytes = 0
    calibrated = False

    def __init__(self, catalogue: list[Skill]) -> None:
        self._catalogue = catalogue
        self._indexes: dict[str | None, tuple[list[str], BM25]] = {}

    def _index(self, exclude: str | None) -> tuple[list[str], BM25]:
        if exclude not in self._indexes:
            skills = [skill for skill in self._catalogue if skill.name != exclude]
            documents = [" ".join(label_texts(skill)) for skill in skills]
            self._indexes[exclude] = ([skill.name for skill in skills], BM25(documents))
        return self._indexes[exclude]

    def rank(self, query: str, exclude: str | None = None, fold: int | None = None) -> Ranking:
        names, index = self._index(exclude)
        scored = [item for item in zip(names, index.scores(query), strict=True) if item[1] > 0]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored

    def route(self, query: str) -> Ranking:
        return self.rank(query)[:1]


class StaticEncoder:
    """A static embedding model: a token table and a mean, read by model2vec."""

    family = "static"

    def __init__(self, key: str) -> None:
        from model2vec import StaticModel

        folder = CACHE / "models" / key
        self.key = key
        self._model = StaticModel.from_pretrained(folder)
        self.dim = int(self._model.dim)
        self.artifact_bytes = sum(
            (folder / name).stat().st_size
            for name in ("config.json", "tokenizer.json", "model.safetensors")
        )

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = self._model.encode(list(texts), use_multiprocessing=False)
        return unit_rows(np.asarray(vectors, dtype=np.float64))


class OnnxEncoder:
    """A sentence-transformers encoder run by ONNX Runtime on the CPU: mean pooling."""

    family = "transformer"
    batch = 32
    max_tokens = 256  # the model's own max_seq_length (sentence_bert_config.json)

    def __init__(self, key: str) -> None:
        import onnxruntime
        from tokenizers import Tokenizer

        folder = CACHE / "models" / key
        self.key = key
        self._tokenizer = Tokenizer.from_file(str(folder / "tokenizer.json"))
        self._tokenizer.enable_truncation(max_length=self.max_tokens)
        self._tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        self._session = onnxruntime.InferenceSession(
            str(folder / "model.onnx"), providers=["CPUExecutionProvider"]
        )
        outputs = [output.name for output in self._session.get_outputs()]
        if outputs != ["last_hidden_state"]:
            raise SystemExit(f"{key}: unexpected model outputs {outputs}")
        self.dim = int(self._session.get_outputs()[0].shape[-1])
        self.artifact_bytes = sum(
            (folder / name).stat().st_size for name in ("tokenizer.json", "model.onnx")
        )

    def encode(self, texts: list[str]) -> np.ndarray:
        pooled = []
        for start in range(0, len(texts), self.batch):
            encodings = self._tokenizer.encode_batch(list(texts[start : start + self.batch]))
            mask = np.array([item.attention_mask for item in encodings], dtype=np.int64)
            feeds = {
                "input_ids": np.array([item.ids for item in encodings], dtype=np.int64),
                "attention_mask": mask,
                "token_type_ids": np.array([item.type_ids for item in encodings], dtype=np.int64),
            }
            hidden = self._session.run(None, feeds)[0].astype(np.float64)
            weights = mask[:, :, None].astype(np.float64)
            pooled.append((hidden * weights).sum(axis=1) / weights.sum(axis=1))
        return unit_rows(np.concatenate(pooled, axis=0))


class EmbeddingArm:
    """A router over one encoder's vectors.

    centroid: nearest label centroid; confidence is the cosine similarity.
    head:     softmax regression trained on the label texts only; confidence is the top
              probability after temperature scaling.
    head-cv:  the same head, with the public scenario queries from the other folds added
              to its training texts. A query is always scored by a head that was trained
              without its fold, so no query is ever scored by a head that saw it.

    Nothing is tuned on the evaluation queries. The penalty is l2 = 1 / (C x number of
    training texts), with C chosen from STRENGTHS by cross-fitted accuracy on the label
    texts: each label text is scored by a head fitted without its fifth of them. The
    temperature is fitted the same way, on the cross-fitted logits of the training texts.
    """

    def __init__(
        self,
        encoder,
        vectors: dict[str, np.ndarray],
        catalogue: list[Skill],
        scenarios: list[Scenario],
        variant: str,
    ) -> None:
        self.name = f"{encoder.key}-{variant}"
        self.family = encoder.family
        self.calibrated = variant != "centroid"
        self._encoder = encoder
        self._vectors = vectors
        self._variant = variant
        self._skills = [skill.name for skill in catalogue]
        self._labelled = [(skill.name, text) for skill in catalogue for text in label_texts(skill)]
        self._examples = (
            [(item.expected_skill, item.query, fold_of(item.id, FOLDS)) for item in scenarios]
            if variant == "head-cv"
            else []
        )
        self._models: dict[tuple[str | None, int | None], tuple] = {}
        self._temperatures: dict[int | None, float] = {}
        self.strength, self.selection = self._select() if self.calibrated else (None, {})
        _, weights, bias, _ = self._model(None, self._fold(None))
        head_bytes = weights.astype(np.float32).nbytes
        head_bytes += 0 if bias is None else bias.astype(np.float32).nbytes
        self.head_bytes = head_bytes
        self.artifact_bytes = encoder.artifact_bytes + head_bytes

    def _fold(self, fold: int | None) -> int | None:
        if self._variant != "head-cv":
            return None
        return 0 if fold is None else fold

    def _training(self, exclude: str | None, fold: int | None, examples: bool = True):
        rows = [(skill, text) for skill, text in self._labelled if skill != exclude]
        if examples:
            rows += [
                (skill, text)
                for skill, text, part in self._examples
                if skill != exclude and part != fold
            ]
        names = [name for name in self._skills if name != exclude]
        index = {name: position for position, name in enumerate(names)}
        data = np.stack([self._vectors[text] for _, text in rows])
        labels = np.array([index[skill] for skill, _ in rows])
        return names, [text for _, text in rows], data, labels

    @staticmethod
    def _cross_fitted(texts, data, labels, classes: int, strength: float) -> np.ndarray:
        """Logits for every training text from a head fitted without its fifth of them."""
        parts = np.array([fold_of(text, FOLDS) for text in texts])
        logits = np.zeros((len(labels), classes))
        for part in range(FOLDS):
            held = parts == part
            weights, bias = fit_softmax(
                data[~held], labels[~held], classes, l2=1.0 / (strength * int((~held).sum()))
            )
            logits[held] = data[held] @ weights.T + bias
        return logits

    def _select(self) -> tuple[float, dict[str, float]]:
        """Choose C on the label texts alone; a tie goes to the stronger penalty."""
        names, texts, data, labels = self._training(None, None, examples=False)
        accuracy = {}
        for strength in STRENGTHS:
            logits = self._cross_fitted(texts, data, labels, len(names), strength)
            accuracy[strength] = float((logits.argmax(axis=1) == labels).mean())
        best = max(STRENGTHS, key=lambda strength: (accuracy[strength], -strength))
        return best, {f"{strength:g}": value for strength, value in accuracy.items()}

    def _temperature(self, fold: int | None) -> float:
        if fold not in self._temperatures:
            names, texts, data, labels = self._training(None, fold)
            logits = self._cross_fitted(texts, data, labels, len(names), self.strength)
            self._temperatures[fold] = fit_temperature(logits, labels)
        return self._temperatures[fold]

    def _model(self, exclude: str | None, fold: int | None) -> tuple:
        key = (exclude, fold)
        if key not in self._models:
            names, _, data, labels = self._training(exclude, fold)
            if self._variant == "centroid":
                self._models[key] = (names, centroids(data, labels, len(names)), None, 1.0)
            else:
                penalty = 1.0 / (self.strength * len(labels))
                weights, bias = fit_softmax(data, labels, len(names), l2=penalty)
                self._models[key] = (names, weights, bias, self._temperature(fold))
        return self._models[key]

    def temperatures(self) -> list[float]:
        return [self._temperatures[key] for key in sorted(self._temperatures, key=str)]

    def _scores(self, vector: np.ndarray, exclude: str | None, fold: int | None):
        names, weights, bias, temperature = self._model(exclude, self._fold(fold))
        if bias is None:
            return names, weights @ vector
        return names, softmax(((weights @ vector + bias) / temperature)[None, :])[0]

    def rank(self, query: str, exclude: str | None = None, fold: int | None = None) -> Ranking:
        vector = self._vectors.get(query)
        if vector is None:
            vector = self._encoder.encode([query])[0]
        names, values = self._scores(vector, exclude, fold)
        order = np.argsort(-values, kind="stable")
        return [(names[position], float(values[position])) for position in order]

    def route(self, query: str) -> Ranking:
        """The serving path: encode one query, score it, return the best label."""
        names, values = self._scores(self._encoder.encode([query])[0], None, None)
        best = int(values.argmax())
        return [(names[best], float(values[best]))]


def top_confidence(ranked: Ranking) -> float:
    return ranked[0][1] if ranked else 0.0


def evaluate(arm, scenarios: list[Scenario], packs: dict[str, str], near_ood: bool) -> dict:
    """Accuracy on the scenarios, and confidence on queries whose skill was removed."""
    total = len(scenarios)
    top1 = top3 = pack_hits = 0
    confidence_in: list[float] = []
    confidence_near: list[float] = []
    rows = []
    for scenario in scenarios:
        fold = fold_of(scenario.id, FOLDS)
        ranked = arm.rank(scenario.query, fold=fold)
        names = [name for name, _ in ranked]
        predicted = names[0] if names else None
        correct = predicted == scenario.expected_skill
        top1 += correct
        top3 += scenario.expected_skill in names[:3]
        pack_hits += predicted is not None and packs[predicted] == packs[scenario.expected_skill]
        confidence_in.append(top_confidence(ranked))
        if near_ood:
            # Near out-of-domain: the same query against a catalogue without its skill.
            # The right answer is then "none of these", so confidence should be low.
            held_out = arm.rank(scenario.query, exclude=scenario.expected_skill, fold=fold)
            confidence_near.append(top_confidence(held_out))
        rows.append(
            {
                "id": scenario.id,
                "fold": fold,
                "expected": scenario.expected_skill,
                "predicted": predicted,
                "confidence": top_confidence(ranked),
                "correct": bool(correct),
            }
        )
    low, high = wilson_interval(top1, total)
    result = {
        "queries": total,
        "top1_hits": int(top1),
        "top1": top1 / total,
        "top1_wilson95": [low, high],
        "top3": top3 / total,
        "pack": pack_hits / total,
        "rows": rows,
    }
    if near_ood:
        result["near_ood_auroc"] = auroc(confidence_in, confidence_near)
    if arm.calibrated:
        result["ece"] = expected_calibration_error(confidence_in, [row["correct"] for row in rows])
    return result


def abstention(result: dict, threshold: float) -> dict:
    """What a router that answers only above the threshold does with these queries."""
    rows = result["rows"]
    accepted = [row for row in rows if row["confidence"] > threshold]
    right = sum(row["correct"] for row in accepted)
    return {
        "coverage": len(accepted) / len(rows),
        "accepted_and_correct": right / len(rows),
        "accuracy_when_accepted": right / len(accepted) if accepted else None,
    }


def latency(arm, scenarios: list[Scenario]) -> dict:
    """Wall time of one routing call, in microseconds, over repeated passes."""
    for scenario in scenarios:
        arm.route(scenario.query)
    samples = []
    for _ in range(LATENCY_REPEATS):
        for scenario in scenarios:
            start = time.perf_counter_ns()
            arm.route(scenario.query)
            samples.append((time.perf_counter_ns() - start) / 1000)
    return {
        "calls": len(samples),
        "p50_us": percentile(samples, 50),
        "p95_us": percentile(samples, 95),
    }


def measure(arm, sets: dict[str, list[Scenario]], packs: dict[str, str], far_ood) -> dict:
    calibration, test = far_ood
    public = evaluate(arm, sets["public"], packs, near_ood=True)
    paraphrase = evaluate(arm, sets["paraphrase"], packs, near_ood=False)

    def refused(texts: list[str]) -> list[float]:
        return [top_confidence(arm.rank(text, fold=fold_of(text, FOLDS))) for text in texts]

    threshold = threshold_for_false_accept(refused(calibration), FALSE_ACCEPT_RATE)
    far = refused(test)
    public_confidence = [row["confidence"] for row in public["rows"]]
    paraphrase_confidence = [row["confidence"] for row in paraphrase["rows"]]
    return {
        "arm": arm.name,
        "family": arm.family,
        "artifact_bytes": arm.artifact_bytes,
        "head_bytes": getattr(arm, "head_bytes", 0),
        "temperatures": arm.temperatures() if hasattr(arm, "temperatures") else [],
        "strength": getattr(arm, "strength", None),
        "strength_selection": getattr(arm, "selection", {}),
        "public": public,
        "paraphrase": paraphrase,
        "far_ood": {
            "threshold": threshold,
            "false_accept_rate": sum(value > threshold for value in far) / len(far),
            "auroc_public": auroc(public_confidence, far),
            "auroc_paraphrase": auroc(paraphrase_confidence, far),
            "public": abstention(public, threshold),
            "paraphrase": abstention(paraphrase, threshold),
        },
        "latency": latency(arm, sets["public"]),
    }


def comparisons(results: list[dict]) -> list[dict]:
    """Sign tests between pairs of arms, on the queries where exactly one was right."""
    by_name = {result["arm"]: result for result in results}
    rows = []
    for first, second in PAIRS:
        if first not in by_name or second not in by_name:
            continue
        for key in ("public", "paraphrase"):
            only_first, only_second, p_value = paired_sign_test(
                [row["correct"] for row in by_name[first][key]["rows"]],
                [row["correct"] for row in by_name[second][key]["rows"]],
            )
            rows.append(
                {
                    "set": key,
                    "first": first,
                    "second": second,
                    "only_first": only_first,
                    "only_second": only_second,
                    "p_value": p_value,
                }
            )
    return rows


def overlap_summary(scenarios: list[Scenario], catalogue: list[Skill]) -> dict:
    """How much of each query's vocabulary already appears in its skill's own text."""
    reference = {skill.name: " ".join(label_texts(skill)) for skill in catalogue}
    shares = [overlap_share(item.query, reference[item.expected_skill]) for item in scenarios]
    return {
        "p25": percentile(shares, 25),
        "median": percentile(shares, 50),
        "p75": percentile(shares, 75),
        "max": max(shares),
        "at_least_half": sum(share >= 0.5 for share in shares),
    }


def machine() -> dict:
    cpu = platform.processor()
    if platform.system() == "Darwin":
        probe = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True
        )
        cpu = probe.stdout.strip() or cpu
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "cpu": cpu,
        "cores": os.cpu_count(),
        "memory_gb": round(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 2**30, 1),
        "python": platform.python_version(),
        "packages": {
            name: version(name) for name in ("numpy", "model2vec", "tokenizers", "onnxruntime")
        },
    }


def print_tables(report: dict) -> None:
    arms = report["arms"]
    for key, title in (("public", "Public scenarios"), ("paraphrase", "Paraphrase set")):
        print(f"\n{title}\n")
        print("| Arm | Top-1 | 95% interval | Top-3 | Pack |")
        print("|---|---|---|---|---|")
        for arm in arms:
            part = arm[key]
            low, high = part["top1_wilson95"]
            print(
                f"| {arm['arm']} | {part['top1']:.3f} ({part['top1_hits']}/{part['queries']}) "
                f"| {low:.3f} to {high:.3f} | {part['top3']:.3f} | {part['pack']:.3f} |"
            )
    print("\nAbstention\n")
    print(
        "| Arm | Near AUROC | Far AUROC pub | Far AUROC para | False accept "
        "| Pub answered | Pub right | Para answered | Para right | ECE pub | ECE para |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for arm in arms:
        far = arm["far_ood"]
        ece_public = arm["public"].get("ece")
        ece_paraphrase = arm["paraphrase"].get("ece")
        print(
            f"| {arm['arm']} | {arm['public']['near_ood_auroc']:.3f} "
            f"| {far['auroc_public']:.3f} | {far['auroc_paraphrase']:.3f} "
            f"| {far['false_accept_rate']:.3f} "
            f"| {far['public']['coverage']:.3f} | {far['public']['accepted_and_correct']:.3f} "
            f"| {far['paraphrase']['coverage']:.3f} "
            f"| {far['paraphrase']['accepted_and_correct']:.3f} "
            f"| {'-' if ece_public is None else format(ece_public, '.3f')} "
            f"| {'-' if ece_paraphrase is None else format(ece_paraphrase, '.3f')} |"
        )
    print("\nPaired comparisons on the paraphrase set\n")
    print("| First | Second | Only first right | Only second right | Sign test p |")
    print("|---|---|---|---|---|")
    for row in report["comparisons"]:
        if row["set"] == "paraphrase":
            print(
                f"| {row['first']} | {row['second']} | {row['only_first']} "
                f"| {row['only_second']} | {row['p_value']:.4f} |"
            )
    print("\nCost\n")
    print("| Arm | Artifact | Head | p50 | p95 |")
    print("|---|---|---|---|---|")
    for arm in arms:
        timing = arm["latency"]
        print(
            f"| {arm['arm']} | {arm['artifact_bytes'] / 1e6:.1f} MB "
            f"| {arm['head_bytes'] / 1e3:.1f} kB "
            f"| {timing['p50_us']:.0f} us | {timing['p95_us']:.0f} us |"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skills-repo", type=Path, required=True, help="a clone of Agent-Skills")
    parser.add_argument("--out", type=Path, default=CACHE / "results.json")
    parser.add_argument("--download", action="store_true", help="fetch missing models and data")
    parser.add_argument(
        "--encoders",
        nargs="*",
        default=[*STATIC_ENCODERS, *TRANSFORMER_ENCODERS],
        help="embedding encoders to measure; pass none for the keyword arms alone",
    )
    args = parser.parse_args()

    root = snapshot(args.skills_repo)
    if sha256_of(PARAPHRASE_SET) != PARAPHRASE_SHA256:
        raise SystemExit(f"{PARAPHRASE_SET.name} does not match its pinned hash")
    ensure_assets(args.download)

    catalogue = load_catalogue(root)
    packs = {skill.name: skill.pack for skill in catalogue}
    sets = {
        "public": load_scenarios(root / "tests" / "scenarios.json"),
        "paraphrase": load_scenarios(PARAPHRASE_SET),
    }
    far_ood = load_far_ood()

    results = []
    for arm in (IncumbentKeyword(root), Bm25Keyword(catalogue)):
        results.append(measure(arm, sets, packs, far_ood))
        print(f"measured {arm.name}", file=sys.stderr)

    texts = {text for skill in catalogue for text in label_texts(skill)}
    texts |= {item.query for scenarios in sets.values() for item in scenarios}
    texts |= set(far_ood[0]) | set(far_ood[1])
    ordered = sorted(texts)
    for key in args.encoders:
        encoder = StaticEncoder(key) if key in STATIC_ENCODERS else OnnxEncoder(key)
        started = time.perf_counter()
        vectors = dict(zip(ordered, encoder.encode(ordered), strict=True))
        elapsed = time.perf_counter() - started
        print(f"encoded {len(ordered)} texts with {key} in {elapsed:.1f} s", file=sys.stderr)
        for variant in VARIANTS:
            arm = EmbeddingArm(encoder, vectors, catalogue, sets["public"], variant)
            results.append(measure(arm, sets, packs, far_ood))
            print(f"measured {arm.name}", file=sys.stderr)
        del encoder, vectors

    report = {
        "skills_commit": SKILLS_COMMIT,
        "dataset_sha256": DATASET_SHA256,
        "paraphrase_sha256": PARAPHRASE_SHA256,
        "skills": len(catalogue),
        "label_texts": sum(len(label_texts(skill)) for skill in catalogue),
        "folds": FOLDS,
        "false_accept_target": FALSE_ACCEPT_RATE,
        "far_ood_queries": {"calibration": len(far_ood[0]), "test": len(far_ood[1])},
        "lexical_overlap": {
            name: overlap_summary(scenarios, catalogue) for name, scenarios in sets.items()
        },
        "machine": machine(),
        "comparisons": comparisons(results),
        "arms": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print_tables(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
