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
                                <!--<i class="fa fa-wrench me-3"/>-->
                                {{ extension.description }}
                            </button>

                            <!-- extension body -->
                            <div :id="'extension-body-' + containerIndex + '-' + extensionIndex" class="accordion-collapse collapse extension-body"
                                 :aria-labelledby="'extension-header-' + containerIndex + '-' + extensionIndex" :data-bs-parent="'#extensions-accordion-' + containerIndex">
                                <iframe :src="extension.port" />
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
    props: {},
    setup() {
        const { isMobile, screenWidth } = useDevice();
        return { conf, Localizer, SidebarManager, isMobile, screenWidth };
    },
    data() {
        return {
            extraPorts: null,
            isLoading: false,
        };
    },
    methods: {
        async updatePlatformInfo(isPlatformConnected) {
            this.isLoading = true;
            this.extraPorts = isPlatformConnected
                ? await backendClient.getExtraPorts()
                : null;
            this.isLoading = false;
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
</style>