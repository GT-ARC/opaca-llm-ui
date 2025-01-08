<!-- Debug Message Component -->
<template>
    <div class="debug-text" :style="{ color: color }">
        {{ text }}
    </div>
</template>

<script>
export default {
    name: 'DebugMessage',
    props: {
        text: {
            type: String,
            required: true
        },
        color: {
            type: String,
            required: true
        }
    }
}
</script>

<style scoped>
.debug-text {
    display: block;
    text-align: left;
    margin-left: 0.5rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 0.875rem;
    padding: 0.25rem 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-wrap: break-word;
}
</style> 