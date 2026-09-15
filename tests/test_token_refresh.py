"""Offline reproduction of token rotation followed by a server restart."""

import json

import httpx
import pytest

from mendeley_mcp import auth
from mendeley_mcp.client import MendeleyClient, MendeleyCredentials


@pytest.mark.asyncio
async def test_rotated_tokens_survive_restart(tmp_path, monkeypatch):
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text(
        json.dumps(
            {
                "client_id": "local-test",
                "client_secret": "fake-secret",
                "access_token": "expired-access",
                "refresh_token": "original-refresh",
                "use_keyring": False,
            }
        )
    )
    monkeypatch.setattr(auth, "CREDENTIALS_FILE", credentials_file)
    credentials = MendeleyCredentials(
        "local-test", "fake-secret", "expired-access", "original-refresh"
    )
    credentials.persist_tokens = True

    def upstream(request):
        if request.url.path == "/oauth/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "new-access",
                    "refresh_token": "rotated-refresh",
                },
            )
        if request.headers["Authorization"] == "Bearer expired-access":
            return httpx.Response(401)
        assert request.headers["Authorization"] == "Bearer new-access"
        return httpx.Response(200, json=[])

    client = MendeleyClient(credentials)
    async with httpx.AsyncClient(
        base_url="https://api.mendeley.com", transport=httpx.MockTransport(upstream)
    ) as http:
        client._client = http
        await client.get_documents()
        assert credentials.access_token == "new-access"  # This works even before the fix.

    # A new server process reads durable storage, not the previous client's memory.
    reloaded = auth.load_credentials()
    assert reloaded["access_token"] == "new-access"
    assert reloaded["refresh_token"] == "rotated-refresh"


@pytest.mark.asyncio
async def test_concurrent_unauthorized_requests_share_refresh():
    import asyncio

    credentials = MendeleyCredentials("id", "secret", "old", "refresh")
    arrivals = 0
    refreshes = 0
    both_arrived = asyncio.Event()

    async def upstream(request):
        nonlocal arrivals, refreshes
        if request.url.path == "/oauth/token":
            refreshes += 1
            await asyncio.sleep(0)
            return httpx.Response(200, json={"access_token": "new"})
        if request.headers["Authorization"] == "Bearer old":
            arrivals += 1
            if arrivals == 2:
                both_arrived.set()
            await both_arrived.wait()
            return httpx.Response(401)
        return httpx.Response(200, json=[])

    client = MendeleyClient(credentials)
    async with httpx.AsyncClient(
        base_url="https://api.mendeley.com", transport=httpx.MockTransport(upstream)
    ) as http:
        client._client = http
        await asyncio.wait_for(asyncio.gather(client.get_documents(), client.get_documents()), 5)
    assert refreshes == 1
    assert credentials.refresh_token == "refresh"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"access_token": ""},
        {"access_token": None},
        {"access_token": "new", "refresh_token": ""},
        {"access_token": "new", "refresh_token": None},
    ],
)
async def test_invalid_refresh_does_not_change_live_pair(payload):
    credentials = MendeleyCredentials("id", "secret", "old", "refresh")
    client = MendeleyClient(credentials)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as http:
        client._client = http
        with pytest.raises(ValueError):
            await client.refresh_access_token()
    assert credentials.access_token == "old"
    assert credentials.refresh_token == "refresh"


@pytest.mark.asyncio
async def test_storage_failure_keeps_live_pair_and_warns_without_secrets(monkeypatch, caplog):
    def fail(*args):
        raise RuntimeError("sensitive-storage-details")

    monkeypatch.setattr(auth, "save_refreshed_tokens", fail)
    credentials = MendeleyCredentials("id", "secret", "old", "refresh", persist_tokens=True)
    client = MendeleyClient(credentials)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"access_token": "new-private-token"})
        )
    ) as http:
        client._client = http
        assert await client.refresh_access_token() == "new-private-token"
    assert "could not be saved" in caplog.text
    assert "sensitive-storage-details" not in caplog.text
    assert "new-private-token" not in caplog.text


def test_environment_credentials_do_not_enable_persistence(monkeypatch):
    from mendeley_mcp.server import get_credentials

    for name, value in {
        "CLIENT_ID": "id",
        "CLIENT_SECRET": "secret",
        "ACCESS_TOKEN": "access",
        "REFRESH_TOKEN": "refresh",
    }.items():
        monkeypatch.setenv("MENDELEY_" + name, value)
    assert get_credentials().persist_tokens is False


def test_saved_credentials_enable_persistence(monkeypatch):
    from mendeley_mcp import server

    for name in ("CLIENT_ID", "CLIENT_SECRET", "ACCESS_TOKEN", "REFRESH_TOKEN"):
        monkeypatch.delenv("MENDELEY_" + name, raising=False)
    monkeypatch.setattr(
        server,
        "load_credentials",
        lambda: {
            "client_id": "id",
            "access_token": "access",
            "refresh_token": "refresh",
        },
    )
    assert server.get_credentials().persist_tokens is True


def test_keyring_rotation_survives_reload(tmp_path, monkeypatch):
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({"client_id": "id", "use_keyring": True}))
    entries = {"client_secret": "secret", "access_token": "old", "refresh_token": "refresh"}

    class Keyring:
        def get_password(self, service, key):
            return entries.get(key)

        def set_password(self, service, key, value):
            entries[key] = value

    monkeypatch.setattr(auth, "CREDENTIALS_FILE", path)
    monkeypatch.setattr(auth, "KEYRING_AVAILABLE", True)
    monkeypatch.setattr(auth, "keyring", Keyring())
    auth.save_refreshed_tokens("id", "refresh", "new", "rotated")
    loaded = auth.load_credentials()
    assert loaded["access_token"] == "new"
    assert loaded["refresh_token"] == "rotated"
    assert loaded["client_secret"] == "secret"
    assert json.loads(path.read_text()) == {"client_id": "id", "use_keyring": True}


@pytest.mark.parametrize("case", ["different-account", "different-token", "missing", "no-keyring"])
def test_changed_or_unavailable_login_is_not_overwritten(tmp_path, monkeypatch, case):
    path = tmp_path / "credentials.json"
    content = json.dumps(
        {
            "client_id": "other" if case == "different-account" else "id",
            "refresh_token": "other" if case == "different-token" else "refresh",
            "use_keyring": case == "no-keyring",
        }
    )
    if case != "missing":
        path.write_text(content)
    monkeypatch.setattr(auth, "CREDENTIALS_FILE", path)
    monkeypatch.setattr(auth, "KEYRING_AVAILABLE", False)
    with pytest.raises((ValueError, RuntimeError, FileNotFoundError)):
        auth.save_refreshed_tokens("id", "refresh", "new", "rotated")
    if case == "missing":
        assert not path.exists()
    else:
        assert path.read_text() == content


def test_file_replace_failure_preserves_original(tmp_path, monkeypatch):
    path = tmp_path / "credentials.json"
    original = json.dumps({"client_id": "id", "refresh_token": "refresh", "use_keyring": False})
    path.write_text(original)
    monkeypatch.setattr(auth, "CREDENTIALS_FILE", path)

    def fail(*args):
        raise OSError("replace failed")

    monkeypatch.setattr(auth.os, "replace", fail)
    with pytest.raises(OSError):
        auth.save_refreshed_tokens("id", "refresh", "new", "rotated")
    assert path.read_text() == original
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.asyncio
async def test_environment_refresh_never_writes_saved_login(monkeypatch):
    from mendeley_mcp.server import get_credentials

    for name, value in {
        "CLIENT_ID": "id",
        "CLIENT_SECRET": "secret",
        "ACCESS_TOKEN": "old",
        "REFRESH_TOKEN": "refresh",
    }.items():
        monkeypatch.setenv("MENDELEY_" + name, value)

    def forbidden(*args):
        pytest.fail("Environment credentials must not write the saved login")

    monkeypatch.setattr(auth, "save_refreshed_tokens", forbidden)
    client = MendeleyClient(get_credentials())
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={"access_token": "new", "refresh_token": "rotated"}
            )
        )
    ) as http:
        client._client = http
        assert await client.refresh_access_token() == "new"


def test_file_token_pair_is_written_with_private_permissions(tmp_path, monkeypatch):
    import sys

    path = tmp_path / "credentials.json"
    path.write_text(
        json.dumps(
            {
                "client_id": "id",
                "client_secret": "secret",
                "refresh_token": "refresh",
                "use_keyring": False,
            }
        )
    )
    monkeypatch.setattr(auth, "CREDENTIALS_FILE", path)
    auth.save_refreshed_tokens("id", "refresh", "new", "rotated")
    loaded = auth.load_credentials()
    assert loaded["access_token"] == "new"
    assert loaded["refresh_token"] == "rotated"
    assert loaded["client_secret"] == "secret"
    if sys.platform != "win32":
        assert path.stat().st_mode & 0o777 == 0o600
