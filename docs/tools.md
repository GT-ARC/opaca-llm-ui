# Tools

SAGE integrates three distinct tool types to give LLM agents access to data, files, and external systems. Regardless of their origin, all tools are normalized into standard OpenAI tool definitions so the model can interact with them uniformly.

Every tool passes through a centralized permission layer prior to execution.

## Approval Types

Each tool can be configured with one of three approval types:
- "allow": The tool executes automatically in the background without interrupting the chat flow.
- "ask": Pauses execution and prompts the user via the UI to approve or deny the action before it runs.
- "deny": Completely blocks the tool. SAGE filters these out during listing so the LLM is unaware of their existence.

## Internal Tools

- Built-in utilities implemented directly within the SAGE backend.
- Used for chat searches, task scheduling, and file handling.
- Default approval type is "allow".

## OPACA Tools

- Generated dynamically from OPACA agent tools on the fly when the agents are prompted.
- Default approval type is "allow".

## MCP Tools

- When an MCP server is added to SAGE, the backend scans all server tools, converts them into OpenAPI compatible tools and caches them in a session.
- Connections use the MCP Python SDK v2 in automatic mode. Modern servers are discovered without an `initialize` request; legacy servers automatically fall back to the existing initialize handshake.
- Default approval type for the tools can be set when adding the MCP server.
- Manual installation offers no authentication, OAuth 2.1, an API-key/token preset, and advanced HTTP headers. The token preset produces either a Bearer authorization header or a raw value in a selected header.
- Registry installations derive URL-variable and HTTP-header fields from the selected remote's registry metadata. If no OAuth token is available, the backend follows a standards-compliant OAuth challenge automatically; a public server falls back to no authentication. Only Streamable HTTP remotes are offered by the browser.
- MCP credentials are encrypted before they are attached to session data and are never exposed to the LLM or returned by the MCP API.
- Logged-in users retain encrypted MCP credentials and OAuth refresh tokens with their persistent authenticated session. Anonymous credentials remain available for at most 24 hours and are not written to the session database, so they are lost when the backend stops.
- Removing an MCP server also removes its locally stored credential material. To replace invalid credentials, remove and add the server again.
