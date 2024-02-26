<script setup>
    //import Buttons from './components/UserButtons.vue';
    import Interactive from './components/content.vue'
    //import PhotoCarousel from "./components/PhotoCarousel.vue";
    /* import { ModalsContainer } from 'vue-final-modal' */
    import { ref, provide, onMounted } from 'vue'
    import conf from '../config.js'
    //import ClickModal from './components/modalClick.vue'
    //import StartedModal from './components/StartedModal.vue'
    //import VIPModal from './components/modalVip.vue'
    //import FlagModal from './components/modalFlag.vue'
    //import Flags from './components/flags.vue'
    import axios from 'axios'

    import "/node_modules/flag-icons/css/flag-icons.min.css";
    import config from '../config.js';

    const tabs = { Interactive };
    const currentTab = ref('Interactive');
    const language = ref('DE')
    //const showModalClick = ref(false);
    //const showModalStart = ref(false);
    //const showModalFlag = ref(false);
    const showVIPModal = ref(false);
    const vipActive = ref(false);
    const WayID = ref(1);
    const BgImg = ref ('src/assets/flags/de.png');
    const WayActive = ref(false);

    const WaySrc = ref('src/assets/ZEKI-Wegfotos/aal_roomplan.png')
    provide('imgSrc', WaySrc)
    provide('language', language)
    provide('vipActive', vipActive)
    provide('config', ref(conf))
    provide('WayActive', WayActive)

    async function sendBackend(roomID) {
        console.log('sendBackend called with room: ' + roomID);
    }

    function setLanguage(lang){
        language.value = lang;        
    }
</script>

<!-- Actual Page Design -->
<template>
    <div>
        <div class="col background">
            <component :is="tabs[currentTab]" class="tab" @clickModal="setRoomID" @reset="resetHistory()" @flags="setFlagID" @vip="showVIPModal=true"></component>
        </div>
    
        <div class="col">
        
            <nav class="navbar fixed-bottom navbar-expand-lg navbar-light bg-light">
                <div class="container-fluid">
                    <a href="#">
                        <img src="./assets/ZEKI-Logo.png" height="70" @click="sendBackend(900)"/>
                    </a>
        
                    <!--  Component switching DropUpMenu for changeing between Buttons and ChatGPT assisted Voice Interface -->
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

    .icon {
        margin: 1em;
    }
</style>
