<template>
    <div class="file align-items-center" :class="{ 'file-suspended': file.suspended }">
        <div class="file-name"> {{file.file_name}} </div>
        <i :class="[
            'fa fa-lg',
            file.suspended ? 'fa-toggle-off' : 'fa-toggle-on',
            'ms-auto',
            'file-menu-button'
            ]"
           @click.stop="this.suspendFile()"
           :title="Localizer.get(file.suspended ? 'tooltipUnsuspendUploadedFile' : 'tooltipSuspendUploadedFile')"
        />
        <i class="fa fa-remove file-menu-button"
           @click.stop="this.deleteFile()"
           :title="Localizer.get('tooltipDeleteUploadedFile')"
        />
    </div>
</template>

<script>
import Localizer from "../../Localizer.js";

export default {
    name: 'SidebarFileItem',
    props: {
        fileId: String,
        file: Object,
    },
    emits: [
        'delete-file',
        'suspend-file'
    ],
    setup() {
        return { Localizer }
    },
    data() {
        return {}
    },
    methods: {
        deleteFile() {
            if (confirm(Localizer.get("confirmDeleteFile"))) {
                this.$emit('delete-file', this.fileId);
            }
        },

        suspendFile() {
            this.$emit('suspend-file', this.fileId, !this.file.suspended);
        }
    },
    mounted() {
    },
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
}

.file:hover {
    cursor: pointer;
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
    color: var(--text-primary-color);
}

.file-suspended .file-name {
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

</style>