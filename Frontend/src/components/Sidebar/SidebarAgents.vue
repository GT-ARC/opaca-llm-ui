<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div v-if="!isMobile" class="sidebar-title">
        {{ Localizer.get('tooltipSidebarAgents') }}
    </div>

    <InputDialogue ref="input"/>

    <div v-if="platformActions && Object.keys(platformActions).length > 0"
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
    <div v-else-if="!platformActions || Object.keys(platformActions).length === 0">
        {{ Localizer.get('sidebarAgentsMissing') }}
    </div>
    <div v-else class="flex-row" >
        <div class="accordion text-start" id="agents-accordion">
            <div v-for="(actions, agent, agentIndex) in this.getAgents()" class="accordion-item" :key="agentIndex">

                <!-- header -->
                <h2 class="accordion-header m-0" :id="'accordion-header-' + agentIndex">
                    <button class="accordion-button collapsed"
                            type="button" data-bs-toggle="collapse"
                            :data-bs-target="'#accordion-body-' + agentIndex"
                            aria-expanded="false"
                            :aria-controls="'accordion-body-' + agentIndex">
                        <i class="fa fa-user me-3"/>
                        <strong>{{ agent }}</strong>&nbsp;({{ actions.length }})
                    </button>
                </h2>

                <!-- body -->
                <div :id="'accordion-body-' + agentIndex" class="accordion-collapse collapse"
                     :aria-labelledby="'accordion-header-' + agentIndex" :data-bs-parent="'#agents-accordion'">
                    <div class="list-group list-group-flush" :id="'actions-accordion-' + agentIndex">
                        <div v-for="(action, actionIndex) in actions" :key="actionIndex" class="list-group-item">

                            <!-- header -->
                            <button class="action-header-button collapsed"
                                    type="button" data-bs-toggle="collapse"
                                    :data-bs-target="'#action-body-' + agentIndex + '-' + actionIndex"
                                    aria-expanded="false"
                                    :aria-controls="'action-body-' + agentIndex + '-' + actionIndex">
                                <i class="fa fa-wrench me-3"/>
                                {{ action.name }}

                                <i class="fa fa-gears"
                                    @click.stop="invokeAction(agent, action.name, action.parameters)"
                                    title="Invoke"
                                />
                            </button>

                            <!-- action body -->
                            <div :id="'action-body-' + agentIndex + '-' + actionIndex" class="accordion-collapse collapse action-body"
                                 :aria-labelledby="'action-header-' + agentIndex + '-' + actionIndex" :data-bs-parent="'#actions-accordion-' + agentIndex">
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

</template>


<script>
import conf from '../../../config.js';
import Localizer from "../../Localizer.js";
import SidebarManager from "../../SidebarManager.js";
import { useDevice } from "../../useIsMobile.js";
import backendClient from "../../utils.js";
import InputDialogue from '../InputDialogue.vue';

export default {
    name: 'SidebarAgents',
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
            return JSON.stringify(obj, null, 2)
        },

        getAgents() {
            return Object.keys(this.platformActions)
                .sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()))
                .filter(agent => {
                    const matches = (s) => s?.toLowerCase().includes(this.searchQuery.toLowerCase());
                    return matches(agent) || this.platformActions[agent].some(action => 
                            matches(action.name) || matches(action.description)
                    );
                })
                .reduce((acc, agent) => {
                    acc[agent] = this.platformActions[agent];
                    return acc;
                }, {});
        },
        async invokeAction(agent, action, schema) {
            const types = {"string": "text", "boolean": "checkbox", "integer": "number", "number": "number"};
            await this.$refs.input.showDialogue(
                "Invoke Action",
                `${agent}--${action}`,
                null,
                Object.fromEntries(
                    Object.entries(schema).map(([k, v]) => [k, {type: types[v.type] ?? "textarea"}])
                ),
                async values => {
                    // JSON-parse non-primitive inputs
                    for (var v in values) {
                        if (types[schema[v].type] === undefined) {
                            values[v] = JSON.parse(values[v]);
                        }
                    }
                    // TODO container login? SHOULD work out-of-the-box if we move the container-login login in the backend to opaca-client instead of abstract agent?
                    var res = await backendClient.invokeAction(agent, action, values);
                    await this.$refs.input.showInfo("Result", JSON.stringify(res));
                }
            );

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
.action-header-button {
    background-color: transparent;
    color: inherit;
    padding: 0 1rem;
    border: none;
    box-shadow: none;
    text-align: left;
    width: 100%;
    font-weight: bold;
}

.action-header-button:focus {
    outline: none;
}

.action-header-button::after {
    display: none;
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