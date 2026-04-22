"""Tests for MCP tool wrappers in the server module."""

from __future__ import annotations

import asyncio
import base64
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import mendeley_mcp.server as server
from mendeley_mcp.client import Document, Folder

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    """Run async tool tests only on asyncio to match the project runtime."""
    return "asyncio"


@pytest.fixture
def patched_server_client(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[SimpleNamespace, AsyncMock]:
    """Patch get_client() so tool tests stay focused on server behavior."""
    client = SimpleNamespace(
        create_folder=AsyncMock(name="create_folder"),
        rename_folder=AsyncMock(name="rename_folder"),
        delete_folder=AsyncMock(name="delete_folder"),
        add_document_to_folder=AsyncMock(name="add_document_to_folder"),
    )
    get_client = AsyncMock(return_value=client, name="get_client")
    monkeypatch.setattr(server, "get_client", get_client)
    return client, get_client


def _decode_tool_result(result: str) -> dict[str, object]:
    """Decode the JSON string returned by a tool coroutine."""
    payload = json.loads(result)
    assert isinstance(payload, dict)
    return payload


@pytest.mark.parametrize(
    ("parent_id", "group_id", "folder"),
    [
        (
            None,
            None,
            Folder(
                id="folder-root",
                name="Systematic Review 2026",
                parent_id=None,
                created="2024-07-02T13:27:52.000Z",
            ),
        ),
        (
            "parent-123",
            None,
            Folder(
                id="folder-child",
                name="Nested Notes",
                parent_id="parent-123",
                created="2024-07-02T13:27:52.000Z",
            ),
        ),
        (
            None,
            "group-456",
            Folder(
                id="folder-group",
                name="Group Reading List",
                parent_id=None,
                created="2024-07-02T13:27:52.000Z",
            ),
        ),
    ],
    ids=["root", "nested", "group"],
)
async def test_mendeley_create_folder_returns_stable_payload(
    patched_server_client: tuple[SimpleNamespace, AsyncMock],
    parent_id: str | None,
    group_id: str | None,
    folder: Folder,
) -> None:
    """The folder tool should return only the stable public contract fields."""
    client, get_client = patched_server_client
    client.create_folder.return_value = folder

    result = await server.mendeley_create_folder(
        name=f"  {folder.name}  ",
        parent_id=parent_id,
        group_id=group_id,
    )

    assert _decode_tool_result(result) == {
        "id": folder.id,
        "name": folder.name,
        "parent_id": folder.parent_id,
        "created": folder.created,
    }
    get_client.assert_awaited_once()
    client.create_folder.assert_awaited_once_with(
        name=folder.name,
        parent_id=parent_id,
        group_id=group_id,
    )


async def test_mendeley_add_document_to_folder_returns_confirmation_payload(
    patched_server_client: tuple[SimpleNamespace, AsyncMock],
) -> None:
    """The assignment tool should return the deterministic confirmation payload."""
    client, get_client = patched_server_client
    client.add_document_to_folder.return_value = {
        "folder_id": "folder-123",
        "document_id": "document-456",
        "status": "added",
    }

    result = await server.mendeley_add_document_to_folder(
        folder_id="  folder-123  ",
        document_id="  document-456  ",
    )

    assert _decode_tool_result(result) == {
        "folder_id": "folder-123",
        "document_id": "document-456",
        "status": "added",
    }
    get_client.assert_awaited_once()
    client.add_document_to_folder.assert_awaited_once_with(
        folder_id="folder-123",
        document_id="document-456",
    )


async def test_mendeley_rename_folder_returns_stable_payload(
    patched_server_client: tuple[SimpleNamespace, AsyncMock],
) -> None:
    """The rename tool should expose only the stable folder contract fields."""
    client, get_client = patched_server_client
    client.rename_folder.return_value = Folder(
        id="folder-123",
        name="Renamed Folder",
        parent_id="parent-456",
        created="2024-07-02T13:27:52.000Z",
    )

    result = await server.mendeley_rename_folder(
        folder_id="  folder-123  ",
        name="  Renamed Folder  ",
    )

    assert _decode_tool_result(result) == {
        "id": "folder-123",
        "name": "Renamed Folder",
        "parent_id": "parent-456",
        "created": "2024-07-02T13:27:52.000Z",
    }
    get_client.assert_awaited_once()
    client.rename_folder.assert_awaited_once_with(
        folder_id="folder-123",
        name="Renamed Folder",
    )


async def test_mendeley_delete_folder_returns_confirmation_payload(
    patched_server_client: tuple[SimpleNamespace, AsyncMock],
) -> None:
    """The delete tool should return the deterministic deletion contract."""
    client, get_client = patched_server_client
    client.delete_folder.return_value = {
        "id": "folder-123",
        "status": "deleted",
    }

    result = await server.mendeley_delete_folder(folder_id="  folder-123  ")

    assert _decode_tool_result(result) == {
        "id": "folder-123",
        "status": "deleted",
    }
    get_client.assert_awaited_once()
    client.delete_folder.assert_awaited_once_with(folder_id="folder-123")


@pytest.mark.parametrize("name", ["", "   ", "\n\t"])
async def test_mendeley_create_folder_rejects_blank_names(
    patched_server_client: tuple[SimpleNamespace, AsyncMock],
    name: str,
) -> None:
    """Blank folder names should be rejected before the client is requested."""
    client, get_client = patched_server_client

    result = await server.mendeley_create_folder(name=name)

    payload = _decode_tool_result(result)
    assert "error" in payload
    assert "name" in str(payload["error"]).lower()
    get_client.assert_not_awaited()
    client.create_folder.assert_not_awaited()


@pytest.mark.parametrize(
    ("folder_id", "name", "expected_field"),
    [
        ("", "Renamed Folder", "folder_id"),
        ("   ", "Renamed Folder", "folder_id"),
        ("folder-123", "", "name"),
        ("folder-123", "   ", "name"),
        ("folder-123", "\n\t", "name"),
    ],
    ids=[
        "blank-folder-id",
        "whitespace-folder-id",
        "blank-name",
        "whitespace-name",
        "control-char-name",
    ],
)
async def test_mendeley_rename_folder_rejects_blank_inputs(
    patched_server_client: tuple[SimpleNamespace, AsyncMock],
    folder_id: str,
    name: str,
    expected_field: str,
) -> None:
    """Blank rename inputs should fail local validation before client use."""
    client, get_client = patched_server_client

    result = await server.mendeley_rename_folder(folder_id=folder_id, name=name)

    payload = _decode_tool_result(result)
    assert "error" in payload
    assert expected_field in str(payload["error"]).lower()
    get_client.assert_not_awaited()
    client.rename_folder.assert_not_awaited()


@pytest.mark.parametrize("folder_id", ["", "   ", "\n\t"])
async def test_mendeley_delete_folder_rejects_blank_folder_ids(
    patched_server_client: tuple[SimpleNamespace, AsyncMock],
    folder_id: str,
) -> None:
    """Blank delete IDs should fail local validation before client use."""
    client, get_client = patched_server_client

    result = await server.mendeley_delete_folder(folder_id=folder_id)

    payload = _decode_tool_result(result)
    assert "error" in payload
    assert "folder_id" in str(payload["error"]).lower()
    get_client.assert_not_awaited()
    client.delete_folder.assert_not_awaited()


@pytest.mark.parametrize(
    ("folder_id", "document_id", "expected_field"),
    [
        ("", "document-456", "folder_id"),
        ("   ", "document-456", "folder_id"),
        ("folder-123", "", "document_id"),
        ("folder-123", "   ", "document_id"),
    ],
    ids=[
        "blank-folder-id",
        "whitespace-folder-id",
        "blank-document-id",
        "whitespace-document-id",
    ],
)
async def test_mendeley_add_document_to_folder_rejects_blank_ids(
    patched_server_client: tuple[SimpleNamespace, AsyncMock],
    folder_id: str,
    document_id: str,
    expected_field: str,
) -> None:
    """Blank folder/document IDs should fail local validation before client use."""
    client, get_client = patched_server_client

    result = await server.mendeley_add_document_to_folder(
        folder_id=folder_id,
        document_id=document_id,
    )

    payload = _decode_tool_result(result)
    assert "error" in payload
    assert expected_field in str(payload["error"]).lower()
    get_client.assert_not_awaited()
    client.add_document_to_folder.assert_not_awaited()


async def test_mendeley_add_document_to_folder_surfaces_duplicate_error(
    patched_server_client: tuple[SimpleNamespace, AsyncMock],
) -> None:
    """Duplicate assignment should be exposed as a clear tool-level error."""
    client, get_client = patched_server_client
    client.add_document_to_folder.side_effect = ValueError("Document already in folder")

    result = await server.mendeley_add_document_to_folder(
        folder_id="folder-123",
        document_id="document-456",
    )

    payload = _decode_tool_result(result)
    assert "error" in payload
    assert "already" in str(payload["error"]).lower()
    assert "folder" in str(payload["error"]).lower()
    get_client.assert_awaited_once()
    client.add_document_to_folder.assert_awaited_once_with(
        folder_id="folder-123",
        document_id="document-456",
    )


@pytest.mark.parametrize(
    ("tool_name", "client_method", "kwargs", "message", "expected_call"),
    [
        (
            "mendeley_rename_folder",
            "rename_folder",
            {"folder_id": "folder-123", "name": "Renamed Folder"},
            "upstream rename failure",
            {"folder_id": "folder-123", "name": "Renamed Folder"},
        ),
        (
            "mendeley_delete_folder",
            "delete_folder",
            {"folder_id": "folder-123"},
            "upstream delete failure",
            {"folder_id": "folder-123"},
        ),
    ],
    ids=["rename-folder", "delete-folder"],
)
async def test_folder_rename_delete_tools_propagate_upstream_errors(
    patched_server_client: tuple[SimpleNamespace, AsyncMock],
    tool_name: str,
    client_method: str,
    kwargs: dict[str, str],
    message: str,
    expected_call: dict[str, str],
) -> None:
    """Rename/delete tool errors should be serialized without false success payloads."""
    client, get_client = patched_server_client
    getattr(client, client_method).side_effect = RuntimeError(message)
    tool = getattr(server, tool_name)

    result = await tool(**kwargs)

    assert _decode_tool_result(result) == {"error": message}
    get_client.assert_awaited_once()
    getattr(client, client_method).assert_awaited_once_with(**expected_call)


@pytest.mark.parametrize(
    ("tool_name", "client_method", "kwargs", "message", "expected_call"),
    [
        (
            "mendeley_create_folder",
            "create_folder",
            {"name": "Systematic Review 2026"},
            "upstream create failure",
            {
                "name": "Systematic Review 2026",
                "parent_id": None,
                "group_id": None,
            },
        ),
        (
            "mendeley_add_document_to_folder",
            "add_document_to_folder",
            {"folder_id": "folder-123", "document_id": "document-456"},
            "upstream assignment failure",
            {"folder_id": "folder-123", "document_id": "document-456"},
        ),
    ],
    ids=["create-folder", "add-document-to-folder"],
)
async def test_folder_management_tools_propagate_upstream_errors(
    patched_server_client: tuple[SimpleNamespace, AsyncMock],
    tool_name: str,
    client_method: str,
    kwargs: dict[str, str],
    message: str,
    expected_call: dict[str, str | None],
) -> None:
    """Unexpected client errors should be serialized without false success payloads."""
    client, get_client = patched_server_client
    getattr(client, client_method).side_effect = RuntimeError(message)
    tool = getattr(server, tool_name)

    result = await tool(**kwargs)

    assert _decode_tool_result(result) == {"error": message}
    get_client.assert_awaited_once()
    getattr(client, client_method).assert_awaited_once_with(**expected_call)


class CatalogDownloadClient:
    """Fake client for catalog file download tests."""

    async def get_document(self, document_id: str) -> Document:
        raise RuntimeError("not found in library")

    async def get_catalog_document(
        self,
        catalog_id: str | None = None,
        doi: str | None = None,
    ) -> dict[str, object]:
        assert catalog_id == "catalog-123"
        assert doi is None
        return {
            "id": "catalog-123",
            "title": "Catalog Paper",
            "year": 2024,
            "source": "Journal of Testing",
            "identifiers": {"doi": "10.1234/catalog"},
        }

    async def get_file_content(self, document_id: str) -> bytes:
        assert document_id == "catalog-123"
        return b"%PDF-1.7\ncatalog pdf"


class MissingFileClient:
    """Fake client for missing file tests."""

    async def get_document(self, document_id: str) -> Document:
        return Document(
            id=document_id,
            title="Library Paper",
            type="journal",
            authors=[],
            year=2023,
            source="Testing Quarterly",
            identifiers={"doi": "10.1234/library"},
            file_attached=False,
        )

    async def get_catalog_document(
        self,
        catalog_id: str | None = None,
        doi: str | None = None,
    ) -> dict[str, object]:
        raise AssertionError("catalog lookup should not be used when library metadata exists")

    async def get_file_content(self, document_id: str) -> None:
        assert document_id == "doc-456"
        return None


def test_mendeley_get_file_content_returns_embedded_pdf(monkeypatch):
    """The tool should return an embedded PDF resource when content is available."""

    async def fake_get_client():
        return CatalogDownloadClient()

    monkeypatch.setattr(server, "get_client", fake_get_client)

    result = asyncio.run(server.mendeley_get_file_content("catalog-123"))

    assert result.isError is False
    assert result.structuredContent == {
        "document_id": "catalog-123",
        "title": "Catalog Paper",
        "year": 2024,
        "source": "Journal of Testing",
        "identifiers": {"doi": "10.1234/catalog"},
        "lookup_source": "catalog",
        "file_available": True,
        "mime_type": "application/pdf",
        "size_bytes": len(b"%PDF-1.7\ncatalog pdf"),
        "filename": "Catalog_Paper.pdf",
    }
    assert result.content[0].type == "text"
    assert result.content[1].type == "resource"
    assert result.content[1].resource.mimeType == "application/pdf"
    assert (
        str(result.content[1].resource.uri)
        == "mendeley://documents/catalog-123/file/Catalog_Paper.pdf"
    )
    assert base64.b64decode(result.content[1].resource.blob) == b"%PDF-1.7\ncatalog pdf"


def test_mendeley_get_file_content_reports_missing_file(monkeypatch):
    """The tool should report when no attached file is available."""

    async def fake_get_client():
        return MissingFileClient()

    monkeypatch.setattr(server, "get_client", fake_get_client)

    result = asyncio.run(server.mendeley_get_file_content("doc-456"))

    assert result.isError is False
    assert result.structuredContent == {
        "document_id": "doc-456",
        "title": "Library Paper",
        "year": 2023,
        "source": "Testing Quarterly",
        "identifiers": {"doi": "10.1234/library"},
        "lookup_source": "library",
        "file_available": False,
        "mime_type": None,
        "size_bytes": 0,
    }
    assert len(result.content) == 1
    assert "No attached file is available" in result.content[0].text
