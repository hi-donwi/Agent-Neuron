"""Read a skill catalogue in the DONWI Skills layout: skills/<name>/SKILL.md.

Each SKILL.md opens with front matter in a restricted, plain-text form: a single-line
`name`, a single-line or folded `description`, and `pack` and `keywords` under
`metadata`. This is a reader for that form, not a YAML parser.
"""

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

_FOLD_MARKERS = {">", ">-", "|", "|-", ""}
_WHEN_HEADING = re.compile(r"^#{2,3}\s+when to use\b", re.IGNORECASE)


@dataclass(frozen=True)
class Skill:
    name: str
    pack: str
    description: str
    keywords: tuple[str, ...]
    when_to_use: tuple[str, ...]


@dataclass(frozen=True)
class Scenario:
    id: str
    query: str
    expected_skill: str
    pack: str


def parse_skill(text: str, fallback_name: str) -> Skill:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{fallback_name}: SKILL.md does not open with front matter")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise ValueError(f"{fallback_name}: front matter is not closed") from None

    name, pack, description, keywords = fallback_name, "core", "", ()
    front = lines[1:end]
    index = 0
    while index < len(front):
        line = front[index]
        key, _, value = line.strip().partition(":")
        value = value.strip()
        indented = line[:1] in (" ", "\t")
        if key == "name" and not indented:
            name = value
        elif key == "description" and not indented:
            if value in _FOLD_MARKERS:
                parts = []
                index += 1
                while index < len(front) and (front[index][:1] in (" ", "\t") or not front[index]):
                    if front[index].strip():
                        parts.append(front[index].strip())
                    index += 1
                description = " ".join(parts)
                continue
            description = value
        elif key == "pack" and indented:
            pack = value
        elif key == "keywords":
            items = value.strip("[]").split(",")
            keywords = tuple(item.strip().strip("\"'") for item in items if item.strip())
        index += 1

    return Skill(name, pack, description, keywords, _when_to_use(lines[end + 1 :]))


def _when_to_use(body: list[str]) -> tuple[str, ...]:
    bullets: list[str] = []
    inside = False
    for line in body:
        if line.startswith("#"):
            if inside:
                break
            inside = bool(_WHEN_HEADING.match(line))
            continue
        if not inside:
            continue
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            bullets.append(stripped[2:].strip())
        elif stripped and bullets and line[:1] in (" ", "\t"):
            bullets[-1] += " " + stripped
    return tuple(bullets)


def label_texts(skill: Skill) -> list[str]:
    """The short texts that describe a skill: name, description, keywords, bullets."""
    texts = [skill.name.replace("-", " "), skill.description, *skill.keywords, *skill.when_to_use]
    return [text for text in texts if text]


def load_catalogue(root: Path) -> list[Skill]:
    skills = []
    for directory in sorted((root / "skills").iterdir()):
        skill_file = directory / "SKILL.md"
        if skill_file.is_file():
            skills.append(parse_skill(skill_file.read_text(encoding="utf-8"), directory.name))
    return sorted(skills, key=lambda skill: skill.name)


def load_scenarios(path: Path) -> list[Scenario]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        Scenario(item["id"], item["query"], item["expected_skill"], item["pack"])
        for item in data["scenarios"]
    ]


def content_hash(root: Path, files: Iterable[Path]) -> str:
    """SHA-256 over each file's path relative to root and its own SHA-256, sorted."""
    entries = sorted(
        (path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
        for path in files
    )
    digest = hashlib.sha256()
    for relative, file_hash in entries:
        digest.update(f"{relative}\t{file_hash}\n".encode())
    return digest.hexdigest()


def fold_of(identifier: str, folds: int) -> int:
    """A fold that depends only on the identifier, so a split never moves."""
    return int(hashlib.sha256(identifier.encode()).hexdigest()[:8], 16) % folds
