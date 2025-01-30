<template>
    <div class="d-flex justify-content-start">
        <!-- sidebar selection -->
        <div id="sidebar-menu"
             class="d-flex flex-column justify-content-start align-items-center p-2 pt-3 gap-2"
             style="height: calc(100vh - 50px)">

            <i @click="selectView('connect')"
               class="fa fa-link p-2 sidebar-item"
               data-toggle="tooltip" data-placement="right" title="Connection"
               v-bind:class="{'sidebar-item-select': isViewSelected('connect')}" />

            <i @click="selectView('questions')"
               class="fa fa-book p-2 sidebar-item"
               data-toggle="tooltip" data-placement="right" title="Prompt Library"
               v-bind:class="{'sidebar-item-select': isViewSelected('questions')}" />

            <i @click="selectView('agents')"
               class="fa fa-users p-2 sidebar-item"
               data-toggle="tooltip" data-placement="right" title="Agents & Actions"
               v-bind:class="{'sidebar-item-select': isViewSelected('agents')}"/>

            <i @click="selectView('config')"
               class="fa fa-cog p-2 sidebar-item"
               data-toggle="tooltip" data-placement="right" title="Configuration"
               v-bind:class="{'sidebar-item-select': isViewSelected('config')}"/>

            <i @click="selectView('debug')"
               class="fa fa-terminal p-2 sidebar-item"
               data-toggle="tooltip" data-placement="right" title="Logging"
               v-bind:class="{'sidebar-item-select': isViewSelected('debug')}"/>
        </div>

        <!-- sidebar content -->
        <div v-show="isViewSelected()" class="mt-4">
            <aside id="sidebar"
               class="container-fluid d-flex flex-column px-3"
               style="height: calc(100vh - 85px); width: 400px">

                <!-- connection settings -->
                <div v-show="isViewSelected('connect')">
                    <div id="sidebarConfig"
                     class="container d-flex flex-column">

                    <div class="py-2 text-start">
                        <input id="opacaUrlInput" type="text"
                               class="form-control m-0"
                               v-model="opacaRuntimePlatform"
                               :placeholder="getConfig().translations[language].opacaLocation" />
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

                    <div class="py-2 text-start" v-if="getConfig().ShowApiKey">
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
                <div v-show="isViewSelected('agents')"
                     id="containers-agents-display" class="container flex-grow-1 overflow-hidden overflow-y-auto">
                    <div v-if="!platformActions || Object.keys(platformActions).length === 0">No actions available.</div>
                    <div v-else class="flex-row" >
                        <div class="accordion text-start" id="agents-accordion">
                            <div v-for="(actions, agent, index) in platformActions" class="accordion-item" :key="index">

                                <!-- header -->
                                <h2 class="accordion-header m-0" :id="'accordion-header-' + index">
                                    <button class="accordion-button" :class="{collapsed: index > 0}"
                                            type="button" data-bs-toggle="collapse"
                                            :data-bs-target="'#accordion-body-' + index" aria-expanded="false"
                                            :aria-controls="'accordion-body-' + index">
                                        <i class="fa fa-user me-3"/>
                                        <strong>{{ agent }}</strong>
                                    </button>
                                </h2>

                                <!-- body -->
                                <div :id="'accordion-body-' + index" class="accordion-collapse collapse" :class="{show: index === 0}"
                                     :aria-labelledby="'accordion-header-' + index" data-bs-parent="#agents-accordion">
                                    <div class="accordion-body p-0 ps-4">
                                        <ul class="list-group list-group-flush">
                                            <li v-for="(action, index) in actions" :key="index" class="list-group-item">
                                                {{ action }}
                                            </li>
                                        </ul>
                                    </div>
                                </div>

                            </div>
                        </div>
                    </div>
                </div>

                <!-- backend config -->
                <div v-show="isViewSelected('config')"
                     id="containers-agents-display" class="container flex-grow-1 overflow-hidden overflow-y-auto">
                    <div v-if="!backendConfig || Object.keys(backendConfig).length === 0">No config available.</div>
                    <div v-else class="flex-row text-start">
                        <!-- Other Config Items -->
                        <div v-for="(value, name) in backendConfig" :key="name" class="config-section">
                            <div class="config-section-header">
                                <strong>{{ name }}</strong>
                            </div>
                            <input v-model="backendConfig[name]"
                                   class="form-control"
                                   type="text" :placeholder="String(value)"/>
                        </div>

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
                    </div>
                </div>

                <!-- debug console -->
                <div v-show="isViewSelected('debug')" id="chatDebug"
                     class="container flex-grow-1 mb-4 p-2 rounded rounded-4">
                    <div id="debug-console" class="text-start">
                        <DebugMessage
                            v-for="debugMessage in debugMessages"
                            :key="debugMessage.text"
                            :text="debugMessage.text"
                            :color="debugMessage.color"
                            :data-type="debugMessage.type"
                        />
                    </div>
                </div>

                <!-- sample questions -->
                <div v-show="isViewSelected('questions')"
                     class="container flex-grow-1 overflow-hidden overflow-y-auto">
                    <SidebarQuestions
                        :questions="getConfig().translations[language].sidebarQuestions"
                        @select-question="handleQuestionSelect"
                        @category-selected="(category) => $emit('category-selected', category)"/>
                </div>

                <div class="resizer me-1" id="resizer" />
            </aside>
        </div>
    </div>
</template>

<script>
import conf from '../../config.js'
import {sendRequest} from "../utils.js";
import DebugMessage from './DebugMessage.vue';
import SidebarQuestions from './SidebarQuestions.vue';


export default {
    name: 'Sidebar',
    components: {
        DebugMessage,
        SidebarQuestions
    },
    props: {
        backend: String,
        language: String
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
            debugMessages: [],
            selectedLanguage: 'english',
            isConnected: false
        };
    },
    methods: {
        getConfig() {
            return conf;
        },

        getSidebarManager() {
            return sm;
        },

        selectView(key) {
            const mainContent = document.getElementById('mainContent');
            if (this.selectedView !== key) {
                this.selectedView = key;
                mainContent?.classList.remove('mx-auto');
            } else {
                this.selectedView = 'none';
                mainContent?.classList.add('mx-auto');
            }
            this.$emit('on-sidebar-toggle', this.selectedView);
            console.log('selected sidebar view:', this.selectedView);
        },

        isViewSelected(key) {
            if (key !== undefined) {
                return this.selectedView === key;
            } else {
                return this.selectedView !== 'none';
            }
        },

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
                    this.selectView(this.getConfig().DefaultSidebarView);
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
                this.selectView('connect');
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
            const response = await sendRequest('PUT', `${conf.BackendAddress}/${backend}/config`, this.backendConfig);
            if (response.status === 200) {
                console.log('Saved backend config.');
            } else {
                console.error('Error saving backend config.');
            }
        },

        async resetBackendConfig() {
            const backend = this.getBackend()
            const response = await sendRequest('POST', `${conf.BackendAddress}/${backend}/config/reset`);
            if (response.status === 200) {
                this.backendConfig = response.data;
                console.log('Reset backend config.');
            } else {
                this.backendConfig = null;
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
                    this.backendConfig = response.data;
                } else {
                    this.backendConfig = null;
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
        }
    },
    mounted() {
        this.setupResizer();
        this.fetchBackendConfig();
        if (this.language === 'GB') {
            this.selectedLanguage = 'english';
        } else if (this.language === 'DE') {
            this.selectedLanguage = 'german';
        }
        // Ensure the main content is properly positioned
        const mainContent = document.getElementById('mainContent');
        if (mainContent) {
            mainContent.classList.remove('mx-auto');
        }

        if (conf.AutoConnect) {
            this.initRpConnection();
        } else {
            this.selectView('connect');
        }
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

.list-group-item:hover {
    background-color: var(--surface-light);
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

    .list-group-item:hover {
        background-color: var(--surface-dark);
    }

    .accordion-body {
        background-color: var(--background-dark);
    }

    .accordion-collapse {
        background-color: var(--background-dark);
    }
}

.config-section {
    margin-bottom: 1.5rem;
}

.config-section-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
}

.config-section-header i {
    color: var(--primary-light);
    font-size: 1.125rem;
}

.config-section-header strong {
    color: var(--text-primary-light);
}

.config-section-content {
    padding-left: 1.5rem;
    color: var(--text-secondary-light);
}

@media (prefers-color-scheme: dark) {
    .config-section-header strong {
        color: var(--text-primary-dark);
    }

    .config-section-content {
        color: var(--text-secondary-dark);
    }

    .config-section-header i {
        color: var(--primary-dark);
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