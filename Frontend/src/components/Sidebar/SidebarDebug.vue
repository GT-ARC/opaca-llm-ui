<template>
    <div id="debug-display"
         class="container flex-grow-1 overflow-hidden overflow-y-auto"
         @scroll="this.handleDebugScroll">

        <div v-if="!isMobile" class="sidebar-title">
            {{ Localizer.get('tooltipSidebarLogs') }}
        </div>

        <div id="debug-console"
             v-if="this.debugMessages.length > 0"
             class="d-flex flex-column text-start rounded-4 p-1">
            <div v-for="(debugMessage, index) in this.debugMessages"
                 :key="`${debugMessage.text}-${index}`">
                <DebugMessage
                    :text="debugMessage.text"
                    :type="debugMessage.type"
                    :execution-time="debugMessage.executionTime"
                    :response-metadata="debugMessage.responseMetadata"
                />
            </div>
        </div>
    </div>

</template>

<script>
import conf from "../../../config.js";
import Localizer from "../../Localizer.js";
import {useDevice} from "../../useIsMobile.js";
import DebugMessage from "../DebugMessage.vue";
import * as utils from "../../utils.js";

export default {
    name: "SidebarDebug",
    props: {
        selectedChatId: String,
    },
    components: {DebugMessage},
    data() {
        return {
            debugMessages: [],
            autoScrollEnabled: true,
        }
    },
    setup() {
        const { isMobile } = useDevice();
        return { conf, Localizer, isMobile };
    },
    methods: {
        scrollDownDebugView() {
            if (!this.autoScrollEnabled) return;
            const debugConsole = document.getElementById('debug-display');
            debugConsole.scrollTop = debugConsole.scrollHeight;
        },

        /**
         * Disable autoscroll for debug console if user scrolled up
         */
        handleDebugScroll() {
            const debugConsole = document.getElementById('debug-display');
            this.autoScrollEnabled = debugConsole.scrollTop +
                debugConsole.clientHeight >= debugConsole.scrollHeight - 10;
        },

        addDebugMessage(text, type, id=null) {
            const message = {id: id, text: text, type: type, chatId: this.selectedChatId};
            utils.addDebugMessage(this.debugMessages, message);
        },

        clearDebugMessages() {
            this.debugMessages = [];
        },

    },
    updated() {
        this.scrollDownDebugView();
    },
}
</script>

<style scoped>

#debug-console {
    background-color: var(--debug-console-color);
    border: 1px solid var(--border-color);
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

</style>