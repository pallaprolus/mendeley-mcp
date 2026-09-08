"""Exercise issue #11 through real JSON-RPC serialization over stdio."""

from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest


@contextmanager
def rpc_server(script: str):
    """Start a server and bound every response wait; always reap the process."""
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    replies = queue.Queue()

    def read_stdout():
        for line in process.stdout:
            replies.put(line)
        replies.put(None)

    reader = threading.Thread(target=read_stdout, daemon=True)
    reader.start()
    request_id = 0

    def request(method, params=None, *, notification=False):
        nonlocal request_id
        request_id += 1
        message = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        if not notification:
            message["id"] = request_id
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()
        if notification:
            return None
        while True:
            line = replies.get(timeout=30)
            assert line is not None, "Server exited before responding"
            response = json.loads(line)
            if response.get("id") == request_id:
                assert "error" not in response, response
                return response["result"]

    try:
        initialized = request("initialize", {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "issue-11-regression", "version": "1.0"},
        })
        assert initialized["serverInfo"]["name"] == "mendeley"
        request("notifications/initialized", notification=True)
        yield request
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        reader.join(timeout=5)
        process.stdout.close()


@pytest.mark.parametrize("mode", ["normal", "truncated", "scanned", "missing", "invalid"])
def test_document_text_reaches_both_client_representations(mode):
    script = f"""
from tests.test_server import TextDownloadClient, _make_pdf
from mendeley_mcp import server

mode = {mode!r}
class Client(TextDownloadClient):
    async def get_file_content(self, document_id):
        if mode == 'missing':
            return None
        if mode == 'invalid':
            return b'not a PDF'
        return await super().get_file_content(document_id)

async def get_client():
    return Client(_make_pdf('' if mode == 'scanned' else 'ISSUE_11_TEXT'))

server.get_client = get_client
if mode == 'truncated':
    server.MAX_EXTRACTED_TEXT_CHARS = 5
server.mcp.run()
"""
    with rpc_server(script) as request:
        tools = request("tools/list")["tools"]
        assert "mendeley_get_document_text" in {tool["name"] for tool in tools}
        result = request("tools/call", {
            "name": "mendeley_get_document_text",
            "arguments": {"document_id": "doc-text"},
        })

    structured = result["structuredContent"]
    assert result.get("isError", False) is (mode == "invalid")
    if mode in {"normal", "truncated"}:
        # Reproduce both a content-block client and Cowork's structured-only view.
        assert structured["text"] == result["content"][1]["text"]
        assert structured["text"] == ("ISSUE" if mode == "truncated" else "ISSUE_11_TEXT")
        assert structured["truncated"] is (mode == "truncated")
        assert structured["char_count"] == len("ISSUE_11_TEXT")
        assert len(result["content"]) == 2
    else:
        assert structured["text_available"] is False
        assert "text" not in structured
        assert len(result["content"]) == 1
