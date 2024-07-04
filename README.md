# Opaca-LLM

A powerful chatbot which fulfills user requests by calling actions from a connected OPACA platform. The chatbot currently supports **ChatGPT** by OpenAI and **Llama-3** by Meta. Both employ different strategies to solve user queries. This project is based on https://gitlab.dai-labor.de/308201/.

## Quickstart

### 1. Start the Opaca Platform

* Follow the **Getting Started** Guide in the opaca repository https://gitlab.dai-labor.de/jiacpp/prototype/#getting-started-quick-testing-guide

### 2. Deploy a demo-service container

* Clone the demo-services repository https://gitlab.dai-labor.de/zeki-bmas/tp-framework/demo-services
* Navigate to the root directory of the project and run `mvn install`
* Then build a docker container by running `docker build -t demo-services .`
* Now deploy the image to the Opaca platform at http://localhost:8000/swagger-ui/index.html#/containers/addContainer with `{"image": {"imageName": "demo-services"}}`

### 3. Start the Opaca-LLM 

* First, run `npm install` in both the root and Backend directories
* To start, run `npm run dev_all` in the repo root directory, then go to http://localhost:5173/
* You might need to define the api-key in the file `Backend/OpenAI/openai_routes.py, line 28` by initializing `self.client = openai.OpenAI(api_key={your_api_key})`. If you are not planning on using the OpenAI model, you can use a random string as your api-key
* If the platform requires authentication, enter a valid username and password and click "Connect". If the authentication was successful, a speech bubble saying "connected" should appear.

### What to do and what to expect?

* Start the app as described above
* The default prompt will be "Which services do you know?". After pressing enter -> the AI should respond with a list of services that are available through the connected Opaca platform
* Ask for help with developing something that might involve those services (or something completely unrelated), for example "What does the service ExampleServiceABC do?" -> if the service includes a description, the AI will create a summary of that description. You can also ask about parameters that are required to call the service
* Try to get the AI to call a service to fulfill your query by asking for information or services that can only be solved by calling actions from the connected Opaca platform.
* (If you use the OpenAI model you need to write "do it" upon receiving a proposed action plan to actually call the actions)

### Debug View (Only for Llama-3)

Upon clicking the **Debug** button to the left of the chat window, a debug window will appear. Alongside the usual response in the chat window, more detailed information about each LLM-agent will be shown in the debug window.
Here is quick overview of each LLM-agent
* **Planner**: Responsible for dividing a task into smaller substasks if necessary. Also handles questions about services or unrelated questions that can be answered without calling actions.
* **API Selector**: Based on the output of the **Planner**, selects a suitable action and generates parameters if necessary.
* **Caller**: Parses the output of the **API Selector**, calls the connected Opaca platform to invoke the specified action and finally evaluates with call stack to give a short summary in natural language
* **Evaluator**: Evaluates the complete plan history and determines if the user query has been fulfilled. If it has -> generate an answer that will be shown to the user including the achieved results, if it has not -> start over at the **Planner**

### Frontend (JS, Vue, Port 5173)

* Based on the Chat component of ZEKI Wayfinding, but heavily modified since then
* Main interaction is via a Chat prompt; input is sent to the backend, then the response of the AI is shown in the chat box
* Alternative interactions via a virtual keyboard (has to be enabled in config) or speech recognition

### Backend (Python, FastAPI, Port 3001)

* One uniform backend with different implementations (e.g. different ways of selecting which action to execute), each taking care of their own prompts, history, etc.
* the backend can be selected in the frontend or configuration (t.b.d.; if in frontend, this should reset the chat)
* for testing, the backend can also be tested in isolation using the FastAPI web UI at http://localhost:3001/docs
