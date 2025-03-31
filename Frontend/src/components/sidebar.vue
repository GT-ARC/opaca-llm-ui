<template>
    <div class="d-flex justify-content-start">
        <!-- sidebar selection -->
        <div id="sidebar-menu"
             class="d-flex flex-column justify-content-start align-items-center p-2 gap-2"
             style="height: calc(100vh - 50px);">

            <i @click="SidebarManager.toggleView('connect')"
               class="fa fa-link p-2 sidebar-item"
               data-toggle="tooltip" data-placement="right" title="Connection"
               v-bind:class="{'sidebar-item-select': SidebarManager.isViewSelected('connect')}" />

            <i @click="SidebarManager.toggleView('questions')"
               class="fa fa-book p-2 sidebar-item"
               data-toggle="tooltip" data-placement="right" title="Prompt Library"
               v-bind:class="{'sidebar-item-select': SidebarManager.isViewSelected('questions')}" />

            <i @click="SidebarManager.toggleView('agents')"
               class="fa fa-users p-2 sidebar-item"
               data-toggle="tooltip" data-placement="right" title="Agents & Actions"
               v-bind:class="{'sidebar-item-select': SidebarManager.isViewSelected('agents')}"/>

            <i @click="SidebarManager.toggleView('config')"
               class="fa fa-cog p-2 sidebar-item"
               data-toggle="tooltip" data-placement="right" title="Configuration"
               v-bind:class="{'sidebar-item-select': SidebarManager.isViewSelected('config')}"/>

            <i @click="SidebarManager.toggleView('debug')"
               class="fa fa-terminal p-2 sidebar-item"
               data-toggle="tooltip" data-placement="right" title="Logging"
               v-bind:class="{'sidebar-item-select': SidebarManager.isViewSelected('debug')}"/>
        </div>

        <!-- sidebar content -->
        <div v-show="SidebarManager.isSidebarOpen()" class="mt-4">
            <aside id="sidebar"
               class="container-fluid d-flex flex-column px-3"
               style="height: calc(100vh - 85px); width: min(400px, 100vw - 3rem)">

                <!-- connection settings -->
                <div v-show="SidebarManager.isViewSelected('connect')">
                    <div id="sidebarConfig"
                     class="container d-flex flex-column">

                    <div class="py-2 text-start">
                        <input id="opacaUrlInput" type="text"
                               class="form-control m-0"
                               v-model="opacaRuntimePlatform"
                               :placeholder="conf.translations[language].opacaLocation" />
                    </div>

                    <div class="py-2 text-start">
                        <div class="row opaca-credentials">
                            <div class="col-md-6">
                                <input id="opacaUser" type="text"
                                       class="form-control m-0"
                                       v-model="opacaUser"
                                       placeholder="Username" />
                            </div>
                            <div class="col-md-6">
                                <input id="opacaPwd" type="password"
                                       class="form-control m-0"
                                       v-model="opacaPwd"
                                       placeholder="Password" />
                            </div>
                        </div>

                    </div>

                    <div class="py-2 text-start" v-if="conf.ShowApiKey">
                        <input id="apiKey" type="password"
                               class="form-control m-0"
                               placeholder="OpenAI API Key"
                               v-model="this.apiKey"
                               @input="this.$emit('api-key-change', this.apiKey)" />
                    </div>

                    <div class="text-center py-2">
                        <button class="btn btn-primary w-100" @click="initRpConnection()" id="button-connect">
                            <i class="fa fa-link me-1"/>Connect
                        </button>
                    </div>

                </div>
                </div>

                <!-- agents/actions overview -->
                <div v-show="SidebarManager.isViewSelected('agents')"
                     id="containers-agents-display" class="container flex-grow-1 overflow-hidden overflow-y-auto">
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
                                                <p><strong>Description:</strong> {{ action.description }}</p>
                                                <strong>Input Parameters:</strong>
                                                <pre class="json-box">{{ formatJSON(action.parameters) }} </pre>
                                                <strong>Result:</strong>
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
                <div v-show="SidebarManager.isViewSelected('config')"
                     id="config-display" class="container flex-grow-1 overflow-hidden overflow-y-auto">
                    <div v-if="!backendConfig || Object.keys(backendConfig).length === 0">No config available.</div>
                    <div v-else class="flex-row text-start">
                        <config-parameter v-for="(value, name) in backendConfigSchema"
                                :key="name"
                                :name="name"
                                :value="value"
                                v-model="backendConfig[name]"/>

                        <div class="py-2 text-center">
                            <button class="btn btn-primary py-2 w-100" type="button" @click="saveBackendConfig">
                                <i class="fa fa-save me-2"/>Save Config
                            </button>
                        </div>
                        <div class="py-2 text-center">
                            <button class="btn btn-danger py-2 w-100" type="button" @click="resetBackendConfig">
                                <i class="fa fa-undo me-2"/>Reset to Default
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
                <div v-show="SidebarManager.isViewSelected('debug')" id="chatDebug"
                     class="container flex-grow-1 mb-4 p-2 rounded rounded-4">
                    <div id="debug-console" class="text-start">
                        <DebugMessage
                            v-for="debugMessage in debugMessages"
                            :key="debugMessage.text"
                            :text="debugMessage.text"
                            :color="debugMessage.color"
                            :type="debugMessage.type"
                            :execution-time="debugMessage.executionTime"
                            :response-metadata="debugMessage.responseMetadata"
                        />
                    </div>
                </div>

                <!-- sample questions -->
                <div v-show="SidebarManager.isViewSelected('questions')"
                     class="container flex-grow-1 overflow-hidden overflow-y-auto">
                    <SidebarQuestions
                        :questions="conf.translations[language].sidebarQuestions"
                        @select-question="handleQuestionSelect"
                        @category-selected="(category) => $emit('category-selected', category)"
                        ref="sidebar_questions" />
                </div>

                <div v-show="!isMobile" class="resizer me-1" id="resizer" />
            </aside>
        </div>
    </div>
</template>

<script>
import conf from '../../config.js'
import {sendRequest} from "../utils.js";
import DebugMessage from './DebugMessage.vue';
import SidebarQuestions from './SidebarQuestions.vue';
import { useDevice } from "../useIsMobile.js";
import ConfigParameter from './ConfigParameter.vue';
import SidebarManager from "../SidebarManager.js";

export default {
    name: 'Sidebar',
    components: {
        DebugMessage,
        SidebarQuestions,
        ConfigParameter
    },
    props: {
        backend: String,
        language: String
    },
    setup() {
        const { isMobile, screenWidth } = useDevice();
        return { SidebarManager, conf, isMobile, screenWidth};
    },
    data() {
        return {
            selectedView: 'none',
            opacaRuntimePlatform: conf.OpacaRuntimePlatform,
            opacaUser: '',
            opacaPwd: '',
            apiKey: '',
            platformActions: null,
            backendConfig: null,
            backendConfigSchema: null,
            debugMessages: [],
            selectedLanguage: 'english',
            isConnected: false,
            configMessage: "",
            configChangeSuccess: false,
            shouldFadeOut: false,
            fadeTimeout: null,
        };
    },
    methods: {
        async initRpConnection() {
            const connectButton = document.getElementById('button-connect');
            connectButton.disabled = true;
            console.log(`CONNECTING as ${this.opacaUser}`);
            try {
                const body = {url: this.opacaRuntimePlatform, user: this.opacaUser, pwd: this.opacaPwd};
                const res = await sendRequest("POST", `${conf.BackendAddress}/connect`, body);
                const rpStatus = parseInt(res.data);
                if (rpStatus === 200) {
                    const res2 = await sendRequest("GET", `${conf.BackendAddress}/actions`)
                    this.platformActions = res2.data;
                    this.isConnected = true;
                    await this.fetchBackendConfig();
                    SidebarManager.selectView(conf.DefaultSidebarView);
                } else if (rpStatus === 403) {
                    this.platformActions = null;
                    this.isConnected = false;
                    alert(conf.translations[this.language].unauthorized);
                } else {
                    this.platformActions = null;
                    this.isConnected = false;
                    alert(conf.translations[this.language].unreachable);
                }
            } catch (e) {
                console.error('Error while initiating prompt:', e);
                this.platformActions = null;
                this.isConnected = false;
                alert('Backend server is unreachable.');
            } finally {
                connectButton.disabled = false;
            }
        },

        getBackend() {
            const parts = this.backend.split('/');
            return parts[parts.length - 1];
        },

        async saveBackendConfig() {
            const backend = this.getBackend();
            try {
                const response = await sendRequest('PUT', `${conf.BackendAddress}/${backend}/config`, this.backendConfig);
                if (response.status === 200) {
                    console.log('Saved backend config.');
                    this.configChangeSuccess = true
                    this.configMessage = "Configuration Changed"
                    this.startFadeOut()
                } else {
                    console.error('Error saving backend config.');
                    this.configChangeSuccess = false
                    this.configMessage = "Unexpected Error"
                    this.startFadeOut()
                }
            } catch (error) {
                if (error.response.status === 400) {
                    console.log("Invalid Configuration Values: ", error.response.data.detail)
                    this.configChangeSuccess = false
                    this.configMessage = "Invalid Configuration Values: " + error.response.data.detail
                    this.startFadeOut()
                }
            }
        },

        async resetBackendConfig() {
            const backend = this.getBackend()
            const response = await sendRequest('POST', `${conf.BackendAddress}/${backend}/config/reset`);
            if (response.status === 200) {
                this.backendConfig = response.data.value;
                this.backendConfigSchema = response.data.config_schema;
                this.configChangeSuccess = true
                this.configMessage = "Reset Configuration to default values"
                this.startFadeOut()
                console.log('Reset backend config.');
            } else {
                this.backendConfig = this.backendConfigSchema = null;
                this.configChangeSuccess = false
                this.configMessage = "Unexpected error occurred during configuration reset"
                this.startFadeOut()
                console.error('Error resetting backend config.');
            }
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

                if (newWidth > 200 && newWidth < 600) {
                    sidebar.style.width = `${newWidth}px`;
                }
            });

            document.addEventListener('mouseup', () => {
                isResizing = false;
                document.body.style.cursor = 'default';
            });
        },

        async fetchBackendConfig() {
            if (!this.isConnected) {
                this.backendConfig = null;
                return;
            }
            const backend = this.getBackend();
            try {
                const response = await sendRequest('GET', `${conf.BackendAddress}/${backend}/config`);
                if (response.status === 200) {
                    this.backendConfig = response.data.value;
                    this.backendConfigSchema = response.data.config_schema;
                } else {
                    this.backendConfig = this.backendConfigSchema = null;
                    console.error(`Failed to fetch backend config for backend ${this.getBackend()}`);
                }
            } catch (error) {
                console.error('Error fetching backend config:', error);
                this.backendConfig = null;
            }
        },

        handleQuestionSelect(question) {
            // Send the question to the chat without closing the sidebar
            this.$emit('select-question', question);
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

        scrollDownConfigView() {
            const configContainer = document.getElementById('config-display');
            configContainer.scrollTop = configContainer.scrollHeight;
        },

        formatJSON(obj) {
            return JSON.stringify(obj, null, 2)
        },
    },
    mounted() {
        this.setupResizer();
        this.fetchBackendConfig();
        if (this.language === 'GB') {
            this.selectedLanguage = 'english';
        } else if (this.language === 'DE') {
            this.selectedLanguage = 'german';
        }

        if (conf.AutoConnect) {
            this.initRpConnection();
        } else {
            SidebarManager.selectView('connect');
        }
    },
    updated() {
        this.scrollDownConfigView()
    },
    watch: {
        backend(newValue) {
            this.fetchBackendConfig();
        },
        language: {
            immediate: true,
            handler(newVal) {
                if (newVal === 'GB') {
                    this.selectedLanguage = 'english';
                } else if (newVal === 'DE') {
                    this.selectedLanguage = 'german';
                }
            }
        }
    }
}
</script>

<style scoped>

#sidebar {
    width: 100%;
    min-width: 150px;
    max-width: 600px;
    position: relative;
    z-index: 999;
}

#sidebar-menu {
    background-color: var(--surface-light);
    border-right: 1px solid var(--border-light);
    padding: 1.5rem 0.75rem;
    transition: all 0.3s ease;
}

.sidebar-item {
    font-size: 1.25rem;
    cursor: pointer;
    width: 3rem;
    height: 3rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--border-radius-lg);
    color: var(--text-secondary-light);
    transition: all 0.2s ease;
}

.sidebar-item:hover {
    background-color: var(--background-light);
    color: var(--primary-light);
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}

.sidebar-item-select {
    background-color: var(--primary-light) !important;
    color: white !important;
}

.sidebar-item-select:hover {
    background-color: var(--secondary-light);
    color: white !important;
}

@media screen and (max-width: 768px) {
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
    border-radius: var(--border-radius-sm);
    background-color: #e5e7eb;
    transition: background-color 0.2s ease;
}

.resizer:hover {
    background-color: var(--primary-light);
}

.debug-container {
    height: 100%;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.debug-messages {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    display: flex;
    flex-direction: column-reverse;
    padding: 0.75rem;
}

.debug-text {
    display: block;
    text-align: left;
    margin-left: 0.5rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 0.875rem;
    padding: 0.25rem 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-wrap: break-word;
}

@media (prefers-color-scheme: dark) {
    .debug-container {
        background-color: var(--surface-dark);
        border-color: var(--border-dark);
    }

    #chatDebug {
        background-color: var(--surface-dark);
    }

    #sidebar {
        background-color: var(--background-dark);
    }

    #sidebar-menu {
        background-color: var(--surface-dark);
    }

    .sidebar-item {
        color: var(--text-secondary-dark);
    }

    .sidebar-item:hover {
        background-color: var(--background-dark);
        color: var(--text-primary-dark);
    }

    .sidebar-item-select {
        background-color: var(--primary-dark);
        color: white;
    }

    .resizer {
        background-color: var(--border-dark);
    }

    .resizer:hover {
        background-color: var(--primary-dark);
    }
}

@media (prefers-color-scheme: light) {
    .debug-container {
        background-color: var(--surface-light);
        border-color: var(--border-light);
    }

    #chatDebug {
        background-color: var(--surface-light);
    }
}

/* Accordion Styling */
.accordion-item {
    border-radius: var(--border-radius-md);
    margin-bottom: 0.5rem;
    border: 1px solid var(--border-light);
    overflow: hidden;
    background-color: var(--surface-light);
}

.accordion-button {
    border-radius: var(--border-radius-md);
    padding: 1rem;
    font-weight: 500;
    transition: all 0.2s ease;
    background-color: var(--surface-light);
    color: var(--text-primary-light);
}

.accordion-button i {
    margin-right: 0.75rem;
}

.accordion-button:not(.collapsed) {
    background-color: var(--primary-light);
    color: white;
    box-shadow: none;
}

.accordion-button:hover {
    background-color: var(--secondary-light)
}

.accordion-button:focus {
    box-shadow: none;
    border-color: transparent;
}

.accordion-button::after {
    background-size: 1rem;
    width: 1rem;
    height: 1rem;
    transition: all 0.2s ease;
}

.accordion-body {
    padding: 0;
    background-color: var(--background-light);
}

.accordion-collapse {
    background-color: var(--background-light);
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
    background-color: var(--bs-gray-200);
    color: var(--text-primary-light);
    padding: 0.75rem;
    border-radius: var(--border-radius-md);
    white-space: pre-wrap; /* Ensures line breaks */
    font-family: monospace;
}

/* Dark mode styles */
@media (prefers-color-scheme: dark) {
    #sidebar-menu {
        background-color: var(--surface-dark);
        border-color: var(--border-dark);
    }

    .sidebar-item {
        color: var(--text-secondary-dark);
    }

    .sidebar-item:hover {
        background-color: var(--background-dark);
        color: var(--primary-dark);
    }

    .sidebar-item-select {
        background-color: var(--primary-dark);
    }

    .sidebar-item-select:hover {
        background-color: var(--secondary-dark);
    }

    .accordion-item {
        background-color: var(--surface-dark);
        border-color: var(--border-dark);
    }

    .accordion-button {
        background-color: var(--surface-dark);
        color: var(--text-primary-dark);
    }

    .accordion-button:not(.collapsed) {
        background-color: var(--primary-dark);
        color: var(--text-primary-dark);
        box-shadow: none;
    }

    .accordion-button:focus {
        box-shadow: none;
        border-color: transparent;
    }

    .accordion-button::after {
        filter: invert(1);
    }

    .json-box {
    background-color: var(--surface-dark);
    color: var(--text-primary-dark);
}

    .form-control {
        background-color: var(--input-dark);
        border-color: var(--border-dark);
        color: var(--text-primary-dark);
    }

    .form-control::placeholder {
        color: var(--text-secondary-dark);
    }

    .form-control:focus {
        background-color: var(--input-dark);
        border-color: var(--primary-dark);
    }

    #chatDebug {
        background-color: var(--surface-dark);
        border-color: var(--border-dark);
    }

    .debug-text {
        color: var(--text-primary-dark);
    }
}

@media (prefers-color-scheme: light) {
    #chatDebug {
        background-color: #fff;
        overflow: hidden;
        border: 1px solid #ccc; /* border only needed in light mode */
    }

    .resizer {
        background-color: gray;
    }
}

.list-group {
    border-radius: var(--border-radius-md);
    overflow: hidden;
    background-color: transparent;
}

.list-group-item {
    padding: 0.75rem 1rem;
    background-color: transparent;
    border: none;
    border-bottom: 1px solid var(--border-light);
    color: var(--text-primary-light);
    transition: all 0.2s ease;
}

.list-group-flush .list-group-item {
    border-right: 0;
    border-left: 0;
    border-radius: 0;
}

/* Dark mode styles */
@media (prefers-color-scheme: dark) {
    .list-group-item {
        border-color: var(--border-dark);
        color: var(--text-primary-dark);
    }

    .accordion-body {
        background-color: var(--background-dark);
    }

    .accordion-collapse {
        background-color: var(--background-dark);
    }
}

#chatDebug {
    height: 100%;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

#debug-console {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    display: flex;
    flex-direction: column;
    padding: 0.5rem;
}

.debug-text {
    display: block;
    text-align: left;
    margin-left: 3px;
    font-family: "Courier New", monospace;
    font-size: small;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-wrap: break-word;
}

@media (prefers-color-scheme: dark) {
    #chatDebug {
        background-color: var(--surface-dark);
        border: 1px solid var(--border-dark);
    }

    #sidebar-menu {
        background-color: var(--surface-dark);
    }

    .sidebar-item {
        color: var(--text-secondary-dark);
    }

    .sidebar-item:hover {
        background-color: var(--background-dark);
        color: var(--text-primary-dark);
    }

    .sidebar-item-select {
        background-color: var(--primary-dark);
        color: white;
    }

    .resizer {
        background-color: var(--border-dark);
    }

    .resizer:hover {
        background-color: var(--primary-dark);
    }
}

@media (prefers-color-scheme: light) {
    #chatDebug {
        background-color: var(--surface-light);
        border: 1px solid var(--border-light);
    }

    .resizer {
        background-color: var(--border-light);
    }
}

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