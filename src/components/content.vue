<template>
    <div class="row d-flex justify-content-center my-5 w-100">
        <div class="col-md-10 col-lg-8 col-xl-6">

            <label for="opacaLocationTextInput">{{ config.translations[language].opacaLocation }}</label>
            <input style="border-radius: 5px; margin-left: 20px;" class="col-9 p-2"  type="text" id="opacaLocationTextInput" v-model="opacaRuntimePlatform" />

            <div class="card" id="chat1" style="border-radius: 15px;">
                <div class="card-body" style="overflow-y: scroll; height: 30em; flex-direction: column-reverse"
                    data-mdb-perfect-scrollbar="true" id="chat-container">
                </div>
            </div>

            <div style="text-align: center; margin-top: 10px; margin-bottom: 10px;" class="container justify-content-center">
                <input style="border-radius: 5px;" class="col-9 p-2"  type="text" id="textInput" v-model="config.translations[language].defaultQuestion" @keypress="textInputKeypressCallback"/>
                <input class="btn btn-primary btn-lg col-2 m-1" type="button" @click="textInputButtonCallback" v-model="config.translations[language].submit" />
            </div>

            <SimpleKeyboard @onChange="onChangeSimpleKeyboard" v-if="config.ShowKeyboard" />

            <div style="text-align: center;
                        width: 100%;
                        margin-bottom: 25px;" class='container'>
                <button style="display: inline-block"
                        class="btn btn-primary btn-lg col-3 m-1" :disabled="busy" @click="startRecognition">
                    {{ config.translations[language].speechRecognition }}
                    <div v-if="recording" class="spinner-border md-2" height=2em role="status" />
                </button>

                <button style="display: inline-block;"
                        class="btn btn-secondary btn-lg col-3 m-1" @click="speakLastMessage">
                    {{ config.translations[language].readLastMessage }}
                </button>

                <button style="display: inline-block"
                        class="btn btn-secondary btn-lg col-3 m-1" @click="resetChat()">
                    {{ config.translations[language].resetChat }}
                </button>
            </div>
            
            <br /><br /><br />
        </div>
    </div>

</template>

<script setup>
    import axios from "axios"
    import { marked } from "marked";
    import { onMounted, onUpdated, inject, ref } from "vue";
    import config from '../../config'
    import SimpleKeyboard from "./SimpleKeyboard.vue";

    const opacaRuntimePlatform = config.OpacaRuntimePlatform;
    const backend = config.Backend;

    const language = inject('language');
    let recognition= null;
    let lastMessage = null;
    const speechSynthesis= window.speechSynthesis;
    const recording= ref(false);
    const busy= ref(false);
    const languages= {
        GB: 'en-EN',
        DE: 'de-DE'
    }

    onMounted(() => {
        console.log("mounted")
        createSpeechBubbleAI(config.translations[language.value].welcome, 'startBubble');
    })

    function onChangeSimpleKeyboard(input) {
        document.getElementById("textInput").value = input;
    }

    async function textInputKeypressCallback(event) {
        if (event.key == "Enter") {
            textInputButtonCallback()
        }
    }

    async function textInputButtonCallback() {
        const userInput = document.getElementById("textInput").value
        document.getElementById("textInput").value = ""
        if (userInput != null) {
            //askLlama(userInput)
            askChatGpt(userInput)
        }
    }

    async function initiatePrompt() {
        await sendRequest("POST", `${config.BackendAddress}/${backend}/connect`, {url: opacaRuntimePlatform});
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
        await initiatePrompt()
        createSpeechBubbleUser(userText);
        try {
            const result = await sendRequest("POST", `${config.BackendAddress}/${backend}/query`, {user_query: userText});
            const answer = result.data
            createSpeechBubbleAI(answer);
            //this.scrollDown();            
        } catch (error) {
            createSpeechBubbleAI("Error while fetching data: " + error)
        }
    };

    async function askLlama(userText) {
      const knownServices = await getOpacaAgents()

      chatHistory = [{
          "role": "system",
          "content": "You are a planner that plans a sequence of RESTful API calls to assist with user queries against an API. You will receive a list of known services. These services will include actions. Only use the exact action names from this list. Create a valid HTTP request which would succeed when called. Your http requests will always be of the type POST. If an action requires further parameters, use the most fitting parameters from the user request. If you think there were no fitting parameters in the user request, just create imaginary values for them based on their names. Do not use actions or parameters that are not included in the list. If there are no fitting actions in the list, include within your response the absence of such an action. If the list is empty, include in your response that there are no available services at all. If you think there is a fitting action, then your answer should only include the API call and the required parameters of that call, which will be included in a json style format after the request url. Your answer should only include the request url and the parameters in a JSON format, nothing else. Here is the format in which you should answer:\n" +
              opacaRuntimePlatform + "/invoke/{action_name};{\"parameter_name\": \"value\"}\nYou have to replace {action_name} with the exact name of the most fitting action from the following list: " + knownServices + "\nFurther, replace 'parameter_name' with the actual parameter that the action requires based on the list. The 'value' field should include a value from the user request if such a value was given. If no such value was given, create a fitting imaginary value. An example would look as follows:\n" +
              "user: 'What is the current noise level in the Living Room?'\nYour response: '" + opacaRuntimePlatform + "/invoke/GetNoise;{\"room\": \"Living Room\"}'\n" +
              "Another example without a fitting parameter in the user request could look like follows:\n" +
              "user: 'What is the current humidity?'\nYour response: '" + opacaRuntimePlatform + "/invoke/GetHumidity;{\"room\": \"Office Room\"}'"
        },
        {
          "role": "assistant",
          "content": config.translations[language.value].welcome
        }]
      chatHistory.push({
        "role": "user",
        "content": userText
      });
      createSpeechBubbleUser(userText);
      //this.scrollDown();
      console.log("send to Backend");
      try {
        const planned_action = await sendRequest("POST", "http://10.0.64.101/llama-3/chat", {messages: chatHistory})
        console.log("planned_action: " + planned_action)
        const planned_url = planned_action.split(";")[0]
        const planned_params = JSON.parse(planned_action.split(";")[1])
        console.log("planned_params: " + JSON.stringify(planned_params))
        const answer = await sendRequest("POST", planned_url, planned_params)
        console.log("answer: " + answer)
        createSpeechBubbleAI(answer)
      } catch (error) {
        console.log("Error while fetching data: " + error)
        createSpeechBubbleAI("Error while fetching data: " + error)
      }
    };

    async function startRecognition() {
        recognition = new (webkitSpeechRecognition || SpeechRecognition)();
        recognition.lang = languages[language.value];
        console.log("language: " + languages[language.value]);;
        busy.value = true;
        recognition.onresult = async (event) => {
            const recognizedText = event.results[0][0].transcript;
            askChatGpt(recognizedText)
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
        await sendRequest("POST", `${config.BackendAddress}/${backend}/reset`, null);
        busy.value = false;
    };

    function createSpeechBubbleAI(text, id) {
        lastMessage = text;
        const chat = document.getElementById("chat-container")
        let d1 = document.createElement("div")
        d1.innerHTML += `
        <div id="${id}" class="d-flex flex-row justify-content-start mb-4">
            <img src=/src/assets/Icons/ai.png alt="avatar 1" style="width: 45px; height: 100%;">
            <div class="p-3 ms-3" style="border-radius: 15px; background-color: #39c0ed33;">
                <div id="aiText" class="small mb-0">${formatTextWithCode(text)}</div>
            </div>
        </div>`
        if (!id) {
            document.getElementById('waitBubble').remove()
            busy.value = false;
        }
        chat.appendChild(d1)
    };

    function formatTextWithCode(text) {
        return `<div style="text-align: left">${marked.parse(text.toString())}</div>`
    }

    function createSpeechBubbleUser(text) {
        const chat = document.getElementById("chat-container")
        let d1 = document.createElement("div")
        d1.innerHTML += `
        <div class="d-flex flex-row justify-content-end mb-4">
            <div class="p-3 ms-3" style="border-radius: 15px; background-color: #fbfbfb;">
                <p class="small mb-0">${text}</p>
            </div>
            <img src=/src/assets/Icons/nutzer.png alt="avatar 1" style="width: 45px; height: 100%;">
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
            const utterance = new SpeechSynthesisUtterance(lastMessage);
            speechSynthesis.speak(utterance);
        }
    }
    
    function beforeDestroy() {
        if (recognition) {
            recognition.stop();
        }
    }

</script>

<style scoped>
    #ButtonVoice {
        margin-bottom: 10em;
    }

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
</style>
