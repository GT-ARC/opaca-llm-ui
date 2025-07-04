<template>
<div class="accordion-item m-0">

    <!-- Header -->
    <div class="accordion-header options-header">
        <div class="accordion-button collapsed d-flex p-2 rounded-0"
             data-bs-toggle="collapse"
             :data-bs-target="`#selector-${this.elementId}`">
            <div class="d-flex me-1 p-1 text-start" style="height: 100%">
                <i class="fa fs-4" :class="[this.icon]" style="width: 30px" />
            </div>
            <div class="d-flex flex-column">
                <div>
                    {{ this.getSelectedItem() }}
                </div>
                <div class="text-muted">
                    {{ this.name }}
                </div>
            </div>
        </div>
    </div>

    <!-- Body -->
    <div :id="`selector-${this.elementId}`"
         class="accordion-collapse collapse"
         :data-bs-parent="`#${this.parent}`">
        <div class="accordion-body">
            <div v-for="(item, itemId) in this.data"
                 :key="itemId"
                 class="options-item"
                 @click="this.onItemClick ? this.onItemClick(item, itemId) : this.select(item, itemId)">
                {{ item }}
                <i class="fa fa-check-circle ms-1" v-if="this.showSelected && itemId === this.itemId" />
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
        elementId: String,
        name: String,
        icon: String,
        data: Array | Object,
        initialSelect: Number | String,
        showSelected: { type: Boolean, default: true },
        onItemClick: { type: Function, default: null },
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
    cursor: pointer;
}

.options-item {
    color: var(--text-primary-color);
    cursor: pointer;
    padding: 0.5rem;
}

.options-item:hover {
    color: var(--primary-color) !important;
    transform: translateY(-1px);
}

.accordion-item {
    min-width: min(300px, 100vw - 6rem);
    max-width: calc(100vw - 6rem);
}

.accordion-header,
.accordion-item,
.accordion-button {
    border-radius: 0 !important;
}
</style>