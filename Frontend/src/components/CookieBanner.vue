<template>
    <div v-if="!isCookieAccepted" class="cookie-banner">
        <p>
            This website uses a cookies to associate your message history and settings (stored in the backend) with you.
            Without those cookies, no continued conversation with the LLM is possible. You can accept to either accept the cookie
            for only this browser session (a new session-cookie will be created for each session), or permanently (your message 
            history can be restored if you restart the browser). You can always check, change or revoke this in your browser settings.
        </p>
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
    },
};
</script>

<style>
.cookie-banner {

}
</style>
