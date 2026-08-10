"""
Java, C/C++, Go, Rust extractors.
"""

import tree_sitter
from app.modules.indexing.symbol_extractor import BaseSymbolExtractor, ExtractedSymbol, SymbolExtractorFactory

@SymbolExtractorFactory.register("java")
class JavaExtractor(BaseSymbolExtractor):
    def _walk(self, node: tree_sitter.Node, parent_symbol: ExtractedSymbol | None):
        if node.type in ("class_declaration", "interface_declaration"):
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node) if name_node else "anonymous"
            sig = self._get_node_text(node).split("{")[0].strip()
            sym_type = "INTERFACE" if node.type == "interface_declaration" else "CLASS"
            sym = self._add_symbol(node, name, sym_type, parent_symbol, sig)
            
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    self._walk(child, sym)
            return
            
        elif node.type in ("method_declaration", "constructor_declaration"):
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node) if name_node else "anonymous"
            sig = self._get_node_text(node).split("{")[0].strip()
            self._add_symbol(node, name, "METHOD", parent_symbol, sig)
            # Not walking body for java methods right now
            return
            
        elif node.type == "import_declaration":
            self._add_symbol(node, self._get_node_text(node).strip(), "IMPORT", parent_symbol, self._get_node_text(node).strip())
            return
            
        for child in node.children:
            self._walk(child, parent_symbol)

@SymbolExtractorFactory.register("c")
@SymbolExtractorFactory.register("cpp")
class CppExtractor(BaseSymbolExtractor):
    def _walk(self, node: tree_sitter.Node, parent_symbol: ExtractedSymbol | None):
        if node.type in ("class_specifier", "struct_specifier"):
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node) if name_node else "anonymous"
            sig = self._get_node_text(node).split("{")[0].strip()
            sym = self._add_symbol(node, name, "CLASS" if node.type == "class_specifier" else "STRUCT", parent_symbol, sig)
            
            # walk body for methods
            for child in node.children:
                if child.type == "field_declaration_list":
                    self._walk(child, sym)
            return
            
        elif node.type == "function_definition":
            decl_node = node.child_by_field_name("declarator")
            name = "anonymous"
            if decl_node:
                # Need to find function_declarator inside
                ident = decl_node.child_by_field_name("declarator")
                if ident:
                    name = self._get_node_text(ident)
            sig = self._get_node_text(node).split("{")[0].strip()
            self._add_symbol(node, name, "FUNCTION", parent_symbol, sig)
            return
            
        for child in node.children:
            self._walk(child, parent_symbol)

@SymbolExtractorFactory.register("go")
class GoExtractor(BaseSymbolExtractor):
    def _walk(self, node: tree_sitter.Node, parent_symbol: ExtractedSymbol | None):
        if node.type == "type_declaration":
            # type MyStruct struct { ... }
            for child in node.children:
                if child.type == "type_spec":
                    name_node = child.child_by_field_name("name")
                    name = self._get_node_text(name_node) if name_node else "anonymous"
                    
                    type_node = child.child_by_field_name("type")
                    if type_node and type_node.type == "struct_type":
                        self._add_symbol(child, name, "STRUCT", parent_symbol, f"type {name} struct")
                    elif type_node and type_node.type == "interface_type":
                        self._add_symbol(child, name, "INTERFACE", parent_symbol, f"type {name} interface")
            return
            
        elif node.type == "function_declaration":
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node) if name_node else "anonymous"
            sig = self._get_node_text(node).split("{")[0].strip()
            self._add_symbol(node, name, "FUNCTION", parent_symbol, sig)
            return
            
        elif node.type == "method_declaration":
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node) if name_node else "anonymous"
            sig = self._get_node_text(node).split("{")[0].strip()
            self._add_symbol(node, name, "METHOD", parent_symbol, sig)
            return
            
        elif node.type == "import_spec":
            path_node = node.child_by_field_name("path")
            if path_node:
                self._add_symbol(node, self._get_node_text(path_node).strip('"\n'), "IMPORT", parent_symbol, self._get_node_text(node).strip())
            return
            
        for child in node.children:
            self._walk(child, parent_symbol)


@SymbolExtractorFactory.register("rust")
class RustExtractor(BaseSymbolExtractor):
    def _walk(self, node: tree_sitter.Node, parent_symbol: ExtractedSymbol | None):
        if node.type == "struct_item":
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node) if name_node else "anonymous"
            sig = self._get_node_text(node).split("{")[0].strip()
            self._add_symbol(node, name, "STRUCT", parent_symbol, sig)
            return
        elif node.type == "enum_item":
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node) if name_node else "anonymous"
            sig = self._get_node_text(node).split("{")[0].strip()
            self._add_symbol(node, name, "ENUM", parent_symbol, sig)
            return
        elif node.type == "impl_item":
            type_node = node.child_by_field_name("type")
            name = self._get_node_text(type_node) if type_node else "anonymous"
            sig = self._get_node_text(node).split("{")[0].strip()
            sym = self._add_symbol(node, name, "IMPL", parent_symbol, sig)
            
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    self._walk(child, sym)
            return
        elif node.type == "function_item":
            name_node = node.child_by_field_name("name")
            name = self._get_node_text(name_node) if name_node else "anonymous"
            sig = self._get_node_text(node).split("{")[0].strip()
            
            sym_type = "METHOD" if parent_symbol and parent_symbol.symbol_type == "IMPL" else "FUNCTION"
            self._add_symbol(node, name, sym_type, parent_symbol, sig)
            return
        elif node.type == "use_declaration":
            self._add_symbol(node, self._get_node_text(node).strip(), "IMPORT", parent_symbol, self._get_node_text(node).strip())
            return
            
        for child in node.children:
            self._walk(child, parent_symbol)
