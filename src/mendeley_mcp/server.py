"""
Mendeley MCP Server - Expose Mendeley library to LLM applications.

This server provides tools for searching, retrieving, and managing
documents in your Mendeley reference library.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from .auth import load_credentials
from .client import Document, MendeleyClient, MendeleyCredentials

# Initialize the MCP server
mcp = FastMCP("mendeley")

# Global client instance
_client: MendeleyClient | None = None


def get_credentials() -> MendeleyCredentials:
    """Get Mendeley credentials from environment or saved config."""
    # First try environment variables
    client_id = os.environ.get("MENDELEY_CLIENT_ID")
    client_secret = os.environ.get("MENDELEY_CLIENT_SECRET")
    access_token = os.environ.get("MENDELEY_ACCESS_TOKEN")
    refresh_token = os.environ.get("MENDELEY_REFRESH_TOKEN")

    if client_id and client_secret and (access_token or refresh_token):
        return MendeleyCredentials(
            client_id=client_id,
            client_secret=client_secret,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    # Fall back to saved credentials
    saved = load_credentials()
    if saved:
        return MendeleyCredentials(
            client_id=saved.get("client_id", ""),
            client_secret=saved.get("client_secret", ""),
            access_token=saved.get("access_token"),
            refresh_token=saved.get("refresh_token"),
        )

    raise ValueError(
        "No Mendeley credentials found. Either:\n"
        "1. Run 'mendeley-auth login' to authenticate, or\n"
        "2. Set MENDELEY_CLIENT_ID, MENDELEY_CLIENT_SECRET, and "
        "MENDELEY_REFRESH_TOKEN environment variables.\n\n"
        "Register your app at: https://dev.mendeley.com/myapps.html"
    )


async def get_client() -> MendeleyClient:
    """Get or create the Mendeley client."""
    global _client
    if _client is None:
        credentials = get_credentials()
        _client = MendeleyClient(credentials)
        await _client.__aenter__()
    return _client


def format_document(doc: Document) -> dict[str, Any]:
    """Format a document for output."""
    return {
        "id": doc.id,
        "title": doc.title,
        "authors": [
            f"{a.get('last_name', '')}, {a.get('first_name', '')}"
            for a in doc.authors
        ],
        "year": doc.year,
        "type": doc.type,
        "source": doc.source,
        "abstract": doc.abstract[:500] + "..." if doc.abstract and len(doc.abstract) > 500 else doc.abstract,
        "identifiers": doc.identifiers,
        "has_pdf": doc.file_attached,
        "citation": doc.format_citation(),
    }


@mcp.tool()
async def mendeley_search_library(
    query: str,
    limit: int = 20,
) -> str:
    """
    Search your Mendeley library for documents.

    Args:
        query: Search query (searches title, authors, abstract, notes)
        limit: Maximum number of results (default: 20, max: 100)

    Returns:
        JSON array of matching documents with metadata
    """
    client = await get_client()
    limit = min(limit, 100)

    try:
        documents = await client.search_library(query, limit=limit)
        results = [format_document(doc) for doc in documents]
        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def mendeley_get_document(
    document_id: str,
) -> str:
    """
    Get detailed information about a specific document.

    Args:
        document_id: The Mendeley document ID

    Returns:
        JSON object with full document metadata
    """
    client = await get_client()

    try:
        doc = await client.get_document(document_id)
        result = {
            "id": doc.id,
            "title": doc.title,
            "authors": doc.authors,
            "year": doc.year,
            "type": doc.type,
            "source": doc.source,
            "abstract": doc.abstract,
            "identifiers": doc.identifiers,
            "keywords": doc.keywords,
            "tags": doc.tags,
            "has_pdf": doc.file_attached,
            "created": doc.created,
            "last_modified": doc.last_modified,
            "citation": doc.format_citation(),
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def mendeley_list_documents(
    folder_id: str | None = None,
    limit: int = 50,
    sort_by: str = "last_modified",
) -> str:
    """
    List documents in your library or a specific folder.

    Args:
        folder_id: Optional folder ID to filter by
        limit: Maximum number of results (default: 50, max: 100)
        sort_by: Sort field - 'last_modified', 'created', or 'title'

    Returns:
        JSON array of documents
    """
    client = await get_client()
    limit = min(limit, 100)

    valid_sorts = ["last_modified", "created", "title"]
    if sort_by not in valid_sorts:
        sort_by = "last_modified"

    try:
        documents = await client.get_documents(
            folder_id=folder_id,
            limit=limit,
            sort=sort_by,
        )
        results = [format_document(doc) for doc in documents]
        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def mendeley_list_folders() -> str:
    """
    List all folders/collections in your Mendeley library.

    Returns:
        JSON array of folders with their IDs and names
    """
    client = await get_client()

    try:
        folders = await client.get_folders()
        results = [
            {
                "id": folder.id,
                "name": folder.name,
                "parent_id": folder.parent_id,
            }
            for folder in folders
        ]
        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def mendeley_search_catalog(
    query: str,
    limit: int = 20,
) -> str:
    """
    Search the global Mendeley catalog (100M+ papers).

    Use this to find papers that may not be in your library.

    Args:
        query: Search query
        limit: Maximum results (default: 20, max: 100)

    Returns:
        JSON array of catalog entries
    """
    client = await get_client()
    limit = min(limit, 100)

    try:
        results = await client.search_catalog(query, limit=limit)
        formatted = []
        for item in results:
            formatted.append({
                "catalog_id": item.get("id"),
                "title": item.get("title"),
                "authors": [
                    f"{a.get('last_name', '')}, {a.get('first_name', '')}"
                    for a in item.get("authors", [])
                ],
                "year": item.get("year"),
                "source": item.get("source"),
                "identifiers": item.get("identifiers"),
                "abstract": item.get("abstract", "")[:300] + "..." if item.get("abstract") else None,
            })
        return json.dumps(formatted, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def mendeley_get_by_doi(
    doi: str,
) -> str:
    """
    Look up a paper by its DOI in the Mendeley catalog.

    Args:
        doi: The DOI of the paper (e.g., "10.1038/nature12373")

    Returns:
        JSON object with paper metadata
    """
    client = await get_client()

    try:
        result = await client.get_catalog_document(doi=doi)
        if not result:
            return json.dumps({"error": f"No paper found with DOI: {doi}"})

        formatted = {
            "catalog_id": result.get("id"),
            "title": result.get("title"),
            "authors": result.get("authors"),
            "year": result.get("year"),
            "source": result.get("source"),
            "abstract": result.get("abstract"),
            "identifiers": result.get("identifiers"),
            "keywords": result.get("keywords"),
            "link": result.get("link"),
        }
        return json.dumps(formatted, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def mendeley_add_document(
    title: str,
    doc_type: str = "journal",
    authors: list[dict[str, str]] | None = None,
    year: int | None = None,
    source: str | None = None,
    abstract: str | None = None,
    identifiers: dict[str, str] | None = None,
) -> str:
    """
    Add a new document to your Mendeley library.

    Args:
        title: Document title (required)
        doc_type: Type - 'journal', 'book', 'conference_proceedings', etc.
        authors: List of author dicts with 'first_name' and 'last_name'
        year: Publication year
        source: Journal/book name
        abstract: Document abstract
        identifiers: Dict with 'doi', 'pmid', 'isbn', etc.

    Returns:
        JSON object with the created document
    """
    client = await get_client()

    kwargs: dict[str, Any] = {}
    if authors:
        kwargs["authors"] = authors
    if year:
        kwargs["year"] = year
    if source:
        kwargs["source"] = source
    if abstract:
        kwargs["abstract"] = abstract
    if identifiers:
        kwargs["identifiers"] = identifiers

    try:
        doc = await client.add_document(title=title, doc_type=doc_type, **kwargs)
        return json.dumps(format_document(doc), indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("mendeley://library/recent")
async def get_recent_documents() -> str:
    """Get the 10 most recently modified documents in the library."""
    client = await get_client()
    try:
        documents = await client.get_documents(limit=10, sort="last_modified")
        results = [format_document(doc) for doc in documents]
        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("mendeley://library/folders")
async def get_all_folders() -> str:
    """Get all folders in the library."""
    client = await get_client()
    try:
        folders = await client.get_folders()
        results = [
            {"id": f.id, "name": f.name, "parent_id": f.parent_id}
            for f in folders
        ]
        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def main() -> None:
    """Run the MCP server."""
    # Validate credentials on startup
    try:
        get_credentials()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Run the server with stdio transport (default for MCP)
    mcp.run()


if __name__ == "__main__":
    main()
