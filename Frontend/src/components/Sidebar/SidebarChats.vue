<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div class="sidebar-title">
        {{ Localizer.get('sidebar_chats') }}
        <i class="fa fa-plus ms-auto sidebar-title-action"
           @click="this.$emit('new-chat')"
           :title="Localizer.get('chats_new')" />
        <i v-if="showHeaderActions"
           class="fa fa-magnifying-glass sidebar-title-action sidebar-title-action-secondary"
           :class="{ disabled: this.chats.length === 0 }"
           :aria-disabled="this.chats.length === 0"
           @click="toggleSearch"
           :title="Localizer.get('chats_search')" />
        <i v-if="showHeaderActions"
           class="fa fa-trash sidebar-title-action sidebar-title-action-danger"
           :class="{ disabled: this.chats.length === 0 }"
           :aria-disabled="this.chats.length === 0"
           @click="onDeleteAllChats"
           :title="Localizer.get('chats_deleteAll')" />
        <i class="fa sidebar-title-action sidebar-title-action-secondary"
           :class="showHeaderActions ? 'fa-angle-right' : 'fa-ellipsis'"
           @click="toggleHeaderActions"
           :title="Localizer.get(showHeaderActions ? 'sidebar_lessActions' : 'sidebar_moreActions')" />
    </div>

    <div v-if="isSearching">
        <input v-model="searchQuery"
               ref="searchBar"
               type="search"
               class="form-control my-2"
               :placeholder="Localizer.get('chats_search')"
               @input="updateSearchResults"
               @keyup.enter="updateSearchResults"
               @keyup.esc="closeSearch" />

        <div v-if="isLoadingResults" class="py-2 text-center text-muted">
            <i class="fa fa-circle-notch fa-spin" />
        </div>

        <div v-if="Object.keys(searchResults).length > 0" class="sidebar-search-results">
            <div v-for="(results, chatId) in searchResults"
                 :key="chatId"
                 class="sidebar-search-result-group">
                <div class="sidebar-search-result-heading">
                    {{ results?.[0].chat_name }}
                </div>
                <div v-for="(result, index) in results"
                     :key="index"
                     class="sidebar-search-result-context sidebar-search-result-clickable"
                     @click="gotoSearchResult(result.chat_id, result.message_id)">
                    {{ result.excerpt }}
                </div>
            </div>
        </div>
    </div>

    <!-- List all the chats -->
    <div v-for="chat in visibleChats" :key="chat.chat_id">
        <SidebarChatItem
            :selected-chat-id="this.selectedChatId"
            :chat-id="chat.chat_id"
            :chat="chat"
            :has-missed-response="isChatMissed(chat.chat_id)"
            @select-chat="chatId => this.$emit('select-chat', chatId)"
            @delete-chat="chatId => this.$emit('delete-chat', chatId)"
            @rename-chat="(chatId, name) => this.$emit('rename-chat', chatId, name)"
        />
    </div>
</div>
</template>

<script>
import Localizer from "../../Localizer.js";
import {useDevice} from "../../useIsMobile.js";
import {nextTick} from "vue";
import backendClient from "../../utils.js";
import SidebarChatItem from "./SidebarChatItem.vue";

export default {
    name: 'SidebarChats',
    components: {SidebarChatItem},
    props: {
        selectedChatId: String,
        chats: Array,
    },
    setup() {
        const {isMobile} = useDevice();
        return { Localizer, isMobile};
    },
    emits: [
        'select-chat',
        'delete-chat',
        'rename-chat',
        'new-chat',
        'goto-search-result',
        'delete-all-chats',
        'update-chats',
    ],
    data() {
        return {
            missedResponseChatIds: [],
            showHeaderActions: false,
            isSearching: false,
            searchQuery: '',
            searchResults: {},
            isLoadingResults: false,
        };
    },
    methods: {
        toggleHeaderActions() {
            this.showHeaderActions = !this.showHeaderActions;
            if (!this.showHeaderActions) {
                this.closeSearch();
            }
        },

        async toggleSearch() {
            if (this.isSearching) {
                this.closeSearch();
                return;
            }
            this.isSearching = true;
            await nextTick();
            this.$refs.searchBar?.focus();
        },

        closeSearch() {
            this.isSearching = false;
            this.searchQuery = '';
            this.searchResults = {};
            this.isLoadingResults = false;
        },

        async updateSearchResults() {
            const query = this.searchQuery;
            this.searchResults = {};

            if (query.length < 3) {
                this.isLoadingResults = false;
                return;
            }

            this.isLoadingResults = true;
            try {
                const results = await backendClient.search(query);
                if (query !== this.searchQuery) return;
                this.searchResults = results;
            } catch (error) {
                console.error(error);
                if (query === this.searchQuery) {
                    this.searchResults = {};
                }
            } finally {
                if (query === this.searchQuery) {
                    this.isLoadingResults = false;
                }
            }
        },

        async updateChats() {
            this.$emit('update-chats');
        },

        markChatMissed(chatId) {
            if (!chatId || this.missedResponseChatIds.includes(chatId)) return;
            this.missedResponseChatIds = [...this.missedResponseChatIds, chatId];
        },

        clearChatMissed(chatId = null) {
            if (chatId) {
                this.missedResponseChatIds = this.missedResponseChatIds.filter(id => id !== chatId);
            } else {
                this.missedResponseChatIds = [];
            }
        },

        isChatMissed(chatId) {
            return this.missedResponseChatIds.includes(chatId);
        },

        gotoSearchResult(chatId, messageId) {
            this.closeSearch();
            this.$emit('goto-search-result', chatId, messageId)
        },

        onDeleteAllChats() {
            if (confirm(Localizer.get('chats_deleteAll_confirm'))) {
                this.$emit('delete-all-chats');
            }
        },
    },
    computed: {
        visibleChats() {
            const query = this.searchQuery.trim().toLowerCase();
            if (!query) return this.chats;

            const matchingChatIds = new Set(Object.keys(this.searchResults));
            return this.chats.filter(chat =>
                chat.name?.toLowerCase().includes(query)
                || matchingChatIds.has(chat.chat_id)
            );
        },
    },
    mounted() {
        //this.updateChats(); // ... is called in this stage, but moved to App.mounted to fix concurrency issues
    },
}
</script>
