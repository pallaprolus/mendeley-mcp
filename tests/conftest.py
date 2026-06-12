"""Pytest configuration and fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


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
def sample_nested_folder_data():
    """Sample nested folder data from API."""
    return {
        "id": "child-folder-id",
        "name": "Screening",
        "parent_id": "parent-folder-id",
        "created": "2024-01-02T00:00:00Z",
    }


@pytest.fixture
def sample_group_folder_data():
    """Sample group-scoped folder data from API."""
    return {
        "id": "group-folder-id",
        "name": "Shared Reading List",
        "parent_id": None,
        "group_id": "group-123",
        "created": "2024-01-03T00:00:00Z",
    }


@pytest.fixture
def root_folder_create_request():
    """Sample request payload for root folder creation."""
    return {
        "name": "Research Papers",
    }


@pytest.fixture
def nested_folder_create_request():
    """Sample request payload for nested folder creation."""
    return {
        "name": "Screening",
        "parent_id": "parent-folder-id",
    }


@pytest.fixture
def group_folder_create_request():
    """Sample request payload for group folder creation."""
    return {
        "name": "Shared Reading List",
        "group_id": "group-123",
    }


@pytest.fixture
def folder_rename_request(sample_folder_data):
    """Sample request payload for renaming an existing folder."""
    return {
        "folder_id": sample_folder_data["id"],
        "name": "Renamed Research Papers",
    }


@pytest.fixture
def renamed_folder_data(sample_folder_data, folder_rename_request):
    """Sample folder data after a successful rename operation."""
    return {
        **sample_folder_data,
        "name": folder_rename_request["name"],
    }


@pytest.fixture
def folder_delete_request(sample_folder_data):
    """Sample request payload for deleting an existing folder."""
    return {
        "folder_id": sample_folder_data["id"],
    }


@pytest.fixture
def folder_delete_result(folder_delete_request):
    """Deterministic client confirmation for a successful folder deletion."""
    return {
        "id": folder_delete_request["folder_id"],
        "status": "deleted",
    }


@pytest.fixture
def folder_assignment_request(sample_document_data, sample_folder_data):
    """Sample request payload for assigning a document to a folder."""
    return {
        "folder_id": sample_folder_data["id"],
        "document_id": sample_document_data["id"],
    }


@pytest.fixture
def folder_assignment_result(folder_assignment_request):
    """Stable client result for a successful folder assignment."""
    return {
        "folder_id": folder_assignment_request["folder_id"],
        "document_id": folder_assignment_request["document_id"],
        "status": "added",
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


@pytest.fixture
def mendeley_client(mock_credentials):
    """Async Mendeley client instance for unit tests."""
    from mendeley_mcp.client import MendeleyClient

    return MendeleyClient(mock_credentials)
