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
from mcp.types import BlobResourceContents, CallToolResult, EmbeddedResource, TextContent

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
    lower_message = message.lower()
    duplicate_markers = (
        "duplicate",
        "already in folder",
        "already in the folder",
        "already associated",
        "already present",
    )
    if any(marker in lower_message for marker in duplicate_markers):
        if "folder" in lower_message:
            return message
        return "Document is already in folder."

    return message or exc.__class__.__name__


def _get_client_method(client: MendeleyClient, method_name: str) -> Any:
    """Resolve a client method while tolerating staggered multi-worker changes."""
    method = getattr(client, method_name, None)
    if not callable(method):
        raise RuntimeError(f"Mendeley client does not support '{method_name}' yet.")
    return method


def _read_result_field(result: Any, field_name: str) -> Any:
    """Read a field from either a dataclass-like object or a mapping result."""
    if isinstance(result, dict):
        return result.get(field_name)
    return getattr(result, field_name, None)


def _format_folder_payload(result: Any, fallback_name: str) -> dict[str, Any]:
    """Build the stable MCP folder payload from a client result."""
    folder_id = _read_result_field(result, "id")
    if not isinstance(folder_id, str) or not folder_id:
        raise ValueError("Folder operation did not return a folder id.")

    name = _read_result_field(result, "name")
    folder_name = name if isinstance(name, str) and name else fallback_name

    return {
        "id": folder_id,
        "name": folder_name,
        "parent_id": _read_result_field(result, "parent_id"),
        "created": _read_result_field(result, "created"),
    }


def _format_folder_delete_payload(result: Any, fallback_id: str) -> dict[str, str]:
    """Build the stable MCP folder-delete payload from a client result."""
    folder_id = _read_result_field(result, "id")
    deleted_folder_id = folder_id if isinstance(folder_id, str) and folder_id else fallback_id

    status = _read_result_field(result, "status")
    deleted_status = status if isinstance(status, str) and status else "deleted"

    return {
        "id": deleted_folder_id,
        "status": deleted_status,
    }


def build_tool_result(
    message: str,
    structured_content: dict[str, Any] | None = None,
    *,
    is_error: bool = False,
    embedded_resource: EmbeddedResource | None = None,
) -> CallToolResult:
    """Create a consistent CallToolResult payload."""
    content: list[TextContent | EmbeddedResource] = [
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
        doc = await client.get_catalog_document(catalog_id=document_id)
        if doc:
            return {
                "document_id": doc.get("id", document_id),
                "title": doc.get("title"),
                "year": doc.get("year"),
                "source": doc.get("source"),
                "identifiers": doc.get("identifiers"),
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
        create_folder = _get_client_method(client, "create_folder")
        result = await create_folder(
            name=trimmed_name,
            parent_id=_trimmed_optional_input(parent_id),
            group_id=_trimmed_optional_input(group_id),
        )
        return _json_response(_format_folder_payload(result, fallback_name=trimmed_name))
    except Exception as e:
        return _json_error_response(_format_error_message(e))


@mcp.tool()
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
        rename_folder = _get_client_method(client, "rename_folder")
        result = await rename_folder(
            folder_id=trimmed_folder_id,
            name=trimmed_name,
        )
        return _json_response(_format_folder_payload(result, fallback_name=trimmed_name))
    except Exception as e:
        return _json_error_response(_format_error_message(e))


@mcp.tool()
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
        delete_folder = _get_client_method(client, "delete_folder")
        result = await delete_folder(folder_id=trimmed_folder_id)
        return _json_response(
            _format_folder_delete_payload(result, fallback_id=trimmed_folder_id)
        )
    except Exception as e:
        return _json_error_response(_format_error_message(e))


@mcp.tool()
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
        add_document_to_folder = _get_client_method(client, "add_document_to_folder")
        await add_document_to_folder(
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
                "abstract": (
                    item.get("abstract", "")[:300] + "..."
                    if item.get("abstract")
                    else None
                ),
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


@mcp.tool()
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
    client = await get_client()
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

    title = metadata.get("title") or document_id
    filename = sanitize_filename(title, default_stem=document_id)
    uri = f"mendeley://documents/{document_id}/file/{filename}"
    embedded_resource = EmbeddedResource(
        type="resource",
        resource=BlobResourceContents(
            uri=uri,
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
