<template>

    <!-- user bubble -->
    <div v-if="this.isUser" :id="this.elementId"
         class="d-flex flex-row justify-content-end mb-4">

        <div class="chatbubble chatbubble-user">
            {{ this.content }}
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

        <div class="chat-content">
            <div id="chatBubble" class="p-3 small mb-2 chatbubble chatbubble-ai">
                <div class="d-flex flex-row justify-content-start message-content">
                    <!-- loading spinner -->
                    <div id="loadingContainer">
                        <div v-show="this.isLoading" class="loader"></div>
                    </div>

                    <!-- content, either status messages or actual response -->
                    <div id="messageContainer" class="message-text">
                        <div v-if="this.isLoading">
                            <div v-for="{ content, mode } in this.statusMessages" :key="line">
                                <div v-if="mode === 'normal'">{{ content }}</div>
                                <div v-if="mode === 'pending'">{{ content }}...</div>
                                <div v-if="mode === 'done'">{{ content }}✓</div>
                            </div>
                        </div>
                        <div v-else>
                            {{ this.getFormattedContent() }}
                        </div>
                    </div>

                </div>

                <!-- footer: debug messages, generate audio, ... -->
                <div class="debug-toggle w-auto"
                     style="cursor: pointer; font-size: 10px;"
                     @click="this.isDebugExpanded = !this.isDebugExpanded">
                    <img src=/src/assets/Icons/double_down_icon.png
                         class="double-down-icon"
                         alt=">>" width="10px" height="10px"
                         :style="this.isDebugExpanded ? 'transform: rotate(180deg)' : ''"/>
                    debug
                </div>
                <div class="debug-toggle w-auto" style="cursor: pointer; font-size: 10px;">
                    <i class="fa fa-volume-up" />
                    Generate Audio (todo)
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
                return marked.parse(this.content);
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

.chatbubble-user {
    background-color: var(--chat-user-light);
    margin-left: auto;
    margin-right: 1rem;
    padding: 0.75rem 1.25rem;
    width: auto !important; /* Override any width constraints */
}

.chatbubble-ai {
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

</style>