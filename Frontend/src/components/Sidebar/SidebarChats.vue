<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div v-if="!isMobile" class="sidebar-title">
        {{ Localizer.get('tooltipSidebarChats') }}
    </div>

    <!-- "New Chat" button -->
    <button type="button" class="btn btn-primary w-100" @click="this.$emit('new-chat')" >
        <i class="fa fa-pen-to-square" />
        {{ Localizer.get('buttonNewChat') }}
    </button>

    <!-- List all the chats -->
    <div v-for="chat in chats" :key="chat.chat_id">
        <div class="chat align-items-center" :class="{'chat-selected': this.selectedChatId === chat.chat_id}"
             @click="this.$emit('select-chat', chat.chat_id)" >
            <span>
                {{ (chat.name ? chat.name : chat.chat_id)?.slice(0, 32) }}
            </span>
            <i class="fa fa-remove chat-menu-button"
               @click="this.$emit('delete-chat', chat.chat_id)"
            />
        </div>
    </div>
</div>
</template>

<script>
import conf from "../../../config.js";
import Localizer from "../../Localizer.js";
import {useDevice} from "../../useIsMobile.js";
import backendClient from "../../utils.js";
import * as uuid from "uuid";

export default {
    name: 'SidebarChats',
    props: {
        selectedChatId: String,
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
            }
        }
    },
    mounted() {
        this.updateChats();
    },
}
</script>

<style scoped>
.chat {
    display: flex;
    padding: 0.5rem 0.5rem 0.5rem 1rem;
    margin-top: 0.5rem;
    border: 1px solid var(--border-color);
    border-radius: 50rem;
    width: 100%;
}

.chat:hover {
    border-color: var(--primary-color);
    cursor: pointer;
}

.chat-selected {
    border-color: var(--primary-color);
}

.chat-menu-button {
    width: 2rem;
    height: 2rem;
    padding: 0;
    aspect-ratio: 1 / 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    align-self: flex-end;
    border-radius: 1rem !important;
    margin-left: auto;
    cursor: pointer;
}

.chat-menu-button:hover {
    background-color: var(--input-color) !important;
    color: var(--text-danger-color) !important;
}

.chat-menu {
    position: absolute;

}
</style>