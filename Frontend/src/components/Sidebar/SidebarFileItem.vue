<template>
    <div class="file align-items-center"
         :class="{ 'file-suspended': file.suspended }"
         @click.stop="this.viewFile()">
        <input
            class="file-name"
            v-model="nameInput"
            ref="nameInput"
            @click="e => this.handleInputClick(e)"
            @keyup.enter.prevent.stop="e => this.handleSubmitName(e)"
            @change.prevent.stop="e => this.handleSubmitName(e)"
            @blur.prevent.stop="e => this.handleCancelName(e)"
            @keyup.esc.prevent.stop="e => this.handleCancelName(e)"
            disabled
        />
        <i :class="[
            'fa fa-lg',
            file.suspended ? 'fa-toggle-off' : 'fa-toggle-on',
            'ms-auto',
            'file-menu-button'
            ]"
           @click.stop="this.suspendFile()"
           :title="Localizer.get('sidebar_files_include')"
        />
        <i class="fa fa-pen-to-square file-menu-button"
           @click.stop="this.renameFile()"
        />
        <i class="fa fa-remove file-menu-button"
           @click.stop="this.deleteFile()"
           :title="Localizer.get('sidebar_files_delete')"
        />
    </div>
</template>

<script>
import Localizer from "../../Localizer.js";
import config from "../../../config.js";
import {nextTick} from "vue";

const BACKEND_ADDRESS = config.BackendAddress;

export default {
    name: 'SidebarFileItem',
    props: {
        fileId: String,
        file: Object,
    },
    emits: [
        'delete-file',
        'suspend-file',
        'view-file',
        'rename-file',
    ],
    setup() {
        return { Localizer }
    },
    data() {
        return {
            nameInput: '',
            isEditingName: false,
        }
    },
    methods: {
        deleteFile() {
            if (confirm(Localizer.get("sidebar_files_delete_confirm", this.file.file_name))) {
                this.$emit('delete-file', this.fileId);
            }
        },

        suspendFile() {
            this.$emit('suspend-file', this.fileId, !this.file.suspended);
        },

        viewFile() {
            this.$emit('view-file', {
                fileName: this.file.file_name,
                src: `${BACKEND_ADDRESS}/files/${this.fileId}/view`,
                mimeType: this.file.content_type
            });
        },

        async renameFile() {
            this.nameInput = this.nameInput.replace(/\.[^.]+$/, "");
            await nextTick(); // necessary for the input.select() below to properly work
            this.isEditingName = true;
            const input = this.$refs.nameInput;
            input.disabled = false;
            input.focus();
            input.select();
        },

        handleSubmitName(event) {
            event.preventDefault();
            event.stopPropagation();
            this.isEditingName = false;
            const name = this.nameInput;
            this.$emit('rename-file', this.fileId, this.nameInput);
            const input = this.$refs.nameInput;
            input.disabled = true;
            input.scrollLeft = 0;
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
            this.nameInput = this.file.file_name;
        },

        handleInputClick(event) {
            if (this.isEditingName) {
                event.stopPropagation();
            }
        },

    },
    mounted() {
        this.nameInput = this.file.file_name;
    },
    watch: {
        file(newFile) {
            this.nameInput = newFile.file_name;
        }
    }
}
</script>

<style scoped>
.file {
    display: flex;
    padding: 0.5rem 0.5rem 0.5rem 1rem;
    margin-top: 0.5rem;
    border: 1px solid var(--border-color);
    border-radius: 50rem;
    width: 100%;
    background-color: var(--background-color);
    color: var(--text-primary-color);
    cursor: pointer;
}

.file:hover {
    border-color: var(--primary-color);
    transform: translateY(-1px);
}

.file-suspended {
    background: color-mix(in srgb, var(--background-color) 40%, transparent);
}

.file-name {
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

.file-name:disabled {
    background-color: var(--background-color);
    color: var(--text-primary-color);
    border: none;
    box-shadow: none;
    cursor: pointer;
    pointer-events: none; /* to propagate underlying pointer events */
}

.file-name:focus {
    background-color: var(--input-color) !important;
    color: var(--text-primary-color);
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}

.file-suspended .file-name:disabled {
    opacity: 0.5;
}

.file-menu-button {
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
    cursor: pointer;
}

.file-menu-button:hover {
    background-color: var(--input-color);
    color: var(--text-danger-color);
}

.fa-toggle-off {
    color: var(--text-secondary-color);
}

.fa-toggle-on {
    color: var(--text-success-color);
}

</style>