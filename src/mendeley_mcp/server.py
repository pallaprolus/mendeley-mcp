"""
Mendeley MCP Server - Expose Mendeley library to LLM applications.

This server provides tools for searching, retrieving, and managing
documents in your Mendeley reference library.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import (
    BlobResourceContents,
    CallToolResult,
    ContentBlock,
    EmbeddedResource,
    TextContent,
)
from pydantic import AnyUrl

from .auth import load_credentials
from .client import Document, Folder, MendeleyClient, MendeleyCredentials

# Initialize the MCP server
mcp = FastMCP("mendeley")

# Embedded files are base64-encoded into the tool result and therefore into the
# client's context window, so oversized files are reported but not embedded.
MAX_EMBEDDED_FILE_BYTES = int(
    os.environ.get("MENDELEY_MCP_MAX_FILE_BYTES", str(10 * 1024 * 1024))
)

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
        "abstract": (
            doc.abstract[:500] + "..."
            if doc.abstract and len(doc.abstract) > 500
            else doc.abstract
        ),
        "identifiers": doc.identifiers,
        "has_pdf": doc.file_attached,
        "citation": doc.format_citation(),
    }


def _json_response(payload: Any) -> str:
    """Serialize a tool response using the repository's JSON-string convention."""
    return json.dumps(payload, indent=2)


def _json_error_response(message: str) -> str:
    """Serialize an MCP error payload."""
    return _json_response({"error": message})


def _trimmed_input(value: str, field_label: str) -> str:
    """Trim and validate a required string input."""
    trimmed = value.strip()
    if not trimmed:
        raise ValueError(f"{field_label} must not be blank.")
    return trimmed


def _trimmed_optional_input(value: str | None) -> str | None:
    """Trim an optional string input without adding new business rules."""
    if value is None:
        return None
    return value.strip()


def _format_error_message(exc: Exception) -> str:
    """Return a stable, user-facing error message."""
    if isinstance(exc, httpx.HTTPStatusError):
        response_text = exc.response.text.strip()
        status_code = exc.response.status_code
        if response_text:
            return f"Upstream Mendeley API error ({status_code}): {response_text}"
        return f"Upstream Mendeley API error ({status_code})."

    message = str(exc).strip()
    return message or exc.__class__.__name__


def _folder_payload(folder: Folder) -> dict[str, Any]:
    """Build the stable MCP folder payload from a client Folder."""
    return {
        "id": folder.id,
        "name": folder.name,
        "parent_id": folder.parent_id,
        "created": folder.created,
    }


def build_tool_result(
    message: str,
    structured_content: dict[str, Any] | None = None,
    *,
    is_error: bool = False,
    embedded_resource: EmbeddedResource | None = None,
) -> CallToolResult:
    """Create a consistent CallToolResult payload."""
    content: list[ContentBlock] = [
        TextContent(type="text", text=message),
    ]
    if embedded_resource is not None:
        content.append(embedded_resource)

    return CallToolResult(
        content=content,
        structuredContent=structured_content,
        isError=is_error,
    )


def sanitize_filename(name: str, default_stem: str) -> str:
    """Create a safe PDF filename for embedded resource metadata."""
    cleaned = re.sub(r"[^\w.-]+", "_", name).strip("._")
    if not cleaned:
        cleaned = default_stem
    if not cleaned.lower().endswith(".pdf"):
        cleaned = f"{cleaned}.pdf"
    return cleaned


async def get_document_metadata(
    client: MendeleyClient,
    document_id: str,
) -> dict[str, Any]:
    """Resolve document metadata from the library first, then the catalog."""
    try:
        doc = await client.get_document(document_id)
        return {
            "document_id": doc.id,
            "title": doc.title,
            "year": doc.year,
            "source": doc.source,
            "identifiers": doc.identifiers,
            "lookup_source": "library",
        }
    except Exception:
        pass

    try:
        catalog_doc = await client.get_catalog_document(catalog_id=document_id)
        if catalog_doc:
            return {
                "document_id": catalog_doc.get("id", document_id),
                "title": catalog_doc.get("title"),
                "year": catalog_doc.get("year"),
                "source": catalog_doc.get("source"),
                "identifiers": catalog_doc.get("identifiers"),
                "lookup_source": "catalog",
            }
    except Exception:
        pass

    return {
        "document_id": document_id,
        "title": None,
        "year": None,
        "source": None,
        "identifiers": None,
        "lookup_source": "unknown",
    }


@mcp.tool(
    title="Search Library",
    description=(
        "Search the authenticated Mendeley library by title, authors, abstract, "
        "or notes and return concise document metadata, citation text, and PDF availability."
    ),
)
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


@mcp.tool(
    title="Get Document",
    description=(
        "Fetch full metadata for one library document, including identifiers, abstract, "
        "keywords, tags, timestamps, and whether a file is attached."
    ),
)
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


@mcp.tool(
    title="List Documents",
    description=(
        "List documents from the library, optionally filtered by folder and ordered by "
        "last modification, creation date, or title."
    ),
)
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


@mcp.tool(
    title="List Folders",
    description=(
        "Return the folder and collection structure of the authenticated Mendeley library, "
        "including parent-child relationships."
    ),
)
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


@mcp.tool(
    title="Create Folder",
    description=(
        "Create a new folder in the personal library, nested under a parent folder, "
        "or in a group context."
    ),
)
async def mendeley_create_folder(
    name: str,
    parent_id: str | None = None,
    group_id: str | None = None,
) -> str:
    """
    Create a new folder in the personal library or in a group context.

    Args:
        name: Folder name
        parent_id: Optional parent folder ID for nested folder creation
        group_id: Optional group ID for group-scoped folder creation

    Returns:
        JSON object with the created folder payload
    """
    try:
        trimmed_name = _trimmed_input(name, "name")
        client = await get_client()
        folder = await client.create_folder(
            name=trimmed_name,
            parent_id=_trimmed_optional_input(parent_id),
            group_id=_trimmed_optional_input(group_id),
        )
        return _json_response(_folder_payload(folder))
    except Exception as e:
        return _json_error_response(_format_error_message(e))


@mcp.tool(
    title="Rename Folder",
    description="Rename an existing folder and return its updated state.",
)
async def mendeley_rename_folder(
    folder_id: str,
    name: str,
) -> str:
    """
    Rename an existing folder.

    Args:
        folder_id: The folder ID to rename
        name: The new folder name

    Returns:
        JSON object with the renamed folder payload
    """
    try:
        trimmed_folder_id = _trimmed_input(folder_id, "folder_id")
        trimmed_name = _trimmed_input(name, "name")
        client = await get_client()
        folder = await client.rename_folder(
            folder_id=trimmed_folder_id,
            name=trimmed_name,
        )
        return _json_response(_folder_payload(folder))
    except Exception as e:
        return _json_error_response(_format_error_message(e))


@mcp.tool(
    title="Delete Folder",
    description="Delete an existing folder and return a deletion confirmation.",
)
async def mendeley_delete_folder(
    folder_id: str,
) -> str:
    """
    Delete an existing folder.

    Args:
        folder_id: The folder ID to delete

    Returns:
        JSON object confirming the folder deletion
    """
    try:
        trimmed_folder_id = _trimmed_input(folder_id, "folder_id")
        client = await get_client()
        result = await client.delete_folder(folder_id=trimmed_folder_id)
        return _json_response(result)
    except Exception as e:
        return _json_error_response(_format_error_message(e))


@mcp.tool(
    title="Add Document To Folder",
    description="Add an existing library document to an existing folder.",
)
async def mendeley_add_document_to_folder(
    folder_id: str,
    document_id: str,
) -> str:
    """
    Add an existing document to an existing folder.

    Args:
        folder_id: The target folder ID
        document_id: The document ID to add to the folder

    Returns:
        JSON object confirming the folder assignment
    """
    try:
        trimmed_folder_id = _trimmed_input(folder_id, "folder_id")
        trimmed_document_id = _trimmed_input(document_id, "document_id")
        client = await get_client()
        await client.add_document_to_folder(
            folder_id=trimmed_folder_id,
            document_id=trimmed_document_id,
        )
        return _json_response(
            {
                "folder_id": trimmed_folder_id,
                "document_id": trimmed_document_id,
                "status": "added",
            }
        )
    except Exception as e:
        return _json_error_response(_format_error_message(e))


@mcp.tool(
    title="Search Catalog",
    description=(
        "Search Mendeley's global catalog for papers that may not yet exist in the user's "
        "library and return catalog identifiers plus summary metadata."
    ),
)
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
                "abstract": (
                    item.get("abstract", "")[:300] + "..."
                    if item.get("abstract")
                    else None
                ),
            })
        return json.dumps(formatted, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    title="Get By DOI",
    description=(
        "Resolve a DOI against the Mendeley catalog and return the best matching paper "
        "metadata, including catalog_id for downstream actions."
    ),
)
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


@mcp.tool(
    title="Add Document",
    description=(
        "Create a new library entry from supplied bibliographic metadata such as title, "
        "authors, year, source, abstract, and identifiers."
    ),
)
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


@mcp.tool(
    title="Remove Document From Folder",
    description=(
        "Remove a document from a folder without deleting the document from the library."
    ),
)
async def mendeley_remove_document_from_folder(
    folder_id: str,
    document_id: str,
) -> str:
    """
    Remove a document from a folder. The document stays in the library.

    Args:
        folder_id: The folder ID to remove the document from
        document_id: The document ID to remove

    Returns:
        JSON object confirming the removal
    """
    try:
        trimmed_folder_id = _trimmed_input(folder_id, "folder_id")
        trimmed_document_id = _trimmed_input(document_id, "document_id")
        client = await get_client()
        result = await client.remove_document_from_folder(
            folder_id=trimmed_folder_id,
            document_id=trimmed_document_id,
        )
        return _json_response(result)
    except Exception as e:
        return _json_error_response(_format_error_message(e))


@mcp.tool(
    title="Update Document",
    description=(
        "Update bibliographic fields on an existing library document, such as title, "
        "authors, year, source, abstract, or identifiers. Only supplied fields change."
    ),
)
async def mendeley_update_document(
    document_id: str,
    title: str | None = None,
    doc_type: str | None = None,
    authors: list[dict[str, str]] | None = None,
    year: int | None = None,
    source: str | None = None,
    abstract: str | None = None,
    identifiers: dict[str, str] | None = None,
) -> str:
    """
    Update fields on an existing document in your library.

    Args:
        document_id: The document ID to update
        title: New document title
        doc_type: New type - 'journal', 'book', 'conference_proceedings', etc.
        authors: List of author dicts with 'first_name' and 'last_name'
        year: Publication year
        source: Journal/book name
        abstract: Document abstract
        identifiers: Dict with 'doi', 'pmid', 'isbn', etc.

    Returns:
        JSON object with the updated document
    """
    try:
        trimmed_document_id = _trimmed_input(document_id, "document_id")
        updates: dict[str, Any] = {}
        if title is not None:
            updates["title"] = title
        if doc_type is not None:
            updates["type"] = doc_type
        if authors is not None:
            updates["authors"] = authors
        if year is not None:
            updates["year"] = year
        if source is not None:
            updates["source"] = source
        if abstract is not None:
            updates["abstract"] = abstract
        if identifiers is not None:
            updates["identifiers"] = identifiers
        if not updates:
            raise ValueError("At least one field to update must be provided.")

        client = await get_client()
        doc = await client.update_document(
            document_id=trimmed_document_id,
            updates=updates,
        )
        return _json_response(format_document(doc))
    except Exception as e:
        return _json_error_response(_format_error_message(e))


@mcp.tool(
    title="Delete Document",
    description=(
        "Permanently delete a document from the library. This is destructive and cannot "
        "be undone through the API — confirm with the user before calling this tool."
    ),
)
async def mendeley_delete_document(
    document_id: str,
) -> str:
    """
    Permanently delete a document from your library.

    This cannot be undone through the API. Confirm with the user before deleting.

    Args:
        document_id: The document ID to delete

    Returns:
        JSON object confirming the deletion
    """
    try:
        trimmed_document_id = _trimmed_input(document_id, "document_id")
        client = await get_client()
        result = await client.delete_document(document_id=trimmed_document_id)
        return _json_response(result)
    except Exception as e:
        return _json_error_response(_format_error_message(e))


def _format_annotation(annotation: dict[str, Any]) -> dict[str, Any]:
    """Format an annotation payload, keeping the fields useful to a reader."""
    positions = annotation.get("positions")
    pages: list[int] = []
    if isinstance(positions, list):
        for position in positions:
            if isinstance(position, dict) and isinstance(position.get("page"), int):
                pages.append(position["page"])
    return {
        "id": annotation.get("id"),
        "type": annotation.get("type"),
        "text": annotation.get("text"),
        "color": annotation.get("color"),
        "pages": sorted(set(pages)),
        "created": annotation.get("created"),
        "last_modified": annotation.get("last_modified"),
    }


@mcp.tool(
    title="Get Annotations",
    description=(
        "Get the user's own annotations on a library document — PDF highlights and "
        "sticky notes — including note text and the pages they appear on. Useful for "
        "surfacing what the user marked as important in a paper."
    ),
)
async def mendeley_get_annotations(
    document_id: str,
    limit: int = 50,
) -> str:
    """
    Get your annotations (highlights and notes) on a document.

    Args:
        document_id: The library document ID
        limit: Maximum number of annotations to return (default 50)

    Returns:
        JSON array of annotations with type, text, color, and page numbers
    """
    try:
        trimmed_document_id = _trimmed_input(document_id, "document_id")
        client = await get_client()
        annotations = await client.get_annotations(
            document_id=trimmed_document_id,
            limit=limit,
        )
        formatted = [
            _format_annotation(a) for a in annotations if isinstance(a, dict)
        ]
        return _json_response(formatted)
    except Exception as e:
        return _json_error_response(_format_error_message(e))


@mcp.tool(
    title="Export BibTeX",
    description=(
        "Export one document or all documents in a folder as BibTeX, generated by "
        "Mendeley. Provide exactly one of document_id or folder_id. Returns raw BibTeX "
        "text ready to paste into a .bib file."
    ),
)
async def mendeley_export_bibtex(
    document_id: str | None = None,
    folder_id: str | None = None,
    limit: int = 50,
) -> str:
    """
    Export library documents as BibTeX.

    Args:
        document_id: Export a single document by ID
        folder_id: Export all documents in a folder by folder ID
        limit: Maximum number of entries when exporting a folder (default 50)

    Returns:
        Raw BibTeX text, or a JSON error object on failure
    """
    try:
        trimmed_document_id = _trimmed_optional_input(document_id) or None
        trimmed_folder_id = _trimmed_optional_input(folder_id) or None
        if trimmed_document_id and trimmed_folder_id:
            raise ValueError("Provide either document_id or folder_id, not both.")
        if not trimmed_document_id and not trimmed_folder_id:
            raise ValueError("Either document_id or folder_id must be provided.")

        client = await get_client()
        return await client.export_bibtex(
            document_id=trimmed_document_id,
            folder_id=trimmed_folder_id,
            limit=limit,
        )
    except Exception as e:
        return _json_error_response(_format_error_message(e))


@mcp.tool(
    title="Get File Content",
    description=(
        "Try to download the first file attached to a library document or catalog entry. "
        "Returns structured metadata and an embedded PDF resource when Mendeley exposes one."
    ),
)
async def mendeley_get_file_content(
    document_id: str,
) -> CallToolResult:
    """
    Download the first file attached to a Mendeley document.

    This accepts either a library document ID or a catalog ID. Catalog entries
    often do not have attached files, so an empty result is common there.

    Args:
        document_id: Mendeley document ID or catalog ID

    Returns:
        MCP tool result with metadata plus an embedded binary resource when a file exists
    """
    try:
        client = await get_client()
    except Exception as e:
        return build_tool_result(_format_error_message(e), is_error=True)

    metadata = await get_document_metadata(client, document_id)

    try:
        file_content = await client.get_file_content(document_id)
    except Exception as e:
        structured_content = {
            **metadata,
            "file_available": False,
            "mime_type": None,
            "size_bytes": None,
        }
        return build_tool_result(
            f"Failed to download file content for document {document_id}: {e}",
            structured_content,
            is_error=True,
        )

    if file_content is None:
        structured_content = {
            **metadata,
            "file_available": False,
            "mime_type": None,
            "size_bytes": 0,
        }
        return build_tool_result(
            (
                f"No attached file is available for document {document_id}. "
                "Catalog entries frequently do not expose downloadable files."
            ),
            structured_content,
        )

    if len(file_content) > MAX_EMBEDDED_FILE_BYTES:
        structured_content = {
            **metadata,
            "file_available": True,
            "mime_type": "application/pdf",
            "size_bytes": len(file_content),
        }
        return build_tool_result(
            (
                f"Attached file for document {document_id} is "
                f"{len(file_content)} bytes, which exceeds the embed limit of "
                f"{MAX_EMBEDDED_FILE_BYTES} bytes. Set the "
                "MENDELEY_MCP_MAX_FILE_BYTES environment variable to adjust it."
            ),
            structured_content,
        )

    title = metadata.get("title") or document_id
    filename = sanitize_filename(title, default_stem=document_id)
    uri = f"mendeley://documents/{document_id}/file/{filename}"
    embedded_resource = EmbeddedResource(
        type="resource",
        resource=BlobResourceContents(
            uri=AnyUrl(uri),
            mimeType="application/pdf",
            blob=base64.b64encode(file_content).decode("ascii"),
        ),
    )
    structured_content = {
        **metadata,
        "file_available": True,
        "mime_type": "application/pdf",
        "size_bytes": len(file_content),
        "filename": filename,
    }
    return build_tool_result(
        f"Downloaded attached file for document {document_id}.",
        structured_content,
        embedded_resource=embedded_resource,
    )


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
