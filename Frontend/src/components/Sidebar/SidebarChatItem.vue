<template>
<div class="chat align-items-center"
     :class="{'chat-selected': this.selectedChatId === chatId, 'chat-selectable': this.isFinished}"
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
        disabled
    />
    <i class="fa fa-edit ms-auto chat-menu-button"
       :class="{'chat-selectable': this.isFinished}"
       @click.stop="this.rename()"
       :title="Localizer.get('tooltipEditChatName')"
    />
    <i class="fa fa-remove chat-menu-button"
       :class="{'chat-selectable': this.isFinished}"
       @click.stop="this.delete()"
       :title="Localizer.get('tooltipDeleteChat')"
    />
</div>
</template>

<script>
import Localizer from "../../Localizer.js";

export default {
    name: 'SidebarChatItem',
    props: {
        selectedChatId: String,
        isFinished: Boolean,
        chatId: String,
        chat: Object,
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
            if (!this.isFinished) return;
            this.$emit('select-chat', this.chatId);
        },

        rename() {
            if (!this.isFinished) return;
            this.isEditingName = true;
            const input = this.$refs.nameInput;
            input.disabled = false;
            input.focus();
            input.select();
        },

        delete() {
            if (!this.isFinished) return;
            this.$emit('delete-chat', this.chatId);
        },

        handleSubmitName(event) {
            event.preventDefault();
            event.stopPropagation();
            this.isEditingName = false;
            const name = this.nameInput;
            this.$emit('rename-chat', this.chatId, this.nameInput);
            console.log('rename-chat', this.chatId, name);
            const input = this.$refs.nameInput;
            input.disabled = true;
            input.blur();
            this.nameInput = name; // reset input after blur triggered cancel
        },

        handleCancelName(event) {
            event.preventDefault();
            event.stopPropagation();
            this.isEditingName = false;
            const input = this.$refs.nameInput;
            input.disabled = true;
            input.blur();
            this.nameInput = this.chat.name ? this.chat.name : this.chatId;
        },

        handleInputClick(event) {
            if (this.isEditingName) {
                event.stopPropagation();
            }
        },
    },
    mounted() {
        this.nameInput = this.chat.name ? this.chat.name : this.chatId;
    },
    watch: {
        chat() {
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

/* overwrite when selectable */
.chat:hover {
    cursor: not-allowed;
}

.chat-selected {
    border-color: var(--primary-color);
}

.chat-selectable:hover {
    border-color: var(--primary-color) !important;
    cursor: pointer !important;
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
    background-color: var(--input-color);
    color: var(--text-primary-color);
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}

.chat-menu-button {
    flex: 0 0 auto;
    width: 2rem;
    height: 2rem;
    padding: 0;
    aspect-ratio: 1 / 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    align-self: flex-end;
    border-radius: 1rem !important;
    cursor: not-allowed;
    z-index: 9999 !important;
}

.chat-menu-button:hover {
    background-color: var(--input-color) !important;
    color: var(--text-danger-color) !important;
}
</style>