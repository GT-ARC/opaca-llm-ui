<template>
    <div class="config-section">
        <div v-if="isObject">
            <div class="config-section-header"><strong>{{ name }}</strong></div>
            <div v-for="(subValue, subName) in value.default" :key="subName" class="nested-config">
                <config-parameter
                    :key="subName"
                    :name="subName"
                    :value="subValue"
                    v-model="nestedConfig[subName]"/>
            </div>
        </div>
        <!-- Boolean types create a checkbox -->
        <template v-else-if="value.type === 'boolean'">
            <div class="config-section-header"><strong>{{ name }}</strong></div>
            <input v-model="localValue"
                   class="form-check-input"
                   type="checkbox"/>
        </template>

        <!-- Dropdown menu for enums -->
        <template v-else-if="Array.isArray(value?.enum)">
            <div class="config-section-header"><strong>{{ name }}</strong></div>
            <select v-model="localValue" class="form-control">
                <option v-for="option in value?.enum" :key="option" :value="option">
                    {{ option }}
                </option>
            </select>
        </template>

        <!-- Numbers and integers check for minimum and maximum ranges -->
        <template v-else-if="['number', 'integer'].includes(value?.type)">
            <div class="config-section-header"><strong>{{ name }}</strong></div>
            <input v-model="localValue"
                   class="form-control"
                   type="number"
                   :min="value?.minimum"
                   :max="value.maximum"
                   :step="value?.type === 'integer' ? 1 : 0.01"/>
        </template>

        <!-- Other values are just plain text inputs -->
        <template v-else>
            <div class="config-section-header"><strong>{{ name }}</strong></div>
            <input v-model="localValue"
                   class="form-control"
                   type="text" :placeholder="String(value)"/>
        </template>
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
};
</script>

<style scoped>


.config-section {
    margin-bottom: 1.5rem;
}

.config-section-content {
    padding-left: 1.5rem;
    color: var(--text-secondary-light);
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



@media (prefers-color-scheme: dark) {
    .config-section-header strong {
        color: var(--text-primary-dark);
    }

    .config-section-content {
        color: var(--text-secondary-dark);
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