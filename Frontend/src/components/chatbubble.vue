<template>
<div :class="{'chatbubble-collapsible': this.isCollapsible}"
     @click.stop="this.toggleCollapsed()">

    <!-- user bubble -->
    <div v-if="this.isUser" :id="this.elementId"
         class="d-flex flex-row justify-content-end" >

        <div class="chatbubble chatbubble-user ms-auto w-auto">
            <div v-html="this.getFormattedContent()" />

            <!-- footer: debug, generate audio, ... -->
            <div class="d-flex justify-content-start small mt-2">

                <!-- copy to clipboard -->
                <div v-show="this.isCopyAvailable()"
                     class="footer-item w-auto me-2"
                     @click="this.copyContentToClipboard()"
                     :title="Localizer.get('tooltipChatbubbleCopy')">
                    <i v-if="this.copySuccess" class="fa fa-check" />
                    <i v-else class="fa fa-copy" />
                </div>

                <!-- save prompt to user library -->
                <div v-show="this.content?.length > 0"
                     class="footer-item w-auto me-2"
                     :class="{ 'disabled': bookmarked }"
                     @click="this.addPromptToUserLibrary()"
                     :title="Localizer.get('tooltipChatbubbleSave')">
                    <i v-if="this.bookmarked" class="fa-solid fa-bookmark" />
                    <i v-else class="fa-regular fa-bookmark" />
                </div>

                <!-- audio stuff -->
                <div v-show="!this.isLoading"
                     class="footer-item w-auto me-2"
                     @click="this.startAudioPlayback()">
                    <i v-if="this.isAudioLoading()" class="fa fa-spin fa-spinner"
                       data-toggle="tooltip" data-placement="down"
                       :title="Localizer.get('tooltipChatbubbleAudioLoad')" />
                    <i v-else-if="this.isAudioPlaying()" class="fa fa-stop-circle"
                       data-toggle="tooltip" data-placement="down"
                       :title="Localizer.get('tooltipChatbubbleAudioStop')" />
                    <i v-else class="fa fa-volume-up"
                       data-toggle="tooltip" data-placement="down"
                       :title="Localizer.get('tooltipChatbubbleAudioPlay')" />
                </div>

                <!-- attached files -->
                <div v-show="this.files?.length > 0"
                     class="footer-item w-auto me-2"
                     @click="this.isFilesExpanded = !this.isFilesExpanded"
                     :title="Localizer.get('tooltipChatbubbleFiles')">
                    <i class="fa fa-file-pdf" />
                </div>

            </div>

            <!-- footer: attached files -->
            <div v-show="this.isFilesExpanded">
                <div class="bubble-debug-text overflow-y-auto p-2 mt-1 rounded-2"
                     style="max-height: 200px; max-width: 600px;">
                    <div class="message-text w-auto"
                         v-for="file in this.files">
                        {{ file }}
                    </div>
                </div>
            </div>

        </div>
    </div>


    <!-- ai bubble -->
    <div v-else :id="this.elementId"
         class="d-flex flex-row justify-content-start w-100">

        <div class="chatbubble chatbubble-ai"
             :class="{glow: this.isLoading}" :style="this.getGlowColors()" >

            <div class="d-flex justify-content-start"
                 :class="{'chatbubble-collapsed': this.isCollapsed}">

                <div v-if="this.isCollapsed" class="chatbubble-collapsed-overlay">
                    <i class="fa fa-arrow-alt-circle-down" />
                </div>

                <!-- loading spinner -->
                <div v-show="this.isLoading" class="w-auto">
                    <i class="fa fa-spin fa-circle-o-notch me-1" />
                </div>

                <!-- content, either status messages or actual response -->
                <div v-if="this.isLoading && this.statusMessages.size > 0" class="message-text w-auto mb-4">
                    <div v-for="[agentName, { text, completed }] in this.statusMessages.entries()" :key="agentName">
                        <div v-if="completed">{{ text }} ✓</div>
                        <div v-else>{{ text }} ...</div>
                    </div>
                    <div v-if="this.getToolCalls().length > 0">
                        <hr />
                        <div v-if="this.getToolCalls().length > 3">
                            ...
                        </div>
                        <div v-for="text in this.getToolCalls().slice(-3)">
                            <i class="fa fa-wrench" /> {{ text }}
                        </div>
                    </div>
                </div>
                <div v-else class="message-text w-auto"
                     v-html="this.getFormattedContent()"
                />

            </div>

            <!-- footer: icons -->
            <div v-if="!this.isCollapsed && !this.isCollapsed"
                 class="d-flex justify-content-start small mt-2">

                <!-- copy to clipboard -->
                <div v-show="this.isCopyAvailable()"
                     class="footer-item w-auto me-2"
                     @click.stop="this.copyContentToClipboard()"
                     :title="Localizer.get('tooltipChatbubbleCopy')">
                    <i v-if="this.copySuccess" class="fa fa-check" />
                    <i v-else class="fa fa-copy" />
                </div>

                <!-- audio stuff -->
                <div v-show="!this.isLoading"
                     class="footer-item w-auto me-2"
                     @click.stop="this.startAudioPlayback()">
                    <i v-if="this.isAudioLoading()" class="fa fa-spin fa-spinner"
                       data-toggle="tooltip" data-placement="down"
                       :title="Localizer.get('tooltipChatbubbleAudioLoad')" />
                    <i v-else-if="this.isAudioPlaying()" class="fa fa-stop-circle"
                       data-toggle="tooltip" data-placement="down"
                       :title="Localizer.get('tooltipChatbubbleAudioStop')" />
                    <i v-else class="fa fa-volume-up"
                       data-toggle="tooltip" data-placement="down"
                       :title="Localizer.get('tooltipChatbubbleAudioPlay')" />
                </div>

                <!-- debug messages -->
                <div v-show="this.debugMessages.length > 0"
                     class="footer-item w-auto me-2"
                     @click.stop="this.isDebugExpanded = !this.isDebugExpanded"
                     :title="Localizer.get('tooltipChatbubbleDebug')">
                    <i class="fa fa-bug" />
                </div>

                <!-- tool calls -->
                <div v-show="this.getToolCalls().length > 0"
                     class="footer-item w-auto me-2"
                     style="cursor: pointer;"
                     @click.stop="this.isToolsExpanded = !this.isToolsExpanded"
                     :title="Localizer.get('tooltipChatbubbleTools')">
                    <i class="fa fa-wrench" />
                </div>

                <!-- error handling -->
                <div v-show="this.error !== null"
                     class="footer-item w-auto me-2"
                     @click.stop="this.isErrorExpanded = !this.isErrorExpanded"
                     :title="Localizer.get('tooltipChatbubbleError')">
                    <i class="fa fa-exclamation-circle text-danger me-1" />
                </div>

            </div>

            <!-- footer: debug messages -->
            <div v-show="this.isDebugExpanded && !this.isCollapsed">
                <div class="bubble-debug-text overflow-y-auto p-2 mt-1 rounded-2" :id="'debug-message-' + this.elementId"
                     style="max-height: 200px"
                     @scroll="handleDebugScroll">
                    <DebugMessage v-for="{ text, type } in this.debugMessages"
                        :text="text"
                        :type="type"
                    />
                </div>
            </div>

            <!-- footer: tool calls -->
            <div v-show="this.isToolsExpanded && !this.isCollapsed">
                <div class="bubble-debug-text overflow-y-auto p-2 mt-1 rounded-2"
                     style="max-height: 200px">
                     <div v-for="text in this.getToolCalls()">
                        {{ text }}
                     </div>
                </div>
            </div>

            <!-- footer: errors -->
            <div v-show="this.isErrorExpanded && !this.isCollapsed">
                <div class="bubble-debug-text overflow-y-auto p-2 mt-1 rounded-2"
                     style="max-height: 200px">
                    <div class="message-text w-auto text-danger"
                         v-html="this.error"
                    />
                </div>
            </div>

        </div>
    </div>
</div>
</template>

<script>
import * as utils from "../utils.js"
import {marked} from "marked";
import DOMPurify from "dompurify";
import conf from "../../config.js";
import {getDebugColor} from "../config/debug-colors.js";
import DebugMessage from "./DebugMessage.vue";
import {useDevice} from "../useIsMobile.js";
import Localizer from "../Localizer.js";
import AudioManager from "../AudioManager.js";
import {isDarkTheme} from "../ColorThemes.js";

export default {
    name: 'chatbubble',
    components: {DebugMessage},
    props: {
        elementId: String,
        isUser: Boolean,
        initialContent: String,
        initialLoading: Boolean,
        files: Array,
        selectedChatId: String,
        isBookmarked: Boolean,
        isCollapsible: {type: Boolean, default: false},
    },
    setup() {
        const { isMobile, screenWidth } = useDevice();
        return { conf, Localizer, AudioManager, isMobile, screenWidth };
    },
    data() {
        return {
            content: this.initialContent ?? '',
            statusMessages: new Map(),
            debugMessages: [],
            isDebugExpanded: false,
            isLoading: this.initialLoading ?? false,
            error: null,
            isErrorExpanded: false,
            ttsAudio: null,
            copySuccess: false,
            bookmarked: this.isBookmarked ?? false,
            autoScrollDebugMessage: true,
            isFilesExpanded: false,
            isToolsExpanded: false,
            isCollapsed: false,
        }
    },

    methods: {
        /**
         * @returns {HTMLElement}
         */
        getElement() {
            return document.getElementById(this.elementId);
        },

        /**
         * @param agentName {string} Name of the agent that caused this status message.
         * @param text {string} Status message text content.
         * @param completed {boolean} Flag to indicate if the task is done.
         */
        addStatusMessage(agentName, text, completed = false) {
            if (!text || !text.trim()) return;
            text = text.trim();
            const message = this.statusMessages.get(agentName);
            if (message) {
                message.text = text;
                message.completed = completed;
            } else {
                // new message -> mark previous steps done
                this.markStatusMessagesDone(agentName);
                this.statusMessages.set(agentName, {text: text, completed: completed});
            }
        },

        getToolCalls() {
            const regex = /^Tool: (\d+)\nAgent: ([^\n]+)\nAction: ([^\n]+)\nArguments:((?:\n- [^\n]+)*)\n+(?:Result: (.+))?$/gs
            return this.debugMessages
                .flatMap( debug => [...debug.text.matchAll(regex)] )
                .map( match => {
                    const id = match[1];
                    const agent = match[2];
                    const action = match[3];
                    const params = match[4].replace("\n- ", " ");
                    var results = match[5];
                    if (results != null && results.length > 30) results = results.substring(0, 30) + " [...]";
                    return `${id}. ${agent}: ${action}(${params}) → ${results}`;
                });
        },

        addDebugMessage(text, type, id=null) {
            const message = {id: id, text: text, type: type, chatId: this.selectedChatId};
            utils.addDebugMessage(this.debugMessages, message);
        },

        scrollDownDebugMsg() {
            if (!this.autoScrollDebugMessage) return;
            const debugId = `debug-message-${this.elementId}`;
            const debug = document.getElementById(debugId);
            if (debug) {
                debug.scrollTop = debug.scrollHeight;
            }
        },

        handleDebugScroll() {
            // Disable autoscroll for debug message if user scrolled up
            const debugMsg = document.getElementById(`debug-message-${this.elementId}`);
            this.autoScrollDebugMessage = debugMsg.scrollTop + debugMsg.clientHeight >= debugMsg.scrollHeight - 10;
        },

        /**
         * Go over the status messages map and mark all pending ones done
         * up to, but not including, the provided "stopKey".
         */
        markStatusMessagesDone(stopKey = null) {
            const messages = Array.from(this.statusMessages.entries());
            for (let i = 0; i < messages.length; ++i) {
                const [key, msg] = messages[i];
                if (key === stopKey) break;
                msg.completed = true;
            }
        },

        getFormattedContent() {
            try {
                const rawHtml = marked.parse(this.content);

                // Load into a temporary DOM element
                const div = document.createElement('div');
                div.innerHTML = rawHtml;

                // Make sure links open in new tab
                div.querySelectorAll('a').forEach(link => {
                    link.setAttribute('target', '_blank');
                    link.setAttribute('rel', 'noopener noreferrer');
                });

                // Sanitize html
                return DOMPurify.sanitize(div.innerHTML, {
                    // Keep attributes we set
                    ADD_ATTR: ['target', 'rel'],
                });
            } catch (error) {
                console.error('Failed to parse chat bubble content:', this.content, error);
                return this.content;
            }
        },

        setContent(newContent) {
            this.content = newContent;
        },

        addContent(newContent) {
            this.content += newContent;
        },

        toggleLoading(value = null) {
            this.isLoading = value !== null
                ? value : !this.isLoading;
        },

        setError(value = null) {
            this.error = value;
        },

        getGlowColors() {
            const agentName = this.debugMessages.at(-1)?.type;
            const isDarkMode = isDarkTheme();
            const baseColor = agentName
                ? getDebugColor(agentName, isDarkMode)
                : null;
            if (!baseColor) return null;
            return {
                '--glow-color-1': baseColor ? `${baseColor}40` : '#00ff0040',
                '--glow-color-2': baseColor ? `${baseColor}90` : '#00ff0090',
            };
        },

        copyContentToClipboard() {
            if (this.content.length <= 0 || this.copySuccess) return;
            navigator.clipboard.writeText(this.content)
                .then(() => {
                    this.copySuccess = true;
                    setTimeout(() => this.copySuccess = false, 2000);
                })
                .catch(error => console.error('Failed to copy text: ', error));
        },

        addPromptToUserLibrary() {
            const prompt = this.content;
            if (prompt.length <= 0 || this.bookmarked) return;
            this.$emit('add-to-library', prompt);
            this.bookmarked = true;
        },

        /**
         * Generate new audio for this message.
         */
        async generateAudio() {
            if (!this.content) return;
            this.ttsAudio = await AudioManager.generateAudio(this.content);
            await this.ttsAudio.setup().then(() => {
                this.ttsAudio.play();
            });
        },

        startAudioPlayback() {
            if (!this.canPlayAudio()) return;
            if (this.isAudioPlaying()) {
                this.stopAudioPlayback();
            } else if (this.ttsAudio) {
                this.ttsAudio.play();
            } else {
                this.generateAudio();
            }
        },

        stopAudioPlayback() {
            if (this.ttsAudio) {
                this.ttsAudio.stop();
            }
        },

        canPlayAudio() {
            return this.content && !this.isLoading
                && !this.isAudioLoading();
        },

        isAudioPlaying() {
            return this.ttsAudio && this.ttsAudio.isPlaying;
        },

        isAudioLoading() {
            return this.ttsAudio && this.ttsAudio.isLoading;
        },

        isCopyAvailable() {
            return this.content.length > 0 && (!this.isMobile
                || window.location.protocol === 'https'
                || window.location.hostname === 'localhost');
        },

        toggleCollapsed(value = null) {
            if (!this.isCollapsible) return;
            this.isCollapsed = value === null
                ? !this.isCollapsed
                : value;
        },
    },

    mounted() {
        if (!this.isLoading && this.isCollapsible) {
            this.isCollapsed = true;
        }
    },

    updated() {
        this.scrollDownDebugMsg();
    },

    watch: {
        isLoading(newVal) {
            if (!newVal && !this.isCollapsible) {
                this.toggleCollapsed(true);
            }
        }
    },

}
</script>

<style>
.message-text img {
    max-width: 100%;
    display: block;
}

.chatbubble p:last-of-type {
    margin-bottom: 0 !important;
}
</style>

<style scoped>
.chatbubble {
    color: var(--text-primary-color);
    border-radius: 1.25rem;
    text-align: left;
    position: relative;
    transition: all 0.2s ease;
    width: fit-content;
    margin-bottom: 1rem;
}

.chatbubble-user {
    background-color: var(--chat-user-color);
    margin-left: auto;
    margin-right: 1rem;
    padding: 0.75rem 1.25rem;
    width: auto !important; /* Override any width constraints */
    word-wrap: break-word;
    overflow-wrap: anywhere;
    max-width: 80ch;
}

.chatbubble-ai {
    background-color: var(--chat-ai-color);
    width: 100%;
    will-change: box-shadow;
    transition: box-shadow 0.2s ease;
    padding: 0.5rem;
}

.message-text {
    flex: 1;
    min-width: 0;
    padding-right: 0.5rem;
    white-space: normal;
    gap: 1rem;
}

.footer-item {
    color: var(--text-secondary-color);
    font-weight: bold;
    cursor: pointer;
}

.footer-item:hover {
    color: var(--primary-color);
}

.footer-item.disabled {
    cursor: not-allowed;
    pointer-events: none;
}

.bubble-debug-text {
    background-color: var(--debug-console-color);
    color: var(--text-secondary-color);
}

.glow {
    --glow-color-1: #00ff0040;
    --glow-color-2: #00ff0090;
    box-shadow: 0 0 8px #00ff0040;
    animation: glow 3s infinite;
}

.chatbubble-collapsible {
    cursor: pointer;
}

.chatbubble-collapsed {
    min-height: 40px !important;
    max-height: 60px !important;
    overflow: hidden;
}

.chatbubble-collapsed-overlay {
    height: 30px;
    z-index: 2;
    left: 0;
    bottom: 0;
    position: absolute;
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    border-bottom-left-radius: 1.25rem;
    border-bottom-right-radius: 1.25rem;
    background-color: rgba(128, 128, 128, 0.4);
    backdrop-filter: blur(2px);
}

@keyframes glow {
    0%, 100% {
        box-shadow: 0 0 12px var(--glow-color-1, #00ff0040);
    }
    50% {
        box-shadow: 0 0 15px var(--glow-color-2, #00ff0090);
    }
}

@media screen and (max-width: 768px) {
    .chatbubble-user {
        margin-right: 0;
    }

    .chatbubble-ai {
        margin-left: 0;
    }
}

</style>