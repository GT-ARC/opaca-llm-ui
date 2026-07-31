<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div class="sidebar-title">
        {{ Localizer.get('sidebar_extensions') }}
        <i class="fa fa-refresh ms-auto sidebar-title-action sidebar-title-action-secondary"
           :class="{ disabled: this.isLoading }"
           :aria-disabled="this.isLoading"
           @click.stop="updatePlatformInfo()"
           :title="Localizer.get('extensions_refresh')" />
    </div>

    <div v-if="this.isLoading">
        <i class="fa fa-circle-notch fa-spin me-1" />
        {{ Localizer.get('extensions_loading') }}
    </div>
    <div v-else-if="!this.extraPorts || Object.keys(this.extraPorts).length === 0"
         class="sidebar-empty-state">
        {{ Localizer.get('extensions_missing') }}
    </div>
    <div v-else class="flex-row" >

        <div v-if="this.maximized != null" class="extension-expand-overlay"
            @click="this.maximized = null"
            @keyup.esc="this.maximized = null">
            <iframe :src="this.maximized" class="extension-expand-window" @click.stop />
        </div>

        <AppAccordion
            id="containers-accordion"
            class="text-start"
            :items="this.extraPorts"
            :get-key="getContainerKey"
        >
            <template #header="{ item: container }">
                <i class="fa fa-puzzle-piece me-3"/>
                <strong>{{ container.container }}</strong>
            </template>

            <template #body="{ item: container, index: containerIndex }">
                <AppAccordion
                    :id="`extensions-accordion-${containerIndex}`"
                    :items="container.extraPorts"
                    :get-key="getExtensionKey"
                    variant="nested"
                >
                    <template #header="{ item: extension }">
                        <span class="flex-grow-1">{{ extension.description }}</span>
                        <span class="section-actions">
                            <i class="fa fa-expand click-icon"
                               @click.stop="this.maximized = extension.fullUrl"
                               :title="Localizer.get('extensions_expand')" />
                        </span>
                    </template>

                    <template #body="{ item: extension }">
                        <div class="extension-body">
                            <iframe :src="extension.fullUrl" />
                        </div>
                    </template>
                </AppAccordion>
            </template>
        </AppAccordion>
    </div>
</div>

</template>


<script>
import Localizer from "../../Localizer.js";
import { useDevice } from "../../useIsMobile.js";
import backendClient from "../../utils.js";
import AppAccordion from '../AppAccordion.vue';

export default {
    name: 'SidebarExtensions',
    components: {AppAccordion},
    props: {
        isPlatformConnected: Boolean,
    },
    setup() {
        const { isMobile } = useDevice();
        return { Localizer, isMobile };
    },
    data() {
        return {
            extraPorts: null,
            isLoading: false,
            maximized: null,
        };
    },
    methods: {
        getContainerKey(container, index) {
            const urls = container.extraPorts
                ?.map(extension => extension.fullUrl)
                .join('|');
            return `${container.container}-${urls || index}`;
        },

        getExtensionKey(extension, index) {
            return extension.fullUrl ?? `${extension.description}-${index}`;
        },

        async updatePlatformInfo() {
            this.isLoading = true;
            this.extraPorts = this.isPlatformConnected
                ? await backendClient.getExtraPorts()
                : null;
            this.isLoading = false;
        },
    },

    watch: {
        isPlatformConnected() {
            this.updatePlatformInfo();
        },
    }
}
</script>

<style scoped>
.extension-body {
    padding: 0.5rem 0;
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
