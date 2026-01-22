<template>
    <div class="container flex-grow-1 overflow-hidden overflow-y-auto">
        <div v-if="!isMobile" class="sidebar-title">
            {{ Localizer.get('tooltipSidebarFiles') }}
        </div>

        <!-- Show info if no files -->
        <div v-if="Object.keys(files).length === 0" class="empty-files text-secondary text-sm p-4">
            {{ Localizer.get('sidebarFilesEmpty') }}
        </div>

        <!-- List all the files -->
        <div v-for="file in files" :key="file.file_id">
            <SidebarFileItem
                :file-id="file.file_id"
                :file="file"
                @delete-file="fileId => this.$emit('delete-file', fileId)"
                @suspend-file="(fileId, suspend) => this.$emit('suspend-file', fileId, suspend)"
                @view-file="$emit('view-file', $event)"
            />
        </div>
    </div>
</template>

<script>
import conf from "../../../config.js";
import Localizer from "../../Localizer.js";
import {useDevice} from "../../useIsMobile.js";
import backendClient from "../../utils.js";
import SidebarFileItem from "./SidebarFileItem.vue";

export default {
    name: 'SidebarFiles',
    components: {SidebarFileItem},
    props: {},
    setup() {
        const {isMobile} = useDevice();
        return {conf, Localizer, isMobile};
    },
    emits: [
        'delete-file',
        'suspend-file',
        'view-file',
    ],
    data() {
        return {
            files: {},
            showFileMenu: false,
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
    },
    mounted() {
        //this.updateFiles(); // ... is called in this stage, but moved to App.mounted to fix concurrency issues
    },
}
</script>

<style scoped>
</style>