"""Authenticated MCP HTTP connections and credential handling.

MCP credentials are encrypted as soon as they enter the backend. For logged-in
users the ciphertext is persisted as part of their SessionData. Anonymous
credentials are usable for 24 hours but are removed from database snapshots by
the session manager, so a backend restart always forgets them.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from urllib.parse import parse_qs, urlparse

import httpx2
from cryptography.fernet import Fernet, InvalidToken
from mcp.client import Client
from mcp.client.auth import AuthorizationCodeResult, OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthMetadata, OAuthToken
from pydantic import AnyUrl

from .models import MCPAuthType, MCPCreateRequest, MCPServer, MCPAuthNotification, OpacaException, SessionData


logger = logging.getLogger(__name__)
ANONYMOUS_CREDENTIAL_TTL_SECONDS = 60 * 60 * 24
OAUTH_TIMEOUT_SECONDS = 15 * 60
TOKEN_EXPIRY_KEY = "token_expires_at"
OAUTH_METADATA_KEY = "oauth_metadata"


def _load_cipher() -> tuple[Fernet, bool]:
    configured_key = os.getenv("MCP_CREDENTIAL_ENCRYPTION_KEY")
    if configured_key:
        try:
            return Fernet(configured_key.encode()), False
        except (ValueError, TypeError) as exc:
            raise RuntimeError(
                "MCP_CREDENTIAL_ENCRYPTION_KEY must be a URL-safe base64-encoded 32-byte Fernet key."
            ) from exc
    logger.warning(
        "MCP_CREDENTIAL_ENCRYPTION_KEY is not configured. MCP credentials can only be decrypted "
        "until this backend process stops. Configure a stable Fernet key before using persistent "
        "authenticated MCP connections."
    )
    return Fernet(Fernet.generate_key()), True


_credential_cipher, uses_ephemeral_encryption_key = _load_cipher()


def encrypt_credentials(data: dict[str, Any]) -> str:
    return _credential_cipher.encrypt(json.dumps(data).encode()).decode()


def decrypt_credentials(server: MCPServer) -> dict[str, Any]:
    if server.credential_expires_at is not None and server.credential_expires_at <= time.time():
        server.encrypted_credentials = None
        raise OpacaException(
            "The credentials for this MCP server have expired. Remove and add the server again.",
            "Anonymous MCP credentials expired.",
            401,
        )
    if not server.encrypted_credentials:
        return {}
    try:
        return json.loads(_credential_cipher.decrypt(server.encrypted_credentials.encode()).decode())
    except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
        raise OpacaException(
            "The credentials for this MCP server can no longer be read. Remove and add the server again.",
            "Unable to decrypt MCP credentials.",
            401,
        ) from exc


def update_credentials(server: MCPServer, data: dict[str, Any]) -> None:
    server.encrypted_credentials = encrypt_credentials(data)


def create_mcp_server(req: MCPCreateRequest, persistent: bool) -> MCPServer:
    auth = req.auth
    credentials: dict[str, Any] = {}
    if auth.headers:
        credentials["headers"] = auth.headers
    if auth.client_id:
        credentials["client_info"] = {
            "client_id": auth.client_id,
            "client_secret": auth.client_secret,
            "redirect_uris": [],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "client_secret_post" if auth.client_secret else "none",
        }

    uses_auth = auth.auth_type != MCPAuthType.NONE
    return MCPServer(
        server_url=req.server_url,
        server_label=req.server_label or "",
        type=req.type,
        auth_type=auth.auth_type,
        encrypted_credentials=encrypt_credentials(credentials) if uses_auth else None,
        credential_expires_at=None if persistent or not uses_auth else time.time() + ANONYMOUS_CREDENTIAL_TTL_SECONDS,
    )


class MCPTokenStorage(TokenStorage):
    def __init__(self, server: MCPServer, session: SessionData | None = None):
        self.server = server
        self.session = session
        self.provider: OAuthClientProvider | None = None

    def bind_provider(self, provider: OAuthClientProvider) -> None:
        self.provider = provider

    async def _persist_if_installed(self) -> None:
        """Persist refreshed OAuth state without waiting for periodic session storage."""
        if not self.session or not self.session.user_id:
            return
        if self.session.mcp_servers.get(self.server.server_label) is not self.server:
            return
        from .services.session_manager import db_client
        await db_client.save_session(self.session)

    async def get_tokens(self) -> OAuthToken | None:
        raw = decrypt_credentials(self.server).get("tokens")
        return OAuthToken.model_validate(raw) if raw else None

    async def set_tokens(self, tokens: OAuthToken) -> None:
        data = decrypt_credentials(self.server)
        data["tokens"] = tokens.model_dump(mode="json")
        if tokens.expires_in is None:
            data.pop(TOKEN_EXPIRY_KEY, None)
        else:
            # expires_in is relative to issuance
            # Persist the absolute time
            data[TOKEN_EXPIRY_KEY] = time.time() + int(tokens.expires_in)
        if self.provider and self.provider.context.oauth_metadata:
            # Refresh can happen before another resource request,
            # so a provider recreated after restart must already know the discovered token
            data[OAUTH_METADATA_KEY] = self.provider.context.oauth_metadata.model_dump(mode="json")
        update_credentials(self.server, data)
        await self._persist_if_installed()

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        raw = decrypt_credentials(self.server).get("client_info")
        if not raw:
            return None
        # The redirect URI is installation-specific and is added after the request base URL is known.
        if self.server.oauth_redirect_uri:
            raw["redirect_uris"] = [self.server.oauth_redirect_uri]
        return OAuthClientInformationFull.model_validate(raw)

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        data = decrypt_credentials(self.server)
        data["client_info"] = client_info.model_dump(mode="json")
        update_credentials(self.server, data)
        await self._persist_if_installed()


class OAuthCallbackBroker:
    """Connect a provider redirect with the callback received by FastAPI."""

    def __init__(self, session: SessionData):
        self.session = session
        self.state: str | None = None
        self.future: asyncio.Future[AuthorizationCodeResult] | None = None

    async def redirect(self, authorization_url: str) -> None:
        state = parse_qs(urlparse(authorization_url).query).get("state", [None])[0]
        if not state:
            raise RuntimeError("The MCP authorization server returned an authorization URL without state.")
        self.state = state
        self.future = asyncio.get_running_loop().create_future()
        oauth_callbacks[state] = self.future
        try:
            await self.session.websocket_send(MCPAuthNotification(authorization_url=authorization_url))
        except BaseException:
            oauth_callbacks.pop(state, None)
            self.future.cancel()
            self.future = None
            self.state = None
            raise

    async def callback(self) -> AuthorizationCodeResult:
        if not self.future:
            raise RuntimeError("MCP OAuth callback requested before the authorization redirect was created.")
        try:
            return await asyncio.wait_for(self.future, timeout=OAUTH_TIMEOUT_SECONDS)
        finally:
            if self.state:
                oauth_callbacks.pop(self.state, None)


oauth_callbacks: dict[str, asyncio.Future[AuthorizationCodeResult]] = {}


def finish_oauth_callback(code: str, state: str, issuer: str | None = None) -> bool:
    future = oauth_callbacks.get(state)
    if not future or future.done():
        return False
    future.set_result(AuthorizationCodeResult(code=code, state=state, iss=issuer))
    return True


def fail_oauth_callback(error: str, state: str) -> bool:
    future = oauth_callbacks.get(state)
    if not future or future.done():
        return False
    future.set_exception(RuntimeError(f"MCP authorization failed: {error}"))
    return True


def _static_headers(server: MCPServer) -> dict[str, str]:
    return decrypt_credentials(server).get("headers", {})


def _oauth_provider(session: SessionData, server: MCPServer) -> OAuthClientProvider:
    if not server.oauth_redirect_uri:
        raise OpacaException(
            "MCP OAuth is not configured on this backend.",
            "Missing OAuth redirect URI.",
            500,
        )
    if server._oauth_provider is not None:
        return server._oauth_provider

    broker = OAuthCallbackBroker(session)
    storage = MCPTokenStorage(server, session)
    provider = OAuthClientProvider(
        server_url=server.server_url,
        client_metadata=OAuthClientMetadata(
            client_name="SAGE",
            redirect_uris=[AnyUrl(server.oauth_redirect_uri)],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
        ),
        storage=storage,
        redirect_handler=broker.redirect,
        callback_handler=broker.callback,
    )
    storage.bind_provider(provider)
    # Restore our encrypted absolute value before its lazy token initialization so an
    # expired access token is refreshed instead of sent and followed by OAuth
    credentials = decrypt_credentials(server)
    token_expiry = credentials.get(TOKEN_EXPIRY_KEY)
    if isinstance(token_expiry, (int, float)):
        provider.context.token_expiry_time = float(token_expiry)
    if metadata := credentials.get(OAUTH_METADATA_KEY):
        provider.context.oauth_metadata = OAuthMetadata.model_validate(metadata)
    server._oauth_provider = provider
    return provider


@asynccontextmanager
async def authenticated_mcp_client(session: SessionData, server: MCPServer) -> AsyncIterator[Client]:
    headers = _static_headers(server)
    auth = _oauth_provider(session, server) if server.auth_type in (MCPAuthType.AUTO, MCPAuthType.OAUTH2) else None
    timeout = httpx2.Timeout(30.0, read=300.0)
    async with httpx2.AsyncClient(
        headers=headers,
        auth=auth,
        follow_redirects=True,
        timeout=timeout,
    ) as http_client:
        transport = streamable_http_client(server.server_url, http_client=http_client)
        # Automatic negotiation prefers the modern discovery flow and falls
        # back to the legacy initialize handshake for older MCP servers.
        async with Client(transport, mode="auto") as client:
            yield client


def _settle_automatic_auth(server: MCPServer) -> None:
    if server.auth_type == MCPAuthType.AUTO:
        # Automatic mode is only used while installing registry entries
        # A successful OAuth challenge stores tokens through MCPTokenStorage
        credentials = decrypt_credentials(server)
        if credentials.get("tokens"):
            server.auth_type = MCPAuthType.OAUTH2
        elif credentials.get("headers"):
            server.auth_type = MCPAuthType.HEADERS
        else:
            server.auth_type = MCPAuthType.NONE
            server.encrypted_credentials = None
            server.credential_expires_at = None
        if server.auth_type != MCPAuthType.OAUTH2:
            server.oauth_redirect_uri = None
            server._oauth_provider = None


async def _list_tools(client: Client, stop_after: str | None = None) -> list[Any]:
    tools = []
    cursor = None
    seen_cursors = set()
    while True:
        page = await client.list_tools() if cursor is None else await client.list_tools(cursor=cursor)
        tools.extend(page.tools)
        if stop_after is not None and any(tool.name == stop_after for tool in page.tools):
            break
        cursor = page.next_cursor
        if not cursor:
            break
        if cursor in seen_cursors:
            raise RuntimeError("MCP server returned a repeated tools cursor.")
        seen_cursors.add(cursor)
    return tools


async def list_mcp_tools(session: SessionData, server: MCPServer) -> list[Any]:
    async with authenticated_mcp_client(session, server) as client:
        tools = await _list_tools(client)
    _settle_automatic_auth(server)
    return tools


async def call_mcp_tool(session: SessionData, server: MCPServer, name: str, arguments: dict[str, Any]):
    async with authenticated_mcp_client(session, server) as client:
        # Each invocation creates a fresh client. Listing through the requested
        # tool gives the v2 client the schema needed for modern x-mcp-header
        # parameters and result validation.
        await _list_tools(client, stop_after=name)
        result = await client.call_tool(name=name, arguments=arguments)
    return result
