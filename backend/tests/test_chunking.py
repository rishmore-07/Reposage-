import pytest
import uuid
from app.modules.indexing.chunking.chunker import SemanticChunker
from app.modules.repositories.models import IndexedFile, CodeSymbol

@pytest.fixture
def mock_file():
    return IndexedFile(
        id=uuid.uuid4(),
        relative_path="test_file.py",
        file_size=100,
        extension=".py",
        is_binary=False,
        file_hash="hash"
    )

def test_semantic_chunker(mock_file):
    source_code = b"def hello():\n    print('world')\n"
    
    symbol = CodeSymbol(
        id=uuid.uuid4(),
        indexed_file_id=mock_file.id,
        name="hello",
        symbol_type="function",
        language="python",
        start_line=0,
        end_line=1,
        start_byte=0,
        end_byte=len(source_code)
    )
    
    chunker = SemanticChunker(source_code, mock_file)
    chunks = chunker.chunk_symbols([symbol])
    
    assert len(chunks) == 1
    assert chunks[0].chunk_type == "function"
    assert chunks[0].symbol_name == "hello"
    assert "File: test_file.py" in chunks[0].content
    assert "def hello():" in chunks[0].content
