<template>
    <div class="notifications-container overflow-auto" @click.stop>
        <div v-if="! this.messages || this.messages.length <= 0" class="p-3 fs-5 text-center text-secondary">
            {{Localizer.get('noNotifsAvailable')}}
        </div>

        <div v-for="{ elementId, content, time } in this.messages">
            <div class="d-flex align-items-center px-1">
                <span>{{ time }}</span>
                <div class="ms-auto">
                    <i class="fa fa-remove delete-button"
                       @click.stop="this.dismissNotification(elementId)"
                       title="Dismiss"
                    />
                </div>
            </div>
            <div :key="content"
                 @click.stop="this.collapseBubble(elementId)"
                 style="cursor: pointer">
                <Chatbubble
                    :element-id="elementId"
                    :is-user="false"
                    :initial-content="content"
                    :initial-loading="false"
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
import {nextTick} from "vue";
import Chatbubble from "./chatbubble.vue";
import conf from '../../config'
import Localizer from "../Localizer.js";
import { useDevice } from "../useIsMobile.js";

export default {
    name: 'notifications-area',
    components: {
        Chatbubble
    },
    props: {
    },
    emits: [
        // create new chat from notification
    ],
    setup() {
        const { isMobile, screenWidth } = useDevice()
        return { conf, Localizer, isMobile, screenWidth };
    },
    data() {
        return {
            messages: []
        }
    },
    methods: {

        /**
         * adapted from different parts in content.vue
         */
        async addNotificationBubble(response) {
            const elementId = `chatbubble-${this.messages.length}`;

            const message = { 
                elementId: elementId, 
                content: response.content , 
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

        async dismissNotification(elementId) {
            this.messages = this.messages.filter(m => m.elementId !== elementId);
        },

        isBubbleCollapsed(elementId) {
            return this.$refs[elementId]?.[0]?.isCollapsed;
        },

        collapseBubble(elementId) {
            this.$refs[elementId]?.[0]?.toggleCollapsed();
        },

    },
}

</script>

<style scoped>

.notifications-container {
    max-height: 80vh;
    min-width: min(600px, 100vw - 9rem);
    max-width: calc(100vw - 9rem);
}

.delete-button {
    width: 2rem;
    height: 2rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 1rem !important;
    cursor: pointer;
}

</style>
