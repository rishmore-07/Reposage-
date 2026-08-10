"""
app/modules/indexing/language_detector.py

Detects programming languages based on file extensions and names.
"""

import os

LANGUAGE_MAP = {
    # Python
    ".py": "python",
    ".pyi": "python",
    # JavaScript / TypeScript
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    # Java
    ".java": "java",
    # C / C++
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
    # Go
    ".go": "go",
    # Rust
    ".rs": "rust",
    # HTML / CSS / JSON / Markdown
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".json": "json",
    ".md": "markdown",
    ".markdown": "markdown",
}


class LanguageDetector:
    """
    Detects the programming language of a file.
    """

    @staticmethod
    def detect_language(file_path: str) -> str:
        """
        Returns the language identifier (e.g. 'python') or 'UNKNOWN' if unsupported.
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        return LANGUAGE_MAP.get(ext, "UNKNOWN")
