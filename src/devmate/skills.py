from __future__ import annotations

import re
from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.tools import BaseTool
from langchain_core.tools import tool

from devmate.config import AppConfig
from devmate.model import create_embedding_model

SLUG_PATTERN = re.compile(r"[^a-z0-9-]+")
SKILLS_COLLECTION = "devmate_skills"


def create_skill_tools(config: AppConfig) -> list[BaseTool]:
    """Create tools for saving, listing, reading, and searching standard Skills."""

    skills_dir = Path(config.skills.skills_dir)
    embedding_model = create_embedding_model(config)
    store = _load_skills_store(embedding_model, skills_dir)

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
        _upsert_skill(store, embedding_model, slug, skill_text, skill_path)
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
        docs = store.similarity_search(query, k=4)
        if not docs:
            return "No relevant skills found."
        return _format_skill_results(docs)

    return [
        save_skill,
        list_skills,
        read_skill,
        search_skills,
    ]


def _load_skills_store(embedding_model: object, skills_dir: Path) -> Chroma:
    persist_dir = skills_dir / ".chroma"
    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))
    store = Chroma(
        collection_name=SKILLS_COLLECTION,
        embedding_function=embedding_model,
        client=client,
    )
    _sync_missing_skills(store, embedding_model, skills_dir)
    return store


def _sync_missing_skills(
    store: Chroma,
    embedding_model: object,
    skills_dir: Path,
) -> None:
    paths = _skill_paths(skills_dir)
    if not paths:
        return
    existing = set(store.get(include=[])["ids"])
    for path in paths:
        slug = path.parent.name
        if slug not in existing:
            content = path.read_text(encoding="utf-8")
            _upsert_skill(store, embedding_model, slug, content, path)


def _upsert_skill(
    store: Chroma,
    embedding_model: object,
    slug: str,
    text: str,
    path: Path,
) -> None:
    vector = embedding_model.embed_query(text)
    store._collection.upsert(
        ids=[slug],
        documents=[text],
        embeddings=[vector],
        metadatas=[{"slug": slug, "source": str(path)}],
    )


def _format_skill_results(docs: list[Document]) -> str:
    parts: list[str] = []
    for doc in docs:
        slug = doc.metadata.get("slug", "unknown")
        parts.append(f"Skill: {slug}\n{doc.page_content[:1200]}")
    return "\n\n---\n\n".join(parts)


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