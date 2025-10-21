<!-- Personal Prompt Editor Component -->
<template>
    <div class="prompt-editor-overlay">
        <div class="prompt-editor-card">
            <h5>{{ prompt && prompt.question ? Localizer.get('editQuestion') : Localizer.get('addPersonalQuestion') }}</h5>

            <label class="prompt-editor-label">Prompt Text</label>
            <textarea v-model="localPrompt.question" class="form-control" rows="4"></textarea>

            <label class="prompt-editor-label">Icon</label>
            <div class="emoji-input-wrapper" ref="emojiWrapper">
                <input v-model="localPrompt.icon"
                       class="form-control emoji-picker-input"
                       maxlength="2"
                       readonly
                       @click="toggleEmojiPicker"
                />
                <!-- Emoji Picker Dropdown -->
                <div v-if="showEmojiPicker" class="emoji-picker-dropdown" @click.stop>
                    <EmojiPicker @select="onEmojiSelect" :native="true"/>
                </div>
            </div>

            <div class="d-flex justify-content-end gap-2 mt-3">
                <button class="btn btn-secondary" @click="$emit('cancel')">Cancel</button>
                <button class="btn btn-primary" @click="save">Save</button>
            </div>
        </div>
    </div>
</template>

<script>
import EmojiPicker from "vue3-emoji-picker";
import "vue3-emoji-picker/css";
import Localizer from "../Localizer.js"

export default {
    name: "PromptEditor",
    components: { EmojiPicker },
    setup() {
        return { Localizer }
    },
    props: {
        prompt: { type: Object, default: null },
    },
    data() {
        return {
            localPrompt: this.prompt ? { ...this.prompt } : { question: "", icon: "⭐" },
            showEmojiPicker: false,
        };
    },

    methods: {
        save() {
            if (!this.localPrompt.question.trim()) return;
            this.$emit("save", { ...this.localPrompt });
        },

        toggleEmojiPicker() {
            this.showEmojiPicker = !this.showEmojiPicker;
        },

        onEmojiSelect(emoji) {
            this.localPrompt.icon = emoji.i;
            this.showEmojiPicker = false;
        },

        handleClickOutside(event) {
            // Close emoji picker if open and click is outside both the input and picker
            if (
                this.showEmojiPicker &&
                this.$refs.emojiWrapper &&
                !this.$refs.emojiWrapper.contains(event.target)
            ) {
                this.showEmojiPicker = false;
            }
        },
    },
    mounted() {
        document.addEventListener("click", this.handleClickOutside);
    },
    beforeUnmount() {
        document.removeEventListener("click", this.handleClickOutside);
    },
};
</script>

<style scoped>
.prompt-editor-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 9999;
}
.prompt-editor-card {
    background: var(--surface-color);
    padding: 1.5rem;
    border-radius: 1rem;
    width: 90%;
    max-width: 500px;
    box-shadow: var(--shadow-lg);
    color: var(--text-primary-color);
}

.emoji-input-wrapper {
    position: relative;
    display: inline-block;
    width: 100%;
}

.emoji-picker-input {
    cursor: pointer;
}

.emoji-picker-dropdown {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    z-index: 10000;
}

/* Overall Emoji Picker */
::v-deep(.v3-emoji-picker) {
    background-color: var(--background-color);
    box-shadow: var(--shadow-md);
}
/* Emoji Picker Text*/
::v-deep(.v3-text) {
    color: var(--text-primary-color);
}
/* Emoji Picker Group Icons */
::v-deep(.v3-groups .v3-icon) {
    filter: invert(var(--icon-invert-color));
}
/* Emoji Picker Search Bar */
::v-deep(.v3-search input) {
    background-color: var(--input-color);
    border-color: var(--border-color);
    color: var(--text-primary-color);
}
/* Emoji Picker Headers */
::v-deep(.v3-sticky) {
    background-color: var(--background-color) !important;
    color: var(--text-primary-color);
}

</style>
