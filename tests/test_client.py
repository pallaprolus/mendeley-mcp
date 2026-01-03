"""Tests for the Mendeley API client."""

import pytest

from mendeley_mcp.client import Document, Folder, MendeleyCredentials


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
