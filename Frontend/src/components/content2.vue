<template>
    <div class="d-flex justify-content-start flex-grow-1 w-100">

        <!-- Move the RecordingPopup outside the main content flow -->
        <RecordingPopup
            v-model:show="showRecordingPopup"
            :language="selectedLanguage"
            @transcription-complete="handleTranscriptionComplete"
            @send-message="handleSendMessage"
            @error="handleRecordingError"
        />

        <Sidebar :backend="backend" :language="language" ref="sidebar"
                 @language-change="handleLanguageChange"
                 @select-question="askChatGpt"
                 @category-selected="newCategory => this.selectedCategory = newCategory"
                 @api-key-change="(newValue) => this.apiKey = newValue"
                 @on-sidebar-toggle="this.onSidebarToggle"/>

        <!-- Main Container: Chat Window, Text Input -->
        <main id="mainContent" class="mx-auto"
              :class="{ 'd-flex flex-column flex-grow-1': this.isMainContentVisible(), 'd-none': !this.isMainContentVisible() }"
              style="max-width: 1000px">

            <!-- Chat Window -->
            <div class="container-fluid flex-grow-1" id="chat1" :class="{'px-3': !isMobile}">

                <!-- chat bubbles -->
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
                                style="resize: none; height: auto; max-height: 300px;"
                                rows="1"
                                @input="textInputCallback"></textarea>

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
                            @click="startRecognition"
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
import {marked} from "marked";
import {sendRequest, shuffleArray} from "../utils.js";
import {debugColors, defaultDebugColors, debugLoadingMessages} from '../config/debug-colors.js';

import { useDevice } from "../useIsMobile.js";

export default {
    name: 'main-content2',
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
            this.updateDebugColors();
        },

        async textInputCallback(event) {
            if (event.key === "Enter" && !event.shiftKey) {
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

        /** todo: check if ai bubble? */
        getLastBubble() {
            if (this.messages.length === 0) {
                throw Error('Tried to get the last chat bubble when none exist. This should not happen.');
            }
            const refId = this.messages[this.messages.length - 1].elementId;
            return this.$refs[refId][0];
        },

        isStreamingBackend() {
            return ['tool-llm', 'rest-gpt', 'self-orchestrated'].includes(this.getBackend());
        },

        async askChatGpt(userText) {
            this.isFinished = false;
            this.showExampleQuestions = false;
            const currentMessageCount = this.messageCount;
            this.messageCount++;
            this.accumulatedContent = ''; // Reset accumulated content for new message
            await this.addChatBubble(userText, true, false);
            try {
                if (this.isStreamingBackend()) {
                    await this.addChatBubble('', false, true);

                    // await this.editAnimationSpeechBubbleAI(currentMessageCount, true, preparingColor);
                    this.scrollDownChat();

                    // create websocket
                    const socket = new WebSocket(`${conf.BackendAddress}/${this.getBackend()}/query_stream`);
                    socket.onopen    = ()    => this.handleStreamingSocketOpen(socket, userText);
                    socket.onmessage = event => this.handleStreamingSocketMessage(event, currentMessageCount);
                    socket.onclose   = ()    => this.handleStreamingSocketClose(currentMessageCount);
                    socket.onerror   = error => this.handleStreamingSocketError(error, currentMessageCount);
                } else {
                    await this.addChatBubble('Generating your answer...', false, true); // todo: translation
                    this.scrollDownChat()

                    const result = await sendRequest(
                        "POST",
                        `${conf.BackendAddress}/${this.getBackend()}/query`,
                        {user_query: userText, api_key: this.apiKey},
                        null);
                    const answer = result.data.content;
                    if (result.data.error) {
                        this.addDebug(result.data.error)
                    }
                    await this.editTextSpeechBubbleAI(answer, false);
                    this.scrollDownChat();

                    this.processDebugInput(result.data.agent_messages, currentMessageCount);
                    this.scrollDownDebug();

                    // Generate audio for the response if needed
                    if (this.autoSpeakNextMessage && this.voiceServerConnected) {
                        await this.generateAudioForMessage(currentMessageCount, answer);
                        this.autoSpeakNextMessage = false;
                    }
                }
            } catch (error) {
                console.error(error);
                const aiBubble = this.getLastBubble();
                aiBubble.toggleLoading(false);
                aiBubble.toggleError(true);
                await this.editTextSpeechBubbleAI("Error while fetching data: " + error, false);
                await this.editAnimationSpeechBubbleAI(currentMessageCount, false);
                this.scrollDownChat();
            }
        },

        async handleStreamingSocketOpen(socket, userText) {
            const inputData = JSON.stringify({user_query: userText, api_key: this.apiKey});
            socket.send(inputData);
        },

        async handleStreamingSocketMessage(event, currentMessageCount) {
            const result = JSON.parse(JSON.parse(event.data)); // YEP, THAT MAKES NO SENSE (WILL CHANGE SOON TM)
            const aiBubble = this.getLastBubble();

            console.log('socket message result', result);

            if (result.hasOwnProperty("agent")) {
                if (result.agent === 'assistant') {
                    aiBubble.toggleLoading(false);
                    const formattedContent = marked.parse(result.content);
                    await this.editTextSpeechBubbleAI(formattedContent, true);

                    // Remove any active glow animation for assistant content
                    // await this.editAnimationSpeechBubbleAI(currentMessageCount, false);
                } else {
                    // Agent messages are intermediate results
                    await this.addDebugToken(result, currentMessageCount);
                }
                this.scrollDownDebug();
            } else {
                // Last message received should be final response
                aiBubble.toggleError(!!result.error);
                const content = result.error ?? result.content;
                await this.editTextSpeechBubbleAI(content, false);
                await this.editAnimationSpeechBubbleAI(currentMessageCount, false);
                aiBubble.toggleLoading(false);

                // todo: needed? Put the final response into the accumulated content
                this.accumulatedContent = result.content;
            }
        },

        async handleStreamingSocketClose(currentMessageCount) {
            console.log("WebSocket connection closed", this.isFinished);
            if (!this.isFinished) {
                const message = "It seems there was a problem during the response generation...";
                await this.handleUnexpectedConnectionClosed(message, currentMessageCount);
            }
            // Get the final accumulated content and message ID for speech
            if (this.autoSpeakNextMessage && this.voiceServerConnected) {
                if (this.accumulatedContent) {
                    await this.generateAudioForMessage(currentMessageCount, this.accumulatedContent);
                    this.autoSpeakNextMessage = false;
                }
            }

            this.isFinished = true;
        },

        async handleStreamingSocketError(error, currentMessageCount) {
            if (!this.isFinished) {
                const message = "I encountered the following error during the response generation: " + error.toString();
                await this.handleUnexpectedConnectionClosed(message, currentMessageCount);
            }
            console.log("Received error: ", error);

            // todo: does this also close the socket?
            this.isFinished = true;
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
                this.autoSpeakNextMessage = true; // Set this flag when message comes from voice input
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
            if (!this.isMobile) {
                // dont add in mobile view, as welcome message + sample questions is too large for mobile screen
                await this.addChatBubble(conf.translations[this.language].welcome, false, false);
            }
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

        async handleUnexpectedConnectionClosed(message, currentMessageCount) {
            console.log('Connection closed unexpectedly', message, currentMessageCount);
            await this.editTextSpeechBubbleAI(message, false);
            await this.editAnimationSpeechBubbleAI(currentMessageCount, false);

            const aiBubble = this.getLastBubble();
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

        getDebugColor(agentName) {
            return (debugColors[agentName] ?? defaultDebugColors)[this.isDarkScheme ? 0 : 1];
        },

        getDebugLoadingMessage(agentName) {
            // Use the current language (GB or DE) to get the appropriate message
            return debugLoadingMessages[this.language]?.[agentName] ?? debugLoadingMessages['GB'][agentName];
        },

        async addDebugToken(agent_message) {
            const aiBubble = this.getLastBubble();
            const agentName = agent_message.agent;
            const color = this.getDebugColor(agentName);
            const message = this.getDebugLoadingMessage(agentName);

            // add debug token as status message (also adds as debug message)
            if (message) {
                aiBubble.addStatusMessage(message, 'pending', {color: color});
                // await this.editAnimationSpeechBubbleAI(messageCount, true, color);
            } else if (agentName === 'system') {
                aiBubble.addDebugMessage(agent_message.content.trim(), {color: color});
            }

            // log tool output
            if (agent_message["tools"].length > 0) {
                const tool_output = agent_message["tools"].map(tool =>
                    `Tool ${tool["id"]}:\nName: ${tool["name"]}\nArguments: ${JSON.stringify(tool["args"])}\nResult: ${JSON.stringify(tool["result"])}`
                ).join("\n\n");
                const type = agent_message["agent"] + "-Tools"
                this.addDebug(tool_output, color, type);
            }

            // log agent message
            if (agent_message["content"] !== "") {
                const text = agent_message["content"];
                const type = agent_message["agent"];
                this.addDebug(text, color, type);
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
                const color = this.getDebugColor(message["agent"]);
                // if tools have been generated, display the tools (no message was generated in that case)
                const content = [
                    message["tools"].length > 0 ? JSON.stringify(message["tools"]) : message["content"],
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

        updateDebugColors() {
            const debugElements = document.querySelectorAll('.debug-text, .bubble-debug-text');
            debugElements.forEach((element) => {
                element.style.color = this.getDebugColor(element.dataset.type ?? "");
            });
        },

        addDebug(text, color, type) {
            const sidebar = this.$refs.sidebar;
            sidebar.addDebugMessage(text, color, type);
        },

        // todo: recreate effect? does not currently do anything with new chatbubble component
        async editAnimationSpeechBubbleAI(active, color) {
            const aiBubble = this.getLastBubble().getElement();
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

        async editTextSpeechBubbleAI(text, isStatusMessage = false) {
            const aiBubble = this.getLastBubble();
            if (!aiBubble) {
                await this.addChatBubble(text, false, true);
            } else if (isStatusMessage) {
                aiBubble.addStatusMessage(text);
            } else {
                aiBubble.setContent(text);
            }
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

        async generateAudioForMessage(messageId, text) {
            try {
                const messageBubble = document.getElementById(messageId);
                if (!messageBubble) {
                    console.error('Message bubble not found:', messageId);
                    return;
                }

                // Get the containers
                const actionContainer = messageBubble.querySelector(".message-actions");
                const audioContainer = messageBubble.querySelector(".audio-container");

                if (!audioContainer) return;

                // Show loading state in place of the button
                actionContainer.innerHTML = `
                    <div class="audio-loading">
                        <div class="loader"></div>
                        <span>Generating audio...</span>
                    </div>
                `;

                // Make API call
                const response = await fetch(`${conf.VoiceServerAddress}/generate_audio?${new URLSearchParams({
                    text: text,
                    voice: 'alloy'
                })}`, {
                    method: 'POST'
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('API error:', response.status, errorText);
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                // Get audio blob
                const audioBlob = await response.blob();
                const audioUrl = URL.createObjectURL(audioBlob);

                // Use this to get around the blocking of autoplay by browsers (based on https://stackoverflow.com/questions/50490304/how-to-make-audio-autoplay-on-chrome)
                // This works for chromium based browsers, but not for firefox and safari.
                // Safari will autoplay the audio if the user clicked on the generate button (as the user initiated that)
                // But if we automatically generate audio, it will not play automatically
                const silenceUrl = `
                <iframe src="../assets/silence.mp3" allow="autoplay" id="audio" style="display: none"></iframe>
                `;

                actionContainer.remove();
                actionContainer.innerHTML = silenceUrl;

                // Create audio player
                const audioPlayer = `
                    <audio controls autoplay>
                        <source src="${audioUrl}" type="audio/mpeg">
                        Your browser does not support the audio element.
                    </audio>
                `;

                // Remove the action container and update audio container
                actionContainer.remove();
                audioContainer.innerHTML = audioPlayer;

            } catch (error) {
                console.error('Error generating audio:', error);
                const actionContainer = messageBubble.querySelector(".message-actions");
                if (actionContainer) {
                    actionContainer.innerHTML = `
                        <div class="audio-error">
                            <i class="fa fa-exclamation-circle"></i>
                            Error generating audio
                        </div>
                    `;
                }
            }
        },

        setupTooltips() {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
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

        if (!this.isMobile) {
            await this.addChatBubble(conf.translations[this.language].welcome, false, false);
        }

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

#chat-container {
    width: 100%;
    max-width: min(95%, 120ch);
    padding: 0.25rem;
    margin: 0 auto;
    position: relative;
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

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
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

/* ??? */

.fixed {
    position: fixed !important;
}

.d-flex.justify-content-start.flex-grow-1.w-100 {
    position: relative;
    z-index: 1;
}

</style>
