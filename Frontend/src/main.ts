import { createApp } from 'vue'
import "bootstrap/dist/css/bootstrap.min.css"
import "@fortawesome/fontawesome-free/css/all.min.css"
import "primeicons/primeicons.css"

import PrimeVue from "primevue/config"
import Aura from "@primeuix/themes/aura"
import {createAuth0} from "@auth0/auth0-vue"

import './style.css'
import App from './App.vue'
import conf from '../config.js';

const app = createApp(App)

app.use(PrimeVue, {
    theme: {
        preset: Aura,
    },
})

if (conf.authEnabled) {
    app.use(createAuth0({
        domain: conf.authDomain,
        clientId: conf.authClientId,
        authorizationParams: {
            redirect_uri: window.location.origin,
            audience: conf.authAudience,
        },
        cacheLocation: "localstorage",
        useRefreshTokens: true,
    }))
}

app.mount('#app')
