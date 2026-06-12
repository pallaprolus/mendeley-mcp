"""Tests for the Mendeley API client."""

from unittest.mock import AsyncMock, Mock, call

import httpx
import pytest

from mendeley_mcp.client import Document, Folder, MendeleyCredentials

FOLDER_MEDIA_TYPE = "application/vnd.mendeley-folder.1+json"
DOCUMENT_MEDIA_TYPE = "application/vnd.mendeley-document.1+json"
ANNOTATION_MEDIA_TYPE = "application/vnd.mendeley-annotation.1+json"
BIBTEX_MEDIA_TYPE = "application/x-bibtex"


def make_json_response(payload):
    """Build a mock response object with a JSON payload."""
    response = Mock()
    response.json.return_value = payload
    return response


@pytest.fixture
def anyio_backend():
    """Run async client tests only on the asyncio backend."""
    return "asyncio"


class TestMendeleyCredentials:
    """Tests for MendeleyCredentials."""

    def test_create_credentials(self):
        """Test creating credentials."""
        creds = MendeleyCredentials(
            client_id="test-id",
            client_secret="test-secret",
            access_token="test-access",
            refresh_token="test-refresh",
        )
        assert creds.client_id == "test-id"
        assert creds.client_secret == "test-secret"
        assert creds.access_token == "test-access"
        assert creds.refresh_token == "test-refresh"

    def test_credentials_without_tokens(self):
        """Test credentials without optional tokens."""
        creds = MendeleyCredentials(
            client_id="test-id",
            client_secret="test-secret",
        )
        assert creds.access_token is None
        assert creds.refresh_token is None


class TestDocument:
    """Tests for Document model."""

    def test_from_api(self):
        """Test creating document from API response."""
        api_data = {
            "id": "doc-123",
            "title": "Test Paper",
            "type": "journal",
            "authors": [
                {"first_name": "John", "last_name": "Doe"},
                {"first_name": "Jane", "last_name": "Smith"},
            ],
            "year": 2024,
            "abstract": "This is a test abstract.",
            "source": "Nature",
            "identifiers": {"doi": "10.1234/test"},
        }
        doc = Document.from_api(api_data)

        assert doc.id == "doc-123"
        assert doc.title == "Test Paper"
        assert doc.type == "journal"
        assert len(doc.authors) == 2
        assert doc.year == 2024
        assert doc.abstract == "This is a test abstract."
        assert doc.source == "Nature"
        assert doc.identifiers == {"doi": "10.1234/test"}

    def test_from_api_minimal(self):
        """Test creating document with minimal data."""
        api_data = {
            "id": "doc-456",
        }
        doc = Document.from_api(api_data)

        assert doc.id == "doc-456"
        assert doc.title == "Untitled"
        assert doc.type == "unknown"
        assert doc.authors == []

    def test_format_citation(self):
        """Test citation formatting."""
        doc = Document(
            id="doc-123",
            title="A Great Paper",
            type="journal",
            authors=[
                {"first_name": "Albert", "last_name": "Einstein"},
            ],
            year=1905,
            source="Annalen der Physik",
        )
        citation = doc.format_citation()

        assert "Einstein, A." in citation
        assert "(1905)" in citation
        assert "A Great Paper" in citation
        assert "Annalen der Physik" in citation

    def test_format_citation_many_authors(self):
        """Test citation formatting with many authors."""
        doc = Document(
            id="doc-123",
            title="Collaborative Work",
            type="journal",
            authors=[
                {"first_name": "A", "last_name": "Author1"},
                {"first_name": "B", "last_name": "Author2"},
                {"first_name": "C", "last_name": "Author3"},
                {"first_name": "D", "last_name": "Author4"},
            ],
            year=2024,
        )
        citation = doc.format_citation()

        assert "et al." in citation
        assert "Author4" not in citation


class TestFolder:
    """Tests for Folder model."""

    def test_from_api(self):
        """Test creating folder from API response."""
        api_data = {
            "id": "folder-123",
            "name": "My Collection",
            "parent_id": "folder-parent",
            "created": "2024-01-01T00:00:00Z",
        }
        folder = Folder.from_api(api_data)

        assert folder.id == "folder-123"
        assert folder.name == "My Collection"
        assert folder.parent_id == "folder-parent"
        assert folder.created == "2024-01-01T00:00:00Z"

    def test_from_api_root_folder(self):
        """Test creating root folder without parent."""
        api_data = {
            "id": "folder-root",
            "name": "Root",
        }
        folder = Folder.from_api(api_data)

        assert folder.id == "folder-root"
        assert folder.parent_id is None


class TestMendeleyClientFolderManagement:
    """Tests for folder-management methods on the client."""

    @pytest.mark.anyio
    async def test_create_folder_root_success(
        self,
        mendeley_client,
        root_folder_create_request,
        sample_folder_data,
    ):
        """Test creating a root folder."""
        request_mock = AsyncMock(return_value=make_json_response(sample_folder_data))
        mendeley_client._request = request_mock

        folder = await mendeley_client.create_folder(**root_folder_create_request)

        assert folder == Folder.from_api(sample_folder_data)
        request_mock.assert_awaited_once_with(
            "POST",
            "/folders",
            accept=FOLDER_MEDIA_TYPE,
            json=root_folder_create_request,
            headers={"Content-Type": FOLDER_MEDIA_TYPE},
        )

    @pytest.mark.anyio
    async def test_create_folder_nested_success(
        self,
        mendeley_client,
        nested_folder_create_request,
        sample_nested_folder_data,
    ):
        """Test creating a nested folder under a parent."""
        request_mock = AsyncMock(return_value=make_json_response(sample_nested_folder_data))
        mendeley_client._request = request_mock

        folder = await mendeley_client.create_folder(**nested_folder_create_request)

        assert folder == Folder.from_api(sample_nested_folder_data)
        request_mock.assert_awaited_once_with(
            "POST",
            "/folders",
            accept=FOLDER_MEDIA_TYPE,
            json=nested_folder_create_request,
            headers={"Content-Type": FOLDER_MEDIA_TYPE},
        )

    @pytest.mark.anyio
    async def test_create_folder_group_success(
        self,
        mendeley_client,
        group_folder_create_request,
        sample_group_folder_data,
    ):
        """Test creating a folder in a shared group context."""
        request_mock = AsyncMock(return_value=make_json_response(sample_group_folder_data))
        mendeley_client._request = request_mock

        folder = await mendeley_client.create_folder(**group_folder_create_request)

        assert folder == Folder.from_api(sample_group_folder_data)
        request_mock.assert_awaited_once_with(
            "POST",
            "/folders",
            accept=FOLDER_MEDIA_TYPE,
            json=group_folder_create_request,
            headers={"Content-Type": FOLDER_MEDIA_TYPE},
        )

    @pytest.mark.anyio
    async def test_rename_folder_success(
        self,
        mendeley_client,
        folder_rename_request,
        renamed_folder_data,
    ):
        """Test renaming a folder returns the folder's post-rename state."""
        request_mock = AsyncMock(
            side_effect=[
                Mock(),
                make_json_response(renamed_folder_data),
            ]
        )
        mendeley_client._request = request_mock

        folder = await mendeley_client.rename_folder(**folder_rename_request)

        assert folder == Folder.from_api(renamed_folder_data)
        assert request_mock.await_args_list == [
            call(
                "PATCH",
                f"/folders/{folder_rename_request['folder_id']}",
                accept=FOLDER_MEDIA_TYPE,
                json={"name": folder_rename_request["name"]},
                headers={"Content-Type": FOLDER_MEDIA_TYPE},
            ),
            call(
                "GET",
                f"/folders/{folder_rename_request['folder_id']}",
                accept=FOLDER_MEDIA_TYPE,
            ),
        ]

    @pytest.mark.anyio
    async def test_delete_folder_success(
        self,
        mendeley_client,
        folder_delete_request,
        folder_delete_result,
    ):
        """Test deleting a folder with a no-payload upstream success response."""
        request_mock = AsyncMock(return_value=Mock())
        mendeley_client._request = request_mock

        result = await mendeley_client.delete_folder(**folder_delete_request)

        assert result == folder_delete_result
        request_mock.assert_awaited_once_with(
            "DELETE",
            f"/folders/{folder_delete_request['folder_id']}",
            accept=FOLDER_MEDIA_TYPE,
        )

    @pytest.mark.anyio
    async def test_add_document_to_folder_success(
        self,
        mendeley_client,
        folder_assignment_request,
        folder_assignment_result,
    ):
        """Test adding a document to a folder."""
        request_mock = AsyncMock(return_value=make_json_response({}))
        mendeley_client._request = request_mock

        result = await mendeley_client.add_document_to_folder(**folder_assignment_request)

        assert result == folder_assignment_result
        request_mock.assert_awaited_once_with(
            "POST",
            f"/folders/{folder_assignment_request['folder_id']}/documents",
            accept=DOCUMENT_MEDIA_TYPE,
            json={"id": folder_assignment_request["document_id"]},
            headers={"Content-Type": DOCUMENT_MEDIA_TYPE},
        )

    @pytest.mark.anyio
    async def test_create_folder_propagates_upstream_failure(
        self,
        mendeley_client,
        root_folder_create_request,
    ):
        """Test that upstream create-folder failures are not swallowed."""
        request = httpx.Request("POST", "https://api.mendeley.com/folders")
        response = httpx.Response(403, request=request)
        error = httpx.HTTPStatusError(
            "upstream rejected folder creation",
            request=request,
            response=response,
        )
        request_mock = AsyncMock(side_effect=error)
        mendeley_client._request = request_mock

        with pytest.raises(httpx.HTTPStatusError, match="upstream rejected folder creation"):
            await mendeley_client.create_folder(**root_folder_create_request)

        request_mock.assert_awaited_once_with(
            "POST",
            "/folders",
            accept=FOLDER_MEDIA_TYPE,
            json=root_folder_create_request,
            headers={"Content-Type": FOLDER_MEDIA_TYPE},
        )

    @pytest.mark.anyio
    async def test_rename_folder_propagates_upstream_failure(
        self,
        mendeley_client,
        folder_rename_request,
    ):
        """Test that upstream rename-folder failures are not swallowed."""
        request = httpx.Request(
            "PATCH",
            f"https://api.mendeley.com/folders/{folder_rename_request['folder_id']}",
        )
        response = httpx.Response(409, request=request)
        error = httpx.HTTPStatusError(
            "upstream rejected folder rename",
            request=request,
            response=response,
        )
        request_mock = AsyncMock(side_effect=error)
        mendeley_client._request = request_mock

        with pytest.raises(httpx.HTTPStatusError, match="upstream rejected folder rename"):
            await mendeley_client.rename_folder(**folder_rename_request)

        request_mock.assert_awaited_once_with(
            "PATCH",
            f"/folders/{folder_rename_request['folder_id']}",
            accept=FOLDER_MEDIA_TYPE,
            json={"name": folder_rename_request["name"]},
            headers={"Content-Type": FOLDER_MEDIA_TYPE},
        )

    @pytest.mark.anyio
    async def test_delete_folder_propagates_upstream_failure(
        self,
        mendeley_client,
        folder_delete_request,
    ):
        """Test that upstream delete-folder failures are not swallowed."""
        request = httpx.Request(
            "DELETE",
            f"https://api.mendeley.com/folders/{folder_delete_request['folder_id']}",
        )
        response = httpx.Response(500, request=request)
        error = httpx.HTTPStatusError(
            "upstream rejected folder deletion",
            request=request,
            response=response,
        )
        request_mock = AsyncMock(side_effect=error)
        mendeley_client._request = request_mock

        with pytest.raises(httpx.HTTPStatusError, match="upstream rejected folder deletion"):
            await mendeley_client.delete_folder(**folder_delete_request)

        request_mock.assert_awaited_once_with(
            "DELETE",
            f"/folders/{folder_delete_request['folder_id']}",
            accept=FOLDER_MEDIA_TYPE,
        )

    @pytest.mark.anyio
    async def test_add_document_to_folder_propagates_upstream_failure(
        self,
        mendeley_client,
        folder_assignment_request,
    ):
        """Test that upstream folder-assignment failures are not swallowed."""
        request = httpx.Request(
            "POST",
            f"https://api.mendeley.com/folders/{folder_assignment_request['folder_id']}/documents",
        )
        response = httpx.Response(409, request=request)
        error = httpx.HTTPStatusError(
            "upstream rejected folder assignment",
            request=request,
            response=response,
        )
        request_mock = AsyncMock(side_effect=error)
        mendeley_client._request = request_mock

        with pytest.raises(httpx.HTTPStatusError, match="upstream rejected folder assignment"):
            await mendeley_client.add_document_to_folder(**folder_assignment_request)

        request_mock.assert_awaited_once_with(
            "POST",
            f"/folders/{folder_assignment_request['folder_id']}/documents",
            accept=DOCUMENT_MEDIA_TYPE,
            json={"id": folder_assignment_request["document_id"]},
            headers={"Content-Type": DOCUMENT_MEDIA_TYPE},
        )


class TestMendeleyClientDocumentManagement:
    """Tests for document update/delete, annotations, and BibTeX export."""

    @pytest.mark.anyio
    async def test_update_document_patches_then_returns_server_state(
        self,
        mendeley_client,
        sample_document_data,
    ):
        """Test that update PATCHes the fields and returns the refetched document."""
        from mendeley_mcp.client import Document

        updated_data = {**sample_document_data, "title": "Corrected Title"}
        request_mock = AsyncMock(
            side_effect=[
                Mock(),
                make_json_response(updated_data),
            ]
        )
        mendeley_client._request = request_mock

        doc = await mendeley_client.update_document(
            document_id=sample_document_data["id"],
            updates={"title": "Corrected Title"},
        )

        assert doc == Document.from_api(updated_data)
        assert request_mock.await_args_list == [
            call(
                "PATCH",
                f"/documents/{sample_document_data['id']}",
                accept=DOCUMENT_MEDIA_TYPE,
                json={"title": "Corrected Title"},
                headers={"Content-Type": DOCUMENT_MEDIA_TYPE},
            ),
            call(
                "GET",
                f"/documents/{sample_document_data['id']}",
                accept=DOCUMENT_MEDIA_TYPE,
                params={"view": "all"},
            ),
        ]

    @pytest.mark.anyio
    async def test_delete_document_returns_confirmation(self, mendeley_client):
        """Test deleting a document returns a deterministic confirmation."""
        request_mock = AsyncMock(return_value=Mock())
        mendeley_client._request = request_mock

        result = await mendeley_client.delete_document("doc-123")

        assert result == {"id": "doc-123", "status": "deleted"}
        request_mock.assert_awaited_once_with(
            "DELETE",
            "/documents/doc-123",
            accept=DOCUMENT_MEDIA_TYPE,
        )

    @pytest.mark.anyio
    async def test_remove_document_from_folder_returns_confirmation(
        self,
        mendeley_client,
    ):
        """Test removing a document from a folder returns a confirmation."""
        request_mock = AsyncMock(return_value=Mock())
        mendeley_client._request = request_mock

        result = await mendeley_client.remove_document_from_folder(
            folder_id="folder-123",
            document_id="doc-456",
        )

        assert result == {
            "folder_id": "folder-123",
            "document_id": "doc-456",
            "status": "removed",
        }
        request_mock.assert_awaited_once_with(
            "DELETE",
            "/folders/folder-123/documents/doc-456",
            accept=DOCUMENT_MEDIA_TYPE,
        )

    @pytest.mark.anyio
    async def test_get_annotations_requests_annotation_media_type(
        self,
        mendeley_client,
    ):
        """Test annotations are fetched with the annotation media type."""
        annotations = [
            {"id": "ann-1", "type": "highlight", "positions": [{"page": 2}]},
        ]
        request_mock = AsyncMock(return_value=make_json_response(annotations))
        mendeley_client._request = request_mock

        result = await mendeley_client.get_annotations("doc-123", limit=10)

        assert result == annotations
        request_mock.assert_awaited_once_with(
            "GET",
            "/annotations",
            accept=ANNOTATION_MEDIA_TYPE,
            params={"document_id": "doc-123", "limit": 10},
        )

    @pytest.mark.anyio
    async def test_export_bibtex_for_single_document(self, mendeley_client):
        """Test single-document BibTeX export uses the bibtex accept header."""
        bibtex = "@article{key,\n  title = {A Paper}\n}\n"
        response = Mock()
        response.text = bibtex
        request_mock = AsyncMock(return_value=response)
        mendeley_client._request = request_mock

        result = await mendeley_client.export_bibtex(document_id="doc-123")

        assert result == bibtex
        request_mock.assert_awaited_once_with(
            "GET",
            "/documents/doc-123",
            accept=BIBTEX_MEDIA_TYPE,
        )

    @pytest.mark.anyio
    async def test_export_bibtex_for_folder(self, mendeley_client):
        """Test folder BibTeX export scopes the document listing to the folder."""
        bibtex = "@article{a,}\n@article{b,}\n"
        response = Mock()
        response.text = bibtex
        request_mock = AsyncMock(return_value=response)
        mendeley_client._request = request_mock

        result = await mendeley_client.export_bibtex(folder_id="folder-123", limit=25)

        assert result == bibtex
        request_mock.assert_awaited_once_with(
            "GET",
            "/documents",
            accept=BIBTEX_MEDIA_TYPE,
            params={"folder_id": "folder-123", "limit": 25},
        )

    @pytest.mark.anyio
    async def test_export_bibtex_requires_a_target(self, mendeley_client):
        """Test BibTeX export rejects calls with neither document nor folder."""
        request_mock = AsyncMock()
        mendeley_client._request = request_mock

        with pytest.raises(ValueError, match="document_id or folder_id"):
            await mendeley_client.export_bibtex()

        request_mock.assert_not_awaited()


class TestGetFileContent:
    """Tests for file download redirect handling."""

    @pytest.mark.anyio
    async def test_get_file_content_follows_303_redirect(
        self,
        mendeley_client,
        monkeypatch,
    ):
        """Mendeley answers the file lookup with a 303 to S3; follow its Location."""
        import mendeley_mcp.client as client_module

        redirect_request = httpx.Request(
            "GET", "https://api.mendeley.com/files/file-1"
        )
        redirect_response = httpx.Response(
            303,
            request=redirect_request,
            headers={"Location": "https://files.example.com/signed-url"},
        )
        redirect_error = httpx.HTTPStatusError(
            "Redirect response '303 See Other'",
            request=redirect_request,
            response=redirect_response,
        )
        request_mock = AsyncMock(
            side_effect=[
                make_json_response([{"id": "file-1"}]),
                redirect_error,
            ]
        )
        mendeley_client._request = request_mock

        downloaded = {}

        class FakeDownloadClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def get(self, url):
                downloaded["url"] = url
                response = Mock()
                response.content = b"%PDF-1.7 fake"
                response.raise_for_status = Mock()
                return response

        monkeypatch.setattr(
            client_module.httpx, "AsyncClient", FakeDownloadClient
        )

        content = await mendeley_client.get_file_content("doc-123")

        assert content == b"%PDF-1.7 fake"
        assert downloaded["url"] == "https://files.example.com/signed-url"

    @pytest.mark.anyio
    async def test_get_file_content_propagates_non_redirect_errors(
        self,
        mendeley_client,
    ):
        """Genuine HTTP errors on the file lookup should not be swallowed."""
        request = httpx.Request("GET", "https://api.mendeley.com/files/file-1")
        response = httpx.Response(500, request=request)
        error = httpx.HTTPStatusError(
            "server error", request=request, response=response
        )
        request_mock = AsyncMock(
            side_effect=[
                make_json_response([{"id": "file-1"}]),
                error,
            ]
        )
        mendeley_client._request = request_mock

        with pytest.raises(httpx.HTTPStatusError, match="server error"):
            await mendeley_client.get_file_content("doc-123")
