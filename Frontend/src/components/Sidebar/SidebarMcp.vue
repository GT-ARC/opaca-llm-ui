<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div v-if="!isMobile" class="sidebar-title">
        {{ Localizer.get('tooltipSidebarMcp') }}
    </div>

    <div v-if="this.isLoading">
        <i class="fa fa-circle-notch fa-spin me-1" />
        {{ Localizer.get('sidebarMcpLoading') }}
    </div>
    <div v-else-if="!platformMcp || Object.keys(platformMcp).length === 0">
        {{ Localizer.get('sidebarMcpMissing') }}
    </div>
    <div v-else class="flex-row" >
        <div class="accordion text-start" id="mcp-accordion">
            <div v-for="(mcpContent, mcpName, mcpServerIndex) in this.getMcp()" class="accordion-item" :key="mcpServerIndex">

                <!-- header -->
                <h2 class="accordion-header m-0" :id="'mcp-header-' + mcpServerIndex">
                    <button class="accordion-button collapsed"
                            type="button" data-bs-toggle="collapse"
                            :data-bs-target="'#mcp-body-' + mcpServerIndex"
                            aria-expanded="false"
                            :aria-controls="'mcp-body-' + mcpServerIndex">
                        <i class="fa fa-user me-3"/>
                        <strong>{{ mcpName }}</strong>
                    </button>
                </h2>

                <!-- body -->
                <div :id="'mcp-body-' + mcpServerIndex" class="accordion-collapse collapse"
                     :aria-labelledby="'mcp-header-' + mcpServerIndex" :data-bs-parent="'#mcp-accordion'">
                    <div class="list-group list-group-flush" :id="'mcp-accordion-' + mcpServerIndex">
                        <div v-for="(mcp, mcpIndex) in mcpContent" :key="mcpIndex" class="list-group-item">

                            <!-- header -->
                            <button class="mcp-header-button collapsed"
                                    type="button" data-bs-toggle="collapse"
                                    :data-bs-target="'#mcp-body-' + mcpServerIndex + '-' + mcpIndex"
                                    aria-expanded="false"
                                    :aria-controls="'mcp-body-' + mcpServerIndex + '-' + mcpIndex">
                                <i class="fa fa-wrench me-3"/>
                                {{ mcp.name }}
                            </button>

                            <!-- mcp body -->
                            <div :id="'mcp-body-' + mcpServerIndex + '-' + mcpIndex" class="accordion-collapse collapse mcp-body"
                                 :aria-labelledby="'mcp-header-' + mcpServerIndex + '-' + mcpIndex" :data-bs-parent="'#mcp-accordion-' + mcpServerIndex">
                                <p v-if="mcp.description">
                                    <strong>{{ Localizer.get('agentActionDescription') }}:</strong>
                                    {{ mcp.description }}
                                </p>
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
    name: 'SidebarMcp',
    props: {},
    setup() {
        const { isMobile, screenWidth } = useDevice();
        return { conf, Localizer, SidebarManager, isMobile, screenWidth };
    },
    data() {
        return {
            platformMcp: null,
            isLoading: false,
            searchQuery: '',
        };
    },
    methods: {
        async updateMcp(isPlatformConnected) {
            this.isLoading = true;
            this.platformMcp = isPlatformConnected
                ? await backendClient.getMCPs()
                : null;
            this.isLoading = false;
        },

        formatJSON(obj) {
            return JSON.stringify(obj, null, 2)
        },

        getMcp() {
            return Object.keys(this.platformMcp)
                .sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()))
                .filter(mcp => {
                    const matches = (s) => s?.toLowerCase().includes(this.searchQuery.toLowerCase());
                    return matches(mcp) || this.platformMcp[mcp].some(mcp =>
                            matches(mcp.name) || matches(mcp.description)
                    );
                })
                .reduce((acc, mcp) => {
                    acc[mcp] = this.platformMcp[mcp];
                    return acc;
                }, {});
        },
    }
}
</script>

<style scoped>
.mcp-header-button {
    background-color: transparent;
    color: inherit;
    padding: 0 1rem;
    border: none;
    box-shadow: none;
    text-align: left;
    width: 100%;
    font-weight: bold;
}

.mcp-header-button:focus {
    outline: none;
}

.mcp-header-button::after {
    display: none;
}

.mcp-body {
    padding: 0.5rem 0;
}

</style>