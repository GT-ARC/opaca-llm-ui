<template>
<div v-if="this.visible" ref="root">

    <div v-for="item in this.items"
         class="item"
         :key="item.id"
         @click="item.callback()" >
        <i class="fa fa-landmark-flag" />
        {{ item.label }}
    </div>

</div>
</template>

<script>
import {nextTick} from "vue";

export default {
    name: "ItemDropdown",
    props: {
        items: Array,
    },
    data() {
        return {
            visible: false,
        }
    },
    methods: {
        async toggle(value = null) {
            this.visible = value === null
                ? !this.visible
                : value;
        },
    }
}
</script>

<style scoped>
.item {
    cursor: pointer;
    padding: 0.5rem;
    border-radius: 0.25rem;
}

.item:hover {
    color: var(--primary-color);
}
</style>