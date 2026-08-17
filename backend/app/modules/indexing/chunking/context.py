"""
app/modules/indexing/chunking/context.py

Extracts structural context (class, parent, module, context path) from CodeSymbol hierarchies.
Builds canonical search documents for embedding and BM25 index.
"""

from typing import List, Dict, Optional, Any
from app.modules.repositories.models import CodeSymbol, IndexedFile

def extract_module_name(relative_path: str, language: str) -> Optional[str]:
    """
    Derives the module name from the file path based on language conventions.
    """
    if not relative_path:
        return None

    path_no_ext = relative_path.rsplit(".", 1)[0]

    if language == "python":
        # e.g., backend/auth/service.py -> backend.auth.service
        return path_no_ext.replace("/", ".").replace("\\", ".")
    elif language == "java":
        # Attempt to find the package path by looking for standard roots like src/main/java
        # This is a heuristic. A more robust way is to parse the `package` statement in the AST,
        # but path-based is requested/acceptable when reliable.
        parts = path_no_ext.replace("\\", "/").split("/")
        if "src" in parts and "main" in parts and "java" in parts:
            idx = parts.index("java")
            return ".".join(parts[idx+1:])
        elif "src" in parts:
            idx = parts.index("src")
            return ".".join(parts[idx+1:])
        else:
            return ".".join(parts)
    elif language in ("javascript", "typescript", "go", "rust", "c", "cpp"):
        # For these, module/package is heavily tied to the directory path
        return path_no_ext.replace("/", ".").replace("\\", ".")
    
    return None

class CodeChunkSearchDocumentBuilder:
    """
    Builds the standardized textual representation of a code chunk for search (BM25 and Qdrant).
    """

    @staticmethod
    def build_document(
        file_path: str,
        language: str,
        module_name: Optional[str],
        class_name: Optional[str],
        parent_symbol: Optional[str],
        symbol_name: Optional[str],
        symbol_type: str,
        context_path: Optional[str],
        code_content: str
    ) -> str:
        """
        Builds the canonical contextual search document.
        """
        lines = []
        lines.append(f"File: {file_path}")
        lines.append(f"Language: {language}")
        
        if module_name:
            lines.append(f"Module: {module_name}")
            
        if class_name:
            lines.append(f"Class: {class_name}")
            
        if parent_symbol:
            lines.append(f"Parent: {parent_symbol}")
        else:
            lines.append("Parent: null")
            
        if symbol_name:
            lines.append(f"Symbol: {symbol_name}")
            
        lines.append(f"Type: {symbol_type}")
        
        if context_path:
            lines.append(f"Context: {context_path}")
            
        lines.append("")
        lines.append("Code:")
        lines.append(code_content)
        
        return "\n".join(lines)


class StructuralContextExtractor:
    """
    Efficiently traverses the symbol hierarchy in memory to compute context fields.
    """
    
    def __init__(self, symbols: List[CodeSymbol]):
        # Build id -> symbol map and children map for quick traversal
        self.symbols_by_id = {sym.id: sym for sym in symbols}
        self.children_by_parent: Dict[Any, List[CodeSymbol]] = {}
        
        for sym in symbols:
            pid = sym.parent_symbol_id
            if pid not in self.children_by_parent:
                self.children_by_parent[pid] = []
            self.children_by_parent[pid].append(sym)

    def get_ancestors(self, symbol: CodeSymbol) -> List[CodeSymbol]:
        """Returns the list of ancestor symbols, ordered from root to immediate parent."""
        ancestors = []
        current = symbol
        while current.parent_symbol_id and current.parent_symbol_id in self.symbols_by_id:
            parent = self.symbols_by_id[current.parent_symbol_id]
            ancestors.append(parent)
            current = parent
        ancestors.reverse()
        return ancestors

    def extract_context(self, symbol: CodeSymbol, file_path: str) -> Dict[str, Optional[str]]:
        """
        Computes class_name, parent_symbol, module_name, and context_path for a symbol.
        """
        ancestors = self.get_ancestors(symbol)
        
        # Determine class_name (first ancestor that is a class-like structure)
        class_name = None
        for anc in reversed(ancestors + [symbol]):
            if anc.symbol_type in ("CLASS", "STRUCT", "INTERFACE", "IMPL"):
                class_name = anc.name
                break
                
        # Determine parent_symbol (immediate parent)
        parent_symbol = ancestors[-1].name if ancestors else None
        
        # Determine context_path
        # Use structurally meaningful names
        path_parts = []
        for anc in ancestors:
            if anc.symbol_type not in ("IMPORT", "VARIABLE", "UNKNOWN"):
                path_parts.append(anc.name)
        
        path_parts.append(symbol.name)
        context_path = ".".join(path_parts) if path_parts else symbol.name
        
        # Derive module
        module_name = extract_module_name(file_path, symbol.language)
        
        return {
            "class_name": class_name,
            "parent_symbol": parent_symbol,
            "module_name": module_name,
            "context_path": context_path
        }
