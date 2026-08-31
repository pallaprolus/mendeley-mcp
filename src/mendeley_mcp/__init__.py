"""
Mendeley MCP Server

An MCP server for integrating Mendeley reference manager with LLM applications.
"""

from .client import Document, Folder, MendeleyClient, MendeleyCredentials
from .server import __version__, mcp

__all__ = [
    "__version__",
    "mcp",
    "MendeleyClient",
    "MendeleyCredentials",
    "Document",
    "Folder",
]
