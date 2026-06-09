from __future__ import annotations

import re
from pathlib import Path

from langchain_core.tools import BaseTool
from langchain_core.tools import tool

from devmate.config import AppConfig

SLUG_PATTERN = re.compile(r"[^a-zA-Z0-9_-]+")


def create_skill_tools(config: AppConfig) -> list[BaseTool]:
    skills_dir = Path(config.skills.skills_dir)

    @tool("save_skill")
    def save_skill(name: str, description: str, content: str) -> str:
        """Save a reusable task skill as a markdown file."""
        skills_dir.mkdir(parents=True, exist_ok=True)
        path = skills_dir / f"{_slugify(name)}.md"

        skill_text = (
            f"# {name}\n\n"
            f"## Description\n{description.strip()}\n\n"
            f"## Procedure\n{content.strip()}\n"
        )

        path.write_text(skill_text, encoding="utf-8")

        return f"Saved skill: {path}"

    @tool("list_skills")
    def list_skills() -> str:
        """List available saved skills."""
        if not skills_dir.exists():
            return "No skills found."

        paths = sorted(skills_dir.glob("*.md"))

        if not paths:
            return "No skills found."

        return "\n".join(path.stem for path in paths)

    @tool("read_skill")
    def read_skill(name: str) -> str:
        """Read a saved skill by name."""
        path = skills_dir / f"{_slugify(name)}.md"

        if not path.exists():
            return f"Skill not found: {name}"

        return path.read_text(encoding="utf-8")

    @tool("search_skills")
    def search_skills(query: str) -> str:
        """Search saved skills for reusable task patterns."""
        if not skills_dir.exists():
            return "No skills found."

        query_terms = {
            term.lower()
            for term in re.findall(r"\w+", query)
            if len(term) >= 3
        }

        matches: list[str] = []

        for path in sorted(skills_dir.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            content_lower = content.lower()
            score = sum(
                1 for term in query_terms if term in content_lower
            )

            if score > 0:
                matches.append(
                    f"Skill: {path.stem}\n{content[:1000]}",
                )

        if not matches:
            return "No relevant skills found."

        return "\n\n---\n\n".join(matches)

    return [
        save_skill,
        list_skills,
        read_skill,
        search_skills,
    ]


def _slugify(name: str) -> str:
    slug = SLUG_PATTERN.sub("-", name.strip()).strip("-").lower()

    if not slug:
        return "untitled-skill"

    return slug
