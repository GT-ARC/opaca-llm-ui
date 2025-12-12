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

                        <!-- Delete Button -->
                        <i
                            class="fa fa-trash delete-icon"
                            @click.stop="this.deleteMcp(mcpName)"
                            title="Delete MCP Server"
                        />
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
    <div class="accordion-button d-flex align-items-center justify-content-center mb-2 cursor-pointer"
         @click.stop="addMcp()">
        <i class="fa fa-plus me-2"></i>
        <span>{{ Localizer.get('addMcp')}}</span>
    </div>

    <InputDialogue ref="input" />
</div>

</template>


<script>
import conf from '../../../config.js';
import Localizer from "../../Localizer.js";
import SidebarManager from "../../SidebarManager.js";
import { useDevice } from "../../useIsMobile.js";
import backendClient from "../../utils.js";
import InputDialogue from '../InputDialogue.vue';

export default {
    name: 'SidebarMcp',
    components: {InputDialogue},
    props: {
        isPlatformConnected: Boolean,
    },
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

        async addMcp() {
            await this.$refs.input.showDialogue(
                Localizer.get('addMcp'),
                null,
                null,
                {
                    mcpJson: {type: "textarea", label: "MCP Server", default: "" },
                }, 
                async (values) => {
                    if (values != null) {
                        try {
                            const data = JSON.parse(values.mcpJson);
                            await backendClient.addMcp({"content": data});
                            await this.updateMcp(true);
                        } catch {
                            await this.$refs.input.showInfo("MCP Server", "Please enter valid MCP JSON");
                        }
                    }
                }
            );
            
        },

        async deleteMcp(mcpName) {
            await this.$refs.input.showDialogue(
                "Delete MCP server?", null, null, {}, 
                async (values) => {
                    if (values != null) {
                        await backendClient.deleteMcp({"name": mcpName});
                        await this.updateMcp(true);
                    }
                }
            );
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
        }
    },
    watch: {
        isPlatformConnected() {
            this.updateMcp(this.isPlatformConnected);
        }
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

.delete-icon {
    position: absolute;
    width: 2em;
    height: 2em;
    right: 2rem;
    top: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    transform: translateY(-50%);
    border-radius: var(--bs-border-radius-lg);
    color: var(--text-danger-color);
    cursor: pointer;
    transition: color 0.2s ease;
}

.delete-icon:hover {
    color: var(--primary-color);
    background-color: var(--background-color);
}

</style>