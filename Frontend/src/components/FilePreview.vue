<template>
<div class="file-preview d-flex">

    <div class="d-flex align-items-center">
        <!-- Icon changes based on upload status -->
        <i :class="this.isUploading ? 'fa fa-spinner fa-spin' : 'fa fa-file-pdf'" class="me-2" />

        <!-- File name -->
        <span class="me-2" :title="this.file.name">
            {{ this.getFilename() }}
        </span>

        <!-- Upload status text -->
        <span v-if="this.isUploading">{{ Localizer.get('uploadingFileText') }}</span>
    </div>

    <!-- Remove file from preview (but not from disk or server) -->
    <button
        type="button"
        class="btn btn-sm btn-outline-danger file-delete-button"
        @click="this.removeFile()"
        :disabled="this.isUploading"
        :title="Localizer.get('tooltipRemoveUploadedFile')"
    >
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
    },
    setup() {
        const {isMobile} = useDevice();
        return {conf, Localizer, isMobile};
    },
    data() {
        return {
            isUploading: false,
        }
    },
    emits: ['removeFile'],
    methods: {
        removeFile() {
            this.$emit('removeFile', this.index, this.filename);
        },

        getFilename() {
            if (this.file?.name?.length >= 32) {
                return `${this.file.name.slice(0, 30)}...`;
            }
            return this.file?.name;
        },
    },
}
</script>

<style scoped>
.file-preview {
    padding: 0.5rem;
    margin: 0.5rem;
    max-width: 40ch;
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
    text-align: left;
}

.file-delete-button {
    margin-left: auto;
    width: 1.5rem;
    height: 1.5rem;
    aspect-ratio: 1 / 1;
    z-index: 6789;
}
</style>