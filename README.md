# OPACA LLM UI

Copyright 2024 GT-ARC & DAI-Labor, TU Berlin

* Main Contributors: Robert Strehlow, Daniel Wetzel, Tobias Küster
* Further contributions by: Oskar Kupke, Abdullah Kiwan, Benjamin Acar

Part of the code in this repository is based on [RestGPT](https://github.com/Yifan-Song793/RestGPT).

This (https://github.com/gt-arc/opaca-llm-ui/) is the public repository of the OPACA LLM UI project. Feel free to create issues if you have any suggestions, or improve things yourself with a fork and pull request. The main development work still happens in the internal/private repository at https://gitlab.dai-labor.de, including most (internal) tickets, development branches, merge requests, build pipelines, etc.

This repository includes software developed in the course of the project "Offenes Innovationslabor KI zur Förderung gemeinwohlorientierter KI-Anwendungen" (aka Go-KI, https://go-ki.org/) funded by the German Federal Ministry of Labour and Social Affairs (BMAS) under the funding reference number DKI.00.00032.21.


## About

The OPACA LLM UI is a powerful chatbot that can fulfill user requests by calling actions from a connected OPACA platform. It consists of two parts: The actual UI / frontend, implemented in Javascript and Vue, and multiple "backends" connecting to an LLM API. The OPACA LLM UI does not include any specific actions but takes all its functionality from the connected OPACA platform.

![OPACA LLM UI Screenshot](resources/opaca-llm-ui.png)


### Frontend

The web UI is implemented in Javascript using Node and Vue. It consists of several components:

* A main chat window, showing the messages in the current interaction and an input field for submitting messages. The LLM's output is interpreted and formatted as Markdown, allowing for text formatting, code snippets, and embedded images (the LLM itself an not generate images, but it can display images if e.g. the URL to an image was returned from an action). The UI also allows for speech input and output (if the last message was spoken, the response will automatically be read out aloud). Each response by the LLM includes additional "debug" output that can be expanded.

* A collapsible sidebar providing different sections for configuring the OPACA Runtime Platform to connect to, browsing the list of available agents and actions, configuring details of the used LLM Backend, and showing additional debug output.

* A Navigation/Header bar, allowing to switch the UI language and the used LLM Backend.

Several aspects of the UI, such as the available and default backends, the selection of sample prompts, or the language can be configured in `config.js`.

The Web-UI in this project was originally based on the LLM-Chat feature of the [ZEKI Wayfinding](https://gitlab.dai-labor.de/smart-space/wayfindingzeki) by Tobias Schulz, but has since been significantly extended and refactored.

### Backend

The backend consists of a general part, providing a simple HTTP API to be used by the frontend for calling the LLM functions (also providing a simple FastAPI UI, useful for testing), and a client for connecting to a specific OPACA runtime platform for retrieving and calling the available agent actions, and several alternative approaches to actually querying the LLM and extracting the agent actions to be executed: 

* Simple: Using a simple prompt including the different available actions and querying the LLM in a loop, extracting the actions to call from the LLM's output.

* RestGPT: Based on [RestGPT](https://github.com/Yifan-Song793/RestGPT); using LangChain with four agents (Planner, Action Selector, Caller, Evaluator) to determine what to do, which actions to call, and evaluate the result.

* ToolLLM: Also using LangChain, but with just two agents, and using the built-in "tools" parameter of newer models.

* Orchestration: A two-staged approach, were an orchestrator delegates to several groups of worker agents, each responsible for different OPACA agents.

The different approaches provide additional configuration parameters, e.g. for the model version to use, and most support both **GPT** (gpt-4o & gpt-4o-mini) by OpenAI and **vLLM** to use locally deployed models (e.g. Mistral, Llama, ...)


### Sessions, Message History and Configuration

The message history and configuration (model version, temperature, etc.) is stored in the backend, along with a session ID, associating it with a specific browser/user. The history is shared between different LLM backends, i.e. if the performance of once backend is not satisfactory, one can switch to another one and continue the same conversation. Also, the LLM will "remember" the past messages when revisiting the site later, or opening a second tab in the same browser, even though the chat window appears empty. Clicking on the "Reset" button (lower right, red) will reset the message history, but not the configuration. To reset the configuration, a user can click the "Reset to Default" button in the configuration view, which resets the configuration for the currently selected backend to its default values.

The Session ID is stored as a Cookie in the frontend and sent to the backend. On the first request, when no Cookie is set, the backend will create a new random Session ID and associated session data and set the Session ID as a Cookie in the response. It will then automatically be used by the frontend in all subsequent requests until the session is terminated. A session ends when the browser window is closed.

![Tool LLM Message Handling](resources/Tool-LLM-Messages.png)

The message handling of the OPACA LLM is illustrated in the image above. During a request, only the initial message query which was entered by the user in the UI is sent to the backend. Upon retrieval, the session ID associated with that user is used to fetch the individual message history. It consists of message pairs, linking a user query to the final output of the OPACA LLM. These message pairs are the exact messages displayed in the UI (excluding the "welcome" message). Combined with the current user query, all messages are sent to the OPACA LLM to generate an answer. In the case of the Tool LLM method, only the Tool Generator agent needs the complete message history. The Tool Evaluator agent only requires the current query and the internal message history. The internal messages are the generated outputs of both agents, used as inputs for the next agent. The final answer generated by the OPACA LLM is then added with the current query as a message pair to the message history in the backend, associated with the session ID.

### Speech Input and Output

The chatbot-UI supports speech-to-text (STT) using the Whisper model. A server with accordant API routes is included in this project under `Backend/tts-server`, and can be included in the setup, or started elsewhere. The STT server is optional; if it is not running, or no URL provided, the STT feature will not be available.


## Configuration and Parameters

The OPACA LLM can be configured in various ways using the `config.js` file in the Frontend directory. Here, you can configure, among others, the default OPACA Platform to connect to, which sample questions to show, which backend options to show, as well as some UI settings. Some of those settings can also be configured using Environment Variables (see next section), while others can be overwritten using Query parameters (i.e. appending `?abc=foo&xyz=bar` to the request URL):

* `autoconnect`: If true, attempt to automatically connect to the default OPACA Platform (without authentication)
* `sidebar`: Which tab of the sidebar to show after connecting; possible options: `none` (hide), `connect` (stay on connect page), `questions` (sample questions), `agents` (agents and actions), `config` and `debug`.
* `samples`: Which category of sample questions to show; possible options see "headers" in the `sidebarQuestions` section in the config (special characters might have to be URL-encoded), plus `random` for a random selection.


## Environment Variables

### Frontend

Frontend env-vars correspond to settings in `config.js`; check there for context and default values. Env vars have to start with `VITE_` so they are evaluated when the app is started (i.e. taking values defined on the host system).

* `VITE_PLATFORM_BASE_URL`: The default URL where to find the OPACA platform
* `VITE_BACKEND_BASE_URL`: The URL where to find the backend
* `VITE_BACKEND_DEFAULT`: The default backend to use, see options in `config.js`
* `VITE_BACKLINK`: Optional 'back' link to be shown in the top-left corner.
* `VITE_SHOW_KEYBOARD`: Whether to show a virtual keyboard.
* `VITE_SHOW_APIKEY`: Whether to show an input field for the OpenAI API key in the UI
* `VITE_VOICE_SERVER_URL`: Where to find the TTS-server; this is optional, but if missing, speech-input is not available.

### Backend

* `OPENAI_API_KEY`: OpenAI API key needed to use GPT models; go to [their website](https://platform.openai.com) to get one.
* `VLLM_BASE_URL`: Alternatively to using OpenAI, location of vLLM API to use (e.g. for LLAMA and other models).
* `VLLM_API_KEY`: API key for the vLLM API, if any.
* `FRONTEND_BASE_URL`: The URL of the frontend, analogous to `VITE_BACKEND_BASE_URL` (may be needed for CORS; defaults to localhost)


## Getting Started

### Using Docker Compose

To build and start the OPACA LLM UI, simply run the Docker Compose: `docker compose up --build`. You can then find the Frontend at `http://localhost:5173` and the backend (FastAPI) at `http://localhost:3001/docs`. Specify the OPACA Platform to connect to (including login credentials, if authentication is enabled) and hit the "Connect" button. The UI should automatically switch to the view showing the available actions, and you can start interacting with the LLM via the chat window.

### Development and testing

For testing and development, you might want to run your own OPACA Platform and example containers.

1. Start the OPACA Platform

   * Clone the [OPACA-Core Repository](https://github.com/GT-ARC/opaca-core) and follow the **Getting Started** guide to build and launch an OPACA runtime platform.

2. Deploy a container for testing
   * Create and build a sample OPACA Agent Container following the same guide. You can use the `sample-container`, but it's actions are mostly meant for unit-testing and don't do anything really useful.
    * Alternatively, a Smart-Office themed example container is available from Docker Hub as `rkader2811/smart-office`
    * Use the OPACA Platform's `POST /containers` route to deploy the container

3. Start the Opaca-LLM

   * In the Backend directory, run `pip3 install -r requirements.txt` and then `python3 -m src.server` to start the backend server.
   * In the Frontend directory, run `npm install` followed by `npm run dev` to run the frontend / web-UI; other than using Docker Compose, this allows for hot code replace while the application is running.
   * Alternatively, run `npm run dev_all` to start both, the backend and the frontend in parallel.

Then, as above, go to `http://localhost:5173`, connect to the OPACA platform and start interacting with the LLM.


## Performance Testing

The different backend methods of the OPACA-LLM have been tested within a designated testing environment. Two different questions sets have been created, to test the answer quality of our implemented methods. The first question set, labeled _simple_, contains questions that would only lead to the invocation of exactly one OPACA action. The question set labeled _complex_ contains questions which would result in numerous OPACA action invocations in one or more internal iterations. To evaluate the answer generated by the OPACA-LLM, each question in both question sets includes an expected answer. The actual response by the OPACA-LLM and the expected answer are then compared by a Judge-LLM using _gpt-4o_. A response can either be "helpful" if the answer fulfills every expectation, or "unhelpful" if information is missing or wrong information is being presented.

To run the tests/benchmark, simply execute the `test.py` script in the `test` directory. The script expects a number of parameters, which are explained with the `-h` parameter. The test script will automatically start an OPACA platform and OPACA LLM instance (backend only) using docker-compose and deploy a number of publicly hosted test containers. The result is then written to JSON file in the `test_runs` directory.

**Note:** The script will try to determine your IP address (in your local network, but _not_ 127.0.0.1), which is needed by the OPACA platform to communicate with its containers. This may not work on all systems. Alternatively, you can provide the URL of the OPACA platform (e.g. using `ifconfig` on your system), including protocol and port, using the `-o` parameter.

For example, a call to the test script my look like this (substitute the backend and model to use, as well as your IP if necessary):

```
python3 test.py -s simple -b simple -m gpt-4o-mini -o http://192.168.178.24:8000
```

Following is an overview of the latest results. It presents the amount of questions in a question set that were deemed "helpful" by the Judge-LLM. The method is given with the model that was used for all agents within that model. The only exception being the _orchestration-method_, which can uses different models for the Orchestrator Agent and Worker Agent.

| Method (model)                                                  | _simple_ (_time_)   | _complex_ (_time_) |
|-----------------------------------------------------------------|---------------------|--------------------|
| Tool-Method (gpt-4o)                                            | **22/24** (158.27s) | 16/23 (418.36s)    |
| Tool-Method (gpt-4o-mini)                                       | **22/24** (141.32s) | 12/23 (431.8s)     |
| Tool-Method (Mistral-Small-Instruct)                            | 18/24 (189.02s)     | 13/23 (375.52s)    |
| Orchestration-Method (Qwen25_32B_INT4 & Mistral-Small-Instruct) | **22/24** (202.23s) | 16/23 (764.45s)    |
| Rest-Gpt (gpt-4o-mini)                                          | 13/24 (120.77s)     | 9/23   (343.75s)   |
| Simple (gpt-4o-mini)                                            | 16/24 (n/a)         | **18/23** (n/a)    |

Please keep in mind, these results are only preliminary and the quality of each question has been measured by another LLM (gpt-4o). Therefore, the performance overview only provides a rough estimate of the actual performance of each method.
