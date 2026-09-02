<template>
    <div class="container flex-grow-1 overflow-hidden overflow-y-auto">
        <div class="sidebar-title">
            {{ Localizer.get('sidebar_files') }}
            <i class="fa fa-plus ms-auto sidebar-title-action"
               @click="this.$emit('upload-file')"
               :title="Localizer.get('files_upload')" />
            <i class="fa fa-magnifying-glass sidebar-title-action sidebar-title-action-secondary"
               :class="{ disabled: Object.keys(files).length === 0 }"
               :aria-disabled="Object.keys(files).length === 0"
               @click="$refs.search.toggleSearch()"
               :title="Localizer.get('files_search')" />
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

        <GenericSearch
            ref="search"
            :items="files"
            :placeholder="Localizer.get('files_search')"
            :get-item-search-values="fileSearchValues"
            :get-item-context-preview="fileContextPreview"
        >
            <template #default="{ filteredItems }">
                <!-- List all the files -->
                <div v-for="file in filteredItems" :key="file.file_id">
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
            </template>
        </GenericSearch>
    </div>
</template>

<script>
import Localizer from "../../Localizer.js";
import {useDevice} from "../../useIsMobile.js";
import backendClient from "../../utils.js";
import GenericSearch from "../GenericSearch.vue";
import SidebarFileItem from "./SidebarFileItem.vue";

export default {
    name: 'SidebarFiles',
    components: {GenericSearch, SidebarFileItem},
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
        fileSearchValues(file) {
            return [file.file_name, ...(file.keywords ?? [])];
        },

        fileContextPreview(file, _query, {matches, getMatchExcerpt}) {
            const matchedKeyword = (file.keywords ?? []).find(matches);
            const matchedText = matchedKeyword ?? file.file_name;
            return {
                key: file.file_id,
                path: file.file_name,
                context: getMatchExcerpt(matchedText),
            };
        },

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
