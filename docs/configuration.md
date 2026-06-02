# Configuration

Following is an overview of all environment variables that can be set in the [docker-compose.yml](../docker-compose.yml).

## Frontend

Frontend env-vars correspond to settings in `config.ts`; check there for context and default values. Env vars have to start with `VITE_` so they are evaluated when the app is started (i.e. taking values defined on the host system). The most important of those are:

* `VITE_BACKEND_URL`: The URL where to find the backend; defaults to `localhost`, which works for testing, but should be replaced with actual IP for deployment to prevent problems with CORS
* `VITE_METHOD`: The prompting method to use, see options in `config.ts`
* `VITE_BACKLINK`: Optional 'back' link to be shown in the top-left corner.
* `VITE_PLATFORM_URL`: The URL where to find the OPACA platform
* `VITE_AUTOCONNECT`: Whether to automatically connect to the given OPACA URL on load; only if no auth is required.
* `VITE_ALLOW_CONTAINER_MANAGEMENT`: Whether to enable the buttons for starting and stopping OPACA containers from within SAGE, provided the user has sufficient privileges.
* `VITE_COLOR_SCHEME`: The color scheme, can be "light", "dark", or "system".
* `VITE_LANGUAGE`: The language to use by default in the UI. Possible options: "GB" (english), "DE" (german).

The other settings found in `config.js` can also be given as Environment variables, but may be less relevant. The name of the env-var is derived from the name of the config parameter by converting to `UPPER_SNAKE_CASE` and prepending `VITE_`, e.g. `VITE_REGISTRY_URL` for `registryUrl`. Similarly, all the config settings can be passed as query parameters, e.g. as `?autoconnect=true&method=simple`. Finally, each of those values is automatically stored in and read from a session cookie.

The resolution order for the config settings is as follows:

* If the setting is given in a query parameter in the URL, use that.
* Else, use the value from the Cookie (i.e. from the previous session), if set.
* Else, use the value from the corresponding `VITE_` environment variable.
* Else, use the default value defined in `config.ts`.


## Backend

* `LLM_HOSTS`: Semicolon-separated list of LLM server hosts/providers, e.g. `openai`, `gemini`, `anthropic`, `mistral`, `<custom-base-url>`, etc.
* `LLM_API_KEYS`: Semicolon-separated list of API-keys for each of the above hosts; default is `""` (for common providers, the API Key is taken from the default api key field, e.g., for `openai` from `OPENAI_API_KEY`, for `gemini` from `GEMINI_API_KEY`, etc. but can be overwritten here if a non-default key is explicitly provided).
* `LLM_MODELS`: Semicolon-separated list of comma-separated lists of supported models for each of the above hosts.
* `CORS_WHITELIST`: Semicolon-separated list of allowed referrers; this is important for CORS; defaults to `http://localhost:5173`, but for deployment should be actual IP and port of the frontend (and any other valid referrers).
* `MONGODB_URI`: The full URI, including username and password, to the MongoDB used for storing the session data. If left empty, sessions are stored in memory only.
* `SESSION_ADMIN_PWD`: password needed to call any of the `/admin/...` routes.

## Session-DB

* `MONGO_INITDB_ROOT_USERNAME`: Username for the MongoDB root user.
* `MONGO_INITDB_ROOT_PASSWORD`: Password for the MongoDB root user.

## OPACA-Platform

An extended documentation of the environment variables of the OPACA platform can be found [here](https://github.com/GT-ARC/opaca-core?tab=readme-ov-file#environment-variables-runtime-platform). Please note that due to simplicity, not all available environment variables are used in the [docker-compose.yml](../docker-compose.yml)
