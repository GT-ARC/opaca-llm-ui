<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div v-if="!isMobile" class="sidebar-title">
        {{ Localizer.get('tooltipSidebarExtensions') }}
    </div>

    <div v-if="this.isLoading">
        <i class="fa fa-circle-notch fa-spin me-1" />
        {{ Localizer.get('sidebarExtensionsLoading') }}
    </div>
    <div v-else-if="!this.extraPorts || Object.keys(this.extraPorts).length === 0">
        {{ Localizer.get('sidebarExtensionsMissing') }}
    </div>
    <div v-else class="flex-row" >

        <div v-if="this.maximized != null" class="extension-expand-overlay"
            @click="this.maximized = null"
            @keyup.esc="this.maximized = null">
            <iframe :src="this.maximized" class="extension-expand-window" @click.stop />
        </div>

        <div class="accordion text-start" id="containers-accordion">
            <div v-for="(container, containerIndex) in this.extraPorts" class="accordion-item" :key="containerIndex">

                <!-- header -->
                <h2 class="accordion-header m-0" :id="'accordion-header-' + containerIndex">
                    <button class="accordion-button collapsed"
                            type="button" data-bs-toggle="collapse"
                            :data-bs-target="'#accordion-body-' + containerIndex"
                            aria-expanded="false"
                            :aria-controls="'accordion-body-' + containerIndex">
                        <i class="fa fa-puzzle-piece me-3"/>
                        <strong>{{ container.container }}</strong>
                    </button>
                </h2>

                <!-- body -->
                <div :id="'accordion-body-' + containerIndex" class="accordion-collapse collapse"
                     :aria-labelledby="'accordion-header-' + containerIndex" :data-bs-parent="'#containers-accordion'">
                    <div class="list-group list-group-flush" :id="'extensions-accordion-' + containerIndex">
                        <div v-for="(extension, extensionIndex) in container.extraPorts" :key="extensionIndex" class="list-group-item">

                            <!-- header -->
                            <button class="extension-header-button collapsed"
                                    type="button" data-bs-toggle="collapse"
                                    :data-bs-target="'#extension-body-' + containerIndex + '-' + extensionIndex"
                                    aria-expanded="false"
                                    :aria-controls="'extension-body-' + containerIndex + '-' + extensionIndex">
                                {{ extension.description }}
                                <i class="fa fa-expand extension-expand-button"
                                    @click.stop="this.maximized = getFullUrl(extension.port, container.token)"
                                    :title="Localizer.get('tooltipExpandExtension')"
                                />
                                <i class="fa fa-refresh extension-expand-button"
                                    @click.stop="updatePlatformInfo(this.extraPorts != null)"
                                    title="Refresh"
                                />
                            </button>

                            <!-- extension body -->
                            <div :id="'extension-body-' + containerIndex + '-' + extensionIndex" class="accordion-collapse collapse extension-body"
                                 :aria-labelledby="'extension-header-' + containerIndex + '-' + extensionIndex" :data-bs-parent="'#extensions-accordion-' + containerIndex">
                                <iframe :src="getFullUrl(extension.port, container.token)" />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

</template>


<script>
import conf from '../../../config.js';
import Localizer from "../../Localizer.js";
import SidebarManager from "../../SidebarManager.js";
import { useDevice } from "../../useIsMobile.js";
import backendClient from "../../utils.js";

export default {
    name: 'SidebarExtensions',
    props: {
        isPlatformConnected: Boolean,
    },
    setup() {
        const { isMobile, screenWidth } = useDevice();
        return { conf, Localizer, SidebarManager, isMobile, screenWidth };
    },
    data() {
        return {
            extraPorts: null,
            isLoading: false,
            maximized: null,
        };
    },
    methods: {
        async updatePlatformInfo() {
            this.isLoading = true;
            this.extraPorts = this.isPlatformConnected
                ? await backendClient.getExtraPorts()
                : null;
            this.isLoading = false;
        },

        getFullUrl(extensionPort, token) {
            return token ? `${extensionPort}?token=${token}` : extensionPort;
        }
    },

    watch: {
        isPlatformConnected() {
            this.updatePlatformInfo();
        },
    }
}
</script>

<style scoped>
.extension-header-button {
    background-color: transparent;
    color: inherit;
    padding: 0 1rem;
    border: none;
    box-shadow: none;
    text-align: left;
    width: 100%;
    font-weight: bold;
}

.extension-header-button:focus {
    outline: none;
}

.extension-header-button::after {
    display: none;
}

.extension-body {
    padding: 0.5rem 0;
}

/* the following are copied from chat tab and search chat overlay... */
.extension-expand-button {
    flex: 0 0 auto;
    width: 2rem;
    height: 2rem;
    padding: 0;
    aspect-ratio: 1 / 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    align-self: flex-end;
    border-radius: 1rem !important;
    cursor: pointer;
}

.extension-expand-overlay {
    position: fixed;
    top: 50px;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0,0,0,0.5); /* backdrop dim */
    z-index: 3000;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding-top: 1rem;
    pointer-events: auto; /* blocks clicks behind */
}

.extension-expand-window {
    width: 100%;
    height: 100%;
    padding: 1rem;
    max-width: max(95vw, 800px);
    max-height: max(85vh, 800px);
    border: 1px solid var(--border-color);
    border-radius: 1rem;
    background-color: var(--background-color);
    color: var(--text-primary-color);
}
</style>