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

        <div>
            <div class="chatbubble chatbubble-ai me-auto ms-2 p-3 mb-2">
                <div class="d-flex justify-content-start">
                    <!-- loading spinner -->
                    <div id="loadingContainer">
                        <div v-show="this.isLoading" class="loader"></div>
                    </div>

                    <!-- content, either status messages or actual response -->
                    <div class="message-text">
                        <div v-if="this.isLoading">
                            <div v-for="{ content, mode } in this.statusMessages" :key="content">
                                <div v-if="mode === 'normal'">{{ content }}</div>
                                <div v-if="mode === 'pending'">{{ content }}...</div>
                                <div v-if="mode === 'done'">{{ content }}✓</div>
                            </div>
                        </div>
                        <div v-else>
                            <div v-html="this.getFormattedContent()" />
                        </div>
                    </div>

                </div>

                <!-- footer: debug messages, generate audio, ... -->
                <div class="row ps-2">
                    <div class="debug-toggle w-auto me-2"
                         style="cursor: pointer; font-size: 10px"
                         @click="this.isDebugExpanded = !this.isDebugExpanded">
                        <img src="/src/assets/Icons/double_down_icon.png"
                             alt=">>" height="10px" width="10px"
                             class="m-0 p-0 w-auto"
                             :style="this.isDebugExpanded ? 'transform: rotate(180deg)' : ''"
                        />
                        Debug
                    </div>
                    <div class="debug-toggle w-auto" style="cursor: pointer; font-size: 10px;">
                        <i v-if="!this.isAudioPlaying" class="fa fa-volume-up" />
                        <i v-else class="fa fa-spin fa-spinner" />
                        Generate Audio (todo)
                    </div>
                </div>
                <div v-show="this.isDebugExpanded">
                    <hr class="debug-separator">
                    <div class="bubble-debug-text">
                        <div v-for="{ content, mode } in this.debugMessages">
                            <div v-if="mode === 'normal'">{{ content }}</div>
                            <div v-if="mode === 'pending'">{{ content }}...</div>
                            <div v-if="mode === 'done'">{{ content }}✓</div>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    </div>`
</template>

<script>
import { marked } from "marked";
import { getDebugColor } from '../config/debug-colors.js';
import conf from "../../config.js";

export default {
    name: 'chatbubble',
    props: {
        elementId: String,
        isUser: Boolean,
        isVoiceServerConnected: Boolean,
        isDarkScheme: Boolean,
        initialContent: String,
    },
    data() {
        return {
            content: this.initialContent ?? '',
            statusMessages: [],
            debugMessages: [],
            isDebugExpanded: false,
            isLoading: false,
            isAudioPlaying: false,
        }
    },

    methods: {
        getElement() {
            return document.getElementById(this.elementId);
        },

        addStatusMessage(text, mode = 'normal', options = null) {
            text = text.trim();
            if (!text) return;
            if (mode !== 'normal') {
                this.markStatusMessagesDone();
            }
            const msg = {content: text, mode: mode, options: options};
            this.statusMessages.push(msg);
            this.debugMessages.push(msg);
        },

        markStatusMessagesDone() {
            this.statusMessages
                .filter(msg => msg.mode === 'pending')
                .forEach(msg => msg.mode = 'done');
        },

        getFormattedContent() {
            try {
                const ft = marked.parse(this.content);
                console.log(ft)
                return ft;
            } catch (e) {
                console.error('Failed to parse chat bubble content:', e);
                return this.content;
            }
        },

        setContent(newContent) {
            this.content = newContent;
        },

        toggleLoading(value = null) {
            this.isLoading = value !== null
                ? value : !this.isLoading;
        },

        clear() {
            this.content = '';
            this.statusMessages = [];
            this.debugMessages = [];
            this.isDebugExpanded = false;
            this.isLoading = false;
        }
    },
    onmounted() {
        this.isLoading = true;
    }
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

.debug-toggle img {
    filter: invert(100%);
}

@media (prefers-color-scheme: dark) {
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

    .chatbubble {
        background: var(--chat-ai-dark);
        color: var(--text-primary-dark);
    }
}

</style>