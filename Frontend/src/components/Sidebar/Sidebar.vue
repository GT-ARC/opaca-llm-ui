<template>
    <div id="sidebar-base" class="d-flex">
        <!-- sidebar selection -->
        <div id="sidebar-menu"
             class="d-flex flex-column justify-content-start align-items-center gap-2">

            <!-- Always Visible: Info -->
            <i @click="SidebarManager.toggleView('info')"
               class="fa fa-circle-info sidebar-menu-item"
               :title="Localizer.get('sidebar_info')"
               v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('info')}" />

            <!-- Always Visible: Chats -->
            <i @click="SidebarManager.toggleView('chats')"
               class="fa fa-message sidebar-menu-item"
               :title="Localizer.get('sidebar_chats')"
               v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('chats')}" />

            <!-- Always Visible: Prompts -->
            <i @click="SidebarManager.toggleView('questions')"
               class="fa fa-book sidebar-menu-item"
               :title="Localizer.get('sidebar_questions')"
               v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('questions')}" />

            <!-- Collapse/Extend Button -->
            <i @click="toggleSidebar()"
               @mouseenter="sidebarToggleHovered = true"
               @mouseleave="sidebarToggleHovered = false"
               class="fa sidebar-menu-toggle"
               :class="getSidebarToggleIcon()"
               :title="getSidebarToggleTooltip()" />

            <!-- Expanded-only tools -->
            <div v-if="!sidebarCollapsed"
                 class="d-flex flex-column align-items-center gap-2"
                 style="min-height: 0; overflow: hidden;">
                <i @click="SidebarManager.toggleView('files')"
                   class="fa fa-file sidebar-menu-item"
                   :title="Localizer.get('sidebar_files')"
                   v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('files')}" />

                <i @click="SidebarManager.toggleView('agents')"
                   class="fa fa-users sidebar-menu-item"
                   :title="Localizer.get('sidebar_agents')"
                   v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('agents')}"/>

                <i @click="SidebarManager.toggleView('playBooks')"
                   class="fa fa-clipboard-check sidebar-menu-item"
                   :title="Localizer.get('sidebar_playBooks')"
                   v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('playBooks')}"/>

                <i @click="SidebarManager.toggleView('extensions')"
                   class="fa fa-puzzle-piece sidebar-menu-item"
                   :title="Localizer.get('sidebar_extensions')"
                   v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('extensions')}"/>

                <i @click="SidebarManager.toggleView('mcp')"
                   class="fa fa-server sidebar-menu-item"
                   :title="Localizer.get('sidebar_mcp')"
                   v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('mcp')}"/>

                <i @click="SidebarManager.toggleView('config')"
                   class="fa fa-cog sidebar-menu-item"
                   :title="Localizer.get('sidebar_config')"
                   v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('config')}"/>

                <i @click="SidebarManager.toggleView('debug')"
                   class="fa fa-bug sidebar-menu-item"
                   :title="Localizer.get('sidebar_logs')"
                   v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('debug')}"/>
            </div>

            <!-- spacer -->
            <div class="flex-grow-1" />

            <!-- Always Visible: FAQ -->
            <i @click="SidebarManager.toggleView('faq')"
               class="fa fa-question-circle sidebar-menu-item"
               :title="Localizer.get('sidebar_faq')"
               v-bind:class="{'sidebar-menu-item-select': SidebarManager.isViewSelected('faq')}"/>

            <!-- Always Visible: User Profile -->
            <SidebarAccount
                v-show="conf.authEnabled"
                @update-user-info="updateSidebarUserInfo"
                @update-mcp-servers="$refs.mcp.updateMcp(connected)"
                ref="account"
            />
        </div>

        <!-- sidebar content -->
        <div v-show="SidebarManager.isSidebarOpen()">
            <aside id="sidebar-content"
                   class="d-flex flex-column position-relative">

                <!-- platform information -->
                <SidebarInfo
                    v-show="SidebarManager.isViewSelected('info')"
                    :is-platform-connected="connected"
                    :sidebar-view="SidebarManager.getSelectedView()"
                    ref="info"
                />

                <!-- chats -->
                <SidebarChats
                    v-show="SidebarManager.isViewSelected('chats')"
                    :selected-chat-id="this.selectedChatId"
                    :chats="this.chats"
                    @select-chat="chatId => this.$emit('select-chat', chatId)"
                    @delete-chat="chatId => this.$emit('delete-chat', chatId)"
                    @rename-chat="(chatId, newName) => this.$emit('rename-chat', chatId, newName)"
                    @new-chat="() => this.$emit('new-chat')"
                    @goto-search-result="(chatId, messageId) => this.$emit('goto-search-result', chatId, messageId)"
                    @delete-all-chats="() => this.$emit('delete-all-chats')"
                    @update-chats="this.updateChats"
                    ref="chats"
                />

                <!-- uploaded files -->
                <SidebarFiles
                    :selectedChatId="this.selectedChatId"
                    :chats="this.chats"
                    v-show="SidebarManager.isViewSelected('files')"
                    @delete-file="fileId => this.$emit('delete-file', fileId)"
                    @delete-all-files="() => this.$emit('delete-all-files')"
                    @upload-file="() => this.$emit('upload-file')"
                    @view-file="$emit('view-file', $event)"
                    @rename-file="(fileId, newName) => this.$emit('rename-file', fileId, newName)"
                    @update-chats="this.updateChats"
                    ref="files"
                />

                <!-- sample questions -->
                <SidebarQuestions
                    v-show="SidebarManager.isViewSelected('questions')"
                    :sidebar-view="SidebarManager.getSelectedView()"
                    @select-question="question => this.$emit('select-question', question)"
                    ref="questions"
                />

                <!-- agents/actions overview -->
                <SidebarAgents
                    v-show="SidebarManager.isViewSelected('agents')"
                    :is-platform-connected="connected"
                    ref="agents"
                />

                <!-- play books -->
                <SidebarPlayBooks
                    v-show="SidebarManager.isViewSelected('playBooks')"
                    :sidebar-view="SidebarManager.getSelectedView()"
                    ref="playBooks"
                />

                <!-- UI extensions -->
                <SidebarExtensions
                    v-show="SidebarManager.isViewSelected('extensions')"
                    :is-platform-connected="connected"
                    ref="extensions"
                />

                <!-- MCP servers -->
                <SidebarMcp
                    v-show="SidebarManager.isViewSelected('mcp')"
                    ref="mcp"
                />

                <!-- method config -->
                <SidebarConfig
                    v-show="SidebarManager.isViewSelected('config')"
                    ref="config"
                />

                <!-- debug console -->
                <SidebarDebug
                    v-show="SidebarManager.isViewSelected('debug')"
                    :selected-chat-id="this.selectedChatId"
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
import conf from '../../../config.js'
import { useDevice } from "../../useIsMobile.js";
import SidebarManager from "../../SidebarManager.js";
import Localizer from "../../Localizer.js";
import SidebarQuestions from './SidebarQuestions.vue';
import SidebarAgents from "./SidebarAgents.vue";
import SidebarExtensions from './SidebarExtensions.vue';
import SidebarConfig from "./SidebarConfig.vue";
import SidebarInfo from "./SidebarInfo.vue";
import SidebarDebug from "./SidebarDebug.vue";
import SidebarFaq from "./SidebarFaq.vue";
import SidebarChats from "./SidebarChats.vue";
import SidebarFiles from "./SidebarFiles.vue";
import SidebarMcp from "./SidebarMcp.vue";
import SidebarPlayBooks from "./SidebarPlayBooks.vue";
import SidebarAccount from "./SidebarAccount.vue";
import backendClient from "../../utils.js";

export default {
    name: 'Sidebar',
    components: {
        SidebarMcp,
        SidebarFiles,
        SidebarChats,
        SidebarFaq,
        SidebarDebug,
        SidebarInfo,
        SidebarConfig,
        SidebarAgents,
        SidebarPlayBooks,
        SidebarExtensions,
        SidebarQuestions,
        SidebarAccount,
    },
    props: {
        connected: Boolean,
        selectedChatId: String,
    },
    emits: [
        'select-question',
        'select-chat',
        'delete-chat',
        'rename-chat',
        'new-chat',
        'delete-file',
        'upload-file',
        'view-file',
        'rename-file',
        'goto-search-result',
        'delete-all-chats',
        'delete-all-files',
    ],
    setup() {
        const { isMobile } = useDevice();
        return { conf, SidebarManager, Localizer, isMobile };
    },
    data() {
        return {
            sidebarCollapsed: conf.sidebarCollapsed,
            sidebarToggleHovered: false,
            chats: [],
        };
    },
    methods: {
        toggleSidebar() {
            conf.sidebarCollapsed = !conf.sidebarCollapsed;
            this.sidebarCollapsed = conf.sidebarCollapsed; // needed for auto-update

            // Close view if it is now hidden
            const view = this.SidebarManager.getSelectedView();
            if (this.SidebarManager.viewNotInCollapsed(view)) {
                this.SidebarManager.close();
            }
        },

        getSidebarToggleIcon() {
            if (conf.sidebarCollapsed) return 'fa-angle-down';
            if (this.sidebarToggleHovered) return 'fa-angle-up';
            return 'fa-minus';
        },

        getSidebarToggleTooltip() {
            if (conf.sidebarCollapsed) return Localizer.get('sidebar_showAdvancedTools');
            return Localizer.get('sidebar_showStandardTools');
        },

        setupResizer() {
            const resizer = document.getElementById('resizer');
            const sidebar = document.getElementById('sidebar-content');

            resizer.addEventListener('mousedown', (e) => {
                SidebarManager.setResizing(true);
                document.body.style.cursor = 'ew-resize';
            });

            document.addEventListener('mousemove', (event) => {
                if (!SidebarManager.isResizing()) return;

                // Calculate the new width for the aside
                const newWidth = event.clientX - sidebar.getBoundingClientRect().left;

                if (newWidth >= 275 && newWidth < 768) {
                    sidebar.style.width = `${newWidth}px`;
                }
            });

            document.addEventListener('mouseup', () => {
                SidebarManager.setResizing(false);
                document.body.style.cursor = 'default';
            });
        },

        async updateChats() {
            try {
                this.chats = await backendClient.chats();
            } catch (error) {
                console.error(error);
                this.chats = [];
            }
        },

        async updateSidebarUserInfo() {
            // All-in-One Place to update user data in the sidebar
            // Called by App.vue
            await this.updateChats();
            await this.$refs.files.updateFiles();
            await this.$refs.config.fetchMethodConfig();
            await this.$refs.questions.loadPrompts();
        }
    },
    mounted() {
        this.setupResizer();

        if (this.isMobile) {
            SidebarManager.close()
        } else {
            SidebarManager.selectView(conf.selectedSidebar, conf.sidebarCollapsed);
        }
    },
}
</script>

<style>
/* used in the sub-components! */
.sidebar-title {
    display: flex;
    align-items: center;
    gap: .25rem;
    font-size: 150%;
    border-left: 5px solid var(--primary-color);
    padding-left: .5em;
    margin-bottom: .5em;
}

.sidebar-title-action {
    flex: 0 0 auto;
    width: 2rem;
    height: 2rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    border: 1px solid var(--primary-color);
    cursor: pointer;
    background-color: transparent;
    color: var(--primary-color);
    font-size: 1rem;
    transition: all 0.2s ease;
}

.sidebar-title-action:hover {
    background-color: var(--primary-color);
    color: var(--button-primary-color);
    transform: translateY(-1px);
}

.sidebar-title-action.active {
    background-color: var(--primary-color);
    border-color: var(--primary-color);
    color: var(--button-primary-color);
}

.sidebar-title-action-secondary {
    border-color: var(--text-secondary-color);
    color: var(--text-secondary-color);
}

.sidebar-title-action-danger {
    border-color: var(--text-danger-color);
    color: var(--text-danger-color);
}

.sidebar-title-action-secondary:hover {
    background-color: var(--text-secondary-color);
    border-color: var(--text-secondary-color);
    color: var(--button-primary-color);
}

.sidebar-title-action-danger:hover {
    background-color: var(--text-danger-color);
    color: var(--button-primary-color);
}

.sidebar-title-action.disabled {
    opacity: .5;
    cursor: default;
    pointer-events: none;
    transform: none;
}

.click-icon {
    flex: 0 0 auto;
    width: 2rem;
    height: 2rem;
    font-size: 1rem;
    padding: 0;
    margin: 0;
    aspect-ratio: 1 / 1 !important;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 1rem !important;
    cursor: pointer;
    color: var(--text-primary-color);
}

.click-icon:hover {
    background-color: var(--input-color);
    color: var(--text-danger-color);
    transform: translateY(-1px);
}

.click-icon.disabled {
    opacity: 0.5;
    cursor: default;
    transform: none;
    pointer-events: none;
    color: var(--text-primary-color) !important;
    background: none !important;
}

.section-actions .click-icon:hover {
    background-color: var(--primary-color);
}

.section-actions .click-icon {
    margin-right: 0 !important;
}

.section-actions .click-icon:last-child {
    margin-right: .75rem !important;
}

.sidebar-search-results {
    max-height: 12rem;
    overflow-y: auto;
    margin-bottom: .5rem;
}

.sidebar-search-result-group + .sidebar-search-result-group {
    margin-top: .75rem;
}

.sidebar-search-result-heading {
    color: var(--secondary-color);
    font-size: .875rem;
}

.sidebar-search-result-context {
    padding: .5rem;
    margin-top: .25rem;
    overflow-wrap: anywhere;
}

.sidebar-search-result-clickable:hover {
    background-color: var(--surface-color);
    cursor: pointer;
}

.sidebar-empty-state {
    padding: 1.2rem;
    color: var(--text-secondary-color);
    font-size: 1rem;
    text-align: center;
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
    min-width: min(275px, calc(100vw - 3rem));
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

.sidebar-menu-toggle {
    font-size: 1.25rem;
    cursor: pointer;
    width: 3rem;
    height: 1.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary-color);
    transition: all 0.2s ease;
}

.sidebar-menu-toggle:hover {
    color: var(--primary-color);
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

    .sidebar-menu-toggle {
        width: 2.5rem;
        height: 1rem;
        font-size: 1rem;
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
