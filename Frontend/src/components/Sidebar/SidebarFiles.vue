<template>
    <div class="container flex-grow-1 overflow-hidden overflow-y-auto">
        <div class="sidebar-title">
            {{ Localizer.get('sidebar_files') }}
            <i class="fa fa-plus ms-auto sidebar-title-action"
               @click="this.$emit('upload-file')"
               :title="Localizer.get('files_upload')" />
            <i class="fa fa-trash sidebar-title-action sidebar-title-action-danger"
               :class="{ disabled: Object.keys(files).length === 0 }"
               :aria-disabled="Object.keys(files).length === 0"
               @click="onDeleteAllFiles"
               :title="Localizer.get('files_deleteAll')" />
        </div>

        <!-- Show info if no files -->
        <div v-if="Object.keys(files).length === 0" class="sidebar-empty-state">
            {{ Localizer.get('files_missing') }}
        </div>

        <!-- List all the files -->
        <div v-for="file in files" :key="file.file_id">
            <SidebarFileItem
                :file-id="file.file_id"
                :file="file"
                :selectedChatId="this.selectedChatId"
                :chats="this.chats"
                @delete-file="fileId => this.$emit('delete-file', fileId)"
                @view-file="$emit('view-file', $event)"
                @rename-file="(fileId, newName) => this.$emit('rename-file', fileId, newName)"
                @update-chats="() => this.$emit('update-chats')"
                @update-files="() => this.updateFiles()"
            />
        </div>
    </div>
</template>

<script>
import Localizer from "../../Localizer.js";
import {useDevice} from "../../useIsMobile.js";
import backendClient from "../../utils.js";
import SidebarFileItem from "./SidebarFileItem.vue";

export default {
    name: 'SidebarFiles',
    components: {SidebarFileItem},
    props: {
        selectedChatId: String,
        chats: Array,
    },
    setup() {
        const {isMobile} = useDevice();
        return {Localizer, isMobile};
    },
    emits: [
        'delete-file',
        'delete-all-files',
        'upload-file',
        'view-file',
        'rename-file',
        'update-chats',
    ],
    data() {
        return {
            files: {},
        };
    },
    methods: {
        async updateFiles() {
            try {
                this.files = await backendClient.files();
            } catch (error) {
                console.log(error);
                this.files = {};
            }
        },

        onDeleteAllFiles() {
            if (confirm(Localizer.get('files_deleteAll_confirm'))) {
                this.$emit('delete-all-files');
            }
        },
    },
    mounted() {
        //this.updateFiles(); // ... is called in this stage, but moved to App.mounted to fix concurrency issues
    },
}
</script>

<style scoped>
</style>
