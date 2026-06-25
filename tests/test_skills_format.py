from __future__ import annotations

import re
from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).resolve().parent.parent / ".skills"
NAME_RE = re.compile(r"^[a-z0-9-]+$")
MAX_DESCRIPTION = 1024

skill_files = sorted(SKILLS_DIR.glob("*/SKILL.md"))


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        raise AssertionError("SKILL.md must start with a YAML frontmatter block.")

    parts = text.split("---", 2)
    # parts[0] == "" before first ---, parts[1] == frontmatter, parts[2] == body
    assert len(parts) >= 3, "SKILL.md frontmatter block is not closed with '---'."

    frontmatter_block = parts[1]
    body = parts[2]

    meta: dict[str, str] = {}
    for line in frontmatter_block.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()

    return meta, body


def test_skills_directory_has_skills() -> None:
    assert skill_files, "No SKILL.md files found under .skills/"


@pytest.mark.parametrize("skill_path", skill_files, ids=lambda p: p.parent.name)
def test_skill_frontmatter_is_valid(skill_path: Path) -> None:
    text = skill_path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)

    parent_name = skill_path.parent.name

    assert "name" in meta, f"{parent_name}: missing 'name' in frontmatter"
    assert "description" in meta, f"{parent_name}: missing 'description'"

    name = meta["name"]
    assert NAME_RE.match(name), f"{parent_name}: name '{name}' is not lowercase/digits/hyphen"
    assert name == parent_name, (
        f"name '{name}' must match parent directory '{parent_name}'"
    )

    description = meta["description"]
    assert description, f"{parent_name}: description must be non-empty"
    assert len(description) <= MAX_DESCRIPTION, (
        f"{parent_name}: description exceeds {MAX_DESCRIPTION} chars"
    )

    assert body.strip(), f"{parent_name}: SKILL.md body must be non-empty"


@pytest.mark.parametrize("skill_path", skill_files, ids=lambda p: p.parent.name)
def test_skill_does_not_require_old_python(skill_path: Path) -> None:
    text = skill_path.read_text(encoding="utf-8")
    assert 'requires-python = ">=3.11"' not in text, (
        f"{skill_path.parent.name}: must target Python >=3.13, not >=3.11"
    )
    assert 'requires-python = ">=3.12"' not in text, (
        f"{skill_path.parent.name}: must target Python >=3.13, not >=3.12"
    )
