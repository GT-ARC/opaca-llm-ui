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
      <div class="site-logo">
        <img style="width: 300px;" src="./assets/opaca-logo.png" alt="logo">
      </div>
    </header>

    <div>
        <div class="col background">
            <component :is="Content" class="tab" @reset="resetHistory()" />
        </div>
        <div class="col">
            <nav class="navbar fixed-bottom navbar-expand-lg navbar-light bg-light">
                <div class="container-fluid">
                    <a href="#">
                        <img src="./assets/ZEKI-Logo.png" height="70"/>
                    </a>
        
                    <!--
                    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarScroll" aria-controls="navbarScroll" aria-expanded="false" aria-label="Toggle navigation">
                        <span class="navbar-toggler-icon"></span>
                    </button>
                    <div class="collapse navbar-collapse" id="navbarScroll">
                        <ul class="navbar-nav me-auto my-2 my-lg-0 navbar-nav-scroll" style="--bs-scroll-height: 100px;">
                            <li class="nav-item dropup">
                                <a class="nav-link dropdown-toggle" href="#" id="navbarScrollingDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                                    Wayfinding
                                </a>
                                <ul class="dropdown-menu" aria-labelledby="navbarScrollingDropdown">
                                    <li v-for="(_, tab) in tabs" :key="tab" :class="['tab-button', { active: currentTab === tab }]" @click="currentTab = tab">
                                        <a class="dropdown-item">{{ tab }}</a>
                                    </li>
                                </ul>
                            </li>
                        </ul>
                    </div>
                    -->
                </div>
            </nav>
        </div>
    </div>
</template>


<style scoped>
    #BigBox {
        display: flex;
        flex-direction: column;
        margin: 0px;
        padding: 0px;
        width: 100%;
    }

    header {
      background-color: #fff;
      width: 100%;
      height: 100px;
      display: flex;
      align-items: center;
    }

    .site-logo {
      margin-left: 20px;
    }
</style>
