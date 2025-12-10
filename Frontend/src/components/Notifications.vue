<template>
    <div class="notifications-container overflow-auto" @click.stop>
        <div v-if="! this.messages || this.messages.length <= 0" class="p-3 fs-5 text-center text-secondary w-100">
            {{Localizer.get('noNotifsAvailable')}}
        </div>

        <div v-for="{ elementId, fullResponse, loading, content, time } in this.messages">
            <div class="d-flex align-items-center justify-content-between px-1">
                <span>{{ time }}</span>
                <!-- grouped buttons -->
                <div class="d-flex gap-1">
                    <i v-if="loading" class="fa fa-stop notification-button"
                        @click.stop="this.stopNotifications()"
                        title="Stop"
                    />
                    <i v-if="! loading" class="fa fa-comment-medical notification-button"
                       @click.stop="this.appendToChat(fullResponse)"
                       :title="Localizer.get('tooltipAppendNotification')"
                    />
                    <i v-if="! loading"class="fa fa-remove notification-button"
                        @click.stop="this.dismissNotification(elementId)"
                        :title="Localizer.get('tooltipDismissNotification')"
                    />
                </div>
            </div>
            <div class="px-2" :key="content">
                <Chatbubble
                    :element-id="elementId"
                    :is-user="false"
                    :initial-content="content"
                    :initial-loading="loading"
                    :is-bookmarked="false"
                    :files="[]"
                    :chat-id="''"
                    :ref="elementId"
                    :is-collapsible="true"
                />
            </div>
        </div>
    </div>
</template>

<script>
import Chatbubble from "./chatbubble.vue";
import conf from '../../config'
import Localizer from "../Localizer.js";
import { useDevice } from "../useIsMobile.js";
import backendClient from "../utils.js";

export default {
    name: 'notifications-area',
    components: {
        Chatbubble
    },
    props: {
    },
    emits: [
        "append-to-chat"
    ],
    setup() {
        const { isMobile, screenWidth } = useDevice()
        return { conf, Localizer, isMobile, screenWidth };
    },
    data() {
        return {
            messages: [],
            nextElementId: 0,
        }
    },
    methods: {

        async addPendingNotificationBubble(response) {
            const elementId = `chatbubble-${this.nextElementId++}`;
            const message = { 
                elementId: elementId,
                loading: true, 
                content: response.query, 
                time: new Date().toLocaleString(),
            };
            this.messages.unshift(message);
        },

        async addNotificationBubble(response) {
            // remove loading messages (also for other task if multiple in parallel...)
            this.messages = this.messages.filter(m => ! m.loading);

            const elementId = `chatbubble-${this.nextElementId++}`;

            const message = { 
                elementId: elementId, 
                fullResponse: response,
                loading: false,
                content: response.content, 
                time: new Date().toLocaleString(),
            };
            this.messages.unshift(message);

            // wait for the next rendering tick so that the component is mounted
            await nextTick();

            // add debug stuff to chat bubble
            const chatBubble = this.$refs[elementId][0];
            for (const msg of response.agent_messages) {
                chatBubble.addDebugMessage(msg.content, msg.agent, msg.id);
                for (const tool of msg.tools) {
                    // adapted from content.vue#addDebugTool
                    const id = tool.id.split("/")[1];
                    const [agent, action] = tool.name.split("--");
                    const args = Object.entries(tool.args).map(([k, v]) => `- ${k}: ${JSON.stringify(v)}`).join("\n");
                    const toolOutput = `Tool: ${id}\nAgent: ${agent}\nAction: ${action}\nArguments:\n${args}\nResult: ${JSON.stringify(tool.result)}`;
                    chatBubble.addDebugMessage(toolOutput, msg.agent, tool.id);
                }
            }
            if (response.error) {
                chatBubble.setError(response.error);
            }
        },

        async stopNotifications() {
            backendClient.stop();
            // there is no differentiation WHICH notification to stop, so this just removes all loading...
            this.messages = this.messages.filter(m => ! m.loading);
        },

        async dismissNotification(elementId) {
            this.messages = this.messages.filter(m => m.elementId !== elementId);
        },

        isBubbleCollapsed(elementId) {
            return this.$refs[elementId]?.[0]?.isCollapsed;
        },

        collapseBubble(elementId) {
            this.$refs[elementId]?.[0]?.toggleCollapsed();
        },

        async appendToChat(response) {
            this.$emit('append-to-chat', response);
        }
    },
}

</script>

<style scoped>
.notifications-container {
    max-height: 80vh;
    min-width: min(600px, 100vw - 9rem);
}

.notification-button {
    width: 2rem;
    height: 2rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 1rem !important;
    cursor: pointer;
}
</style>
