<template>
    <header>
        <div class="text-center py-0 my-0 mx-auto col">
            <nav class="navbar navbar-expand" type="light">

                <!-- backlink -->
                <div class="ms-1 w-auto text-start" v-if="conf.BackLink != null">
                    <a :href="conf.BackLink">
                        <img src="./assets/Icons/back.png" class="logo" alt="Back" height="20"/>
                    </a>
                </div>

                <!-- logos -->
                <div class="me-2 w-auto text-start" :class="{'ms-5': !this.isMobile}">
                    <a href="https://github.com/GT-ARC/opaca-core" target="blank">
                        <img v-bind:src="isMobile ? 'src/assets/opaca-logo-small.png' : 'src/assets/opaca-logo.png'"
                             class="logo" alt="Opaca Logo"
                             v-bind:height="isMobile ? 24 : 40"/>
                    </a>
                </div>
                <div class="me-2 w-auto text-start">
                    <a href="https://go-ki.org/" target="blank">
                        <img src="./assets/goki-gray-alpha.png" class="logo" alt="Go-KI Logo"
                             v-bind:height="isMobile ? 24 : 40"/>
                    </a>
                </div>
                <div class="me-2 w-auto text-start">
                    <a href="https://ze-ki.de/" target="blank">
                        <img src="./assets/zeki-logo.png" class="logo" alt="ZEKI Logo"
                             v-bind:height="isMobile ? 24 : 40"/>
                    </a>
                </div>

                <!-- options -->
                <div class="ms-auto me-0 w-auto"
                     v-bind:class="{ 'me-1': this.isMobile, 'me-3': !this.isMobile }">
                    <ul class="navbar-nav me-auto my-0 navbar-nav-scroll">

                        <!-- Connection -->
                        <li class="nav-item dropdown-center me-2">
                            <a class="nav-link dropdown-toggle" id="connectionSelector" href="#" role="button" data-bs-toggle="dropdown">
                                <span v-if="isConnecting" class="fa fa-spin fa-spinner fa-dis"></span>
                                <i :class="['fa', connected ? 'fa-link' : 'fa-unlink', 'me-1']" :style="{'color': connected ? 'green' : 'red'}"/>
                                <span v-show="!isMobile">{{ connected ? Localizer.get('pltConnected') : Localizer.get('pltDisconnected') }}</span>
                            </a>
                            <div class="dropdown-menu show p-4" aria-labelledby="connectionSelector" :style="{'min-width': !isMobile && '320px'}">
                                <div class="mb-3">
                                    <input v-if="!connected"
                                           type="text"
                                           v-model="opacaRuntimePlatform"
                                           placeholder="Enter URL"
                                           class="form-control form-control-sm me-2"/>
                                </div>
                                <button :class="['w-100', 'btn', connected ? 'btn-secondary' : 'btn-primary']"
                                        :disabled="isConnecting"
                                        @click="connectToPlatform">
                                    <template v-if="isConnecting">
                                        <span class="fa fa-spin fa-spinner fa-dis"></span>
                                    </template>
                                    <template v-else>
                                        {{ connected ? Localizer.get('disconnect') : Localizer.get('connect') }}
                                    </template>
                                </button>
                            </div>
                        </li>

                        <!-- languages -->
                        <li class="nav-item dropdown me-2">
                            <a class="nav-link dropdown-toggle" href="#" id="languageSelector" role="button" data-bs-toggle="dropdown">
                                <i class="fa fa-globe me-1"/>
                                <span v-show="!isMobile">{{ Localizer.get('name') }}</span>
                            </a>
                            <ul class="dropdown-menu" aria-labelledby="languageSelector">
                                <li v-for="{ key, name } in Localizer.getAvailableLocales()"
                                    @click="Localizer.language = key">
                                    <a class="dropdown-item">
                                        <p :style= "{'font-weight': Localizer.language === key ? 'bold' : 'normal'}">
                                            {{ name }}
                                        </p>
                                    </a>
                                </li>
                            </ul>
                        </li>

                        <!-- backends -->
                        <li class="nav-item dropdown me-2">
                            <a class="nav-link dropdown-toggle" href="#" id="backendSelector" role="button" data-bs-toggle="dropdown">
                                <i class="fa fa-server me-1"/>
                                <span v-show="!isMobile">{{ getBackendName(backend) }}</span>
                            </a>
                            <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="backendSelector">
                                <li v-for="(value, key) in conf.Backends"
                                    @click="setBackend(key)">

                                    <!-- top-level item/group -->
                                    <a v-if="typeof value !== 'string'" class="dropdown-item">
                                        <p v-if="this.isBackendSelected(key)" class="fw-bold">{{ value.name }}</p>
                                        <p v-else>{{ value.name }}</p>
                                    </a>
                                    <a v-else class="dropdown-item">
                                        <p v-if="this.isBackendSelected(key)" class="fw-bold">{{ value }}</p>
                                        <p v-else>{{ value }}</p>
                                    </a>

                                    <!-- sub-level items -->
                                    <ul v-if="typeof value !== 'string'"
                                        class="dropdown-menu dropdown-submenu dropdown-submenu-left">
                                        <li v-for="(subvalue, subkey) in value.subBackends"
                                            @click="this.setBackend(key + '/' + subkey)">
                                            <a class="dropdown-item">
                                                <p v-if="this.isBackendSelected(key + '/' + subkey)" class="fw-bold">
                                                    {{ subvalue }}
                                                </p>
                                                <p v-else>
                                                    {{ subvalue }}
                                                </p>
                                            </a>
                                        </li>
                                    </ul>

                                </li>
                            </ul>
                        </li>

                        <!-- Voice Server Settings -->
                        <li v-if="AudioManager.isBackendConfigured()" class="nav-item dropdown me-0">

                            <a class="nav-link dropdown-toggle" href="#" id="voiceServerSettings" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                                <i class="fa fa-microphone me-1"/>
                                <span v-show="!isMobile">Voice Server</span>
                            </a>
                            <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="voiceServerSettings">
                                <li>
                                    <div class="dropdown-item">
                                        <div class="d-flex align-items-center">
                                            <i class="fa" :class="AudioManager.isVoiceServerConnected ? 'fa-check-circle text-success' : 'fa-times-circle text-danger'" />
                                            <span class="ms-2">{{ AudioManager.isVoiceServerConnected ? Localizer.get('ttsConnected') : Localizer.get('ttsDisconnected') }}</span>
                                        </div>
                                    </div>
                                </li>
                                <li v-if="AudioManager.isVoiceServerConnected">
                                    <div class="dropdown-item dropdown-item-text">
                                        <!-- add word-wrapping to accomodate smaller devices -->
                                        <div class="text-muted"
                                             style=" min-width: min(400px, 100vw - 6rem); max-width: calc(100vw - 6rem); word-wrap: break-word; white-space: normal;">
                                            {{ Localizer.get('ttsServerInfo', AudioManager.deviceInfo.model, AudioManager.deviceInfo.device) }}
                                        </div>
                                    </div>
                                </li>
                                <li v-if="!AudioManager.isVoiceServerConnected">
                                    <button class="dropdown-item" @click="AudioManager.initVoiceServerConnection()">
                                        <i class="fa fa-refresh me-2"/>
                                        {{ Localizer.get('ttsRetry') }}
                                    </button>
                                </li>
                            </ul>
                        </li>

                        <!-- color theme toggle -->
                        <li class="nav-item me-2">
                            <a class="nav-link" href="#" role="button" @click="this.switchTheme()"  aria-expanded="false">
                                <i class="fa fa-adjust me-1" />
                            </a>
                        </li>
                    </ul>
                </div>
            </nav>
        </div>
    </header>



    <!-- Auth Modal -->
    <div v-if="showAuthInput" class="auth-overlay">
        <div class="dropdown-menu show p-4">
            <form @submit.prevent="connectToPlatform">
                <h5 class="mb-3">{{ Localizer.get('unauthenticated') }}</h5>
                <input
                        v-model="platformUser"
                        type="text"
                        :class="['form-control', 'mb-2', { 'is-invalid': loginError}]"
                        :placeholder="Localizer.get('username')"
                        @input="loginError = false"
                />
                <input
                        v-model="platformPassword"
                        type="password"
                        :class="['form-control', 'mb-3', { 'is-invalid': loginError}]"
                        :placeholder="Localizer.get('password')"
                        @input="loginError = false"
                />
                <div v-if="loginError" class="text-danger bg-light border border-danger rounded p-2 mb-3">
                    {{ Localizer.get('authError') }}
                </div>

                <button type="submit" class="btn btn-primary w-100" @click="connectToPlatform" :disabled="isConnecting">
                    <span v-if="isConnecting" class="fa fa-spinner fa-spin"></span>
                    <span v-else>{{ Localizer.get('submit') }}</span>
                </button>
                <button type="button" class="btn btn-link w-100 mt-2 text-muted" @click="showAuthInput = false">
                    {{ Localizer.get('cancel') }}
                </button>
            </form>
        </div>
    </div>

    <div class="col background">
        <MainContent
            :backend="this.backend"
            :language="this.language"
            :connected="this.connected"
            ref="content"
        />
    </div>
</template>

<script>
import conf from '../config.js';
import MainContent from './components/content.vue';

import {useDevice} from "./useIsMobile.js";
import Localizer from "./Localizer.js"
import {sendRequest} from "./utils.js";
import SidebarManager from "./SidebarManager.js";
import AudioManager from "./AudioManager.js";

export default {
    name: 'App',
    components: {MainContent},
    setup() {
        const { isMobile, screenWidth } = useDevice();
        return { conf, Localizer, AudioManager, isMobile, screenWidth };
    },
    data() {
        return {
            language: 'GB',
            backend: conf.BackendDefault,
            sidebar: 'connect',
            isDarkMode: (conf.ColorScheme === "light" ? false : conf.ColorScheme === "dark" ? true :
                         window.matchMedia('(prefers-color-scheme: dark)').matches),
            opacaRuntimePlatform: conf.OpacaRuntimePlatform,
            connected: false,
            isConnecting: false,
            showAuthInput: false,
            platformUser: "",
            platformPassword: "",
            loginError: false,
        }
    },
    methods: {
        async connectToPlatform() {
            if (this.connected) {
                this.connected = false;
                return
            }
            try {
                this.isConnecting = true;
                this.loginError = false;

                const body = {url: this.opacaRuntimePlatform, user: this.platformUser, pwd: this.platformPassword};
                const res = await sendRequest("POST", `${conf.BackendAddress}/connect`, body);
                this.platformPassword = "";
                const rpStatus = parseInt(res.data);

                if (rpStatus === 200) {
                    this.connected = true;
                    this.showAuthInput = false;
                } else if (rpStatus === 403) {
                    this.connected = false;
                    if (this.showAuthInput) {
                        this.loginError = true;
                    }
                    this.showAuthInput = true;
                } else {
                    this.connected = false;
                    alert(Localizer.get('unreachable'));
                }
            } catch (e) {
                console.error('Error while initiating prompt:', e);
                this.connected = false;
                alert('Backend server is unreachable.');
            } finally {
                this.isConnecting = false;
            }
        },

        setBackend(key) {
            const keyPath = key.split('/');
            const value = conf.Backends[keyPath[0]];
            const isGroupSelection = keyPath.length === 1 && typeof value !== 'string';

            if (isGroupSelection) {
                if (!this.isBackendSelected(key)) {
                    // select first entry in group
                    const first = Array.from(Object.keys(value.subBackends))[0];
                    this.backend = key + '/' + first;
                } else {
                    // do nothing, group already selected
                    // click one of the items in the group directly to select it
                }
            } else {
                // set backend directly
                this.backend = key;
            }

            console.log("BACKEND IS NOW:", this.backend);
        },

        getBackendName(key) {
            const path = key.split('/');
            if (path.length === 1) {
                return conf.Backends[key];
            } else {
                return conf.Backends[path[0]].subBackends[path[1]];
            }
        },

        /**
         * Checks if the given backend/group is currently selected.
         */
        isBackendSelected(key) {
            const selectedPath = this.backend.split('/');
            const keyPath = key.split('/');
            const value = conf.Backends[keyPath[0]];
            const isGroupSelection = keyPath.length === 1 && typeof value !== 'string';
            if (isGroupSelection && selectedPath.length > 1) {
                // check if the currently selected backend is in the group
                return selectedPath[0] === keyPath[0];
            }
            return key === this.backend;
        },

        switchTheme() {
            console.log("IN SET THEME")
            this.isDarkMode = ! this.isDarkMode;
            this.setTheme();
        },

        setTheme() {
            const theme = this.isDarkMode ? "dark" : "light";
            var colors = [
                "--background-color",
                "--surface-color",
                "--primary-color",
                "--secondary-color",
                "--accent-color",
                "--text-primary-color",
                "--text-secondary-color",
                "--text-success-color",
                "--text-danger-color",
                "--border-color",
                "--chat-user-color",
                "--chat-ai-color",
                "--input-color",
                "--debug-console-color",
                "--icon-invert-color",
            ]
            for (const color of colors) {
                document.documentElement.style.setProperty(color, `var(${color.replace("color", theme)})`);
            }
        },
    },

    mounted() {
        if (conf.ColorScheme != "system") {
            this.setTheme();
        }
        AudioManager.initVoiceServerConnection();

        if (conf.AutoConnect) {
            this.connectToPlatform();
        } else {
            SidebarManager.selectView(this.isMobile ? 'none' : conf.DefaultSidebarView);
        }
    }
}
</script>

<style scoped>
.background {
    background-color: var(--background-color);
}

header {
    background-color: var(--background-color);
    width: 100%;
    height: 50px;
    display: flex;
    align-items: center;
    box-shadow: var(--shadow-sm);
    border-bottom: 1px solid #e5e7eb;
    padding: 0 1rem;
    position: sticky;
    top: 0;
    z-index: 1000;
}

.logo {
    transition: transform 0.2s ease;
    filter: invert(var(--icon-invert-color));
}

.logo:hover {
    transform: scale(1.05);
}

.dropdown-item {
    cursor: pointer;
    padding: 0.75rem 1rem;
    transition: all 0.2s ease;
    color: var(--text-primary-color);
}

.dropdown-item:hover {
    background-color: var(--background-color);
    color: var(--primary-color);
}

.dropdown-menu {
    border-radius: var(--bs-border-radius);
    border: 1px solid #e5e7eb;
    box-shadow: var(--shadow-md);
    padding: 0.5rem;
    min-width: 200px;
    background-color: var(--surface-color);
    color: var(--text-primary-color)
}

.dropdown-menu li {
    position: relative;
}

.dropdown-menu h5 {
    color: var(--text-primary-color);
}

.dropdown-menu .dropdown-submenu {
    display: none;
    position: absolute;
    left: 100%;
    top: -7px;
    border-radius: var(--bs-border-radius);
    border: 1px solid #e5e7eb;
    box-shadow: var(--shadow-md);
}

.dropdown-menu .dropdown-submenu-left {
    right: 100%;
    left: auto;
}

.dropdown-menu > li:hover > .dropdown-submenu {
    display: block;
}

.nav-link {
    padding: 0.5rem 1rem;
    border-radius: var(--bs-border-radius);
    transition: all 0.2s ease;
    color: var(--text-primary-color);
}

.nav-link:hover {
    background-color: var(--surface-color);
    color: var(--primary-color);
}

.dropdown-toggle {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.connection-indicator {
    transition: background-color 0.3s ease, box-shadow 0.3s ease;
    box-shadow: 0 0 4px rgba(0, 0, 0, 0.1);
}

.auth-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background-color: rgba(0, 0, 0, 0.5); /* Transparent overlay */
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999; /* Should appear above all other items */
}

.is-invalid {
    border-color: #dc3545;
    background-color: #f8d7da;
    color: #842029;
}

.is-invalid::placeholder {
    color: #842029
}

@media (prefers-color-scheme: dark) {

    header {
        border-color: #2e2e2e;
    }

    .dropdown-menu {
        border-color: #2e2e2e;
        color: var(--text-primary-dark);
    }

}

/* Voice Server Settings Styles */
.text-success {
    color: var(--text-success-color) !important;
}

.text-danger {
    color: var(--text-danger-color) !important;
}

.text-muted {
    color: var(--text-secondary-color) !important;
}

.dropdown-item .fa {
    width: 1.25rem;
    text-align: center;
}

.dropdown-item button {
    background: none;
    border: none;
    width: 100%;
    text-align: left;
    padding: 0;
}
</style>
