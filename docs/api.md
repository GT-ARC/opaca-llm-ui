# API

The OPACA LLM provides a RESTful API for most requests, while also providing a websocket for streaming responses. The general functions OPACA LLM range from an automatic message generation, login functionalities to setting specific configurations. A detailed list of all available endpoints is listed below.

## RESTful API

### GET `/actions`

- Returns a dictionary of all the available actions that were returned by the OPACA platform. The key in the dictionary represents the agent's name with a list of all its provided services as the value.
- inputs: `None`
- outputs: `Dict[str, List[str]]`

### GET `/backends`

- Returns a dictionary containing the names of all available backends.
- inputs: `None`
- outputs: `List[str]`

### GET `/{backend}/config`

- Returns the current configuration for the selected backend.
- inputs: `backend` (The backend for which the configuration should be returned)
- outputs: `Dict[str, Any]`

### PUT `/{backend}/config`

- Updates the configuration for the selected backend. If this endpoint is used via the UI, the matching configuration for the selected backend is used. This endpoint requires an exact match of the configuration object to be provided.
- inputs: `backend` (The backend for which the configuration will be updated)
- body: `conf` (A JSON object containing the exact same configuration settings for the currently selected backend)
- outputs: `Dict[str, Any]`

### POST `/{backend}/config/reset`

- Resets the configuration for the currently selected backend to its default values.
- inputs: `backend` (The backend for which the configuration will be reste)
- outputs: `Dict[str, Any]`

### POST `/{backend}/query`

- The selected `backend` will generate an answer based on the given `Message` in the request body. Returns a `Response` object.
- inputs: `backend` (The name of the backend to generate a response)
- body: `Message`
- outputs: `Response`

### POST `/connect`

- Attempts to establish a connection to the given OPACA platform.
- inputs: `None`
- outputs: status code

### GET `/history`

- Returns a list of the full message history that is saved for a specific user
- inputs: `None`
- outputs: `List`

### POST `/reset`

- Resets the message history for the current user.
- inputs: `None`
- outputs: `None`

### POST `/reset_all`

- Resets the message history for **all** users.
- inputs: `None`
- outputs: `None`

## Websocket/Streaming

### `/{backend}/query_stream`

- Behaves similar to **POST** `/{backend}/query`, but instead establishes a websocket connection to stream the message generation to the connected client.
- inputs: `backend` (The backend which will generate and stream the message)
- expected incoming messages: `Message`
- stream outputs: `AgentMessage` & `Response`
