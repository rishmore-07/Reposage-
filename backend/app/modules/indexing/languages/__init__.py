"""
Import all language extractors to register them with the factory.
"""

from .python import PythonExtractor
from .javascript import JavaScriptExtractor, TypeScriptExtractor
from .core import JavaExtractor, CppExtractor, GoExtractor, RustExtractor

__all__ = [
    "PythonExtractor",
    "JavaScriptExtractor",
    "TypeScriptExtractor",
    "JavaExtractor",
    "CppExtractor",
    "GoExtractor",
    "RustExtractor",
]
