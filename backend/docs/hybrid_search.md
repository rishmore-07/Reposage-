# RepoSage Hybrid Search Architecture

## Overview

RepoSage uses a **Hybrid Search** architecture that combines two complementary
retrieval strategies to find the most relevant code chunks:

```
                         User Query
                             │
                +────────────┴────────────+
                │                         │
                ▼                         ▼
         Keyword Search              Semantic Search
             BM25                  Nomic + Qdrant
                │                         │
                +────────────┬────────────+
                             │
                             ▼
                    Reciprocal Rank
                       Fusion (RRF)
                             │
                             ▼
                      Hybrid Results
```

## Search Modes

RepoSage supports three retrieval modes:

| Mode | Strategy | Best For |
|------|----------|----------|
| `semantic` | Vector similarity via Nomic embeddings + Qdrant | Conceptual queries, paraphrases |
| `keyword` | BM25 lexical ranking | Exact identifiers, function names, variable names |
| `hybrid` | Both + RRF fusion (default) | General queries combining both strengths |

## How Keyword Search Works

### BM25 (Best Match 25)

BM25 is a probabilistic ranking function that scores documents based on term
frequency (TF), inverse document frequency (IDF), and document length normalization.

Each code chunk is tokenized into a searchable document combining:

```
File: backend/auth/service.py
Language: Python
Type: function
Symbol: authenticate_user

def authenticate_user(username, password):
    ...
```

This ensures that queries for function names, file paths, class names,
and identifiers all benefit from BM25 ranking.

### Index Lifecycle

```
Repository Ingestion
        ↓
Clone → Parse → Chunk → CodeChunk records
        ↓
Generate Embeddings → Qdrant
        ↓
Build BM25 Index → data/keyword_indices/{repo_id}.pkl
        ↓
Validate both indices ready
        ↓
Mark ingestion COMPLETED
```

The BM25 index is built from the **complete, finalized** set of CodeChunks
after all embedding and vector upserts are done. Both Qdrant and BM25
indices must be ready before the ingestion is marked as completed.

### Staleness Detection

Before using a persisted BM25 index, the system validates it against the
current CodeChunk IDs in the database:

```
stored chunk IDs  vs  current CodeChunk IDs
       ↓                       ↓
       match? → use index
       differ? → invalidate → rebuild
```

## How Semantic Search Works

Semantic search uses dense vector embeddings to find conceptually related code:

1. Query text → Nomic embedding (768-dim) via Ollama
2. Vector similarity search in Qdrant (cosine distance)
3. Repository-scoped filtering via Qdrant payload filter

This allows queries like "Where are login credentials verified?" to find
`authenticate_user()` even when the exact words don't match.

## Why RRF (Reciprocal Rank Fusion)

BM25 scores and cosine similarity scores have completely different
distributions. Directly adding them produces meaningless results.

RRF solves this by using **ranks** instead of raw scores:

```
RRF_score(d) = Σ 1 / (k + rank_i(d))
```

Where:
- `k` = 60 (configurable constant)
- `rank_i(d)` = rank of document `d` in system `i` (1-indexed)

Example:

```
Semantic: A(rank 1), B(rank 2), C(rank 3)
Keyword:  B(rank 1), A(rank 2), D(rank 3)

RRF scores:
A = 1/(60+1) + 1/(60+2) = 0.01639 + 0.01613 = 0.03252
B = 1/(60+2) + 1/(60+1) = 0.01613 + 0.01639 = 0.03252
C = 1/(60+3) = 0.01587
D = 1/(60+3) = 0.01587
```

Chunks appearing in both systems get boosted. Chunks unique to one system
still appear but with lower scores.

## Repository Isolation

**Every search operation is scoped to a single repository.**

- **Semantic**: Qdrant filter on `repository_id` payload field
- **Keyword**: Each repository has its own BM25 index file
- **Hybrid**: Only fuses results from the same repository

This is enforced at every layer and tested explicitly.

## Configuration

All search parameters are configurable via environment variables:

```env
# Default search mode
SEARCH_MODE=hybrid

# Candidate pool sizes (retrieve more than final K for fusion)
SEMANTIC_CANDIDATE_K=50
KEYWORD_CANDIDATE_K=50

# Final result count
HYBRID_TOP_K=10

# RRF fusion constant
RRF_K=60

# BM25 index storage directory
KEYWORD_INDEX_DIR=./data/keyword_indices
```

## Failure Handling

### At Query Time (Graceful Degradation)

| Scenario | Behavior |
|----------|----------|
| Qdrant unavailable | Returns keyword-only results |
| BM25 index missing | Returns semantic-only results |
| Both unavailable | Returns HTTP 503 with clear error |

Empty results are never returned silently when a backend fails.

### At Ingestion Time (Strict)

If BM25 index building fails during ingestion, the ingestion is marked
as **FAILED**. This prevents the system from claiming a repository is
fully indexed when keyword search would not work.

## API Usage

### Search Endpoint

```
POST /api/v1/repositories/{repository_id}/search
```

#### Request Body

```json
{
    "query": "Where is JWT authentication implemented?",
    "top_k": 10,
    "mode": "hybrid",
    "debug": false
}
```

#### Response

```json
{
    "results": [
        {
            "chunk_id": "...",
            "repository_id": "...",
            "file_path": "backend/auth/middleware.py",
            "language": "python",
            "chunk_type": "function",
            "symbol_name": "auth_middleware",
            "content": "...",
            "score": 0.032,
            "rank": 1,
            "source": "hybrid"
        }
    ],
    "mode": "hybrid",
    "total_candidates": 5
}
```

#### Debug Mode

Set `"debug": true` to include ranking details:

```json
{
    "semantic_rank": 2,
    "keyword_rank": 1,
    "semantic_score": 0.85,
    "keyword_score": 4.2,
    "rrf_score": 0.032
}
```

## How to Run Retrieval Evaluation

```bash
# Run evaluation tests with output
pytest tests/evaluation/test_retrieval_quality.py -v -s

# Run all search tests
pytest tests/unit/test_rrf.py tests/unit/test_keyword_search.py \
       tests/unit/test_hybrid_search.py tests/unit/test_evaluation.py \
       tests/integration/test_search.py -v
```

## Security Notes

### Pickle Files

BM25 indices are stored as pickle files. To prevent arbitrary code execution:

- Pickle files are **only** loaded from the RepoSage-managed `keyword_index_dir`
- Repository ID format is validated (UUID regex) to prevent path traversal
- File location is verified against the expected directory before unpickling
- User-supplied file paths are **never** accepted for unpickling
