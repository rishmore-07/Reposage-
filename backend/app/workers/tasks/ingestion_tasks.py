"""
app/workers/tasks/ingestion_tasks.py

Celery tasks for repository ingestion (Phase 3).
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

from celery.utils.log import get_task_logger
from sqlalchemy import create_engine, delete, update, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import IngestionStatus
from app.core.encryption import decrypt_string
from app.modules.repositories.models import (
    RepositoryIngestion,
    Repository,
    UserConnectedRepository,
    IndexedFile,
    CodeSymbol,
)
from app.modules.users.models import User
from app.modules.repositories.git_service import GitRepositoryService
from app.modules.repositories.file_discovery import FileDiscoveryService
import asyncio
from app.modules.indexing.language_detector import LanguageDetector
from app.modules.indexing.parser_service import TreeSitterParser
from app.modules.indexing.symbol_extractor import SymbolExtractorFactory
from app.modules.indexing.chunking.chunker import SemanticChunker
from app.modules.embeddings.factory import EmbeddingFactory
from app.modules.vectorstore.qdrant_service import QdrantService
from app.modules.vectorstore.schemas import VectorPayload
from app.modules.repositories.models import CodeChunk
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)

# Synchronous engine for Celery tasks (Celery is not async-compatible)
_sync_engine = create_engine(settings.database_sync_url, pool_pre_ping=True)


def _get_sync_session() -> Session:
    """Return a new synchronous SQLAlchemy session for task use."""
    return Session(_sync_engine)


@celery_app.task(
    name="app.workers.tasks.ingestion_tasks.ingest_repository",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def ingest_repository(self: object, ingestion_id: str) -> dict[str, str]:
    """
    Background job to ingest a repository (Phase 3B).
    Clones the repository and discovers files safely.
    """
    logger.info(f"Starting ingestion job {ingestion_id}")

    # To ensure cleanup runs even on unexpected Celery failures, we keep track of the git service
    git_service = None

    try:
        with _get_sync_session() as session:
            # 1. Fetch the ingestion record and associated repository
            ingestion = session.scalar(
                select(RepositoryIngestion).where(RepositoryIngestion.id == uuid.UUID(ingestion_id))
            )
            
            if not ingestion:
                logger.error(f"Ingestion record {ingestion_id} not found.")
                return {"status": "error", "message": "Record not found"}
                
            repository = session.scalar(
                select(Repository).where(Repository.id == ingestion.repository_id)
            )

            # Find a user connected to this repository to obtain credentials
            # In a real app we might want the specific user who triggered this,
            # but any connected user with a valid token works for cloning.
            user_conn = session.scalar(
                select(UserConnectedRepository).where(UserConnectedRepository.repository_id == repository.id)
            )
            
            if not user_conn:
                raise RuntimeError("No user is connected to this repository. Cannot authenticate.")
                
            user = session.scalar(
                select(User).where(User.id == user_conn.user_id)
            )
            
            if not user or not user.github_access_token:
                raise RuntimeError("Connected user does not have a GitHub access token.")

            # 2. Mark as RUNNING and "Cloning"
            ingestion.status = IngestionStatus.RUNNING
            ingestion.started_at = datetime.now(UTC)
            ingestion.progress_message = "Cloning repository"
            session.commit()
            
            # Secure token decryption (in memory only)
            github_token = decrypt_string(user.github_access_token)

            git_service = GitRepositoryService(repository.id, ingestion.id)
            
        # We perform time-consuming I/O outside the DB transaction
        # 3. Clone Repository
        commit_sha = git_service.clone_repository(
            full_name=repository.full_name,
            default_branch=repository.default_branch,
            github_token=github_token
        )
        
        # Discard token from local scope
        del github_token

        with _get_sync_session() as session:
            ingestion = session.scalar(
                select(RepositoryIngestion).where(RepositoryIngestion.id == uuid.UUID(ingestion_id))
            )
            ingestion.progress_message = "Discovering files"
            repository = session.scalar(
                select(Repository).where(Repository.id == ingestion.repository_id)
            )
            repository.last_commit_sha = commit_sha
            session.commit()

        # 4. Discover Files
        discovery_service = FileDiscoveryService(git_service.get_source_dir())
        discovered_files = discovery_service.discover_files()

        with _get_sync_session() as session:
            ingestion = session.scalar(
                select(RepositoryIngestion).where(RepositoryIngestion.id == uuid.UUID(ingestion_id))
            )
            ingestion.progress_message = "Saving file metadata"
            session.commit()
            
            # Clean up any stale data from previous attempts (retries / re-runs)
            old_files = session.scalars(
                select(IndexedFile).where(IndexedFile.ingestion_id == ingestion.id)
            ).all()
            if old_files:
                old_file_ids = [f.id for f in old_files]
                # CASCADE deletes will handle CodeSymbol and CodeChunk
                session.execute(
                    delete(IndexedFile).where(IndexedFile.ingestion_id == ingestion.id)
                )
                session.commit()
                logger.info(f"Cleaned up {len(old_file_ids)} stale IndexedFile records from previous attempt.")

            # 5. Batch insert IndexedFile records
            indexed_files_to_insert = [
                IndexedFile(
                    repository_id=ingestion.repository_id,
                    ingestion_id=ingestion.id,
                    relative_path=f["relative_path"],
                    file_size=f["file_size"],
                    extension=f["extension"],
                    is_binary=f["is_binary"],
                    file_hash=f["file_hash"],
                )
                for f in discovered_files
            ]
            
            if indexed_files_to_insert:
                session.add_all(indexed_files_to_insert)
                session.commit()
            
        # 6. Parse and Extract
        parser = TreeSitterParser()
        
        parsed_count = 0
        unsupported_count = 0
        error_count = 0
        symbol_count = 0
        
        with _get_sync_session() as session:
            ingestion = session.scalar(select(RepositoryIngestion).where(RepositoryIngestion.id == uuid.UUID(ingestion_id)))
            
            indexed_files = session.scalars(select(IndexedFile).where(IndexedFile.ingestion_id == ingestion.id)).all()
            total_files = len(indexed_files)
            
            ingestion.file_count = total_files
            ingestion.progress_message = f"Parsing source files (0/{total_files})"
            session.commit()
            
            all_chunks = []
            
            for i, idx_file in enumerate(indexed_files):
                # Update progress periodically
                if i % 10 == 0:
                    ingestion.progress_message = f"Parsing source files ({i}/{total_files})"
                    session.commit()
                    
                if idx_file.is_binary:
                    continue
                    
                language = LanguageDetector.detect_language(idx_file.relative_path)
                if language == "UNKNOWN":
                    unsupported_count += 1
                    continue
                    
                file_path = git_service.get_source_dir() / idx_file.relative_path
                
                try:
                    with open(file_path, "rb") as f:
                        source_code = f.read()
                        
                    parse_result = parser.parse(source_code, language)
                    if parse_result.status == "FAILED":
                        error_count += 1
                        continue
                        
                    if parse_result.status == "UNSUPPORTED":
                        unsupported_count += 1
                        continue
                        
                    parsed_count += 1
                    
                    if parse_result.tree:
                        extractor = SymbolExtractorFactory.get_extractor(language, source_code)
                        extracted_symbols = extractor.extract(parse_result.tree.root_node)
                        
                        db_symbols = []
                        # We need to map extractor UUIDs to actual DB objects for parent/child
                        
                        for ext_sym in extracted_symbols:
                            db_sym = CodeSymbol(
                                id=ext_sym.id,
                                indexed_file_id=idx_file.id,
                                parent_symbol_id=ext_sym.parent_id,
                                name=ext_sym.name,
                                symbol_type=ext_sym.symbol_type,
                                language=language,
                                start_line=ext_sym.start_line,
                                start_column=ext_sym.start_column,
                                end_line=ext_sym.end_line,
                                end_column=ext_sym.end_column,
                                start_byte=ext_sym.start_byte,
                                end_byte=ext_sym.end_byte,
                                signature=ext_sym.signature,
                            )
                            db_symbols.append(db_sym)
                            
                        if db_symbols:
                            session.add_all(db_symbols)
                            symbol_count += len(db_symbols)
                            # Flush to ensure symbols are available for relationships
                            session.flush()
                            
                            # Semantic Chunking
                            chunker = SemanticChunker(source_code, idx_file)
                            file_chunk_requests = chunker.chunk_symbols(db_symbols)
                            
                            # Filter unchanged chunks idempotently
                            for req in file_chunk_requests:
                                existing_chunk = session.scalar(
                                    select(CodeChunk).where(
                                        CodeChunk.indexed_file_id == idx_file.id,
                                        CodeChunk.content_hash == req.content_hash
                                    )
                                )
                                if not existing_chunk:
                                    new_chunk = CodeChunk(
                                        id=uuid.uuid4(),
                                        indexed_file_id=req.indexed_file_id,
                                        code_symbol_id=req.code_symbol_id,
                                        parent_chunk_id=req.parent_chunk_id,
                                        content=req.content,
                                        chunk_type=req.chunk_type,
                                        symbol_name=req.symbol_name,
                                        language=req.language,
                                        class_name=req.class_name,
                                        parent_symbol=req.parent_symbol,
                                        module_name=req.module_name,
                                        context_path=req.context_path,
                                        start_line=req.start_line,
                                        end_line=req.end_line,
                                        start_byte=req.start_byte,
                                        end_byte=req.end_byte,
                                        content_hash=req.content_hash,
                                    )
                                    session.add(new_chunk)
                                    # To embed, we need the new chunk
                                    all_chunks.append({
                                        "chunk": new_chunk,
                                        "repository_id": str(ingestion.repository_id),
                                        "file_path": idx_file.relative_path,
                                    })
                                else:
                                    # Chunk unchanged, no need to re-embed, but ensure it's kept
                                    pass
                                    
                            session.commit()
                            
                except Exception as ex:
                    logger.warning(f"Failed to process file {idx_file.relative_path}: {ex}")
                    error_count += 1
            
            # Phase 3D: Embeddings & Vector Upsert
            if all_chunks:
                ingestion.progress_message = f"Generating embeddings for {len(all_chunks)} chunks"
                session.commit()
                
                async def embed_and_upsert():
                    qdrant_service = QdrantService()
                    await qdrant_service.initialize_collection()
                    
                    embedding_provider = EmbeddingFactory.get_provider()
                    
                    batch_size = settings.embedding_batch_size
                    for i in range(0, len(all_chunks), batch_size):
                        batch = all_chunks[i:i + batch_size]
                        texts = [item["chunk"].content for item in batch]
                        vectors = await embedding_provider.embed_documents(texts)
                        
                        payloads = []
                        for item in batch:
                            chunk = item["chunk"]
                            payloads.append(VectorPayload(
                                chunk_id=str(chunk.id),
                                repository_id=item["repository_id"],
                                indexed_file_id=str(chunk.indexed_file_id),
                                code_symbol_id=str(chunk.code_symbol_id) if chunk.code_symbol_id else None,
                                file_path=item["file_path"],
                                language=chunk.language,
                                chunk_type=chunk.chunk_type,
                                symbol_name=chunk.symbol_name,
                                class_name=chunk.class_name,
                                parent_symbol=chunk.parent_symbol,
                                module_name=chunk.module_name,
                                context_path=chunk.context_path,
                                start_line=chunk.start_line,
                                end_line=chunk.end_line,
                                content=chunk.content
                            ))
                        
                        await qdrant_service.upsert_vectors(vectors, payloads)
                
                try:
                    asyncio.run(embed_and_upsert())
                except Exception as embed_exc:
                    logger.error(f"Embedding failed: {embed_exc}")
                    raise RuntimeError("Embedding service unavailable") from embed_exc

            # Phase 3E: Build BM25 Keyword Index
            # Both Qdrant (semantic) and BM25 (keyword) indices must be ready
            # before the ingestion is marked as COMPLETED.
            ingestion.progress_message = "Building keyword search index"
            session.commit()

            try:
                from app.modules.retrieval.keyword_index import build_index, save_index

                # Collect ALL chunks for this repository (not just new ones)
                all_repo_chunks = session.scalars(
                    select(CodeChunk)
                    .join(IndexedFile, CodeChunk.indexed_file_id == IndexedFile.id)
                    .where(IndexedFile.repository_id == ingestion.repository_id)
                ).all()

                bm25_chunks_data = []
                for chunk in all_repo_chunks:
                    # Get file path from the indexed file
                    idx_file = session.scalar(
                        select(IndexedFile).where(IndexedFile.id == chunk.indexed_file_id)
                    )
                    file_path = idx_file.relative_path if idx_file else ""

                    bm25_chunks_data.append({
                        "chunk_id": str(chunk.id),
                        "repository_id": str(ingestion.repository_id),
                        "indexed_file_id": str(chunk.indexed_file_id),
                        "code_symbol_id": str(chunk.code_symbol_id) if chunk.code_symbol_id else None,
                        "file_path": file_path,
                        "language": chunk.language,
                        "chunk_type": chunk.chunk_type,
                        "symbol_name": chunk.symbol_name,
                        "class_name": chunk.class_name,
                        "parent_symbol": chunk.parent_symbol,
                        "module_name": chunk.module_name,
                        "context_path": chunk.context_path,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "content": chunk.content,
                    })

                if bm25_chunks_data:
                    bm25_index = build_index(ingestion.repository_id, bm25_chunks_data)
                    save_index(ingestion.repository_id, bm25_index)
                    logger.info(
                        f"BM25 index built for repository {ingestion.repository_id} "
                        f"with {len(bm25_chunks_data)} chunks."
                    )
                else:
                    logger.info(
                        f"No chunks to index for BM25 in repository {ingestion.repository_id}."
                    )

            except Exception as bm25_exc:
                logger.error(f"BM25 index build failed: {bm25_exc}")
                raise RuntimeError("BM25 keyword index build failed") from bm25_exc
                    
            ingestion.parsed_file_count = parsed_count
            ingestion.unsupported_file_count = unsupported_count
            ingestion.parse_error_count = error_count
            ingestion.symbol_count = symbol_count
            ingestion.status = IngestionStatus.COMPLETED
            ingestion.progress_message = "Completed"
            ingestion.completed_at = datetime.now(UTC)
            
            # Phase 3F: Update Repository index_version
            repository = session.scalar(select(Repository).where(Repository.id == ingestion.repository_id))
            repository.index_version = 2
            
            session.commit()
            
            logger.info(f"Ingestion {ingestion_id} status: COMPLETED. Parsed {parsed_count}, Extracted {symbol_count} symbols, Chunks {len(all_chunks)}.")

        return {"status": "success", "ingestion_id": ingestion_id, "files_discovered": total_files}

    except Exception as exc:
        logger.error(f"Ingestion job {ingestion_id} failed: {exc}")
        
        # Cleanup workspace on failure
        if git_service:
            try:
                git_service.cleanup_workspace()
            except Exception as cleanup_exc:
                logger.error(f"Failed to cleanup workspace: {cleanup_exc}")

        with _get_sync_session() as session:
            session.execute(
                update(RepositoryIngestion)
                .where(RepositoryIngestion.id == uuid.UUID(ingestion_id))
                .values(
                    status=IngestionStatus.FAILED,
                    progress_message="Failed",
                    error_message=str(exc),
                    completed_at=datetime.now(UTC)
                )
            )
            session.commit()
        raise
