## About

The OPACA LLM UI is a powerful chatbot that can fulfill user requests by calling actions from a connected OPACA platform. It consists of two parts: The actual UI / frontend, implemented in Javascript and Vue, and multiple "backends" connecting to an LLM API. The OPACA LLM UI does not include any specific actions but takes all its functionality from the connected OPACA platform.


## How do I use it?

1. Connect to an OPACA Runtime Platform.
2. Check the provided agents & actions or have a look at the sample queries.
3. Select the prompting method to use (e.g. Tool-LLM, Simple, ...) and check its configuration.
4. Try one of the sample queries or type your own question into the chat window.
5. Wait a few seconds for the LLM's response, inspect the debug-output for "behind the scenes" info, and ask follow-up questions.


## How does this work?

The architecture consists of a frontend (this UI) and a backend, providing an API to be called by the frontend. The backend provides several different prompting methods or interaction modes (see further below), each with their own strengths and weaknesses. Each of those have access to all the actions provided by the agents running on the connected OPACA platform.

The frontend includes different sidebars that can be expanded or collapsed, providing e.g. information on the available agents, sample queries, configuration for the different prompting methods, and detailed debug output. The message history and configuration is stored in the browser session, so multiple users can use the system in parallel.

For more detailed information, please visit the project's GitHub page (link at the bottom of this page).


## What happens with my data?

Your chat history is stored in the Backend and associated with you via a browser cookie. The cookie has a life-time of 30 days, which is renewed each time you make a request. Once the cookie expires, the chat histories will be removed from the backend. You can also at any time use the "Reset" function to clear your chat history. Note: If you delete the cookie from your browser, a new cookie will be issued and you lose the ability to Reset the old history (it will then be deleted when the old cookie expires).

You chat prompts are forwarded to the configured LLM (e.g. GPT, or some locally installed LLM), and may be in some way evaluated by the companies running those LLM. The OPACA-LLM itself (the Frontend and Backend) does in no way inspect or evaluate your chat prompts or the results other than what's necessary for e.g. invoking the respective tools and formatting the response.


## Other Frequently Asked Questions

**What is OPACA and why do I need to connect to it?**
OPACA is a frameworks combining multi-agent systems with container-technologies and microservices. OPACA enables the assistant to use tools. Without connecting, tool-based actions cannot be performed.

**What are tools/services and how do I know which are available?**
Each tool available to the LLM corresponds to an action provided by one of the agents running on the OPACA platform. They are loaded automatically when connecting to a backend. You can see which are available in the "Agents & Actions" tab.

**What is the difference between the interaction modes?**
* Simple: Using a simple prompt including the different available actions and querying the LLM in a loop, extracting the actions to call from the LLM's output.
* Tool-LLM: Two agents using the built-in 'tools' parameter of newer models, providing a good balance of speed/simplicity and functionality.
* Self-Orchestration: A two-staged approach, where an orchestrator delegates to several groups of worker agents, each responsible for different OPACA agents.
* Simple-Tools: A single agent, as in 'Simple', but using the 'tools' parameter.

**What prompts can I use and where can I learn more?**  
Use natural language to describe what you want. Check the Prompt Library for examples and templates. The LLM can help by calling the different tools provided by the agents on the OPACA platform, or with general questions.

**Can I use my own tools/services?**  
Yes. If you have the backend URL and credentials, you can deploy and register new AgentContainers with OPACA and use their actions as additional tools.


## Further Reading

* <a href="https://github.com/GT-ARC/opaca-llm-ui" target="_blank">OPACA-LLM on Github</a>
* <a href="https://github.com/GT-ARC/opaca-core" target="_blank">OPACA on Github</a>
* <a href="https://go-ki.org/" target="_blank">Go-KI Project</a>