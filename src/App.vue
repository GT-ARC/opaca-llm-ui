<script setup>
    import Content from './components/content.vue'
    import { ref, provide, onMounted } from 'vue'
    import conf from '../config.js'

    const language = ref('GB')

    provide('language', language)
    provide('config', ref(conf))

    function setLanguage(lang){
        language.value = lang;        
    }
</script>

<template>
    <header>
        <div class="col">
            <nav class="navbar fixed-top navbar-expand-lg navbar-light bg-light">
                <div class="container-fluid">
                    <a href="#">
                        <img src="./assets/opaca-logo.png" height="50"/>
                    </a>
                </div>

                <ul class="navbar-nav me-auto my-2 my-lg-0 navbar-nav-scroll" style="--bs-scroll-height: 100px;">
                    <li style="margin-right: 70px;" class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="languageSelector" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                            {{ conf.translations[language].language}}
                        </a>
                        <ul class="dropdown-menu" aria-labelledby="languageSelector">
                            <li @click="setLanguage('DE')"><a class="dropdown-item"><span class="fi fi-de m-3"></span>DE</a></li>
                            <li @click="setLanguage('GB')"><a class="dropdown-item"><span class="fi fi-gb m-3"></span>EN</a></li>
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
</style>
