<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div v-if="!isMobile" class="sidebar-title">
        {{ Localizer.get('sidebar_agents') }}
    </div>

    <InputDialogue ref="input"/>

    <div v-if="this.isLoading">
        <i class="fa fa-circle-notch fa-spin me-1" />
        {{ Localizer.get('agents_loading') }}
    </div>
    <div v-else-if="!platformContainers || platformContainers.length === 0">
        {{ Localizer.get('agents_missing') }}
    </div>
    <div v-else class="flex-row" >
        <input
            type="text"
            class="form-control my-2"
            :placeholder="Localizer.get('agents_search')"
            v-model="this.searchQuery"
        />
        <div class="accordion text-start" id="agents-accordion">

            <div v-for="{containerId, agents, image} in this.getContainers()" :key="containerId"
                 class="accordion-item">

                <!-- Container Header -->
                <h2 :id="`container-accordion-header-${containerId}`"
                    class="accordion-header">
                    <button class="accordion-button containers-header collapsed"
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
                            <h2 :id="`agents-accordion-header-${containerId}-${agentIndex}`"
                                class="accordion-header">
                                <button class="accordion-button agents-header collapsed"
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
                                            <button class="accordion-button actions-header collapsed"
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
                                            <p class="invoke" @click.stop="invokeAction(agentId, action.name, action.parameters)">
                                                <strong>{{ Localizer.get('agents_invoke') }}</strong>
                                                <i class="fa fa-circle-play mx-2"/>
                                            </p>
                                            <p v-if="action.description">
                                                <strong>{{ Localizer.get('agents_description') }}:</strong>
                                                {{ action.description }}
                                            </p>
                                            <strong>{{ Localizer.get('agents_parameters') }}:</strong>
                                            <pre class="json-box">{{ formatJSON(action.parameters) }}</pre>
                                            <strong>{{ Localizer.get('agents_result') }}:</strong>
                                            <pre class="json-box">{{ formatJSON(action.result) }} </pre>
                                        </div>

                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <button class="accordion-button align-items-center mb-2"
         @click.stop="addContainer()">
        <i class="fa fa-plus me-2"></i>
        <span>{{ Localizer.get("agents_deploy") }}</span>
    </button>
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
            platformContainers: null,
            isLoading: false,
            searchQuery: '',
        };
    },
    methods: {
        async updatePlatformInfo() {
            this.isLoading = true;
            this.platformContainers = this.isPlatformConnected
                ? await backendClient.getContainers()
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
            if (!this.platformContainers) return [];

            // Create local deep-copy of the container data
            let containers = JSON.parse(JSON.stringify(this.platformContainers));

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

        async addContainer() {
            await this.$refs.input.showDialogue(
                Localizer.get("agents_deploy"),
                Localizer.get("agents_deploy_hint"),
                null,
                {
                    image: { type: "text", label: "Image Name" },
                    json: { type: "textarea", label: "Post Container JSON", default: "" },
                },
                async values => {
                    var postContainer = values.json;
                    if (! postContainer || postContainer === "") {
                        postContainer = {image: {imageName: values.image}};
                    }
                    await backendClient.deployContainer(postContainer);
                }
            );
        },

        async invokeAction(agent, action, schema) {
            const types = {"string": "text", "boolean": "checkbox", "integer": "number", "number": "number"};
            await this.$refs.input.showDialogue(
                Localizer.get('agents_invoke'),
                `**Agent:** ${agent}\n\n**Action:** ${action}`,
                null,
                Object.fromEntries(
                    Object.entries(schema).map(([k, v]) => [k, {type: types[v.type] ?? "textarea", label: `${k} (${this.typeHint(v)})`}])
                ),
                async values => {
                    // JSON-parse non-primitive inputs --> parse errors are shown in error label
                    var parameters = Object.fromEntries(
                        Object.entries(values).map(([k, v]) => [k, types[schema[k].type] === undefined ? JSON.parse(v) : v])
                    );
                    // TODO container login? SHOULD work out-of-the-box if we move the container-login in the backend to opaca-client instead of abstract agent?
                    var res = await backendClient.invokeAction(agent, action, parameters);
                    if (res.success) {
                        await this.$refs.input.showInfo(Localizer.get('agents_result'), "```\n" + JSON.stringify(res.result, null, 2) + "\n```");
                    } else {
                        throw new Error(res.error);
                    }
                }
            );
        },

        typeHint(json) {
            if (json.type === "array") {
                return `list of ${this.typeHint(json.items)}`;
            } else {
                return json.type;
            }
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

.accordion-button.containers-header {
    padding: 1rem 1rem;
}

.accordion-button.agents-header {
    padding: 0.9rem 1rem;
}

.accordion-button.actions-header {
    padding: 0.8rem 1rem;
}

.list-group-item {
    border: none;
}

.invoke:hover {
    color: var(--primary-color);
    cursor: pointer;
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