<template>
    <header>
        <div class="col">
            <nav class="navbar navbar-expand-lg" type="light">
                <div class="sidebar-toggle d-none"> <!-- toggleSidebar() here -->
                    <i class="fa fa-bars fs-3 my-auto p-3"/>
                </div>

                <div class="ms-5 w-auto text-start">
                    <img src="./assets/opaca-logo.png" class="logo" alt="Opaca Logo" height="50"/>
                </div>
                <div class="ms-5 w-auto text-start">
                    <img src="./assets/goki-gray-alpha.png" class="logo" alt="Go-KI Logo" height="50"/>
                </div>
                <div class="ms-5 w-auto text-start">
                    <img src="./assets/zeki-logo.png" class="logo" alt="ZEKI Logo" height="50"/>
                </div>

                <div class="my-auto text-end w-auto ms-auto me-5">
                    <ul class="navbar-nav me-auto my-2 my-lg-0 navbar-nav-scroll">

                        <!-- languages -->
                        <li class="nav-item dropdown me-3">
                            <a class="nav-link dropdown-toggle" href="#" id="languageSelector" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                                <i class="fa fa-globe me-1"/>
                                {{ getConfig().translations[this.language].name}}
                            </a>
                            <ul class="dropdown-menu" aria-labelledby="languageSelector">
                                <li v-for="(value, key) in getConfig().translations" @click="this.setLanguage(key)">
                                    <a class="dropdown-item">
                                        <p v-bind:style= "[this.language === key ? {'font-weight': 'bold'} : {'font-weight': 'normal'}]">
                                            {{ value.name }}
                                        </p>
                                    </a>
                                </li>
                            </ul>
                        </li>

                        <!-- backends -->
                        <li class="nav-item dropdown">
                            <a class="nav-link dropdown-toggle" href="#" id="backendSelector" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                                <i class="fa fa-server me-1"/>
                                {{ getBackendName(backend) }}
                            </a>
                            <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="backendSelector">
                                <li v-for="(value, key) in getConfig().Backends"
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
                    </ul>
                </div>
            </nav>
        </div>
    </header>

    <div class="col background">
        <MainContent class="tab" :backend="this.backend" :language="this.language" ref="content" />
    </div>
</template>

<script>
import conf from '../config.js'
import MainContent from './components/content.vue'

export default {
    name: 'App',
    components: {MainContent},
    data() {
        return {
            language: 'GB',
            backend: conf.BackendDefault,
            sidebar: 'connect',
        }
    },
    methods: {
        getConfig() {
            return conf;
        },

        setLanguage(lang){
            this.language = lang;
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

        setupTooltips() {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl)
            });
        }
    },
    mounted() {
        this.setupTooltips();
    }
}
</script>

<style scoped>
header {
    background-color: #fff;
    width: 100%;
    height: 50px;
    display: flex;
    align-items: center;
}

.dropdown-item {
    cursor: pointer;
}

.dropdown-menu li {
    position: relative;
}

.dropdown-menu .dropdown-submenu {
    display: none;
    position: absolute;
    left: 100%;
    top: -7px;
}

.dropdown-menu .dropdown-submenu-left {
    right: 100%;
    left: auto;
}

.dropdown-menu > li:hover > .dropdown-submenu {
    display: block;
}

@media (prefers-color-scheme: dark) {
    .logo {
        filter: invert(100%)
    }

    #logo {
        filter: invert(100%)
    }

    .navbar {
        background-color: #333;
        color: white;
    }

    .navbar-nav .nav-link {
        color: white;
    }

    .dropdown-menu, .dropdown-item {
        background-color: #212529 !important;
        color: white;
    }
}
</style>
