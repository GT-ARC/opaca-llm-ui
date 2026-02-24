# Backend API

SAGE provides a RESTful API for most requests, while also providing a websocket for streaming responses. The API is used internally for communication between Frontend and Backend. When SAGE is started, you can access all routes via FastAPI on `http://<host>:3001/docs`

#### General routes

* `GET /methods`: Returns a list of available LLM prompting methods.
* `GET /models`: Returns a list of supported LLM models.
* `POST /connect`: Attempts to establish a connection to the given OPACA platform.
* `POST /disconnect`: Severs the connection to the currently connected OPACA platform.
* `GET /actions`: Returns a dictionary of all the available actions that were returned by the OPACA platform. The key in the dictionary represents the agent's name with a list of all its provided services as the value.
* `POST /actions/invoke`: Allows to invoke an OPACA action directly from the UI.
* `GET /extra-ports`: Returns a dictionary of all the extra-ports provided by the Agent Containers currently running on the connected OPACA platform.
* `POST /stop`: Stop all generation currently in progress for the session.
* `POST /query/{method}`: Asks the selected prompting method to generate an answer based on the given user query. This is independent of any existing chat histories (see below).
* `POST /platform-info`: Returns a short summary of the currently connected OPACA platform and generates one if it does not exist yet.

#### Chat routes

* `GET /chats`: Returns a list of all chats associated with the current session, but without their full message histories.
* `GET /chats/{chat_id}`: Returns the full message history and other details for the given chat.
* `POST /chats/{chat_id}/query/{method}`: Makes a query to the given prompting method using a user query and the given chat's message history. The result is returned once, in full.
* `PUT /chats/{chat_id}`: Used to update a chat's displayed name.
* `DELETE /chats/{chat_id}`: Deletes the given chat.

#### Config routes

* `GET /config/{method}`: Get the configuration of that prompting method (e.g. the used model).
* `PUT /config/{method}`: Update the configuration of that prompting method (e.g. the used model).
* `DELETE /config/{method}`: Reset the configuration of that prompting method (e.g. the used model) to the default values.

#### MCP routes

* `GET /mcp`: Returns all available MCP tools for the current session.
* `POST /mcp`: Adds a new MCP endpoint and all its tools to the current session.
* `DELETE /mcp`: Deletes an MCP endpoint and removes its tools from the current session.

#### File routes

* `POST /files`: Add files to be taken into account with the next request.
* `GET /files`: Returns all uploaded files for the current session.
* `DELETE /files/{file_id}`: Deletes a file from the current session.
* `PATCH /files/{file_id}`: Toggle the inclusion of a file in the next request.
* `GET /files/{file_id}/view`: Serves a file for preview in the browser.

#### Sample Prompts routes

* `GET /prompts`: Returns the list of sample prompts for the current session.
* `POST /prompts`: Adds a new sample prompt to the current session.
* `DELETE /prompts`: Resets the sample prompts of the current session to the default ones.
* `GET /prompts/default`: Returns the default sample prompts.

#### Admin routes

The following routes can be used to administer all currently active sessions, including those of other users. They therefore require a password in the `X-Api-Password` header (see FastAPI UI for details), which can be set in the `SESSION_ADMIN_PWD` environment variable. (A more fine-grained inspection and manipulation of the sessions would be possible by directly accessing the DB, but these routes are more convenient in case there is e.g. some out-of-control scheduled task in another session.)

* `GET /admin/sessions`: Get an overview of current sessions, including chat-names (no full chats), uploaded files' names, scheduled tasks, etc.
* `PUT /admin/sessions/{session_id}/{action}`: Perform some action on the given session. Available actions are:
  * `DELETE`: Deletes the session.
  * `LOGOUT`: Logout of all logged-in containers and additional LLM hosts for this session.
  * `STOP_TASKS`: Stop/delete all Scheduled Tasks of this session.
  * `BLOCK`: Block this session, disallowing any future requests until unblocked.
  * `UNBLOCK`: Unblock the session.
* `POST /prompts/default`: Change the default sample prompts.

#### Websocket

* `/ws`: Establishes a permanent websocket connection to stream messages and notifications from the backend to the UI.