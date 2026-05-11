<template>
    <div>
        <div v-if="showFileDropOverlay"
             id="fileDropOverlay"
             @dragleave.prevent="() => toggleFileDropOverlay(false)"
             @drop.prevent="handleOverlayDrop">
            <div id="overlayContent">
                <p>{{ Localizer.get("files_droparea") }}</p>
                <span class="fa fa-upload" />
            </div>
        </div>
        <InputDialogue ref="input" />
    </div>
</template>

<script>
import Localizer from "../Localizer.js";
import SidebarManager from "../SidebarManager";
import InputDialogue from "./InputDialogue.vue";

const TEXT_SAMPLE_BYTES = 4096;
const ALLOWED_TEXT_CONTROL_CODES = new Set([9, 10, 12, 13]);
const CODE_FENCE_LANGUAGES = {
    ".json": "json",
    ".csv": "csv",
    ".xml": "xml",
    ".bpmn": "xml",
    ".py": "python",
    ".js": "javascript",
    ".log": "text",
};

export default {
    name: "FileDropHandler",
    components: { InputDialogue },
    emits: ["files-dropped", "text-dropped"],
    setup() {
        return { Localizer };
    },
    data() {
        return {
            showFileDropOverlay: false,
        };
    },
    methods: {
        async toggleFileDropOverlay(show) {
            this.showFileDropOverlay = show && !SidebarManager.isResizing();
        },

        async handleOverlayDrop(event) {
            const dataTransfer = event.dataTransfer;
            if (!dataTransfer) {
                return;
            }

            const draggedContentType = this.getDraggedContentType(dataTransfer);
            await this.toggleFileDropOverlay(false);

            if (draggedContentType === "files") {
                this.$emit("files-dropped", dataTransfer.files);
                return;
            }

            const text = dataTransfer.getData("text/plain");
            if (text) {
                this.$emit("text-dropped", text);
            }
        },

        // Textfile Handling

        getDraggedContentType(dataTransfer) {
            const items = Array.from(dataTransfer.items ?? []);
            const types = Array.from(dataTransfer.types ?? []);

            if (items.some(item => item.kind === "file") || types.includes("Files")) {
                return "files";
            }

            if (items.some(item => item.kind === "string" && item.type === "text/plain") ||
                types.includes("text/plain")) {
                return "text";
            }

            return null;
        },

        getFileExtension(file) {
            const fileName = file.name?.toLowerCase() ?? "";
            const dotIndex = fileName.lastIndexOf(".");
            return dotIndex >= 0 ? fileName.slice(dotIndex) : "";
        },

        async prepareFiles(fileList, onReadError) {
            const files = Array.from(fileList ?? []);
            if (files.length === 0) {
                return { cancelled: false, formattedText: [], uploadableFiles: [] };
            }

            const textFiles = [];
            const uploadableFiles = [];

            for (const file of files) {
                if (await this.isTextFileSafely(file)) {
                    textFiles.push(file);
                } else {
                    uploadableFiles.push(file);
                }
            }

            if (textFiles.length === 0) {
                return { cancelled: false, formattedText: [], uploadableFiles };
            }

            // Ask once per batch
            const textFileHandling = await this.askTextFileHandling();
            if (!textFileHandling) {
                return { cancelled: true, formattedText: [], uploadableFiles: [] };
            }

            if (textFileHandling === "upload") {
                return {
                    cancelled: false,
                    formattedText: [],
                    uploadableFiles: [...uploadableFiles, ...textFiles],
                };
            }

            return {
                cancelled: false,
                formattedText: await this.readTextFiles(textFiles, onReadError),
                uploadableFiles,
            };
        },

        async isTextFileSafely(file) {
            try {
                return await this.isTextFile(file);
            } catch (error) {
                console.warn("Failed to inspect file locally, uploading instead:", file.name, error);
                return false;
            }
        },

        async isTextFile(file) {
            // File.type and extensions are only metadata hints
            // Sniff the bytes so extensionless text files (e.g. Dockerfile) are handled like other text inputs
            const sample = await file.slice(0, TEXT_SAMPLE_BYTES).arrayBuffer();
            const bytes = new Uint8Array(sample);

            if (bytes.length === 0) {
                return true;
            }

            if (bytes.includes(0)) {
                return false;
            }

            // Fatal UTF-8 decoding rejects binary files that only happen not to contain NUL bytes
            let text;
            try {
                text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
            } catch {
                return false;
            }

            return !this.hasBinaryControlCharacters(text);
        },

        hasBinaryControlCharacters(text) {
            // Regular text may contain tab, newline, form-feed, and carriage return
            // Other C0 control characters are a strong signal that the file is binary
            for (let i = 0; i < text.length; i++) {
                const code = text.charCodeAt(i);
                if (code < 32 && !ALLOWED_TEXT_CONTROL_CODES.has(code)) {
                    return true;
                }
            }

            return false;
        },

        wrapInCodeFence(text, language = "") {
            const longestBacktickRun = Math.max(0, ...(text.match(/`+/g) ?? []).map(run => run.length));
            const fence = "`".repeat(Math.max(3, longestBacktickRun + 1));
            return `${fence}${language}\n${text}\n${fence}`;
        },

        formatTextFileContent(file, text) {
            const normalizedText = text.replace(/\r\n/g, "\n");
            const extension = this.getFileExtension(file);

            if (extension === ".md" || extension === ".markdown") {
                return normalizedText;
            }

            if (CODE_FENCE_LANGUAGES[extension]) {
                return this.wrapInCodeFence(normalizedText, CODE_FENCE_LANGUAGES[extension]);
            }

            return normalizedText;
        },

        async readTextFiles(files, onReadError) {
            return (await Promise.all(
                files.map(file => file.arrayBuffer()
                    .then(buffer => new TextDecoder("utf-8", { fatal: true }).decode(buffer))
                    .then(text => this.formatTextFileContent(file, text))
                    .catch(async error => {
                        if (onReadError) {
                            await onReadError(`Failed to read text file: ${file.name}\nError: ${error}`);
                        }
                        return null;
                    }))
            )).filter(text => text != null);
        },

        async askTextFileHandling() {
            return await new Promise(resolve => {
                this.$refs.input.showDialogue(
                    Localizer.get("files_textHandling_title"),
                    Localizer.get("files_textHandling_message"),
                    null,
                    {
                        handling: {
                            type: "select",
                            label: "",
                            default: "insert",
                            values: {
                                insert: Localizer.get("files_textHandling_insert"),
                                upload: Localizer.get("files_textHandling_upload"),
                            }
                        }
                    },
                    async values => resolve(values.handling),
                    async () => resolve(null)
                );
            });
        },
    },
}
</script>

<style scoped>
#fileDropOverlay {
    position: absolute;
    display: flex;
    height: calc(100% - 2rem); /* room for margin + border */
    width: calc(100% - 2rem); /* room for margin + border */
    background: color-mix(in srgb, var(--background-color) 80%, transparent); /* Adds opacity */
    color: var(--primary-color);
    align-items: center;
    justify-content: center;
    z-index: 2000;
    transition: opacity 0.2s ease;
    backdrop-filter: blur(3px);
    border: 3px dashed var(--primary-color);
    border-radius: 1rem;
    margin: 1rem;
}

#overlayContent {
    font-size: 1.5rem;
    text-align: center;
    pointer-events: none;
}
</style>
