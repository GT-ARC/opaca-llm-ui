<template>
    <div class="d-flex justify-content-start flex-grow-1 w-100 position-relative z-1"
         @dragover.prevent="() => toggleFileDropOverlay(true)"
         @dragenter.prevent="() => toggleFileDropOverlay(true)">

        <!-- File Drop Overlay -->
        <div v-if="showFileDropOverlay" id="fileDropOverlay"
             @dragleave.prevent="() => toggleFileDropOverlay(false)"
             @drop.prevent="e => {toggleFileDropOverlay(false); uploadFiles(e.dataTransfer.files);}">
            <div id="overlayContent">
                <p>{{ Localizer.get("dropFiles") }}</p>
                <span class="fa fa-file-pdf" />
            </div>
        </div>

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
            :method="method"
            :language="language"
            :connected="connected"
            :selected-chat-id="selectedChatId"
            :is-finished="isFinished"
            ref="sidebar"
            @select-question="question => this.handleSelectQuestion(question)"
            @select-category="category => this.handleSelectCategory(category)"
            @select-chat="chatId => this.handleSelectChat(chatId)"
            @delete-chat="chatId => this.handleDeleteChat(chatId)"
            @rename-chat="(chatId, newName) => this.handleRenameChat(chatId, newName)"
            @new-chat="() => {this.suspendAllFiles(); this.startNewChat()}"
            @delete-file="fileId => this.handleDeleteFile(fileId)"
            @suspend-file="(fileId, suspend) => this.handleSuspendFile(fileId, suspend)"
            @goto-search-result="(chatId, messageId) => this.gotoSearchResult(chatId, messageId)"
        />


        <!-- Main Container: Chat Window, Text Input -->
        <main id="mainContent" class="mx-auto"
            :class="{ 'd-flex flex-column flex-grow-1': this.isMainContentVisible(), 'd-none': !this.isMainContentVisible() }">

            <!-- Chat Window with Chat bubbles -->
            <div class="container-fluid flex-grow-1 chat-container" id="chat1"
                @scroll="this.handleChatScroll">
                <div class="chatbubble-container d-flex flex-column justify-content-between mx-auto">
                    <Chatbubble
                        v-for="{ elementId, isUser, content, isLoading, files, bookmarked } in this.messages"
                        :key="content"
                        :element-id="elementId"
                        :is-user="isUser"
                        :initial-content="content"
                        :initial-loading="isLoading"
                        :is-bookmarked="bookmarked"
                        :files="files"
                        :chat-id="this.selectedChatId"
                        :ref="elementId"
                        @add-to-library="addPromptToSidebar"
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

            <!-- Upload Preview for Each File -->
            <div v-if="selectedFiles?.length"
                 class="upload-status-preview mx-auto">

                <!-- Loop through each selected file -->
                <div v-for="(fileObj, index) in selectedFiles" :key="fileObj.fileId || (fileObj.file?.name + '-' + index)">
                    <FilePreview
                        v-if="index < this.maxDisplayedFiles()"
                        :key="fileObj.fileId"
                        :file-id="fileObj.fileId"
                        :file="fileObj.file"
                        :is-uploading="fileObj.isUploading"
                        @remove-file="this.handleDeleteFile"
                    />
                </div>

                <div v-if="selectedFiles?.length > this.maxDisplayedFiles()"
                     class="d-flex p-2 align-items-center">
                    {{ Localizer.get('fileOverflow', selectedFiles.length - this.maxDisplayedFiles()) }}
                </div>
            </div>

            <!-- Input Area -->
            <div class="input-container">

                <div class="input-area"
                     @click="this.$refs.textInputRef?.focus()" >
                    <div class="scroll-wrapper" :class="{'w-100': this.isMobile}">
                        <textarea
                            id="textInput"
                            v-model="textInput"
                            class="text-input form-control"
                            :class="{ 'small-scrollbar': isSmallScrollbar }"
                            :placeholder="Localizer.get('inputPlaceholder')"
                            rows="1"
                            @keydown="textInputCallback"
                            @input="resizeTextInput"
                            @paste="handlePaste"
                            ref="textInputRef"
                        />
                    </div>

                    <!-- buttons -->
                    <div class="mt-auto d-flex" :class="{'w-100': this.isMobile}">

                        <!-- upload file button -->
                        <label class="btn btn-secondary input-area-button align-items-center"
                               :class="[this.isMobile ? 'me-1': 'ms-1']"
                               :title="Localizer.get('tooltipUploadFile')" >
                            <i class="fa fa-upload" />
                            <input
                                type="file"
                                ref="fileInput"
                                accept=".pdf"
                                class="d-none"
                                :disabled="!this.isFinished"
                                @change="e => uploadFiles(e.target.files)"
                                multiple
                            />
                        </label>

                        <!-- reset, audio, send (right-bound) -->
                        <div :class="{'ms-auto': this.isMobile}">
                            <button type="button"
                                    v-if="AudioManager.isRecognitionSupported()"
                                    class="btn btn-outline-primary input-area-button ms-1"
                                    @click="this.startRecognition()"
                                    :disabled="!isFinished"
                                    :title="Localizer.get('tooltipButtonRecord')">
                                <i v-if="!AudioManager.isLoading" class="fa fa-microphone" />
                                <i v-else class="fa fa-spin fa-spinner" />
                            </button>

                            <button type="button"
                                    v-if="!isFinished"
                                    class="btn btn-outline-danger input-area-button ms-1"
                                    @click="stopGeneration"
                                    :title="Localizer.get('tooltipButtonStop')">
                                <i class="fa fa-stop"/>
                            </button>

                            <button type="button"
                                    v-if="isFinished"
                                    class="btn btn-primary input-area-button ms-1"
                                    @click="submitText"
                                    :disabled="this.textInput.trim().length <= 0"
                                    :title="Localizer.get('tooltipButtonSend')">
                                <i class="fa fa-paper-plane" style="transform: translateX(-1px)" />
                            </button>
                        </div>

                    </div>

                </div>
            </div>

        </main>

    </div>

</template>

<script>
import {nextTick} from "vue";
import * as uuid from "uuid";
import Sidebar from "./Sidebar/Sidebar.vue";
import RecordingPopup from './RecordingPopup.vue';
import Chatbubble from "./chatbubble.vue";
import conf from '../../config'
import backendClient from "../utils.js";
import Localizer from "../Localizer.js";
import AudioManager from "../AudioManager.js";
import { useDevice } from "../useIsMobile.js";
import SidebarManager from "../SidebarManager";
import OptionsSelect from "./OptionsSelect.vue";
import FilePreview from "./FilePreview.vue";

export default {
    name: 'main-content',
    components: {
        FilePreview,
        OptionsSelect,
        Sidebar,
        RecordingPopup,
        Chatbubble
    },
    props: {
        method: String,
        language: String,
        connected: Boolean,
    },
    emits: [
        'select-category',
        'container-login-required',
    ],
    setup() {
        const { isMobile, screenWidth } = useDevice()
        return { conf, SidebarManager, Localizer, AudioManager, isMobile, screenWidth };
    },
    data() {
        return {
            messages: [],
            textInput: '',
            isFinished: true,
            showExampleQuestions: true,
            autoSpeakNextMessage: false,
            showRecordingPopup: false,
            selectedCategory: conf.DefaultQuestions,
            isSmallScrollbar: true,
            selectedFiles: [],
            selectedChatId: '',
            newChat: false,
            showFileDropOverlay: false,
            autoScrollEnabled: true,
            socket: null,
        }
    },
    methods: {
        async textInputCallback(event) {
            if (event.key === 'Enter' && !event.shiftKey && this.textInput.trim().length > 0) {
                event.preventDefault();
                await this.submitText();
                this.resizeTextInput();
            }
        },

        async submitText() {
            if (this.textInput && this.isFinished) {
                // Copy current input and reset field
                let userInput = this.textInput.trim();
                this.textInput = '';

                await nextTick();
                this.resizeTextInput();

                const files = this.selectedFiles
                    ? this.selectedFiles.map(file => file.name)
                    : [];
                await this.askChatGpt(userInput, files);

                // Clear files list after sending
                this.selectedFiles = [];

                // update chats list
                await this.$refs.sidebar.$refs.chats.updateChats();
            }
        },

        async stopGeneration() {
            await backendClient.stop();
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

        async askChatGpt(userText, files = null) {
            this.isFinished = false;
            this.showExampleQuestions = false;
            this.newChat = false;

            // add user chat bubble
            await this.addChatBubble(userText, true, false, files);

            // add debug entry for user message
            const debug = this.$refs.sidebar.$refs.debug;
            debug.addDebugMessage(userText, "user");

            // add AI chat bubble in loading state, add prepare message
            await this.addChatBubble('', false, true);
            const aiBubble = this.getLastBubble();
            aiBubble.addStatusMessage('preparing', Localizer.getLoadingMessage('preparing'), false);

            // get chat response (intermediate results are streamed via websocket)
            try {
                const result = await backendClient.query(this.selectedChatId, this.method, userText, true, 5*60*1000);

                // display final result
                if (result.error) {
                    aiBubble.setError(result.error);
                    this.$refs.sidebar.$refs.debug.addDebugMessage(`\n${result.content}\n\nCause: ${result.error}\n`, "ERROR");
                }
                aiBubble.setContent(result.content);
            } finally {
                // always set to completed, even in case of error, e.g. timeout
                aiBubble.toggleLoading(false);
                this.isFinished = true;
                this.startAutoSpeak();
                this.scrollDownChat();
            }
        },

        async toggleFileDropOverlay(show) {
            this.showFileDropOverlay = show;
        },

        async uploadFiles(fileList) {
            const files = Array.from(fileList);

            // Filter out non-PDFs
            const pdfFiles = files.filter(file => file.type === "application/pdf");

            if (pdfFiles.length === 0) {
                alert("Only PDF files are allowed.");
                return;
            }

            // Save selected files to state
            // Files will remain here while component instance is alive (i.e. till page reload)
            const wrappedFiles = pdfFiles.map(file => ({
                file,
                fileId: null,
                isUploading: true
            }));
            this.selectedFiles.push(...wrappedFiles);

            try {
                const result = await backendClient.uploadFiles(files);

                result.uploaded_files.forEach((uploaded, idx) => {
                    const wrapper = wrappedFiles[idx];
                    wrapper.fileId = uploaded.file_id;
                    wrapper.isUploading = false;
                });
            } catch (error) {
                console.error("File upload failed:", error);
                alert("File upload failed. See console for details.");
            } finally {
                // Force vue to update
                this.selectedFiles = [...this.selectedFiles];
                this.$refs.fileInput.value = "";
                await this.$refs.sidebar.$refs.files.updateFiles();
            }
        },

        // Remove selected file
        async handleDeleteFile(fileId) {
            // Clean up preview if it exists
            this.selectedFiles = this.selectedFiles.filter(f => f.fileId !== fileId);

            // From backend
            await backendClient.deleteFile(fileId);
            await this.$refs.sidebar.$refs.files.updateFiles();
        },

        async handleSuspendFile(fileId, suspend) {
            await backendClient.suspendFile(fileId, suspend);
            await this.$refs.sidebar.$refs.files.updateFiles();
        },

        async suspendAllFiles() {
            const files = await backendClient.files();
            for (const file of Object.values(files)) {
                if (!file.suspended) {
                    await backendClient.suspendFile(file.file_id, true);
                }
            }
            await this.$refs.sidebar.$refs.files.updateFiles();
        },

        maxDisplayedFiles() {
            return this.isMobile ? 2 : 4;
        },

        async connectWebsocket() {
            const url = `${conf.BackendAddress}/ws`
            this.socket = new WebSocket(url);
            this.socket.onmessage = event => this.handleStreamingSocketMessage(event);
        },

        async handleStreamingSocketMessage(event) {
            const aiBubble = this.getLastBubble();
            const result = JSON.parse(event.data);

            if (result.type === "ContainerLoginNotification") {
                this.$emit('container-login-required', result);
            }

            if (result.type === "MissingApiKeyNotification") {
                this.$emit('api-key-required', result);
            }

            if (result.type === "TextChunkMessage") {
                // chunk: str
                // is_output: bool
                if (result.is_output) {
                    aiBubble.toggleLoading(false);
                    aiBubble.addContent(result.chunk);
                    this.scrollDownChat();
                }
                await this.addDebugToken(result);
                this.scrollDownDebug();
            }

            if (result.type === "ToolCallMessage") {
                await this.addDebugTool(result.agent, result);
                this.scrollDownDebug();
            }

            if (result.type === "ToolResultMessage") {
                await this.addDebugResult(result);
                this.scrollDownDebug();
            }

            if (result.type === "StatusMessage") {
                const agentName = result.agent;
                const message = result.status;
                if (message) {
                    aiBubble.markStatusMessagesDone(agentName);
                    aiBubble.addStatusMessage(agentName, message, false);
                }
                this.scrollDownChat();
            }

            if (result.type === "PendingCallback") {
                await this.addChatBubble(`Working on deferred query: ${result.query}`, false, true);
            }

            if (result.type === "PushMessage") {
                if (result.error) {
                    aiBubble.setError(result.error);
                }
                aiBubble.setContent(result.content);
                aiBubble.toggleLoading(false);
                this.isFinished = true;
                this.startAutoSpeak();
                this.scrollDownChat();
            }

            if (result.type === "MetricsMessage") {
                // metrics: dict
                // execution_time: float
                // TODO do something with metrics messages
            }
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

        submitContainerLogin(containerLoginUser, containerLoginPassword, containerLoginTimeout) {
            const containerLoginDetails = JSON.stringify({
                username: containerLoginUser,
                password: containerLoginPassword,
                timeout: containerLoginTimeout,
            });
            this.socket.send(containerLoginDetails);
        },

        submitApiKey(apiKey) {
            const apiKeyResponse = JSON.stringify({api_key: apiKey});
            this.socket.send(apiKeyResponse);
        },


        handleRecordingError(error) {
            console.error('Recording error:', error);
            alert('Error recording audio: ' + error.message);
        },

        startRecognition() {
            if (AudioManager.isVoiceServerConnected && AudioManager.useWhisperStt) {
                this.showRecordingPopup = true;
            } else {
                AudioManager.startWebSpeechRecognition(text => {
                    this.handleTranscriptionComplete(text);
                    this.autoSpeakNextMessage = true;
                    this.submitText();
                });
            }
        },

        /**
         * @param content {string} initial chatbubble content
         * @param isUser {boolean} whether the message is by the user or the AI
         * @param isLoading {boolean} initial loading state, should be true if the bubble is intended to be edited
         * @param files {Array} files attached to the message
         * later (streaming responses etc.)
         */
        async addChatBubble(content, isUser = false, isLoading = false, files = null) {
            const elementId = `chatbubble-${this.messages.length}`;

            const bookmarked = this.compareToBookmarks(content);

            const message = {
                elementId: elementId,
                isUser: isUser,
                content: content,
                isLoading: isLoading,
                files: files,
                bookmarked: bookmarked,
            };
            this.messages.push(message);

            // wait for the next rendering tick so that the component is mounted
            await nextTick();
            this.scrollDownChat();
        },

        compareToBookmarks(content) {
            const bookmarks = this.$refs.sidebar.$refs.questions.personalPrompts;
            return bookmarks.some(b => b.question.trim() === content.trim());
        },

        handleUnexpectedConnectionClosed(message) {
            console.error('Connection closed unexpectedly', message);
            const aiBubble = this.getLastBubble();
            aiBubble.setContent(message);
            aiBubble.toggleLoading(false);
            aiBubble.setError("Connection closed unexpectedly");
        },

        handleChatScroll() {
            const chat = document.getElementById('chat1');
            this.autoScrollEnabled = chat.scrollTop + chat.clientHeight >= chat.scrollHeight - 50;
        },

        scrollDownChat() {
            if (!this.autoScrollEnabled) return;
            const div = document.getElementById('chat1');
            div.scrollTop = div.scrollHeight;
        },

        scrollDownDebug() {
            this.$refs.sidebar.$refs.debug.scrollDownDebugView();
        },

        async addDebugToken(chunk) {
            this.addDebug(chunk.chunk, chunk.agent, chunk.id);
        },

        async addDebugTool(llm_agent, tool) {
            const id = tool.id.split("/")[1];
            const [agent, action] = tool.name.split("--");
            const args = Object.entries(tool.args).map(([k, v]) => `- ${k}: ${JSON.stringify(v)}`).join("\n");
            const toolOutput = `Tool: ${id}\nAgent: ${agent}\nAction: ${action}\nArguments:\n${args}\n`;
            this.addDebug(toolOutput, llm_agent, tool.id);
        },

        async addDebugResult(result) {
            const id = result.id.split("/")[1];
            const toolOutput = `Result: ${JSON.stringify(result.result)}`
            this.addDebug(toolOutput, `Result ${id}`, result.id);
        },

        addDebug(text, type, id=null) {
            const debug = this.$refs.sidebar.$refs.debug;
            debug.addDebugMessage(text, type, id);
            const aiBubble = this.getLastBubble();
            aiBubble.addDebugMessage(text, type, id);
        },

        isMainContentVisible() {
            return !(this.isMobile && SidebarManager.isSidebarOpen());
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

        async loadHistory(chatId) {
            if (!chatId || chatId === this.selectedChatId) return;
            try {
                const res = await backendClient.history(chatId);
                const debug = this.$refs.sidebar.$refs.debug;

                // clear messages
                this.messages = [];
                debug.clearDebugMessages();

                // add messages from history
                for (const msg of res.responses) {
                    if (!msg) continue;
                    // request
                    await this.addChatBubble(msg.query, true);
                    debug.addDebugMessage(msg.query, "user");
                    // response
                    await this.addChatBubble(msg.content, false);
                    for (const agent_message of msg.agent_messages) {
                        const chunk = {
                            id: agent_message.id,
                            agent: agent_message.agent,
                            chunk: agent_message.content,
                            is_output: false,
                        }
                        this.addDebugToken(chunk);
                        for (const tool of agent_message.tools) {
                            this.addDebugTool(agent_message.agent, tool);
                            this.addDebugResult({id: tool.id, result: tool.result});
                        }
                    }
                    if (msg.error) {
                        this.getLastBubble().setError(msg.error);
                    }
                }

                if (this.messages.length !== 0) {
                    this.showExampleQuestions = false;
                    this.selectedChatId = chatId;
                    this.newChat = false;
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
        },

        async handleSelectChat(chatId) {
            await this.loadHistory(chatId);
            this.$refs.textInputRef.focus();
        },

        async handleDeleteChat(chatId) {
            await this.startNewChat();
            await backendClient.delete(chatId);
            await this.$refs.sidebar.$refs.chats.updateChats(chatId);
        },

        async handleRenameChat(chatId, newName) {
            try {
                await backendClient.updateName(chatId, newName);
            } finally {
                await this.$refs.sidebar.$refs.chats.updateChats(chatId);
            }
        },

        async startNewChat() {
            if (this.isMobile) {
                SidebarManager.close();
            }
            if (!this.newChat) {
                this.selectedChatId = uuid.v4();
                this.newChat = true;
                this.messages = [];
                this.$refs.sidebar.$refs.debug.clearDebugMessages();
                this.textInput = '';
                this.showExampleQuestions = true;
                Localizer.reloadSampleQuestions(null);
            }
            await nextTick();
            this.$refs.textInputRef.focus();
        },

        async scrollToMessage(messageId) {
            const elementId = this.messages[messageId]?.elementId;
            const ref = this.$refs[elementId]?.[0];
            if (this.isMobile) {
                SidebarManager.close();
                await nextTick();
                const messageDiv = ref?.getElement();
                const messageRect = messageDiv?.getBoundingClientRect();
                const container = document.getElementById('chat1');
                const containerRect = container?.getBoundingClientRect();
                container.scrollTop = messageRect.top - containerRect.top;
            } else {
                await nextTick();
                const messageDiv = ref?.getElement();
                messageDiv.scrollIntoView({ behavior: 'smooth' });
            }
        },

        async gotoSearchResult(chatId, messageId) {
            await this.loadHistory(chatId);
            await this.scrollToMessage(messageId);
        },

        async handlePaste(event) {
            const items = event.clipboardData.items;

            const files = [];

            for (let i = 0; i < items.length; i++) {
                const item = items[i];
                if (item.kind === "file") {
                    const file = item.getAsFile();
                    if (file) files.push(file);
                }
            }

            if (files.length > 0) {
                // Prevent from being inserted into the input
                event.preventDefault();

                await this.uploadFiles(files);
            }
            // If no file found, let normal paste happen
        },

        addPromptToSidebar(prompt) {
            // call SidebarQuestions method
            this.$refs.sidebar.$refs.questions.addPersonalPrompt(prompt);
        },
    },

    mounted() {
        this.startNewChat();
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
    padding: 1rem 0;
}

.input-container {
    width: 100%;
    background-color: var(--background-color);
    padding: 0.5rem 0.5rem 1rem 0.5rem; /* 1rem bottom padding so it's the same as sidebar */
    flex-shrink: 0;
    position: relative;
}

.text-input {
    padding: 0.75rem;
    margin: 0;
    min-height: 2.5rem;
    max-height: min(33vh, 20rem);
    line-height: 1.5;
    border-radius: 0 !important;
    resize: none;
    height: auto;
    border: none;
    box-shadow: none;
}

.text-input[rows] {
    height: auto;
    overflow-y: auto;
}

.input-area {
    position: relative;
    display: flex;
    flex-wrap: wrap;
    align-items: stretch;
    background-color: var(--input-color);
    width: min(95%, 100ch);
    border-radius: 1rem;
    cursor: text;
    padding: 0.5rem;
    margin-left: auto;
    margin-right: auto;
}

.input-area:focus-within {
    outline: 2px solid var(--primary-color);
}

.scroll-wrapper {
    overflow: hidden;
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    min-width: 16ch;
}

.small-scrollbar::-webkit-scrollbar-thumb {
    background-color: transparent !important;
}

.upload-status-preview {
    font-size: 0.9rem;
    border-radius: 6px;
    background-color: var(--background-color);
    color: var(--text-primary-color);
    display: flex;
    flex-wrap: wrap;
    width: min(95%, 100ch);
    padding: 0.25rem 0;
}

.input-area-button {
    padding: 0;
    width: 2.5rem;
    height: 2.5rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    align-self: flex-end;
    margin-bottom: 2px;
    border-radius: 1.25rem !important;
    transition: all 0.2s ease;
}

.input-area-button:hover {
    transform: translateY(-1px);
}

.input-area-button:disabled {
    opacity: 0.5;
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

.btn-outline-danger:disabled {
    color: var(--text-primary-color);
    border-color: var(--text-primary-color);
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

#fileDropOverlay {
    position: absolute;
    display: flex;
    height: calc(100% - 2rem); /* room for margin + border */
    width: calc(100% - 2rem); /* room for margin + border */
    background: color-mix(in srgb, var(--background-color) 80%, transparent); /* Adds opacity */
    color: var(--primary-color);
    align-items: center;
    justify-content: center;
    z-index: 2000;
    transition: opacity 0.2s ease;
    backdrop-filter: blur(3px);
    border: 3px dashed var(--primary-color);
    border-radius: 1rem;
    margin: 1rem;
}

#overlayContent {
    font-size: 1.5rem;
    text-align: center;
    pointer-events: none;
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

    .input-container {
        padding: 0;
    }

    .input-area {
        width: 100%;
        margin: 0;
        border-radius: 0;
    }

    .text-input {
        padding: 0.5rem 0.25rem;
    }

    .sample-questions {
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
