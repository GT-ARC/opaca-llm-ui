<template>
<div class="config-group">

    <h5 v-if="showTitle" class="mt-3>"><strong>{{ name }}</strong></h5>

    <div class="nested-group" :class="{ 'no-header': !showTitle }">
        <template v-for="(schema, name) in schema.properties" :key="schema">

            <ConfigGroup
                v-if="schema.type === 'object'"
                :name="name"
                :schema="schema"
                v-model="localValue[name]"
                v-show="!collapsed"
            />

            <ConfigParameter
                v-else-if="localValue[name] !== undefined"
                :name="name"
                :config-param="schema"
                v-model="localValue[name]"
                @update:modelValue="schema?.title === 'model' ? $emit('update:modelValue', localValue) : null"
            />

            <div v-if="showTitle && schema.type !== 'object'" class="group-header mt-3>">
                <div class="header" @click="toggleCollapse">
                    <strong>Advanced Settings</strong>
                    <span
                        class="chevron"
                        :class="{ rotated: !collapsed }"
                    >
                        ▶
                    </span>
                </div>
            </div>

        </template>
    </div>
</div>


</template>

<script>
import ConfigParameter from "./ConfigParameter.vue";
import {useDevice} from "../useIsMobile.js";

export default {
    name: "ConfigGroup",
    components: {ConfigParameter},
    props: {
        name: String,
        schema: Object,
        modelValue: [Number, String, Object, Boolean],
        showTitle: false,
    },
    setup() {
        const {isMobile} = useDevice();
        return { isMobile };
    },
    data() {
        return {
            collapsed: true,
        }
    },
    emits: ['update:modelValue'],
    computed: {
        localValue: {
            get() {
                return this.modelValue;
            },
            set(val) {
                this.$emit('update:modelValue', val);
            }
        }
    },
    methods: {
        toggleCollapse() {
            if (this.showTitle) {
                this.collapsed = !this.collapsed;
            }
        }
    }
}
</script>

<style scoped>

.nested-group {
    margin-bottom: 2.0rem;
}

.nested-group.no-header {
    border-color: var(--border-color);
    border-style: solid;
    border-width: 1px;
    padding: 1rem;
    border-radius: var(--bs-border-radius);
}

.group-header {
    user-select: none;
    display: flex;
    align-items: center;
}

.header {
    cursor: pointer;
    display: flex;
    gap: 0.5rem;
}

.header:hover {
    color: var(--primary-color);
}

.chevron {
    display: inline-block;
    transition: transform 0.2s ease;
    font-size: 0.8rem;
    transform: rotate(90deg);
}

.chevron.rotated {
    transform: rotate(-90deg);
}

</style>