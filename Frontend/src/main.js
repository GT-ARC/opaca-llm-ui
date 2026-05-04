import { createApp } from 'vue'
import "bootstrap/dist/css/bootstrap.min.css"
import "@fortawesome/fontawesome-free/css/all.min.css"
import "primeicons/primeicons.css"

import PrimeVue from "primevue/config"
import Aura from "@primeuix/themes/aura"

import './style.css'
import App from './App.vue'

const app = createApp(App)

app.use(PrimeVue, {
    theme: {
        preset: Aura,
    },
})

app.mount('#app')
