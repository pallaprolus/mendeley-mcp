"""
OAuth authentication flow for Mendeley.

This module provides a CLI for users to authenticate with Mendeley
and obtain their refresh token for use with the MCP server.
"""

from __future__ import annotations

import http.server
import json
import os
import secrets
import socketserver
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any

import click
import httpx

try:
    import keyring

    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

MENDELEY_AUTH_URL = "https://api.mendeley.com/oauth/authorize"
MENDELEY_TOKEN_URL = "https://api.mendeley.com/oauth/token"
CONFIG_DIR = Path.home() / ".config" / "mendeley-mcp"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"

# Callback handler for OAuth
_oauth_response: dict[str, Any] = {}


class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """Handler for OAuth callback."""

    def do_GET(self) -> None:
        global _oauth_response

        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            _oauth_response["code"] = params["code"][0]
            _oauth_response["success"] = True
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"""
                <html>
                <head><title>Mendeley MCP - Authentication Successful</title></head>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1>Authentication Successful!</h1>
                    <p>You can close this window and return to your terminal.</p>
                </body>
                </html>
                """
            )
        elif "error" in params:
            _oauth_response["error"] = params.get("error_description", params["error"])[0]
            _oauth_response["success"] = False
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            error_msg = _oauth_response["error"]
            self.wfile.write(
                f"""
                <html>
                <head><title>Mendeley MCP - Authentication Failed</title></head>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1>Authentication Failed</h1>
                    <p>Error: {error_msg}</p>
                    <p>Please try again.</p>
                </body>
                </html>
                """.encode()
            )

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress HTTP server logs."""
        pass


def save_credentials(
    client_id: str,
    client_secret: str,
    access_token: str,
    refresh_token: str,
) -> None:
    """Save credentials securely."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if KEYRING_AVAILABLE:
        # Store sensitive credentials in system keyring
        keyring.set_password("mendeley-mcp", "client_secret", client_secret)
        keyring.set_password("mendeley-mcp", "access_token", access_token)
        keyring.set_password("mendeley-mcp", "refresh_token", refresh_token)

        # Store non-sensitive config in file
        config = {
            "client_id": client_id,
            "use_keyring": True,
        }
    else:
        # Fall back to file storage (with warning)
        config = {
            "client_id": client_id,
            "client_secret": client_secret,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "use_keyring": False,
        }

    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(config, f, indent=2)

    # Restrict file permissions on Unix
    if sys.platform != "win32":
        os.chmod(CREDENTIALS_FILE, 0o600)


def load_credentials() -> dict[str, str] | None:
    """Load saved credentials."""
    if not CREDENTIALS_FILE.exists():
        return None

    with open(CREDENTIALS_FILE) as f:
        config = json.load(f)

    if config.get("use_keyring") and KEYRING_AVAILABLE:
        client_secret = keyring.get_password("mendeley-mcp", "client_secret")
        access_token = keyring.get_password("mendeley-mcp", "access_token")
        refresh_token = keyring.get_password("mendeley-mcp", "refresh_token")
        if access_token and refresh_token:
            config["client_secret"] = client_secret
            config["access_token"] = access_token
            config["refresh_token"] = refresh_token
        else:
            return None

    return config


def exchange_code_for_tokens(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict[str, str]:
    """Exchange authorization code for access and refresh tokens."""
    import base64
    
    # Mendeley requires HTTP Basic Auth
    auth_string = f"{client_id}:{client_secret}"
    auth_bytes = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
    
    # Try with Basic Auth first
    response = httpx.post(
        MENDELEY_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        headers={
            "Authorization": f"Basic {auth_bytes}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    
    # If Basic Auth fails, try with credentials in body
    if response.status_code == 401:
        response = httpx.post(
            MENDELEY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
    
    response.raise_for_status()
    return response.json()


@click.group()
def cli() -> None:
    """Mendeley MCP authentication tool."""
    pass


@cli.command()
@click.option(
    "--client-id",
    envvar="MENDELEY_CLIENT_ID",
    prompt="Client ID",
    help="Your Mendeley application client ID",
)
@click.option(
    "--client-secret",
    envvar="MENDELEY_CLIENT_SECRET",
    prompt="Client Secret",
    hide_input=True,
    help="Your Mendeley application client secret",
)
@click.option(
    "--port",
    default=8585,
    help="Local port for OAuth callback (default: 8585)",
)
def login(client_id: str, client_secret: str, port: int) -> None:
    """
    Authenticate with Mendeley and save credentials.

    This will open your browser to authorize the application.
    After authorization, your tokens will be saved securely.
    """
    global _oauth_response
    _oauth_response = {}

    redirect_uri = f"http://localhost:{port}/callback"
    state = secrets.token_urlsafe(16)

    # Build authorization URL
    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "all",
        "state": state,
    }
    auth_url = f"{MENDELEY_AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

    click.echo("\nOpening browser for Mendeley authentication...")
    click.echo(f"If the browser doesn't open, visit:\n{auth_url}\n")

    # Start local server for callback
    with socketserver.TCPServer(("", port), OAuthCallbackHandler) as httpd:
        # Open browser in background
        threading.Thread(target=lambda: webbrowser.open(auth_url), daemon=True).start()

        click.echo("Waiting for authorization...")
        httpd.handle_request()

    if not _oauth_response.get("success"):
        error = _oauth_response.get("error", "Unknown error")
        click.echo(f"\nAuthentication failed: {error}", err=True)
        sys.exit(1)

    # Exchange code for tokens
    click.echo("Exchanging code for tokens...")
    try:
        tokens = exchange_code_for_tokens(
            code=_oauth_response["code"],
            client_id=str(client_id),  # Ensure string
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
    except httpx.HTTPStatusError as e:
        click.echo(f"\nToken exchange failed: {e.response.text}", err=True)
        click.echo(f"Status code: {e.response.status_code}", err=True)
        click.echo(f"\nDebug info:", err=True)
        click.echo(f"  Client ID: {client_id}", err=True)
        click.echo(f"  Redirect URI: {redirect_uri}", err=True)
        click.echo(f"  Code received: {_oauth_response['code'][:20]}...", err=True)
        sys.exit(1)

    # Save credentials
    save_credentials(
        client_id=client_id,
        client_secret=client_secret,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )

    storage_method = "system keyring" if KEYRING_AVAILABLE else "config file"
    click.echo(f"\nSuccess! Credentials saved to {storage_method}.")
    click.echo(f"Config location: {CREDENTIALS_FILE}")

    if not KEYRING_AVAILABLE:
        click.echo(
            "\nNote: Install 'keyring' package for more secure token storage:\n"
            "  pip install keyring"
        )

    click.echo("\nYou can now use mendeley-mcp with Claude Desktop or other MCP clients.")
    click.echo("\nAdd to your MCP config:")
    click.echo(
        """
{
  "mcpServers": {
    "mendeley": {
      "command": "mendeley-mcp"
    }
  }
}
"""
    )


@cli.command()
def status() -> None:
    """Check authentication status."""
    creds = load_credentials()
    if not creds:
        click.echo("Not authenticated. Run 'mendeley-auth login' first.")
        sys.exit(1)

    click.echo("Authenticated with Mendeley")
    click.echo(f"Client ID: {creds.get('client_id', 'N/A')}")
    click.echo(f"Config file: {CREDENTIALS_FILE}")
    click.echo(f"Using keyring: {creds.get('use_keyring', False)}")

    # Test the token
    if creds.get("access_token"):
        try:
            response = httpx.get(
                "https://api.mendeley.com/profiles/me",
                headers={
                    "Authorization": f"Bearer {creds['access_token']}",
                    "Accept": "application/vnd.mendeley-profiles.2+json",
                },
            )
            if response.status_code == 200:
                profile = response.json()
                name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
                click.echo(f"Logged in as: {name or 'Unknown'}")
            elif response.status_code == 401:
                click.echo("Token expired. Run 'mendeley-auth login' to re-authenticate.")
        except Exception as e:
            click.echo(f"Could not verify token: {e}")


@cli.command()
def logout() -> None:
    """Remove saved credentials."""
    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()
        click.echo("Credentials file removed.")

    if KEYRING_AVAILABLE:
        try:
            keyring.delete_password("mendeley-mcp", "client_secret")
            keyring.delete_password("mendeley-mcp", "access_token")
            keyring.delete_password("mendeley-mcp", "refresh_token")
            click.echo("Keyring credentials removed.")
        except keyring.errors.PasswordDeleteError:
            pass

    click.echo("Logged out successfully.")


@cli.command()
def show_env() -> None:
    """Show environment variables for manual configuration."""
    creds = load_credentials()
    if not creds:
        click.echo("Not authenticated. Run 'mendeley-auth login' first.")
        sys.exit(1)

    click.echo("# Add these to your environment or MCP config:\n")
    click.echo(f'export MENDELEY_CLIENT_ID="{creds.get("client_id", "")}"')
    click.echo(f'export MENDELEY_CLIENT_SECRET="{creds.get("client_secret", "")}"')
    click.echo(f'export MENDELEY_ACCESS_TOKEN="{creds.get("access_token", "")}"')
    click.echo(f'export MENDELEY_REFRESH_TOKEN="{creds.get("refresh_token", "")}"')


if __name__ == "__main__":
    cli()
