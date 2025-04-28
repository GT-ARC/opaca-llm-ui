<template>
    <div class="config-section">
        <div v-if="isObject">
            <div class="config-section-header">
                <strong>{{ name }}</strong>
                <div v-if="value.description" class="tooltip-container">
                    <button
                        class="question-mark"
                        @mouseover="toggleTooltip"
                        @mouseleave="toggleTooltip">
                        ?
                    </button>
                    <div v-if="showTooltip" class="tooltip-bubble">
                        {{ value.description }}
                    </div>
                </div>
            </div>
            <div v-for="(subValue, subName) in value.default" :key="subName" class="nested-config">
                <config-parameter
                    :key="subName"
                    :name="subName"
                    :value="subValue"
                    v-model="nestedConfig[subName]"/>
            </div>
        </div>

        <div v-else>
            <!-- header: name and tooltip description -->
            <div class="config-section-header">
                <strong>{{ name }}</strong>
                <div v-if="value.description" class="tooltip-container">
                    <button
                        class="question-mark"
                        @mouseover="toggleTooltip"
                        @mouseleave="toggleTooltip">
                        ?
                    </button>
                    <div v-if="showTooltip" class="tooltip-bubble">
                        {{ value.description }}
                    </div>
                </div>
            </div>

            <!-- boolean type: checkbox -->
            <div v-if="value.type === 'boolean'">
                <input v-model="localValue"
                       class="form-check-input"
                       type="checkbox"/>
            </div>

            <!-- enums: dropdown menu -->
            <div v-else-if="Array.isArray(value?.enum)">
                <select v-model="localValue" class="form-control">
                    <option v-for="option in value?.enum" :key="option" :value="option">
                        {{ option }}
                    </option>
                </select>
            </div>

            <!-- numbers: check min/max range -->
            <div v-else-if="['number', 'integer'].includes(value.type)">
                <input v-model="localValue"
                       class="form-control"
                       type="number"
                       :min="value?.minimum"
                       :max="value.maximum"
                       :step="value.type === 'integer' ? 1 : 0.01"/>
            </div>

            <!-- array type: dynamic list (is this used?) -->
            <div v-else-if="value.type === 'array'">
                <div v-for="(item, index) in localValue" :key="index" class="array-item">
                    <div class="input-with-minus">
                        <input v-model="localValue[index]" class="form-control" :type="['number', 'integer'].includes(value.array_items.type) ? 'number' : 'text'"/>
                        <button type="button" class="btn btn-outline-danger btn-sm remove-button" @click="removeItem(index)">
                            &minus;
                        </button>
                    </div>
                </div>
                <button class="btn btn-primary btn-sm add-button" @click="addItem">Add Item</button>
            </div>

            <!-- other elements: plain text input -->
            <div v-else>
                <input v-model="localValue"
                       class="form-control"
                       type="text"/>
            </div>

        </div>

    </div>
</template>


<script>
export default {
    name: "ConfigParameter",
    props: {
        name: {
            type: String,
            required: true,
        },
        value: {
            type: Object,
            required: true,
        },
        modelValue: {
            type: [Boolean, Number, String, Array, Object],
            required: true,
        },
    },
    emits: ["update:modelValue"],
    computed: {
        isObject() {
            return this.value.type === "object";
        },
        localValue: {
            get() {
                return this.modelValue;
            },
            set(newValue) {
                this.$emit("update:modelValue", newValue)
            },
        },
        nestedConfig: {
            get() {
                return this.modelValue || {};
            },
            set(newConfig) {
                this.$emit("update:modelValue", newConfig);
            },
        },
    },
    data() {
        return {
            showTooltip: false
        }
    },
    methods: {
        addItem() {
            if (Array.isArray(this.localValue)) {
                const itemType = this.value.array_items.type;
                let newItem;

                switch (itemType) {
                    case "boolean":
                        newItem = false;
                        break;
                    case "number":
                    case "integer":
                        newItem = 0;
                        break;
                    default:
                        newItem = "";
                }
                this.localValue.push(newItem);
            } else {
                console.warn("Called the method 'addItem' for a non-array type!")
            }
        },

        removeItem(index) {
            if (Array.isArray(this.localValue)) {
                this.localValue.splice(index, 1);
            } else {
                console.warn("Called the method 'removeItem' for a non-array type!")
            }
        },

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
    color: var(--primary-light);
    font-size: 1.125rem;
}

.config-section-header strong {
    color: var(--text-primary-light);
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

@media (prefers-color-scheme: dark) {
    .config-section-header strong {
        color: var(--text-primary-dark);
    }

    .config-section-header i {
        color: var(--primary-dark);
    }

    .form-control {
        background-color: var(--input-dark);
        border-color: var(--border-dark);
        color: var(--text-primary-dark);
    }

    .form-control::placeholder {
        color: var(--text-secondary-dark);
    }

    .form-control:focus {
        background-color: var(--input-dark);
        border-color: var(--primary-dark);
    }
}
</style>