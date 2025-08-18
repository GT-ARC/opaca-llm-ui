<template>
    <div class="d-flex justify-content-start flex-grow-1 w-100 position-relative z-1">

        <!-- Move the RecordingPopup outside the main content flow -->
        <RecordingPopup
            v-model:show="showRecordingPopup"
            :language="Localizer.getLanguageForTTS()"
            @transcription-complete="handleTranscriptionComplete"
            @send-message="handleSendMessage"
            @error="handleRecordingError"
            ref="RecordingPopup"
        />

        <Sidebar
            :backend="backend"
            :language="language"
            :connected="connected"
             ref="sidebar"
             @select-question="question => this.handleSelectQuestion(question)"
             @select-category="category => this.handleSelectCategory(category)"
        />


        <!-- Main Container: Chat Window, Text Input -->
        <main id="mainContent" class="mx-auto"
              :class="{ 'd-flex flex-column flex-grow-1': this.isMainContentVisible(), 'd-none': !this.isMainContentVisible() }">

            <!-- Chat Window with Chat bubbles -->
            <div class="container-fluid flex-grow-1 chat-container" id="chat1">
                <div class="chatbubble-container d-flex flex-column justify-content-between mx-auto">
                    <Chatbubble v-for="{ elementId, isUser, content, isLoading } in this.messages"
                        :element-id="elementId"
                        :is-user="isUser"
                        :initial-content="content"
                        :initial-loading="isLoading"
                        :ref="elementId"
                    />
                </div>

                <!-- sample questions -->
                <div v-show="showExampleQuestions" class="sample-questions">
                    <div v-if="!this.isMobile" class="w-100 p-3 text-center fs-4">
                        {{ Localizer.get("welcome") }}
                    </div>
                    <div v-for="(question, index) in Localizer.getSampleQuestions(this.textInput, this.selectedCategory)"
                         :key="index"
                         class="sample-question"
                         @click="this.askSampleQuestion(question.question)">
                        {{ question.icon }} <br>
                        <span v-if="question.question === '__loading__'"><i class="fa fa-ellipsis fa-beat-fade"/></span>
                        <span v-else>{{ question.question }}</span>
                    </div>
                    <div class="w-100 text-center">
                        <button type="button" class="btn btn-outline-primary p-2"
                                @click="Localizer.reloadSampleQuestions(null)">
                            <i class="fa fa-arrow-right"/>
                            {{ Localizer.get('rerollQuestions') }}
                        </button>
                    </div>
                </div>

            </div>

            <!-- Input Area -->
            <div class="input-container">
                <div class="input-group">
                    <div class="scroll-wrapper">
                      <textarea id="textInput"
                                v-model="textInput"
                                ref="textInputRef"
                                :placeholder="Localizer.get('inputPlaceholder')"
                                class="form-control"
                                :class="{ 'small-scrollbar': isSmallScrollbar }"
                                style="resize: none; height: auto; max-height: 150px;"
                                rows="1"
                                @keydown="textInputCallback"
                                @input="resizeTextInput"
                      ></textarea>
                    </div>

                    <!-- user has entered text into message box -> send button available -->
                    <button type="button"
                            v-if="this.isSendAvailable() && isFinished"
                            class="btn btn-primary input-area-button"
                            @click="submitText"
                            :title="Localizer.get('tooltipButtonSend')"
                            style="margin-left: -2px">
                        <i class="fa fa-paper-plane"/>
                    </button>
                    <button type="button"
                            v-if="!isFinished"
                            class="btn btn-outline-danger input-area-button"
                            @click="stopGeneration"
                            :title="Localizer.get('tooltipButtonStop')"
                            style="margin-left: -2px">
                        <i class="fa fa-stop"/>
                    </button>
                    <button type="button"
                            v-if="AudioManager.isRecognitionSupported()"
                            class="btn btn-outline-primary input-area-button"
                            @click="this.startRecognition()"
                            :disabled="!isFinished"
                            :title="Localizer.get('tooltipButtonRecord')">
                        <i v-if="!AudioManager.isLoading" class="fa fa-microphone" />
                        <i v-else class="fa fa-spin fa-spinner" />
                    </button>
                    <button type="button"
                            v-if="this.isResetAvailable()"
                            class="btn btn-outline-danger input-area-button"
                            @click="resetChat"
                            :disabled="!isFinished"
                            :title="Localizer.get('tooltipButtonReset')">
                        <i class="fa fa-refresh"/>
                    </button>
                </div>
            </div>

        </main>

    </div>

</template>

<script>
import {nextTick} from "vue";
import Sidebar from "./sidebar.vue";
import RecordingPopup from './RecordingPopup.vue';
import Chatbubble from "./chatbubble.vue";
import conf from '../../config'
import {sendRequest} from "../utils.js";
import Localizer from "../Localizer.js";
import AudioManager from "../AudioManager.js";

import { useDevice } from "../useIsMobile.js";
import SidebarManager from "../SidebarManager";
import OptionsSelect from "./OptionsSelect.vue";

export default {
    name: 'main-content',
    components: {
        OptionsSelect,
        Sidebar,
        RecordingPopup,
        Chatbubble
    },
    props: {
        backend: String,
        language: String,
        connected: Boolean,
    },
    emits: [
        'select-category',
    ],
    setup() {
        const { isMobile, screenWidth } = useDevice()
        return { conf, SidebarManager, Localizer, AudioManager, isMobile, screenWidth };
    },
    data() {
        return {
            messages: [],
            socket: null,
            apiKey: '',
            textInput: '',
            isFinished: true,
            showExampleQuestions: true,
            autoSpeakNextMessage: false,
            showRecordingPopup: false,
            selectedCategory: conf.DefaultQuestions,
            isSmallScrollbar: true,
        }
    },
    methods: {
        async textInputCallback(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                await this.submitText();
                this.resizeTextInput();
            }
        },

        async submitText() {
            if (this.textInput && this.isFinished) {
                const userInput = this.textInput;
                this.textInput = '';
                await nextTick();
                this.resizeTextInput();
                await this.askChatGpt(userInput);
            }
        },

        async stopGeneration() {
            await sendRequest("POST", `${conf.BackendAddress}/stop`);
        },

        async askSampleQuestion(questionText) {
            // Do not send questions during autogeneration
            if (questionText === "__loading__") return;

            this.textInput = questionText
            await nextTick();
            this.resizeTextInput();
            await this.submitText();
        },

        resizeTextInput() {
            const textArea = document.getElementById('textInput');
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

            // add debug entry for user message
            const sidebar = this.$refs.sidebar;
            sidebar.addDebugMessage(userText, "user");

            // add AI chat bubble in loading state, add prepare message
            await this.addChatBubble('', false, true);
            this.getLastBubble().addStatusMessage('preparing',
                Localizer.getLoadingMessage('preparing'), false);

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

        async handleStreamingSocketMessage(event) {
            const aiBubble = this.getLastBubble();
            const result = JSON.parse(JSON.parse(event.data)); // YEP, THAT MAKES NO SENSE (WILL CHANGE SOON TM)

            if (result.hasOwnProperty('agent')) {
                if (result.agent === 'Output Generator') {
                    // put output_generator content directly in the bubble
                    aiBubble.toggleLoading(false);
                    aiBubble.addContent(result.content);
                    await this.addDebugToken(result, false);
                } else {
                    // other agent messages are intermediate results
                    this.processAgentStatusMessage(result);
                    await this.addDebugToken(result, false);
                }

                this.scrollDownDebug();
                this.scrollDownChat();
            } else {
                // no agent property -> Last message received should be final response
                console.log(result.error);
                if (result.error) {
                    aiBubble.setError(result.error);
                    const sidebar = this.$refs.sidebar;
                    sidebar.addDebugMessage(`\n${result.content}\n\nCause: ${result.error}\n`, "ERROR");
                }
                aiBubble.setContent(result.content);
                aiBubble.toggleLoading(false);
                this.isFinished = true;
            }
        },

        async handleStreamingSocketClose() {
            console.log("WebSocket connection closed", this.isFinished);
            if (!this.isFinished) {
                const message = Localizer.get('socketClosed');
                this.handleUnexpectedConnectionClosed(message);
            }

            this.startAutoSpeak();
            this.isFinished = true;
            this.scrollDownChat();
        },

        async handleStreamingSocketError(error) {
            console.error("Received error: ", error);
            if (!this.isFinished) {
                const message = Localizer.get('socketError', error.toString());
                this.handleUnexpectedConnectionClosed(message);
            }

            this.isFinished = true;
            this.scrollDownChat();
        },

        startAutoSpeak() {
            if (this.autoSpeakNextMessage) {
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

        startRecognition() {
            if (AudioManager.isVoiceServerConnected) {
                this.showRecordingPopup = true;
            } else {
                AudioManager.startWebSpeechRecognition(text => {
                    this.handleTranscriptionComplete(text);
                    this.autoSpeakNextMessage = true;
                    this.submitText();
                });
            }
        },

        async resetChat() {
            this.messages = [];
            this.$refs.sidebar.clearDebugMessage();
            this.showExampleQuestions = true;
            await sendRequest("POST", `${conf.BackendAddress}/reset`);
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
            aiBubble.setError("Connection closed unexpectedly");
        },

        scrollDownChat() {
            const div = document.getElementById('chat1');
            div.scrollTop = div.scrollHeight;
        },

        scrollDownDebug() {
            const div = document.getElementById('debug-console');
            div.scrollTop = div.scrollHeight;
        },

        processAgentStatusMessage(agentMessage) {
            const aiBubble = this.getLastBubble();
            const agentName = agentMessage.agent;
            const message = Localizer.getLoadingMessage(agentName);
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

        isMainContentVisible() {
            return !(this.isMobile && SidebarManager.isSidebarOpen());
        },

        isSendAvailable() {
            if (!this.isMobile) return true;
            return this.textInput.length > 0;
        },

        isResetAvailable() {
            if (!this.isMobile) return true;
            return this.textInput.length === 0;
        },

        updateScrollbarThumb() {
            this.$nextTick(() => {
                const el = this.$refs.textInputRef;
                if (!el) return;

                const computedStyle = getComputedStyle(el);
                const maxHeight = parseFloat(computedStyle.maxHeight);

                // If current height is less than the max-height
                this.isSmallScrollbar = el.offsetHeight < maxHeight;
            });
        },

        async loadHistory() {
            try {
                const res = await fetch(`${conf.BackendAddress}/history`, {
                    credentials: 'include'
                });

                if (!res.ok) throw new Error("Failed to fetch history");

                const messages = await res.json();

                for (const msg of messages) {
                    const isUser = msg.role === 'user';
                    await this.addChatBubble(msg.content, isUser);
                }
                if(messages.length !== 0) {
                    this.showExampleQuestions = false;
                }
            } catch (err) {
                console.error("Failed to load chat history:", err);
            }
        },

        handleSelectQuestion(question) {
            if (this.isMobile) {
                SidebarManager.close();
            }
            this.askSampleQuestion(question);
        },

        handleSelectCategory(category) {
            if (this.selectedCategory !== category) {
                if (this.showExampleQuestions) {
                    Localizer.reloadSampleQuestions(category);
                }
                this.selectedCategory = category;
                this.$emit('select-category', category);
            }
        }
    },

    mounted() {
        this.loadHistory();
        this.updateScrollbarThumb();
    },
    watch: {
        textInput() {
            this.updateScrollbarThumb();
        },
    }
}

</script>

<style scoped>
.chat-container {
    flex: 1;
    overflow-y: auto;
    position: relative;
    display: flex;
    flex-direction: column;
    min-height: 0; /* Important for Firefox */
    padding: 2rem 0; /* Increased top padding for first message */
}

.input-container {
    width: 100%;
    background-color: var(--background-color);
    border-top: 1px solid var(--border-color);
    padding: 1rem 0;
    margin-bottom: 1rem;
    flex-shrink: 0;
    position: relative;
    z-index: 11; /* Above the fade effect */
}

#textInput {
    box-shadow: 0 0 0 1px var(--border-color);
    padding: 0.75rem 1rem;
    height: 3rem;
    min-height: 3rem;
    resize: none;
    max-height: min(40vh, 20rem);
    line-height: 1.5;
    border-radius: 1.5rem !important;
}

#textInput[rows] {
    height: auto;
    overflow-y: auto;
}

.scroll-wrapper {
    border-radius: 1.5rem;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
}

.small-scrollbar::-webkit-scrollbar-thumb {
    background-color: transparent !important;
}

.input-area-button {
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

.input-area-button:hover {
    transform: translateY(-1px);
}

.input-area-button:disabled {
    animation: bounce 1s infinite;
    opacity: 0.7;
}

.input-area-button i {
    font-size: 1.25rem;
    line-height: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.25rem;
    height: 1.25rem;
}

.chatbubble-container {
    width: min(95%, 100ch);
}

#mainContent {
    width: 100%;
    max-width: 100%;
    height: calc(100vh - 50px);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    position: relative; /* For fade positioning */
    background-color: var(--background-color);
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
    background-color: var(--chat-user-color);
    border: 1px solid var(--border-color);
    border-radius: var(--bs-border-radius-lg);
    color: var(--text-primary-color);
    transition: all 0.2s ease;
    text-align: center;
}

.sample-question:hover {
    background-color: var(--surface-color);
    border-color: var(--primary-color);
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
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

/* animations */
@keyframes bounce {
    0%, 100% {
        transform: translateY(0);
    }
    50% {
        transform: translateY(-2px);
    }
}

</style>
