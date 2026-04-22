"""
Mendeley API client for interacting with the Mendeley REST API.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

MENDELEY_API_BASE = "https://api.mendeley.com"
MENDELEY_AUTH_URL = "https://api.mendeley.com/oauth/authorize"
MENDELEY_TOKEN_URL = "https://api.mendeley.com/oauth/token"
DOCUMENT_MEDIA_TYPE = "application/vnd.mendeley-document.1+json"
FILE_MEDIA_TYPE = "application/vnd.mendeley-file.1+json"
FOLDER_MEDIA_TYPE = "application/vnd.mendeley-folder.1+json"


@dataclass
class MendeleyCredentials:
    """Mendeley OAuth credentials."""

    client_id: str
    client_secret: str
    access_token: str | None = None
    refresh_token: str | None = None

    @classmethod
    def from_env(cls) -> MendeleyCredentials:
        """Load credentials from environment variables."""
        client_id = os.environ.get("MENDELEY_CLIENT_ID")
        client_secret = os.environ.get("MENDELEY_CLIENT_SECRET")
        access_token = os.environ.get("MENDELEY_ACCESS_TOKEN")
        refresh_token = os.environ.get("MENDELEY_REFRESH_TOKEN")

        if not client_id or not client_secret:
            raise ValueError(
                "MENDELEY_CLIENT_ID and MENDELEY_CLIENT_SECRET must be set. "
                "Register your app at https://dev.mendeley.com/myapps.html"
            )

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            access_token=access_token,
            refresh_token=refresh_token,
        )


@dataclass
class Document:
    """Represents a Mendeley document."""

    id: str
    title: str
    type: str
    authors: list[dict[str, str]]
    year: int | None = None
    abstract: str | None = None
    source: str | None = None
    identifiers: dict[str, str] | None = None
    keywords: list[str] | None = None
    tags: list[str] | None = None
    folder_uuids: list[str] | None = None
    file_attached: bool = False
    created: str | None = None
    last_modified: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Document:
        """Create a Document from API response data."""
        return cls(
            id=data["id"],
            title=data.get("title", "Untitled"),
            type=data.get("type", "unknown"),
            authors=data.get("authors", []),
            year=data.get("year"),
            abstract=data.get("abstract"),
            source=data.get("source"),
            identifiers=data.get("identifiers"),
            keywords=data.get("keywords"),
            tags=data.get("tags"),
            folder_uuids=data.get("folder_uuids"),
            file_attached=data.get("file_attached", False),
            created=data.get("created"),
            last_modified=data.get("last_modified"),
        )

    def format_citation(self) -> str:
        """Format document as a citation string."""
        author_str = ""
        if self.authors:
            names = []
            for author in self.authors[:3]:
                last = author.get("last_name", "")
                first = author.get("first_name", "")
                if last:
                    names.append(f"{last}, {first[0]}." if first else last)
            author_str = "; ".join(names)
            if len(self.authors) > 3:
                author_str += " et al."

        year_str = f"({self.year})" if self.year else ""
        source_str = f". {self.source}" if self.source else ""

        return f"{author_str} {year_str}. {self.title}{source_str}"


@dataclass
class Folder:
    """Represents a Mendeley folder/collection."""

    id: str
    name: str
    parent_id: str | None = None
    created: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Folder:
        """Create a Folder from API response data."""
        return cls(
            id=data["id"],
            name=data["name"],
            parent_id=data.get("parent_id"),
            created=data.get("created"),
        )


class MendeleyClient:
    """Async client for the Mendeley API."""

    def __init__(self, credentials: MendeleyCredentials) -> None:
        self.credentials = credentials
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> MendeleyClient:
        self._client = httpx.AsyncClient(
            base_url=MENDELEY_API_BASE,
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client

    def _auth_headers(self, accept: str | None = None) -> dict[str, str]:
        """Get authorization headers."""
        if not self.credentials.access_token:
            raise ValueError(
                "No access token available. Run 'mendeley-auth login' first."
            )
        headers = {
            "Authorization": f"Bearer {self.credentials.access_token}",
        }
        if accept:
            headers["Accept"] = accept
        return headers

    @staticmethod
    def _content_type_headers(media_type: str) -> dict[str, str]:
        """Build a content-type header for typed JSON API requests."""
        return {"Content-Type": media_type}

    @staticmethod
    def _json_object(payload: Any, resource_name: str) -> dict[str, Any]:
        """Validate and return an object-shaped JSON response."""
        if not isinstance(payload, dict):
            raise ValueError(
                f"Unexpected {resource_name} response from Mendeley API."
            )
        return payload

    @staticmethod
    def _json_array(payload: Any, resource_name: str) -> list[Any]:
        """Validate and return an array-shaped JSON response."""
        if not isinstance(payload, list):
            raise ValueError(
                f"Unexpected {resource_name} response from Mendeley API."
            )
        return payload

    @staticmethod
    def _next_page_url(response: httpx.Response) -> str | None:
        """Return the next paginated URL when present."""
        next_link = response.links.get("next")
        if next_link is None:
            return None

        next_url = next_link.get("url")
        return next_url if isinstance(next_url, str) else None

    @staticmethod
    def _folder_document_id(payload: object) -> str | None:
        """Extract a document identifier from folder-membership payloads."""
        if not isinstance(payload, dict):
            return None

        document_id = payload.get("id")
        return document_id if isinstance(document_id, str) else None

    async def _request_document_resource(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Request a document resource using the shared document media type."""
        return await self._request(
            method,
            path,
            accept=DOCUMENT_MEDIA_TYPE,
            **kwargs,
        )

    async def _request_file_resource(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Request a file resource using the shared file media type."""
        return await self._request(
            method,
            path,
            accept=FILE_MEDIA_TYPE,
            **kwargs,
        )

    async def _request_folder_resource(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Request a folder resource using the shared folder media type."""
        return await self._request(
            method,
            path,
            accept=FOLDER_MEDIA_TYPE,
            **kwargs,
        )

    async def _request_folder_write(
        self,
        method: str,
        path: str,
        payload: dict[str, Any],
    ) -> httpx.Response:
        """Send a folder-management write request with the correct media type."""
        return await self._request_folder_resource(
            method,
            path,
            json=payload,
            headers=self._content_type_headers(FOLDER_MEDIA_TYPE),
        )

    async def _request_folder_document_write(
        self,
        method: str,
        path: str,
        payload: dict[str, str],
    ) -> httpx.Response:
        """Send a folder-document write request with the correct media type."""
        return await self._request_document_resource(
            method,
            path,
            json=payload,
            headers=self._content_type_headers(DOCUMENT_MEDIA_TYPE),
        )

    async def refresh_access_token(self) -> str:
        """Refresh the access token using the refresh token."""
        if not self.credentials.refresh_token:
            raise ValueError("No refresh token available.")

        # Mendeley prefers HTTP Basic Auth
        import base64
        auth_str = f"{self.credentials.client_id}:{self.credentials.client_secret}"
        auth_bytes = base64.b64encode(auth_str.encode()).decode()

        response = await self.client.post(
            MENDELEY_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.credentials.refresh_token,
            },
            headers={
                "Authorization": f"Basic {auth_bytes}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        response.raise_for_status()
        data = self._json_object(response.json(), "token refresh")

        access_token = data.get("access_token")
        if not isinstance(access_token, str):
            raise ValueError("Token refresh did not return an access token.")

        self.credentials.access_token = access_token

        refresh_token = data.get("refresh_token")
        if refresh_token is not None:
            if not isinstance(refresh_token, str):
                raise ValueError("Token refresh returned an invalid refresh token.")
            self.credentials.refresh_token = refresh_token

        return access_token

    async def _request(
        self,
        method: str,
        path: str,
        accept: str = "application/json",
        **kwargs: Any,
    ) -> httpx.Response:
        """Make an authenticated request, refreshing token if needed."""
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.credentials.access_token}"
        headers["Accept"] = accept

        response = await self.client.request(method, path, headers=headers, **kwargs)

        # If unauthorized, try refreshing the token
        if response.status_code == 401 and self.credentials.refresh_token:
            await self.refresh_access_token()
            headers["Authorization"] = f"Bearer {self.credentials.access_token}"
            response = await self.client.request(method, path, headers=headers, **kwargs)

        response.raise_for_status()
        return response

    async def search_library(
        self,
        query: str,
        limit: int = 20,
    ) -> list[Document]:
        """Search documents in the user's library."""
        response = await self._request_document_resource(
            "GET",
            "/search/documents",
            params={"query": query, "limit": limit},
        )
        data = self._json_array(response.json(), "document search")
        return [Document.from_api(doc) for doc in data]

    async def get_documents(
        self,
        folder_id: str | None = None,
        limit: int = 50,
        sort: str = "last_modified",
        order: str = "desc",
    ) -> list[Document]:
        """Get documents from the library or a specific folder."""
        params: dict[str, Any] = {
            "limit": limit,
            "sort": sort,
            "order": order,
            "view": "all",
        }
        if folder_id:
            params["folder_id"] = folder_id

        response = await self._request_document_resource(
            "GET",
            "/documents",
            params=params,
        )
        data = self._json_array(response.json(), "document list")
        return [Document.from_api(doc) for doc in data]

    async def get_document(self, document_id: str) -> Document:
        """Get a specific document by ID."""
        response = await self._request_document_resource(
            "GET",
            f"/documents/{document_id}",
            params={"view": "all"},
        )
        return Document.from_api(self._json_object(response.json(), "document"))

    async def get_folders(self) -> list[Folder]:
        """Get all folders in the library."""
        response = await self._request_folder_resource(
            "GET",
            "/folders",
        )
        data = self._json_array(response.json(), "folder list")
        return [Folder.from_api(folder) for folder in data]

    async def get_folder(self, folder_id: str) -> Folder:
        """Get a specific folder by ID."""
        response = await self._request_folder_resource(
            "GET",
            f"/folders/{folder_id}",
        )
        return Folder.from_api(self._json_object(response.json(), "folder"))

    async def create_folder(
        self,
        name: str,
        parent_id: str | None = None,
        group_id: str | None = None,
    ) -> Folder:
        """Create a folder in the personal library or a group."""
        payload: dict[str, Any] = {"name": name}
        if parent_id is not None:
            payload["parent_id"] = parent_id
        if group_id is not None:
            payload["group_id"] = group_id

        response = await self._request_folder_write(
            "POST",
            "/folders",
            payload,
        )
        return Folder.from_api(self._json_object(response.json(), "folder"))

    async def rename_folder(
        self,
        folder_id: str,
        name: str,
    ) -> Folder:
        """Rename an existing folder and return the stable folder payload."""
        folder = await self.get_folder(folder_id)
        await self._request_folder_write(
            "PATCH",
            f"/folders/{folder_id}",
            {"name": name},
        )
        return Folder(
            id=folder.id,
            name=name,
            parent_id=folder.parent_id,
            created=folder.created,
        )

    async def delete_folder(
        self,
        folder_id: str,
    ) -> dict[str, str]:
        """Delete an existing folder and return a deterministic confirmation."""
        await self._request(
            "DELETE",
            f"/folders/{folder_id}",
            accept=FOLDER_MEDIA_TYPE,
        )
        return {
            "id": folder_id,
            "status": "deleted",
        }

    async def _folder_contains_document(
        self,
        folder_id: str,
        document_id: str,
    ) -> bool:
        """Check whether a folder already contains a specific document."""
        path = f"/folders/{folder_id}/documents"
        params: dict[str, int] | None = None

        while True:
            request_kwargs: dict[str, Any] = {}
            if params is not None:
                request_kwargs["params"] = params

            response = await self._request_document_resource(
                "GET",
                path,
                **request_kwargs,
            )
            memberships = self._json_array(
                response.json(),
                "folder document membership",
            )
            if any(
                self._folder_document_id(membership) == document_id
                for membership in memberships
            ):
                return True

            next_page_url = self._next_page_url(response)
            if next_page_url is None:
                return False

            path = next_page_url
            params = None

    async def add_document_to_folder(
        self,
        folder_id: str,
        document_id: str,
    ) -> dict[str, str]:
        """Add an existing document to a folder with explicit duplicate rejection."""
        if await self._folder_contains_document(folder_id, document_id):
            raise ValueError("Document is already in the target folder.")

        await self._request_folder_document_write(
            "POST",
            f"/folders/{folder_id}/documents",
            {"id": document_id},
        )
        return {
            "folder_id": folder_id,
            "document_id": document_id,
            "status": "added",
        }

    async def get_file_content(self, document_id: str) -> bytes | None:
        """Get the PDF content of a document if available."""
        # First, get the file info
        response = await self._request_file_resource(
            "GET",
            "/files",
            params={"document_id": document_id},
        )
        files = self._json_array(response.json(), "file list")

        if not files:
            return None

        file_id = files[0]["id"]

        # Get the download URL
        response = await self._request_file_resource(
            "GET",
            f"/files/{file_id}",
        )

        # The response contains a redirect URL for download
        download_url = response.headers.get("Location")
        if not download_url:
            return None

        # Download the actual file
        async with httpx.AsyncClient() as download_client:
            file_response = await download_client.get(download_url)
            file_response.raise_for_status()
            return file_response.content

    async def search_catalog(
        self,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search the Mendeley catalog (global database)."""
        response = await self._request_document_resource(
            "GET",
            "/search/catalog",
            params={"query": query, "limit": limit},
        )
        return self._json_array(response.json(), "catalog search")

    async def get_catalog_document(
        self,
        catalog_id: str | None = None,
        doi: str | None = None,
    ) -> dict[str, Any]:
        """Get a document from the catalog by ID or DOI."""
        if doi:
            response = await self._request(
                "GET",
                "/catalog",
                accept=DOCUMENT_MEDIA_TYPE,
                params={"doi": doi, "view": "all"},
            )
            data = self._json_array(response.json(), "catalog lookup")
            return data[0] if data else {}
        elif catalog_id:
            response = await self._request_document_resource(
                "GET",
                f"/catalog/{catalog_id}",
                params={"view": "all"},
            )
            return self._json_object(response.json(), "catalog document")
        else:
            raise ValueError("Either catalog_id or doi must be provided")

    async def add_document(
        self,
        title: str,
        doc_type: str = "journal",
        **kwargs: Any,
    ) -> Document:
        """Add a new document to the library."""
        data = {
            "title": title,
            "type": doc_type,
            **kwargs,
        }
        response = await self._request_document_resource(
            "POST",
            "/documents",
            json=data,
            headers=self._content_type_headers(DOCUMENT_MEDIA_TYPE),
        )
        return Document.from_api(self._json_object(response.json(), "document"))
