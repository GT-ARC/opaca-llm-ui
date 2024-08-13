<template>
    <div class="row d-flex justify-content-start my-5 m-1 w-100">

        <div class="col-md-10 col-xl-3 mt-5">
          <div class='container'>
                <button class="btn btn-secondary btn-lg col-5 m-1" @click="debug=!debug">
                    Debug
                </button>
          </div>
            <div class="debug-window-container" v-if="debug" id="chatDebug" style="border-radius: 15px;">
                <div class="card-body" style="overflow-y: scroll; height: 34em; flex-direction: column-reverse"
                    data-mdb-perfect-scrollbar="true" id="debug-console">
                </div>
            </div>
        </div>
        <div class="col-md-10 col-lg-8 col-xl-6">

            <div class="container">
                <div>
                    <label for="opacaUrlInput">{{ config.translations[language].opacaLocation }}</label>
                    <input class="col-7 p-1" type="text" id="opacaUrlInput" v-model="opacaRuntimePlatform" />
                    <button class="btn btn-secondary col-2" @click="initiatePrompt">Connect</button>
                </div>
                <div>
                    <label for="opacaUser" class="small">Username</label>
                    <input class="col-4 small" type="text" id="opacaUser" v-model="opacaUser" />
                    <label for="opacaPwd" class="small">Password</label>
                    <input class="col-4 small" type="password" id="opacaPwd" v-model="opacaPwd" />
                </div>
            </div>
            
            <div class="card" id="chat1" style="border-radius: 15px;">
                <div class="card-body" style="overflow-y: scroll; height: 30em; flex-direction: column-reverse"
                    data-mdb-perfect-scrollbar="true" id="chat-container">
                </div>
            </div>

            <div class="container justify-content-center">
                <input class="col-9 p-2" type="text" id="textInput" v-model="config.translations[language].defaultQuestion" @keypress="textInputCallback"/>
                <button class="btn btn-primary btn-lg col-2 m-1" @click="submitText">
                    {{ config.translations[language].submit }}
                </button>
            </div>

            <SimpleKeyboard @onChange="onChangeSimpleKeyboard" v-if="config.ShowKeyboard" />

            <div class='container'>
                <button class="btn btn-primary btn-lg col-3 m-1" :disabled="busy" @click="startRecognition">
                    {{ config.translations[language].speechRecognition }}
                    <div v-if="recording" class="spinner-border md-2" height=2em role="status" />
                </button>
                <button class="btn btn-secondary btn-lg col-3 m-1" @click="speakLastMessage">
                    {{ config.translations[language].readLastMessage }}
                </button>
                <button class="btn btn-secondary btn-lg col-3 m-1" @click="resetChat">
                    {{ config.translations[language].resetChat }}
                </button>
            </div>

            <br /><br /><br />
        </div>
        <div class="col-md-10 col-xl-3 mt-4" v-if="isOpenAI()">
            <div class="container">
                <div>
                    <label for="apiKey">OpenAI API-Key</label>
                </div>
                <div>
                    <input class="col-10" type="password" id="apiKey" v-model="apiKey">
                </div>
            </div>
        </div>
    </div>

</template>

<script setup>
    import axios from "axios"
    import { marked } from "marked";
    import { onMounted, onUpdated, inject, ref } from "vue";
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
        if (event.key == "Enter") {
            submitText()
        }
    }

    async function submitText() {
        const userInput = document.getElementById("textInput").value
        document.getElementById("textInput").value = ""
        if (userInput != null) {
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
    };

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
    };
    
    async function askChatGpt(userText) {
        createSpeechBubbleUser(userText);
        try {
            const result = await sendRequest("POST", `${config.BackendAddress}/${backend.value}/query`, {user_query: userText, debug: debug.value, api_key: apiKey});
            const answer = result.data.result
            const debugText = result.data.debug
            createSpeechBubbleAI(answer);
            if (debug.value) {
                processDebugInput(debugText).forEach((d) => addDebug(d.text, d.color))
            }
            //this.scrollDown();            
        } catch (error) {
            createSpeechBubbleAI("Error while fetching data: " + error)
        }
    };

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
    };

    async function resetChat() {
        document.getElementById("chat-container").innerHTML = '';
        createSpeechBubbleAI(config.translations[language.value].welcome, 'startBubble')
        await sendRequest("POST", `${config.BackendAddress}/${backend.value}/reset`, null);
        busy.value = false;
    };

    function createSpeechBubbleAI(text, id) {
        lastMessage = text;
        const chat = document.getElementById("chat-container")
        let d1 = document.createElement("div")
        d1.innerHTML += `
        <div id="${id}" class="d-flex flex-row justify-content-start mb-4">
            <img src=/src/assets/Icons/ai.png alt="AI" class="chaticon">
            <div class="p-2 ms-3 small mb-0 chatbubble" style="background-color: #39c0ed33;">
                ${marked.parse(text)}
            </div>
        </div>`
        if (!id) {
            document.getElementById('waitBubble').remove()
            busy.value = false;
        }
        chat.appendChild(d1)
    };

    function createSpeechBubbleUser(text) {
        const chat = document.getElementById("chat-container")
        let d1 = document.createElement("div")
        d1.innerHTML += `
        <div class="d-flex flex-row justify-content-end mb-4">
            <div class="p-2 ms-3 small mb-0 chatbubble" style="background-color: #fbfbfb;">
                ${text}
            </div>
            <img src=/src/assets/Icons/nutzer.png alt="User" class="chaticon">
        </div>`
        chat.appendChild(d1)
        createSpeechBubbleAI('. . .', 'waitBubble')
    };

    function scrollDown() {
        var chatDiv = document.getElementById('chat-container')
        var height = chatDiv[0].scrollHeight;
        chatDiv.scrollTop(height);
    };

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
            "Final Answer:": "#0f0"
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

    function isOpenAI() {
        return ! backend.value.includes("llama")
    }
    
    function beforeDestroy() {
        if (recognition) {
            recognition.stop();
        }
    }

</script>

<style>

    input {
        border-radius: 5px;
        margin: 10px;
    }

    .chatbubble {
        border-radius: 10px;
        text-align: left
    }

    .chaticon {
        width: 45px;
        height: 100%;
    }

    .debug-window-container {
        background-color: #000; /* Black background */
        border-radius: 15px;
        overflow: hidden;
    }

    .debug-text {
        display: block;
        text-align: left;
        margin-left: 3px;
        font-family: "Courier New", monospace;
        font-size: small;
    }

   /* NONE of those styles seem to have ANY effect...
    #chat1 .form-outline .form-control~.form-notch div {
        pointer-events: none;
        border: 1px solid;
        border-color: #eee;
        box-sizing: border-box;
        background: transparent;
    }

    #chat1 .form-outline .form-control~.form-notch .form-notch-leading {
        left: 0;
        top: 0;
        height: 100%;
        border-right: none;
        border-radius: .65rem 0 0 .65rem;
    }

    #chat1 .form-outline .form-control~.form-notch .form-notch-middle {
        flex: 0 0 auto;
        max-width: calc(100% - 1rem);
        height: 100%;
        border-right: none;
        border-left: none;
    }

    #chat1 .form-outline .form-control~.form-notch .form-notch-trailing {
        flex-grow: 1;
        height: 100%;
        border-left: none;
        border-radius: 0 .65rem .65rem 0;
    }

    #chat1 .form-outline .form-control:focus~.form-notch .form-notch-leading {
        border-top: 0.125rem solid #39c0ed;
        border-bottom: 0.125rem solid #39c0ed;
        border-left: 0.125rem solid #39c0ed;
    }

    #chat1 .form-outline .form-control:focus~.form-notch .form-notch-leading,
    #chat1 .form-outline .form-control.active~.form-notch .form-notch-leading {
        border-right: none;
        transition: all 0.2s linear;
    }

    #chat1 .form-outline .form-control:focus~.form-notch .form-notch-middle {
        border-bottom: 0.125rem solid;
        border-color: #39c0ed;
    }

    #chat1 .form-outline .form-control:focus~.form-notch .form-notch-middle,
    #chat1 .form-outline .form-control.active~.form-notch .form-notch-middle {
        border-top: none;
        border-right: none;
        border-left: none;
        transition: all 0.2s linear;
    }

    #chat1 .form-outline .form-control:focus~.form-notch .form-notch-trailing {
        border-top: 0.125rem solid #39c0ed;
        border-bottom: 0.125rem solid #39c0ed;
        border-right: 0.125rem solid #39c0ed;
    }

    #chat1 .form-outline .form-control:focus~.form-notch .form-notch-trailing,
    #chat1 .form-outline .form-control.active~.form-notch .form-notch-trailing {
        border-left: none;
        transition: all 0.2s linear;
    }

    #chat1 .form-outline .form-control:focus~.form-label {
        color: #39c0ed;
    }

    #chat1 .form-outline .form-control~.form-label {
        color: #bfbfbf;
    }
    */
</style>
