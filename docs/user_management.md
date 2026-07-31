# User Management

## Anonymous Sessions

To manage multiple users at the same time, SAGE uses session handling to track the current users and manage the generated messages accordingly. This is done by using a browser cookie called `session_id`.

Every time a client performs a request to the backend, the header of the HTTP request will be extracted and searched for the cookie named `session_id`. If no session cookie exists, a new session ID will be generated. The session ID is a randomly generated UUID. Once generated, the session ID is then saved in a local dictionary called `session` and is also set in the response header cookies. This way, the browser will use this cookie in all subsequent requests to the backend, as long as the cookie exists. For reoccurring requests, the session id will automatically be located in the request cookies, which is then used to retrieve the current session.

The session ID cookie is stored persistently, so that the last chat session can be restored when the browser is restarted. In this case, the cookie will have a time to live of 30 days, which will be renewed with each request.

The `sessions` dictionary consists of the session IDs, which are used as unique keys and `SessionData` objects as their values. In these `SessionData` objects, all relevant information regarding the unique session is saved.

Currently, all saved session data can be reset by resetting the DB volume (or by simply restarting the backend if no DB is used). Additionally, individual chat histories can be deleted by calling the `DELETE /chats/{chat_id}` (one chat) or `DELETE /chats` (all chats) route or by clicking the delete buttons in the respective sidebar view.

## Authenticated User Sessions

Users can optionally authenticate themselves by creating an account. This is done by using the [Auth0](https://auth0.com/) platform. After a successful first login, the current anonymous session is used to create a new user session, which is then linked to a unique user. All following requests are then validated by the token in the `Authorization` Header. This makes user data available across different browsers or devices. Authenticated user sessions are only available within a _localhost_ or _HTTPS_ environment. Authenticated user sessions have no expiration date and are never deleted. Each session can only be associated with one user. Sessions cannot change the user once it has been assigned to a user.

Enabling authenticated user sessions requires you to [set up an Auth0 Tenant](https://auth0.com/docs/get-started/auth0-overview/create-tenants). Afterward, follow this [Auth0 Quickstart Guide](https://auth0.com/docs/get-started/auth0-overview/create-applications/single-page-web-apps) to create a Single-Page-Application (SPA). With those components created, you should have the `VITE_AUTH_DOMAIN` from your tenant and `VITE_AUTH_CLIENT_ID` from your SPA available to use as environment variables in your `.env` file. Finally, in your Auth0 Dashboard, go to your SPA and click the Tab "API Access"; If an API already exists, you can use its URL as your `VITE_AUTH_AUDIENCE`. If no such API exists, go to **Applications > APIs** and create a new one. 

By default, authenticated user sessions are turned off. To turn them on, set the following environment variables in your `.env` file:

- `VITE_AUTH_ENABLED`: Whether authentication should be enabled or not. Can be `true` or `false`. Defaults to `false`.
- `VITE_AUTH_DOMAIN`: The Auth0 domain that can be retrieved from the application page. (e.g. `<your-project-name>.eu.auth0.com`)
- `VITE_AUTH_CLIENT_ID`: The Client id, can also be retrieved from the application page. (e.g. `12345678901234567890123456789012`)
- `VITE_AUTH_AUDIENCE`: The Audience is defined by the API in your Auth0 tenant. (e.g. `https://<your-project-name>/api/v1/`)

## OPACA Platform User Management

When SAGE is interacting with an OPACA platform, it uses the user management provided by the OPACA platform in addition to its own user authentication described in [Authenticated User Sessions](user_management.md#authenticated-user-sessions). Please refer to [the docs there](https://github.com/GT-ARC/opaca-core/blob/main/doc/user-management.md) for details. Then connecting to an OPACA Runtime Platform (RP), SAGE will first try to login without authentication, and if that fails ask you for your OPACA User username and password. All following interactions with the OPACA RP will be carried out as this user (in order to be able to invoke actions, the user needs at last "USER" rights); if no auth is used, the default (admin) user will be used.

Besides the OPACA RP itself, individual Agent Containers (AC) may also require authentication, for instance for connecting to some external API, e.g. for e-mails. Again, please refer to the general OPACA documentation for any details. If SAGE tries to invoke an action and from the error response infers that login may be required, it automatically presents a login dialogue to the user, tries to login to the container with the given credentials, and retries the action. SAGE will later automatically logout of the container again after a time that can be determined by the user in the login dialogue.

Note that the user credentials given in the Container Login dialogue are at no point stored or logged, neither in SAGE nor in the OPACA RP, and in particular never sent to the LLM, but only to the respective OPACA Agent Container. What the agent container does with the credentials is beyond our control. Only provide your credentials to Agent Containers you trust!

## Admin Access

While each user has some control over their own session, other users' sessions can be controlled via the `/admin/...` routes, e.g. in case of an out-of-control Scheduled Tasks or other unwanted activity or security concerns. There routes are therefore password-protected. The password can be set with the `SESSION_ADMIN_PWD` environment variable.
