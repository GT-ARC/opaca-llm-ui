<template>
    <div class="d-flex justify-content-start my-4 w-100">

        <!-- Left Container: Configuration, Debug-Output -->
        <div v-show="isSidebarOpen()">
            <aside id="sidebar"
               class="container-fluid d-flex flex-column px-4"
               style="height: calc(100vh - 85px); width: calc(100vw / 4)">

            <div id="sidebarConfig" class="container d-flex flex-column">
                <div class="p-2 text-start">
                    <input id="opacaUrlInput" type="text"
                           class="form-control m-0"
                           v-model="opacaRuntimePlatform"
                           :placeholder="config.translations[language].opacaLocation" />
                </div>

                <div class="p-2 text-start">
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

                <div class="p-2 text-start" v-if="config.ShowApiKey">
                    <input id="apiKey" type="password"
                           class="form-control m-0"
                           v-model="apiKey"
                           placeholder="OpenAI API Key" />
                </div>

                <div class="text-center p-2">
                    <button class="btn btn-primary w-100" @click="initiatePrompt"><i class="fa fa-link me-1"/>Connect</button>
                </div>

                <div class="form-check p-2 text-start">
                    <input class="form-check-input ms-0 me-1" type="checkbox" value="" id="showDebugOutput" v-model="debug">
                    <label class="form-check-label" for="showDebugOutput">Show Debug Output</label>
                </div>
            </div>

            <div v-show="debug" id="chatDebug"
                 class="container flex-grow-1 mb-4 p-2 rounded rounded-4">
                <div id="debug-console" class="flex-row-reverse text-start"/>
            </div>

            <div class="resizer me-1" id="resizer" />
        </aside>
        </div>
        <!-- Main Container: Chat Window, Text Input -->
        <main id="mainContent" class="d-flex flex-column flex-grow-1 pe-4"
              style="height:calc(100vh - 85px); max-width: calc(100vw * 3 / 4);">

            <!-- Chat Window -->
            <div class="container card flex-grow-1" id="chat1" style="border-radius: 15px; overflow-y: auto;">
                <div class="card-body" style="flex-direction: column-reverse" id="chat-container"/>
            </div>

            <div class="container p-0">
                <div class="input-group mt-2 mb-4">
                    <input id="textInput" placeholder="Type here ..."
                           class="form-control p-2 rounded-start-2"
                           :value="config.translations[language].defaultQuestion"
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

    const backend = inject('backend');
    const language = inject('language');
    const sidebarOpen = inject('sidebarOpen');
    let recognition= null;
    let lastMessage = null;
    const speechSynthesis = window.speechSynthesis;
    const recording = ref(false);
    const busy = ref(false);
    const debug = ref(false);
    const autoSpeakNextMessage = ref(false);
    const languages = {
        GB: 'en-GB',
        DE: 'de-DE'
    }
    const darkScheme = ref(false);

    onMounted(() => {
        console.log("mounted")
        updateTheme()
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updateTheme);
        createSpeechBubbleAI(config.translations[language.value].welcome, 'startBubble');
        initiatePrompt();
        setupResizableSidebar();
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
            alert(text)
        } else if (res.status === 403) {
            alert(config.translations[language.value].unauthorized)
        } else {
            alert(config.translations[language.value].unreachable)
        }
    }

    async function sendRequest(method, url, body) {
        try {
            const response = await axios.request({
                method: method,
                url: url,
                data: body,
                headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            });
            return response;
        } catch (error) {
            throw error;
        }
    }

    async function askChatGpt(userText) {
        createSpeechBubbleUser(userText);
        try {
            const result = await sendRequest("POST", `${config.BackendAddress}/${backend.value}/query`, {user_query: userText, debug: true, api_key: apiKey});
            const answer = result.data.result;
            const debugText = result.data.debug;
            createSpeechBubbleAI(answer);
            processDebugInput(debugText)
                    .forEach((d) => addDebug(d.text, d.color));
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
        await sendRequest("POST", `${config.BackendAddress}/${backend.value}/reset`, null);
        busy.value = false;
    }

    function createSpeechBubbleAI(text, id) {
        lastMessage = text;
        const chat = document.getElementById("chat-container")
        let d1 = document.createElement("div")
        d1.innerHTML += `
        <div id="${id}" class="d-flex flex-row justify-content-start mb-4">
            <img src=/src/assets/Icons/ai.png alt="AI" class="chaticon">
            <div class="p-2 ms-3 small mb-0 chatbubble chat-ai">
                ${marked.parse(text)}
            </div>
        </div>`
        if (!id) {
            const waitBubble = document.getElementById('waitBubble');
            if (waitBubble) waitBubble.remove();
            busy.value = false;
        }
        chat.appendChild(d1)
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

    function processDebugInput(input) {
        // color schemes for modes [dark, light]
        const keywordColors = {
            // RestGPT
            "Query:": ["#fff", "#000"],
            "Planner:": ["#f00", "#9c0000"],
            "API Selector:": ["#ff0", "#bf6e00"],
            "Caller:": ["#00f", "#0000b1"],
            "Final Answer:": ["#0f0", "#007300"],
            // Tools
            "Tool": ["#f00", "#9c0000"],
            "AI Answer:": ["#0f0", "#007300"],
            // Simple
            "user:": ["#fff", "#000"],
            "assistant:": ["#88f", "#434373"],
            "system:": ["#ff8", "#71713d"],
        }
        const regex = new RegExp(`(${Object.keys(keywordColors).join('|')})`, 'g')
        const parts = input.split(regex).filter(Boolean);
        const result = [];
        for (let i = 0; i < parts.length; i += 2) {
            const keyword = parts[i]
            const text = parts[i + 1] || ""
            const color = (keywordColors[keyword] ?? ["#fff", "#000"])[darkScheme.value ? 0 : 1];
            result.push({text: keyword + text, color: color})
        }
        return result;
    }

    function updateDebugColors() {
        const debugElements = document.querySelectorAll('.debug-text');
        debugElements.forEach((element) => {
            const text = element.innerText || element.textContent;
            element.style.color = processDebugInput(text)[0]["color"];
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

    function isSidebarOpen() {
        return sidebarOpen.value;
    }

</script>

<style>
.chatbubble {
    border-radius: 10px;
    text-align: left
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

.resizer {
    width: 4px;
    cursor: ew-resize;
    height: calc(100vh - 85px - 25px);
    position: absolute;
    top: 0;
    right: 0;
    border-radius: 2px;
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

    .resizer {
        background-color: #181818;
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
}

</style>
