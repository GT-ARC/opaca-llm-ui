# Session Handling & Cookies

To manage multiple users at the same time, SAGE uses session handling to track the current users and manage the generated messages accordingly. This is done by using a browser cookie called `session_id`.

Every time a client performs a request to the backend, the header of the HTTP request will be extracted and searched for the cookie named `session_id`. If no session cookie exists, a new session ID will be generated. The session ID is a randomly generated UUID. Once generated, the session ID is then saved in a local dictionary called `session` and is also set in the response header cookies. This way, the browser will use this cookie in all subsequent requests to the backend, as long as the cookie exists. For reoccurring requests, the session id will automatically be located in the request cookies, which is then used to retrieve the current session.

The session ID cookie is stored persistently, so that the last chat session can be restored when the browser is restarted. In this case, the cookie will have a time to live of 30 days, which will be renewed with each request.

The `sessions` dictionary consists of the session IDs, which are used as unique keys and `SessionData` objects as their values. In these `SessionData` objects, all relevant information regarding the unique session is saved.

Currently, all saved session data can be reset by either calling the endpoint `POST /reset_all` or by simply restarting the backend. Additionally, individual chat histories can be deleted by calling the `DELETE /chats/{chat_id}` route or by clicking the delete button on a chat in the respective sidebar view.


## User Management

SAGE uses the user management provided by the OPACA platform. Please refer to [the docs there](https://github.com/GT-ARC/opaca-core/blob/main/doc/user-management.md) for details. Then connecting to an OPACA Runtime Platform (RP), SAGE will first try to login without authentication, and if that fails ask you for your OPACA User username and password. All following interactions with the OPACA RP will be carried out as this user (in order to be able to invoke actions, the user needs at last "USER" rights); if no auth is used, the default (admin) user will be used.

Besides the OPACA RP itself, individual Agent Containers (AC) may also require authentication, for instance for connecting to some external API, e.g. for e-mails. Again, please refer to the general OPACA documentation for any details. If SAGE tries to invoke an action and from the error response infers that login may be required, it automatically presents a login dialogue to the user, tries to login to the container with the given credentials, and retries the action. SAGE will later automatically logout of the container again after a time that can be determined by the user in the login dialogue.

Note that the user credentials given in the Container Login dialogue are at no point stored or logged, neither in SAGE nor in the OPACA RP, and in particular never sent to the LLM, but only to the respective OPACA Agent Container. What the agent container does with the credentials is beyond our control. Only provide your credentials to Agent Containers you trust!
