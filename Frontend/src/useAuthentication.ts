import {computed} from "vue";
import {useAuth0} from "@auth0/auth0-vue";
import conf from '../config.js';

/* Helper wrapper to turn authentication on and off */

export function useAuthentication() {
    if (!conf.authEnabled) {
        return {
            isAuthenticated: computed(() => false),
            user: computed(() => null),
            loginWithPopup: async () => {},
            logout: async () => {},
            getAccessTokenSilently: async () => null
        };
    }

    if (!conf.authAudience) {
        throw new Error("Unable to start. You need to set 'VITE_AUTH_AUDIENCE' when authentication is enabled.")
    } else if (!conf.authClientId) {
        throw new Error("Unable to start. You need to set 'VITE_AUTH_CLIENT_ID' when authentication is enabled.")
    } else if (!conf.authDomain) {
        throw new Error("Unable to start. You need to set 'VITE_AUTH_DOMAIN' when authentication is enabled")
    }

    return useAuth0();
}