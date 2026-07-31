<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div class="sidebar-title">
        {{ Localizer.get('sidebar_mcp') }}
        <i class="fa fa-plus ms-auto sidebar-title-action"
           @click.stop="addMcp()"
           :title="Localizer.get('mcp_add')" />
    </div>

    <div v-if="this.isLoading">
        <i class="fa fa-circle-notch fa-spin me-1" />
        {{ Localizer.get('mcp_loading') }}
    </div>
    <div v-else-if="!platformMcp || Object.keys(platformMcp).length === 0"
         class="sidebar-empty-state">
        {{ Localizer.get('mcp_missing') }}
    </div>
    <div v-else class="flex-row" >
        <AppAccordion
            id="mcp-accordion"
            class="text-start"
            :items="getMcpServers()"
            :get-key="server => server.name"
        >
            <template #header="{ item: server }">
                <i class="fa fa-server me-3"/>
                <strong class="flex-grow-1">{{ server.name }}</strong>

                <span class="section-actions">
                    <i class="fa fa-remove click-icon"
                       @click.stop="this.deleteMcp(server.name)"
                       :title="Localizer.get('mcp_remove')" />
                </span>
            </template>

            <template #body="{ item: server, index: mcpServerIndex }">
                <AppAccordion
                    :id="`mcp-accordion-${mcpServerIndex}`"
                    :items="server.tools"
                    :get-key="mcp => mcp.name"
                    variant="nested"
                >
                    <template #header="{ item: mcp }">
                        <div class="position-relative d-inline-block me-3">
                            <i class="fa fa-wrench"/>
                            <span class="position-absolute top-100 start-100 p-1 rounded-circle"
                                  :class="{
                                      'bg-approval-ask': getEffectiveApproval(mcp) === 'ask',
                                      'bg-approval-deny': getEffectiveApproval(mcp) === 'deny',
                                      'bg-approval-allow': getEffectiveApproval(mcp) === 'allow'
                                  }" style="outline: 2px solid var(--surface-color); transform: translate(-30%, -90%);">
                                <span class="visually-hidden">Approval State</span>
                            </span>
                        </div>
                        {{ mcp.name }}
                    </template>

                    <template #body="{ item: mcp, index: mcpIndex }">
                        <div class="mcp-body">
                            <p class="invoke" @click.stop="invokeAction(mcp.server_label, mcp.name, mcpToOpacaSchema(mcp.inputSchema))">
                                <strong>{{ Localizer.get('agents_invoke') }}</strong>
                                <i class="fa fa-circle-play mx-2"/>
                            </p>
                            <p v-if="mcp.description" class="mb-2">
                                <strong>{{ Localizer.get('agents_description') }}:</strong>
                                {{ mcp.description }}
                            </p>
                            <div class="d-flex align-items-center">
                                <strong class="me-2">Approval:</strong>
                                <div class="btn-group btn-group-sm w-100" role="group">
                                    <input type="radio" class="btn-check" :name="'approval-' + mcpServerIndex + '-' + mcpIndex" :id="'btn-ask-' + mcpServerIndex + '-' + mcpIndex" autocomplete="off"
                                        @change="e => setApproval(mcp.server_label, mcp.name, 'ask')"
                                        :checked="getEffectiveApproval(mcp) === 'ask'"
                                        :disabled="isForbiddenApplied(mcp)">
                                    <label class="btn btn-outline-secondary approval-ask" :for="'btn-ask-' + mcpServerIndex + '-' + mcpIndex">Ask</label>

                                    <input type="radio" class="btn-check" :name="'approval-' + mcpServerIndex + '-' + mcpIndex" :id="'btn-deny-' + mcpServerIndex + '-' + mcpIndex" autocomplete="off"
                                        @change="e => setApproval(mcp.server_label, mcp.name, 'deny')"
                                        :checked="getEffectiveApproval(mcp) === 'deny'"
                                        :disabled="isForbiddenApplied(mcp)">
                                    <label class="btn btn-outline-secondary approval-deny" :for="'btn-deny-' + mcpServerIndex + '-' + mcpIndex">Deny</label>

                                    <input type="radio" class="btn-check" :name="'approval-' + mcpServerIndex + '-' + mcpIndex" :id="'btn-allow-' + mcpServerIndex + '-' + mcpIndex" autocomplete="off"
                                        @change="e => setApproval(mcp.server_label, mcp.name, 'allow')"
                                        :checked="getEffectiveApproval(mcp) === 'allow'"
                                        :disabled="isForbiddenApplied(mcp) || isConfirmationApplied(mcp)">
                                    <label class="btn btn-outline-secondary approval-allow" :for="'btn-allow-' + mcpServerIndex + '-' + mcpIndex">Allow</label>
                                </div>
                            </div>
                        </div>
                    </template>
                </AppAccordion>
            </template>
        </AppAccordion>
    </div>
    <InputDialogue ref="input" />
</div>

</template>


<script>
import Localizer from "../../Localizer.js";
import { useDevice } from "../../useIsMobile.js";
import backendClient from "../../utils.js";
import AppAccordion from '../AppAccordion.vue';
import InputDialogue from '../InputDialogue.vue';
import { getEffectiveApproval, isConfirmationTool, isForbiddenTool } from '../../approvalUtils.js';

export default {
    name: 'SidebarMcp',
    components: {AppAccordion, InputDialogue},
    setup() {
        const { isMobile } = useDevice();
        return { Localizer, isMobile };
    },
    data() {
        return {
            platformMcp: null,
            isLoading: false,
            searchQuery: '',
            restrictedActions: { forbidden: [], need_confirmation: [] },
        };
    },
    methods: {
        async updateMcp() {
            this.isLoading = true;
            try {
                this.restrictedActions = await backendClient.getRestrictedActions();
                this.platformMcp = await backendClient.getMCPs();
            } finally {
                this.isLoading = false;
            }
        },

        async addMcp() {
            await this.$refs.input.showDialogue(
                Localizer.get('mcp_add'), null, null,
                {
                    mcpServerUrl: {type: "text", label: "Server URL"},
                    mcpServerLabel: {type: "text", label: "Server Label (Optional)", optional: true},
                    mcpDefaultApproval: {type: "select", label: "Default Approval", default: "ask", values: {
                        ask: "Always Ask",
                        allow: "Auto Allow",
                        deny: "Auto Deny"
                    }},
                },
                async (values) => {
                    // Get values from submission dialogue
                    const data = {type: "mcp", server_url: values.mcpServerUrl, server_label: values.mcpServerLabel, default_approval: values.mcpDefaultApproval}

                    // Validate input
                    var mcpError = this.isValidInput(data.server_url, data.server_label);
                    if (mcpError !== "") {
                        throw new Error(mcpError);
                    }

                    // Add MCP server to backend, retry on failure
                    try {
                        await backendClient.addMcp(data);
                    } catch (err) {
                        throw new Error(err.response.data.detail);
                    }
                    await this.updateMcp(true);
                }
            );
            
        },

        async deleteMcp(mcpName) {
            await this.$refs.input.showDialogue(
                Localizer.get('mcp_remove') + "?", null, null, {}, 
                async (values) => {
                    await backendClient.deleteMcp(mcpName);
                    await this.updateMcp(true);
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
        },

        getMcpServers() {
            return Object.entries(this.getMcp())
                .map(([name, tools]) => ({name, tools}));
        },

        getEffectiveApproval(mcp) {
            return getEffectiveApproval(`${mcp.server_label}--${mcp.name}`, mcp.approval, this.restrictedActions);
        },

        isForbiddenApplied(mcp) {
            return isForbiddenTool(`${mcp.server_label}--${mcp.name}`, this.restrictedActions);
        },

        isConfirmationApplied(mcp) {
            return isConfirmationTool(`${mcp.server_label}--${mcp.name}`, this.restrictedActions);
        },

        async setApproval(serverLabel, toolName, approval) {
            try {
                await backendClient.setMcpToolApproval(serverLabel, toolName, approval);

                for (const server in this.platformMcp) {
                    const tool = this.platformMcp[server].find(t => t.server_label === serverLabel && t.name === toolName);
                    if (tool) {
                        tool.approval = approval;
                        break;
                    }
                }
            } catch (err) {
                console.error("Failed to update approval", err);
            }
        },

        isValidInput(s_url, s_label) {
            // Return a detailed error msg if the mcp server url or label is malformed. Return an empty string if the url is valid.

            // Check if the url string is empty
            if (!s_url) {
                return "The Server Url cannot be empty!"
            }

            // Check if the label starts with a letter and only contains letters, digits, '-', and '_'
            if (s_label && !/^[A-Za-z][A-Za-z0-9_-]*$/.test(s_label)) {
                return "The server label must start with a letter and consist of only letters, digits, '-' and '_'"
            }

            // Check if the string is in a valid url format
            let url;
            try {
                url = new URL(s_url);
            } catch (_) {
                return "The server url needs to be in a valid format (\"https://...\")!";
            }

            // Check if the protocol is https. Otherwise mcp tools will not work.
            if (url.protocol === "http:") {
                return "Only HTTPS is allowed for MCP Servers!"
            } else if (url.protocol === "https:") {
                return ""
            }

            return "Unknown error encountered!"
        },

        // MCP INVOCATION
        // Copied from Agents Sidebar; intentionally left param names unchanged for easier comparison
        // we could maybe also move this to a utils class, or wait if Agents and MCP sidebar are merged eventually?

        async invokeAction(agent, action, schema) {
            const types = {"string": "text", "boolean": "checkbox", "integer": "number", "number": "number"};
            await this.$refs.input.showDialogue(
                Localizer.get('agents_invoke'),
                `**Server:** ${agent}\n\n**Tool:** ${action}`,
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
            if (json.anyOf) {
                return json.anyOf.map(this.typeHint).join(" or ");
            }
            if (json.type === "array") {
                return `list of ${this.typeHint(json.items)}`;
            } else {
                return json.type;
            }
        },

        mcpToOpacaSchema(inputSchema) {
            const res = { ...inputSchema.properties };
            for (const key of inputSchema.required ?? []) {
                res[key].required = true;
            }
            return res;
        },
    },

    mounted() {
        this.updateMcp();
    }
}
</script>

<style scoped>
.mcp-body {
    padding: 0.5rem;
}

</style>
