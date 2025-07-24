<template>
    <div v-if="!isCookieAccepted" class="cookie-banner">
        <p>This website uses cookies to ensure you get the best experience on our website.</p>
        <button @click="acceptCookies(false)">Accept for this Session</button>
        <button @click="acceptCookies(true)">Accept Persistently</button>
    </div>
</template>

<script>
export default {

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

        acceptCookies(persistentSession) {
            document.cookie = "cookieConsent=true; max-age=" + 60 * 60 * 24 * 30; // 30 days
            if (persistentSession) {
                document.cookie = "persistentSession=true; max-age=" + 60 * 60 * 24 * 30; // 30 days
            }
            this.isCookieAccepted = true;
        },

        agreedToPersistentSession() {
            return document.cookie.split(';').some((item) => item.trim().startsWith('persistentSession='));
        }
    },
};
</script>

<style>
.cookie-banner {

}
</style>
