<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div class="sidebar-title">
        {{ Localizer.get('sidebar_agents') }}
        <i v-if="conf.allowContainerManagement && this.isPlatformConnected"
           class="fa fa-plus ms-auto sidebar-title-action"
           @click.stop="addContainer()"
           :title="Localizer.get('agents_deploy')" />
        <i class="fa fa-magnifying-glass sidebar-title-action sidebar-title-action-secondary"
           :class="{
               'ms-auto': !(conf.allowContainerManagement && this.isPlatformConnected),
               disabled: this.isLoading || !this.platformContainers || this.platformContainers.length === 0,
           }"
           :aria-disabled="this.isLoading || !this.platformContainers || this.platformContainers.length === 0"
           @click="toggleSearch"
           :title="Localizer.get('agents_search')" />
    </div>

    <InputDialogue ref="input"/>

    <div v-if="this.isLoading">
        <i class="fa fa-circle-notch fa-spin me-1" />
        {{ Localizer.get('agents_loading') }}
    </div>
    <div v-else-if="platformContainers === null"
         class="sidebar-empty-state">
        {{ Localizer.get('general_disconnected') }}
    </div>
    <div v-else-if="platformContainers.length === 0"
         class="sidebar-empty-state">
        {{ Localizer.get('agents_missing') }}
    </div>
    <div v-else class="flex-row" >
        <input v-if="isSearching"
            type="search"
            ref="searchBar"
            class="form-control my-2"
            :placeholder="Localizer.get('agents_search')"
            v-model="this.searchQuery"
        />
        <div v-if="agentSearchContexts.length > 0" class="sidebar-search-results">
            <div v-for="result in agentSearchContexts"
                 :key="result.key"
                 class="sidebar-search-result-group">
                <div class="sidebar-search-result-heading">{{ result.path }}</div>
                <div class="sidebar-search-result-context">{{ result.context }}</div>
            </div>
        </div>
        <AppAccordion
            id="agents-accordion"
            class="text-start"
            :items="getContainers()"
            :get-key="container => container.containerId"
        >
            <template #header="{ item: {containerId, image} }">
                <i :class="isInternalContainer(containerId) ? 'fa fa-cube me-3' : 'fa fa-box me-3'"/>
                <strong class="container-name">{{ (image?.name === "" ? null : image?.name) ?? image?.imageName ?? containerId }}</strong>

                <span v-if="conf.allowContainerManagement && !isInternalContainer(containerId)"
                      class="section-actions">
                    <i class="fa fa-remove click-icon"
                       @click.stop.prevent="this.stopContainer(containerId)"
                       :title="Localizer.get('agents_undeploy')" />
                </span>
            </template>

            <template #body="{ item: {containerId, agents, approvals}, index: containerIndex }">
                <AppAccordion
                    :id="`agents-accordion-${containerIndex}`"
                    :items="agents"
                    :get-key="agent => agent.agentId"
                    variant="nested"
                >
                    <template #header="{ item: {agentId, actions} }">
                        <i class="fa fa-user me-3"/>
                        <strong>{{ agentId }}</strong>&nbsp;({{ actions?.length }})
                    </template>

                    <template #body="{ item: {agentId, actions}, index: agentIndex }">
                        <AppAccordion
                            :id="`actions-accordion-${containerIndex}-${agentIndex}`"
                            :items="actions"
                            :get-key="action => action.name"
                            variant="nested"
                        >
                            <template #header="{ item: action }">
                                <div class="position-relative d-inline-block me-3">
                                    <i class="fa fa-wrench"/>
                                    <span class="position-absolute top-100 start-100 p-1 rounded-circle"
                                          :class="{
                                              'bg-approval-ask': getEffectiveApproval(agentId, action, approvals) === 'ask',
                                              'bg-approval-deny': getEffectiveApproval(agentId, action, approvals) === 'deny',
                                              'bg-approval-allow': getEffectiveApproval(agentId, action, approvals) === 'allow'
                                          }" style="outline: 2px solid var(--surface-color); transform: translate(-180%, -70%);">
                                        <span class="visually-hidden">Approval State</span>
                                    </span>
                                </div>
                                {{ action.name }}
                            </template>

                            <template #body="{ item: action, index: actionIndex }">
                                <div class="action-body p-2">
                                    <p class="invoke" @click.stop="invokeAction(agentId, action.name, action.parameters)">
                                        <strong>{{ Localizer.get('agents_invoke') }}</strong>
                                        <i class="fa fa-circle-play mx-2"/>
                                    </p>
                                    <p v-if="action.description">
                                        <strong>{{ Localizer.get('agents_description') }}:</strong>
                                        {{ action.description }}
                                    </p>
                                    <!-- Action Permissions -->
                                    <div class="d-flex align-items-baseline mb-3">
                                        <strong class="me-2">Approval:</strong>
                                        <div class="btn-group btn-group-sm w-100" role="group">
                                            <input type="radio" class="btn-check" :name="`approval-${containerId}-${agentIndex}-${actionIndex}`" :id="`btn-ask-${containerId}-${agentIndex}-${actionIndex}`" autocomplete="off"
                                                @change="e => setApproval(containerId, agentId, action.name, 'ask')"
                                                :checked="getEffectiveApproval(agentId, action, approvals) === 'ask'"
                                                :disabled="isForbiddenApplied(agentId, action)">
                                            <label class="btn btn-outline-secondary approval-ask" :for="`btn-ask-${containerId}-${agentIndex}-${actionIndex}`">Ask</label>

                                            <input type="radio" class="btn-check" :name="`approval-${containerId}-${agentIndex}-${actionIndex}`" :id="`btn-deny-${containerId}-${agentIndex}-${actionIndex}`" autocomplete="off"
                                                @change="e => setApproval(containerId, agentId, action.name, 'deny')"
                                                :checked="getEffectiveApproval(agentId, action, approvals) === 'deny'"
                                                :disabled="isForbiddenApplied(agentId, action)">
                                            <label class="btn btn-outline-secondary approval-deny" :for="`btn-deny-${containerId}-${agentIndex}-${actionIndex}`">Deny</label>

                                            <input type="radio" class="btn-check" :name="`approval-${containerId}-${agentIndex}-${actionIndex}`" :id="`btn-allow-${containerId}-${agentIndex}-${actionIndex}`" autocomplete="off"
                                                @change="e => setApproval(containerId, agentId, action.name, 'allow')"
                                                :checked="getEffectiveApproval(agentId, action, approvals) === 'allow'"
                                                :disabled="isForbiddenApplied(agentId, action) || isConfirmationApplied(agentId, action)">
                                            <label class="btn btn-outline-secondary approval-allow" :for="`btn-allow-${containerId}-${agentIndex}-${actionIndex}`">Allow</label>
                                        </div>
                                    </div>

                                    <strong>{{ Localizer.get('agents_parameters') }}:</strong>
                                    <pre class="json-box">{{ formatJSON(action.parameters) }}</pre>
                                    <strong>{{ Localizer.get('agents_result') }}:</strong>
                                    <pre class="json-box">{{ formatJSON(action.result) }} </pre>
                                </div>
                            </template>
                        </AppAccordion>
                    </template>
                </AppAccordion>
            </template>
        </AppAccordion>
    </div>
</div>

</template>


<script>
import { nextTick } from 'vue';
import conf from '../../../config.js';
import Localizer from "../../Localizer.js";
import { useDevice } from "../../useIsMobile.js";
import backendClient from "../../utils.js";
import AppAccordion from '../AppAccordion.vue';
import InputDialogue from '../InputDialogue.vue';
import { getEffectiveApproval, isConfirmationTool, isForbiddenTool } from '../../approvalUtils.js';

export default {
    name: 'SidebarAgents',
    components: {AppAccordion, InputDialogue},
    props: {
        isPlatformConnected: Boolean,
    },
    setup() {
        const { isMobile } = useDevice();
        return { conf, Localizer, isMobile };
    },
    data() {
        return {
            platformContainers: null,
            isLoading: false,
            isSearching: false,
            searchQuery: '',
            restrictedActions: { forbidden: [], need_confirmation: [] },
        };
    },
    computed: {
        agentSearchContexts() {
            const query = this.searchQuery.trim().toLowerCase();
            if (!query || !this.platformContainers) return [];

            const results = [];
            const matches = value => value?.toLowerCase().includes(query);
            const excerpt = value => {
                const text = value ?? '';
                const index = text.toLowerCase().indexOf(query);
                if (index < 0) return text;
                const start = Math.max(0, index - 40);
                const end = Math.min(text.length, index + query.length + 40);
                return `${start > 0 ? '…' : ''}${text.slice(start, end)}${end < text.length ? '…' : ''}`;
            };

            this.platformContainers.forEach(container => {
                const containerName = container.image?.imageName ?? container.containerId;
                if (matches(containerName)) {
                    results.push({
                        key: `container-${container.containerId}`,
                        path: containerName,
                        context: excerpt(containerName),
                    });
                }

                container.agents?.forEach(agent => {
                    if (matches(agent.agentId)) {
                        results.push({
                            key: `agent-${container.containerId}-${agent.agentId}`,
                            path: `${containerName} › ${agent.agentId}`,
                            context: excerpt(agent.agentId),
                        });
                    }

                    agent.actions?.forEach(action => {
                        if (!matches(action.name) && !matches(action.description)) return;
                        results.push({
                            key: `action-${container.containerId}-${agent.agentId}-${action.name}`,
                            path: `${containerName} › ${agent.agentId} › ${action.name}`,
                            context: excerpt(matches(action.description) ? action.description : action.name),
                        });
                    });
                });
            });

            return results;
        },
    },
    methods: {
        async toggleSearch() {
            this.isSearching = !this.isSearching;
            if (!this.isSearching) {
                this.searchQuery = '';
                return;
            }
            await nextTick();
            this.$refs.searchBar?.focus();
        },

        getEffectiveApproval(agentId, action, approvals) {
            return getEffectiveApproval(`${agentId}--${action.name}`, approvals?.[`${agentId}--${action.name}`], this.restrictedActions);
        },
        isForbiddenApplied(agentId, action) {
            return isForbiddenTool(`${agentId}--${action.name}`, this.restrictedActions);
        },
        isConfirmationApplied(agentId, action) {
            return isConfirmationTool(`${agentId}--${action.name}`, this.restrictedActions);
        },
        async setApproval(containerId, agentName, actionName, approval) {
            const toolName = `${agentName}--${actionName}`;

            try {
                await backendClient.setContainerApproval(containerId, toolName, approval);

                const container = this.platformContainers.find(c => c.containerId === containerId);
                if (container) {
                    if (!container.approvals) container.approvals = {};
                    container.approvals[toolName] = approval;
                }
            } catch (err) {
                console.error("Failed to update approval", err);
            }
        },

        async updatePlatformInfo() {
            this.isLoading = true;
            try {
                this.restrictedActions = await backendClient.getRestrictedActions();
                const externalContainers = this.isPlatformConnected
                    ? await backendClient.getContainers()
                    : [];
                const internalContainers = await backendClient.getInternalTools();
                const allContainers = [...externalContainers, ...internalContainers];

                // Fetch approvals for each container
                for (let container of allContainers) {
                    container.approvals = await backendClient.getContainerApprovals(container.containerId);
                }

                this.platformContainers = allContainers;
            } finally {
                this.isLoading = false;
            }
            await nextTick();
        },

        formatJSON(obj) {
            return JSON.stringify(obj, null, 2);
        },

        isInternalContainer(containerId) {
            return containerId === "__internal_tools__";
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
            containers.sort((a, b) => {
                if (this.isInternalContainer(a.containerId) && !this.isInternalContainer(b.containerId)) return -1;
                if (!this.isInternalContainer(a.containerId) && this.isInternalContainer(b.containerId)) return 1;
                return a.image.imageName.toLowerCase().localeCompare(b.image.imageName.toLowerCase());
            });
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

        // MULTI-PAGE "WIZARD" FOR STARTING CONTAINERS IN DIFFERENT WAYS, INCLUDING PARAMETERS

        async addContainer() {
            await this.$refs.input.showDialogue(
                Localizer.get("agents_deploy"),
                Localizer.get("agents_deploy_how"),
                null,
                {
                    howto: { type: "select", default: "name", values: {
                        "name": "Image Name",
                        "json": "JSON",
                        "reg": "Registry",
                        "update": Localizer.get("agents_deploy_update_existing"),
                    }},
                },
                async values => {
                    switch (values.howto) {
                        case "name": return await this.addContainerFromImageName();
                        case "json": return await this.addContainerFromJson();
                        case "reg": return await this.addContainerFromRegistry();
                        case "update": return await this.updateContainerDialogue();
                    }
                }
            );
        },

        async addContainerFromRegistry() {
            await this.$refs.input.showDialogue(
                Localizer.get("agents_deploy"),
                Localizer.get("agents_deploy_registry"),
                null,
                {
                    registry: { type: "text", label: "Registry URL (incl Port)", default: conf.registryUrl},
                },
                async values => {
                    // get images from the registry (names and JSON)
                    conf.registryUrl = values.registry;
                    const res = await fetch(`${values.registry}/images`);
                    const images = Object.fromEntries(
                        JSON.parse(await res.text())
                            .map(img => Object.fromEntries(Object.entries(img).filter(([k]) => !k.startsWith('_'))))
                            .map(img => [img.imageName, img])
                    );
                    // select which image to deploy
                    await this.$refs.input.showDialogue(
                        Localizer.get("agents_deploy"),
                        Localizer.get("agents_deploy_select"),
                        null,
                        {
                            image: { type: "select", values: Object.fromEntries(Object.entries(images).map(([k, v]) => [k, `${v.name} (${v.version}), ${v.provider}`]))},
                        },
                        async values => {
                            const json = images[values.image];
                            await this.doPostContainerImage(json);
                        }
                    );
                }
            );
        },

        async addContainerFromImageName() {
            await this.$refs.input.showDialogue(
                Localizer.get("agents_deploy"),
                Localizer.get("agents_deploy_name"),
                null,
                {
                    image: { type: "text", label: "Image Name"},
                },
                async values => {
                    await this.doSubmitContainer({image: {imageName: values.image}});
                }
            );
        },

        async addContainerFromJson() {
            await this.$refs.input.showDialogue(
                Localizer.get("agents_deploy"),
                Localizer.get("agents_deploy_json"),
                null,
                {
                    json: { type: "textarea", label: "Image/Container JSON", monospace: true, rows: 15 },
                },
                async values => {
                    var json = JSON.parse(values.json);
                    if (json.image) {
                        return this.doSubmitContainer(json);
                    }
                    if (json.imageName) {
                        return this.doPostContainerImage(json);
                    }
                    throw new Error("Invalid JSON format.");
                }
            );
        },

        async updateContainerDialogue() {
            const externalContainers = (this.platformContainers ?? [])
                .filter(container => !this.isInternalContainer(container.containerId));

            if (externalContainers.length === 0) {
                throw new Error(Localizer.get("agents_deploy_update_missing"));
            }

            const containerOptions = Object.fromEntries(
                externalContainers.map(c => [c.image.imageName, c.image.imageName])
            );

            await this.$refs.input.showDialogue(
                Localizer.get("agents_deploy"),
                Localizer.get("agents_deploy_update_select"),
                null,
                {
                    container: { type: "select", values: containerOptions }
                },
                async values => {
                    const existing = externalContainers.find(c => c.image.imageName === values.container);
                    const baseContainer = {
                        image: existing.image,
                        arguments: existing.arguments || {}
                    };
                    await this.$refs.input.showDialogue(
                        Localizer.get("agents_deploy"),
                        Localizer.get("agents_deploy_update_edit"),
                        null,
                        {
                            json: { type: "textarea", label: "Container JSON", default: JSON.stringify(baseContainer, null, 2), monospace: true, rows: 15 }
                        },
                        async configValues => {
                            const updatedContainer = JSON.parse(configValues.json);
                            await this.doSubmitContainer(updatedContainer, true);
                        }
                    );
                }
            );
        },

        async doPostContainerImage(image) {
            if (image.parameters && image.parameters.length > 0) {
                const types = {"string": "text", "boolean": "checkbox", "integer": "number", "number": "number"};
                await this.$refs.input.showDialogue(
                    Localizer.get("agents_deploy"),
                    Localizer.get("agents_deploy_params"),
                    null,
                    Object.fromEntries(
                        image.parameters.map((p => [p.name, {type: types[p.type] ?? "textarea", label: `${p.name} (${this.typeHint(p)})`, default: p.defaultValue, optional: !p.required}]))
                    ),
                    async values => {
                        await this.doSubmitContainer({image: image, arguments: values});
                    }
                );
            } else {
                await this.doSubmitContainer({image: image});
            }
        },

        async doSubmitContainer(container, isUpdate = false) {
            const res = await backendClient.deployContainer(container, isUpdate);
            if (res.success) {
                await this.updatePlatformInfo();
            } else {
                throw new Error(res.error);
            }
        },

        async stopContainer(containerId) {
            if (confirm(Localizer.get('agents_undeploy_confirm'))) {
                await backendClient.undeployContainer(containerId);
                await this.updatePlatformInfo();
            }
        },

        // ACTION INVOCATION

        async invokeAction(agent, action, schema) {
            const types = {"string": "text", "boolean": "checkbox", "integer": "number", "number": "number"};
            await this.$refs.input.showDialogue(
                Localizer.get('agents_invoke'),
                `**Agent:** ${agent}\n\n**Action:** ${action}`,
                null,
                Object.fromEntries(
                    Object.entries(schema).map(([k, v]) => [k, {
                        type: types[v.type] ?? "textarea",
                        label: `${k} (${this.typeHint(v)}${v.required ? "" : ", opt."})`,
                        optional: !v.required,
                        default: v.defaultValue }]
                    )
                ),
                async values => {
                    // JSON-parse non-primitive inputs --> parse errors are shown in error label
                    var parameters = Object.fromEntries(
                        Object.entries(values)
                                .map(([k, v]) => [k, schema[k].type !== "string" && v === "" ? null : v])
                                .filter(([k, v]) => v !== null || schema[k].required)
                                .map(([k, v]) => [k, types[schema[k].type] === undefined ? JSON.parse(v) : v])
                    );
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
    },
    mounted() {
        this.updatePlatformInfo();
    }
}
</script>

<style scoped>
.container-name {
    flex: 1 1 auto;
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
