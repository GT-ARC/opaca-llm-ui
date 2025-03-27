<template>
    <div class="d-flex justify-content-start flex-grow-1 w-100 position-relative z-1">

        <!-- Move the RecordingPopup outside the main content flow -->
        <RecordingPopup
            v-model:show="showRecordingPopup"
            :language="selectedLanguage"
            @transcription-complete="handleTranscriptionComplete"
            @send-message="handleSendMessage"
            @error="handleRecordingError"
        />

        <Sidebar :backend="backend"
                 :language="language"
                 :is-dark-scheme="isDarkScheme"
                 ref="sidebar"
                 @language-change="handleLanguageChange"
                 @select-question="askChatGpt"
                 @category-selected="newCategory => this.selectedCategory = newCategory"
                 @api-key-change="(newValue) => this.apiKey = newValue"
                 @on-sidebar-toggle="this.onSidebarToggle"
        />

        <!-- Main Container: Chat Window, Text Input -->
        <main id="mainContent" class="mx-auto"
              :class="{ 'd-flex flex-column flex-grow-1': this.isMainContentVisible(), 'd-none': !this.isMainContentVisible() }"
              style="max-width: 1000px !important;">

            <!-- Chat Window with Chat bubbles -->
            <div class="container-fluid flex-grow-1" id="chat1" :class="{'px-5': !isMobile}">
                <div v-for="{ elementId, isUser, content, isLoading } in this.messages">
                    <Chatbubble
                        :element-id="elementId"
                        :is-user="isUser"
                        :is-voice-server-connected="this.voiceServerConnected"
                        :is-dark-scheme="this.isDarkScheme"
                        :initial-content="content"
                        :initial-loading="isLoading"
                        :ref="elementId"
                    />
                </div>

                <!-- sample questions -->
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
                                :placeholder="conf.translations[language].inputPlaceholder || 'Send a message...'"
                                class="form-control overflow-hidden"
                                style="resize: none; height: auto; max-height: 150px;"
                                rows="1"
                                @keydown="textInputCallback"
                                @input="resizeTextInput"
                      ></textarea>

                    <!-- user has entered text into message box -> send button available -->
                    <button type="button"
                            v-if="this.isSendAvailable()"
                            class="btn btn-primary"
                            @click="submitText"
                            :disabled="!isFinished">
                        <i class="fa fa-paper-plane"/>
                    </button>
                    <button type="button"
                            v-if="this.voiceServerConnected"
                            class="btn btn-outline-primary"
                            @click="this.showRecordingPopup = true"
                            :disabled="!isFinished">
                        <i class="fa fa-microphone"/>
                    </button>
                    <button type="button"
                            v-if="this.isResetAvailable()"
                            class="btn btn-outline-danger"
                            @click="resetChat"
                            :disabled="!isFinished">
                        <i class="fa fa-refresh"/>
                    </button>
                </div>
            </div>

            <!-- Simple Keyboard -->
            <SimpleKeyboard v-if="conf.ShowKeyboard"
                            @change="input => this.textInput = input" />

        </main>

    </div>

</template>

<script>
import {nextTick} from "vue";
import SimpleKeyboard from "./SimpleKeyboard.vue";
import Sidebar from "./sidebar.vue";
import RecordingPopup from './RecordingPopup.vue';
import Chatbubble from "./chatbubble.vue";
import conf from '../../config'
import {sendRequest, shuffleArray} from "../utils.js";
import {debugLoadingMessages} from '../config/debug-colors.js';

import { useDevice } from "../useIsMobile.js";

export default {
    name: 'main-content',
    components: {
        Sidebar,
        SimpleKeyboard,
        RecordingPopup,
        Chatbubble
    },
    props: {
        backend: String,
        language: String,
    },
    setup() {
        const { isMobile, screenWidth } = useDevice()
        return { conf, isMobile, screenWidth };
    },
    data() {
        return {
            messages: [],
            socket: null,

            apiKey: '',
            textInput: '',
            messageCount: 0,
            isFinished: true,
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
            randomSampleQuestions: null,
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
        updateTheme() {
            this.isDarkScheme = window.matchMedia('(prefers-color-scheme: dark)').matches;
        },

        async textInputCallback(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                await this.submitText();
            }
        },

        async submitText() {
            if (this.textInput) {
                const userInput = this.textInput;
                this.textInput = '';
                await this.askChatGpt(userInput);
            }
        },

        resizeTextInput(event) {
            const textArea = event.target;
            if (textArea) {
                textArea.style.height = 'auto';
                textArea.style.height = `${textArea.scrollHeight}px`;
            }
        },

        getLastBubble() {
            if (this.messages.length === 0) {
                throw Error('Tried to get the last chat bubble when none exist. This should not happen.');
            }
            const refId = this.messages[this.messages.length - 1].elementId;
            return this.$refs[refId][0];
        },

        async askChatGpt(userText) {
            this.isFinished = false;
            this.showExampleQuestions = false;

            // add user chat bubble
            await this.addChatBubble(userText, true, false);

            // add AI chat bubble in loading state, add prepare message
            await this.addChatBubble('', false, true);
            this.getLastBubble().addStatusMessage('preparing',
                this.getDebugLoadingMessage('preparing'), false);

            try {
                const url = `${conf.BackendAddress}/${this.getBackend()}/query_stream`
                this.socket = new WebSocket(url);
                this.socket.onopen    = ()    => this.handleStreamingSocketOpen(this.socket, userText);
                this.socket.onmessage = event => this.handleStreamingSocketMessage(event);
                this.socket.onclose   = ()    => this.handleStreamingSocketClose();
                this.socket.onerror   = error => this.handleStreamingSocketError(error);
            } catch (error) {
                await this.handleStreamingSocketError(error);
            }
        },

        async handleStreamingSocketOpen(socket, userText) {
            try {
                const inputData = JSON.stringify({user_query: userText, api_key: this.apiKey});
                socket.send(inputData);
            } catch (error) {
                await this.handleStreamingSocketError(error);
            }
        },

        /** todo: rework/simplify */
        async handleStreamingSocketMessage(event) {
            const aiBubble = this.getLastBubble();
            const result = JSON.parse(JSON.parse(event.data)); // YEP, THAT MAKES NO SENSE (WILL CHANGE SOON TM)

            if (result.hasOwnProperty('agent')) {
                if (result.agent === 'output_generator') {
                    // put output_generator content directly in the bubble
                    aiBubble.addContent(result.content);
                } else {
                    // other agent messages are intermediate results
                    this.processAgentStatusMessage(result);
                    await this.addDebugToken(result, false);
                }

                this.scrollDownDebug();
                this.scrollDownChat();
            } else {
                // no agent property -> Last message received should be final response
                aiBubble.toggleError(!!result.error);
                const content = result.error
                    ? result.error : result.content;
                aiBubble.setContent(content);
                aiBubble.toggleLoading(false);
                this.isFinished = true;
            }
        },

        async handleStreamingSocketClose() {
            console.log("WebSocket connection closed", this.isFinished);
            if (!this.isFinished) {
                const message = "It seems there was a problem in the response generation.";
                this.handleUnexpectedConnectionClosed(message);
            }

            this.startAutoSpeak();
            this.isFinished = true;
            this.scrollDownChat();
        },

        async handleStreamingSocketError(error) {
            console.error("Received error: ", error);
            if (!this.isFinished) {
                const message = "An Error occurred in the response generation: " + error.toString();
                this.handleUnexpectedConnectionClosed(message);
            }

            this.isFinished = true;
            this.scrollDownChat();
        },

        startAutoSpeak() {
            if (this.autoSpeakNextMessage && this.voiceServerConnected) {
                const aiBubble = this.getLastBubble();
                aiBubble.startAudioPlayback();
                this.autoSpeakNextMessage = false;
            }
        },

        handleTranscriptionComplete(text) {
            if (text) {
                this.textInput = text;
            }
        },

        handleSendMessage(text) {
            if (text) {
                this.textInput = "";
                this.autoSpeakNextMessage = true;
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
            this.messages = [];
            this.$refs.sidebar.clearDebugMessage();
            await this.showWelcomeMessage();
            this.showExampleQuestions = true;
            await sendRequest("POST", `${conf.BackendAddress}/reset`);
        },

        async showWelcomeMessage() {
            // don't add in mobile view, as welcome message + sample questions is too large for mobile screen
            if (!this.isMobile) {
                await this.addChatBubble(conf.translations[this.language].welcome, false, false);
            }
        },

        /**
         * @param content {string} initial chatbubble content
         * @param isUser {boolean} whether the message is by the user or the AI
         * @param isLoading {boolean} initial loading state, should be true if the bubble is intended to be edited
         * later (streaming responses etc.)
         */
        async addChatBubble(content, isUser = false, isLoading = false) {
            const elementId = `chatbubble-${this.messages.length}`;
            const message = { elementId: elementId, isUser: isUser, content: content, isLoading: isLoading };
            this.messages.push(message);

            // wait for the next rendering tick so that the component is mounted
            await nextTick();
            this.scrollDownChat();
        },

        handleUnexpectedConnectionClosed(message) {
            console.error('Connection closed unexpectedly', message);
            const aiBubble = this.getLastBubble();
            aiBubble.setContent(message);
            aiBubble.toggleLoading(false);
            aiBubble.toggleError(true);
        },

        scrollDownChat() {
            const div = document.getElementById('chat1');
            div.scrollTop = div.scrollHeight;
        },
        
        scrollDownDebug() {
            const div = document.getElementById('debug-console');
            div.scrollTop = div.scrollHeight;
        },

        getDebugLoadingMessage(agentName) {
            // Use the current language (GB or DE) to get the appropriate message
            return debugLoadingMessages[this.language]?.[agentName] ?? debugLoadingMessages['GB'][agentName];
        },

        processAgentStatusMessage(agentMessage) {
            const aiBubble = this.getLastBubble();
            const agentName = agentMessage.agent;
            const message = this.getDebugLoadingMessage(agentName);
            if (message) {
                aiBubble.markStatusMessagesDone(agentName);
                aiBubble.addStatusMessage(agentName, message, false);
            }
        },

        async addDebugToken(agentMessage) {
            // log tool output
            if (agentMessage.tools && agentMessage.tools.length > 0) {
                const toolOutput = agentMessage["tools"].map(tool =>
                    `Tool ${tool["id"]}:\nName: ${tool["name"]}\nArguments: ${JSON.stringify(tool["args"])}\nResult: ${JSON.stringify(tool["result"])}`
                ).join("\n\n");
                const type = agentMessage.agent;
                this.addDebug(toolOutput, type);
            }

            // log agent message
            if (agentMessage.content) {
                const text = agentMessage.content;
                const type = agentMessage.agent;
                this.addDebug(text, type);
            }
        },

        addDebug(text, type) {
            const sidebar = this.$refs.sidebar;
            sidebar.addDebugMessage(text, type);
            const aiBubble = this.getLastBubble();
            aiBubble.addDebugMessage(text, type);
        },

        getBackend() {
            const parts = this.backend.split('/');
            return parts[parts.length - 1];
        },

        getRandomSampleQuestions(num_questions = 3) {
            function mapIcons(q, c) { return {question: q.question, icon: q.icon ?? c.icon} }
            if (this.randomSampleQuestions == null) {
                let questions = [];
                conf.translations[this.language].sidebarQuestions
                    .forEach(group => questions = questions.concat(group.questions.map(q => mapIcons(q, group))));
                shuffleArray(questions);
                this.randomSampleQuestions = questions.slice(0, num_questions);
            }
            return this.randomSampleQuestions;
        },

        getCurrentCategoryQuestions() {
            const categories = conf.translations[this.language].sidebarQuestions;
            const currentCategory = categories.find(cat => cat.header === this.selectedCategory);

            if (!currentCategory) {
                // If no category is selected, show random sample questions
                return this.getRandomSampleQuestions();
            } else {
                this.randomSampleQuestions = null; // roll a new sample next time
            }

            // Take first 3 questions and use their individual icons
            return currentCategory.questions.slice(0, 3).map(q => ({
                question: q.question,
                icon: q.icon || currentCategory.icon // Fallback to category icon if question has no icon
            }));
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

        isResetAvailable() {
            if (!this.isMobile) return true;
            return this.textInput.length === 0;
        },

        setupTooltips() {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl)
            });
        },

        async initVoiceServerConnection() {
            try {
                const response = await fetch(`${conf.VoiceServerAddress}/info`);
                if (!response.ok) {
                    const data = await response.json();
                    this.deviceInfo = `${data.model} on ${data.device}`;
                    this.voiceServerConnected = true;
                } else {
                    this.deviceInfo = 'Speech recognition device not available';
                    this.voiceServerConnected = false;
                }
            } catch (error) {
                console.error('Error fetching device info:', error);
            }
        }
    },

    async mounted() {
        // Initialize the selected language from the sidebar if available
        if (this.$refs.sidebar) {
            this.selectedLanguage = this.$refs.sidebar.selectedLanguage;
        }
        this.updateTheme();
        this.setupTooltips();
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', this.updateTheme);
        await this.showWelcomeMessage();
        const questions = conf.DefaultQuestions;
        this.selectedCategory = questions;
        this.$refs.sidebar.$refs.sidebar_questions.expandSectionByHeader(questions);

        await this.initVoiceServerConnection();
    },

}

</script>

<style>
#chat1 {
    flex: 1;
    overflow-y: auto;
    position: relative;
    display: flex;
    flex-direction: column;
    min-height: 0; /* Important for Firefox */
    padding: 2rem 0; /* Increased top padding for first message */
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

}

/* Override any Bootstrap input group border radius styles */
.input-group > :first-child,
.input-group > :last-child,
.input-group > .form-control:not(:last-child),
.input-group > .form-control:not(:first-child) {
    border-radius: 1.5rem !important;
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

/* mobile layout style changes */
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
}

</style>
