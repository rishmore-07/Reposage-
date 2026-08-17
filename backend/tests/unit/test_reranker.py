import pytest
from app.modules.retrieval.reranker import MockRerankerProvider
from app.modules.retrieval.schemas import RerankerCandidate

@pytest.fixture
def mock_reranker():
    return MockRerankerProvider()

@pytest.fixture
def sample_candidates():
    return [
        RerankerCandidate(
            chunk_id="1",
            repository_id="repo-1",
            file_path="foo.py",
            language="python",
            chunk_type="code",
            content="def something(): pass",
            context_path="foo.something",
            symbol_name="something",
            rrf_score=0.1
        ),
        RerankerCandidate(
            chunk_id="2",
            repository_id="repo-1",
            file_path="bar.py",
            language="python",
            chunk_type="code",
            content="def auth(): pass",
            context_path="bar.auth",
            symbol_name="auth",
            rrf_score=0.2
        )
    ]

@pytest.mark.asyncio
async def test_mock_reranker_deterministic_scoring(mock_reranker, sample_candidates):
    query = "auth"
    reranked = await mock_reranker.rerank(query, sample_candidates, top_k=10)
    
    assert len(reranked) == 2
    # "auth" appears in chunk 2's context_path, symbol_name, and content.
    assert reranked[0].chunk_id == "2"
    assert reranked[1].chunk_id == "1"
    assert reranked[0].reranker_score > reranked[1].reranker_score
    
    # Check score preservation
    assert reranked[0].rrf_score == 0.2
    assert reranked[1].rrf_score == 0.1

@pytest.mark.asyncio
async def test_mock_reranker_empty_candidates(mock_reranker):
    reranked = await mock_reranker.rerank("query", [], top_k=10)
    assert reranked == []

@pytest.mark.asyncio
async def test_mock_reranker_top_k(mock_reranker, sample_candidates):
    # Pass top_k=1
    reranked = await mock_reranker.rerank("auth", sample_candidates, top_k=1)
    assert len(reranked) == 1
    assert reranked[0].chunk_id == "2"

@pytest.mark.asyncio
async def test_mock_reranker_repeated_execution(mock_reranker, sample_candidates):
    run1 = await mock_reranker.rerank("auth system", sample_candidates, top_k=10)
    run2 = await mock_reranker.rerank("auth system", sample_candidates, top_k=10)
    
    assert run1[0].chunk_id == run2[0].chunk_id
    assert run1[0].reranker_score == run2[0].reranker_score

@pytest.mark.asyncio
async def test_mock_reranker_empty_query(mock_reranker, sample_candidates):
    reranked = await mock_reranker.rerank("", sample_candidates, top_k=10)
    assert len(reranked) == 2
    # Should preserve original order
    assert reranked[0].chunk_id == "1"
    assert reranked[1].chunk_id == "2"
