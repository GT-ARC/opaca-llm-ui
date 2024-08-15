<script setup>
    import Content from './components/content.vue'
    import { ref, provide } from 'vue'
    import conf from '../config.js'

    const language = ref('GB')
    const backend = ref(conf.BackendDefault)

    provide('language', language)
    provide('backend', backend)
    provide('config', ref(conf))

    function setLanguage(lang){
        language.value = lang;        
    }
    function setBackend(val){
        backend.value = val;
        console.log("BACKEND IS NOW " + val);
    }
</script>

<template>
    <header>
        <div class="col">
            <nav class="navbar navbar-expand-lg" type="light">
                <div class="container-fluid" style="width: 50%;">
                    <img src="./assets/opaca-logo.png" alt="Opaca Logo" height="50"/>
                </div>

                <ul class="navbar-nav me-auto my-2 my-lg-0 navbar-nav-scroll">
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="languageSelector" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                            {{ conf.translations[language].language}}
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
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="backendSelector" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                            Backend
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

    @media (prefers-color-scheme: dark) {
      .navbar {
        background-color: #333;
        color: white;
      }
      .navbar-nav .nav-link {
        color: white;
      }
    }
</style>
