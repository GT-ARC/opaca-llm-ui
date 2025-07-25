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
                <!--
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
                -->

                <!-- options -->
                <div class="ms-auto me-0 w-auto"
                     v-bind:class="{ 'me-1': this.isMobile, 'me-3': !this.isMobile }">
                    <ul class="navbar-nav me-auto my-0 navbar-nav-scroll">

                        <!-- Connection -->
                        <li class="nav-item dropdown me-2">
                            <a id="connectionSelector"
                               class="nav-link dropdown-toggle"
                               href="#" role="button"
                               data-bs-toggle="dropdown">
                                <span v-if="isConnecting" class="fa fa-spin fa-spinner fa-dis"></span>
                                <i :class="['fa', connected ? 'fa-link' : 'fa-unlink', 'me-1']" :style="{'color': connected ? 'green' : 'red'}"/>
                                <span v-show="!isMobile">{{ connected ? Localizer.get('pltConnected') : Localizer.get('pltDisconnected') }}</span>
                            </a>
                            <div id="connection-menu"
                                 class="dropdown-menu dropdown-menu-end p-4"
                                 aria-labelledby="connectionSelector"
                                 :style="{'min-width': !isMobile && '320px'}">
                                <div class="mb-3">
                                    <input :disabled="connected"
                                           type="text"
                                           v-model="opacaRuntimePlatform"
                                           placeholder="Enter URL"
                                           class="form-control form-control-sm me-2"/>
                                </div>
                                <button :class="['w-100', 'btn', connected ? 'btn-secondary' : 'btn-primary']"
                                        :disabled="isConnecting"
                                        @click="connected ? disconnectFromPlatform() : connectToPlatform()">
                                    <span v-if="isConnecting">
                                        <i class="fa fa-spin fa-spinner"></i>
                                    </span>
                                    <span v-else>
                                        {{ connected ? Localizer.get('disconnect') : Localizer.get('connect') }}
                                    </span>
                                </button>
                            </div>
                        </li>

                        <!-- Options -->
                        <li class="nav-item dropdown me-2">
                            <a class="nav-link dropdown-toggle"
                               href="#"
                               id="options-dropdown"
                               role="button" data-bs-toggle="dropdown">
                                <i class="fa fa-gear me-1"/>
                                <span v-show="!isMobile">{{ Localizer.get('settings') }}</span>
                            </a>
                            <div class="dropdown-menu dropdown-menu-end"
                                 id="options-menu"
                                 aria-labelledby="options-dropdown">
                                <div class="dropdown-item d-flex">
                                    <OptionsSelect
                                        @select="(key, value) => this.handleOptionSelect(key, value)"
                                        ref="OptionsSelect"
                                    />
                                </div>
                            </div>
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
            @select-category="category => this.selectedCategory = category"
            ref="content"
        />
    </div>
</template>

<script>
import conf, {Backends} from '../config.js';
import MainContent from './components/content.vue';
import {useDevice} from "./useIsMobile.js";
import Localizer from "./Localizer.js"
import {sendRequest} from "./utils.js";
import SidebarManager from "./SidebarManager.js";
import AudioManager from "./AudioManager.js";
import OptionsSelect from "./components/OptionsSelect.vue";
import {getCurrentTheme, setColorTheme} from './ColorThemes.js';

export default {
    name: 'App',
    components: {OptionsSelect, MainContent},
    setup() {
        const { isMobile, screenWidth } = useDevice();
        return { conf, Backends, Localizer, AudioManager, isMobile, screenWidth };
    },
    data() {
        return {
            language: 'GB',
            backend: conf.DefaultBackend,
            sidebar: 'connect',
            opacaRuntimePlatform: conf.OpacaRuntimePlatform,
            connected: false,
            isConnecting: false,
            showAuthInput: false,
            platformUser: "",
            platformPassword: "",
            loginError: false,
            selectedCategory: null,
        }
    },
    methods: {
        async connectToPlatform() {
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
                this.toggleConnectionDropdown(!this.connected);
            }
        },

        async disconnectFromPlatform() {
            try {
                await sendRequest("POST", `${conf.BackendAddress}/disconnect`);
                this.connected = false;
            } catch (e) {
                console.error(e);
                this.connected = true;
                alert('Backend server is unreachable.');
            } finally {
                this.toggleConnectionDropdown(this.connected);
            }
        },

        setBackend(key) {
            this.backend = key;
        },

        /**
         * Force the connection dropdown opened or closed.
         *
         * @param show {boolean} If true, force-show the dropdown, hide otherwise.
         */
        toggleConnectionDropdown(show) {
            const toggle = document.getElementById('connectionSelector');
            const dropdown = bootstrap.Dropdown.getOrCreateInstance(toggle);
            if (show) {
                dropdown.show();
            } else {
                dropdown.hide();
            }
        },

        setTheme(theme) {
            setColorTheme(document, theme);
        },

        updateLanguage(newLanguage) {
            Localizer.language = newLanguage;
            Localizer.reloadSampleQuestions(this.selectedCategory);
        },

        handleOptionSelect(key, value) {
            switch (key) {
                case 'method': this.setBackend(value); break;
                case 'language': this.updateLanguage(value); break;
                case 'colorMode': this.setTheme(value); break;
                default: break;
            }
        }
    },

    mounted() {
        if (conf.ColorScheme !== "system") {
            this.setTheme(conf.ColorScheme);
        }

        if (AudioManager.isBackendConfigured()) {
            AudioManager.initVoiceServerConnection();
        }

        if (conf.AutoConnect) {
            this.connectToPlatform();
        } else {
            this.toggleConnectionDropdown(true);
        }

        if (this.isMobile) {
            SidebarManager.close()
        } else {
            SidebarManager.selectView(conf.DefaultSidebarView);
        }

        // prevent options dropdown menu from closing once anything in it is clicked
        document.getElementById('options-menu')?.addEventListener('click', e => {
            e.stopPropagation();
        });

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
    border-bottom: 1px solid var(--border-color);
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
    padding: 0 !important;
    transition: all 0.2s ease;
    color: var(--text-primary-color);
    margin: 0 !important;
}

.dropdown-item-text {
    min-width: min(400px, 100vw - 6rem);
    max-width: calc(100vw - 6rem);
    word-wrap: break-word;
    white-space: normal;
}

.dropdown-item:hover {
    background-color: var(--background-color);
    color: var(--primary-color);
}

.dropdown-menu {
    border-radius: var(--bs-border-radius);
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-md);
    padding: 0;
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
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-md);
}

.dropdown-menu .dropdown-submenu-left {
    right: 100%;
    left: auto;
}

.dropdown-menu > li:hover > .dropdown-submenu {
    display: block;
}

/* navbar stuff */
.nav-link {
    padding: 0.5rem 1rem;
    border-radius: var(--bs-border-radius);
    transition: all 0.2s ease;
    color: var(--text-primary-color);
}

.nav-link:hover {
    background-color: var(--surface-color) !important;
    color: var(--primary-color) !important;
}

.nav-link.show {
    color: var(--text-primary-color) !important;
}

.dropdown-toggle {
    display: flex;
    align-items: center;
    gap: 0.5rem;
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

/* Voice Server Settings Styles */
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

#connection-menu {
    min-width: min(400px, 100vw - 6rem);
    max-width: calc(100vw - 4rem);
}

@media (max-width: 576px) {
    #connection-menu {
        position: fixed !important;
        top: auto !important;
        bottom: auto !important;
        left: 2rem !important;
        right: auto !important;
    }
}
</style>
