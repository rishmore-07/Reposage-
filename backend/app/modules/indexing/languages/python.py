"""
Python symbol extractor.
"""

import tree_sitter
from app.modules.indexing.symbol_extractor import BaseSymbolExtractor, ExtractedSymbol, SymbolExtractorFactory

@SymbolExtractorFactory.register("python")
class PythonExtractor(BaseSymbolExtractor):
    
    def _walk(self, node: tree_sitter.Node, parent_symbol: ExtractedSymbol | None):
        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node) if name_node else "anonymous_class"
            
            # Extract basic signature (first line or up to colon)
            signature = self._get_node_text(node).split(":")[0].strip()
            
            sym = self._add_symbol(node, name, "CLASS", parent_symbol, signature)
            
            # Walk body
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    self._walk(child, sym)
            return

        elif node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node) if name_node else "anonymous_function"
            
            signature = self._get_node_text(node).split(":")[0].strip()
            
            # If parent is a class, it's a method
            sym_type = "METHOD" if parent_symbol and parent_symbol.symbol_type == "CLASS" else "FUNCTION"
            sym = self._add_symbol(node, name, sym_type, parent_symbol, signature)
            
            # Walk body
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    self._walk(child, sym)
            return
            
        elif node.type == "import_statement":
            # import X
            for child in node.children:
                if child.type == "dotted_name":
                    name = self._get_node_text(child)
                    self._add_symbol(node, name, "IMPORT", parent_symbol, f"import {name}")
            return
            
        elif node.type == "import_from_statement":
            # from X import Y
            module_name_node = node.child_by_field_name("module_name")
            module_name = self._get_node_text(module_name_node) if module_name_node else ""
            self._add_symbol(node, module_name, "IMPORT", parent_symbol, self._get_node_text(node).split("\n")[0].strip())
            return
            
        # Default traversal
        for child in node.children:
            self._walk(child, parent_symbol)
