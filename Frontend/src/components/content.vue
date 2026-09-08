<template>
    <div class="d-flex justify-content-start flex-grow-1 w-100 position-relative z-1"
         @dragover.prevent="() => this.$refs.fileDropHandler?.toggleFileDropOverlay(true)"
         @dragenter.prevent="() => this.$refs.fileDropHandler?.toggleFileDropOverlay(true)">

        <!-- File Viewer Overlay -->
        <FileViewer
            :visible="!!viewerFile"
            :fileName="viewerFile?.fileName"
            :src="viewerFile?.src"
            :mime-type="viewerFile?.mimeType"
            @close="viewerFile = null"
        />

        <InputDialogue ref="input" />
        <FileDropHandler
            ref="fileDropHandler"
            @files-dropped="handleFiles"
            @text-dropped="insertDroppedText"
        />

        <Sidebar
            :connected="connected"
            :selected-chat-id="selectedChatId"
            ref="sidebar"
            @select-question="question => this.handleSelectQuestion(question)"
            @select-chat="chatId => this.handleSelectChat(chatId)"
            @delete-chat="chatId => this.handleDeleteChat(chatId)"
            @rename-chat="(chatId, newName) => this.handleRenameChat(chatId, newName)"
            @new-chat="() => this.startNewChat()"
            @delete-file="fileId => this.handleDeleteFile(fileId)"
            @delete-all-files="() => this.handleDeleteAllFiles()"
            @upload-file="() => this.$refs.fileInput?.click()"
            @view-file="openViewer"
            @rename-file="handleRenameFile"
            @goto-search-result="(chatId, messageId) => this.gotoSearchResult(chatId, messageId)"
            @delete-all-chats="() => this.handleDeleteAllChats()"
        />


        <!-- Main Container: Chat Window, Text Input -->
        <main id="mainContent" class="mx-auto"
              :class="{ 'd-flex flex-column flex-grow-1': this.isMainContentVisible(), 'd-none': !this.isMainContentVisible() }">

            <!-- Chat Window with Chat bubbles -->
            <div class="container-fluid flex-grow-1 chat-container" id="chat1"
                 @scroll="this.handleChatScroll">
                <div class="chatbubble-container d-flex flex-column justify-content-between mx-auto">
                    <Chatbubble
                        v-for="{ elementId, isUser, content, isLoading, files } in this.messages"
                        :key="content"
                        :element-id="elementId"
                        :is-user="isUser"
                        :initial-content="content"
                        :initial-loading="isLoading"
                        :files="files"
                        :chat-id="this.selectedChatId"
                        @view-file="openViewer"
                        :ref="elementId"
                    />
                </div>

                <!-- sample questions -->
                <div v-show="showExampleQuestions" class="sample-questions">
                    <div v-if="!this.isMobile" class="w-100 p-3 text-center fs-4">
                        {{ Localizer.get("chatarea_welcome") }}
                    </div>
                    <div v-for="(question, index) in Localizer.getSampleQuestions(this.textInput, conf.selectedCategory)"
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
                            {{ Localizer.get('chatarea_rerollSamples') }}
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
                        @view-file="openViewer"
                    />
                </div>

                <div v-if="selectedFiles?.length > this.maxDisplayedFiles()"
                     class="d-flex p-2 align-items-center">
                    {{ Localizer.get('files_overflow', selectedFiles.length - this.maxDisplayedFiles()) }}
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
                            :placeholder="Localizer.get('chatarea_input')"
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
                               :class="[this.isMobile ? 'me-1': 'ms-1', !this.isChatFinished() ? 'disabled' : '']"
                               :title="Localizer.get('files_upload')" >
                            <i class="fa fa-upload" />
                            <input
                                type="file"
                                ref="fileInput"
                                class="d-none"
                                @change="handleFileSelection"
                                multiple
                            />
                        </label>

                        <!-- reset, audio, send (right-bound) -->
                        <div :class="{'ms-auto': this.isMobile}">
                            <button type="button"
                                    v-if="AudioManager.isRecognitionSupported() && ! AudioManager.isRecording"
                                    class="btn btn-outline-primary input-area-button ms-1"
                                    @click="this.startRecognition()"
                                    :disabled="!this.isChatFinished()"
                                    :title="Localizer.get('chatarea_speak')">
                                <i v-if="AudioManager.isTranscribing" class="fa fa-spin fa-spinner" />
                                <i v-else class="fa fa-microphone" />
                            </button>
                            <button type="button"
                                    v-if="AudioManager.isRecognitionSupported() && AudioManager.isRecording"
                                    class="btn btn-outline-primary input-area-button ms-1"
                                    @click="AudioManager.stopRecognition()"
                                    :disabled="!this.isChatFinished()"
                                    :title="Localizer.get('chatarea_speak_stop')">
                                <i class="fa fa-stop"/>
                            </button>

                            <button type="button"
                                    v-if="!this.isChatFinished()"
                                    class="btn btn-outline-danger input-area-button ms-1"
                                    @click="stopGeneration"
                                    :title="Localizer.get('chatarea_abort')">
                                <i class="fa fa-xmark"/>
                            </button>

                            <button type="button"
                                    v-if="this.isChatFinished()"
                                    class="btn btn-primary input-area-button ms-1"
                                    @click="submitText"
                                    :disabled="this.textInput.trim().length <= 0 || this.hasPendingUploads()"
                                    :title="Localizer.get('chatarea_submit')">
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
import Chatbubble from "./chatbubble.vue";
import conf, {addListener} from '../../config.js'
import backendClient, { formatAgentDebugText, formatToolDebugResult } from "../utils.js";
import Localizer from "../Localizer.js";
import AudioManager from "../AudioManager.js";
import { useDevice } from "../useIsMobile.js";
import SidebarManager from "../SidebarManager";
import OptionsSelect from "./OptionsSelect.vue";
import FilePreview from "./FilePreview.vue";
import FileViewer from "./FileViewer.vue";
import InputDialogue from "./InputDialogue.vue";
import FileDropHandler from "./FileDropHandler.vue";
import {
    clearMissedChatResponse as clearTabMissedChatResponse,
    markMissedChatResponse as markTabMissedChatResponse,
    showDesktopNotification,
} from "../browserNotifications.js";

export default {
    name: 'main-content',
    components: {
        FilePreview,
        FileViewer,
        OptionsSelect,
        Sidebar,
        InputDialogue,
        Chatbubble,
        FileDropHandler,
    },
    props: {
        connected: Boolean,
    },
    emits: [
        'action-confirmation-required',
        'container-login-required',
        'api-key-required',
        'new-notification',
    ],
    setup() {
        const { isMobile } = useDevice()
        return { conf, Localizer, AudioManager, isMobile };
    },
    data() {
        return {
            messages: [],
            textInput: '',
            showExampleQuestions: true,
            autoSpeakNextMessage: false,
            isSmallScrollbar: true,
            selectedFiles: [],
            pendingFileOperations: 0,
            selectedChatId: '',
            newChat: false,
            autoScrollEnabled: true,
            socket: null,
            viewerFile: null,
            windowIsFocused: true,
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
            if (this.textInput && this.isChatFinished() && !this.hasPendingUploads()) {
                // Copy current input and reset field
                let userInput = this.textInput.trim();
                this.textInput = '';

                await nextTick();
                this.resizeTextInput();

                const files = this.selectedFiles.map(wrappedFile => this.createMessageFile(wrappedFile.file));
                const fileIds = this.selectedFiles
                    .map(wrappedFile => wrappedFile.fileId)
                    .filter(fileId => fileId != null);
                await this.askChatGpt(userInput, files, fileIds);

                // Clear files list after sending
                this.selectedFiles = [];

            }
        },

        async stopGeneration() {
            await backendClient.stopChat(this.selectedChatId);
        },

        async askSampleQuestion(questionText) {
            // Do not send questions during autogeneration
            if (questionText === "__loading__") return;

            var placeholders = questionText.match(/\[[^\]]+\]/g);
            if (placeholders !== null) {
                // substitute placeholders
                await this.$refs.input.showDialogue(
                    Localizer.get("questions_placeholders"), questionText, null,
                    Object.fromEntries(placeholders.map(x => [x, {type: "text", label: x}])),
                    async (values) => {
                        // ask the completed question
                        this.setTextAndSubmit(placeholders.reduce((t, k) => t.replace(k, values[k]), questionText));
                    }
                );
            } else {
                // just ask the question
                await this.setTextAndSubmit(questionText);
            }
        },

        async setTextAndSubmit(questionText) {
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
                console.warn('Tried to get the last chat bubble when none exist.');
                this.newChat = false;
                this.showExampleQuestions = false;
                this.addChatBubble("...");
            }
            const refId = this.messages[this.messages.length - 1].elementId;
            return this.$refs[refId][0];
        },

        async askChatGpt(userText, files = null, fileIds = []) {
            const chatId = this.selectedChatId;
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
            aiBubble.addStatusMessage('preparing', Localizer.get('chatbubble_preparing'), false);
            this.clearMissedChatResponse(chatId);

            // get chat response (intermediate results are streamed via websocket)
            try {
                const result = await backendClient.query(
                    chatId,
                    conf.method,
                    userText,
                    true,
                    5*60*1000,
                    fileIds,
                );

                // display final result
                if (this.selectedChatId === chatId) {
                    this.applyFinalResponse(result, this.getLastBubble());
                }

                if (this.shouldNotifyChatResponse(chatId)) {
                    this.markMissedChatResponse(chatId, result.content);
                }
            } finally {
                if (this.selectedChatId === chatId) {
                    // always set to completed, even in case of error, e.g. timeout
                    aiBubble.toggleLoading(false);
                    this.startAutoSpeak();
                    this.scrollDownChat();
                    await this.$refs.sidebar.updateChats();
                }
            }
        },

        applyFinalResponse(response, aiBubble) {
            if (!response || !aiBubble) return;
            if (response.error) {
                aiBubble.setError(response.error);
                this.$refs.sidebar.$refs.debug.addDebugMessage(`\n${response.content}\n\nCause: ${response.error}\n`, "ERROR");
            }
            aiBubble.setContent(response.content ?? '');
            this.syncStructuredAgentDebugMessages(response.agent_messages || []);
        },

        shouldNotifyChatResponse(chatId) {
            return !(chatId === this.selectedChatId
                && !document.hidden
                && this.windowIsFocused
                && this.isMainContentVisible());
        },

        shouldShowSystemChatNotification() {
            return document.hidden || !document.hasFocus() || ! this.windowIsFocused;
        },

        markMissedChatResponse(chatId, content) {
            this.$refs.sidebar.$refs.chats.markChatMissed(chatId);
            markTabMissedChatResponse(chatId);

            if (this.shouldShowSystemChatNotification()) {
                showDesktopNotification(
                    Localizer.get('notification_chatFinished'),
                    {
                        body: this.createNotificationPreview(content) || null,
                        onClick: async () => this.handleOpenMissedChatResponse(chatId),
                    },
                );
            }
        },

        clearMissedChatResponse(chatId = null) {
            this.$refs.sidebar.$refs.chats.clearChatMissed(chatId);
            clearTabMissedChatResponse(chatId);
        },

        createNotificationPreview(content) {
            const lines = (content ?? '')
                .split(/\r?\n/)
                .map(line => line.trim())
                .filter(line => line.length > 0)
                .slice(0, 3);
            const preview = lines.join('\n');
            return preview.length > 240 ? `${preview.substring(0, 237)}...` : preview;
        },

        async showInfo(message) {
            await this.$refs.input.showInfo(null, message);
        },

        async handleFiles(fileList) {
            const files = Array.from(fileList ?? []);
            if (files.length === 0) {
                return;
            }

            this.pendingFileOperations += 1;
            try {
                const { cancelled, formattedText, uploadableFiles } = await this.$refs.fileDropHandler.prepareFiles(
                    files,
                    message => this.showInfo(message)
                );
                if (cancelled) {
                    return;
                }

                if (formattedText.length > 0) {
                    await this.insertDroppedText(formattedText.join("\n\n"));
                }

                if (uploadableFiles.length > 0) {
                    await this.uploadFiles(uploadableFiles);
                }
            } finally {
                this.pendingFileOperations -= 1;
            }
        },

        async handleFileSelection(event) {
            try {
                await this.handleFiles(event.target.files);
            } finally {
                if (this.$refs.fileInput) {
                    this.$refs.fileInput.value = "";
                }
            }
        },

        async insertDroppedText(text) {
            const textarea = this.$refs.textInputRef;
            const normalizedText = text.replace(/\r\n/g, "\n");

            if (!textarea || typeof textarea.selectionStart !== "number") {
                this.textInput = `${this.textInput}${normalizedText}`;
                await nextTick();
                this.resizeTextInput();
                this.$refs.textInputRef?.focus();
                return;
            }

            const start = textarea.selectionStart;
            const end = textarea.selectionEnd;
            const currentInput = this.textInput ?? "";
            this.textInput = `${currentInput.slice(0, start)}${normalizedText}${currentInput.slice(end)}`;

            await nextTick();
            this.resizeTextInput();
            textarea.focus();
            const caretPosition = start + normalizedText.length;
            textarea.setSelectionRange(caretPosition, caretPosition);
        },

        async uploadFiles(fileList) {
            const files = Array.from(fileList);

            files.forEach(file => {
                if (file.type?.startsWith("image/") && !file.previewUrl) {
                    file.previewUrl = URL.createObjectURL(file);
                }
            });

            // Save selected files to state
            // Files will remain here while component instance is alive (i.e. till page reload)
            const wrappedFiles = files.map(file => ({
                file,
                fileId: null,
                isUploading: true,
            }));
            this.selectedFiles.push(...wrappedFiles);

            try {
                const result = await backendClient.uploadFiles(files, this.selectedChatId);

                result.uploadedFiles?.forEach((uploaded, idx) => {
                    const wrapper = wrappedFiles[idx];
                    wrapper.fileId = uploaded.file_id;
                    wrapper.isUploading = false;
                });

                await this.$refs.sidebar.$refs.files.updateFiles();
                await this.$refs.sidebar.updateChats();
            } catch (error) {
                console.error("File upload failed:", error);
                this.selectedFiles = this.selectedFiles.filter(wrapper => !wrappedFiles.includes(wrapper));
                const message = error instanceof Error ? error.message : String(error);
                await this.showInfo(`File upload failed: ${message}`);
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
            const res = await backendClient.deleteFile(fileId, false);
            if (res === false) {
                await this.$refs.input.showDialogue(
                    Localizer.get("files_delete"), Localizer.get("files_delete_failed"), null, {},
                    async (values) => {
                        await backendClient.deleteFile(fileId, true);
                        await this.$refs.sidebar.$refs.files.updateFiles();
                    }
                );
            } else {
                await this.$refs.sidebar.$refs.files.updateFiles();
            }
        },

        async handleDeleteAllFiles() {
            const fileIds = Object.keys(this.$refs.sidebar.$refs.files.files);

            this.viewerFile = null;
            this.selectedFiles = [];

            for (const fileId of fileIds) {
                await this.handleDeleteFile(fileId);
            }

            await this.$refs.sidebar.updateChats();
        },

        async handleRenameFile(fileId, newName) {
            await backendClient.renameFile(fileId, newName);
            await this.$refs.sidebar.$refs.files.updateFiles();
        },

        maxDisplayedFiles() {
            return this.isMobile ? 2 : 4;
        },

        createMessageFile(file) {
            return {
                name: file.name,
                type: file.type,
                url: file.url || file.previewUrl || null,
            };
        },

        async connectWebsocket() {
            const url = `${conf.backendUrl}/ws`
            this.socket = new WebSocket(url);
            this.socket.onmessage = event => this.handleStreamingSocketMessage(event);
        },

        async handleStreamingSocketMessage(event) {
            const result = JSON.parse(event.data);

            // Abort if the websocket message is not for the currently
            // selected chat.
            if (result.chat_id !== undefined && result.chat_id !== this.selectedChatId) {
                return;
            } else if (result.chat_id !== undefined && (!this.messages || this.messages.length === 0)) {
                console.warn('No chat bubbles for streaming found.');
                return;
            }

            if (result.type === 'ReloadChatsMessage') {
                await this.$refs.sidebar.updateChats();
            }

            if (result.type === "ConfirmActionNotification") {
                this.$emit('action-confirmation-required', result);
            }

            if (result.type === "ContainerLoginNotification") {
                this.$emit('container-login-required', result);
            }

            if (result.type === "MissingApiKeyNotification") {
                this.$emit('api-key-required', result);
            }

            if (result.type === "TextChunkMessage") {
                // chunk: str
                // is_output: bool
                if (result.is_output && !this.isChatFinished()) {
                    const aiBubble = this.getLastBubble();
                    aiBubble.toggleLoading(false);
                    aiBubble.addContent(result.chunk);
                    this.scrollDownChat();
                }
                this.addDebugToken(result);
                this.scrollDownDebug();
            }

            if (result.type === "ResetTextMessage") {
                const aiBubble = this.getLastBubble();
                aiBubble.setContent("");
            }

            if (result.type === "ToolCallMessage") {
                this.addDebugTool(result.agent, result);
                this.scrollDownDebug();
            }

            if (result.type === "ToolResultMessage") {
                this.addDebugResult(result);
                this.scrollDownDebug();
            }

            if (result.type === "StatusMessage") {
                const agentName = result.agent;
                const message = result.status;
                if (message) {
                    const aiBubble = this.getLastBubble();
                    aiBubble.markStatusMessagesDone(agentName);
                    aiBubble.addStatusMessage(agentName, message, false);
                }
                this.scrollDownChat();
            }

            if (result.type === "PushAdvert" || result.type === "PushMessage") {
                this.$emit('new-notification', result);
            }

            if (result.type === "MetricsMessage") {
                const aiBubble = this.getLastBubble();
                aiBubble.addMetric(result);
            }
        },

        startAutoSpeak() {
            if (this.autoSpeakNextMessage) {
                const aiBubble = this.getLastBubble();
                aiBubble.startAudioPlayback();
                this.autoSpeakNextMessage = false;
            }
        },

        submitContainerLogin(id, containerLoginUser, containerLoginPassword, containerLoginTimeout) {
            const containerLoginDetails = JSON.stringify({
                id: id,
                username: containerLoginUser,
                password: containerLoginPassword,
                timeout: containerLoginTimeout,
            });
            this.socket.send(containerLoginDetails);
        },

        submitConfirmAction(id, allowed) {
            this.socket.send(JSON.stringify({id: id, allowed: allowed}));
        },

        submitApiKey(id, apiKey) {
            const apiKeyResponse = JSON.stringify({id: id, api_key: apiKey});
            this.socket.send(apiKeyResponse);
        },

        startRecognition() {
            AudioManager.startRecognition(text => {
                if (text) {
                    this.textInput = text;
                    this.autoSpeakNextMessage = true;
                    this.submitText();
                }
            }, error => this.showInfo(error));
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

            const message = {
                elementId: elementId,
                isUser: isUser,
                content: content,
                isLoading: isLoading,
                files: files,
            };
            this.messages.push(message);

            // wait for the next rendering tick so that the component is mounted
            await nextTick();
            this.scrollDownChat();
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

        addDebugToken(chunk) {
            this.addDebug(chunk.chunk, chunk.agent, chunk.id);
        },

        addDebugTool(llm_agent, tool) {
            const id = tool.id.split("/")[1];
            const [agent, action] = tool.name.split("--");
            const args = Object.entries(tool.args).map(([k, v]) => `- ${k}: ${JSON.stringify(v)}`).join("\n");
            const toolOutput = `Tool: ${id}\nAgent: ${agent}\nAction: ${action}\nArguments:\n${args}\n`;
            this.addDebug(toolOutput, llm_agent, tool.id);
        },

        addDebugResult(result) {
            const id = result.id.split("/")[1];
            const toolOutput = `Result: ${formatToolDebugResult(result.result)}`
            this.addDebug(toolOutput, `Result ${id}`, result.id);
        },

        syncStructuredAgentDebugMessages(agentMessages) {
            for (const agentMessage of agentMessages) {
                const formattedText = formatAgentDebugText(agentMessage);
                if (!formattedText || formattedText === (agentMessage?.content ?? "")) continue;
                this.setDebug(formattedText, agentMessage.agent, agentMessage.id);
            }
        },

        addDebug(text, type, id=null) {
            const debug = this.$refs.sidebar.$refs.debug;
            debug.addDebugMessage(text, type, id);
            const aiBubble = this.getLastBubble();
            aiBubble?.addDebugMessage(text, type, id);
        },

        setDebug(text, type, id=null) {
            const debug = this.$refs.sidebar.$refs.debug;
            debug.setDebugMessage(text, type, id);
            const aiBubble = this.getLastBubble();
            aiBubble?.setDebugMessage(text, type, id);
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

        async loadHistory(chatId, switchChat = true) {
            if (!chatId || (!switchChat && this.selectedChatId !== chatId)) return;
            try {
                const chat = await backendClient.history(chatId);
                const debug = this.$refs.sidebar.$refs.debug;

                // clear messages
                this.messages = [];
                debug.clearDebugMessages();

                // add messages from history
                const numResponses = chat.responses?.length ?? 0;
                for (const [index, msg] of chat.responses?.entries()) {
                    if (!msg) continue;

                    // request
                    if (msg.query) {
                        await this.addChatBubble(msg.query, true);
                        debug.addDebugMessage(msg.query, "user");
                    }

                    // response
                    const isLoading = !chat.is_finished && index === numResponses - 1;
                    await this.addChatBubble(msg.content, false, isLoading);
                    await nextTick();
                    const aiBubble = this.getLastBubble();

                    for (const agent_message of msg.agent_messages) {
                        const chunk = {
                            id: agent_message.id,
                            agent: agent_message.agent,
                            chunk: formatAgentDebugText(agent_message),
                            is_output: false,
                        };
                        this.addDebugToken(chunk);
                        for (const tool of agent_message.tools) {
                            this.addDebugTool(agent_message.agent, tool);
                            this.addDebugResult({id: tool.id, result: tool.result});
                        }
                        const metric = {
                            agent: agent_message.agent,
                            execution_time: agent_message.execution_time,
                            metrics: agent_message.response_metadata
                        };
                        aiBubble?.addMetric(metric)
                    }
                    if (msg.error) {
                        this.getLastBubble().setError(msg.error);
                    }
                }

                if (this.messages.length > 0) {
                    this.showExampleQuestions = false;
                    this.selectedChatId = chatId;
                    this.newChat = false;
                    if (switchChat) {
                        this.clearMissedChatResponse(chatId);
                    }
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
            if (this.showExampleQuestions) {
                Localizer.reloadSampleQuestions(category);
            }
        },

        async handleSelectChat(chatId) {
            await this.loadHistory(chatId);
            this.$refs.textInputRef.focus();
        },

        async handleOpenMissedChatResponse(chatId) {
            await this.loadHistory(chatId);
            this.$refs.textInputRef?.focus();
            this.clearMissedChatResponse(chatId);
        },

        handleVisibilityChange() {
            if (document.hidden) return;

            if (this.selectedChatId && this.isMainContentVisible()) {
                this.clearMissedChatResponse(this.selectedChatId);
            }
        },

        async handleDeleteChat(chatId) {
            await this.startNewChat();
            await backendClient.delete(chatId);
            await this.$refs.sidebar.updateChats();
        },

        async handleRenameChat(chatId, newName) {
            try {
                await backendClient.updateName(chatId, newName);
            } finally {
                await this.$refs.sidebar.updateChats();
            }
        },

        async handleDeleteAllChats() {
            await this.startNewChat();
            await backendClient.deleteAllChats();
            await this.$refs.sidebar.updateChats();
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
            this.$refs.textInputRef?.focus();
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

                await this.handleFiles(files);
            }
            // If no file found, let normal paste happen
        },

        openViewer(file) {
            this.viewerFile = file;
        },

        isChatFinished() {
            const currentChat = this.$refs.sidebar?.$refs.chats?.chats
                ?.find(chat => chat?.chat_id === this.selectedChatId);
            return currentChat?.is_finished || this.newChat;
        },

        hasPendingUploads() {
            return this.pendingFileOperations > 0
                || this.selectedFiles.some(file => file.isUploading);
        }
    },

    mounted() {
        this.startNewChat();
        this.updateScrollbarThumb();
        document.addEventListener('visibilitychange', this.handleVisibilityChange);
        window.addEventListener('focus', () => { this.windowIsFocused = true; });
        window.addEventListener('blur',  () => { this.windowIsFocused = false; });
        addListener("selectedCategory", (category) => this.handleSelectCategory(category));
    },
    beforeUnmount() {
        document.removeEventListener('visibilitychange', this.handleVisibilityChange);
        clearTabMissedChatResponse();
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

.input-area-button:disabled,
.input-area-button.disabled {
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
