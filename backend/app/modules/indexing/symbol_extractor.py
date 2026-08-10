"""
app/modules/indexing/symbol_extractor.py

Defines the extraction framework for ASTs.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

import tree_sitter


@dataclass
class ExtractedSymbol:
    """In-memory representation of an extracted code symbol."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    symbol_type: str = ""
    start_line: int = 0
    start_column: int = 0
    end_line: int = 0
    end_column: int = 0
    start_byte: Optional[int] = None
    end_byte: Optional[int] = None
    signature: Optional[str] = None
    
    # Hierarchical references
    parent_id: Optional[uuid.UUID] = None
    children: list["ExtractedSymbol"] = field(default_factory=list)


class BaseSymbolExtractor:
    """
    Base class for traversing an AST and extracting symbols.
    Language-specific extractors should inherit from this.
    """

    def __init__(self, source_code: bytes, language: str):
        self.source_code = source_code
        self.language = language
        self.symbols: list[ExtractedSymbol] = []

    def extract(self, root_node: tree_sitter.Node) -> list[ExtractedSymbol]:
        """
        Traverse the root node and return a flat list of all ExtractedSymbols,
        with parent_id properly populated.
        """
        self._walk(root_node, parent_symbol=None)
        return self.symbols
        
    def _add_symbol(
        self,
        node: tree_sitter.Node,
        name: str,
        symbol_type: str,
        parent_symbol: ExtractedSymbol | None,
        signature: str | None = None
    ) -> ExtractedSymbol:
        # tree-sitter line/column is 0-indexed. 
        # We will keep them 0-indexed, or 1-indexed? The prompt says: "Be consistent about whether database lines are zero-based or one-based... Prefer a user-friendly convention for line numbers and document the choice."
        # User friendly is 1-indexed for lines, 0-indexed for columns (standard in many IDEs).
        
        symbol = ExtractedSymbol(
            name=name,
            symbol_type=symbol_type,
            start_line=node.start_point[0] + 1,  # 1-indexed lines
            start_column=node.start_point[1],    # 0-indexed columns
            end_line=node.end_point[0] + 1,
            end_column=node.end_point[1],
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            signature=signature,
            parent_id=parent_symbol.id if parent_symbol else None
        )
        
        if parent_symbol:
            parent_symbol.children.append(symbol)
            
        self.symbols.append(symbol)
        return symbol

    def _walk(self, node: tree_sitter.Node, parent_symbol: ExtractedSymbol | None):
        """
        Recursively walk the AST. Override this or specific visitation methods in subclasses.
        """
        # Default behavior: Just visit all children without extracting symbols
        for child in node.children:
            self._walk(child, parent_symbol)

    def _get_node_text(self, node: tree_sitter.Node) -> str:
        """Helper to extract text from a node."""
        if not node:
            return ""
        return self.source_code[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


class SymbolExtractorFactory:
    """
    Factory to retrieve the appropriate extractor for a given language.
    """
    _registry = {}

    @classmethod
    def register(cls, language: str):
        def decorator(extractor_class):
            cls._registry[language] = extractor_class
            return extractor_class
        return decorator

    @classmethod
    def get_extractor(cls, language: str, source_code: bytes) -> BaseSymbolExtractor:
        extractor_class = cls._registry.get(language)
        if extractor_class:
            return extractor_class(source_code, language)
        # Fallback empty extractor if language doesn't have specific rules
        return BaseSymbolExtractor(source_code, language)

# Import languages to register them automatically
import app.modules.indexing.languages  # noqa: E402
