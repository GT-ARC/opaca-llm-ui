<template>
<div class="file-preview d-flex">

    <div class="d-flex flex-row text-break"
        @click="this.viewFile()">
        <!-- Icon changes based on upload status -->
        <div class="d-flex h-100 align-items-center me-1">
            <i :class="this.isUploading ? 'fa fa-spinner fa-spin' : 'fa fa-file-pdf'" />
        </div>

        <!-- File name -->
        <span class="d-flex flex-wrap me-1 align-items-start" :title="this.file.name">
            {{ this.getFilename() }}
        </span>

        <!-- Upload status text -->
        <span v-if="this.isUploading">
            {{ Localizer.get('uploadingFileText') }}
        </span>
    </div>

    <!-- Remove file from preview (and also from server) -->
    <button
        type="button"
        class="btn btn-sm btn-outline-danger file-delete-button"
        @click="this.removeFile()"
        :disabled="this.isUploading"
        :title="Localizer.get('tooltipDeleteUploadedFile')" >
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
        fileId: String,
        file: Object,
        isUploading: Boolean,
    },
    setup() {
        const {isMobile} = useDevice();
        return {conf, Localizer, isMobile};
    },
    data() {
        return {};
    },
    emits: ['remove-file', 'view-file'],
    methods: {
        removeFile() {
            this.$emit('remove-file', this.fileId);
        },

        getFilename() {
            const maxLength = 40;
            if (this.file?.name?.length > maxLength) {
                return `${this.file.name.slice(0, maxLength - 2)}…`;
            }
            return this.file?.name;
        },

        viewFile() {
            this.$emit('view-file', {
                fileName: this.file.name,
                src: this.file.url || URL.createObjectURL(this.file),
                mimeType: this.file.content_type || this.file.type
            });
        }
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
    cursor: pointer;
}

.file-delete-button {
    margin-left: auto;
    width: 1.5rem;
    height: 1.5rem;
    aspect-ratio: 1 / 1;
}
</style>