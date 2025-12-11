<!-- Personal Prompt Editor Component -->
<template>
    <div class="text-submission-overlay">
        <div class="text-submission-card">
            <h5>{{ Localizer.get(locTitle) }}</h5>

            <textarea v-model="content" class="form-control" rows="4"></textarea>

            <div class="d-flex justify-content-end gap-2 mt-3">
                <button class="btn btn-secondary" @click="$emit('cancel')">{{ Localizer.get('cancel') }}</button>
                <button class="btn btn-primary" @click="submit">{{ Localizer.get('submit') }}</button>
            </div>
        </div>
    </div>
</template>

<script>
import Localizer from "../Localizer.js"

export default {
    name: "TextSubmissionOverlay",
    setup() {
        return { Localizer }
    },
    props: {
        locTitle: { type: String, default: "addPersonalQuestion" },
    },
    data() {
        return {
            content: "",
        };
    },

    methods: {
        submit() {
            if (!this.content.trim()) return;
            this.$emit("submit", this.content);
        },
    },
};
</script>

<style scoped>
.text-submission-overlay {
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
.text-submission-card {
    background: var(--surface-color);
    padding: 1.5rem;
    border-radius: 1rem;
    width: 90%;
    max-width: 500px;
    box-shadow: var(--shadow-lg);
    color: var(--text-primary-color);
}

</style>
