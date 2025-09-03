<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div v-if="!isMobile" class="sidebar-title">
        {{ Localizer.get('tooltipSidebarChats') }}
    </div>

    <!-- "New Chat" button -->
    <button type="button"
            class="btn btn-primary w-100"
            @click="this.$emit('new-chat')"
            :disabled="!this.isFinished" >
        <i class="fa fa-pen-to-square" />
        {{ Localizer.get('buttonNewChat') }}
    </button>

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

export default {
    name: 'SidebarChats',
    components: {SidebarChatItem},
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
    ],
    data() {
        return {
            chats: [],
            showChatMenu: false,
        };
    },
    methods: {
        async updateChats() {
            try {
                this.chats = await backendClient.chats();
            } catch (error) {
                console.log(error);
                this.chats = [];
            }
        },
    },
    mounted() {
        this.updateChats();
    },
}
</script>

<style scoped>
</style>