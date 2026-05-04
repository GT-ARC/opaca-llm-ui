<template>
    <span class="d-none" aria-hidden="true" />
</template>

<script>
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
    name: "TextFileHandler",
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
    },
}
</script>
