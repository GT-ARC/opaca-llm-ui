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
            />

            <ConfigParameter
                v-else-if="localValue[name] !== undefined"
                :name="name"
                :config-param="schema"
                v-model="localValue[name]"
            />

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
            showTooltip: false,
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
        toggleTooltip() {
            this.showTooltip = !this.showTooltip;
        },
    }
}
</script>