<template>
<div class="config-section">

    <!-- header: name and tooltip description -->
    <div class="config-section-header">
        <strong>{{ configParam?.name ?? name }}</strong>

        <!-- param description -->
        <div v-if="configParam?.description && !this.isMobile" class="tooltip-container">
            <button
                class="question-mark"
                @mouseover="toggleTooltip"
                @mouseleave="toggleTooltip">
                ?
            </button>
            <div v-if="showTooltip" class="tooltip-bubble">
                {{ configParam.description }}
            </div>
        </div>

        <!-- if param is a slider, display the slider value here -->
        <output v-if="['number', 'integer'].includes(configParam.type)"
                :id="`slider-value-${this.name}`"
                class="small text-secondary w-auto ms-auto">
            {{ localValue }}
        </output>
    </div>

    <!-- boolean type: checkbox -->
    <div v-if="configParam.type === 'boolean'">
        <input v-model="localValue"
               class="form-check-input"
               type="checkbox"
        />
    </div>

    <!-- enums -->
    <div v-else-if="Array.isArray(configParam?.enum)">
        <ComboBox
            v-model="localValue"
            :items="configParam?.enum"
            :default-disabled="!configParam?.free_input"
        />
    </div>

    <!-- numbers: check min/max range -->
    <div v-else-if="['number', 'integer'].includes(configParam.type)">
        <input v-model="localValue"
               class="slider"
               type="range"
               :min="configParam.minimum"
               :max="configParam.maximum"
               :step="configParam.step"
               :aria-describedby="`slider-value-${this.name}`"
        />
    </div>

    <!-- other elements: plain text input -->
    <div v-else>
        <input v-model="localValue"
               class="form-control"
               type="text"
        />
    </div>

</div>
</template>


<script>
import Localizer from "../Localizer.js";
import ComboBox from "./ComboBox.vue";
import {useDevice} from "../useIsMobile.js";

export default {
    name: "ConfigParameter",
    components: {ComboBox},
    props: {
        name: String,
        configParam: Object,

        // is set by v-model in parent component
        modelValue: Object, // <- "Any" type
    },
    setup() {
        const {isMobile} = useDevice();
        return { Localizer, isMobile };
    },
    emits: ["update:modelValue"],
    computed: {
        localValue: {
            get() {
                return this.modelValue;
            },
            set(newValue) {
                const value = this.parseValue(newValue, this.configParam?.type);
                this.$emit("update:modelValue", value);
            },
        },
    },
    data() {
        return {
            showTooltip: false,
        }
    },
    methods: {
        toggleTooltip() {
            this.showTooltip = !this.showTooltip;
        },
        parseValue(value, type) {
            switch (type) {
                case 'number':
                case 'integer':
                    return Number(value);
                case 'boolean':
                    return Boolean(value);
                default:
                    return value;
            }
        },
    },
};
</script>

<style scoped>

/* Remove number spinner for Chrome, Safari, Edge, ... */
input[type="number"]::-webkit-inner-spin-button,
input[type="number"]::-webkit-outer-spin-button {
    -webkit-appearance: none;
    margin: 0;
}

/* Remove number spinner for Firefox */
input[type="number"] {
    appearance: textfield;
}

.slider {
    -webkit-appearance: none;
    background-color: var(--input-color);
    padding: 0;
    border-radius: 50px;
    width: 100%;
}

.slider::-webkit-slider-thumb,
.slider::-moz-range-thumb {
    -webkit-appearance: none;
    appearance: none;
    background: var(--primary-color);
    border: none;
    border-radius: 50rem;
    width: 25px;
    height: 25px;
    cursor: pointer;
}

.config-section {
    margin-bottom: 1.5rem;
}

.config-section-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
}

.config-section-header i {
    color: var(--primary-color);
    font-size: 1.125rem;
}

.config-section-header strong {
    color: var(--text-primary-color);
}

.tooltip-container {
    position: relative;
    margin-left: 8px;
}

.question-mark {
    background: none;
    border: none;
    font-size: 12px;
    color: #007bff;
    cursor: pointer;
    padding: 2px 4px;
    border-radius: 50%;
    line-height: 1;
    font-weight: bold;
}

.tooltip-bubble {
    position: absolute;
    display: block;
    width: 200px;
    top: 32px;
    left: -50px;
    background-color: #333;
    color: white;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 12px;
    word-wrap: break-word;
    z-index: 1000;
}

.tooltip-bubble::after {
    content: '';
    position: absolute;
    top: -6px;
    left: 10px;
    border-width: 6px;
    border-style: solid;
    border-color: transparent transparent #333 transparent;
}

</style>