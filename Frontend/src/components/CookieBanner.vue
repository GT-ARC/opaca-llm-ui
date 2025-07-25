<template>
    <div v-if="!isCookieAccepted" class="cookie-banner">
        <p>
            This website uses cookies to associate your message history and settings (stored in the backend) with you.
            Without those cookies, no continued conversation with the LLM is possible. You can chose to either accept the cookies
            for only this browser session (a new session-cookie will be created for each session), or permanently (your message 
            history can be restored if you restart the browser). You can always check, change or revoke this in your browser settings.
        </p>
        <button class="btn btn-secondary" @click="acceptCookies(false)">Accept for this Session</button>
        <button class="btn btn-primary" @click="acceptCookies(true)">Accept Persistently</button>
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
            const max_age = 60 * 60 * 24 * 30; // 30 days
            document.cookie = "cookieConsent=true; max-age=" + max_age;
            if (persistentSession) {
                document.cookie = "persistentSession=true; max-age=" + max_age;
            }
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
