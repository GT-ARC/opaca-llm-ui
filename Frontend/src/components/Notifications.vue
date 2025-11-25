<template>
    <div class="notifications-container overflow-auto">
        <div v-for="{ taskId, loading, content, time } in this.messages">
            <div class="d-flex align-items-center justify-content-between px-1">
                <span>{{ time }}</span>
                <i v-if="! loading" class="fa fa-remove delete-button"
                    @click.stop="this.dismissNotification(elementId)"
                    title="Dismiss"
                />
            </div>
            <Chatbubble
                :key="content"
                :element-id="taskId"
                :is-user="false"
                :initial-content="content"
                :initial-loading="loading"
                :is-bookmarked="false"
                :files="[]"
                :chat-id="''"
                :ref="taskId"
                @add-to-library=""
            />
        </div>
    </div>
</template>

<script>
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
            const message = { 
                taskId: response.task_id,
                loading: true, 
                content: response.query, 
                time: new Date().toLocaleString(),
            };
            this.messages.unshift(message);
        },

        async finishNotificationBubble(response) {
            // update message
            const message = this.messages.find(m => m.taskId == response.task_id);
            message.loading = false;
            message.content = response.content;
            message.time = new Date().toLocaleString();

            // add debug stuff to chat bubble
            const chatBubble = this.$refs[response.task_id][0];
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
            this.messages = this.messages.filter(m => m.elementId != elementId);
        }

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
