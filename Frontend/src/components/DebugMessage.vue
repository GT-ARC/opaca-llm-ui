<!-- Debug Message Component -->
<template>
    <div class="debug-text" :style="this.getDebugColoring(this.type)" :data-type="type" @click.stop="this.toggleCollapsed()" >
        <div class="debug-header">
            <i v-if="canCollapse() && collapsed" class="fa fa-caret-right" />
            <i v-if="canCollapse() && ! collapsed" class="fa fa-caret-down" />
            {{type}}
        </div>
        <!--
        IMPORTRANT: do NOT add space or fancy line breaks in this div,
        as those will show in the output as a single leading space!
        @click="" is intentional, else problems with select-copy-paste -> collapse/expand on header and left margin, not on text
        -->
        <div class="debug-content" @click.stop="">{{getDisplayText()}}</div>
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
    },
    data() {
        return {
            collapsed: true,    // defaults to true, but ignored if irrelevant
            collapseSize: 300,  // min text size when to show collapse toggle
        }
    },

    methods: {
        canCollapse() {
            return this.text.length > this.collapseSize;
        },

        toggleCollapsed() {
            this.collapsed = ! this.collapsed;
        },

        getDisplayText() {
            if (this.canCollapse() && this.collapsed) {
                return this.text.substring(0, this.collapseSize) + '...';
            } else {
                return this.text.trim();
            }
        },

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

</style>
