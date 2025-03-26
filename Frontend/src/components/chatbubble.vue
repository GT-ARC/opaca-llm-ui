<template>

    <!-- user bubble -->
    <div v-if="this.isUser" :id="this.elementId"
         class="d-flex flex-row justify-content-end mb-4">

        <div class="chatbubble chatbubble-user ms-auto me-2 p-3 mb-2">
            <div v-html="this.content" />
        </div>
        <div class="chaticon">
            <img src="/src/assets/Icons/nutzer.png" alt="User">
        </div>
    </div>


    <!-- ai bubble -->
    <div v-else :id="this.elementId"
         class="d-flex flex-row justify-content-start mb-4 w-100">

        <!-- ai icon -->
        <div class="chaticon">
            <img src="/src/assets/Icons/ai.png" alt="AI">
        </div>

        <div class="chatbubble chatbubble-ai me-auto ms-2 p-3 mb-2"
             :style="this.glowStyle">

            <div class="d-flex justify-content-start">
                <!-- loading spinner -->
                <div v-show="this.isLoading">
                    <i class="fa fa-spin fa-circle-o-notch me-1" />
                </div>

                <!-- error indicator -->
                <div v-show="this.isError">
                    <i class="fa fa-exclamation-circle text-danger me-1" />
                </div>

                <!-- content, either status messages or actual response -->
                <div v-if="this.isLoading && this.statusMessages.size > 0" class="message-text mb-4" :class="{'text-danger': isError}">
                    <div v-for="[key, { text, mode }] in this.statusMessages.entries()" :key="key">
                        <div v-if="mode === 'normal'">{{ text }}</div>
                        <div v-if="mode === 'pending'">{{ text }} ...</div>
                        <div v-if="mode === 'done'">{{ text }} ✓</div>
                    </div>
                </div>
                <div v-else class="message-text" :class="{'text-danger': isError}"
                     v-html="this.getFormattedContent()"
                />

            </div>

            <!-- footer: debug, generate audio, ... -->
            <div class="d-flex justify-content-start small">
                <div v-show="!this.isLoading && this.debugMessages.length > 0"
                     class="footer-item w-auto me-2"
                     style="cursor: pointer;"
                     @click="this.isDebugExpanded = !this.isDebugExpanded"
                     data-toggle="tooltip" data-placement="down" title="Toggle Debug">
                    <i class="fa fa-bug" />
                </div>
                <div v-show="!this.isLoading"
                     class="footer-item w-auto me-2"
                     style="cursor: pointer;"
                     @click="this.startAudioPlayback()">
                    <i v-if="this.isAudioLoading" class="fa fa-spin fa-spinner"
                       data-toggle="tooltip" data-placement="down" title="Audio is loading..." />
                    <i v-else-if="this.isAudioPlaying" class="fa fa-stop"
                       data-toggle="tooltip" data-placement="down" title="Stop Audio" />
                    <i v-else class="fa fa-volume-up"
                       data-toggle="tooltip" data-placement="down" title="Play Audio" />
                </div>
            </div>

            <!-- footer: debug messages -->
            <div v-show="this.isDebugExpanded">
                <div class="bubble-debug-text overflow-y-auto p-2 rounded-2   " style="max-height: 200px">
                    <div v-for="{ text, options } in this.debugMessages"
                         :style="{ color: (options && options.color) ? options.color : null }">
                        <div>{{ text }}</div>
                    </div>
                </div>
            </div>

        </div>
    </div>
</template>

<script>
import {marked} from "marked";
import conf from "../../config.js";

export default {
    name: 'chatbubble',
    props: {
        elementId: String,
        isUser: Boolean,
        isVoiceServerConnected: Boolean,
        isDarkScheme: Boolean,
        initialContent: String,
        initialLoading: Boolean,
    },
    data() {
        return {
            content: this.initialContent ?? '',
            statusMessages: new Map(),
            debugMessages: [],
            isDebugExpanded: false,
            isLoading: this.initialLoading ?? false,
            isError: false,
            ttsAudio: null,
            isAudioLoading: false,
            isAudioPlaying: false,
            glowColor: '#00ff00'
        }
    },

    methods: {
        getElement() {
            return document.getElementById(this.elementId);
        },

        /**
         * @param agent {string} Name of the agent that caused this status message.
         * @param text {string} Status message text content.
         * @param mode {string} Any of 'normal', 'pending' or 'done'.
         * @param options {Object}
         */
        addStatusMessage(agent, text, mode = 'normal', options = null) {
            if (!text || !text.trim()) return;
            text = text.trim();
            const message = this.statusMessages.get(agent);
            if (message) {
                message.text = text;
                message.mode = mode;
                message.options = options;
            } else {
                // new message -> mark previous steps done
                this.markStatusMessagesDone();
                this.statusMessages.set(agent, {text: text, mode: mode, options: options});
            }

            // update glow animation color
            if (options && options.color) {
                this.glowColor = options.color;
            }
        },

        /**
         * todo: better way to do this, that doesnt copy the copy the code from the sidebar debug messages?
         * @param text {string}
         * @param color {string}
         * @param type {string}
         */
        addDebugMessage(text, color, type) {
            if (!text) return;
            const message = {text: text, type: type, options: {color: color}};

            // if there are no messages yet, just push the new one
            if (this.debugMessages.length === 0) {
                this.debugMessages.push(message);
                return;
            }

            const lastMessage = this.debugMessages[this.debugMessages.length - 1];
            if (lastMessage.type === type && type === 'Tool Generator-Tools') {
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
         * mark all pending status messages done
         */
        markStatusMessagesDone() {
            Array.from(this.statusMessages.values())
                .filter(msg => msg.mode === 'pending')
                .forEach(msg => msg.mode = 'done');
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

        toggleError(value = null) {
            this.isError = value !== null
                ? value : !this.isError;
        },

        /**
         * generate new audio for this message using the whisper voice server
         */
        async generateAudio(voice = 'alloy') {
            if (!this.content) return;
            if (!this.isVoiceServerConnected) {
                console.warn('voice server not connected');
                return;
            }
            this.isAudioLoading = true;

            try {
                const url = `${conf.VoiceServerAddress}/generate_audio`;
                const payload = { method: 'POST' };
                const params = new URLSearchParams({
                    text: this.content,
                    voice: voice
                });

                const response = await fetch(`${url}?${params}`, payload);
                if (response.ok) {
                    const audioBlob = await response.blob();
                    const audioUrl = URL.createObjectURL(audioBlob);
                    this.ttsAudio = new Audio(audioUrl);
                    this.ttsAudio.onplay = () => this.isAudioPlaying = true;
                    this.ttsAudio.onpause = () => this.isAudioPlaying = false;
                    this.ttsAudio.onend = () => this.isAudioPlaying = false;
                    this.ttsAudio.play();
                } else {
                    const errorText = await response.text();
                    console.error('Audio API error:', response.status, errorText);
                }
            } catch (error) {
                console.error(error);
                alert('Failed to generate audio.');
                this.ttsAudio = null;
                this.isAudioPlaying = false;
            } finally {
                this.isAudioLoading = false;
            }
        },

        startAudioPlayback() {
            console.log('startAudioPlayback', this.canPlayAudio());
            if (!this.canPlayAudio()) return;
            if (this.isAudioPlaying) {
                this.stopAudioPlayback();
            } else if (this.ttsAudio) {
                this.ttsAudio.play();
            } else {
                this.generateAudio();
            }
        },

        stopAudioPlayback() {
            if (!this.ttsAudio) return;
            this.ttsAudio.pause();
            this.ttsAudio.currentTime = 0;
        },

        canPlayAudio() {
            return this.isVoiceServerConnected && !this.isUser
                && this.content && !this.isLoading && !this.isAudioLoading;
        },

        clearStatusMessages() {
            this.statusMessages = new Map();
        },

        clearDebugMessages() {
            this.debugMessages = [];
        },

        glowStyle() {
            return this.isLoading
                    ? { animation: `glowEffect 1.5s infinite alternate`,
                        '--glow-color': this.glowColor }
                    : { animation: 'none' };
        },

        clear() {
            this.content = '';
            this.statusMessages = [];
            this.debugMessages = [];
            this.isDebugExpanded = false;
            this.isLoading = false;
            this.isError = false;
            this.ttsAudio = null;
            this.isAudioPlaying = false;
            this.isAudioLoading = false;
        }
    },
}
</script>

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
    background-color: white;
    border-radius: 50%;
    border: 1px solid var(--border-light);
    aspect-ratio: 1 / 1;
}

.chaticon img {
    width: 100%;
    height: 100%;
    object-fit: contain;
}

.footer-item {
    color: var(--text-secondary-light);
}

.footer-item:hover {
    color: var(--primary-light);
}

.glowing {
    animation: glow 1.5s infinite alternate;
}

@keyframes glow {
    from {
        box-shadow: 0 0 5px rgba(0, 255, 0, 0.25);
    }
    to {
        box-shadow: 0 0 20px rgba(0, 255, 0, 0.5);
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
        background-color: var(--surface-dark);
        color: var(--text-secondary-dark);
    }

    .chatbubble {
        background: var(--chat-ai-dark);
        color: var(--text-primary-dark);
    }

    .chaticon {
        background: var(--chat-ai-dark);
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