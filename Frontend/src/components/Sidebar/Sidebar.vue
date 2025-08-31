<template>
    <div id="sidebar-base" class="d-flex">
        <!-- sidebar selection -->
        <div id="sidebar-menu"
             class="d-flex flex-column justify-content-start align-items-center gap-2">

            <i @click="SidebarManager.toggleView('info')"
               class="fa fa-circle-info sidebar-menu-item"
               :title="Localizer.get('tooltipSidebarInfo')"
               v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('info')}" />

            <i @click="SidebarManager.toggleView('chats')"
               class="fa fa-message sidebar-menu-item"
               :title="Localizer.get('tooltipSidebarInfo')"
               v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('chats')}" />

            <i @click="SidebarManager.toggleView('questions')"
               class="fa fa-book sidebar-menu-item"
               :title="Localizer.get('tooltipSidebarPrompts')"
               v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('questions')}" />

            <i @click="SidebarManager.toggleView('agents')"
               class="fa fa-users sidebar-menu-item"
               :title="Localizer.get('tooltipSidebarAgents')"
               v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('agents')}"/>

            <i @click="SidebarManager.toggleView('config')"
               class="fa fa-cog sidebar-menu-item"
               :title="Localizer.get('tooltipSidebarConfig')"
               v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('config')}"/>

            <i @click="SidebarManager.toggleView('debug')"
               class="fa fa-bug sidebar-menu-item"
               :title="Localizer.get('tooltipSidebarLogs')"
               v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('debug')}"/>

            <!-- spacer -->
            <div class="flex-grow-1" />

            <i @click="SidebarManager.toggleView('faq')"
               class="fa fa-question-circle sidebar-menu-item"
               :title="Localizer.get('tooltipSidebarFaq')"
               v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('faq')}"/>
        </div>

        <!-- sidebar content -->
        <div v-show="SidebarManager.isSidebarOpen()">
            <aside id="sidebar-content"
                   class="d-flex flex-column position-relative">

                <!-- platform information -->
                <SidebarInfo
                    v-show="SidebarManager.isViewSelected('info')"
                    :is-platform-connected="connected"
                    @update-platform-info="this.handleUpdatePlatformInfo"
                    ref="info"
                />

                <SidebarChats
                    v-show="SidebarManager.isViewSelected('chats')"
                    :selected-chat-id="this.selectedChatId"
                    @select-chat="chatId => this.$emit('select-chat', chatId)"
                    @delete-chat="chatId => this.$emit('delete-chat', chatId)"
                    @rename-chat="(chatId, newName) => this.$emit('rename-chat', chatId, newName)"
                />

                <!-- sample questions -->
                <SidebarQuestions
                    v-show="SidebarManager.isViewSelected('questions')"
                    @select-question="question => this.$emit('select-question', question)"
                    @select-category="category => this.$emit('select-category', category)"
                    ref="questions"
                />

                <!-- agents/actions overview -->
                <SidebarAgents
                    v-show="SidebarManager.isViewSelected('agents')"
                    ref="agents"
                />

                <!-- backend config -->
                <SidebarConfig
                    v-show="SidebarManager.isViewSelected('config')"
                    :backend="this.getBackend()"
                    ref="config"
                />

                <!-- debug console -->
                <SidebarDebug
                    v-show="SidebarManager.isViewSelected('debug')"
                    ref="debug"
                />

                <!-- Help/FAQ -->
                <SidebarFaq
                    v-show="SidebarManager.isViewSelected('faq')"
                    ref="faq"
                />

                <div v-show="!isMobile" class="resizer" id="resizer" />
            </aside>
        </div>
    </div>
</template>

<script>
import conf, {Backends, BackendDescriptions} from '../../../config.js'
import backendClient, {addDebugMessage} from "../../utils.js";
import { useDevice } from "../../useIsMobile.js";
import SidebarManager from "../../SidebarManager.js";
import Localizer from "../../Localizer.js";
import SidebarQuestions from './SidebarQuestions.vue';
import SidebarAgents from "./SidebarAgents.vue";
import SidebarConfig from "./SidebarConfig.vue";
import SidebarInfo from "./SidebarInfo.vue";
import SidebarDebug from "./SidebarDebug.vue";
import SidebarFaq from "./SidebarFaq.vue";
import SidebarChats from "./SidebarChats.vue";

export default {
    name: 'Sidebar',
    components: {
        SidebarChats,
        SidebarFaq,
        SidebarDebug,
        SidebarInfo,
        SidebarConfig,
        SidebarAgents,
        SidebarQuestions,
    },
    props: {
        backend: String,
        language: String,
        connected: Boolean,
        selectedChatId: String,
    },
    emits: [
        'select-question',
        'select-category',
        'select-chat',
        'delete-chat',
        'rename-chat',
    ],
    setup() {
        const { isMobile, screenWidth } = useDevice();
        return { conf, Backends, BackendDescriptions, SidebarManager, Localizer, isMobile, screenWidth};
    },
    data() {
        return {};
    },
    methods: {
        getBackend() {
            const parts = this.backend.split('/');
            return parts[parts.length - 1];
        },

        handleUpdatePlatformInfo(isPlatformConnected) {
            if (!this.$refs.agents) return;
            this.$refs.agents.updatePlatformInfo(isPlatformConnected);
        },

        setupResizer() {
            const resizer = document.getElementById('resizer');
            const sidebar = document.getElementById('sidebar-content');
            let isResizing = false;

            resizer.addEventListener('mousedown', (e) => {
                isResizing = true;
                document.body.style.cursor = 'ew-resize';
            });

            document.addEventListener('mousemove', (event) => {
                if (!isResizing) return;

                // Calculate the new width for the aside
                const newWidth = event.clientX - sidebar.getBoundingClientRect().left;

                if (newWidth > 200 && newWidth < 768) {
                    sidebar.style.width = `${newWidth}px`;
                }
            });

            document.addEventListener('mouseup', () => {
                isResizing = false;
                document.body.style.cursor = 'default';
            });
        },

        addDebugMessage(text, type) {
            if (!this.$refs.debug) return;
            this.$refs.debug.addDebugMessage(text, type);
        },

        clearDebugMessage() {
            if (!this.$refs.debug) return;
            this.$refs.debug.clearDebugMessage();
        },

    },
    mounted() {
        this.setupResizer();
    },
}
</script>

<style>
/* used in the sub-components! */
.sidebar-title {
    font-size: 150%;
    border-left: 5px solid var(--primary-color);
    padding-left: .5em;
    margin-bottom: .5em;
}
</style>

<style scoped>
#sidebar-base {
    background-color: var(--background-color);
}

/* sidebar content */
#sidebar-content {
    width: min(400px, 100vw - 3rem);
    height: calc(100vh - 50px - 1rem - 1rem); /* 100% - header - top margin - bottom margin */
    min-width: 150px;
    max-width: 768px;
    padding: .5rem;
    margin: 1rem 0 0 1rem;
    z-index: 999;
    background-color: var(--surface-color);
    border-radius: .5rem;
}

#sidebar-menu {
    background-color: var(--surface-color);
    border-right: 1px solid var(--border-color);
    padding: 0.5rem;
    margin: 1rem 0 0 1rem;
    transition: all 0.2s ease;
    border-radius: 0.5rem;
    height: calc(100vh - 50px - 1rem - 1rem); /* 100% - header - top margin - bottom margin */
}

.sidebar-menu-item {
    font-size: 1.25rem;
    cursor: pointer;
    width: 3rem;
    height: 3rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--bs-border-radius-lg);
    color: var(--text-secondary-color);
    transition: all 0.2s ease;
}

.sidebar-menu-item:hover {
    background-color: var(--background-color);
    color: var(--primary-color);
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}

.sidebar-menu-item-select {
    background-color: var(--primary-color) !important;
    color: white !important;
}

.sidebar-menu-item-select:hover {
    background-color: var(--secondary-color);
    color: white !important;
}

.resizer {
    width: 4px;
    cursor: ew-resize;
    height: calc(100vh - 50px - 1rem - 1rem); /* same as content */
    position: absolute;
    top: 0;
    right: 0;
    border-radius: var(--bs-border-radius-sm);
    background-color: var(--border-color);
    transition: background-color 0.2s ease;
}

.resizer:hover {
    background-color: var(--primary-color);
}

/* mobile design */
@media screen and (max-width: 768px) {
    .resizer {
        display: none;
    }

    #sidebar-menu {
        padding: 0.25rem;
        margin: 0;
        height: calc(100vh - 50px);
    }

    .sidebar-menu-item {
        font-size: 1rem;
        width: 2.5rem;
        height: 2.5rem;
    }

    #sidebar-content {
        width: min(600px, 100vw - 3rem);
        height: calc(100vh - 50px);
        padding-left: 0;
        padding-right: 0;
        margin: 0;
    }

}

</style>