"""
JavaScript / TypeScript symbol extractor.
"""

import tree_sitter
from app.modules.indexing.symbol_extractor import BaseSymbolExtractor, ExtractedSymbol, SymbolExtractorFactory

class JSTSExtractor(BaseSymbolExtractor):
    
    def _walk(self, node: tree_sitter.Node, parent_symbol: ExtractedSymbol | None):
        if node.type in ("class_declaration", "class"):
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node) if name_node else "anonymous_class"
            
            # Simple signature logic
            text = self._get_node_text(node)
            signature = text.split("{")[0].strip()
            
            sym = self._add_symbol(node, name, "CLASS", parent_symbol, signature)
            
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    self._walk(child, sym)
            return

        elif node.type in ("function_declaration", "function_item", "arrow_function", "method_definition"):
            # function_declaration/arrow_function/method_definition
            name = "anonymous_function"
            
            if node.type == "method_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = self._get_node_text(name_node)
            else:
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = self._get_node_text(name_node)
                elif node.parent and node.parent.type == "variable_declarator":
                    # const myFunc = () => {}
                    name_node = node.parent.child_by_field_name("name")
                    if name_node:
                        name = self._get_node_text(name_node)
            
            signature = self._get_node_text(node).split("{")[0].strip()
            if len(signature) > 200:
                signature = signature[:197] + "..."
            
            sym_type = "METHOD" if node.type == "method_definition" else "FUNCTION"
            sym = self._add_symbol(node, name, sym_type, parent_symbol, signature)
            
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    self._walk(child, sym)
            return

        elif node.type == "import_statement":
            source_node = node.child_by_field_name("source")
            if source_node:
                source = self._get_node_text(source_node).strip("'\"")
                self._add_symbol(node, source, "IMPORT", parent_symbol, self._get_node_text(node).strip())
            return
            
        elif node.type == "export_statement":
            # Just record it, let's extract the actual symbols inside
            # Usually export class X, we want the class X symbol
            declaration = node.child_by_field_name("declaration")
            if declaration:
                # we just process the declaration, it will get picked up as class/function
                self._walk(declaration, parent_symbol)
            return

        # Default traversal
        for child in node.children:
            self._walk(child, parent_symbol)


@SymbolExtractorFactory.register("javascript")
class JavaScriptExtractor(JSTSExtractor):
    pass

@SymbolExtractorFactory.register("typescript")
class TypeScriptExtractor(JSTSExtractor):
    def _walk(self, node: tree_sitter.Node, parent_symbol: ExtractedSymbol | None):
        if node.type == "interface_declaration":
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node) if name_node else "anonymous_interface"
            signature = self._get_node_text(node).split("{")[0].strip()
            self._add_symbol(node, name, "INTERFACE", parent_symbol, signature)
            # could walk methods inside interface if desired
            return
        elif node.type == "type_alias_declaration":
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node) if name_node else "anonymous_type"
            signature = self._get_node_text(node).split("=")[0].strip()
            self._add_symbol(node, name, "TYPE", parent_symbol, signature)
            return
            
        super()._walk(node, parent_symbol)
