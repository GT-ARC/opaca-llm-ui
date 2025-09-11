<template>
    <div class="file align-items-center">
        <i :class="[
            'fa',
            file.suspended ? 'fa-toggle-off' : 'fa-toggle-on',
            'ms-auto',
            'file-menu-button'
            ]"
           @click.stop="this.suspendFile()"
           :title="Localizer.get('tooltipSuspendUploadedFile')"
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
    data() {},
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
        this.nameInput = this.file.name ? this.file.name : this.fileId;
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
</style>