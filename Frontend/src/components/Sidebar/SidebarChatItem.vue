<template>
    <div class="chat align-items-center"
         :class="{'chat-selected': this.selectedChatId === chatId}"
         :title="this.getTooltip()"
         @click="this.select()" >
        <input
            class="chat-name"
            v-model="nameInput"
            ref="nameInput"
            @click="e => this.handleInputClick(e)"
            @keyup.enter="e => this.handleSubmitName(e)"
            @change="e => this.handleSubmitName(e)"
            @blur="e => this.handleCancelName(e)"
            @keyup.esc="e => this.handleCancelName(e)"
            :disabled="!isEditingName"
        />
        <i v-if="isWorking()"
           class="fa fa-spin fa-spinner click-icon chat-status"
           :title="Localizer.get('chats_working')"
        />
        <i v-else-if="hasMissedResponse"
           class="fa fa-circle-exclamation click-icon chat-status chat-status-ready"
           :title="Localizer.get('chats_responseReady')"
        />
        <i class="fa fa-edit ms-auto click-icon"
           :class="{ disabled: !this.canModify() }"
           :aria-disabled="!this.canModify()"
           @click.stop="this.rename()"
           :title="Localizer.get('chats_edit')"
        />
        <i class="fa fa-remove click-icon click-icon-danger"
           :class="{ disabled: !this.canModify() }"
           :aria-disabled="!this.canModify()"
           @click.stop="this.delete()"
           :title="Localizer.get('chats_delete')"
        />
    </div>
</template>

<script>
import Localizer from "../../Localizer.js";

export default {
    name: 'SidebarChatItem',
    props: {
        selectedChatId: String,
        chatId: String,
        chat: Object,
        hasMissedResponse: Boolean,
    },
    emits: [
        'select-chat',
        'rename-chat',
        'delete-chat',
    ],
    setup() {
        return { Localizer }
    },
    data() {
        return {
            nameInput: '',
            isEditingName: false,
        };
    },
    methods: {
        select() {
            this.$emit('select-chat', this.chatId);
        },

        async rename() {
            if (!this.canModify()) return;
            this.isEditingName = true;
            await this.$nextTick();
            const input = this.$refs.nameInput;
            input.focus();
            input.select();
        },

        delete() {
            if (!this.canModify()) return;
            if (confirm(Localizer.get("chats_delete_confirm"))) {
                this.$emit('delete-chat', this.chatId);
            }
        },

        canModify() {
            return !this.isWorking();
        },

        isWorking() {
            return this.chat?.is_finished === false;
        },

        handleSubmitName(event) {
            if (!this.isEditingName) return;
            event.preventDefault();
            event.stopPropagation();
            this.isEditingName = false;
            const name = this.nameInput;
            this.$emit('rename-chat', this.chatId, this.nameInput);
            const input = this.$refs.nameInput;
            input.scrollLeft = 0;
            input.blur();
            this.nameInput = name;
        },

        handleCancelName(event) {
            if (!this.isEditingName) return;
            event.preventDefault();
            event.stopPropagation();
            this.isEditingName = false;
            const input = this.$refs.nameInput;
            input.blur();
            this.nameInput = this.chat.name ? this.chat.name : this.chatId;
        },

        handleInputClick(event) {
            if (this.isEditingName) {
                event.stopPropagation();
            }
        },

        getTooltip() {
            return `ID: ${this.chat.chat_id}\n` + 
                   //`Responses: ${this.chat.responses.length}\n` +  // XXX shows as zero?
                   `Active files: ${this.chat.active_files.length || "none"}\n` +
                   `Created: ${Localizer.toLocaleString(this.chat.time_created)}\n` +
                   `Modified: ${Localizer.toLocaleString(this.chat.time_modified)}`;
        },
    },
    mounted() {
        this.nameInput = this.chat.name ? this.chat.name : this.chatId;
    },
    watch: {
        chat() {
            if (this.isEditingName) return;
            this.nameInput = this.chat.name ? this.chat.name : this.chatId;
        }
    }
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
    background-color: var(--background-color);
    color: var(--text-primary-color);
}

.chat:hover {
    cursor: pointer;
    border-color: var(--primary-color);
    transform: translateY(-1px);
}

.chat-selected {
    border-color: var(--primary-color);
}

.chat-name {
    white-space: nowrap !important;
    text-overflow: clip !important;
    overflow: hidden !important;
    min-width: 0 !important;
    flex: 1;
    padding: 0;
    margin: 0;
    margin-right: 0.25rem !important;
    width: auto;
    background-color: var(--input-color);
    color: var(--text-primary-color);
    border: 1px solid var(--border-color);
    cursor: text;
}

.chat-name:disabled {
    background-color: var(--background-color);
    color: var(--text-primary-color);
    border: none;
    box-shadow: none;
    cursor: pointer;
    pointer-events: none; /* to propagate underlying pointer events */
}

.chat-name:focus {
    background-color: var(--input-color) !important;
    color: var(--text-primary-color);
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}

.chat-status,
.chat-status:hover {
    background-color: transparent;
    color: var(--text-primary-color);
    cursor: default;
}

.chat-status-ready,
.chat-status-ready:hover {
    color: var(--primary-color);
}
</style>
