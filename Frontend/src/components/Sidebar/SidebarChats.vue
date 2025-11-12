<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <SearchChatsOverlay
        v-if="isSearching"
        :is-searching="isSearching"
        :chats="chats"
        @stop-search="this.isSearching = false"
        @goto-search-result="this.gotoSearchResult"
    />

    <div v-if="!isMobile" class="sidebar-title">
        {{ Localizer.get('tooltipSidebarChats') }}
    </div>

    <div class="d-grid gap-2">
        <!-- "New Chat" button -->
        <button type="button"
                class="btn btn-primary py-2 w-100"
                @click="this.$emit('new-chat')"
                :disabled="!this.isFinished" >
            <i class="fa fa-pen-to-square" />
            {{ Localizer.get('buttonNewChat') }}
        </button>

        <!-- "Search" button -->
        <button type="button"
                class="btn btn-secondary py-2 w-100"
                @click="this.isSearching = true"
                :disabled="!this.isFinished" >
            <i class="fa fa-magnifying-glass" />
            {{ Localizer.get('buttonSearchChats') }}
        </button>

        <!-- "Delete All Chats" button -->
        <button type="button"
                class="btn btn-danger py-2 w-100"
                @click="onDeleteAllChats"
                :disabled="!this.isFinished || this.chats.length === 0">
            <i class="fa fa-trash" />
            {{ Localizer.get('buttonDeleteAllChats') }}
        </button>
    </div>

    <!-- List all the chats -->
    <div v-for="chat in chats" :key="chat.chat_id">
        <SidebarChatItem
            :selected-chat-id="this.selectedChatId"
            :is-finished="this.isFinished"
            :chat-id="chat.chat_id"
            :chat="chat"
            @select-chat="chatId => this.$emit('select-chat', chatId)"
            @delete-chat="chatId => this.$emit('delete-chat', chatId)"
            @rename-chat="(chatId, name) => this.$emit('rename-chat', chatId, name)"
        />
    </div>
</div>
</template>

<script>
import conf from "../../../config.js";
import Localizer from "../../Localizer.js";
import {useDevice} from "../../useIsMobile.js";
import backendClient from "../../utils.js";
import SidebarChatItem from "./SidebarChatItem.vue";
import SearchChatsOverlay from "../SearchChatsOverlay.vue";

export default {
    name: 'SidebarChats',
    components: {SearchChatsOverlay, SidebarChatItem},
    props: {
        selectedChatId: String,
        isFinished: Boolean,
    },
    setup() {
        const {isMobile} = useDevice();
        return {conf, Localizer, isMobile};
    },
    emits: [
        'select-chat',
        'delete-chat',
        'rename-chat',
        'new-chat',
        'goto-search-result',
        'delete-all-chats',
    ],
    data() {
        return {
            chats: [],
            showChatMenu: false,
            isSearching: false,
        };
    },
    methods: {
        async updateChats() {
            try {
                this.chats = await backendClient.chats();
            } catch (error) {
                console.error(error);
                this.chats = [];
            }
        },

        gotoSearchResult(chatId, messageId) {
            this.isSearching = false;
            this.$emit('goto-search-result', chatId, messageId)
        },

        onDeleteAllChats() {
            if (confirm(Localizer.get('confirmDeleteAllChats'))) {
                this.$emit('delete-all-chats');
            }
        },
    },
    mounted() {
        //this.updateChats(); // ... is called in this stage, but moved to App.mounted to fix concurrency issues
    },
}
</script>

<style scoped>
</style>