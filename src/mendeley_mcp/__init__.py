"""
Mendeley MCP Server

An MCP server for integrating Mendeley reference manager with LLM applications.
"""

from .client import Document, Folder, MendeleyClient, MendeleyCredentials
from .server import mcp

__version__ = "0.1.0"
__all__ = [
    "mcp",
    "MendeleyClient",
    "MendeleyCredentials",
    "Document",
    "Folder",
]
