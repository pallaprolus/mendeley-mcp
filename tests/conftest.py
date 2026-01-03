"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def sample_document_data():
    """Sample document data from API."""
    return {
        "id": "test-doc-id",
        "title": "Machine Learning: A Review",
        "type": "journal",
        "authors": [
            {"first_name": "John", "last_name": "Smith"},
            {"first_name": "Jane", "last_name": "Doe"},
        ],
        "year": 2024,
        "abstract": "This paper reviews recent advances in machine learning...",
        "source": "Journal of AI Research",
        "identifiers": {
            "doi": "10.1234/jair.2024.001",
            "pmid": "12345678",
        },
        "keywords": ["machine learning", "deep learning", "neural networks"],
        "file_attached": True,
        "created": "2024-01-15T10:00:00Z",
        "last_modified": "2024-06-01T15:30:00Z",
    }


@pytest.fixture
def sample_folder_data():
    """Sample folder data from API."""
    return {
        "id": "test-folder-id",
        "name": "Research Papers",
        "parent_id": None,
        "created": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_credentials():
    """Mock Mendeley credentials for testing."""
    from mendeley_mcp.client import MendeleyCredentials

    return MendeleyCredentials(
        client_id="test-client-id",
        client_secret="test-client-secret",
        access_token="test-access-token",
        refresh_token="test-refresh-token",
    )
