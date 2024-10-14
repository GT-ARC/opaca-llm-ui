<template>
    <div class="d-flex justify-content-start flex-grow-1 w-100">

        <!-- Sidebar Menu -->
        <div id="sidebar-menu"
             class="d-flex flex-column justify-content-start align-items-center p-2 pt-3 gap-2"
             style="height: calc(100vh - 50px)">

            <i @click="toggleSidebar('connect')"
               class="fa fa-link p-2 sidebar-item"
               data-toggle="tooltip" data-placement="right" title="Config"
               v-bind:class="{'sidebar-item-select': isSidebarOpen('connect')}" />

            <i @click="toggleSidebar('agents')"
               class="fa fa-users p-2 sidebar-item"
               data-toggle="tooltip" data-placement="right" title="Agents"
               v-bind:class="{'sidebar-item-select': isSidebarOpen('agents')}"/>

            <i @click="toggleSidebar('debug')"
               class="fa fa-terminal p-2 sidebar-item"
               data-toggle="tooltip" data-placement="right" title="Debug"
               v-bind:class="{'sidebar-item-select': isSidebarOpen('debug')}"/>
        </div>

        <!-- Left Container: Configuration, Debug-Output -->
        <div v-show="isSidebarOpen()" class="mt-4">
            <aside id="sidebar"
               class="container-fluid d-flex flex-column px-3"
               style="height: calc(100vh - 85px); width: 400px">

                <!-- connection/backend settings -->
                <div v-show="isSidebarOpen('connect')">
                    <div id="sidebarConfig"
                     class="container d-flex flex-column">

                    <div class="py-2 text-start">
                        <input id="opacaUrlInput" type="text"
                               class="form-control m-0"
                               v-model="opacaRuntimePlatform"
                               :placeholder="config.translations[language].opacaLocation" />
                    </div>

                    <div class="py-2 text-start">
                        <div class="row opaca-credentials">
                            <div class="col-md-6">
                                <input id="opacaUser" type="text"
                                       class="form-control m-0"
                                       v-model="opacaUser"
                                       placeholder="Username" />
                            </div>
                            <div class="col-md-6">
                                <input id="opacaPwd" type="password"
                                       class="form-control m-0"
                                       v-model="opacaPwd"
                                       placeholder="Password" />
                            </div>
                        </div>

                    </div>

                    <div class="py-2 text-start" v-if="config.ShowApiKey">
                        <input id="apiKey" type="password"
                               class="form-control m-0"
                               v-model="apiKey"
                               placeholder="OpenAI API Key" />
                    </div>

                    <div class="text-center py-2">
                        <button class="btn btn-primary w-100" @click="initiatePrompt">
                            <i class="fa fa-link me-1"/>Connect
                        </button>
                    </div>

                </div>
                </div>

                <!-- debug console -->
                <div v-show="isSidebarOpen('debug')" id="chatDebug"
                     class="container flex-grow-1 mb-4 p-2 rounded rounded-4">
                    <div id="debug-console" class="flex-row-reverse text-start"/>
                </div>

                <!-- agents/actions overiew -->
                <div v-show="isSidebarOpen('agents')"
                     id="containers-agents-display" class="container flex-grow-1 overflow-hidden overflow-y-auto">
                    <div v-if="!platformActions || Object.keys(platformActions).length === 0">No actions available.</div>
                    <div v-else class="flex-row" >
                        <div class="accordion text-start" id="agents-accordion">
                            <div v-for="(actions, agent, index) in platformActions" class="accordion-item" :key="index">

                                <!-- header -->
                                <h2 class="accordion-header m-0" :id="'accordion-header-' + index">
                                    <button class="accordion-button" :class="{collapsed: index > 0}"
                                            type="button" data-bs-toggle="collapse"
                                            :data-bs-target="'#accordion-body-' + index" aria-expanded="false"
                                            :aria-controls="'accordion-body-' + index">
                                        <i class="fa fa-user me-1"/>
                                        <strong>{{ agent }}</strong>
                                    </button>
                                </h2>

                                <!-- body -->
                                <div :id="'accordion-body-' + index" class="accordion-collapse collapse" :class="{show: index === 0}"
                                     :aria-labelledby="'accordion-header-' + index" data-bs-parent="#agents-accordion">
                                    <div class="accordion-body p-0 ps-4">
                                        <ul class="list-group list-group-flush">
                                            <li v-for="(action, index) in actions" :key="index" class="list-group-item">
                                                {{ action }}
                                            </li>
                                        </ul>
                                    </div>
                                </div>

                            </div>
                        </div>
                    </div>
                </div>

                <div class="resizer me-1" id="resizer" />
            </aside>
        </div>

        <!-- Main Container: Chat Window, Text Input -->
        <main id="mainContent" class="d-flex flex-column flex-grow-1 mt-4 pe-4"
              style="height:calc(100vh - 85px); max-width: calc(100vw * 3 / 4);">

            <!-- Chat Window -->
            <div class="container card flex-grow-1" id="chat1" style="border-radius: 15px; overflow-y: auto;">
                <div class="card-body" style="flex-direction: column-reverse" id="chat-container"/>
                <div v-show="showExampleQuestions" class="sample-questions">
                    <div v-for="(question, index) in config.translations[language].sampleQuestions"
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

                    <button type="button" :disabled="busy"
                            class="btn btn-outline-primary ms-2 rounded rounded-1"
                            @click="startRecognition">
                        <i v-if="recording" class="fa fa-spinner fa-spin mx-2"/>
                        <i v-else class="fa fa-microphone mx-2"/>
                    </button>

                    <button type="button" :disabled="busy" v-if="!!speechSynthesis"
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
            <SimpleKeyboard @onChange="onChangeSimpleKeyboard" v-if="config.ShowKeyboard" />
        </main>
    </div>

</template>

<script setup>
import axios from "axios"
import {marked} from "marked";
import {inject, onMounted, ref} from "vue";
import config from '../../config'
import SimpleKeyboard from "./SimpleKeyboard.vue";

document.getElementById('')

    let opacaRuntimePlatform = config.OpacaRuntimePlatform;
    let opacaUser = "";
    let opacaPwd = "";
    let apiKey = "";
    let platformActions = null;

    const backend = inject('backend');
    const language = inject('language');
    const sidebar = inject('sidebar');
    let recognition= null;
    let lastMessage = null;
    let messageCount = 0;
    const speechSynthesis = window.speechSynthesis;
    const recording = ref(false);
    const busy = ref(false);
    const debug = ref(false);
    const showExampleQuestions = ref(true);
    const autoSpeakNextMessage = ref(false);
    const languages = {
        GB: 'en-GB',
        DE: 'de-DE'
    }
    const darkScheme = ref(false);

    onMounted(() => {
        console.log("mounted")
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
          return new bootstrap.Tooltip(tooltipTriggerEl)
        });

        updateTheme()
        setupResizableSidebar();
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updateTheme);
        createSpeechBubbleAI(config.translations[language.value].welcome, 'startBubble');
        initiatePrompt();
    });

    function setupResizableSidebar() {
        const resizer = document.getElementById('resizer');
        const sidebar = document.getElementById('sidebar');
        let isResizing = false;

        resizer.addEventListener('mousedown', (e) => {
          isResizing = true;
          document.body.style.cursor = 'ew-resize';
        });

        document.addEventListener('mousemove', (event) => {
          if (!isResizing) return;

          // Calculate the new width for the aside
          const newWidth = event.clientX - sidebar.getBoundingClientRect().left;

          if (newWidth > 200 && newWidth < 600) {
            sidebar.style.width = `${newWidth}px`;
          }
        });

        document.addEventListener('mouseup', () => {
          isResizing = false;
          document.body.style.cursor = 'default';
        });
    }

    function updateTheme() {
        // Check if dark color scheme is preferred
        darkScheme.value = window.matchMedia('(prefers-color-scheme: dark)').matches;
        updateDebugColors()
    }

    function onChangeSimpleKeyboard(input) {
        document.getElementById("textInput").value = input;
    }

    async function textInputCallback(event) {
        if (event.key === "Enter") {
            await submitText()
        }
    }

    async function submitText() {
        const userInput = document.getElementById("textInput").value
        document.getElementById("textInput").value = ""
        if (userInput != null && userInput !== "") {
            await askChatGpt(userInput)
        }
    }

    async function initiatePrompt() {
        const body = {url: opacaRuntimePlatform, user: opacaUser, pwd: opacaPwd}
        const res = await sendRequest("POST", `${config.BackendAddress}/connect`, body);
        if (res.status === 200) {
            const res2 = await sendRequest("GET", `${config.BackendAddress}/actions`, null);
            const actions = res2.data;
            let text = config.translations[language.value].connected;
            if (Object.keys(actions).length > 0) {
                for (const agent in actions) {
                    //text += `\n* **${agent}:** ${actions[agent].join(", ")}`
                    text += `\n* ${agent}`
                }
            } else {
                text += config.translations[language.value].none
            }
            platformActions = actions;
            toggleSidebar('agents');
        } else if (res.status === 403) {
            alert(config.translations[language.value].unauthorized);
            platformActions = null;
        } else {
            alert(config.translations[language.value].unreachable);
            platformActions = null;
        }
    }

    async function sendRequest(method, url, body) {
        try {
            return await axios.request({
                method: method,
                url: url,
                data: body,
                headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            });
        } catch (error) {
            throw error;
        }
    }

    async function askChatGpt(userText) {
        showExampleQuestions.value = false;
        createSpeechBubbleUser(userText);
        try {
            const result = await sendRequest("POST", `${config.BackendAddress}/${getBackend()}/query`, {user_query: userText, debug: true, api_key: apiKey});
            const answer = result.data.content;
            if (result.data.error) {
                addDebug(result.data.error)
            }
            createSpeechBubbleAI(answer, messageCount);
            processDebugInput(result.data.agent_messages, messageCount);
            messageCount++;
            scrollDown(debug.value);
        } catch (error) {
            console.error(error);
            createSpeechBubbleAI("Error while fetching data: " + error)
            scrollDown(false);
        }
        if (autoSpeakNextMessage.value) {
            speakLastMessage();
            autoSpeakNextMessage.value = false;
        }
    }

    function isSpeechRecognitionSupported() {
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
    }

    async function startRecognition() {
        if (!isSpeechRecognitionSupported()) return;
        abortSpeaking();
        console.log("Recognized language: " + languages[language.value]);
        const recognition = new (webkitSpeechRecognition || SpeechRecognition)()
        recognition.lang = languages[language.value];
        recognition.onresult = async (event) => {
            if (!event.results || event.results.length <= 0) return;
            const recognizedText = event.results[0][0].transcript;
            addDebug('Recognized text: ' + recognizedText);
            autoSpeakNextMessage.value = true
            await askChatGpt(recognizedText);
        };
        recognition.onspeechend = () => {
            recording.value = false;
        };
        recognition.onnomatch = () => {
            console.error('Failed to recognize spoken text.');
        };
        recognition.onerror = (error) => {
            console.error(error);
            addDebug('Recognition Error: ' + error.message || error.error, 'red');
            createSpeechBubbleAI('The speech recognition failed to understand your request.');
        };
        recognition.onend = () => {
            console.log('Recognition ended.');
            recording.value = false;
            busy.value = false;
        };
        recognition.start();
        recording.value = true;
        busy.value = true;
    }

    async function resetChat() {
        document.getElementById("chat-container").innerHTML = '';
        abortSpeaking();
        createSpeechBubbleAI(config.translations[language.value].welcome, 'startBubble');
        showExampleQuestions.value = true;
        await sendRequest("POST", `${config.BackendAddress}/${getBackend()}/reset`, null);
        busy.value = false;
    }

    function createSpeechBubbleAI(text, id) {
        lastMessage = text;
        const chat = document.getElementById("chat-container")
        let d1 = document.createElement("div")
        let debugId = `debug-${id}`;
        d1.innerHTML += `
        <div id="${id}" class="d-flex flex-row justify-content-start mb-4">
            <img src=/src/assets/Icons/ai.png alt="AI" class="chaticon">
            <div class="p-2 ms-3 small mb-0 chatbubble chat-ai">
                ${marked.parse(text)}
                <div id="${debugId}-toggle" class="debug-toggle" style="display: none; cursor: pointer; font-size: 10px;">
                    <img src=/src/assets/Icons/double_down_icon.png class="double-down-icon" alt=">>" width="10px" height="10px" style="transform: none"/>
                    debug
                </div>
                <hr id="${debugId}-separator" class="debug-separator" style="display: none;">
                <div id="${debugId}-text" v-if="debugExpanded" class="bubble-debug-text" style="display: none;"/>
            </div>
        </div>`

        const waitBubble = document.getElementById('waitBubble');
        if (waitBubble) {
            waitBubble.remove();
        }
        busy.value = false;

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
    }

    function createSpeechBubbleUser(text) {
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
        createSpeechBubbleAI('. . .', 'waitBubble')
        scrollDown(false)
    }

    function scrollDown(debug) {
        const chatDiv = debug ? document.getElementById('chatDebug') : document.getElementById('chat1');
        chatDiv.scrollTop = chatDiv.scrollHeight;
    }

    function speakLastMessage() {
        if (speechSynthesis) {
            abortSpeaking();
            console.log("Speaking message: " + lastMessage);
            const utterance = new SpeechSynthesisUtterance(lastMessage);
            utterance.lang = languages[language.value];
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
    }

    function abortSpeaking() {
        if (speechSynthesis && speechSynthesis.speaking) {
            speechSynthesis.cancel();
        }
    }

    function getDebugColor(agentName, darkScheme) {
        // color schemes for modes [dark, light]
        const keywordColors = {
            // RestGPT
            "Planner": ["#f00", "#9c0000"],
            "Action Selector": ["#ff0", "#bf6e00"],
            "Caller": ["#5151ff", "#0000b1"],
            "Evaluator": ["#0f0", "#007300"],
            // Tools
            "Tool Generator": ["#f00", "#9c0000"],
            "Tool Evaluator": ["#ff0", "#bf6e00"],
            // Simple
            "user": ["#fff", "#000"],
            "assistant": ["#88f", "#434373"],
            "system": ["#ff8", "#71713d"],
        }

        // return either specific color for light/dark mode or default black/white
        return (keywordColors[agentName] ?? ["#fff", "#000"])[darkScheme ? 0 : 1];
    }

    function processDebugInput(agent_messages, messageCount) {
        if (agent_messages.length > 0) {
            // if at least one debug message was found, let the "debug" button appear on the speech bubble
            const debugToggle = document.getElementById(`debug-${messageCount}-toggle`);
            debugToggle.style.display = 'block';
        }

        // agent_messages has fields: [agent, content, execution_time, response_metadata[completion_tokens, prompt_tokens, total_tokens]]
        for (const message of agent_messages) {
            const color = getDebugColor(message["agent"], darkScheme.value);
            // if tools have been generated, display the tools (no message was generated in that case)
            const content = message["agent"] + ": " + (message["tools"].length > 0 ? message["tools"] : message["content"])
            addDebug(content, color)

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
    }

    function updateDebugColors() {
        const debugElements = document.querySelectorAll('.debug-text, .bubble-debug-text');
        debugElements.forEach((element) => {
            const text = element.innerText || element.textContent;
            element.style.color = getDebugColor(text.split(':')[0] ?? "", darkScheme.value);
        });
    }

    function addDebug(text, color) {
        const debugChat = document.getElementById("debug-console");
        let d1 = document.createElement("div")
        d1.className = "debug-text"
        d1.textContent = text
        if (color) {
            d1.style.color = color
        }
        debugChat.append(d1)
    }

    function beforeDestroy() {
        if (recognition) {
            recognition.stop();
        }
    }

    function isSidebarOpen(key) {
        if (key !== undefined) {
            return sidebar.value === key;
        } else {
            return sidebar.value !== 'none';
        }
    }

    function toggleSidebar(key) {
        const mainContent = document.getElementById('mainContent');
        if (sidebar.value !== key) {
            sidebar.value = key;
            mainContent.classList.remove('mx-auto');
        } else {
            sidebar.value = 'none';
            if (!mainContent.classList.contains('mx-auto')) {
                mainContent.classList.add('mx-auto');
            }
        }
        console.log('sidebar value: ', sidebar.value);
    }

    function getBackend() {
        const parts = backend.value.split('/');
        return parts[parts.length - 1];
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

.debug-text {
    display: block;
    text-align: left;
    margin-left: 3px;
    font-family: "Courier New", monospace;
    font-size: small;
}

#sidebar {
    min-width: 200px;
    max-width: 600px;
    position: relative;
}

#sidebar-menu {
    background-color: #fff;
}

.sidebar-item {
    font-size: 20px;
    cursor: pointer;
    width: 50px;
    border-radius: 5px;
}

.sidebar-item:hover {
    background-color: #ccc;
}

.sidebar-item-select {
    background-color: #ddd;
}

.resizer {
    width: 4px;
    cursor: ew-resize;
    height: calc(100vh - 85px - 25px);
    position: absolute;
    top: 0;
    right: 0;
    border-radius: 2px;
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

    #sidebar-menu {
        background-color: #333;
    }

    .sidebar-item:hover {
        background-color: #222;
    }

    .sidebar-item-select {
        background-color: #2a2a2a;
    }

    .resizer {
        background-color: #181818;
    }

    .accordion, .accordion-item, .accordion-header, .accordion-body, .accordion-collapse {
        background-color: #222;
        color: #fff;
    }

    .accordion-item {
        border-color: #454d55;
    }

    .accordion-button {
        background-color: #343a40;
        color: #fff;
    }

    .accordion-button:not(.collapsed) {
        background-color: #212529;
        color: #fff;
    }

    .accordion-button:focus {
        box-shadow: 0 0 0 0.25rem rgba(255, 255, 255, 0.25); /* Light glow for focus */
    }

    .accordion-body .list-group .list-group-item {
        background-color: #222;
        color: #fff;
    }

    .accordion-button::after {
        filter: invert(100%) !important ;
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
    .resizer {
        background-color: gray;
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
