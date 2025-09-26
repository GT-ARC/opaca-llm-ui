<template>
<div class="search-overlay"
     @click="this.$emit('stop-search')"
     @keyup.esc="this.$emit('stop-search')">
    <div class="search-window" @click.stop>

        <!-- Search Bar -->
        <input v-model="searchText" ref="searchBar"
               @input="this.updateSearchResults"
               @keyup.enter="this.updateSearchResults"
        />

        <div v-if="Array.from(Object.keys(this.searchResults)).length > 0" class="search-result-list">
            <div v-for="(results, chatId) in searchResults" :key="chatId" class="mt-3">
                <div class="small" style="color: var(--secondary-color)">
                    {{ results?.[0].chat_name }}
                </div>
                <div v-for="(result, index) in results" :key="index" class="search-result" @click="this.gotoResult(result)">
                    {{ result.excerpt }}
                </div>
            </div>
        </div>

    </div>
</div>
</template>

<script>
import conf from "../../config.js";
import backendClient from "../utils.js";
import Localizer from "../Localizer.js";

export default {
    name: "SearchChatsOverlay",
    props: {
        isSearching: Boolean,
        chats: Array,
    },
    data() {
        return {
            searchText: '',
            searchResults: {},
            isLoadingResults: false,
        };
    },
    setup() {
        return { conf, Localizer };
    },
    emits: [
        'stop-search',
        'goto-search-result',
    ],
    methods: {
        async updateSearchResults() {
            if (this.searchText.length < 3) {
                this.searchResults = {};
                return;
            }
            try {
                this.isLoadingResults = true;
                this.searchResults = await backendClient.search(this.searchText);
            } catch (error) {
                console.error(error);
                this.searchResults = {};
            } finally {
                this.isLoadingResults = false;
            }
        },

        gotoResult(result) {
            this.$emit('goto-search-result', result.chat_id, result.message_id);
        },

        clear() {
            this.searchText = '';
            this.searchResults = {};
            this.isLoadingResults = false;
        },
    },
    mounted() {
        this.clear();
        this.$refs.searchBar.focus();
    },
    watch: {
        isSearching(val) {
            // prevent background scroll when search is open
            document.body.style.overflow = val ? 'hidden' : '';
            this.updateSearchResults();
        },
    }
}
</script>

<style scoped>
.search-overlay {
    position: fixed;
    top: 50px;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0,0,0,0.5); /* backdrop dim */
    z-index: 3000;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding-top: 1rem;
    pointer-events: auto; /* blocks clicks behind */
}

.search-window {
    width: 100%;
    padding: 1rem;
    max-width: min(95vw, 800px);
    border: 1px solid var(--border-color);
    border-radius: 1rem;
    background-color: var(--background-color);
    color: var(--text-primary-color);
}

.search-window input {
    background-color: var(--input-color);
    border: none;
    box-shadow: none;
    outline: none;
    color: var(--text-primary-color);
    width: 100%;
    padding: 0.5rem;
    border-radius: 0.25rem;
}

.search-window input:focus {
    border: 1px solid var(--primary-color) !important;
}

.search-result-list {
    margin-top: 0.5rem;
    gap: 0.25rem;
    max-height: calc(100vh - 50px - 10rem);
    overflow: auto;
}

.search-result {
    padding: 0.5rem;
    margin-top: 0.25rem;
}

.search-result:hover {
    background-color: var(--surface-color);
    cursor: pointer;
}

@media screen and (max-width: 768px) {
    .search-window {}
}
</style>