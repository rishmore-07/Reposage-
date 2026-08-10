"""
app/modules/indexing/parser_service.py

Provides a safe facade for Tree-sitter parsing.
"""

import importlib
from dataclasses import dataclass

import tree_sitter
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ParseResult:
    status: str  # "SUCCESS", "PARTIAL", "FAILED", "UNSUPPORTED"
    tree: tree_sitter.Tree | None
    error_message: str | None = None


class TreeSitterParser:
    """
    Service for parsing source code into an AST.
    Safely loads grammars and handles parsing errors without crashing.
    """

    def __init__(self):
        # Cache loaded languages to avoid re-importing
        self._languages = {}

    def _get_language(self, lang_name: str) -> tree_sitter.Language | None:
        if lang_name in self._languages:
            return self._languages[lang_name]

        # e.g., 'tree-sitter-python'
        # The python package is typically imported as tree_sitter_python
        module_name = f"tree_sitter_{lang_name}"
        
        try:
            module = importlib.import_module(module_name)
            # Modern tree-sitter bindings provide a `language()` function
            ts_language = tree_sitter.Language(module.language())
            self._languages[lang_name] = ts_language
            return ts_language
        except ImportError:
            logger.warning(f"Grammar package {module_name} not installed.")
            return None
        except Exception as e:
            logger.error(f"Failed to load language grammar {lang_name}: {e}")
            return None

    def parse(self, source_code: bytes, language_name: str) -> ParseResult:
        """
        Parses source code and returns a syntax tree.
        """
        if language_name == "UNKNOWN":
            return ParseResult(status="UNSUPPORTED", tree=None)

        ts_lang = self._get_language(language_name)
        if not ts_lang:
            return ParseResult(status="FAILED", tree=None, error_message=f"Grammar not found for {language_name}")

        try:
            parser = tree_sitter.Parser(ts_lang)
            tree = parser.parse(source_code)
            
            if tree.root_node.has_error:
                return ParseResult(status="PARTIAL", tree=tree)
            return ParseResult(status="SUCCESS", tree=tree)
            
        except Exception as e:
            logger.error(f"Tree-sitter parse exception for {language_name}: {e}")
            return ParseResult(status="FAILED", tree=None, error_message=str(e))
