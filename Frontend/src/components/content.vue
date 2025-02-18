<template>
    <div class="d-flex justify-content-start flex-grow-1 w-100">

        <Sidebar :backend="backend" :language="language" ref="sidebar"
                 @language-change="handleLanguageChange"
                 @select-question="askChatGpt"
                 @category-selected="updateSelectedCategory"
                 @api-key-change="(newValue) => this.apiKey = newValue"
                 @on-sidebar-toggle="this.onSidebarToggle"/>

        <!-- Recording Popup -->
        <RecordingPopup
            v-model:show="showRecordingPopup"
            :language="selectedLanguage"
            @transcription-complete="handleTranscriptionComplete"
            @send-message="handleSendMessage"
            @error="handleRecordingError"
        />

        <!-- Main Container: Chat Window, Text Input -->
        <main id="mainContent" class="mx-auto"
              v-bind:class="{ 'd-flex flex-column flex-grow-1': this.isMainContentVisible(), 'd-none': !this.isMainContentVisible() }">

            <!-- Chat Window -->
            <div class="container-fluid flex-grow-1 px-0" id="chat1">
                <div class="card-body" id="chat-container"/>
                <div v-show="showExampleQuestions" class="sample-questions">
                    <div v-for="(question, index) in getCurrentCategoryQuestions()"
                         :key="index"
                         class="sample-question"
                         @click="askChatGpt(question.question)">
                        {{ question.icon }} <br> {{ question.question }}
                    </div>
                </div>
            </div>

            <!-- Input Area -->
            <div class="input-container">
                <div class="input-group">
                      <textarea id="textInput"
                                v-model="textInput"
                                :placeholder="getConfig().translations[language].inputPlaceholder || 'Send a message...'"
                                class="form-control overflow-hidden"
                                rows="1"
                                @input="autoResize"
                                @keypress="textInputCallback"></textarea>

                    <!-- user has entered text into message box -> send button available -->
                    <button type="button"
                            v-if="this.isSendAvailable()"
                            class="btn btn-primary"
                            @click="submitText"
                            :disabled="isBusy">
                        <i class="fa fa-paper-plane"/>
                    </button>
                    <button type="button"
                            v-if="this.isSpeechRecognitionAvailable()"
                            class="btn btn-outline-primary"
                            @click="startRecognition"
                            :disabled="isBusy">
                        <i v-if="isRecording" class="fa fa-spinner fa-spin"/>
                        <i v-else class="fa fa-microphone"/>
                    </button>
                    <button type="button"
                            v-if="this.isResetAvailable()"
                            class="btn btn-outline-danger"
                            @click="resetChat"
                            :disabled="isBusy">
                        <i class="fa fa-refresh"/>
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
import {sendRequest, shuffleArray} from "../utils.js";
import RecordingPopup from './RecordingPopup.vue';
import {debugColors, defaultDebugColors, debugLoadingMessages} from '../config/debug-colors.js';

import { useDevice } from "../useIsMobile.js";

export default {
    name: 'main-content',
    components: {
        Sidebar,
        SimpleKeyboard,
        RecordingPopup
    },
    props: {
        backend: String,
        language: String,
    },
    setup() {
        const { isMobile, screenWidth } = useDevice()
        return { isMobile, screenWidth };
    },
    data() {
        return {
            apiKey: '',
            textInput: '',
            recognition: null,
            lastMessage: null,
            messageCount: 0,
            speechSynthesis: window.SpeechSynthesis,
            isRecording: false,
            isBusy: false,
            showExampleQuestions: true,
            autoSpeakNextMessage: false,
            isDarkScheme: false,
            showRecordingPopup: false,
            selectedLanguage: 'english',
            deviceInfo: '',
            selectedCategory: 'Information & Upskilling',
            voiceServerConnected: false,
            statusMessages: {}, // Track status messages by messageCount
            accumulatedContent: '',
            isSidebarActive: false,
        }
    },
    watch: {
        language: {
            immediate: true,
            handler(newVal) {
                if (newVal === 'GB') {
                    this.selectedLanguage = 'english';
                } else if (newVal === 'DE') {
                    this.selectedLanguage = 'german';
                }
            }
        }
    },
    methods: {
        getConfig() {
            return conf;
        },

        updateTheme() {
            // Check if dark color scheme is preferred
            this.isDarkScheme = window.matchMedia('(prefers-color-scheme: dark)').matches;
            this.updateDebugColors(this.isDarkScheme)
        },

        onChangeSimpleKeyboard(input) {
            this.textInput = input;
        },

        async textInputCallback(event) {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                await this.submitText();
            }
        },

        async submitText() {
            const userInput = this.textInput;
            if (this.textInput) {
                this.textInput = '';
                await this.askChatGpt(userInput);
            }
        },

        async askChatGpt(userText) {
            this.isFinished = false;
            this.showExampleQuestions = false;
            const currentMessageCount = this.messageCount;
            this.messageCount++;
            const debugMessageLength = this.$refs.sidebar.debugMessages.length;
            this.accumulatedContent = ''; // Reset accumulated content for new message
            this.createSpeechBubbleUser(userText);
            try {
                if (['tool-llm-openai', 'rest-gpt-openai', 'self-orchestrated'].includes(this.getBackend())) {
                    // Initialize with preparing message
                    this.statusMessages[currentMessageCount] = new Map();
                    const systemMessage = this.getDebugLoadingMessage('preparing');
                    this.statusMessages[currentMessageCount].set('preparing', systemMessage + ' ...');
                    this.editTextSpeechBubbleAI(Array.from(this.statusMessages[currentMessageCount].values()).join('\n'), currentMessageCount);
                    
                    // Show loading indicator for initial message
                    const aiBubble = document.getElementById(`${currentMessageCount}`);
                    if (aiBubble) {
                        const loadingContainer = aiBubble.querySelector("#loadingContainer .loader");
                        if (loadingContainer) {
                            loadingContainer.classList.remove('hidden');
                        }
                    }
                    
                    const preparingColor = this.getDebugColor('preparing', this.isDarkScheme);
                    this.editAnimationSpeechBubbleAI(currentMessageCount, true, preparingColor);
                    this.scrollDown(false);

                    const socket = new WebSocket(`${conf.BackendAddress}/${this.getBackend()}/query_stream`);

                    socket.onmessage = (event) => {
                        const result = JSON.parse(JSON.parse(event.data)); // YEP, THAT MAKES NO SENSE (WILL CHANGE SOON TM)
                        if (result.hasOwnProperty("agent")) {
                            // Mark system preparation as complete on first agent message
                            if (this.statusMessages[currentMessageCount].has('preparing')) {
                                const preparingMessage = this.getDebugLoadingMessage('preparing');
                                this.statusMessages[currentMessageCount].set('preparing', preparingMessage + ' ✓');
                            }

                            if (result.agent === 'assistant') {
                                // Accumulate content for streaming without coloring
                                if (!this.accumulatedContent) {
                                    this.accumulatedContent = '';
                                    // Hide loading indicator on first chunk
                                    const aiBubble = document.getElementById(`${currentMessageCount}`);
                                    if (aiBubble) {
                                        const loadingContainer = aiBubble.querySelector("#loadingContainer .loader");
                                        if (loadingContainer) {
                                            loadingContainer.classList.add('hidden');
                                        }
                                    }
                                }
                                this.accumulatedContent += result.content;
                                // Apply markdown parsing to the entire accumulated content
                                const formattedContent = marked.parse(this.accumulatedContent);
                                this.editTextSpeechBubbleAI(formattedContent, currentMessageCount, true, false); // Pass false to prevent loading indicator changes
                                // Remove any active glow animation for assistant content
                                this.editAnimationSpeechBubbleAI(currentMessageCount, false);
                            } else {
                                // Agent messages are intermediate results
                                this.addDebugToken(result, currentMessageCount);
                            }
                            this.scrollDown(true);
                        } else {
                            // Last message received should be final response
                            this.editTextSpeechBubbleAI(result.content, currentMessageCount);
                            this.editAnimationSpeechBubbleAI(currentMessageCount, false);

                            // Hide loading indicator
                            const aiBubble = document.getElementById(`${currentMessageCount}`);
                            if (aiBubble) {
                                const loadingContainer = aiBubble.querySelector("#loadingContainer .loader");
                                if (loadingContainer) {
                                    loadingContainer.classList.add('hidden');
                                }
                            }

                            // Handle Debug Message in Chat Bubble
                            this.bindDebugMsgToBubble(currentMessageCount, debugMessageLength)
                        }
                    };

                    socket.onopen = () => {
                        const inputData = {user_query: userText, api_key: this.apiKey};
                        socket.send(JSON.stringify(inputData));
                    };

                    socket.onclose = () => {
                        if (!this.isFinished) {
                            this.handleUnexpectedConnectionClosed("❗It seems there was a problem during the response generation...", currentMessageCount, debugMessageLength)
                        }
                        console.log("WebSocket connection closed");
                    };

                    socket.onerror = (error) => {
                        if (!this.isFinished) {
                            this.handleUnexpectedConnectionClosed("❗I encountered the following error during the response generation: " + error.toString(), currentMessageCount, debugMessageLength)
                        }
                        console.log("Received error: ", error)
                    }
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
                this.editTextSpeechBubbleAI("Error while fetching data: " + error, currentMessageCount);
                this.editAnimationSpeechBubbleAI(currentMessageCount, false);
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
            this.showRecordingPopup = true;
        },

        handleTranscriptionComplete(text) {
            if (text) {
                this.textInput = text;
            }
        },

        handleSendMessage(text) {
            if (text) {
                this.textInput = "";
                this.askChatGpt(text);
            }
        },

        handleRecordingError(error) {
            console.error('Recording error:', error);
            alert('Error recording audio: ' + error.message);
        },

        handleLanguageChange(newLanguage) {
            this.selectedLanguage = newLanguage;
            // Update the main app language based on the selected language
            if (newLanguage === 'english') {
                this.$emit('update:language', 'GB');
            } else if (newLanguage === 'german') {
                this.$emit('update:language', 'DE');
            }
        },

        async resetChat() {
            document.getElementById("chat-container").innerHTML = '';
            this.$refs.sidebar.debugMessages = []
            this.abortSpeaking();
            if (!this.isMobile) {
                // dont add in mobile view, as welcome message + sample questions is too large for mobile screen
                this.createSpeechBubbleAI(conf.translations[this.language].welcome, 'startBubble');
            }
            this.showExampleQuestions = true;
            await sendRequest("POST", `${conf.BackendAddress}/reset`);
            this.isBusy = false;
        },

        createSpeechBubbleAI(text, id, isPreformatted = false) {
            this.lastMessage = text;
            const chat = document.getElementById("chat-container");
            let d1 = document.createElement("div");
            let debugId = `debug-${id}`;
            const isStatusMessage = text.includes('...') || text.includes('✓');
            
            // Format the initial text appropriately
            const formattedText = isStatusMessage 
                ? text.split('\n')
                    .filter(line => line.trim() !== '')
                    .map(line => `<div class="status-line">${line}</div>`)
                    .join('')
                : isPreformatted ? text : marked.parse(text);

            d1.innerHTML = `
            <div id="${id}" class="d-flex flex-row justify-content-start mb-4">
                <div class="chaticon">
                    <img src="/src/assets/Icons/ai.png" alt="AI">
                </div>
                <div id="chatBubble" class="p-3 small mb-0 chatbubble chat-ai">
                    <div class="d-flex flex-row justify-content-start message-content">
                        <div id="loadingContainer"><div class="loader hidden"></div></div>
                        <div id="messageContainer" class="message-text">${formattedText}</div>
                    </div>
                    <div id="${debugId}-toggle" class="debug-toggle" style="display: none; cursor: pointer; font-size: 10px;">
                        <img src=/src/assets/Icons/double_down_icon.png class="double-down-icon" alt=">>" width="10px" height="10px" style="transform: none"/>
                        debug
                    </div>
                    <hr id="${debugId}-separator" class="debug-separator" style="display: none;">
                    <div id="${debugId}-text" v-if="debugExpanded" class="bubble-debug-text" style="display: none;"/>
                </div>
            </div>`;

            this.isBusy = false;
            chat.appendChild(d1);

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
            d1.innerHTML = `
                <div class="d-flex flex-row justify-content-end mb-4">
                    <div class="chatbubble chat-user">
                        ${text}
                    </div>
                    <div class="chaticon">
                        <img src="/src/assets/Icons/nutzer.png" alt="User">
                    </div>
                </div>`;
            chat.appendChild(d1)
            this.scrollDown(false)
        },

        bindDebugMsgToBubble(currentMessageCount, debugMessageLength) {
            // Append the debug messages generated during this request to the ai message bubble
            const aiBubble = document.getElementById(`debug-${currentMessageCount}-text`);
            const debugMessages = this.$refs.sidebar.debugMessages;
            if (aiBubble) {
                for (let i = debugMessageLength; i < debugMessages.length; i++) {
                    let d1 = document.createElement("div");
                    d1.className = "bubble-debug-text";
                    d1.textContent = debugMessages.at(i).text;
                    d1.style.color = debugMessages.at(i).color;
                    d1.dataset.type = debugMessages.at(i).type;
                    aiBubble.append(d1);
                }
            }

            // Make expand debug button appear
            const debugToggle = document.getElementById(`debug-${currentMessageCount}-toggle`);
            debugToggle.style.display = 'block';
            this.scrollDown(false);
            this.isFinished = true
        },

        handleUnexpectedConnectionClosed(message, currentMessageCount, debugMessageLength) {
            this.editTextSpeechBubbleAI(message, currentMessageCount);
            this.editAnimationSpeechBubbleAI(currentMessageCount, false);
            this.bindDebugMsgToBubble(currentMessageCount, debugMessageLength)

            const aiBubble = document.getElementById(`${currentMessageCount}`);
            const messageContainer = aiBubble.querySelector("#messageContainer");
            messageContainer.style.color = "red"

            const loadingContainer = aiBubble.querySelector("#loadingContainer .loader");
            if (loadingContainer) {
                loadingContainer.classList.add('hidden');
            }
        },

        scrollDown(debug) {
            const chatDiv = debug
                    ? document.getElementById('debug-console')
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
            return (debugColors[agentName] ?? defaultDebugColors)[darkScheme ? 0 : 1];
        },

        getDebugLoadingMessage(agentName) {
            // Use the current language (GB or DE) to get the appropriate message
            return debugLoadingMessages[this.language]?.[agentName] ?? debugLoadingMessages['GB'][agentName];
        },

        addDebugToken(agent_message, messageCount) {
            const color = this.getDebugColor(agent_message["agent"], this.isDarkScheme);
            const message = this.getDebugLoadingMessage(agent_message["agent"]);

            // Initialize status messages for this messageCount if not exists
            if (!this.statusMessages[messageCount]) {
                this.statusMessages[messageCount] = new Map();
            }

            // Update status message for this agent
            if (message) {
                // Mark previous agent's message as completed
                for (const [agent, status] of this.statusMessages[messageCount].entries()) {
                    if (status.endsWith('...')) {
                        this.statusMessages[messageCount].set(agent, status.replace('...', '✓'));
                    }
                }
                // Set current agent's message
                this.statusMessages[messageCount].set(agent_message["agent"], message + ' ...');
            }

            // Build cumulative status message from all agents
            const statusMessage = Array.from(this.statusMessages[messageCount].values()).join('\n');
            
            // Change the loading message and color depending on the currently received agent message
            this.editTextSpeechBubbleAI(statusMessage, messageCount);
            this.editAnimationSpeechBubbleAI(messageCount, true, color);

            if (agent_message["tools"] && agent_message["tools"].length > 0) {
                const tool_output = agent_message["tools"].map(tool =>
                    `Tool ${tool["id"]}:\nName: ${tool["name"]}\nArguments: ${JSON.stringify(tool["args"])}\nResult: ${tool["result"]}`
                ).join("\n\n")
                this.addDebug(tool_output, color, agent_message["agent"] + "-Tools");

            } else {
                this.addDebug(agent_message["content"], color, agent_message["agent"]);
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
                const content = [
                    `${message["agent"]}:`,
                    message["tools"].length > 0 ? message["tools"].join('\n') : message["content"],
                    `Execution time: ${message["execution_time"].toFixed(2)}s`
                ].join('\n');
                
                this.addDebug(content, color, message["agent"]);

                // Add the formatted debug text to the associated speech bubble
                const messageBubble = document.getElementById(`debug-${messageCount}-text`)
                if (messageBubble) {
                    let d1 = document.createElement("div")
                    d1.className = "bubble-debug-text"
                    d1.textContent = content
                    d1.style.color = color
                    d1.dataset.type = message["agent"]
                    messageBubble.append(d1)
                }
            }
        },

        updateDebugColors(darkScheme) {
            const debugElements = document.querySelectorAll('.debug-text, .bubble-debug-text');
            debugElements.forEach((element) => {
                element.style.color = this.getDebugColor(element.dataset.type ?? "", darkScheme);
            });
        },

        addDebug(text, color, type) {
            const debugMessages = this.$refs.sidebar.debugMessages;

            // If the message includes tools, the message needs to be replaced instead of appended
            if (debugMessages.length > 0 && debugMessages[debugMessages.length - 1].type === "Tool Generator-Tools" && text) {
                debugMessages[debugMessages.length - 1] = {
                    text: text,
                    color: color,
                    type: "Tool Generator-Tools",
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

        editAnimationSpeechBubbleAI(id, active, color) {
            const aiBubble = document.getElementById(`${id}`);
            if (!aiBubble) return;

            if (!document.querySelector(`#move-glow`)) {
                // Create a style block for the custom animation
                const style = document.createElement("style");
                style.id = "move-glow";
                style.innerHTML = `
                    @keyframes move-glow {
                        0%, 100% {
                            box-shadow: 0 0 8px var(--glow-color-1, #ffffff33);
                        }
                        50% {
                            box-shadow: 0 0 15px var(--glow-color-2, #ffffff73);
                        }
                    }
                `;
                document.head.appendChild(style);
            }

            const chatBubble = aiBubble.querySelector("#chatBubble");
            if (!chatBubble) return;

            if (active) {
                if (color === "#ffffff") {
                    // Initial phase - use primary color with more intensity
                    chatBubble.style.setProperty("--glow-color-1", "var(--primary-light)40");
                    chatBubble.style.setProperty("--glow-color-2", "var(--primary-light)90");
                } else {
                    chatBubble.style.setProperty("--glow-color-1", `${color}40`);
                    chatBubble.style.setProperty("--glow-color-2", `${color}90`);
                }
                chatBubble.style.animation = "move-glow 3s infinite";
            } else {
                chatBubble.style.animation = "";
            }
        },

        editTextSpeechBubbleAI(text, id, isPreformatted = false, updateLoading = true) {
            const aiBubble = document.getElementById(`${id}`);
            if (!aiBubble) {
                // If the bubble doesn't exist yet, create it
                this.createSpeechBubbleAI(text, id);
                return;
            }

            const messageContainer = aiBubble.querySelector("#messageContainer");
            if (!messageContainer) return;

            // Check if this is a status message (contains checkmarks or ellipsis)
            const isStatusMessage = text.includes('...') || text.includes('✓');
            
            if (isStatusMessage) {
                // Format status messages with clean line breaks
                const formattedText = text.split('\n')
                    .filter(line => line.trim() !== '')
                    .map(line => `<div class="status-line">${line}</div>`)
                    .join('');
                messageContainer.innerHTML = formattedText;

                // Show loading indicator for active status only if we should update loading
                if (updateLoading) {
                    const loadingContainer = aiBubble.querySelector("#loadingContainer .loader");
                    if (loadingContainer) {
                        loadingContainer.classList.toggle('hidden', !text.includes('...'));
                    }
                }
            } else {
                // Use the pre-formatted content or parse markdown as needed
                messageContainer.innerHTML = isPreformatted ? text : marked.parse(text);
                
                // Hide loading indicator only if we should update loading
                if (updateLoading) {
                    const loadingContainer = aiBubble.querySelector("#loadingContainer .loader");
                    if (loadingContainer) {
                        loadingContainer.classList.add('hidden');
                    }
                }
            }
        },

        toggleLoadingSymbol(id) {
            const aiBubble = document.getElementById(`${id}`);
            if (!aiBubble) return;

            const loadingContainer = aiBubble.querySelector("#loadingContainer");
            if (!loadingContainer) return;

            loadingContainer.classList.toggle("loader");
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
        },

        autoResize(event) {
            const textarea = event.target;
            textarea.style.height = 'auto';
            textarea.style.height = (textarea.scrollHeight) + 'px';
        },

        getRandomSampleQuestions(num_questions = 3) {
            function mapIcons(q, c) { return {question: q.question, icon: q.icon ?? c.icon} }
            let questions = [];
            this.getConfig().translations[this.language].sidebarQuestions
                .forEach(group => questions = questions.concat(group.questions.map(q => mapIcons(q, group))));
            shuffleArray(questions);
            return questions.slice(0, num_questions);
        },

        getCurrentCategoryQuestions() {
            const categories = conf.translations[this.language].sidebarQuestions;
            const currentCategory = categories.find(cat => cat.header === this.selectedCategory);

            if (!currentCategory) {
                // If no category is selected, show random sample questions
                return this.getRandomSampleQuestions();
            }

            // Take first 3 questions and use their individual icons
            return currentCategory.questions.slice(0, 3).map(q => ({
                question: q.question,
                icon: q.icon || currentCategory.icon // Fallback to category icon if question has no icon
            }));
        },

        updateSelectedCategory(category) {
            this.selectedCategory = category;
        },

        updateWidth() {
            this.windowWidth = window.innerWidth;
        },

        onSidebarToggle(key) {
            this.isSidebarActive = (key !== 'none');
        },

        isMainContentVisible() {
            return !(this.isMobile && this.isSidebarActive);
        },

        isSendAvailable() {
            if (!this.isMobile) return true;
            return this.textInput.length > 0;
        },

        isSpeechRecognitionAvailable() {
            if (!this.voiceServerConnected) return false;
            if (!this.isMobile) return true;
            return this.textInput.length === 0;
        },

        isResetAvailable() {
            if (!this.isMobile) return true;
            return this.textInput.length === 0;
        },
    },

    async mounted() {
        window.addEventListener('resize', this.updateWidth);

        // Initialize the selected language from the sidebar if available
        if (this.$refs.sidebar) {
            this.selectedLanguage = this.$refs.sidebar.selectedLanguage;
        }
        this.updateTheme();
        this.setupTooltips();
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', this.updateTheme);

        if (!this.isMobile) {
            this.createSpeechBubbleAI(conf.translations[this.language].welcome, 'startBubble');
        }

        this.updateSelectedCategory(this.getConfig().DefaultQuestions);

        // Check voice server connection
        try {
            const response = await fetch(`${conf.VoiceServerAddress}/info`);
            if (!response.ok) {
                throw new Error('Failed to fetch device info');
            }
            const data = await response.json();
            this.deviceInfo = `${data.model} on ${data.device}`;
            this.voiceServerConnected = true;
        } catch (error) {
            console.error('Error fetching device info:', error);
            this.deviceInfo = 'Speech recognition device not available';
            this.voiceServerConnected = false;
        }
    },

    beforeUnmount() {
        window.removeEventListener('resize', this.updateWidth);
    }
}

</script>

<style>
.chatbubble {
    border-radius: 1.25rem;
    text-align: left;
    position: relative;
    transition: all 0.2s ease;
    width: fit-content;
    max-width: 800px;
}

.message-content {
    align-items: flex-start;
    gap: 0.75rem;
}

.message-text {
    flex: 1;
    min-width: 0;
    padding-right: 0.5rem;
    white-space: normal;
}

.chat-user {
    background-color: var(--chat-user-light);
    margin-left: auto;
    margin-right: 1rem;
    padding: 0.75rem 1.25rem;
    width: auto !important; /* Override any width constraints */
}

.chat-ai {
    background-color: var(--chat-ai-light);
    margin-left: 1rem;
    margin-right: auto;
    width: calc(100% - 4rem) !important;
    will-change: box-shadow;
    transition: box-shadow 0.3s ease;
}

.chaticon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.5rem;
    height: 2.5rem;
    background-color: white;
    border-radius: 50%;
    border: 1px solid var(--border-light);
    padding: 0.5rem;
    margin: 0 0.5rem;
}

.chaticon img {
    width: 100%;
    height: 100%;
    object-fit: contain;
}

#chat1 {
    flex: 1;
    overflow-y: auto;
    position: relative;
    display: flex;
    flex-direction: column;
    min-height: 0; /* Important for Firefox */
    padding: 2rem 0; /* Increased top padding for first message */
}

#chat-container {
    width: 100%;
    max-width: min(95%, 120ch);
    padding: 0.25rem;
    margin: 0 auto;
    position: relative;
}

/* Move fade effects to mainContent */
#mainContent::before,
#mainContent::after {
    content: '';
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    width: min(95%, 120ch);
    height: 40px;
    pointer-events: none;
    z-index: 10;
    max-width: calc(100% - 2rem); /* Account for padding */
}

/* Top fade */
#mainContent::before {
    top: 0;
    background: linear-gradient(to bottom,
        var(--background-light) 0%,
        var(--background-light) 40%,
        transparent 100%);
}

/* Bottom fade */
#mainContent::after {
    bottom: 88px; /* Input container height + padding */
    background: linear-gradient(to top,
        var(--background-light) 0%,
        var(--background-light) 40%,
        transparent 100%);
}

@media (prefers-color-scheme: dark) {
    #mainContent::before {
        background: linear-gradient(to bottom,
            var(--background-dark) 0%,
            var(--background-dark) 40%,
            transparent 100%);
    }

    #mainContent::after {
        background: linear-gradient(to top,
            var(--background-dark) 0%,
            var(--background-dark) 40%,
            transparent 100%);
    }
}

/* Responsive widths for larger screens */
@media (min-width: 1400px) {
    #mainContent::before,
    #mainContent::after {
        width: min(70%, 160ch);
        max-width: calc(100% - 4rem);
    }
}

@media (min-width: 1800px) {
    #mainContent::before,
    #mainContent::after {
        width: min(60%, 180ch);
        max-width: calc(100% - 4rem);
    }
}

.input-container {
    width: 100%;
    background-color: var(--background-light);
    border-top: 1px solid var(--border-light);
    padding: 1rem 0;
    margin-bottom: 1rem;
    flex-shrink: 0;
    position: relative;
    z-index: 11; /* Above the fade effect */
}

.input-group {
    width: 100%;
    max-width: min(95%, 160ch);
    margin: 0 auto;
    padding: 0 1rem;
}

.input-group .form-control {
    box-shadow: 0 0 0 1px var(--border-light);
    background-color: var(--background-light);
    color: var(--text-primary-light);
    padding: 0.75rem 1rem;
    height: 3rem;
    min-height: 3rem;
    resize: none;
    overflow-y: hidden;
    max-height: min(40vh, 20rem);
    line-height: 1.5;
    border-radius: 1.5rem !important;
}

.input-group .form-control[rows] {
    height: auto;
    overflow-y: auto;
}

.input-group .form-control::placeholder {
    color: var(--text-secondary-light);
}

.input-group .form-control:focus {
    box-shadow: 0 0 0 1px var(--primary-light);
}

.input-group .btn {
    padding: 0;
    width: 3rem;
    height: 3rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    align-self: flex-end;
    margin-bottom: 2px;
    border-radius: 1.5rem !important;
    transition: all 0.2s ease;
}

.input-group .btn:hover {
    transform: translateY(-1px);
}

.input-group .btn:disabled {
    animation: bounce 1s infinite;
    opacity: 0.7;
}

.input-group .btn i {
    font-size: 1.25rem;
    line-height: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.25rem;
    height: 1.25rem;
}

.input-group .btn-primary i.fa-paper-plane {
    margin-left: -2px; /* Adjust send icon position */
}


@keyframes bounce {
    0%, 100% {
        transform: translateY(0);
    }
    50% {
        transform: translateY(-2px);
    }
}

#mainContent {
    width: 100%;
    max-width: 100%;
    padding-right: 0 !important;
    height: calc(100vh - 60px);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    position: relative; /* For fade positioning */
}

.sample-questions {
    width: 100%;
    max-width: min(90%, 120ch);
    margin: 0 auto;
    padding: 1rem;
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    justify-content: center;
}

.sample-question {
    flex: 1 1 250px;
    max-width: 300px;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    padding: 1.5rem;
    background-color: var(--background-light);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius-lg);
    color: var(--text-primary-light);
    transition: all 0.2s ease;
    text-align: center;
}

.sample-question:hover {
    background-color: var(--surface-light);
    border-color: var(--primary-light);
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}

.btn-primary {
    background-color: var(--primary-light) !important;
    border: none;
    color: white;
}

.btn-primary:hover {
    background-color: var(--secondary-light) !important;
}

@media (prefers-color-scheme: dark) {
    body {
        background-color: var(--background-dark);
    }

    #mainContent {
        background-color: var(--background-dark);
    }

    .chat-user {
        background-color: var(--chat-user-dark);
        color: var(--text-primary-dark);
    }

    .chat-ai {
        background-color: var(--chat-ai-dark);
        color: var(--text-primary-dark);
    }

    .input-container {
        background-color: var(--background-dark);
        border-color: var(--border-dark);
    }

    .input-group .form-control {
        background-color: var(--input-dark);
        box-shadow: 0 0 0 1px var(--border-dark);
        color: var(--text-primary-dark);
    }

    .input-group .form-control::placeholder {
        color: var(--text-secondary-dark);
    }

    .input-group .form-control:focus {
        box-shadow: 0 0 0 1px var(--primary-dark);
    }

    .btn-outline-primary {
        border-color: var(--border-dark);
        color: var(--text-secondary-dark);
        background-color: transparent;
    }

    .btn-outline-primary:hover {
        border-color: var(--primary-dark);
        color: var(--primary-dark);
        background-color: transparent;
    }

    .btn-outline-danger {
        border-color: var(--border-dark);
        color: var(--text-secondary-dark);
        background-color: transparent;
    }

    .btn-outline-danger:hover {
        border-color: #ef4444;
        color: #ef4444;
        background-color: transparent;
    }

    .sample-question {
        background-color: var(--chat-user-dark);
        border-color: var(--border-dark);
        color: var(--text-primary-dark);
    }

    .sample-question:hover {
        background-color: var(--chat-ai-dark);
        border-color: var(--primary-dark);
    }

    .chaticon {
        background-color: var(--surface-dark);
        border-color: var(--border-dark);
    }

    .chaticon img {
        filter: invert(1);
    }
}

#chatDebug {
    background-color: var(--surface-light);
    border-radius: var(--border-radius-lg);
    padding: 1rem;
    box-shadow: var(--shadow-md);
}

@media (prefers-color-scheme: dark) {
    #chatDebug {
        background-color: var(--surface-dark);
        color: var(--text-primary-dark);
    }

    .debug-toggle {
        color: var(--text-secondary-dark);
    }

    .debug-toggle:hover {
        color: var(--text-primary-dark);
    }

    .bubble-debug-text {
        background-color: var(--surface-dark);
        color: var(--text-secondary-dark);
    }
}

@media (min-width: 1400px) {
    #chat-container,
    .input-group,
    .sample-questions {
        max-width: min(70%, 160ch);
    }
}

@media (min-width: 1800px) {
    #chat-container,
    .input-group,
    .sample-questions {
        max-width: min(60%, 180ch);
    }
}

/* Override any Bootstrap input group border radius styles */
.input-group > :first-child,
.input-group > :last-child,
.input-group > .form-control:not(:last-child),
.input-group > .form-control:not(:first-child) {
    border-radius: 1.5rem !important;
}

.bubble-debug-text {
    font-size: 0.875rem;
    color: var(--text-secondary-light);
    padding: 0.5rem 0.75rem;
    margin-top: 0.5rem;
    background-color: transparent;
}

.debug-toggle {
    cursor: pointer;
    font-size: 0.75rem;
    margin-top: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    color: var(--text-secondary-light);
    transition: color 0.2s ease;
    padding: 0.25rem;
}

.debug-toggle:hover {
    color: var(--primary-light);
}

.loader {
    border: 2px solid transparent;
    border-top: 2px solid #3498db;
    border-radius: 50%;
    width: 14px;
    height: 14px;
    animation: spin 1s linear infinite;
    margin-right: 8px;
}

.hidden {
    display: none;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

@media (max-width: 400px) {
    .opaca-credentials {
        flex-direction: column;
    }
}

.debug-toggle img {
    width: 10px;
    height: 10px;
    opacity: 0.6;
    transition: all 0.2s ease;
    margin-right: 0.25rem;
}

.debug-toggle:hover img {
    opacity: 1;
}

.debug-separator {
    border: 0;
    margin: 0.5rem 0;
    border-top: 1px solid var(--border-light);
    opacity: 0.2;
}

@media (prefers-color-scheme: dark) {
    .debug-text {
        /* Remove empty style */
    }

    .debug-toggle {
        color: var(--text-secondary-dark);
    }

    .debug-toggle:hover {
        color: var(--primary-dark);
    }

    .bubble-debug-text {
        color: var(--text-secondary-dark);
        background-color: transparent;
    }

    .debug-separator {
        border-color: var(--border-dark);
    }
}

.bubble-debug-text::before {
    content: attr(data-agent);
    margin-right: 0.75rem;
}

/* Add margin to the first chat bubble */
/* i dont know what this is supposed to do, but i dont think it works.
    it just offsets the user-chat bubble down so it's lower than the user icon, which looks weird imo, especially since the same doesnt happen for the ai.
    feel free to uncomment if this was the intention. */
.chatbubble:first-child {
    /* margin-top: 1rem; */
}

/* Add margin to the last chat bubble */
.chatbubble:last-child {
    margin-bottom: 1rem;
}

.chat-ai.waiting {
    opacity: 0.7;
}

/* Remove the static dots */
.chat-ai.waiting::after {
    display: none;
}

.chat-ai.waiting span {
    display: inline-block;
    animation: wave 1s infinite;
    margin: 0 1px;
}

.chat-ai.waiting span:nth-child(2) {
    animation-delay: 0.2s;
}

.chat-ai.waiting span:nth-child(3) {
    animation-delay: 0.4s;
}

@keyframes wave {
    0%, 100% {
        transform: translateY(0);
    }
    50% {
        transform: translateY(-4px);
    }
}

#waitBubble {
    opacity: 0.7;
}

/* Remove the bubble bounce animation */
#waitBubble .chat-ai {
    animation: none;
}

.status-line {
    margin: 0;
    line-height: 1.4;
    padding: 0.1rem 0;
    display: flex;
    align-items: center;
}

@media screen and (max-width: 768px) {
    #mainContent {
        display: none;
    }

    #mainContent::before {
        background: none;
        content: none;
    }

    #mainContent::after {
        background: none;
        content: none;
    }

    .input-container {
        padding: 0.5rem;
    }

    .input-group {
        padding: 0;
    }

    .chat-user {
        margin-right: 0;
    }

    .chat-ai {
        margin-left: 0;
    }

    .chaticon {
        padding: 0.5rem;
        margin: 0 0.25rem;
    }

}

@keyframes move-glow {
    0%, 100% {
        box-shadow: 0 0 8px var(--glow-color-1, #ffffff33);
    }
    50% {
        box-shadow: 0 0 15px var(--glow-color-2, #ffffff73);
    }
}

</style>
