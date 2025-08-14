<template>
<div class="file-preview d-flex">

    <div class="d-flex flex-row text-break">
        <!-- Icon changes based on upload status -->
        <div class="d-flex h-100 align-items-center me-1">
            <i :class="this.uploadStatus?.isUploading ? 'fa fa-spinner fa-spin' : 'fa fa-file-pdf'" />
        </div>

        <!-- File name -->
        <span class="d-flex flex-wrap me-1 align-items-start" :title="this.file.name">
            {{ this.getFilename() }}
        </span>

        <!-- Upload status text -->
        <span v-if="this.uploadStatus?.isUploading">
            {{ Localizer.get('uploadingFileText') }}
        </span>
    </div>

    <!-- Remove file from preview (but not from disk or server) -->
    <button
        type="button"
        class="btn btn-sm btn-outline-danger file-delete-button"
        @click="this.removeFile()"
        :disabled="this.isUploading"
        :title="Localizer.get('tooltipRemoveUploadedFile')" >
        <i class="fa fa-remove" />
    </button>
</div>
</template>

<script>
import conf from "../../config.js";
import {useDevice} from "../useIsMobile.js";
import Localizer from "../Localizer.js";

export default {
    name: "FilePreview",
    props: {
        file: Object,
        index: length,
        uploadStatus: Object,
    },
    setup() {
        const {isMobile} = useDevice();
        return {conf, Localizer, isMobile};
    },
    data() {
        return {};
    },
    emits: ['removeFile'],
    methods: {
        removeFile() {
            this.$emit('removeFile', this.index, this.file?.name);
        },

        getFilename() {
            const maxLength = 40;
            if (this.file?.name?.length > maxLength) {
                return `${this.file.name.slice(0, maxLength - 2)}…`;
            }
            return this.file?.name;
        },
    },
}
</script>

<style scoped>
.file-preview {
    overflow-wrap: anywhere;
    word-wrap: anywhere;
    padding: 0.5rem;
    margin: 0.25rem;
    max-width: min(100%, 40ch);
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
    text-align: left;
}

.file-delete-button {
    margin-left: auto;
    width: 1.5rem;
    height: 1.5rem;
    aspect-ratio: 1 / 1;
}
</style>