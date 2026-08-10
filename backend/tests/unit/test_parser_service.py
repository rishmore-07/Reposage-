import pytest
from app.modules.indexing.parser_service import TreeSitterParser

def test_parser_service_valid_python():
    parser = TreeSitterParser()
    result = parser.parse(b"def hello():\n    print('world')", "python")
    
    assert result.status == "SUCCESS"
    assert result.tree is not None
    assert result.tree.root_node.has_error is False

def test_parser_service_valid_javascript():
    parser = TreeSitterParser()
    result = parser.parse(b"function hello() { console.log('world'); }", "javascript")
    
    assert result.status == "SUCCESS"
    assert result.tree is not None

def test_parser_service_invalid_python():
    parser = TreeSitterParser()
    # Missing colon and indentation
    result = parser.parse(b"def hello()\nprint('world')", "python")
    
    # Tree-sitter still produces a tree, but with errors
    assert result.status == "PARTIAL"
    assert result.tree is not None
    assert result.tree.root_node.has_error is True

def test_parser_service_empty_source():
    parser = TreeSitterParser()
    result = parser.parse(b"", "python")
    
    assert result.status == "SUCCESS"
    assert result.tree is not None

def test_parser_service_unsupported_language():
    parser = TreeSitterParser()
    result = parser.parse(b"some text", "UNKNOWN")
    
    assert result.status == "UNSUPPORTED"
    assert result.tree is None

def test_parser_service_missing_grammar():
    parser = TreeSitterParser()
    result = parser.parse(b"some text", "not_a_real_language_123")
    
    assert result.status == "FAILED"
    assert result.tree is None
    assert "Grammar not found" in result.error_message
