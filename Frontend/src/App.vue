<template>
    <header>
        <div class="col">
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

                        <!-- languages -->
                        <li class="nav-item dropdown me-2">
                            <a class="nav-link dropdown-toggle" href="#" id="languageSelector" role="button" data-bs-toggle="dropdown" aria-expanded="false">
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
                            <a class="nav-link dropdown-toggle" href="#" id="backendSelector" role="button" data-bs-toggle="dropdown" aria-expanded="false">
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
                    </ul>
                </div>
            </nav>
        </div>
    </header>

    <div class="col background">
        <MainContent
            class="tab"
            :backend="this.backend"
            :language="this.language"
            ref="content"
        />
    </div>
</template>

<script>
import conf from '../config.js';
import MainContent from './components/content.vue';

import {useDevice} from "./useIsMobile.js";
import Localizer from "./Localizer.js"
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
        }
    },
    methods: {
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
    },

    mounted() {
        AudioManager.initVoiceServerConnection();
    }
}
</script>

<style scoped>
.background {
    background-color: var(--background-light);
}

header {
    background-color: var(--background-light);
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
}

.logo:hover {
    transform: scale(1.05);
}

.dropdown-item {
    cursor: pointer;
    padding: 0.75rem 1rem;
    transition: all 0.2s ease;
}

.dropdown-item:hover {
    background-color: var(--surface-light);
}

.dropdown-menu {
    border-radius: var(--border-radius-md);
    border: 1px solid #e5e7eb;
    box-shadow: var(--shadow-md);
    padding: 0.5rem;
    min-width: 200px;
}

.dropdown-menu li {
    position: relative;
}

.dropdown-menu .dropdown-submenu {
    display: none;
    position: absolute;
    left: 100%;
    top: -7px;
    border-radius: var(--border-radius-md);
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
    border-radius: var(--border-radius-md);
    transition: all 0.2s ease;
    color: var(--text-primary-light);
}

.nav-link:hover {
    background-color: var(--surface-light);
    color: var(--primary-light);
}

.dropdown-toggle {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

@media (prefers-color-scheme: dark) {
    .background {
        background-color: var(--background-dark);
    }

    header {
        background-color: var(--background-dark);
        border-color: #2e2e2e;
    }

    .logo {
        filter: invert(1);
    }

    .nav-link {
        color: var(--text-primary-dark);
    }

    .nav-link:focus {
        color: var(--text-primary-dark);
    }

    .nav-link:hover {
        background-color: var(--surface-dark);
        color: var(--primary-dark);
    }

    .dropdown-menu {
        background-color: var(--surface-dark);
        border-color: #2e2e2e;
    }

    .dropdown-item {
        color: var(--text-primary-dark);
    }

    .dropdown-item:hover {
        background-color: var(--background-dark);
        color: var(--primary-dark);
    }

    .text-muted {
        color: var(--text-secondary-dark) !important;
    }
}

/* Voice Server Settings Styles */
.text-success {
    color: #10b981 !important;
}

.text-danger {
    color: #ef4444 !important;
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

@media (prefers-color-scheme: dark) {
    .text-success {
        color: #34d399 !important;
    }

    .text-danger {
        color: #f87171 !important;
    }
}
</style>
