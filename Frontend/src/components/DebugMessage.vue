<!-- Debug Message Component -->
<template>
    <div class="debug-text" :style="this.getDebugColoring(this.type)" :data-type="type">
        <div class="debug-header">{{ type }}</div>
        <div class="debug-content">{{ text }}</div>
        <div v-if="executionTime" class="debug-execution-time">
            Execution time: {{ executionTime.toFixed(2) }}s
        </div>
        <div v-if="responseMetadata && responseMetadata.total_tokens > 0" class="debug-execution-time">
            Tokens (Prompt, Complete): {{responseMetadata.total_tokens}} ({{responseMetadata.prompt_tokens}}, {{responseMetadata.completion_tokens}})
        </div>
    </div>
</template>

<script>
import {getDebugColor} from "../config/debug-colors.js";
import {isDarkTheme} from "../ColorThemes.js";

export default {
    name: 'DebugMessage',
    props: {
        text: {
            type: String,
            required: true
        },
        type: {
            type: String,
            required: true
        },
        executionTime: {
            type: Number,
            default: null
        },
        responseMetadata: {
            type: Object,
            default: null
        },
    },

    methods: {
        getDebugColoring (agentName) {
            const isDarkScheme = isDarkTheme();
            const color = getDebugColor(agentName, isDarkScheme);
            return {color: color ?? null};
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

.debug-header {
    font-weight: bold;
    margin-bottom: 0.25rem;
}

.debug-content {
    margin-left: 1rem;
}

.debug-execution-time {
    font-size: 0.75rem;
    margin-top: 0.25rem;
    opacity: 0.8;
}
</style> 