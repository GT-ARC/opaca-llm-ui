<template>
    <div class="d-flex justify-content-start flex-grow-1 w-100 position-relative z-1">
        <!-- Chat Window with Chat bubbles -->
        <div class="container-fluid flex-grow-1">
            <div class="chatbubble-container d-flex flex-column justify-content-between mx-auto">
                <Chatbubble
                    v-for="{ elementId, content } in this.messages"
                    :key="content"
                    :element-id="elementId"
                    :is-user="false"
                    :initial-content="content"
                    :initial-loading="false"
                    :is-bookmarked="false"
                    :files="[]"
                    :chat-id="''"
                    :ref="elementId"
                    @add-to-library=""
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
        // set status to "dirty" (highlight notification symbol)
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

            const message = { elementId: elementId, content: response.content };
            this.messages.push(message);

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

    },

    mounted() {
        this.addNotificationBubble({content: "Just a test", agent_messages: [{content: "stuff", tools: [{id: "1/1", name: "foo--bar", args: {x: 42}, result: "result"}]}], error: null});
        this.addNotificationBubble({content: "Another test", agent_messages: [], error: "some error"});
    },
}

</script>

<style scoped>

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

.chat-container {
    flex: 1;
    overflow-y: auto;
    position: relative;
    display: flex;
    flex-direction: column;
    min-height: 0; /* Important for Firefox */
    padding: 1rem 0;
}

</style>
