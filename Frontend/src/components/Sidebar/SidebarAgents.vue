<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div v-if="!isMobile" class="sidebar-title">
        {{ Localizer.get('tooltipSidebarAgents') }}
    </div>

    <div v-if="platformActions"
         class="my-2">
        <input
            type="text"
            class="form-control"
            :placeholder="Localizer.get('searchAgentsPlaceholder')"
            v-model="this.searchQuery"
        />
    </div>

    <div v-if="this.isLoading">
        <i class="fa fa-circle-notch fa-spin me-1" />
        {{ Localizer.get('sidebarAgentsLoading') }}
    </div>
    <div v-else-if="!platformActions">
        {{ Localizer.get('sidebarAgentsMissing') }}
    </div>
    <div v-else class="flex-row" >
        <div class="accordion text-start" id="agents-accordion">

            <div v-for="{containerId, agents, image} in this.getContainers()" :key="containerId"
                 class="accordion-item">

                <!-- Container Header -->
                <h2 :id="`container-accordion-header-${containerId}`"
                    class="accordion-header">
                    <button class="accordion-button collapsed"
                            type="button" data-bs-toggle="collapse"
                            :data-bs-target="`#container-accordion-body-${containerId}`"
                            :aria-controls="`container-accordion-body-${containerId}`"
                            aria-expanded="false">
                        <i class="fa fa-box me-3"/>
                        <strong>{{ image?.imageName ?? containerId }}</strong>
                    </button>
                </h2>

                <!-- Container Body -->
                <div :id="`container-accordion-body-${containerId}`"
                     class="accordion-collapse collapse ps-1"
                     :data-bs-parent="'#agents-accordion'"
                     :aria-labelledby="`container-accordion-header-${containerId}`">
                    <div :id="`agents-accordion-${containerId}`"
                         class="list-group list-group-flush" >

                        <div v-for="({agentId, actions}, agentIndex) in agents"
                             class="accordion-item" :key="agentIndex">

                            <!-- Agent Header -->
                            <h2 class="accordion-header" :id="`agents-accordion-header-${containerId}-${agentIndex}`">
                                <button class="accordion-button collapsed"
                                        type="button" data-bs-toggle="collapse"
                                        :data-bs-target="`#agents-accordion-body-${containerId}-${agentIndex}`"
                                        aria-expanded="false"
                                        :aria-controls="`agents-accordion-body-${containerId}-${agentIndex}`">
                                    <i class="fa fa-user me-3"/>
                                    <strong>{{ agentId }}</strong>&nbsp;({{ actions?.length }})
                                </button>
                            </h2>

                            <!-- Agent Body -->
                            <div :id="`agents-accordion-body-${containerId}-${agentIndex}`"
                                 class="accordion-collapse collapse ps-1"
                                 :aria-labelledby="`agents-accordion-header-${containerId}-${agentIndex}`"
                                 :data-bs-parent="`#agents-accordion-${containerId}`">
                                <div :id="`actions-accordion-${containerId}-${agentIndex}`"
                                     class="list-group list-group-flush" >
                                    <div v-for="(action, actionIndex) in actions" :key="actionIndex" class="list-group-item p-0">

                                        <!-- Action Header -->
                                        <h2 :id="`action-accordion-header-${containerId}-${agentIndex}-${actionIndex}`"
                                            class="accordion-header">
                                            <button class="accordion-button collapsed"
                                                    type="button" data-bs-toggle="collapse"
                                                    :data-bs-target="`#action-accordion-body-${containerId}-${agentIndex}-${actionIndex}`"
                                                    :aria-controls="`action-accordion-body-${containerId}-${agentIndex}-${actionIndex}`"
                                                    aria-expanded="false">
                                                <i class="fa fa-wrench me-3"/>
                                                {{ action.name }}
                                            </button>
                                        </h2>

                                        <!-- Action Body -->
                                        <div :id="`action-accordion-body-${containerId}-${agentIndex}-${actionIndex}`"
                                             class="accordion-collapse collapse action-body p-2"
                                             :aria-labelledby="`action-accordion-header-${containerId}-${agentIndex}-${actionIndex}`"
                                             :data-bs-parent="`#actions-accordion-${containerId}-${agentIndex}`">
                                            <p v-if="action.description">
                                                <strong>{{ Localizer.get('agentActionDescription') }}:</strong>
                                                {{ action.description }}
                                            </p>
                                            <strong>{{ Localizer.get('agentActionParameters') }}:</strong>
                                            <pre class="json-box">{{ formatJSON(action.parameters) }}</pre>
                                            <strong>{{ Localizer.get('agentActionResult') }}:</strong>
                                            <pre class="json-box">{{ formatJSON(action.result) }} </pre>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>

            </div>

            <!-- REMOVED STUFF HERE -->
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
    name: 'SidebarAgents',
    props: {
        isPlatformConnected: Boolean,
    },
    setup() {
        const { isMobile, screenWidth } = useDevice();
        return { conf, Localizer, SidebarManager, isMobile, screenWidth };
    },
    data() {
        return {
            platformActions: null,
            isLoading: false,
            searchQuery: '',
        };
    },
    methods: {
        async updatePlatformInfo() {
            this.isLoading = true;
            this.platformActions = this.isPlatformConnected
                ? await backendClient.getActions()
                : null;
            this.isLoading = false;
        },

        formatJSON(obj) {
            return JSON.stringify(obj, null, 2);
        },

        getContainers() {
            const matches = (s) => {
                if (!this.searchQuery) return true;
                return s?.toLowerCase().includes(this.searchQuery.toLowerCase());
            }
            if (!this.platformActions) return [];
            let containers = JSON.parse(JSON.stringify(this.platformActions));

            // sort containers/agents/actions alphabetically
            containers.sort((a, b) => a.image.imageName.toLowerCase().localeCompare(b.image.imageName.toLowerCase()));
            containers.forEach(container => {
                container.agents.sort((a, b) => a.agentId.toLowerCase().localeCompare(b.agentId.toLowerCase()));
                container.agents.forEach(agent => {
                    agent.actions.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
                });
            });

            // filter for search query
            containers = containers.filter(container => {
                if (matches(container.image.imageName)) return true;
                container.agents = container.agents.filter(agent => {
                    if (matches(agent.agentId)) return true;
                    agent.actions = agent.actions.filter(action => {
                        return matches(action.name) || matches(action.description);
                    });
                    return agent.actions.length > 0;
                });
                return container.agents.length > 0;
            });

            return containers;
        },
    },
    watch: {
        isPlatformConnected() {
            this.updatePlatformInfo();
        }
    }
}
</script>

<style scoped>
.accordion-item {
    border: none;
    margin-bottom: 0;
}

.accordion-header {
    margin-bottom: 0.25rem;
}

.list-group-item {
    border: none;
}

.action-body {
    padding: 0.5rem 0;
}

.json-box {
    background-color: var(--surface-color);
    color: var(--text-primary-color);
    padding: 0.75rem;
    border-radius: var(--bs-border-radius);
    white-space: pre-wrap; /* Ensures line breaks */
    font-family: monospace;
}
</style>