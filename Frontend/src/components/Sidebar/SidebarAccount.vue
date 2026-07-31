<template>
<div class="sidebar-account-wrapper">
    <div class="sidebar-menu-item sidebar-avatar-wrapper"
         @click.stop="toggleProfileMenu()"
         :class="{'sidebar-menu-item-select': accountMenuOpen}"
         :title="Localizer.get('sidebar_account')">
         <img v-if="this.isAuthenticated && user?.picture"
              :src="user.picture"
              class="sidebar-avatar"
              alt="User avatar"/>
         <i v-else class="fa fa-user"/>
    </div>

    <div v-if="accountMenuOpen"
         class="sidebar-account-menu"
         @click.stop>
        <button type="button"
                class="sidebar-account-menu-button"
                @click="handleProfileAuthClick()">
            <i :class="['fa', this.isAuthenticated ? 'fa-right-from-bracket' : 'fa-right-to-bracket']"/>
            <span>{{ this.isAuthenticated ? Localizer.get('account_logout') : Localizer.get('account_login') }}</span>
        </button>
        <button type="button"
                class="sidebar-account-menu-button"
                @click="handleProfileSettingsClick()">
            <i class="fa fa-gear"/>
            <span>{{ Localizer.get('settings_menu') }}</span>
        </button>
    </div>
</div>
</template>

<script>
import Localizer from "../../Localizer.ts";
import {useAuthentication} from "../../useAuthentication.ts";
import backendClient from "../../utils.ts";

export default {
    name: "SidebarAccount",
    emits: [
        'updateUserInfo',
        'updateMcpServers',
    ],
    setup() {
        const { loginWithPopup, logout, user, isAuthenticated } = useAuthentication();
        return { Localizer, loginWithPopup, logout, user, isAuthenticated };
    },
    data() {
        return {
            accountMenuOpen: false,
        }
    },
    methods: {
        toggleProfileMenu() {
            this.accountMenuOpen = !this.accountMenuOpen;
        },

        closeProfileMenu() {
            this.accountMenuOpen = false;
        },

        async handleProfileAuthClick() {
            if (this.isAuthenticated) {
                // Handle backend logout before auth0 redirect to save updated cookie
                await backendClient.user_logout()
                // This will reset the "session_id" cookie, there should NEVER be another call here between these two lines
                await this.logout({ logoutParams: { returnTo: window.location.origin } });
            } else {
                try {
                    await this.loginWithPopup({authorizationParams: {screen_hint: 'signup'}})
                } catch (error) {
                    // Only show an error in the console, if the popup was not closed
                    if (error.error === 'cancelled') return;
                    console.error("Auth0 login failed: ", error)
                }
                // Update the sidebar information to reflect the new user state
                this.$emit('updateUserInfo');
                // MCP Servers need to be updated separately
                this.$emit('updateMcpServers');
                // NOTE: This should not happen on logout, since it will refresh the page and
                // update the information anyway. Otherwise an error is thrown
            }
        },

        async handleProfileSettingsClick() {
            alert("Not implemented yet.")
        },
    },
    mounted() {
        document.addEventListener('click', this.closeProfileMenu);
    },
    beforeUnmount() {
        document.removeEventListener('click', this.closeProfileMenu);
    },
}
</script>

<style scoped>

.sidebar-account-wrapper {
    position: relative;
}

.sidebar-account-menu {
    position: absolute;
    left: calc(100% + 0.5rem);
    bottom: 0;
    min-width: 10rem;
    padding: 0.35rem;
    background-color: var(--surface-color);
    border: 1px solid var(--border-color);
    border-radius: var(--bs-border-radius);
    z-index: 1001;
}

.sidebar-account-menu-button {
    width: 100%;
    min-height: 2.25rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.45rem 0.65rem;
    border: 0;
    border-radius: var(--bs-border-radius-sm);
    background: transparent;
    color: var(--text-primary-color);
    text-align: left;
    white-space: nowrap;
}

.sidebar-account-menu-button:hover {
    background-color: var(--background-color);
    color: var(--primary-color);
}

.sidebar-account-menu-button i {
    width: 1rem;
    text-align: center;
}

.sidebar-avatar-wrapper {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
}

.sidebar-avatar {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    object-fit: cover;
}

</style>