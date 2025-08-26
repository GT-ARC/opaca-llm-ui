# Session Handling & Cookies

To manage multiple users at the same time, the OPACA LLM uses session handling to track the current users and manage the generated messages accordingly. This is done by using a browser cookie called `session_id`.

Every time a client performs a request to the backend, the header of the HTTP request will be extracted and searched for the cookie named `session_id`. If no session cookie exists, a new session ID will be generated. The session ID is a randomly generated UUID. Once generated, the session ID is then saved in a local dictionary called `session` and is also set in the response header cookies. This way, the browser will use this cookie in all subsequent requests to the backend, as long as the cookie exists. For reoccurring requests, the session id will automatically be located in the request cookies, which is then used to retrieve the current session.

The session ID cookie is stored persistently, so that the last chat session can be restored when the browser is restarted. In this case, the cookie will have a time to live of 30 days, which will be renewed with each request.

The `sessions` dictionary consists of the session IDs, which are used as unique keys and `SessionData` objects as their values. In these `SessionData` objects, all relevant information regarding the unique session is saved.

Currently, all saved session data can be reset by either calling the endpoint `POST /reset_all` or by simply restarting the backend. Additionally, the saved message history within the `SessionData` can be reset my calling `POST /reset` or by clicking the reset button in the UI.
