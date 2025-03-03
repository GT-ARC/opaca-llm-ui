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
         class="d-flex flex-row justify-content-start mb-4">

        <!-- ai icon -->
        <div class="chaticon">
            <img src="/src/assets/Icons/ai.png" alt="AI">
        </div>

        <div class="chat-content">
            <div id="chatBubble" class="p-3 small mb-2 chatbubble chatbubble-ai">
                <div class="d-flex flex-row justify-content-start message-content">
                    <!-- loading spinner -->
                    <div id="loadingContainer">
                        <div v-if="this.isLoading()" class="loader"></div>
                    </div>

                    <!-- content -->
                    <div id="messageContainer" class="message-text">
                        <div v-if="this.isStatusMessage()">
                            <div v-for="line in this.getFormattedContent()" :key="line">
                                {{ line }}
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
                <hr id="${debugId}-separator"
                    v-show="this.isDebugExpanded"
                    class="debug-separator">
                <div id="${debugId}-text"
                     v-show="this.isDebugExpanded"
                     class="bubble-debug-text"/>

            </div>
        </div>
    </div>`
</template>

<script>
import { marked } from "marked";
import {debugColors, defaultDebugColors, debugLoadingMessages} from '../config/debug-colors.js';

export default {
    name: 'chatbubble',
    props: {
        elementId: String,
        isUser: Boolean,
        isVoiceServerConnected: Boolean,
        isDarkScheme: Boolean,
    },
    data() {
        return {
            content: '',
            debugMessages: [],
            isDebugExpanded: false,
        }
    },
    methods: {
        addDebugMsg(text, options = null) {
            // todo
        },
        getFormattedContent() {
            if (this.isStatusMessage()) {
                return this.content.split('\n')
                    .map(line => line.trim())
                    .filter(line => !!line);
            } else {
                return marked.parse(this.content);
            }
        },
        setContent(newContent) {
            this.content = newContent;
        },
        getDebugColor(colorKey) {
            return (debugColors[colorKey] ?? defaultDebugColors)[this.isDarkScheme ? 1 : 0];
        },
        isLoading() {
            return this.content.includes('...');
        },
        isStatusMessage() {
            return this.isLoading() || this.content.includes('✓');
        },
    },
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