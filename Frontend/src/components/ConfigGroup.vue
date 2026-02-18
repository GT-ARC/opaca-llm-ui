<template>
<div class="config-group">

    <h5 v-if="showTitle" class="mt-3>"><strong>{{ name }}</strong></h5>

    <div class="nested-group">
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
            />

            <div v-if="showTitle && schema.type !== 'object'" class="group-header mt-3>">
                <div class="header-right" @click="toggleCollapse">
                    <strong>Settings</strong>
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

.group-header {
    user-select: none;
    display: flex;
    align-items: center;
}

.header-right {
    cursor: pointer;
    display: flex;
    margin-left: auto;
    gap: 0.5rem;
}

.header-right:hover {
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