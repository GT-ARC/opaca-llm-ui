<template>
    <div class="d-flex justify-content-start">
        <!-- sidebar selection -->
        <div id="sidebar-menu"
             class="d-flex flex-column justify-content-start align-items-center p-2 pt-3 gap-2"
             style="height: calc(100vh - 50px)">

            <i @click="selectView('connect')"
               class="fa fa-link p-2 sidebar-item"
               data-toggle="tooltip" data-placement="right" title="Config"
               v-bind:class="{'sidebar-item-select': isViewSelected('connect')}" />

            <i @click="selectView('agents')"
               class="fa fa-users p-2 sidebar-item"
               data-toggle="tooltip" data-placement="right" title="Agents"
               v-bind:class="{'sidebar-item-select': isViewSelected('agents')}"/>

            <i @click="selectView('config')"
               class="fa fa-cog p-2 sidebar-item"
               data-toggle="tooltip" data-placement="right" title="Backend Config"
               v-bind:class="{'sidebar-item-select': isViewSelected('config')}"/>

            <i @click="selectView('debug')"
               class="fa fa-terminal p-2 sidebar-item"
               data-toggle="tooltip" data-placement="right" title="Debug"
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
                                        <i class="fa fa-user me-1"/>
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
                    <div v-else class="flex-row text-start" >
                        <div v-for="(value, name) in backendConfig" :key="name">
                            <div class="py-2">
                                <div><strong>{{ name }}</strong></div>
                                <input v-model="backendConfig[name]"
                                       class="form-control w-100"
                                       type="text" :placeholder="String(value)"/>
                            </div>
                        </div>
                        <div class="py-2 text-center">
                            <button class="btn btn-primary py-2 w-100" type="button" @click="this.saveBackendConfig()">
                                <i class="fa fa-save me-1"/>
                                Save Config
                            </button>
                        </div>
                    </div>
                </div>

                <!-- debug console -->
                <div v-show="isViewSelected('debug')" id="chatDebug"
                     class="container flex-grow-1 mb-4 p-2 rounded rounded-4">
                    <div id="debug-console" class="flex-row-reverse text-start">
                        <div v-for="debugMessage in this.debugMessages" class="debug-text"
                             :style="debugMessage.color ? { color: debugMessage.color } : {}">
                            {{ debugMessage.text }}
                        </div>
                    </div>
                </div>

                <div class="resizer me-1" id="resizer" />
            </aside>
        </div>
    </div>
</template>

<script>
import conf from '../../config.js'
import {sendRequest} from "../utils.js";

export default {
    name: 'Sidebar',
    props: {
        backend: String,
        language: String
    },
    data() {
        return {
            selectedView: 'connect',
            opacaRuntimePlatform: conf.OpacaRuntimePlatform,
            opacaUser: '',
            opacaPwd: '',
            apiKey: '',
            platformActions: null,
            backendConfig: null,
            debugMessages: []
        };
    },
    methods: {
        getConfig() {
            return conf;
        },

        selectView(key) {
            const mainContent = document.getElementById('mainContent');
            if (this.selectedView !== key) {
                this.selectedView = key;
                mainContent.classList.remove('mx-auto');
            } else {
                this.selectedView = 'none';
                if (!mainContent.classList.contains('mx-auto')) {
                    mainContent.classList.add('mx-auto');
                }
            }
            this.$emit('onSidebarToggle', this.selectedView);
            console.log('selected sidebar view:', this.selectedView);
        },

        isViewSelected(key) {
            if (key !== undefined) {
                return this.selectedView === key;
            } else {
                return this.selectedView !== 'none';
            }
        },

        initRpConnection() {
            this.$emit('connect', this.opacaRuntimePlatform, this.opacaUser, this.opacaPwd);
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
            const backend = this.getBackend();
            const response = await sendRequest('GET', `${conf.BackendAddress}/${backend}/config`);
            if (response.status === 200) {
                this.backendConfig = response.data;
            } else {
                this.backendConfig = null;
                console.error(`Failed to fetch backend config for backend ${this.getBackend()}`);
            }
        }
    },
    mounted() {
        this.setupResizer();
        this.fetchBackendConfig();
    },
    watch: {
        backend(newValue) {
            this.fetchBackendConfig();
        }
    }
}
</script>

<style scoped>

#sidebar {
    min-width: 200px;
    max-width: 600px;
    position: relative;
}

#sidebar-menu {
    background-color: #fff;
}

.sidebar-item {
    font-size: 20px;
    cursor: pointer;
    width: 50px;
    border-radius: 5px;
}

.sidebar-item:hover {
    background-color: #ccc;
}

.sidebar-item-select {
    background-color: #ddd;
}

.resizer {
    width: 4px;
    cursor: ew-resize;
    height: calc(100vh - 85px - 25px);
    position: absolute;
    top: 0;
    right: 0;
    border-radius: 2px;
}

.debug-text {
    display: block;
    text-align: left;
    margin-left: 3px;
    font-family: "Courier New", monospace;
    font-size: small;
}

@media (prefers-color-scheme: dark) {
    .form-control::placeholder {
        color: #6c757d;
        opacity: 1;
    }

    #sidebar-menu {
        background-color: #333;
    }

    .sidebar-item:hover {
        background-color: #222;
    }

    .sidebar-item-select {
        background-color: #2a2a2a;
    }

    .resizer {
        background-color: #181818;
    }

    .accordion, .accordion-item, .accordion-header, .accordion-body, .accordion-collapse {
        background-color: #222;
        color: #fff;
    }

    .accordion-item {
        border-color: #454d55;
    }

    .accordion-button {
        background-color: #343a40;
        color: #fff;
    }

    .accordion-button:not(.collapsed) {
        background-color: #212529;
        color: #fff;
    }

    .accordion-button:focus {
        box-shadow: 0 0 0 0.25rem rgba(255, 255, 255, 0.25); /* Light glow for focus */
    }

    .accordion-body .list-group .list-group-item {
        background-color: #222;
        color: #fff;
    }

    .accordion-button::after {
        filter: invert(100%) !important ;
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

</style>