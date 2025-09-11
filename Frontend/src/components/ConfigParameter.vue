<template>
<div class="config-section">

    <!-- header: name and tooltip description -->
    <div class="config-section-header">
        <strong>{{ name }}</strong>
        <div v-if="configParam?.description" class="tooltip-container">
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
        <!-- no free input: dropdown menu -->
        <div v-if="!configParam.free_input">
            <select v-model="localValue" class="form-control">
                <option v-for="option in configParam?.enum" :key="option" :value="option">
                    {{ option }}
                </option>
            </select>
        </div>

        <!-- use input with datalist as combo-box -->
        <div v-else>
            <input v-model="localValue" class="form-control" :list="`datalist-${name}`" type="text"/>
            <datalist :id="`datalist-${name}`">
                <option v-for="option in configParam?.enum" :key="option" :value="option">
                    {{ option }}
                </option>
            </datalist>
        </div>
    </div>

    <!-- numbers: check min/max range -->
    <div v-else-if="['number', 'integer'].includes(configParam.type)">
        <input v-model="localValue"
               class="form-control"
               type="number"
               :min="configParam.minimum"
               :max="configParam.maximum"
               :step="configParam.step"
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

export default {
    name: "ConfigParameter",
    props: {
        name: String,
        configParam: Object,

        // is set by v-model in parent component
        modelValue: [Boolean, Number, String, Array, Object],
    },
    setup() {
        return { Localizer };
    },
    emits: ["update:modelValue"],
    computed: {
        localValue: {
            get() {
                return this.modelValue;
            },
            set(newValue) {
                this.$emit("update:modelValue", newValue);
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
        }
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

.nested-config {
  margin-left: 1.5em;
  border-left: 2px solid #ddd;
  padding-left: 1em;
}

.input-with-minus {
    display: flex;
    align-items: center;
    gap: 8px;
}

.add-button {
    margin-top: 0.75rem;
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