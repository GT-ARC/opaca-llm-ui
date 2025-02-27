# User Interface

![OPACA LLM UI Screenshot](img/opaca-llm-ui.png)

The web UI is implemented in Javascript using Node and Vue. 

## Main Chat Window

The main chat window shows the messages in the current interaction and an input field for submitting messages. The LLM's output is interpreted and formatted as Markdown, allowing for text formatting, code snippets, and embedded images (the LLM itself an not generate images, but it can display images if e.g. the URL to an image was returned from an action). Initially, the chat window shows a selection of example prompts that can be used.

Below the chat output is the input prompt. Clicking on the "send" button or pressing Enter will submit the query to the LLM. The UI also allows for speech input and output using the microphone button. If the last message was spoken, the response will automatically be read out aloud. Finally, the "reset" button can be used to clear the chat history. Note that the full history is stored in a Session Cookie and may include more messages than what's shown in the current chat view.

Each response by the LLM includes additional "debug" output that can be expanded by clicking on the "debug" button below the message. Also, the messages can be read aloud using text-to-speech by clicking another button. Before the LLM's final response is ready, the "thinking process" is streamed to the UI (this may vary depending on the backend method being used).

## Sidebar

A collapsible sidebar providing different sections for configuring the OPACA Runtime Platform to connect to, browsing the list of available agents and actions, configuring details of the used LLM Backend, and showing additional debug output.

* **Connection**: Used to connect to an OPACA Runtime Platform, including authentication, if necessary. Note that if the OPACA LLM is running in Docker-Compose, you will have to provide your own IP address here (e.g. taken from `ifconfig`), as "localhost" will not work in this case. For easier startup, the default-URL can be passed as an environment variable, and the `?autoconnect` query parameter can be used to automatically connect to it.
* **Prompt Library**: A list of example prompts, grouped into different categories. These prompts are tailored for our current internal demonstration deployment, and can be changed in the `config.js` file (see below). Clicking an example prompt will automatically send it to the LLM.
* **Agents & Actions**: Shows the list of all Agents and their respective Actions currently available on the connected OPACA Runtime Platform. Each Agent can be expanded to show its Actions, which can be further expanded to show their parameters and a short description.
* **Configuration**: Allows to send different configurations to the backend, depending on the selected backend method, e.g. for which LLM to use at what temperature.
* **Logging**: Shows the full logging-information sent by the AI-agents in the backend; this is the same as shown underneath the individual messages, but all in one place. Also, other than the output underneath the message, the logging output in this section is streamed as the LLM is still "thinking", making it a valuable resource for requests that take more time.


## Header

The Navigation/Header bar contains some dropdown that can be used to e.g. set the language of the UI (this does not influence the language of the LLM, which will just react to the language it is spoken to), and most importantly a selector for the [method](methods_overview.md) to be used for interacting with the actual LLM.

## Configuration

Several aspects of the UI, such as the available and default backends, the selection of sample prompts, or the default language can be configured in `config.js`. Several of those can also be configured via environment variables, e.g. in the `docker-compose.yml` file.
