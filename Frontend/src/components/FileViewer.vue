<template>
    <div v-if="visible" class="file-viewer-overlay">
        <div class="file-viewer">
            <button class="close-btn" @click="$emit('close')">
                <i class="fa fa-times"></i>
            </button>

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
</template>

<script>
export default {
  name: 'FileViewer',
  props: {
    src: String,   // can be blob:... or https://...
    mimeType: String,
    visible: Boolean
  },
  emits: ['close'],
  computed: {
    isImage() {
      return this.mimeType && this.mimeType.startsWith('image/')
    },
    isPdf() {
      return this.mimeType === 'application/pdf'
    }
  }
}
</script>

<style scoped>
.file-viewer-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.75);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
}
.file-viewer {
    background: white;
    border-radius: 8px;
    width: 90%;
    height: 90%;
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}
.viewer-content {
    flex: 1;
    border: none;
    object-fit: contain;
    width: 100%;
    height: 100%;
}
.close-btn {
    position: absolute;
    top: 10px;
    right: 10px;
    background: none;
    border: none;
    color: #333;
    font-size: 1.5rem;
    cursor: pointer;
}
</style>
