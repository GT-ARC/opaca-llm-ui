<template>
    <div class="row d-flex justify-content-center my-5 w-100">
        <div class="col-md-10 col-lg-8 col-xl-6">

            <div class="card" id="chat1" style="border-radius: 15px;">
                <div class="card-header d-flex justify-content-between align-items-center p-3 bg-info text-white border-bottom-0"
                    style="border-top-left-radius: 15px; border-top-right-radius: 15px;">
                    <i class="fas fa-angle-left"></i>
                    <p class="mb-0 fw-bold">AI Chat</p>
                    <i class="fas fa-times"></i>
                </div>
                <div class="card-body" style="overflow-y: scroll; height: 50em; flex-direction: column-reverse"
                    data-mdb-perfect-scrollbar="true" id="chat-container">
                    <div class="d-flex flex-row justify-content-start mb-4">
                        <img src=../assets/Icons/ai.png alt="avatar 1" style="width: 45px; height: 100%;">
                        <div class="p-3 ms-3" style="border-radius: 15px; background-color: #39c0ed33;">
                            <p class="small mb-0">{{
                                config.translations[language].welcome
                            }}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="row fixed-bottom" id="ButtonVoice">
        <div class="row justify-content-center">

            <input type="text" id="textInput" value="Ask me something!" />
            <input type="button" @click="textInputButtonCallback" value="Submit" />

            <button class="btn btn-primary btn-lg col-3 m-1" :disabled="busy" @click="startRecognition">
                {{ recording ? config.translations[language].recognitionActive : config.translations[language].speechRecognition }}
                <div v-if="recording" class="spinner-border text-danger md-2" height=2em role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </button>

            <button class="btn btn-secondary btn-lg col-2 m-1" @click="speakLastMessage">
                {{ config.translations[language].readLastMessage }}
            </button>

            <button class="btn btn-secondary col-1 m-1" @click="resetChat()">
                {{ config.translations[language].resetChat }}
            </button>
        </div>
    </div>
</template>

<script setup>
    import axios from "axios"
    import { onMounted, onUpdated, inject, ref } from "vue";
    import config from '../../config'

    const language = inject('language');
    let chatHistory = [];
    let answer = null;
    let recognition= null;
    const speechSynthesis= window.speechSynthesis;
    const recording= ref(false);
    const busy= ref(false);
    var currentLang = language.value;
    const languages= {
        DE: 'de-DE',
        GB: 'en-EN'
    }
    onMounted(() => {initiatePrompt()})
    onUpdated(() => {
        console.log("updated")
        if (currentLang != language.value) {
            currentLang = language.value;
            resetChat();
            console.log("initiated on update")
        }
    })

    async function textInputButtonCallback() {
        alert("button clicked")
        const userInput = document.getElementById("textInput").value
        alert(userInput)
        if (userInput != null) {
            askChatGpt(userInput)
        } else {
            alert("input was null")
        }
    }

    function initiatePrompt(){
        chatHistory = [{"role": "system", "content": config.translations[language.value].prompt},{"role": "assistant", "content": config.translations[language.value].welcome},];
        console.log("initiatePrompt")
        console.log(chatHistory)
    };

    async function fetchData(message) {
        try {
            const response = await axios.post(config.BackendAddress + '/wapi/chat', {
                prompt: message
            }, {
                headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            });

            console.log("fetchData worked with message: " + response.data);   
            return response.data; // Assuming the response contains data you want to use.
        } catch (error) {
            console.error("Fehler bei der Anfrage an den Server:", error);
            throw error; // You may want to handle the error further up the call stack.
        }
    };

    async function askChatGpt(userText) {
        chatHistory.push({
            "role": "user",
            "content": userText
        });
        createSpeechBubbleUser(userText);
        //this.scrollDown();
        console.log("send to Backend");
        try {
            const answer = await fetchData(chatHistory);
            const messages = answer.messages;
            console.log("answer " + messages[messages.length-1].content);
            chatHistory = messages;
            
            createSpeechBubbleAI(messages[messages.length-1].content);
            //this.scrollDown();
        } catch (error) {
            console.log("Error while fetching data: " + error)
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

    function resetChat() {
        
        document.getElementById("chat-container").innerHTML = '';
        createSpeechBubbleAI(config.translations[language.value].welcome, 'startBubble')
        chatHistory = [{
            "role": "system",
            "content": config.translations[language.value].prompt
        }, {
            "role": "assistant",
            "content": config.translations[language.value].welcome
        },];
        busy.value = false;
        console.log("resetChat")
    };


    function createSpeechBubbleAI(text, id) {
        const chat = document.getElementById("chat-container")
        let d1 = document.createElement("div")
        d1.innerHTML += '<div id="' + id + '" class="d-flex flex-row justify-content-start mb-4"><img src=/src/assets/Icons/ai.png alt="avatar 1" style="width: 45px; height: 100%;"><div class="p-3 ms-3" style="border-radius: 15px; background-color: #39c0ed33;"><p id="aiText" class="small mb-0">' + text + '</p></div></div>'
        if (!id) {
            document.getElementById('waitBubble').remove()
            busy.value = false;
        } else { }

        chat.appendChild(d1)
    };

    function createSpeechBubbleUser(text) {
        const chat = document.getElementById("chat-container")
        let d1 = document.createElement("div")
        d1.innerHTML += '<div class="d-flex flex-row justify-content-end mb-4"><div class="p-3 ms-3" style="border-radius: 15px; background-color: #fbfbfb;"><p class="small mb-0">' + text + '</p></div><img src=/src/assets/Icons/nutzer.png alt="avatar 1" style="width: 45px; height: 100%;"></div>'
        chat.appendChild(d1)
        createSpeechBubbleAI('. . .', 'waitBubble')
    };

    function scrollDown() {
        var ChatDiv = document.getElementById('chat-container')
        var height = ChatDiv[0].scrollHeight;
        ChatDiv.scrollTop(height);
    };

    function speakLastMessage() {
        if (speechSynthesis && chatHistory.length > 0) {
            const lastMessage = chatHistory[chatHistory.length - 1].content;
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
