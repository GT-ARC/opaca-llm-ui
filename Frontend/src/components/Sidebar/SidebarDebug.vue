<template>
    <div id="debug-display"
         class="container flex-grow-1 overflow-hidden overflow-y-auto"
         @scroll="this.handleDebugScroll">

        <div v-if="!isMobile" class="sidebar-title">
            {{ Localizer.get('tooltipSidebarLogs') }}
        </div>

        <div id="debug-console"
             class="d-flex flex-column text-start rounded-4"
             :class="{'p-1': this.debugMessages.length > 0}" >
            <DebugMessage v-for="debugMessage in debugMessages"
                          :key="debugMessage.text"
                          :text="debugMessage.text"
                          :type="debugMessage.type"
                          :execution-time="debugMessage.executionTime"
                          :response-metadata="debugMessage.responseMetadata"
            />
        </div>
    </div>

</template>

<script>
import conf from "../../../config.js";
import Localizer from "../../Localizer.js";
import {useDevice} from "../../useIsMobile.js";
import DebugMessage from "../DebugMessage.vue";
import {addDebugMessage} from "../../utils.js";

export default {
    name: "SidebarDebug",
    props: {},
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

        addDebugMessage(text, type) {
            addDebugMessage(this.debugMessages, text, type);
        },

        clearDebugMessage() {
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