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

        <slot
            name="context-previews"
            :context-previews="contextPreviews"
            :select-context="selectContext"
        >
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
                        @click="selectContext(preview, context)"
                    >
                        {{ context.text }}
                    </div>
                </div>
            </div>
        </slot>
    </template>

    <slot
        :filtered-items="filteredItems"
        :search-active="searchActive"
        :search-query="searchQuery"
        :is-loading="isLoading"
        :context-previews="contextPreviews"
    />
</template>

<script>
import {nextTick} from 'vue';

const identity = value => value;

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
        /**
         * May return the filtered collection directly or an object containing
         * { filteredItems, contextPreviews }. Both synchronous and asynchronous
         * callbacks are supported.
         */
        filterItems: {
            type: Function,
            default: null,
        },
        /** Values searched by the built-in flat collection filter. */
        getItemSearchValues: {
            type: Function,
            default: item => [item],
        },
        getItemKey: {
            type: Function,
            default: (_item, index) => index,
        },
        /**
         * Builds a preview for one filtered item. It may return a string, one
         * preview, multiple previews, or null to suppress the preview.
         */
        getItemContextPreview: {
            type: Function,
            default: null,
        },
    },
    emits: [
        'search-active-change',
        'search-query-change',
        'filtered-items-change',
        'context-select',
        'search-error',
    ],
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
                this.$emit('search-active-change', true);
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
            this.$emit('search-active-change', false);
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
                    : this.defaultFilterItems(this.items, query, helpers);
                if (version !== this.searchVersion) return;

                const hasSearchResultShape = result
                    && !Array.isArray(result)
                    && Object.prototype.hasOwnProperty.call(result, 'filteredItems');
                this.filteredItems = hasSearchResultShape ? result.filteredItems : result;
                this.contextPreviews = this.normalizeContextPreviews(
                    hasSearchResultShape
                        ? result.contextPreviews
                        : this.createContextPreviews(this.filteredItems, query, helpers),
                );
                this.$emit('filtered-items-change', this.filteredItems);
            } catch (error) {
                if (version !== this.searchVersion) return;
                console.error(error);
                this.filteredItems = this.emptyCollection(this.items);
                this.contextPreviews = [];
                this.$emit('search-error', error);
                this.$emit('filtered-items-change', this.filteredItems);
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
                    if (!entry || typeof entry === 'string') return entry;
                    return {
                        ...entry,
                        key: entry.key ?? `${this.getItemKey(item, index)}-${previewIndex}`,
                    };
                });
            }).filter(identity);
        },

        normalizeContextPreviews(previews = []) {
            return previews.filter(identity).map((preview, previewIndex) => {
                if (typeof preview === 'string') {
                    preview = {context: preview};
                }
                const rawContexts = preview.contexts ?? [preview.context ?? ''];
                const contexts = rawContexts.map((context, contextIndex) => {
                    if (typeof context === 'string') context = {text: context};
                    return {
                        ...context,
                        key: context.key ?? contextIndex,
                        text: context.text ?? context.context ?? '',
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
            this.$emit('context-select', context, preview);
        },

        getSearchHelpers(query = this.searchQuery) {
            const normalizedQuery = query.trim().toLowerCase();
            return {
                query,
                normalizedQuery,
                matches: value => String(value ?? '').toLowerCase().includes(normalizedQuery),
                excerpt: (value, radius = 40) => {
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
