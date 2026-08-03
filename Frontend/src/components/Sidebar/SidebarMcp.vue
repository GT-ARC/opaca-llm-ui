<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div class="sidebar-title">
        {{ Localizer.get('sidebar_mcp') }}
        <i class="fa fa-plus ms-auto sidebar-title-action"
           @click.stop="addMcp()"
           :title="Localizer.get('mcp_add')" />
        <i class="fa fa-magnifying-glass sidebar-title-action sidebar-title-action-secondary"
           @click="toggleSearch"
           :title="Localizer.get('mcp_search')" />
    </div>

    <input v-if="isSearching"
           type="search"
           ref="searchBar"
           class="form-control my-2"
           :placeholder="Localizer.get('mcp_search')"
           v-model="this.searchQuery" />
    <div v-if="mcpSearchContexts.length > 0" class="sidebar-search-results">
        <div v-for="result in mcpSearchContexts"
             :key="result.key"
             class="sidebar-search-result-group">
            <div class="sidebar-search-result-heading">{{ result.path }}</div>
            <div class="sidebar-search-result-context">{{ result.context }}</div>
        </div>
    </div>

    <section class="mcp-section">
        <div class="mcp-section-title">
            {{ Localizer.get('mcp_installed') }}
        </div>

        <div v-if="this.isLoading">
            <i class="fa fa-circle-notch fa-spin me-1" />
            {{ Localizer.get('mcp_loading') }}
        </div>
        <div v-else-if="!platformMcp || Object.keys(platformMcp).length === 0"
             class="sidebar-empty-state">
            {{ Localizer.get('mcp_installedPlaceholder') }}
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
    </section>

    <section class="mcp-section">
        <div class="mcp-section-title">
            {{ Localizer.get('mcp_browse') }}
            <i class="fa fa-refresh ms-auto sidebar-title-action sidebar-title-action-secondary"
               :class="{ disabled: isRegistryLoading || isRegistryLoadingMore }"
               :aria-disabled="isRegistryLoading || isRegistryLoadingMore"
               @click.stop="updateRegistry(true)"
               :title="Localizer.get('mcp_registryRefresh')" />
        </div>

        <div v-if="isRegistryLoading">
            <i class="fa fa-circle-notch fa-spin me-1" />
            {{ Localizer.get('mcp_registryLoading') }}
        </div>
        <div v-else-if="registryUnavailable && (!registryMcp || registryMcp.length === 0)"
             class="sidebar-empty-state">
            {{ Localizer.get('mcp_registryUnavailable') }}
        </div>
        <div v-else-if="filteredRegistryMcp && filteredRegistryMcp.length === 0"
             class="sidebar-empty-state">
            {{ Localizer.get('mcp_registryEmpty') }}
        </div>
        <div v-else-if="filteredRegistryMcp" class="flex-row">
            <div v-if="registryLoadMoreFailed" class="mcp-registry-warning">
                {{ Localizer.get('mcp_registryLoadMoreFailed') }}
            </div>
            <AppAccordion
                id="mcp-registry-accordion"
                class="text-start"
                :items="filteredRegistryMcp"
                :get-key="server => server.name"
            >
                <template #header="{ item: server }">
                    <i class="fa fa-server me-3" />
                    <strong class="flex-grow-1">{{ server.title || server.name }}</strong>
                    <span class="section-actions"
                          :title="server.compatibleRemoteUrls.length === 0
                              ? Localizer.get('mcp_registryNoRemote')
                              : null">
                        <i class="fa fa-plus click-icon mcp-add-icon"
                           :class="{ disabled: server.compatibleRemoteUrls.length === 0 }"
                           @click.stop="addMcp(server)"
                           :title="server.compatibleRemoteUrls.length > 0
                               ? Localizer.get('mcp_add')
                               : null" />
                    </span>
                </template>

                <template #body="{ item: server }">
                    <div class="mcp-registry-body">
                        <p v-if="server.description" class="mb-2">
                            {{ server.description }}
                        </p>
                        <p class="mb-1 small">
                            <strong>{{ server.name }}</strong>
                        </p>
                        <p class="mb-2 small">
                            {{ Localizer.get('mcp_registryVersion') }}: {{ server.version }}
                        </p>
                        <div v-if="server.remotes?.length" class="small">
                            <strong>{{ Localizer.get('mcp_registryEndpoints') }}:</strong>
                            <div v-for="remote in server.remotes"
                                 :key="`${remote.type}-${remote.url}`"
                                 class="mcp-registry-endpoint">
                                {{ remote.url }}
                            </div>
                        </div>
                    </div>
                </template>
            </AppAccordion>

            <button v-if="registryNextCursor"
                    type="button"
                    class="btn btn-outline-secondary btn-sm w-100 mt-2"
                    :disabled="isRegistryLoadingMore"
                    @click="loadMoreRegistry()">
                <i v-if="isRegistryLoadingMore" class="fa fa-circle-notch fa-spin me-1" />
                {{ Localizer.get('mcp_registryLoadMore') }}
            </button>
        </div>
    </section>

    <InputDialogue ref="input" />
</div>

</template>


<script>
import { nextTick } from 'vue';
import Localizer from "../../Localizer.js";
import { useDevice } from "../../useIsMobile.js";
import backendClient from "../../utils.js";
import AppAccordion from '../AppAccordion.vue';
import InputDialogue from '../InputDialogue.vue';
import { getEffectiveApproval, isConfirmationTool, isForbiddenTool } from '../../approvalUtils.js';

const MCP_REGISTRY_ENDPOINT = 'https://registry.modelcontextprotocol.io/v0.1/servers';
const MCP_REGISTRY_PAGE_SIZE = 20;

export default {
    name: 'SidebarMcp',
    components: {AppAccordion, InputDialogue},
    props: {
        sidebarView: String,
    },
    setup() {
        const { isMobile } = useDevice();
        return { Localizer, isMobile };
    },
    data() {
        return {
            platformMcp: null,
            isLoading: false,
            isSearching: false,
            searchQuery: '',
            restrictedActions: { forbidden: [], need_confirmation: [] },
            registryMcp: null,
            registryNextCursor: null,
            registryUnavailable: false,
            registryLoadMoreFailed: false,
            isRegistryLoading: false,
            isRegistryLoadingMore: false,
            registrySearchTimeout: null,
            registryAbortController: null,
            registryQueryVersion: 0,
        };
    },
    computed: {
        mcpSearchContexts() {
            const query = this.searchQuery.trim().toLowerCase();
            if (!query) return [];

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

            Object.entries(this.platformMcp ?? {}).forEach(([serverName, tools]) => {
                if (matches(serverName)) {
                    results.push({
                        key: `installed-${serverName}`,
                        path: `${Localizer.get('mcp_installed')} › ${serverName}`,
                        context: excerpt(serverName),
                    });
                }

                tools.forEach(tool => {
                    if (!matches(tool.name) && !matches(tool.description)) return;
                    results.push({
                        key: `installed-${serverName}-${tool.name}`,
                        path: `${Localizer.get('mcp_installed')} › ${serverName} › ${tool.name}`,
                        context: excerpt(matches(tool.description) ? tool.description : tool.name),
                    });
                });
            });

            (this.registryMcp ?? []).forEach(server => {
                if (!matches(server.name) && !matches(server.title) && !matches(server.description)) return;
                const serverTitle = server.title || server.name;
                results.push({
                    key: `registry-${server.name}`,
                    path: `${Localizer.get('mcp_browse')} › ${serverTitle}`,
                    context: excerpt(matches(server.description) ? server.description : serverTitle),
                });
            });

            return results;
        },

        filteredRegistryMcp() {
            if (!this.registryMcp) return this.registryMcp;

            const query = this.searchQuery.trim().toLowerCase();
            if (!query) return this.registryMcp;

            return this.registryMcp.filter(server =>
                server.name?.toLowerCase().includes(query)
                || server.title?.toLowerCase().includes(query)
                || server.description?.toLowerCase().includes(query)
            );
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

        async updateMcp() {
            this.isLoading = true;
            try {
                this.restrictedActions = await backendClient.getRestrictedActions();
                this.platformMcp = await backendClient.getMCPs();
            } finally {
                this.isLoading = false;
            }
        },

        async requestRegistryPage(cursor = null, searchQuery = '', signal = null) {
            const url = new URL(MCP_REGISTRY_ENDPOINT);
            url.searchParams.set('version', 'latest');
            url.searchParams.set('limit', MCP_REGISTRY_PAGE_SIZE.toString());
            if (cursor) url.searchParams.set('cursor', cursor);
            if (searchQuery) url.searchParams.set('search', searchQuery);

            const response = await fetch(url, {
                headers: { Accept: 'application/json' },
                signal,
            });
            if (!response.ok) {
                throw new Error(`MCP registry returned HTTP ${response.status}`);
            }
            return await response.json();
        },

        normalizeRegistryServers(entries) {
            return (entries ?? [])
                .map(entry => entry?.server)
                .filter(server => server?.name)
                .map(server => ({
                    ...server,
                    compatibleRemoteUrls: this.getRegistryRemoteUrls(server),
                }));
        },

        async updateRegistry(force = false) {
            if (this.isRegistryLoading) {
                if (!force) return;
                this.registryAbortController?.abort();
            }
            if (!force && this.registryMcp !== null) return;

            const requestVersion = this.registryQueryVersion;
            const controller = new AbortController();
            this.registryAbortController = controller;
            this.isRegistryLoading = true;
            this.registryUnavailable = false;
            this.registryLoadMoreFailed = false;
            try {
                const result = await this.requestRegistryPage(
                    null,
                    this.searchQuery.trim(),
                    controller.signal,
                );
                if (requestVersion !== this.registryQueryVersion) return;
                this.registryMcp = this.normalizeRegistryServers(result.servers);
                this.registryNextCursor = result.metadata?.nextCursor ?? null;
            } catch (error) {
                if (error.name === 'AbortError') return;
                console.error('Failed to load the MCP registry', error);
                this.registryMcp = [];
                this.registryNextCursor = null;
                this.registryUnavailable = true;
            } finally {
                if (this.registryAbortController === controller) {
                    this.registryAbortController = null;
                    this.isRegistryLoading = false;
                }
            }
        },

        async loadMoreRegistry() {
            if (!this.registryNextCursor || this.isRegistryLoadingMore) return;

            const requestVersion = this.registryQueryVersion;
            this.isRegistryLoadingMore = true;
            this.registryLoadMoreFailed = false;
            try {
                const result = await this.requestRegistryPage(
                    this.registryNextCursor,
                    this.searchQuery.trim(),
                );
                if (requestVersion !== this.registryQueryVersion) return;
                const nextServers = this.normalizeRegistryServers(result.servers);
                const knownServers = new Set(this.registryMcp.map(server => server.name));
                this.registryMcp.push(...nextServers.filter(server => !knownServers.has(server.name)));
                this.registryNextCursor = result.metadata?.nextCursor ?? null;
            } catch (error) {
                console.error('Failed to load more MCP registry entries', error);
                this.registryLoadMoreFailed = true;
            } finally {
                this.isRegistryLoadingMore = false;
            }
        },

        async addMcp(registryServer = null) {
            const registryRemoteUrls = registryServer?.compatibleRemoteUrls ?? [];
            if (registryServer && registryRemoteUrls.length === 0) return;

            const serverUrlInput = registryRemoteUrls.length > 1
                ? {
                    type: "select",
                    label: "Server URL",
                    default: registryRemoteUrls[0],
                    values: Object.fromEntries(registryRemoteUrls.map(url => [url, url])),
                }
                : {
                    type: "text",
                    label: "Server URL",
                    default: registryRemoteUrls[0] ?? null,
                };

            await this.$refs.input.showDialogue(
                Localizer.get('mcp_add'),
                null,
                null,
                {
                    mcpServerUrl: serverUrlInput,
                    mcpServerLabel: {
                        type: "text",
                        label: "Server Label (Optional)",
                        default: registryServer ? this.getRegistryLabel(registryServer) : null,
                        optional: true,
                    },
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

        getRegistryRemoteUrls(server) {
            return [...new Set((server.remotes ?? [])
                .map(remote => remote.url)
                .filter(url => {
                    try {
                        return new URL(url).protocol === 'https:';
                    } catch (_) {
                        return false;
                    }
                }))];
        },

        getRegistryLabel(server) {
            const label = (server.title || server.name.split('/').pop() || 'MCPServer')
                .replace(/[^A-Za-z0-9_-]+/g, '-')
                .replace(/^[^A-Za-z]+/, '')
                .replace(/-+$/g, '');
            return label || 'MCPServer';
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
        if (this.sidebarView === 'mcp') this.updateRegistry();
    },

    watch: {
        sidebarView(newView) {
            if (newView === 'mcp') this.updateRegistry();
        },
        searchQuery() {
            this.registryQueryVersion += 1;
            this.registryNextCursor = null;
            this.registryLoadMoreFailed = false;
            clearTimeout(this.registrySearchTimeout);
            this.registrySearchTimeout = setTimeout(() => {
                this.registrySearchTimeout = null;
                this.updateRegistry(true);
            }, 300);
        },
    },

    beforeUnmount() {
        clearTimeout(this.registrySearchTimeout);
        this.registryAbortController?.abort();
    }
}
</script>

<style scoped>
.mcp-body {
    padding: 0.5rem;
}

.mcp-registry-body {
    padding: 0.75rem;
}

.mcp-registry-endpoint {
    overflow-wrap: anywhere;
}

.mcp-registry-warning {
    margin-bottom: 0.5rem;
    color: var(--text-danger-color);
    text-align: center;
}

.mcp-add-icon:hover {
    color: var(--button-primary-color);
}

.mcp-section + .mcp-section {
    margin-top: 1.5rem;
}

.mcp-section-title {
    display: flex;
    align-items: center;
    min-height: 2rem;
    margin-bottom: 0.5rem;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

</style>
