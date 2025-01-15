<template>
    <div class="d-flex justify-content-start flex-grow-1 w-100">

        <Sidebar :backend="backend" :language="language" ref="sidebar"
                 @connect="initiatePrompt"
                 @api-key-change="(newValue) => this.apiKey = newValue"/>

        <!-- Main Container: Chat Window, Text Input -->
        <main id="mainContent" class="d-flex flex-column flex-grow-1 mt-4 pe-4"
              style="height:calc(100vh - 85px); max-width: calc(100vw * 3 / 4);">

            <!-- Chat Window -->
            <div class="container card flex-grow-1" id="chat1" style="border-radius: 15px; overflow-y: auto;">
                <div class="card-body" style="flex-direction: column-reverse" id="chat-container"/>
                <div v-show="showExampleQuestions" class="sample-questions">
                    <div v-for="(question, index) in getConfig().translations[language].sampleQuestions"
                         :key="index"
                         class="sample-question"
                         @click="askChatGpt(question.question)">
                        {{question.icon}} <br> {{ question.question }}
                    </div>
                </div>
            </div>

            <div class="container p-0">
                <div class="input-group mt-2 mb-4">
                    <input id="textInput" placeholder="Type here ..."
                           class="form-control p-2 rounded-start-2"
                           @keypress="textInputCallback"/>
                    <button type="button"
                            class="btn btn-primary rounded-end-2"
                            @click="submitText">
                        <i class="fa fa-send mx-2"/>
                    </button>

                    <button type="button" :disabled="isBusy"
                            class="btn btn-outline-primary ms-2 rounded rounded-1"
                            @click="startRecognition">
                        <i v-if="isRecording" class="fa fa-spinner fa-spin mx-2"/>
                        <i v-else class="fa fa-microphone mx-2"/>
                    </button>

                    <button type="button" :disabled="isBusy" v-if="!!speechSynthesis"
                            class="d-none btn btn-outline-primary ms-2 rounded rounded-1"
                            @click="speakLastMessage">
                        <i class="fa fa-volume-up mx-2"/>
                    </button>

                    <button type="button"
                            class="btn btn-outline-danger ms-2 rounded rounded-1"
                            @click="resetChat">
                        <i class="fa fa-undo mx-2"/>
                    </button>
                </div>
            </div>

            <!-- Simple Keyboard -->
            <SimpleKeyboard v-if="getConfig().ShowKeyboard"
                            @change="this.onChangeSimpleKeyboard" />
        </main>
    </div>

</template>

<script>
import {marked} from "marked";
import conf from '../../config'
import SimpleKeyboard from "./SimpleKeyboard.vue";
import Sidebar from "./sidebar.vue";
import {sendRequest} from "../utils.js";

export default {
    name: 'main-content',
    components: {Sidebar, SimpleKeyboard},
    props: {
        backend: String,
        language: String,
    },
    data() {
        return {
            apiKey: '',
            recognition: null,
            lastMessage: null,
            messageCount: 0,
            speechSynthesis: window.SpeechSynthesis,
            isRecording: false,
            isBusy: false,
            showExampleQuestions: true,
            autoSpeakNextMessage: false,
            isDarkScheme: false
        }
    },
    methods: {
        getConfig() {
            return conf;
        },

        updateTheme() {
            // Check if dark color scheme is preferred
            this.isDarkScheme = window.matchMedia('(prefers-color-scheme: dark)').matches;
            this.updateDebugColors()
        },

        onChangeSimpleKeyboard(input) {
            document.getElementById("textInput").value = input;
        },

        async textInputCallback(event) {
            if (event.key === "Enter") {
                await this.submitText()
            }
        },

        async submitText() {
            const userInput = document.getElementById("textInput").value;
            document.getElementById("textInput").value = "";
            if (userInput != null && userInput !== "") {
                await this.askChatGpt(userInput);
            }
        },

        async initiatePrompt(url, username, password) {
            console.log(`CONNECTING as ${opacaUser}`)
            const body = {url: url, user: username, pwd: password};
            const connectButton = document.getElementById('button-connect');
            connectButton.disabled = true;
            try {
                const res = await sendRequest("POST", `${conf.BackendAddress}/connect`, body);
                const rpStatus = parseInt(res.data); // actual rp status is in response body (maybe backend should instead just return this as its own status?)
                if (rpStatus === 200) {
                    const res2 = await sendRequest("GET", `${conf.BackendAddress}/actions`)
                    this.$refs.sidebar.platformActions = res2.data;
                    this.$refs.sidebar.selectView('agents');
                } else if (rpStatus === 403) {
                    this.$refs.sidebar.platformActions = null;
                    alert(conf.translations[this.language].unauthorized);
                } else {
                    this.$refs.sidebar.platformActions = null;
                    alert(conf.translations[this.language].unreachable);
                }
            } catch (e) {
                console.error('Error while initiating prompt:', e);
                this.$refs.sidebar.platformActions = null;
                alert('Backend server is unreachable.'); // put in config?
            } finally {
                connectButton.disabled = false;
            }
        },

        async askChatGpt(userText) {
            this.showExampleQuestions = false;
            const debugMessageLength = this.$refs.sidebar.debugMessages.length;
            const currentMessageCount = this.messageCount;
            this.messageCount++;
            this.createSpeechBubbleUser(userText);
            try {
                if (this.getBackend() === 'tool-llm-openai') {

                    this.createSpeechBubbleAI(`Preparing the system`, currentMessageCount);
                    this.toggleLoadingSymbol(currentMessageCount);
                    this.editAnimationSpeechBubbleAI(currentMessageCount, true, "#ffffff");
                    this.scrollDown(false)

                    const socket = new WebSocket(`${conf.BackendAddress}/${this.getBackend()}/query_stream`);

                    socket.onmessage = (event) => {
                        const result = JSON.parse(JSON.parse(event.data)); // YEP, THAT MAKES NO SENSE (WILL CHANGE SOON TM)
                        if (result.hasOwnProperty("agent")) {
                            // Agent messages are intermediate results
                            this.addDebugToken(result, currentMessageCount)
                            this.scrollDown(true);
                        } else {
                            // Last message received should be final response
                            this.toggleLoadingSymbol(currentMessageCount);
                            this.editTextSpeechBubbleAI(result.content, currentMessageCount)
                            this.editAnimationSpeechBubbleAI(currentMessageCount, false, "#ffffff");

                            // Append the debug messages generated during this request to the ai message bubble
                            const aiBubble = document.getElementById(`debug-${currentMessageCount}-text`)
                            const debugMessages = this.$refs.sidebar.debugMessages
                            if (aiBubble) {
                                for (let i = debugMessageLength; i < debugMessages.length; i++) {
                                    let d1 = document.createElement("div")
                                    d1.className = "bubble-debug-text"
                                    d1.textContent = debugMessages.at(i).text
                                    d1.style.color = debugMessages.at(i).color
                                    aiBubble.append(d1)
                                }
                            }

                            // Make expand debug button appear
                            const debugToggle = document.getElementById(`debug-${currentMessageCount}-toggle`);
                            debugToggle.style.display = 'block';
                            this.scrollDown(false)
                        }
                    }

                    socket.onopen = () => {
                        const inputData = {user_query: userText, api_key: this.apiKey};
                        socket.send(JSON.stringify(inputData));
                    };

                    socket.onclose = () => {
                        console.log("WebSocket connection closed");
                    };
                } else {
                    this.createSpeechBubbleAI(`Generating your answer`, currentMessageCount);
                    this.toggleLoadingSymbol(currentMessageCount);
                    this.scrollDown(false)

                    const result = await sendRequest(
                        "POST",
                        `${conf.BackendAddress}/${this.getBackend()}/query`,
                        {user_query: userText, api_key: this.apiKey},
                        null);
                    const answer = result.data.content;
                    if (result.data.error) {
                        this.addDebug(result.data.error)
                    }
                    this.toggleLoadingSymbol(currentMessageCount)
                    this.editTextSpeechBubbleAI(answer, currentMessageCount)
                    this.scrollDown(false);
                    this.processDebugInput(result.data.agent_messages, currentMessageCount);
                    this.scrollDown(true);
                }
            } catch (error) {
                console.error(error);
                this.toggleLoadingSymbol(currentMessageCount)
                this.createSpeechBubbleAI("Error while fetching data: " + error)
                this.scrollDown(false);
            }
            if (this.autoSpeakNextMessage) {
                this.speakLastMessage();
                this.autoSpeakNextMessage = false;
            }
        },

        isSpeechRecognitionSupported() {
            // very hacky check if the user is using the (full) google chrome browser
            const isGoogleChrome = window.chrome !== undefined
                    && window.navigator.userAgentData !== undefined
                    && window.navigator.userAgentData.brands.some(b => b.brand === 'Google Chrome')
                    && window.navigator.vendor === "Google Inc."
                    && Array.from(window.navigator.plugins).some(plugin => plugin.name === "Chrome PDF Viewer");
            if (!isGoogleChrome) {
                alert('At the moment, speech recognition is only supported in the Google Chrome browser.');
                return false;
            }
            if (!('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
                alert("Please enable 'SpeechRecognition' and 'webkitSpeechRecognition' in your browser's config.");
                return false;
            }
            if (location.protocol !== 'https' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
                alert('Speech recognition is only supported using a secure connection (HTTPS) or when hosted locally.');
                return false;
            }
            return true;
        },

        async startRecognition() {
            if (!this.isSpeechRecognitionSupported()) return;
            this.abortSpeaking();
            console.log("Recognized language: " + conf.languages[this.language]);
            const recognition = new (webkitSpeechRecognition || SpeechRecognition)()
            recognition.lang = conf.languages[this.language];
            recognition.onresult = async (event) => {
                if (!event.results || event.results.length <= 0) return;
                const recognizedText = event.results[0][0].transcript;
                this.addDebug('Recognized text: ' + recognizedText, "white", "speech");
                this.autoSpeakNextMessage = true
                await this.askChatGpt(recognizedText);
            };
            recognition.onspeechend = () => {
                this.isRecording = false;
            };
            recognition.onnomatch = () => {
                console.error('Failed to recognize spoken text.');
            };
            recognition.onerror = (error) => {
                console.error(error);
                this.addDebug('Recognition Error: ' + error.message || error.error, 'red', "error");
                this.createSpeechBubbleAI('The speech recognition failed to understand your request.');
            };
            recognition.onend = () => {
                console.log('Recognition ended.');
                this.isRecording = false;
                this.isBusy = false;
            };
            recognition.start();
            this.isRecording = true;
            this.isBusy = true;
        },

        async resetChat() {
            document.getElementById("chat-container").innerHTML = '';
            this.abortSpeaking();
            this.createSpeechBubbleAI(conf.translations[this.language].welcome, 'startBubble');
            this.showExampleQuestions = true;
            await sendRequest("POST", `${conf.BackendAddress}/reset`);
            this.isBusy = false;
        },

        createSpeechBubbleAI(text, id) {
            this.lastMessage = text;
            const chat = document.getElementById("chat-container")
            let d1 = document.createElement("div")
            let debugId = `debug-${id}`;
            d1.innerHTML += `
            <div id="${id}" class="d-flex flex-row justify-content-start mb-4">
                <img src=/src/assets/Icons/ai.png alt="AI" class="chaticon">
                <div id="chatBubble" class="p-2 ms-3 small mb-0 chatbubble chat-ai">
                    <div class="d-flex flex-row justify-content-start">
                        <div id="loadingContainer"><div class="loader hidden"></div></div>
                        <div id="messageContainer">${marked.parse(text)}</div>
                    </div>
                    <div id="${debugId}-toggle" class="debug-toggle" style="display: none; cursor: pointer; font-size: 10px;">
                        <img src=/src/assets/Icons/double_down_icon.png class="double-down-icon" alt=">>" width="10px" height="10px" style="transform: none"/>
                        debug
                    </div>
                    <hr id="${debugId}-separator" class="debug-separator" style="display: none;">
                    <div id="${debugId}-text" v-if="debugExpanded" class="bubble-debug-text" style="display: none;"/>
                </div>
            </div>`

            this.isBusy = false;

            chat.appendChild(d1)

            const debugToggle = document.getElementById(`${debugId}-toggle`);
            const debugSeparator = document.getElementById(`${debugId}-separator`);
            const debugText = document.getElementById(`${debugId}-text`);

            let debugExpanded = false;

            debugToggle.addEventListener('click', () => {
                debugExpanded = !debugExpanded;
                if (debugExpanded) {
                    debugSeparator.style.display = 'block';
                    debugText.style.display = 'block';
                    const icon = debugToggle.querySelector('img');
                    icon.style.transform = 'rotate(180deg)'
                }
                else {
                    debugSeparator.style.display = 'none';
                    debugText.style.display = 'none';
                    const icon = debugToggle.querySelector('img');
                    icon.style.transform = 'none'
                }
            })
        },

        createSpeechBubbleUser(text) {
            const chat = document.getElementById("chat-container")
            let d1 = document.createElement("div")
            d1.innerHTML += `
            <div class="d-flex flex-row justify-content-end mb-4">
                <div class="p-2 me-3 small mb-0 chatbubble chat-user">
                    ${text}
                </div>
                <img src=/src/assets/Icons/nutzer.png alt="User" class="chaticon">
            </div>`
            chat.appendChild(d1)
            this.scrollDown(false)
        },

        scrollDown(debug) {
            const chatDiv = debug
                    ? document.getElementById('chatDebug')
                    : document.getElementById('chat1');
            chatDiv.scrollTop = chatDiv.scrollHeight;
        },

        speakLastMessage() {
            if (speechSynthesis) {
                this.abortSpeaking();
                console.log("Speaking message: " + this.lastMessage);
                const utterance = new SpeechSynthesisUtterance(this.lastMessage);
                utterance.lang = conf.languages[this.language];
                utterance.onstart = () => {
                    console.log("Speaking started.");
                }
                utterance.onend = () => {
                    console.log("Speaking ended.");
                }
                utterance.onerror = (error) => {
                    console.error(error);
                }
                speechSynthesis.speak(utterance);
            }
        },

        abortSpeaking() {
            if (speechSynthesis && speechSynthesis.speaking) {
                speechSynthesis.cancel();
            }
        },

        getDebugColor(agentName, darkScheme) {
            // color schemes for modes [dark, light]
            const keywordColors = {
                // RestGPT
                "Planner": ["#ff0000", "#9c0000"],
                "Action Selector": ["#ffff00", "#bf6e00"],
                "Caller": ["#5151ff", "#0000b1"],
                "Evaluator": ["#00ff00", "#007300"],
                // Tools
                "Tool Generator": ["#ff0000", "#9c0000"],
                "Tool Evaluator": ["#ffff00", "#bf6e00"],
                // Simple
                "user": ["#ffffff", "#000000"],
                "assistant": ["#8888ff", "#434373"],
                "system": ["#ffff88", "#71713d"],
            }

            // return either specific color for light/dark mode or default black/white
            return (keywordColors[agentName] ?? ["#fff", "#000"])[darkScheme ? 0 : 1];
        },

        getDebugLoadingMessage(agentName) {
            const debugLoadingMessages = {
                // RestGPT
                "Planner": "Planning the next step",
                "Action Selector": "Selecting the best action",
                "Caller": "Calling the OPACA platform",
                "Evaluator": "Evaluating the results",
                // Tools
                "Tool Generator": "Generating the necessary tools",
                "Tool Evaluator": "Evaluating the tools",
                // Simple
                "user": "",
                "assistant": "",
                "system": "",
            }

            return debugLoadingMessages[agentName];
        },

        addDebugToken(agent_message, messageCount) {
            const color = this.getDebugColor(agent_message["agent"], this.isDarkScheme);
            const message = this.getDebugLoadingMessage(agent_message["agent"])
            // Change the loading message and color depending on the currently received agent message

            this.editTextSpeechBubbleAI(message, messageCount)
            this.editAnimationSpeechBubbleAI(messageCount, true, color)

            if (agent_message["tools"].length > 0) {
                this.addDebug(agent_message["tools"].join('\n'), color, agent_message["agent"] + "-Tools")
            }
            else {
                this.addDebug(agent_message["content"], color, agent_message["agent"])
            }
        },

        processDebugInput(agent_messages, messageCount) {
            if (agent_messages.length > 0) {
                // if at least one debug message was found, let the "debug" button appear on the speech bubble
                const debugToggle = document.getElementById(`debug-${messageCount}-toggle`);
                debugToggle.style.display = 'block';
            }

            // agent_messages has fields: [agent, content, execution_time, response_metadata[completion_tokens, prompt_tokens, total_tokens]]
            for (const message of agent_messages) {
                const color = this.getDebugColor(message["agent"], this.isDarkScheme);
                // if tools have been generated, display the tools (no message was generated in that case)
                const content = message["agent"] + ": " + (message["tools"].length > 0 ? message["tools"] : message["content"])
                this.addDebug(content, color, message["agent"])

                // Add the formatted debug text to the associated speech bubble
                const messageBubble = document.getElementById(`debug-${messageCount}-text`)
                if (messageBubble) {
                    let d1 = document.createElement("div")
                    d1.className = "bubble-debug-text"
                    d1.textContent = content
                    d1.style.color = color
                    messageBubble.append(d1)
                }
            }
        },

        updateDebugColors() {
            const debugElements = document.querySelectorAll('.debug-text, .bubble-debug-text');
            debugElements.forEach((element) => {
                const text = element.innerText || element.textContent;
                element.style.color = this.getDebugColor(text.split(':')[0] ?? "", this.darkScheme);
            });
        },

        addDebug(text, color, type) {
            const debugMessages = this.$refs.sidebar.debugMessages;

            // If the message includes tools, the message needs to be replaced instead of appended
            if (debugMessages.length > 0 && debugMessages[debugMessages.length - 1].type === "Tool Generator-Tools" && text) {
                debugMessages[debugMessages.length - 1] = {
                    text: text,
                    color: color,
                    type: type,
                }
            }
            // If the message has the same type as before but is not a tool, append the token to the text
            else if (debugMessages.length > 0 && debugMessages[debugMessages.length - 1].type === type) {
                debugMessages[debugMessages.length - 1].text += `${text}`
            }
            // If the message has a new type, assume it is the beginning of a new agent message
            else {
                debugMessages.push({
                    text: type + ":\n" + text,
                    color: color,
                    type: type,
                });
            }
        },

        editTextSpeechBubbleAI(text, id) {
            const aiBubble = document.getElementById(`${id}`)
            aiBubble.querySelector("#messageContainer").innerHTML = `${marked.parse(text)}`
            // aiBubble.querySelector("#chatBubble").style.boxShadow = color ? `0 0 10px ${color}` : ""
        },

        editAnimationSpeechBubbleAI(id, active, color) {
            const aiBubble = document.getElementById(`${id}`)
            const animationName = `move-glow-${color.replace(/[^a-zA-Z0-9]/g, "")}`
            if (!document.querySelector(`#${animationName}`)) {
                // Create a style block for the custom animation
                const style = document.createElement("style");
                style.id = animationName;
                style.innerHTML = `
                    @keyframes ${animationName} {
                        0%, 100% {
                            box-shadow: 0 0 10px ${color}40;
                        }
                        50% {
                            box-shadow: 0 0 20px ${color}90;
                        }
                    }
                `;
                document.head.appendChild(style);
            }

            aiBubble.querySelector("#chatBubble").style.animation = active ? `${animationName} 3s infinite` : "";
        },

        toggleLoadingSymbol(id) {
            const aiBubble = document.getElementById(`${id}`)
            const loadingContainer = aiBubble.querySelector("#loadingContainer");
            if (loadingContainer) {
                loadingContainer.classList.toggle("loader");
            }
        },

        getBackend() {
            const parts = this.backend.split('/');
            return parts[parts.length - 1];
        },

        setupTooltips() {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl)
            });
        }
    },

    mounted() {
        this.updateTheme();
        this.setupTooltips();
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', this.updateTheme);
        this.createSpeechBubbleAI(conf.translations[this.language].welcome, 'startBubble');
        console.log("mounted");
    },
}

</script>

<style>
.chatbubble {
    border-radius: 10px;
    text-align: left;
    flex-direction: column;
    justify-content: flex-start;
    align-items: flex-end;
    position: relative;
}

.chat-user {
    background-color: #eee3;
}

.chat-ai {
    background-color: #4ce3;
}

.chaticon {
    width: 45px;
    height: 100%;
    background-color: #fff;
    border-radius: 5px;
}

#chatDebug {
    background-color: black;
    overflow: hidden;
    overflow-y: auto;
}

.sample-questions {
  display: flex;
  flex-direction: row;
  justify-content: center;
  margin-bottom: 10px;
}

.sample-question {
  display: flex;
  flex: 1;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  margin: 5px;
  padding: 10px;
  background-color: #333;
  border-radius: 5px;
  color: #fff;
}

.sample-question:hover {
    background: #222;
}

.debug-separator {
    border: 0;
    margin: 5px 0;
}

.debug-toggle {
    cursor: pointer;
    font-size: 10px;
    margin-top: auto;
    display: flex;
    justify-content: flex-end;
}

.bubble-debug-text {
    font-size: 12px;
    color: #333;
    padding: 5px;
    border-radius: 5px;
    margin-top: 5px;
    display: flex;
    justify-content: flex-start;
}

.loader {
  border: 4px solid transparent;
  border-top: 4px solid #3498db; /* Change this color for different loading styles */
  border-radius: 50%;
  width: 24px;
  height: 24px;
  animation: spin 1s linear infinite;
  margin-right: 10px; /* Space between the loader and the text */
}

.hidden {
    display: none;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

@media (max-width: 400px) {
    .opaca-credentials {
        flex-direction: column;
    }
}

@media (prefers-color-scheme: dark) {
    body {
        color: #fff;
        background-color: #222;
    }
    #chat1 {
        color: #fff;
        background-color: #444;
    }

    .form-check-input:valid, .form-control:valid {
        background-color: #212529!important;
        color: white;
    }
    .form-check-input:checked {
        background-color: #0d6efd!important;
    }
    .form-control::placeholder {
        color: #6c757d;
        opacity: 1;
    }

    .debug-toggle {
        color: #eee;
    }

    .bubble-debug-text {
        background-color: #222222;
    }

    .debug-separator {
        border-top: 1px solid #ddd;
    }

    .double-down-icon {
        filter: invert(1);
    }
}

@media (prefers-color-scheme: light) {
    #chatDebug {
        background-color: #fff;
        overflow: hidden;
        border: 1px solid #ccc; /* border only needed in light mode */
    }

    .sample-question {
        background-color: #ddd;
        color: #000;
    }

    .sample-question:hover {
        background: #eee;
    }

    .debug-toggle {
        color: #444;
    }

    .bubble-debug-text {
        background-color: #c8e3ea;
    }

    .debug-separator {
        border-top: 1px solid #808080;
    }
}

</style>
