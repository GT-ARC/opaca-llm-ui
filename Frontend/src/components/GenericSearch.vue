<template>
    <template v-if="searchActive">
        <input
            ref="searchBar"
            v-model="searchQuery"
            type="search"
            class="form-control my-2"
            :placeholder="placeholder"
            @input="scheduleSearch"
            @keyup.enter="refreshSearch"
            @keyup.esc="closeSearch"
        />

        <div v-if="isLoading" class="py-2 text-center text-muted">
            <i class="fa fa-circle-notch fa-spin" />
        </div>

        <div v-if="contextPreviews.length > 0" class="sidebar-search-results">
            <div
                v-for="preview in contextPreviews"
                :key="preview.key"
                class="sidebar-search-result-group"
            >
                <div class="sidebar-search-result-heading">{{ preview.path }}</div>
                <div
                    v-for="context in preview.contexts"
                    :key="context.key"
                    class="sidebar-search-result-context"
                    :class="{ 'sidebar-search-result-clickable': context.clickable }"
                    @click="context.clickable && selectContext(preview, context)"
                >
                    {{ context.text }}
                </div>
            </div>
        </div>
    </template>

    <slot :filtered-items="filteredItems" />
</template>

<script>
import {nextTick} from 'vue';

/**
 * Reusable search controller and renderer.
 *
 * `items` is always the source collection. The default slot always receives
 * `filteredItems`, which is the search result derived from that collection.
 * Search is also run with an empty query on mount, after `items` is replaced,
 * and when search is closed. The default mode shows all `items` while
 * inactive, whereas a custom search may additionally sort or transform them.
 *
 * There are two search modes:
 *
 * 1. Built-in flat-item search (no `filterItems` callback):
 *    - `getItemSearchValues(item)` selects the values matched for each item.
 *    - `getItemContextPreview(item, query, helpers, key)` optionally creates
 *      the preview displayed above the filtered collection.
 * 2. Custom filtering (`filterItems` is provided):
 *    - `filterItems(items, query, helpers)` replaces built-in filtering and
 *      supports nested collections and asynchronous search.
 *    - If it returns `contextPreviews`, those are displayed. Otherwise,
 *      `getItemContextPreview` is applied to its filtered items as a fallback.
 *    - `getItemSearchValues` is ignored because filtering is fully custom.
 *
 * A custom filter returns:
 *
 * {
 *     filteredItems: Array | Object,
 *     contextPreviews: [{
 *         key: any,
 *         path: string,
 *         context?: string,
 *         contexts?: [{key?: any, text: string, clickable?: boolean, onSelect?: Function}],
 *     }],
 * }
 *
 * `helpers.matches(value)` compares only that value with the normalized query;
 * it does not use `getItemSearchValues`. `helpers.getMatchExcerpt(value,
 * radius)` shortens matching text for display, but does not create a context preview.
 * Custom filters can return previews without providing `getItemContextPreview`,
 * or rely on that callback for preview creation.
 *
 * Through a template ref, callers can toggle/open/close/refresh search and read
 * its filtered items, active state, query, or context previews.
 */

export default {
    name: 'GenericSearch',
    props: {
        items: {
            type: [Array, Object],
            default: () => [],
        },
        placeholder: {
            type: String,
            default: 'Search...',
        },
        debounce: {
            type: Number,
            default: 0,
        },
        /** Custom filtering; both synchronous and asynchronous callbacks are supported. */
        filterItems: {
            type: Function,
            default: null,
        },
        /** Values searched by the built-in flat collection filter. */
        getItemSearchValues: {
            type: Function,
            default: item => [item],
        },
        /**
         * Builds one or more previews for a filtered item, or null to suppress it.
         */
        getItemContextPreview: {
            type: Function,
            default: null,
        },
    },
    emits: ['search-query-change'],
    data() {
        return {
            searchActive: false,
            searchQuery: '',
            filteredItems: this.items,
            contextPreviews: [],
            isLoading: false,
            searchTimeout: null,
            searchVersion: 0,
        };
    },
    methods: {
        async toggleSearch() {
            if (this.searchActive) {
                this.closeSearch();
                return;
            }
            await this.openSearch();
        },

        async openSearch() {
            if (!this.searchActive) {
                this.searchActive = true;
            }
            await nextTick();
            this.$refs.searchBar?.focus();
        },

        closeSearch() {
            clearTimeout(this.searchTimeout);
            this.searchVersion += 1;
            this.searchActive = false;
            this.searchQuery = '';
            this.isLoading = false;
            this.contextPreviews = [];
            this.filteredItems = this.items;
            this.$emit('search-query-change', '');
            this.refreshSearch();
        },

        scheduleSearch() {
            this.$emit('search-query-change', this.searchQuery);
            clearTimeout(this.searchTimeout);
            if (this.debounce > 0) {
                this.searchTimeout = setTimeout(() => this.refreshSearch(), this.debounce);
            } else {
                this.refreshSearch();
            }
        },

        async refreshSearch() {
            clearTimeout(this.searchTimeout);
            const version = ++this.searchVersion;
            const query = this.searchQuery;
            const helpers = this.getSearchHelpers(query);

            this.isLoading = true;
            try {
                const result = this.filterItems
                    ? await this.filterItems(this.items, query, helpers)
                    : {
                        filteredItems: this.defaultFilterItems(this.items, query, helpers),
                        contextPreviews: null,
                    };
                if (version !== this.searchVersion) return;

                this.filteredItems = result.filteredItems;
                this.contextPreviews = this.normalizeContextPreviews(
                    result.contextPreviews
                        ?? this.createContextPreviews(this.filteredItems, query, helpers),
                );
            } catch (error) {
                if (version !== this.searchVersion) return;
                console.error(error);
                this.filteredItems = this.emptyCollection(this.items);
                this.contextPreviews = [];
            } finally {
                if (version === this.searchVersion) this.isLoading = false;
            }
        },

        defaultFilterItems(items, query, helpers) {
            if (!query.trim()) return items;
            if (Array.isArray(items)) {
                return items.filter(item => this.asArray(this.getItemSearchValues(item)).some(helpers.matches));
            }
            return Object.fromEntries(
                Object.entries(items ?? {}).filter(([key, item]) =>
                    [key, ...this.asArray(this.getItemSearchValues(item))].some(helpers.matches),
                ),
            );
        },

        createContextPreviews(items, query, helpers) {
            if (!query.trim() || !this.getItemContextPreview) return [];
            const entries = Array.isArray(items)
                ? items.map((item, index) => [index, item])
                : Object.entries(items ?? {});
            return entries.flatMap(([index, item]) => {
                const preview = this.getItemContextPreview(item, query, helpers, index);
                return this.asArray(preview).map((entry, previewIndex) => {
                    if (!entry) return entry;
                    return {
                        ...entry,
                        key: entry.key ?? `${index}-${previewIndex}`,
                    };
                });
            }).filter(Boolean);
        },

        normalizeContextPreviews(previews = []) {
            return previews.filter(Boolean).map((preview, previewIndex) => {
                const rawContexts = preview.contexts ?? [{text: preview.context ?? ''}];
                const contexts = rawContexts.map((context, contextIndex) => {
                    return {
                        ...context,
                        key: context.key ?? contextIndex,
                        text: context.text ?? '',
                        clickable: context.clickable ?? Boolean(context.onSelect),
                    };
                });
                return {
                    ...preview,
                    key: preview.key ?? previewIndex,
                    path: preview.path ?? '',
                    contexts,
                };
            });
        },

        selectContext(preview, context) {
            context.onSelect?.(context, preview);
        },

        getSearchHelpers(query = this.searchQuery) {
            const normalizedQuery = query.trim().toLowerCase();
            return {
                query,
                normalizedQuery,
                matches: value => String(value ?? '').toLowerCase().includes(normalizedQuery),
                getMatchExcerpt: (value, radius = 40) => {
                    const text = String(value ?? '');
                    const index = text.toLowerCase().indexOf(normalizedQuery);
                    if (index < 0 || !normalizedQuery) return text;
                    const start = Math.max(0, index - radius);
                    const end = Math.min(text.length, index + normalizedQuery.length + radius);
                    return `${start > 0 ? '…' : ''}${text.slice(start, end)}${end < text.length ? '…' : ''}`;
                },
            };
        },

        emptyCollection(items) {
            return Array.isArray(items) ? [] : {};
        },

        asArray(value) {
            return Array.isArray(value) ? value : [value];
        },

        // Public ref API, mirroring the imperative style of InputDialogue.
        getFilteredItems() {
            return this.filteredItems;
        },
        getSearchActiveState() {
            return this.searchActive;
        },
        getSearchQuery() {
            return this.searchQuery;
        },
        getContextPreviews() {
            return this.contextPreviews;
        },
    },
    watch: {
        items() {
            this.refreshSearch();
        },
    },
    mounted() {
        this.refreshSearch();
    },
    beforeUnmount() {
        clearTimeout(this.searchTimeout);
        this.searchVersion += 1;
    },
};
</script>

<style scoped>
.sidebar-search-results {
    max-height: 12rem;
    overflow-y: auto;
    margin-bottom: .5rem;
}

.sidebar-search-result-group + .sidebar-search-result-group {
    margin-top: .75rem;
}

.sidebar-search-result-heading {
    color: var(--secondary-color);
    font-size: .875rem;
}

.sidebar-search-result-context {
    padding: .5rem;
    margin-top: .25rem;
    overflow-wrap: anywhere;
}

.sidebar-search-result-clickable:hover {
    background-color: var(--surface-color);
    cursor: pointer;
}
</style>
