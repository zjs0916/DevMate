from __future__ import annotations

import argparse
import logging
from pathlib import Path

from devmate.config import load_config
from devmate.rag import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    build_knowledge_base,
    load_local_documents,
)

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Index local documents for DevMate RAG.",
    )
    parser.add_argument(
        "--config",
        default="config.toml",
        help="Path to config TOML file.",
    )
    parser.add_argument(
        "--docs-dir",
        default="docs",
        help="Directory containing markdown or text documents.",
    )
    parser.add_argument(
        "--persist-dir",
        default=".chroma",
        help="Directory for the local Chroma vector database.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the existing Chroma persist directory before indexing.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Maximum characters per chunk.",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=DEFAULT_CHUNK_OVERLAP,
        help="Character overlap used for oversized chunk splitting.",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Optional corpus manifest JSONL/JSON path used for metadata and signature.",
    )

    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    args = parse_args()
    docs_dir = Path(args.docs_dir)
    persist_dir = Path(args.persist_dir)

    documents = load_local_documents(
        docs_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        manifest_path=args.manifest,
    )

    if not documents:
        LOGGER.error("No documents found in %s.", docs_dir)
        raise SystemExit(1)

    config = load_config(args.config)
    build_knowledge_base(
        config=config,
        docs_dir=docs_dir,
        persist_dir=persist_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        manifest_path=args.manifest,
        reset=args.reset,
    )

    LOGGER.info(
        "Indexed %s document chunks from %s into %s.",
        len(documents),
        docs_dir,
        persist_dir,
    )


if __name__ == "__main__":
    main()
