<template>

    <CookieBanner />

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
                    <a href="https://github.com/GT-ARC/opaca-llm-ui" target="blank">
                        <img v-bind:src="isMobile ? 'src/assets/sage-logo-small.png' : 'src/assets/sage-logo.png'"
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

                        <!-- Notifications -->
                        <li class="nav-item dropdown me-2">
                            <a class="nav-link dropdown-toggle"
                               href="#"
                               id="notifications-dropdown"
                               role="button" data-bs-toggle="dropdown"
                               @click="this.unreadNotifications = 0">
                                <i v-if="this.unreadNotifications > 0" class="fa-solid fa-bell text-info me-1" />
                                <i v-else class="fa-regular fa-bell me-1" />
                                <span v-show="!isMobile">{{ this.unreadNotifications }}</span>
                            </a>
                            <div class="dropdown-menu dropdown-menu-end"
                                 id="notifications-area"
                                 aria-labelledby="notifications-dropdown">
                                <Notifications
                                    ref="Notifications"
                                />
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

    <InputDialogue ref="input"/>

    <div class="col background">
        <MainContent
            :method="this.method"
            :language="this.language"
            :connected="this.connected"
            @select-category="category => this.selectedCategory = category"
            @container-login-required="containerLoginDetails => handleContainerLogin(containerLoginDetails)"
            @api-key-required="apiKeyMessage => handleApiKey(apiKeyMessage)"
            @new-notification="response => createNotification(response)"
            ref="content"
        />
    </div>
</template>

<script>
import conf, {Methods} from '../config.js';
import MainContent from './components/content.vue';
import {useDevice} from "./useIsMobile.js";
import Localizer from "./Localizer.js"
import backendClient from "./utils.js";
import SidebarManager from "./SidebarManager.js";
import AudioManager from "./AudioManager.js";
import Notifications from './components/Notifications.vue';
import OptionsSelect from "./components/OptionsSelect.vue";
import {getCurrentTheme, setColorTheme} from './ColorThemes.js';
import CookieBanner from './components/CookieBanner.vue';
import InputDialogue from './components/InputDialogue.vue';

export default {
    name: 'App',
    components: {OptionsSelect, MainContent, CookieBanner, Notifications, InputDialogue},
    setup() {
        const { isMobile, screenWidth } = useDevice();
        return { conf, Methods, Localizer, AudioManager, isMobile, screenWidth };
    },
    data() {
        return {
            language: 'GB',
            method: conf.DefaultMethod,
            sidebar: 'connect',
            opacaRuntimePlatform: conf.OpacaRuntimePlatform,
            connected: false,
            isConnecting: false,
            selectedCategory: null,
            unreadNotifications: 0,
        }
    },
    methods: {
        async connectToPlatform(username="", password="") {
            try {
                this.isConnecting = true;
                this.loginError = false;

                const rpStatus = await backendClient.connect(this.opacaRuntimePlatform, username, password);
                this.platformPassword = "";

                if (rpStatus === 200) {
                    this.connected = true;
                    this.showAuthInput = false;
                } else if (rpStatus === 403) {
                    this.connected = false;

                    await this.$refs.input.showDialogue(
                        "Platform Login", 
                        Localizer.get('unauthenticated'),
                        username != "" ? Localizer.get('authError') : null,
                        {
                            username: "text",
                            password: "password",
                        }, 
                        (values) => {
                            if (values != null) {
                                this.connectToPlatform(values.username, values.password);
                            }
                        }
                    );

                } else {
                    this.connected = false;
                    alert(Localizer.get('opacaUnreachable'));
                }
            } catch (e) {
                console.error('Error while initiating prompt:', e);
                this.connected = false;
                alert(Localizer.get('backendUnreachable'));
            } finally {
                this.isConnecting = false;
                this.toggleConnectionDropdown(!this.connected);
            }
        },

        async disconnectFromPlatform() {
            try {
                await backendClient.disconnect();
                this.connected = false;
            } catch (e) {
                console.error(e);
                this.connected = true;
                alert(Localizer.get('backendUnreachable'));
            } finally {
                this.toggleConnectionDropdown(this.connected);
            }
        },

        setMethod(key) {
            this.method = key;
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
                case 'method': this.setMethod(value); break;
                case 'language': this.updateLanguage(value); break;
                case 'colorMode': this.setTheme(value); break;
                default: break;
            }
        },

        createNotification(response) {
            const notificationArea = this.$refs.Notifications;
            notificationArea.addNotificationBubble(response);
            this.unreadNotifications += 1;
        },

        async handleContainerLogin(containerLoginDetails) {
            await this.$refs.input.showDialogue(
                "Container Login", 
                `${Localizer.get('containerLoginMessage')}\n${containerLoginDetails.container_name}--${containerLoginDetails.tool_name}`, 
                containerLoginDetails.retry ? Localizer.get('authError') : null,
                {
                    username: "text",
                    password: "password",
                    timeout: {
                        "0": "Logout immediately",
                        "300": "Logout after 5 minutes",
                        "1800": "Logout after 30 minutes",
                        "3600": "Logout after 1 hour",
                        "14400": "Logout after 4 hours",
                    },
                }, 
                (values) => {
                    if (values != null) {
                        this.$refs.content.submitContainerLogin(values.username, values.password, values.timeout);
                    } else {
                        this.$refs.content.submitContainerLogin("", "", 0);
                    }
                }
            );
        },

        async handleApiKey(apiKeyMessage) {
            await this.$refs.input.showDialogue(
                "API Key Required",
                (apiKeyMessage?.is_invalid ? Localizer.get("apiKeyInvalid") : Localizer.get("apiKeyMissing")) + apiKeyMessage?.model,
                null,
                {
                    apiKey: "password",
                }, 
                (values) => {
                    if (values != null) {
                        this.$refs.content.submitApiKey(values.apiKey);
                    } else {
                        this.$refs.content.submitApiKey("");
                    }
                }
            );
        },

        async waitForConnection() {
            const maxAttempts = 15;
            for (let i = 0; i < maxAttempts; i++) {
                try {
                    return await backendClient.getConnection()
                } catch {
                    await new Promise(r => setTimeout(r, 1000));
                }
            }
            alert(Localizer.get('backendUnreachable'));
            throw new Error("SAGE Backend is unreachable.");
        }
    },

    async mounted() {
        if (conf.ColorScheme !== "system") {
            this.setTheme(conf.ColorScheme);
        }

        if (AudioManager.isBackendConfigured()) {
            AudioManager.initVoiceServerConnection();
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

        // check connection state until backend is reachable; also acts as initial "handshake" to initialize the Session
        // if no connection is established, display the user an error
        const url = await this.waitForConnection();
        if (url != null) {
            this.connected = true;
            this.opacaRuntimePlatform = url;
        } else if (conf.AutoConnect) {
            await this.connectToPlatform();
        } else {
            this.toggleConnectionDropdown(true);
        }
        // initialize sidebar states; NOTE: this is done here, and not in their respective mounted() methods
        // to ensure that all those steps are executed sequentially and no redundant sessions are created!
        const sidebars = await this.$refs.content.$refs.sidebar.$refs;
        await sidebars.files.updateFiles();
        await sidebars.chats.updateChats();
        await sidebars.config.fetchMethodConfig();
        await sidebars.questions.loadPersonalPrompts();
        // open permanent websocket connection to backend for "push notifications" to the UI
        this.$refs.content.connectWebsocket();
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
