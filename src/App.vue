<script setup>
    import Content from './components/content.vue'
    import { ref, provide } from 'vue'
    import conf from '../config.js'

    const language = ref('GB')
    const backend = ref(conf.BackendDefault)
    const sidebarOpen = ref(true);

    provide('language', language)
    provide('backend', backend)
    provide('sidebarOpen', sidebarOpen)
    provide('config', ref(conf))

    function setLanguage(lang){
        language.value = lang;        
    }
    function setBackend(val){
        backend.value = val;
        console.log("BACKEND IS NOW " + val);
    }
    function toggleSidebar() {
        sidebarOpen.value = !sidebarOpen.value;
        console.log('sidebar open: ' + sidebarOpen.value);

        // adjust spacing
        const mainContent = document.getElementById('mainContent');
        if (sidebarOpen.value) {
            mainContent.classList.remove('mx-auto')
            mainContent.classList.add('pe-4')
        } else {
            mainContent.classList.remove('pe-4');
            mainContent.classList.add('mx-auto');
        }
    }
</script>

<template>
    <header>
        <div class="col">
            <nav class="navbar navbar-expand-lg" type="light">
                <div class="sidebar-toggle" @click="toggleSidebar()">
                    <i class="fa fa-bars fs-3 my-auto p-3"/>
                </div>

                <div class="ms-4 w-auto text-start">
                    <img src="./assets/opaca-logo.png" id="logo" alt="Opaca Logo" height="50"/>
                </div>

                <div class="my-auto text-end w-auto ms-auto me-5">
                    <ul class="navbar-nav me-auto my-2 my-lg-0 navbar-nav-scroll">

                        <!-- languages -->
                        <li class="nav-item dropdown me-3">
                            <a class="nav-link dropdown-toggle" href="#" id="languageSelector" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                                <i class="fa fa-globe me-1"/>
                                {{ conf.translations[language].name}}
                            </a>
                            <ul class="dropdown-menu" aria-labelledby="languageSelector">
                                <li v-for="(value, key) in conf.translations" @click="setLanguage(key)">
                                    <a class="dropdown-item">
                                        <p v-bind:style= "[language === key ? {'font-weight': 'bold'} : {'font-weight': 'normal'}]">
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
                                {{ conf.Backends[backend] }}
                            </a>
                            <ul class="dropdown-menu" aria-labelledby="backendSelector">
                                <li v-for="(value, key) in conf.Backends" @click="setBackend(key)">
                                    <a class="dropdown-item">
                                        <p v-bind:style= "[backend === key ? {'font-weight': 'bold'} : {'font-weight': 'normal'}]">
                                            {{ value }}
                                        </p>
                                    </a>
                                </li>
                            </ul>
                        </li>
                    </ul>
                </div>
            </nav>
        </div>
    </header>

    <div class="col background">
        <component :is="Content" class="tab" @reset="resetHistory()" />
    </div>
</template>

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

    .sidebar-toggle {
        cursor: pointer;
    }

    @media (prefers-color-scheme: dark) {

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
    }
</style>
