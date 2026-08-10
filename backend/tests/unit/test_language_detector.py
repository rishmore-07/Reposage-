import pytest
from app.modules.indexing.language_detector import LanguageDetector

def test_language_detector_supported():
    assert LanguageDetector.detect_language("main.py") == "python"
    assert LanguageDetector.detect_language("src/App.tsx") == "typescript"
    assert LanguageDetector.detect_language("index.js") == "javascript"
    assert LanguageDetector.detect_language("Server.java") == "java"
    assert LanguageDetector.detect_language("main.go") == "go"
    assert LanguageDetector.detect_language("lib.rs") == "rust"
    assert LanguageDetector.detect_language("style.css") == "css"
    assert LanguageDetector.detect_language("data.json") == "json"
    assert LanguageDetector.detect_language("README.md") == "markdown"

def test_language_detector_unsupported():
    assert LanguageDetector.detect_language("unknown.xyz") == "UNKNOWN"
    assert LanguageDetector.detect_language("Makefile") == "UNKNOWN"
    assert LanguageDetector.detect_language(".env") == "UNKNOWN"

def test_language_detector_case_insensitivity():
    assert LanguageDetector.detect_language("Main.PY") == "python"
    assert LanguageDetector.detect_language("APP.TSX") == "typescript"
