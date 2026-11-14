import json

import pytest

from neuron_lab.skillset import (
    content_hash,
    fold_of,
    label_texts,
    load_catalogue,
    load_scenarios,
    parse_skill,
)

FOLDED = """---
name: ci-cd
description: >-
  Set up or improve CI/CD pipelines: automated gates and safe deployments.
  Use when adding GitHub Actions.
metadata:
  pack: core
  keywords: ci, cd, github actions, quality gate
---

# CI/CD & Automation

## Overview

Automate the checks.

## When to use
- Creating or maintaining a CI pipeline.
- Adding quality gates; debugging a red build.

## Process
1. Shift left.
"""

SINGLE_LINE = """---
name: api-design
description: Design stable HTTP APIs.
metadata:
  pack: java
---

# API design
"""


def write_skill(root, name, text):
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(text)


def test_parse_reads_a_folded_description_and_the_metadata():
    skill = parse_skill(FOLDED, fallback_name="unused")

    assert skill.name == "ci-cd"
    assert skill.pack == "core"
    assert skill.description == (
        "Set up or improve CI/CD pipelines: automated gates and safe deployments. "
        "Use when adding GitHub Actions."
    )
    assert skill.keywords == ("ci", "cd", "github actions", "quality gate")


def test_parse_collects_the_when_to_use_bullets_and_stops_at_the_next_heading():
    skill = parse_skill(FOLDED, fallback_name="unused")

    assert skill.when_to_use == (
        "Creating or maintaining a CI pipeline.",
        "Adding quality gates; debugging a red build.",
    )


def test_parse_handles_a_single_line_description_and_missing_optional_fields():
    skill = parse_skill(SINGLE_LINE, fallback_name="unused")

    assert skill.name == "api-design"
    assert skill.pack == "java"
    assert skill.description == "Design stable HTTP APIs."
    assert skill.keywords == ()
    assert skill.when_to_use == ()


def test_parse_refuses_a_file_without_front_matter():
    with pytest.raises(ValueError):
        parse_skill("# No front matter here\n", fallback_name="broken")


def test_label_texts_are_the_name_the_description_keywords_and_bullets():
    skill = parse_skill(FOLDED, fallback_name="unused")

    assert label_texts(skill) == [
        "ci cd",
        "Set up or improve CI/CD pipelines: automated gates and safe deployments. "
        "Use when adding GitHub Actions.",
        "ci",
        "cd",
        "github actions",
        "quality gate",
        "Creating or maintaining a CI pipeline.",
        "Adding quality gates; debugging a red build.",
    ]


def test_load_catalogue_returns_skills_sorted_by_name(tmp_path):
    write_skill(tmp_path, "ci-cd", FOLDED)
    write_skill(tmp_path, "api-design", SINGLE_LINE)

    catalogue = load_catalogue(tmp_path)

    assert [skill.name for skill in catalogue] == ["api-design", "ci-cd"]


def test_load_scenarios_reads_the_four_fields(tmp_path):
    path = tmp_path / "scenarios.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "scenarios": [
                    {
                        "id": "s-1",
                        "query": "add a workflow",
                        "expected_skill": "ci-cd",
                        "pack": "core",
                    }
                ],
            }
        )
    )

    scenarios = load_scenarios(path)

    assert len(scenarios) == 1
    assert scenarios[0].id == "s-1"
    assert scenarios[0].query == "add a workflow"
    assert scenarios[0].expected_skill == "ci-cd"
    assert scenarios[0].pack == "core"


def test_content_hash_changes_when_a_file_changes_and_ignores_file_order(tmp_path):
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("one")
    second.write_text("two")

    before = content_hash(tmp_path, [first, second])

    assert content_hash(tmp_path, [second, first]) == before
    second.write_text("changed")
    assert content_hash(tmp_path, [first, second]) != before


def test_fold_is_a_stable_function_of_the_identifier():
    assert fold_of("scenario-api-design-1", 5) == fold_of("scenario-api-design-1", 5)
    assert all(0 <= fold_of(f"s-{i}", 5) < 5 for i in range(50))
    assert len({fold_of(f"s-{i}", 5) for i in range(50)}) == 5
