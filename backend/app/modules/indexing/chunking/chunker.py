import hashlib
from typing import List
from app.modules.repositories.models import IndexedFile, CodeSymbol
from app.modules.indexing.chunking.schemas import ChunkRequest
from app.modules.indexing.chunking.context import StructuralContextExtractor, CodeChunkSearchDocumentBuilder

class SemanticChunker:
    """
    Transforms CodeSymbol records into semantic code chunks ready for embedding.
    Generates a deterministic hash for each chunk for idempotent indexing.
    """

    def __init__(self, source_code: bytes, indexed_file: IndexedFile):
        self.source_code = source_code
        self.indexed_file = indexed_file

    def _generate_hash(self, content: str) -> str:
        """Generate a deterministic SHA-256 hash for the chunk content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def chunk_symbols(self, symbols: List[CodeSymbol]) -> List[ChunkRequest]:
        """
        Convert a list of Tree-sitter CodeSymbols into ChunkRequests.
        Adds semantic context headers (File, Language, Symbol Name) to the chunk content.
        """
        extractor = StructuralContextExtractor(symbols)
        
        chunks = []
        for symbol in symbols:
            # Extract the raw snippet
            if symbol.start_byte is not None and symbol.end_byte is not None:
                snippet_bytes = self.source_code[symbol.start_byte:symbol.end_byte]
            else:
                # Fallback to line numbers if byte offsets are missing
                lines = self.source_code.split(b"\n")
                # Line numbers are 0-indexed in Tree-sitter, but let's assume they are stored 0-indexed.
                snippet_bytes = b"\n".join(lines[symbol.start_line:symbol.end_line + 1])
                
            snippet = snippet_bytes.decode("utf-8", errors="replace")

            # Extract structural context
            context = extractor.extract_context(symbol, self.indexed_file.relative_path)
            
            # Build canonical search document
            full_content = CodeChunkSearchDocumentBuilder.build_document(
                file_path=self.indexed_file.relative_path,
                language=symbol.language,
                module_name=context["module_name"],
                class_name=context["class_name"],
                parent_symbol=context["parent_symbol"],
                symbol_name=symbol.name,
                symbol_type=symbol.symbol_type,
                context_path=context["context_path"],
                code_content=snippet
            )

            chunk = ChunkRequest(
                indexed_file_id=self.indexed_file.id,
                code_symbol_id=symbol.id,
                parent_chunk_id=None,  # Parent hierarchy is tracked via CodeSymbol.parent_symbol_id
                content=full_content,
                chunk_type=symbol.symbol_type,
                symbol_name=symbol.name,
                language=symbol.language,
                class_name=context["class_name"],
                parent_symbol=context["parent_symbol"],
                module_name=context["module_name"],
                context_path=context["context_path"],
                start_line=symbol.start_line,
                end_line=symbol.end_line,
                start_byte=symbol.start_byte,
                end_byte=symbol.end_byte,
                content_hash=self._generate_hash(full_content)
            )
            chunks.append(chunk)

        # Also create a chunk for the entire file if it's small, or just file-level chunking
        # To avoid duplicating too much, we will rely on symbol chunks primarily.
        
        return chunks
