<template>
    <div v-if="visible" class="file-viewer-overlay" @click.stop="$emit('close')">
        <div class="file-viewer-wrapper" @click.stop>
            <div class="file-viewer-header">
                <span class="file-name">{{ fileName }}</span>
                <button class="btn close-btn" @click="$emit('close')">
                    <i class="fa fa-times"></i>
                </button>
            </div>
            <div class="file-viewer">
                <!-- Image -->
                <img v-if="isImage" :src="src" alt="Preview" class="viewer-content" />

                <!-- PDF -->
                <iframe v-else-if="isPdf" :src="src" class="viewer-content" />

                <!-- Unsupported -->
                <div v-else class="unsupported">
                    <p>Preview not available for this file type.</p>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: 'FileViewer',
    props: {
        fileName: String,
        src: String,   // can be blob:... or https://...
        mimeType: String,
        visible: Boolean
    },
    emits: ['close'],
    computed: {
        isImage() {
            return this.mimeType && this.mimeType.startsWith('image/');
        },
        isPdf() {
            return this.mimeType === 'application/pdf';
        },
        fileName() {
            return this.fileName;
        }
    }
}
</script>

<style scoped>
.file-viewer-overlay {
    position: absolute;
    inset: 0;
    background: color-mix(in srgb, var(--background-color) 80%, transparent);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    padding: 0 1rem 1rem 1rem;
}

.file-viewer-wrapper {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    max-width: 1600px;
    background-color: #282828;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: var(--shadow-md);
}

.file-viewer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.25rem 1rem;
    font-weight: bold;
    color: var(--text-primary-dark);
}

.file-viewer {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
}

.viewer-content {
    flex: 1;
    object-fit: contain;
    width: 100%;
    height: 100%;
    padding: 0 10px 10px; /* no padding below title bar */
}

.close-btn {
    width: 25px;
    height: 25px;
    padding: 0;
    border-radius: 50%;
    cursor: pointer;
    color: var(--button-primary-dark);
}

.close-btn:hover {
    background-color: var(--border-dark);
}
</style>
