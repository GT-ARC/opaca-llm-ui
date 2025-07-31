<template>
    <div id="sidebar-base" class="d-flex">
        <!-- sidebar selection -->
        <div id="sidebar-menu"
             class="d-flex flex-column justify-content-start align-items-center gap-2">

            <i @click="SidebarManager.toggleView('info')"
               class="fa fa-circle-info sidebar-item"
               :title="Localizer.get('tooltipSidebarInfo')"
               v-bind:class="{'sidebar-item-select': SidebarManager.isViewSelected('info')}" />

            <i @click="SidebarManager.toggleView('questions')"
               class="fa fa-book sidebar-item"
               :title="Localizer.get('tooltipSidebarPrompts')"
               v-bind:class="{'sidebar-item-select': SidebarManager.isViewSelected('questions')}" />

            <i @click="SidebarManager.toggleView('agents')"
               class="fa fa-users sidebar-item"
               :title="Localizer.get('tooltipSidebarAgents')"
               v-bind:class="{'sidebar-item-select': SidebarManager.isViewSelected('agents')}"/>

            <i @click="SidebarManager.toggleView('config')"
               class="fa fa-cog sidebar-item"
               :title="Localizer.get('tooltipSidebarConfig')"
               v-bind:class="{'sidebar-item-select': SidebarManager.isViewSelected('config')}"/>

            <i @click="SidebarManager.toggleView('debug')"
               class="fa fa-bug sidebar-item"
               :title="Localizer.get('tooltipSidebarLogs')"
               v-bind:class="{'sidebar-item-select': SidebarManager.isViewSelected('debug')}"/>

            <!-- spacer -->
            <div class="flex-grow-1" />

            <i @click="SidebarManager.toggleView('faq')"
               class="fa fa-question-circle sidebar-item"
               :title="Localizer.get('tooltipSidebarFaq')"
               v-bind:class="{'sidebar-item-select': SidebarManager.isViewSelected('faq')}"/>
        </div>

        <!-- sidebar content -->
        <div v-show="SidebarManager.isSidebarOpen()">
            <aside id="sidebar"
                   class="container-fluid d-flex flex-column position-relative"
                   :class="{'px-3': !isMobile}">

                <!-- platform information -->
                <div v-show="SidebarManager.isViewSelected('info')"
                     class="container flex-grow-1 overflow-hidden overflow-y-auto">
                     <div v-if="!isMobile" class="sidebar-title">
                        {{ Localizer.get('tooltipSidebarInfo') }}
                     </div>
                    <div v-if="!connected" class="placeholder-container">
                        <img src="../assets/opaca-llm-sleeping-dog-dark.png" alt="Sleeping-dog" class="placeholder-image" />
                        <h5 class="p-4">It's a little quiet here...</h5>
                    </div>
                    <div v-else v-html="this.howAssistContent" class="faq-content w-auto"/>
                </div>

                <!-- sample questions -->
                <div v-show="SidebarManager.isViewSelected('questions')"
                     class="container flex-grow-1 overflow-hidden overflow-y-auto">
                     <div v-if="!isMobile" class="sidebar-title">
                        {{ Localizer.get('tooltipSidebarPrompts') }}
                     </div>
                    <SidebarQuestions
                        @select-question="question => this.$emit('select-question', question)"
                        @select-category="category => this.$emit('select-category', category)"
                        ref="sidebar_questions"
                    />
                </div>

                <!-- agents/actions overview -->
                <div v-show="SidebarManager.isViewSelected('agents')"
                     class="container flex-grow-1 overflow-hidden overflow-y-auto">
                     <div v-if="!isMobile" class="sidebar-title">
                        {{ Localizer.get('tooltipSidebarAgents') }}
                     </div>
                    <div v-if="!platformActions || Object.keys(platformActions).length === 0">No actions available.</div>
                    <div v-else class="flex-row" >
                        <div class="accordion text-start" id="agents-accordion">
                            <div v-for="(actions, agent, agentIndex) in platformActions" class="accordion-item" :key="agentIndex">

                                <!-- header -->
                                <h2 class="accordion-header m-0" :id="'accordion-header-' + agentIndex">
                                    <button class="accordion-button collapsed"
                                            type="button" data-bs-toggle="collapse"
                                            :data-bs-target="'#accordion-body-' + agentIndex"
                                            aria-expanded="false"
                                            :aria-controls="'accordion-body-' + agentIndex">
                                        <i class="fa fa-user me-3"/>
                                        <strong>{{ agent }}</strong>
                                    </button>
                                </h2>

                                <!-- body -->
                                <div :id="'accordion-body-' + agentIndex" class="accordion-collapse collapse"
                                     :aria-labelledby="'accordion-header-' + agentIndex" :data-bs-parent="'#agents-accordion'">
                                    <div class="list-group list-group-flush" :id="'actions-accordion-' + agentIndex">
                                        <div v-for="(action, actionIndex) in actions" :key="actionIndex" class="list-group-item">

                                            <!-- header -->
                                            <button class="action-header-button collapsed"
                                                    type="button" data-bs-toggle="collapse"
                                                    :data-bs-target="'#action-body-' + agentIndex + '-' + actionIndex"
                                                    aria-expanded="false"
                                                    :aria-controls="'action-body-' + agentIndex + '-' + actionIndex">
                                                <i class="fa fa-wrench me-3"/>
                                                {{ action.name }}
                                            </button>

                                            <!-- action body -->
                                            <div :id="'action-body-' + agentIndex + '-' + actionIndex" class="accordion-collapse collapse"
                                                 :aria-labelledby="'action-header-' + agentIndex + '-' + actionIndex" :data-bs-parent="'#actions-accordion-' + agentIndex">
                                                <p v-if="action.description">
                                                    <strong>{{ Localizer.get('agentActionDescription') }}:</strong>
                                                    {{ action.description }}
                                                </p>
                                                <strong>{{ Localizer.get('agentActionParameters') }}:</strong>
                                                <pre class="json-box">{{ formatJSON(action.parameters) }}</pre>
                                                <strong>{{ Localizer.get('agentActionResult') }}:</strong>
                                                <pre class="json-box">{{ formatJSON(action.result) }} </pre>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- backend config -->
                <div v-show="SidebarManager.isViewSelected('config')" id="config-display" 
                     class="container flex-grow-1 overflow-hidden overflow-y-auto">
                     <div v-if="!isMobile" class="sidebar-title">
                        {{ Localizer.get('tooltipSidebarConfig') }}
                     </div>
                     <div class="py-2">
                        <p class="fw-bold">Config for
                            <i class="fa fa-server ms-1"/>
                            {{ Backends[this.getBackend()] }}
                        </p>
                        <p>{{ BackendDescriptions[this.getBackend()] }}</p>
                    </div>
                    <div v-if="!backendConfig || Object.keys(backendConfig).length === 0">No config available.</div>
                    <div v-else class="flex-row text-start">
                        <ConfigParameter v-for="(value, name) in backendConfigSchema"
                                          :key="name"
                                          :name="name"
                                          :value="value"
                                          v-model="backendConfig[name]"/>

                        <div class="py-2 text-center">
                            <button class="btn btn-primary py-2 w-100" type="button" @click="saveBackendConfig">
                                <i class="fa fa-save me-2"/>{{ Localizer.get('buttonBackendConfigSave') }}
                            </button>
                        </div>
                        <div class="py-2 text-center">
                            <button class="btn btn-danger py-2 w-100" type="button" @click="resetBackendConfig">
                                <i class="fa fa-undo me-2"/>{{ Localizer.get('buttonBackendConfigReset') }}
                            </button>
                        </div>
                        <div
                            v-if="!this.shouldFadeOut"
                            class="config-error-message text-center"
                            :class="{ 'text-danger': !this.configChangeSuccess, 'text-success': this.configChangeSuccess}">
                            {{ this.configMessage }}
                        </div>
                    </div>
                </div>

                <!-- debug console -->
                <div v-show="SidebarManager.isViewSelected('debug')" id="debug-display"
                     class="container flex-grow-1 overflow-hidden overflow-y-auto"
                     @scroll="handleDebugScroll">
                     <div v-if="!isMobile" class="sidebar-title">
                        {{ Localizer.get('tooltipSidebarLogs') }}
                     </div>
                    <div id="debug-console"
                         class="d-flex flex-column text-start rounded-4">
                        <DebugMessage v-for="debugMessage in debugMessages"
                                      :key="debugMessage.text"
                                      :text="debugMessage.text"
                                      :type="debugMessage.type"
                                      :execution-time="debugMessage.executionTime"
                                      :response-metadata="debugMessage.responseMetadata"
                        />
                    </div>
                </div>

                <!-- Help/FAQ -->
                <div v-show="SidebarManager.isViewSelected('faq')"
                     class="container flex-grow-1 overflow-hidden overflow-y-auto">
                     <div v-if="!isMobile" class="sidebar-title">
                        {{ Localizer.get('tooltipSidebarFaq') }}
                     </div>
                    <div v-html="this.faqContent"
                         class="d-flex flex-column text-start faq-content">
                    </div>
                </div>

                <div v-show="!isMobile" class="resizer me-1" id="resizer" />
            </aside>
        </div>
    </div>
</template>

<script>
import conf, {Backends, BackendDescriptions} from '../../config.js'
import backendClient, {addDebugMessage} from "../utils.js";
import DebugMessage from './DebugMessage.vue';
import SidebarQuestions from './SidebarQuestions.vue';
import { useDevice } from "../useIsMobile.js";
import ConfigParameter from './ConfigParameter.vue';
import SidebarManager from "../SidebarManager.js";
import Localizer from "../Localizer.js";
import {marked} from "marked";

export default {
    name: 'Sidebar',
    components: {
        DebugMessage,
        SidebarQuestions,
        ConfigParameter
    },
    props: {
        backend: String,
        language: String,
        connected: Boolean,
    },
    emits: [
        'select-question',
        'select-category',
    ],
    setup() {
        const { isMobile, screenWidth } = useDevice();
        return { conf, Backends, BackendDescriptions, SidebarManager, Localizer, isMobile, screenWidth};
    },
    data() {
        return {
            opacaRuntimePlatform: conf.OpacaRuntimePlatform,
            opacaUser: '',
            opacaPwd: '',
            apiKey: '',
            platformActions: null,
            backendConfig: null,
            backendConfigSchema: null,
            debugMessages: [],
            configMessage: "",
            configChangeSuccess: false,
            shouldFadeOut: false,
            fadeTimeout: null,
            faqContent: '',
            howAssistContent: '',
            autoScrollEnabled: true,
        };
    },
    methods: {

        async showHowCanYouHelpInSidebar() {
            try {
                this.howAssistContent = "Querying functionality, please wait...";
                const res = await backendClient.query("tool-llm", "How can you assist me?", false);
                const answer = res.agent_messages[0].content;
                this.howAssistContent = marked.parse(answer);
            } catch (error) {
                console.log("ERROR " + error);
                this.howAssistContent = `There was an error when querying the functionality: ${error}`
            }
        },

        getBackend() {
            const parts = this.backend.split('/');
            return parts[parts.length - 1];
        },

        async saveBackendConfig() {
            try {
                await backendClient.updateConfig(this.getBackend(), this.backendConfig);
                console.log('Saved backend config.');
                this.configChangeSuccess = true
                this.configMessage = "Configuration Changed"
            } catch (error) {
                if (error.response.status === 400) {
                    console.log("Invalid Configuration Values: ", error.response.data.detail)
                    this.configChangeSuccess = false
                    this.configMessage = "Invalid Configuration Values: " + error.response.data.detail
                } else {
                    console.error('Error saving backend config.');
                    this.configChangeSuccess = false
                    this.configMessage = "Unexpected Error"
                }
            }
            this.startFadeOut()
        },

        async resetBackendConfig() {
            try {
                const res = await backendClient.resetConfig(this.getBackend());
                console.log('Reset backend config.');
                this.backendConfig = res.value;
                this.backendConfigSchema = res.config_schema;
                this.configChangeSuccess = true
                this.configMessage = "Reset Configuration to default values"
            } catch (error) {
                console.error('Error resetting backend config.');
                this.backendConfig = this.backendConfigSchema = null;
                this.configChangeSuccess = false
                this.configMessage = "Unexpected error occurred during configuration reset"
            }
            this.startFadeOut()
        },

        setupResizer() {
            const resizer = document.getElementById('resizer');
            const sidebar = document.getElementById('sidebar');
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

        async fetchBackendConfig() {
            const backend = this.getBackend();
            this.backendConfig = this.backendConfigSchema = null;
            try {
                const res = await backendClient.getConfig(backend);
                this.backendConfig = res.value;
                this.backendConfigSchema = res.config_schema;
            } catch (error) {
                console.error('Error fetching backend config:', error);
            }
        },

        startFadeOut() {
            // Clear previous timeout (if the user saves the config again before fade-out could happen)
            if (this.fadeTimeout) {
                clearTimeout(this.fadeTimeout);
            }

            this.shouldFadeOut = false

            this.fadeTimeout = setTimeout(() => {
                this.shouldFadeOut = true;
            }, 3000)
        },

        scrollDownDebugView() {
            if (!this.autoScrollEnabled) return;
            const configContainer = document.getElementById('debug-display');
            configContainer.scrollTop = configContainer.scrollHeight;
        },

        formatJSON(obj) {
            return JSON.stringify(obj, null, 2)
        },

        handleDebugScroll() {
            // Disable autoscroll for debug console if user scrolled up
            const debugConsole = document.getElementById('debug-display');
            this.autoScrollEnabled = debugConsole.scrollTop + debugConsole.clientHeight >= debugConsole.scrollHeight - 10;
        },

        addDebugMessage(text, type) {
            addDebugMessage(this.debugMessages, text, type);
        },

        async buildFaqContent() {
            const readmeUrl = '/src/assets/about.md';
            try {
                const response = await fetch(readmeUrl);
                if (response.ok) {
                    const faqRaw = await response.text();
                    this.faqContent = marked.parse(faqRaw);
                } else {
                    console.error('Failed to fetch FAQ content:', response.status, response);
                }
            } catch (error) {
                console.error('Failed to fetch FAQ content:', error);
            }
        },

        clearDebugMessage() {
            this.debugMessages = [];
        },

    },
    mounted() {
        this.setupResizer();
        this.buildFaqContent();
        this.fetchBackendConfig();
    },
    updated() {
        this.scrollDownDebugView()
    },
    watch: {
        backend() {
            this.fetchBackendConfig();
        },
        async connected(newVal) {
            if (newVal) {
                await this.fetchBackendConfig()
                this.showHowCanYouHelpInSidebar() // Intentionally no await
                this.platformActions = await backendClient.getActions();
            } else {
                this.platformActions = null;
            }
        }
    }
}
</script>

<style scoped>
#sidebar-base {
    background-color: var(--background-color);
}

/* sidebar content */
#sidebar {
    width: min(400px, 100vw - 3rem);
    height: calc(100vh - 100px);
    min-width: 150px;
    max-width: 768px;
    z-index: 999;
    background-color: var(--surface-color);
    margin: 1em 0 0 1em;
    border-radius: .5em;
    padding: .5em;
}

#sidebar-menu {
    background-color: var(--surface-color);
    border-right: 1px solid var(--border-color);
    padding: .5em;
    margin: 1em 0 0 1em;
    transition: all 0.2s ease;
    border-radius: .5em;
    height: calc(100vh - 100px);
}

.sidebar-title {
    font-size: 150%;
    border-left: 5px solid var(--primary-color);
    padding-left: .5em;
    margin-bottom: .5em;
}

.sidebar-item {
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

.sidebar-item:hover {
    background-color: var(--background-color);
    color: var(--primary-color);
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}

.sidebar-item-select {
    background-color: var(--primary-color) !important;
    color: white !important;
}

.sidebar-item-select:hover {
    background-color: var(--secondary-color);
    color: white !important;
}

.faq-content {
    color: var(--text-primary-color);
}

@media screen and (max-width: 768px) {
    #sidebar {
        width: min(600px, 100vw - 3rem);
    }

    .sidebar-item {
        font-size: 0.8rem;
        width: 2rem;
        height: 2rem;
    }
}

.resizer {
    width: 4px;
    cursor: ew-resize;
    height: calc(100vh - 85px - 25px);
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

#debug-console {
    background-color: var(--debug-console-color);
    border: 1px solid var(--border-color);
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.action-header-button {
    background-color: transparent;
    color: inherit;
    padding: 0.5rem 0;
    border: none;
    box-shadow: none;
    text-align: left;
    width: 100%;
    font-weight: bold;
}

.action-header-button:focus {
    outline: none;
}

.action-header-button::after {
    display: none;
}

.json-box {
    background-color: var(--surface-color);
    color: var(--text-primary-color);
    padding: 0.75rem;
    border-radius: var(--bs-border-radius);
    white-space: pre-wrap; /* Ensures line breaks */
    font-family: monospace;
}

.placeholder-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 2rem;
    box-sizing: border-box;
    color: var(--text-secondary-light);
}

.placeholder-image {
    width: 180px;
    margin-bottom: 1rem;
    opacity: 0.6;
}

/* mobile design */
@media screen and (max-width: 768px) {
    .resizer {
        display: none;
    }

    #sidebar-menu {
        padding: 0.75rem;
    }

    .sidebar-item {
        font-size: 1rem;
        width: 2rem;
        height: 2rem;
    }
}

</style>