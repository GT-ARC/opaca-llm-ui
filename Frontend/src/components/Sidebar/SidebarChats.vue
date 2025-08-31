<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div v-if="!isMobile" class="sidebar-title">
        {{ Localizer.get('tooltipSidebarChats') }}
    </div>

    <div v-for="chat in chats" :key="chat.chat_id">
        {{JSON.stringify(chat)}}
    </div>
</div>
</template>

<script>
import conf from "../../../config.js";
import Localizer from "../../Localizer.js";
import {useDevice} from "../../useIsMobile.js";
import backendClient from "../../utils.js";

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
    ],
    data() {
        return {
            chats: [],
        };
    },
    methods: {

    },
    async mounted() {
        this.chats = await backendClient.chats();
    },
}
</script>

<style scoped>

</style>