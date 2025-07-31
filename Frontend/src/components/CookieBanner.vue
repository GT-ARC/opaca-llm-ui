<template>
    <div v-if="!isCookieAccepted" class="cookie-banner">
        <p>
            {{ Localizer.get('cookiesText') }}
        </p>         
        <button class="btn btn-primary" @click="acceptCookies()">{{ Localizer.get('cookiesAccept') }}</button>
    </div>
</template>

<script>
import Localizer from "./../Localizer.js"

export default {
    setup() {
        return { Localizer };
    },

    data() {
        return {
            isCookieAccepted: false,
        };
    },

    mounted() {
        this.checkCookieConsent();
    },

    methods: {

        checkCookieConsent() {
            this.isCookieAccepted = document.cookie.split(';').some((item) => item.trim().startsWith('cookieConsent='));
        },

        acceptCookies() {
            const max_age = 60 * 60 * 24 * 365 * 10; // 10 years...
            document.cookie = "cookieConsent=true; max-age=" + max_age;
            this.isCookieAccepted = true;
        },
    },
};
</script>

<style>
.cookie-banner {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 1em;
    margin: 1em;
    border-radius: 1em;
    text-align: center;
    background-color: rgba(196, 196, 196, 0.5); /* Transparent overlay */
    z-index: 9999; /* Should appear above all other items */
}
</style>
