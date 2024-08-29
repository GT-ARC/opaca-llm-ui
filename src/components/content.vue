<template>
    <div class="row d-flex justify-content-start my-4 w-100">

        <!-- Left Container: Configuration, Debug-Output -->
        <aside class="col-xl-4 d-flex flex-column" style="height:calc(100vh - 85px)">
            <div class="container">
                <div>
                    <label for="opacaUrlInput">{{ config.translations[language].opacaLocation }}</label>
                    <input class="col-5" type="text" id="opacaUrlInput" v-model="opacaRuntimePlatform" />
                    <button class="btn btn-primary btn-sm" @click="initiatePrompt">Connect</button>
                </div>
                <div class="small">
                    <label for="opacaUser">Username</label>
                    <input class="col-3" type="text" id="opacaUser" v-model="opacaUser" />
                    <label for="opacaPwd">Password</label>
                    <input class="col-3" type="password" id="opacaPwd" v-model="opacaPwd" />
                </div>
            </div>
            <div class="container small">
                <label for="apiKey">OpenAI API-Key</label>
                <input class="col-7" type="password" id="apiKey" v-model="apiKey">
            </div>
            <div class='container'>
                <button class="btn btn-secondary btn-sm col-5 m-1" @click="debug=!debug">
                    {{ debug ? "Hide Debug Output" : "Show Debug Output"}}
                </button>
            </div>
            <div class="container debug-window-container flex-grow-1" v-if="debug" id="chatDebug"
                 style="margin: 10px; border-radius: 15px; overflow-y: auto;">
                <div class="card-body" style="flex-direction: column-reverse" id="debug-console"/>
            </div>
        </aside>

        <!-- Main Container: Chat Window, Text Input -->
        <main class="col-xl-8 d-flex flex-column position-relative" style="height:calc(100vh - 85px)">

            <!-- Chat Window -->
            <div class="container card flex-grow-1" id="chat1" style="border-radius: 15px; overflow-y: auto;">
                <div class="card-body" style="flex-direction: column-reverse" id="chat-container"/>
            </div>

            <!-- Input and Submit Button -->
            <div class="container">
                <input class="col-9" type="text" id="textInput" v-model="config.translations[language].defaultQuestion" @keypress="textInputCallback"/>
                <button class="btn btn-primary" @click="submitText">
                    {{ config.translations[language].submit }}
                </button>
            </div>

            <!-- Simple Keyboard -->
            <SimpleKeyboard @onChange="onChangeSimpleKeyboard" v-if="config.ShowKeyboard" />

            <!-- Button Group Container -->
            <div class='container'>
                <button class="btn btn-primary col-2 m-1" :disabled="busy" @click="startRecognition">
                    {{ config.translations[language].speechRecognition }}
                    <div v-if="recording" class="spinner-border md-2" height=2em role="status" />
                </button>
                <button class="btn btn-secondary col-2 m-1" @click="speakLastMessage">
                    {{ config.translations[language].readLastMessage }}
                </button>
                <button class="btn btn-secondary col-2 m-1" @click="resetChat">
                    {{ config.translations[language].resetChat }}
                </button>
            </div>
        </main>
    </div>

</template>

<script setup>
    import axios from "axios"
    import { marked } from "marked";
    import { onMounted, inject, ref } from "vue";
    import config from '../../config'
    import SimpleKeyboard from "./SimpleKeyboard.vue";

    let opacaRuntimePlatform = config.OpacaRuntimePlatform;
    let opacaUser = "";
    let opacaPwd = "";
    let apiKey = "";
    
    const backend = inject('backend');
    const language = inject('language');
    let recognition= null;
    let lastMessage = null;
    const speechSynthesis= window.speechSynthesis;
    const recording= ref(false);
    const busy= ref(false);
    const debug = ref(false);
    const languages= {
        GB: 'en-EN',
        DE: 'de-DE'
    }

    onMounted(() => {
        console.log("mounted")
        createSpeechBubbleAI(config.translations[language.value].welcome, 'startBubble');
        initiatePrompt();
    })

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
        if (res.data) {
            createSpeechBubbleAI("Connected!", "connect")
        } else {
            createSpeechBubbleAI("Failed to connect...", "connect")
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
            const result = await sendRequest("POST", `${config.BackendAddress}/${backend.value}/query`, {user_query: userText, debug: debug.value, api_key: apiKey});
            const answer = result.data.result
            const debugText = result.data.debug
            createSpeechBubbleAI(answer);
            if (debug.value) {
                processDebugInput(debugText).forEach((d) => addDebug(d.text, d.color))
                scrollDown(true)
            }
            scrollDown(false);
        } catch (error) {
            createSpeechBubbleAI("Error while fetching data: " + error)
            scrollDown(false);
        }
    }

    async function startRecognition() {
        // TODO this does not seem to work for me
        recognition = new (webkitSpeechRecognition || SpeechRecognition)();
        recognition.lang = languages[language.value];
        console.log("language: " + languages[language.value]);
        busy.value = true;
        recognition.onresult = async (event) => {
            const recognizedText = event.results[0][0].transcript;
            await askChatGpt(recognizedText)
        };
        recognition.onend = () => {
            recording.value = false;
            console.log("Recognition ended.");
        };
        recognition.start();
        recording.value = true;
    }

    async function resetChat() {
        document.getElementById("chat-container").innerHTML = '';
        createSpeechBubbleAI(config.translations[language.value].welcome, 'startBubble')
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
            document.getElementById('waitBubble').remove()
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
            console.log(lastMessage)
            // TODO this does not seem to work for me
            const utterance = new SpeechSynthesisUtterance(lastMessage);
            speechSynthesis.speak(utterance);
        }
    }

    function processDebugInput(input) {
        const keywordColors = {
            "Query:": "#fff",
            "Planner:": "#f00",
            "API Selector:": "#ff0",
            "Caller:": "#00f",
            "Final Answer:": "#0f0",
            "Tool": "#f00",
            "AI Answer:": "#0f0",
        }
        const regex = new RegExp(`(${Object.keys(keywordColors).join('|')})`, 'g')

        const parts = input.split(regex).filter(Boolean)
        const result = []
        for (let i = 0; i < parts.length; i += 2) {
            const keyword = parts[i]
            const text = parts[i + 1] || ""
            const color = keywordColors[keyword] || "#fff";
            result.push({text: keyword + text, color: color})
        }

        return result
    }

    function addDebug(text, color) {
        const debugChat = document.getElementById("debug-console")
        let d1 = document.createElement("div")
        d1.className = "debug-text"
        d1.textContent = text
        d1.style.color = color
        debugChat.append(d1)
    }
    
    function beforeDestroy() {
        if (recognition) {
            recognition.stop();
        }
    }

</script>

<style>
    @media (prefers-color-scheme: dark) {
        body {
            color: #fff;
            background-color: #222;
        }
        #chat1 {
            color: #fff;
            background-color: #444;
        }
    }

    input {
        border-radius: 5px;
        margin: 10px;
    }

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

    .debug-window-container {
        background-color: #000; /* Black background */
        overflow: hidden;
    }

    .debug-text {
        display: block;
        text-align: left;
        margin-left: 3px;
        font-family: "Courier New", monospace;
        font-size: small;
    }
</style>
