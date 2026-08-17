"""
app/modules/retrieval/keyword_search.py

BM25 keyword retriever for code chunks.

Uses the rank_bm25 library (Okapi BM25) for lexical/keyword retrieval.
Supports exact identifiers, function names, class names, filenames,
variable names, technical terms, and natural language queries.

The BM25 index is loaded from disk (built during ingestion) and
validated against the current repository state before use.
If the index is stale or missing, it is rebuilt from the database.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.modules.repositories.models import CodeChunk, IndexedFile
from app.modules.retrieval.keyword_index import (
    PersistedIndex,
    _tokenize,
    build_index,
    build_searchable_text,
    delete_index,
    load_index,
    save_index,
    validate_index,
)

logger = get_logger(__name__)


class KeywordSearchService:
    """
    BM25-based keyword search over CodeChunks.

    Repository isolation: only searches chunks belonging to the
    specified repository_id.
    """

    def __init__(self, db: AsyncSession | None = None):
        """
        Args:
            db: Optional async database session. Required for index
                rebuilding from DB when the persisted index is missing
                or stale. Not needed when index is available on disk.
        """
        self.db = db

    async def search(
        self,
        repository_id: uuid.UUID,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search for code chunks matching the query using BM25.

        Args:
            repository_id: UUID of the repository to search within.
            query: Search query string.
            top_k: Number of top results to return.

        Returns:
            List of result dicts with chunk metadata and BM25 score,
            sorted by descending score.

        Raises:
            RuntimeError: If the index cannot be loaded or rebuilt.
        """
        if not query or not query.strip():
            return []

        index = await self._get_or_rebuild_index(repository_id)
        if index is None:
            logger.warning(
                "keyword_search_no_index",
                repository_id=str(repository_id),
            )
            raise RuntimeError(
                f"No keyword index available for repository {repository_id}. "
                "Repository may not be ingested yet."
            )

        # Tokenize query using the same tokenizer as indexing
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        # Get BM25 scores for all documents
        scores = index.bm25.get_scores(query_tokens)

        # Create (index, score) pairs and sort by score descending
        scored_indices = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True,
        )

        # Take top_k results with score > 0
        results = []
        for idx, score in scored_indices[:top_k]:
            if score <= 0:
                break

            chunk_data = index.chunk_data[idx]
            result = {
                "chunk_id": chunk_data.get("chunk_id", ""),
                "repository_id": chunk_data.get("repository_id", ""),
                "indexed_file_id": chunk_data.get("indexed_file_id", ""),
                "code_symbol_id": chunk_data.get("code_symbol_id"),
                "file_path": chunk_data.get("file_path", ""),
                "language": chunk_data.get("language", ""),
                "chunk_type": chunk_data.get("chunk_type", ""),
                "symbol_name": chunk_data.get("symbol_name"),
                "start_line": chunk_data.get("start_line", 0),
                "end_line": chunk_data.get("end_line", 0),
                "content": chunk_data.get("content", ""),
                "score": float(score),
            }
            results.append(result)

        logger.debug(
            "keyword_search_completed",
            repository_id=str(repository_id),
            query_length=len(query),
            results_count=len(results),
        )

        return results

    async def _get_or_rebuild_index(
        self, repository_id: uuid.UUID
    ) -> PersistedIndex | None:
        """
        Load the BM25 index from disk, validating it against the DB.
        If stale or missing, rebuild from the database.
        """
        # Try loading from disk
        index = load_index(repository_id)

        if index is not None:
            # Validate against current DB state if we have a session
            if self.db is not None:
                current_chunk_ids = await self._get_chunk_ids(repository_id)
                if validate_index(index, current_chunk_ids):
                    return index
                else:
                    logger.info(
                        "keyword_index_rebuilding_stale",
                        repository_id=str(repository_id),
                    )
                    delete_index(repository_id)
            else:
                # No DB session, trust the persisted index
                return index

        # Rebuild from database
        if self.db is not None:
            return await self._rebuild_index(repository_id)

        return None

    async def _rebuild_index(
        self, repository_id: uuid.UUID
    ) -> PersistedIndex | None:
        """Rebuild the BM25 index from CodeChunk records in the database."""
        chunks_data = await self._load_chunks_from_db(repository_id)

        if not chunks_data:
            logger.info(
                "keyword_index_rebuild_no_chunks",
                repository_id=str(repository_id),
            )
            return None

        index = build_index(repository_id, chunks_data)
        save_index(repository_id, index)

        logger.info(
            "keyword_index_rebuilt",
            repository_id=str(repository_id),
            chunk_count=len(chunks_data),
        )

        return index

    async def _load_chunks_from_db(
        self, repository_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Load all CodeChunk records for a repository from the database."""
        if self.db is None:
            return []

        # Join CodeChunk with IndexedFile to get file_path
        stmt = (
            select(CodeChunk, IndexedFile.relative_path)
            .join(IndexedFile, CodeChunk.indexed_file_id == IndexedFile.id)
            .where(IndexedFile.repository_id == repository_id)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        chunks_data = []
        for chunk, file_path in rows:
            chunks_data.append({
                "chunk_id": str(chunk.id),
                "repository_id": str(repository_id),
                "indexed_file_id": str(chunk.indexed_file_id),
                "code_symbol_id": str(chunk.code_symbol_id) if chunk.code_symbol_id else None,
                "file_path": file_path,
                "language": chunk.language,
                "chunk_type": chunk.chunk_type,
                "symbol_name": chunk.symbol_name,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "content": chunk.content,
            })

        return chunks_data

    async def _get_chunk_ids(self, repository_id: uuid.UUID) -> list[str]:
        """Get all CodeChunk IDs for a repository from the database."""
        if self.db is None:
            return []

        stmt = (
            select(CodeChunk.id)
            .join(IndexedFile, CodeChunk.indexed_file_id == IndexedFile.id)
            .where(IndexedFile.repository_id == repository_id)
        )

        result = await self.db.execute(stmt)
        return [str(row[0]) for row in result.all()]
