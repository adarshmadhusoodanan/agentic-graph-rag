"""CLI entrypoint for running ingestion against real files.

Usage:
    uv run python -m src.ingest path/to/document.txt
    uv run python -m src.ingest path/to/docs_dir/                # every .txt/.md file
    uv run python -m src.ingest path/to/document.txt --doc-id my-custom-id
"""

import argparse
import sys
from pathlib import Path

from src.ingestion.etl import ingest_document
from src.utils.logger import get_logger

logger = get_logger(__name__)

_SUPPORTED_SUFFIXES = {".txt", ".md"}


def _resolve_files(path: Path) -> list[Path]:
    """Return the files to ingest for a given file or directory path."""
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(
            p
            for p in path.rglob("*")
            if p.is_file() and p.suffix.lower() in _SUPPORTED_SUFFIXES
        )
    raise FileNotFoundError(f"No such file or directory: {path}")


def _doc_id_for(path: Path) -> str:
    """Derive a stable doc_id from a file path.

    Using the filename stem (not a random id) means re-running ingestion on
    the same file updates the same document instead of creating a duplicate,
    consistent with how ingest_document() is idempotent internally.
    """
    return path.stem


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ingest documents into Qdrant (vectors) + Neo4j (graph)."
    )
    parser.add_argument(
        "path", type=Path, help="Path to a file or a directory of files to ingest"
    )
    parser.add_argument(
        "--doc-id",
        help="Override the derived doc_id (only valid for a single file)",
    )
    args = parser.parse_args(argv)

    try:
        files = _resolve_files(args.path)
    except FileNotFoundError as e:
        logger.error(str(e))
        return 1

    if not files:
        logger.warning(
            "No supported files (%s) found under %s",
            ", ".join(_SUPPORTED_SUFFIXES),
            args.path,
        )
        return 1

    if args.doc_id and len(files) > 1:
        logger.error("--doc-id can only be used when ingesting a single file")
        return 1

    logger.info("Found %d file(s) to ingest", len(files))
    for file_path in files:
        doc_id = args.doc_id or _doc_id_for(file_path)
        text = file_path.read_text(encoding="utf-8")
        logger.info("Ingesting '%s' as doc_id='%s'", file_path, doc_id)
        try:
            ingest_document(doc_id=doc_id, text=text)
        except Exception:
            logger.exception("Failed to ingest %s", file_path)
            return 1

    logger.info("Ingestion complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())