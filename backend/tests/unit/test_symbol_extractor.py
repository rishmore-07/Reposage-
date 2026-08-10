import pytest
import tree_sitter
from app.modules.indexing.parser_service import TreeSitterParser
from app.modules.indexing.symbol_extractor import SymbolExtractorFactory

# Ensure all language extractors are registered
import app.modules.indexing.languages  # noqa: F401

def parse_and_extract(source_code: bytes, language: str):
    parser = TreeSitterParser()
    result = parser.parse(source_code, language)
    assert result.tree is not None
    
    extractor = SymbolExtractorFactory.get_extractor(language, source_code)
    return extractor.extract(result.tree.root_node)

def test_extract_python():
    source = b"""
import os
from datetime import datetime

class MyClass:
    def __init__(self):
        self.value = 1
        
    def my_method(self, x: int) -> int:
        return x + 1

def my_func():
    pass
"""
    symbols = parse_and_extract(source, "python")
    
    # 2 imports, 1 class, 2 methods, 1 function = 6 symbols
    assert len(symbols) == 6
    
    # Check imports
    imports = [s for s in symbols if s.symbol_type == "IMPORT"]
    assert len(imports) == 2
    assert imports[0].name == "os"
    assert imports[1].name == "datetime"
    
    # Check class
    classes = [s for s in symbols if s.symbol_type == "CLASS"]
    assert len(classes) == 1
    my_class = classes[0]
    assert my_class.name == "MyClass"
    assert "class MyClass" in my_class.signature
    
    # Check methods
    methods = [s for s in symbols if s.symbol_type == "METHOD"]
    assert len(methods) == 2
    assert methods[0].name == "__init__"
    assert methods[0].parent_id == my_class.id
    
    assert methods[1].name == "my_method"
    assert methods[1].parent_id == my_class.id
    
    # Check function
    funcs = [s for s in symbols if s.symbol_type == "FUNCTION"]
    assert len(funcs) == 1
    assert funcs[0].name == "my_func"
    assert funcs[0].parent_id is None

def test_extract_javascript():
    source = b"""
import { useState } from 'react';

export class MyComponent {
    render() {
        return null;
    }
}

function helper(a, b) {
    return a + b;
}

const arrowHelper = () => {}
"""
    symbols = parse_and_extract(source, "javascript")
    
    imports = [s for s in symbols if s.symbol_type == "IMPORT"]
    assert len(imports) == 1
    assert imports[0].name == "react"
    
    classes = [s for s in symbols if s.symbol_type == "CLASS"]
    assert len(classes) == 1
    assert classes[0].name == "MyComponent"
    
    methods = [s for s in symbols if s.symbol_type == "METHOD"]
    assert len(methods) == 1
    assert methods[0].name == "render"
    assert methods[0].parent_id == classes[0].id
    
    funcs = [s for s in symbols if s.symbol_type == "FUNCTION"]
    assert len(funcs) == 2
    func_names = {f.name for f in funcs}
    assert "helper" in func_names
    assert "arrowHelper" in func_names

def test_extract_java():
    source = b"""
import java.util.List;

public class Server {
    public Server() {}
    
    public void start() {}
}
"""
    symbols = parse_and_extract(source, "java")
    
    imports = [s for s in symbols if s.symbol_type == "IMPORT"]
    assert imports[0].name == "import java.util.List;"
    
    classes = [s for s in symbols if s.symbol_type == "CLASS"]
    assert classes[0].name == "Server"
    
    methods = [s for s in symbols if s.symbol_type == "METHOD"]
    assert len(methods) == 2
    assert methods[0].name == "Server"
    assert methods[1].name == "start"

def test_extract_go():
    source = b"""
import "fmt"

type User struct {
    ID int
}

func (u *User) GetName() string {
    return "name"
}

func main() {
    fmt.Println("Hello")
}
"""
    symbols = parse_and_extract(source, "go")
    
    imports = [s for s in symbols if s.symbol_type == "IMPORT"]
    assert imports[0].name == "fmt"
    
    structs = [s for s in symbols if s.symbol_type == "STRUCT"]
    assert structs[0].name == "User"
    
    methods = [s for s in symbols if s.symbol_type == "METHOD"]
    assert methods[0].name == "GetName"
    
    funcs = [s for s in symbols if s.symbol_type == "FUNCTION"]
    assert funcs[0].name == "main"

def test_extract_rust():
    source = b"""
use std::collections::HashMap;

struct App {
    state: i32
}

impl App {
    fn new() -> Self {
        App { state: 0 }
    }
}

fn helper() {}
"""
    symbols = parse_and_extract(source, "rust")
    
    imports = [s for s in symbols if s.symbol_type == "IMPORT"]
    assert imports[0].name == "use std::collections::HashMap;"
    
    structs = [s for s in symbols if s.symbol_type == "STRUCT"]
    assert structs[0].name == "App"
    
    impls = [s for s in symbols if s.symbol_type == "IMPL"]
    assert impls[0].name == "App"
    
    methods = [s for s in symbols if s.symbol_type == "METHOD"]
    assert methods[0].name == "new"
    assert methods[0].parent_id == impls[0].id
    
    funcs = [s for s in symbols if s.symbol_type == "FUNCTION"]
    assert funcs[0].name == "helper"
