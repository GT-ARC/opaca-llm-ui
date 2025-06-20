<template>

    <!-- user bubble -->
    <div v-if="this.isUser" :id="this.elementId"
         class="d-flex flex-row justify-content-end mb-4">

        <div class="chatbubble chatbubble-user me-2 p-3 mb-2 w-auto ms-auto">
            <div v-html="this.content"></div>
        </div>
        <div class="chaticon">
            <img src="/src/assets/Icons/nutzer.png" alt="User">
        </div>
    </div>


    <!-- ai bubble -->
    <div v-else :id="this.elementId"
         class="d-flex flex-row justify-content-start mb-4 w-100">

        <!-- ai icon -->
        <div v-if="!isMobile" class="chaticon">
            <img src="/src/assets/Icons/ai.png" alt="AI">
        </div>

        <div class="chatbubble chatbubble-ai me-auto ms-2 p-3 mb-2"
             :class="{glow: this.isLoading}" :style="this.getGlowColors()">

            <div class="d-flex justify-content-start">
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
                </div>
                <div v-else class="message-text w-auto"
                     v-html="this.getFormattedContent()"
                />

            </div>

            <!-- footer: debug, generate audio, ... -->
            <div class="d-flex justify-content-start small">
                <div v-show="this.debugMessages.length > 0"
                     class="footer-item w-auto me-2"
                     style="cursor: pointer;"
                     @click="this.isDebugExpanded = !this.isDebugExpanded"
                     :title="Localizer.get('tooltipChatbubbleDebug')">
                    <i class="fa fa-bug" />
                </div>
                <div v-show="this.error !== null"
                     class="footer-item w-auto me-2"
                     style="cursor: pointer;"
                     @click="this.isErrorExpanded = !this.isErrorExpanded"
                     :title="Localizer.get('tooltipChatbubbleError')">
                    <i class="fa fa-exclamation-circle text-danger me-1" />
                </div>
                <div v-show="!this.isLoading"
                     class="footer-item w-auto me-2"
                     style="cursor: pointer;"
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
            </div>

            <!-- footer: debug messages -->
            <div v-show="this.isDebugExpanded">
                <div class="bubble-debug-text overflow-y-auto p-2 rounded-2"
                     style="max-height: 200px">
                    <DebugMessage v-for="{ text, type } in this.debugMessages"
                        :text="text"
                        :type="type"
                        :is-dark-scheme="this.isDarkScheme"
                    />
                </div>
            </div>

            <div v-show="this.isErrorExpanded">
                <div class="bubble-debug-text overflow-y-auto p-2 rounded-2"
                     style="max-height: 200px">
                    <div class="message-text w-auto text-danger"
                         v-html="this.error"
                    />
                </div>
            </div>

        </div>
    </div>
</template>

<script>
import {marked} from "marked";
import conf from "../../config.js";
import {getDebugColor} from "../config/debug-colors.js";
import DebugMessage from "./DebugMessage.vue";
import {useDevice} from "../useIsMobile.js";
import Localizer from "../Localizer.js";
import AudioManager from "../AudioManager.js";

export default {
    name: 'chatbubble',
    components: {DebugMessage},
    props: {
        elementId: String,
        isUser: Boolean,
        isDarkScheme: Boolean,
        initialContent: String,
        initialLoading: Boolean,
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
        }
    },

    methods: {
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

        /**
         * todo: better way to do this, that doesnt copy the copy the code from the sidebar debug messages?
         * @param text {string}
         * @param type {string}
         */
        addDebugMessage(text, type) {
            if (!text) return;
            const message = {text: text, type: type};

            // if there are no messages yet, just push the new one
            if (this.debugMessages.length === 0) {
                this.debugMessages.push(message);
                return;
            }

            const lastMessage = this.debugMessages[this.debugMessages.length - 1];
            if (lastMessage.type === type && type === 'Tool Generator') {
                // If the message includes tools, the message needs to be replaced instead of appended
                this.debugMessages[this.debugMessages.length - 1] = message;
            } else if (lastMessage.type === type) {
                // If the message has the same type as before but is not a tool, append the token to the text
                lastMessage.text += text;
            } else {
                // new message type
                this.debugMessages.push(message);
            }
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
                return marked.parse(this.content);
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
            const baseColor = agentName
                ? getDebugColor(agentName, this.isDarkScheme)
                : null;
            if (!baseColor) return null;
            return {
                '--glow-color-1': baseColor ? `${baseColor}40` : '#00ff0040',
                '--glow-color-2': baseColor ? `${baseColor}90` : '#00ff0090',
            };
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
            return !this.isUser && this.content && !this.isLoading
                && !this.isAudioLoading();
        },

        isAudioPlaying() {
            return this.ttsAudio && this.ttsAudio.isPlaying;
        },

        isAudioLoading() {
            return this.ttsAudio && this.ttsAudio.isLoading;
        },

        clearStatusMessages() {
            this.statusMessages = new Map();
        },

        clearDebugMessages() {
            this.debugMessages = [];
        },

        clear() {
            this.clearStatusMessages();
            this.clearDebugMessages();
            this.content = '';
            this.isDebugExpanded = false;
            this.isErrorExpanded = false;
            this.isLoading = false;
            this.error = null;
            this.ttsAudio = null;
        }
    },

}
</script>

<style>
.message-text img {
    max-width: 100%;
    display: block;
}
</style>

<style scoped>
.chatbubble {
    background-color: var(--chat-ai-light);
    border-radius: 1.25rem;
    text-align: left;
    position: relative;
    transition: all 0.2s ease;
    width: fit-content;
    max-width: 800px;
}

.chatbubble-user {
    margin-left: auto;
    margin-right: 1rem;
    padding: 0.75rem 1.25rem;
    width: auto !important; /* Override any width constraints */
    word-wrap: break-word;
    overflow-wrap: anywhere;
}

.chatbubble-ai {
    width: 100%;
    will-change: box-shadow;
    transition: box-shadow 0.3s ease;
}

.message-text {
    flex: 1;
    min-width: 0;
    padding-right: 0.5rem;
    white-space: normal;
    gap: 1rem;
}

.chaticon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.5rem;
    height: 2.5rem;
    background: var(--chat-ai-light);
    border-radius: 50%;
    border: 1px solid var(--border-light);
    padding: 0.5rem;
    aspect-ratio: 1 / 1;
}

.chaticon img {
    object-fit: contain;
    width: 100%;
    height: 100%;
}

.footer-item {
    color: var(--text-secondary-light);
}

.footer-item:hover {
    color: var(--primary-light);
}

.bubble-debug-text {
    background-color: var(--debug-console-light);
    color: var(--text-secondary-light);
}

.glow {
    --glow-color-1: #00ff0040;
    --glow-color-2: #00ff0090;
    box-shadow: 0 0 8px #00ff0040;
    animation: glow 3s infinite;
}

@keyframes glow {
    0%, 100% {
        box-shadow: 0 0 12px var(--glow-color-1, #00ff0040);
    }
    50% {
        box-shadow: 0 0 15px var(--glow-color-2, #00ff0090);
    }
}

@media (prefers-color-scheme: dark) {
    .footer-item {
        color: var(--text-secondary-dark);
    }

    .footer-item:hover {
        color: var(--text-primary-dark);
    }

    .bubble-debug-text {
        background-color: var(--debug-console-dark);
        color: var(--text-secondary-dark);
    }

    .chatbubble {
        background: var(--chat-ai-dark);
        color: var(--text-primary-dark);
    }

    .chaticon {
        background: var(--chat-ai-dark);
        border-color: var(--border-dark);
    }

    .chaticon img {
        filter: invert(100%);
    }

}

@media screen and (max-width: 768px) {
    .chatbubble-user {
        margin-right: 0;
    }

    .chatbubble-ai {
        margin-left: 0;
    }

    .chaticon {
        padding: 0.5rem;
        margin: 0 0.25rem;
    }
}

</style>