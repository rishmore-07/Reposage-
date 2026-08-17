"""
app/modules/retrieval/keyword_index.py

BM25 keyword index persistence and lifecycle management.

Manages the lifecycle of per-repository BM25 indices:
- Build: Creates a BM25 index from CodeChunk records
- Persist: Saves to disk as pickle with metadata for validation
- Load: Loads from disk with staleness checking
- Invalidate: Removes stale indices

SECURITY NOTE:
    BM25 indices are stored as pickle files under the RepoSage-managed
    data/keyword_indices/ directory ONLY. This module NEVER accepts
    user-supplied file paths for unpickling. The directory is computed
    from settings.keyword_index_dir and the repository UUID.
"""

from __future__ import annotations

import os
import pickle
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Plus

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Regex for validating UUID strings (prevents path traversal)
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Current index format version — increment when format changes
INDEX_VERSION = 2


@dataclass
class IndexMetadata:
    """Metadata stored alongside the BM25 index for validation."""

    repository_id: str
    index_version: int
    chunk_count: int
    chunk_ids: list[str]
    created_at: str
    updated_at: str


@dataclass
class PersistedIndex:
    """Complete BM25 index with metadata, ready for serialization."""

    metadata: IndexMetadata
    bm25: BM25Okapi
    # Parallel array: chunk_ids[i] maps to bm25 document i
    chunk_ids: list[str]
    # Parallel array: full chunk data for result construction
    chunk_data: list[dict[str, Any]]


def _get_index_dir() -> Path:
    """Return the keyword index storage directory, creating it if needed."""
    index_dir = Path(settings.keyword_index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    return index_dir


def _get_index_path(repository_id: uuid.UUID) -> Path:
    """
    Return the pickle file path for a repository's BM25 index.

    Security: validates repository_id is a proper UUID to prevent path traversal.
    """
    repo_id_str = str(repository_id)
    if not _UUID_PATTERN.match(repo_id_str):
        raise ValueError(f"Invalid repository ID format: {repo_id_str}")

    return _get_index_dir() / f"{repo_id_str}.pkl"


def _tokenize(text: str) -> list[str]:
    """
    Simple whitespace + punctuation tokenizer for BM25.

    Splits on non-alphanumeric characters and lowercases tokens.
    Keeps underscores (common in code identifiers like JWT_SECRET).
    """
    # Split on anything that isn't a word character (alphanumeric + underscore)
    tokens = re.split(r"[^\w]+", text.lower())
    # Filter empty strings
    return [t for t in tokens if t]


def build_searchable_text(chunk_data: dict[str, Any]) -> str:
    """
    Build the searchable text representation for a CodeChunk.

    Combines file path, language, chunk type, symbol name, and content
    into a single string optimized for BM25 retrieval.
    """
    parts = []

    file_path = chunk_data.get("file_path", "")
    if file_path:
        parts.append(f"File: {file_path}")

    language = chunk_data.get("language", "")
    if language:
        parts.append(f"Language: {language}")

    chunk_type = chunk_data.get("chunk_type", "")
    if chunk_type:
        parts.append(f"Type: {chunk_type}")

    module_name = chunk_data.get("module_name")
    if module_name:
        parts.append(f"Module: {module_name}")

    class_name = chunk_data.get("class_name")
    if class_name:
        parts.append(f"Class: {class_name}")

    parent_symbol = chunk_data.get("parent_symbol")
    if parent_symbol:
        parts.append(f"Parent: {parent_symbol}")
    else:
        parts.append("Parent: null")

    symbol_name = chunk_data.get("symbol_name")
    if symbol_name:
        parts.append(f"Symbol: {symbol_name}")

    context_path = chunk_data.get("context_path")
    if context_path:
        parts.append(f"Context: {context_path}")

    content = chunk_data.get("content", "")
    if content:
        parts.append(content)

    return "\n".join(parts)


def build_index(
    repository_id: uuid.UUID,
    chunks: list[dict[str, Any]],
) -> PersistedIndex:
    """
    Build a BM25 index from a list of chunk data dictionaries.

    Each chunk dict should contain at minimum:
        chunk_id, repository_id, file_path, language, chunk_type,
        symbol_name, content

    Args:
        repository_id: UUID of the repository being indexed.
        chunks: List of chunk data dicts.

    Returns:
        PersistedIndex ready for searching or saving to disk.
    """
    if not chunks:
        logger.warning(
            "build_index_empty",
            repository_id=str(repository_id),
        )

    chunk_ids = []
    chunk_data_list = []
    tokenized_corpus = []

    for chunk in chunks:
        chunk_id = chunk.get("chunk_id", "")
        chunk_ids.append(chunk_id)
        chunk_data_list.append(chunk)

        searchable_text = build_searchable_text(chunk)
        tokens = _tokenize(searchable_text)
        tokenized_corpus.append(tokens)

    # Build BM25 index
    bm25 = BM25Plus(tokenized_corpus) if tokenized_corpus else BM25Plus([[""]])

    now = datetime.now(UTC).isoformat()
    metadata = IndexMetadata(
        repository_id=str(repository_id),
        index_version=INDEX_VERSION,
        chunk_count=len(chunks),
        chunk_ids=chunk_ids,
        created_at=now,
        updated_at=now,
    )

    return PersistedIndex(
        metadata=metadata,
        bm25=bm25,
        chunk_ids=chunk_ids,
        chunk_data=chunk_data_list,
    )


def save_index(repository_id: uuid.UUID, index: PersistedIndex) -> Path:
    """
    Persist a BM25 index to disk.

    Args:
        repository_id: UUID of the repository.
        index: The PersistedIndex to save.

    Returns:
        Path to the saved pickle file.
    """
    path = _get_index_path(repository_id)

    with open(path, "wb") as f:
        pickle.dump(index, f, protocol=pickle.HIGHEST_PROTOCOL)

    logger.info(
        "keyword_index_saved",
        repository_id=str(repository_id),
        chunk_count=index.metadata.chunk_count,
        path=str(path),
    )

    return path


def load_index(repository_id: uuid.UUID) -> PersistedIndex | None:
    """
    Load a BM25 index from disk.

    Security: Only loads from the RepoSage-managed keyword_index_dir.
    Validates repository_id format and index metadata.

    Args:
        repository_id: UUID of the repository.

    Returns:
        PersistedIndex if found and valid, None otherwise.
    """
    path = _get_index_path(repository_id)

    if not path.exists():
        logger.debug(
            "keyword_index_not_found",
            repository_id=str(repository_id),
        )
        return None

    # Security: verify the file is within the expected directory
    expected_dir = _get_index_dir().resolve()
    actual_parent = path.resolve().parent
    if actual_parent != expected_dir:
        logger.error(
            "keyword_index_path_violation",
            repository_id=str(repository_id),
            expected_dir=str(expected_dir),
            actual_parent=str(actual_parent),
        )
        return None

    try:
        with open(path, "rb") as f:
            index: PersistedIndex = pickle.load(f)  # noqa: S301

        # Validate metadata
        if not isinstance(index, PersistedIndex):
            logger.warning(
                "keyword_index_invalid_type",
                repository_id=str(repository_id),
            )
            return None

        if index.metadata.repository_id != str(repository_id):
            logger.warning(
                "keyword_index_repository_mismatch",
                expected=str(repository_id),
                found=index.metadata.repository_id,
            )
            return None

        if index.metadata.index_version != INDEX_VERSION:
            logger.info(
                "keyword_index_version_outdated",
                repository_id=str(repository_id),
                stored_version=index.metadata.index_version,
                current_version=INDEX_VERSION,
            )
            return None

        logger.debug(
            "keyword_index_loaded",
            repository_id=str(repository_id),
            chunk_count=index.metadata.chunk_count,
        )
        return index

    except Exception as e:
        logger.error(
            "keyword_index_load_failed",
            repository_id=str(repository_id),
            error=str(e),
        )
        return None


def validate_index(
    index: PersistedIndex,
    current_chunk_ids: list[str],
) -> bool:
    """
    Check whether a loaded index matches the current repository chunk state.

    Args:
        index: The loaded PersistedIndex.
        current_chunk_ids: Current CodeChunk IDs from the database.

    Returns:
        True if the index matches, False if it is stale.
    """
    stored_ids = set(index.metadata.chunk_ids)
    current_ids = set(current_chunk_ids)

    if stored_ids != current_ids:
        logger.info(
            "keyword_index_stale",
            repository_id=index.metadata.repository_id,
            stored_count=len(stored_ids),
            current_count=len(current_ids),
            added=len(current_ids - stored_ids),
            removed=len(stored_ids - current_ids),
        )
        return False

    return True


def delete_index(repository_id: uuid.UUID) -> bool:
    """
    Remove a persisted BM25 index from disk.

    Args:
        repository_id: UUID of the repository.

    Returns:
        True if the file was deleted, False if it didn't exist.
    """
    path = _get_index_path(repository_id)

    if path.exists():
        path.unlink()
        logger.info(
            "keyword_index_deleted",
            repository_id=str(repository_id),
        )
        return True

    return False
