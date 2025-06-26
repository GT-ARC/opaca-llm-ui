<template>
<div class="accordion-item m-0" style="max-width: 300px">

    <!-- Header -->
    <div class="accordion-header options-header">
        <div class="accordion-button collapsed d-flex p-2"
             data-bs-toggle="collapse"
             :data-bs-target="`#selector-${this.name}`">
            <div class="d-flex me-3 p-1" style="height: 100%;">
                <i class="fa fs-2" :class="[this.icon]" />
            </div>
            <div class="d-flex flex-column">
                <div class="fs-5">
                    {{ this.getSelectedItem() }}
                </div>
                <div class="text-muted">
                    {{ this.name }}
                </div>
            </div>
        </div>
    </div>

    <!-- Body -->
    <div :id="`selector-${this.name}`"
         class="accordion-collapse collapse"
         :data-bs-parent="`#${this.parent}`">
        <div class="accordion-body">
            <div v-for="(item, itemId) in this.data"
                 :key="itemId"
                 class="options-item"
                 @click="this.select(item, itemId)">
                {{ item }}
                <i class="fa fa-check-circle ms-1" v-if="itemId === this.itemId" />
            </div>
        </div>
    </div>

</div>
</template>

<script>
export default {
    name: "OptionsSelectItem",
    props: {
        parent: String,
        name: String,
        icon: String,
        data: Array | Object,
        initialSelect: Number | String,
    },
    data() {
        return {
            itemId: this.initialSelect,
        }
    },
    emits: [
        'select'
    ],
    methods: {
        getSelectedItem() {
            const item = this.data[this.itemId];
            if (item) return item;
            return null;
        },
        select(item, itemId) {
            this.itemId = itemId;
            this.$emit('select', item, itemId);
        }
    }
}
</script>

<style scoped>
.options-header {
    margin: 0;
    border-radius: 0 !important;
    cursor: pointer;
}

.options-item {
    color: var(--text-primary-color);
    cursor: pointer;
    padding: 0.5rem;
}

.options-item:hover {
    color: var(--primary-color);
    transform: translateY(-1px);
}
</style>