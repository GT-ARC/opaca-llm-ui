# OPACA LLM UI

Copyright 2023-2024 GT-ARC & DAI-Labor, TU Berlin

* Main Contributors: Robert Strehlow, Tobias Küster
* Further contributions by: Oskar Kupke, Benjamin Acar, Abdullah Kiwan

This (https://github.com/gt-arc/opaca-llm-ui/) is the public repository of the OPACA LLM UI project. Feel free to create issues if you have any suggestions, or improve things yourself with a fork and pull request. The main development work still happens in the internal/private repository at https://gitlab.dai-labor.de, including most (internal) tickets, development branches, merge requests, build pipelines, etc.


## TODO: review, update and extend readme
* explain repository structure
* explain UI functionality
* include a screenshot
* explain backend functionality, different clients (just in brief, not as detailed as in the paper)
* pay attribution to rest-gpt



A powerful chatbot which fulfills user requests by calling actions from a connected OPACA platform. The chatbot currently supports **ChatGPT** (gpt-4o & gpt-4o-mini) by OpenAI and **Llama-3** (llama3.1:70b) by Meta. There are currently three approaches to solve user queries:
* Simple: First generates a plan consisting of API calls and then asks for confirmation by the user to execute it
* RestGPT: Uses 4 agents (Planner, Action Selector, Caller, Evaluator) in a chain to automatically fulfill user queries
* ToolLLM: Uses the built-in function of OpenAI models "tools" to generate and executes requests (**ChatGPT** only)

The Web-UI in this project is based on the LLM-Chat feature of the [ZEKI Wayfinding](https://gitlab.dai-labor.de/smart-space/wayfindingzeki) by Tobias Schulz, but has since been significantly extended and refactored.


## Quickstart

### 1. Start the Opaca Platform

* Follow the **Getting Started** Guide in the opaca repository https://gitlab.dai-labor.de/jiacpp/prototype/#getting-started-quick-testing-guide

### 2. Deploy a demo-service container

**Local Container**

* Clone the demo-services repository https://gitlab.dai-labor.de/zeki-bmas/tp-framework/demo-services
* Navigate to the root directory of the project and run `mvn install`
* Then build the docker container by running `docker build -t demo-services .`
* Now deploy the image to the Opaca platform at http://localhost:8000/swagger-ui/index.html#/containers/addContainer with `{"image": {"imageName": "demo-services"}}`

**From Docker Hub**

* Deploy a compatible container from Docker Hub: `{"image": {"imageName": "rkader2811/smart-office"}}`

### 3. Start the Opaca-LLM 

* First, run `npm install` in the root directory to install all dependencies
* To start all components, run `npm run dev_all` in the root directory, then go to http://localhost:5173/
* To use OpenAI models, set your api-key in your environment variables or paste your key in the input box in the Web-UI
* If the platform requires authentication, enter a valid username and password and click "Connect". If the authentication was successful, a speech bubble saying "connected" should appear.

### What to do and what to expect?

* Start the app as described above
* The default prompt will be "Which services do you know?". After pressing enter -> the AI should respond with a list of services that are available through the connected Opaca platform
* Ask for help with developing something that might involve those services (or something completely unrelated), for example "What does the service ExampleServiceABC do?" -> if the service includes a description, the AI will create a summary of that description. You can also ask about parameters that are required to call the service
* Try to get the AI to call a service to fulfill your query by asking for information or services that can only be solved by calling actions from the connected Opaca platform.
* (If you use the "Simpel" method you need to write "do it" upon receiving a proposed action plan to actually call the actions)

### Debug View

Upon enabling the debug view in the Web-UI, more detailed information about each LLM-agent will be shown when interacting with the chatbot.

Here is an overview of each LLM-agent of the RestGPT method:
* **Planner**: Responsible for dividing a task into smaller substasks if necessary. Also handles questions about services or unrelated questions that can be answered without calling actions.
* **API Selector**: Based on the output of the **Planner**, selects a suitable action and generates parameters if necessary.
* **Caller**: Parses the output of the **API Selector**, calls the connected Opaca platform to invoke the specified action and finally evaluates with call stack to give a short summary in natural language
* **Evaluator**: Evaluates the complete plan history and determines if the user query has been fulfilled. If it has -> generate an answer that will be shown to the user including the achieved results, if it has not -> start over at the **Planner**

### Frontend (JS, Vue, Port 5173)

* Based on the Chat component of ZEKI Wayfinding, but heavily modified since then
* Main interaction is via a Chat prompt; input is sent to the backend, then the response of the AI is shown in the chat box
* Alternative interactions via speech recognition

### Backend (Python, FastAPI, Port 3001)

* One uniform backend with different implementations (e.g. different ways of selecting which action to execute), each taking care of their own prompts, history, etc.
* the backend can be selected in the frontend or configuration (t.b.d.; if in frontend, this should reset the chat)
* for testing, the backend can also be tested in isolation using the FastAPI web UI at http://localhost:3001/docs
