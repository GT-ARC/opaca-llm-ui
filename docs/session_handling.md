# Session Handling

To manage multiple users at the same time, the OPACA LLM uses session handling to track the current users and manage the generated messages accordingly. This is done by using a browser cookie called `session_id`.

Every time a client performs a request to the backend, the header of the HTTP request will be extracted and searched for the cookie named `session_id`. If it is the first time this specific browser has made a request to the backend, a new session id will be generated. The session id is a randomly generated UUID. Once generated, the session id is then saved in a local dictionary called `session` and is also set in the response header cookies. This way, the browser will use this cookie in all subsequent requests to the backend during the session. For reoccurring requests, the session id will automatically be located in the request cookies, which is then used to retrieve the current session. 

The `sessions` dictionary consists of the session ids, which are used as unique keys and [`SessionData`](models.md#sessiondata) objects as their values. In these [`SessionData`](models.md#sessiondata) objects, all relevant information regarding the unique session is saved.

Currently, all saved session data can be reset by either calling the endpoint `POST /reset_all` or by simply restarting the backend. Additionally, the saved message history within the `SessionData` can be reset my calling `POST /reset` or by clicking the reset button in the UI.