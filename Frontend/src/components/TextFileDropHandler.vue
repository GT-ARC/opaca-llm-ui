<template>
    <span class="d-none" aria-hidden="true" />
</template>

<script>
export default {
    name: "TextFileDropHandler",
    methods: {
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

        isTextFile(file) {
            const textExtensions = new Set([".txt", ".md", ".markdown", ".log", ".json", ".csv", ".xml", ".bpmn", ".py", ".js"]);

            const textMimeTypes = new Set([
                "text/plain",
                "text/markdown",
                "application/json",
                "text/json",
                "text/csv",
                "application/xml",
                "text/xml",
                "text/javascript",
                "application/javascript",
                "application/x-javascript",
                "text/x-python",
                "application/x-python-code",
            ]);

            const ext = this.getFileExtension(file);
            const hasTextExtension = textExtensions.has(ext);

            const type = file.type?.toLowerCase();
            const hasTextMime = textMimeTypes.has(type);

            return hasTextMime || hasTextExtension;
        },

        wrapDroppedTextInCodeFence(text, language = "") {
            const longestBacktickRun = Math.max(0, ...(text.match(/`+/g) ?? []).map(run => run.length));
            const fence = "`".repeat(Math.max(3, longestBacktickRun + 1));
            return `${fence}${language}\n${text}\n${fence}`;
        },

        formatDroppedFileText(file, text) {
            const normalizedText = text.replace(/\r\n/g, "\n");
            const extension = this.getFileExtension(file);
            const codeFenceLanguages = {
                ".json": "json",
                ".csv": "csv",
                ".xml": "xml",
                ".bpmn": "xml",
                ".py": "python",
                ".js": "javascript",
                ".log": "text",
            };

            if (extension === ".md" || extension === ".markdown") {
                return normalizedText;
            }

            if (codeFenceLanguages[extension]) {
                return this.wrapDroppedTextInCodeFence(normalizedText, codeFenceLanguages[extension]);
            }

            return normalizedText;
        },

        async readTextFiles(files, onReadError) {
            return (await Promise.all(
                files.map(file => file.text()
                    .then(text => this.formatDroppedFileText(file, text))
                    .catch(async error => {
                        if (onReadError) {
                            await onReadError(`Failed to read dropped file: ${file.name}\nError: ${error}`);
                        }
                        return null;
                    }))
            )).filter(text => text != null);
        },
    },
}
</script>
