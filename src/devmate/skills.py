from __future__ import annotations

import re
from pathlib import Path

from langchain_core.tools import BaseTool
from langchain_core.tools import tool

from devmate.config import AppConfig

SLUG_PATTERN = re.compile(r"[^a-z0-9-]+")


def create_skill_tools(config: AppConfig) -> list[BaseTool]:
    """Create tools for saving, listing, reading, and searching standard Skills."""

    skills_dir = Path(config.skills.skills_dir)

    @tool("save_skill")
    def save_skill(name: str, description: str, content: str) -> str:
        """Save a reusable task pattern as a standard Agent Skill."""
        slug = _slugify(name)
        skill_dir = skills_dir / slug
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_path = skill_dir / "SKILL.md"
        skill_text = _format_skill_markdown(
            name=slug,
            description=description,
            content=content,
        )
        skill_path.write_text(skill_text, encoding="utf-8")
        return f"Saved standard skill: {skill_path}"

    @tool("list_skills")
    def list_skills() -> str:
        """List available standard Agent Skills."""
        paths = _skill_paths(skills_dir)
        if not paths:
            return "No skills found."
        return "\n".join(path.parent.name for path in paths)

    @tool("read_skill")
    def read_skill(name: str) -> str:
        """Read a standard Agent Skill by name."""
        skill_path = skills_dir / _slugify(name) / "SKILL.md"
        if not skill_path.exists():
            return f"Skill not found: {name}"
        return skill_path.read_text(encoding="utf-8")

    @tool("search_skills")
    def search_skills(query: str) -> str:
        """Search standard Agent Skills for reusable task patterns."""
        query_terms = {
            term.lower()
            for term in re.findall(r"\w+", query)
            if len(term) >= 3
        }

        matches: list[str] = []
        for path in _skill_paths(skills_dir):
            content = path.read_text(encoding="utf-8")
            content_lower = content.lower()
            score = sum(
                1
                for term in query_terms
                if term in content_lower
            )
            if score > 0:
                matches.append(
                    f"Skill: {path.parent.name}\n{content[:1200]}",
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


def _skill_paths(skills_dir: Path) -> list[Path]:
    if not skills_dir.exists():
        return []
    return sorted(skills_dir.glob("*/SKILL.md"))


def _format_skill_markdown(
    name: str,
    description: str,
    content: str,
) -> str:
    clean_description = _single_line(description)[:1024]
    clean_content = content.strip()
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {clean_description}\n"
        "---\n\n"
        f"# {name}\n\n"
        "## Instructions\n\n"
        f"{clean_content}\n"
    )


def _single_line(value: str) -> str:
    return " ".join(value.strip().split())


def _slugify(name: str) -> str:
    slug = SLUG_PATTERN.sub("-", name.strip().lower()).strip("-")
    if not slug:
        return "untitled-skill"
    return slug[:64]