<template>
    <div v-if="!isCookieAccepted" class="cookie-banner">
        <p>
            This website uses cookies to associate your chat session (message history and settings) with you.
            This cookie is kept for 30 days after the last interaction, or until manually deleted.
            The session data is stored in the backend and the messages are sent to the configured LLM.
            The session data will be deleted from the backend when the cookie expires, or by clicking the "Reset" button.
            The cookies and session data are used for the sole purpose of the chat interaction.
            Without, no continued conversation with the LLM is possible.
            By using this website, you consent to the above policy.
        </p>
        <button class="btn btn-primary" @click="acceptCookies()">Accept Cookies</button>
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
