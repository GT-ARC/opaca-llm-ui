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

### File handling

File upload and conversation queries are separate requests. Selecting a PDF or image uploads it immediately to the SAGE backend. If a chat ID is supplied, the file also becomes active for that chat. Extractable PDF text is processed locally with YAKE to generate keywords; images currently have no generated keywords and are represented by their filenames until their contents are read by a vision-capable model. Text files are inserted into the user prompt by the frontend rather than uploaded.

The query's `file_ids` field identifies files attached to that specific user request. This preserves the meaning of references such as "this file", but does not send full file contents to the LLM. Provider upload happens lazily when `AskFiles` reads selected active files, and the resulting provider IDs are cached per provider, purpose, and API key.

The file sets have the following relationship:

TODO: Add venn diagram

- **Uploaded files** are all files stored in the current session.
- **Active files** are the files that tools are permitted to read in one chat. They are a subset of uploaded files.
- **Current files** are the active, uploaded IDs included with the current query. They are a subset of active files and are not persisted as a separate set.
- **Relevant files** are selected per query from all uploaded filenames and keywords. They may be active or inactive and are not stored after selection.

Internal file tools keep metadata selection separate from full-content access:

- `GetFileKeywords` returns filenames, keywords, active status, and current-request status without another LLM call.
- `FindRelevantFiles` uses an LLM to select relevant files from the same metadata, including inactive files.
- `SetActiveFiles` replaces the chat's active file working set and can require user approval.
- `AskFiles` sends selected active files to a supporting model and answers from their full contents.

## OPACA Tools

- Generated dynamically from OPACA agent tools on the fly when the agents are prompted.
- Default approval type is "allow".

## MCP Tools

- When an MCP server is added to SAGE, the backend scans all server tools, converts them into OpenAPI compatible tools and caches them in a session.
- Default approval type for the tools can be set when adding the MCP server.
