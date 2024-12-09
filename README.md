# OPACA LLM UI

Copyright 2024 GT-ARC & DAI-Labor, TU Berlin

* Main Contributors: Robert Strehlow, Tobias Küster
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

* ToolLLM: Also using LangChain, but with just two agents, and using the built-in "tools" parameter of OpenAI models. A similar version for LLAMA is currently in progress.

The different LLM clients provide additional configuration parameters, e.g. for the model version to use, and most support both **GPT** (gpt-4o & gpt-4o-mini) by OpenAI and **Llama-3** (llama3.1:70b) by Meta.

### Sessions, Message History and Configuration

The message history and configuration (model version, temperature, etc.) is stored in the backend, along with a session ID, associating it with a specific browser/user. The history is shared between different LLM backends, i.e. if the performance of once backend is not satisfactory, one can switch to another one and continue the same conversation. Also, the LLM will "remember" the past messages when revisiting the site later, or opening a second tab in the same browser, even though the chat window appears empty. Clicking on the "Reset" button (lower right, red) will reset the message history, but not the configuration.

The Session ID is stored as a Cookie in the frontend and sent to the backend. On the first request, when no Cookie is set, the backend will create a new random Session ID and associated session data and set the Session ID as a Cookie in the response. It will then automatically be used by the frontend in all subsequent requests.


## Environment Variables

### Frontend

Frontend env-vars correspond to settings in `config.js`; check there for context and default values. Env vars have to start with `VITE_` so they are evaluated when the app is started (i.e. taking values defined on the host system).

* `VITE_PLATFORM_BASE_URL`: The default URL where to find the OPACA platform
* `VITE_BACKEND_BASE_URL`: The URL where to find the backend
* `VITE_BACKEND_DEFAULT`: The default backend to use, see options in `config.js`
* `VITE_SHOW_KEYBOARD`: Whether to show a virtual keyboard.
* `VITE_SHOW_APIKEY`: Whether to show an input field for the OpenAI API key in the UI

### Backend

* `OPENAI_API_KEY`: OpenAI API key needed to use GPT models; go to [their website](https://platform.openai.com) to get one.


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
