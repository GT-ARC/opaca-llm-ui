<template>
<div class="position-relative" ref="root">
    <div class="input-group combo-box">
        <input
            ref="input"
            type="text"
            class="form-control"
            :placeholder="placeholder"
            v-model="localValue"
            @input="onInput"
            @keydown.down.prevent="moveSelection(1)"
            @keydown.up.prevent="moveSelection(-1)"
            @keydown.enter.prevent="commitHighlighted"
            @keydown.esc.prevent="toggleDropdown(false)"
            role="combobox"
            :aria-expanded="open ? 'true' : 'false'"
            aria-autocomplete="list"
            autocomplete="off"
            :disabled="disabled"
        />
        <button
            class="btn btn-outline-secondary"
            type="button"
            @click="toggleDropdown"
            aria-label="Toggle options">
            <i v-if="open" class="fa fa-caret-up" />
            <i v-else class="fa fa-caret-down" />
        </button>
    </div>

    <ul
        v-if="open"
        class="list-group position-absolute start-0 end-0 mt-1"
        style="z-index: 1050; max-height: 240px; overflow: auto;"
        role="listbox">
        <li
            v-for="(item, idx) in items"
            :key="item + '_' + idx"
            class="list-group-item list-group-item-action"
            :class="{ active: idx === highlighted }"
            role="option"
            :aria-selected="idx === highlighted ? 'true' : 'false'"
            @mouseup.prevent="select(item)"
            @mousemove="highlighted = idx">
            {{ item }}
        </li>
    </ul>
</div>
</template>

<script>
export default {
    name: "ComboBox",
    props: {
        modelValue: { type: String, default: "" },
        items: { type: Array, default: () => [] },
        placeholder: { type: String, default: "" },
        defaultDisabled: { type: Boolean, default: false },
    },
    emits: ["update:modelValue"],
    data() {
        return {
            open: false,
            highlighted: -1,
            localValue: this.modelValue,
            disabled: this.defaultDisabled,
        };
    },
    watch: {
        modelValue(newValue) {
            if (newValue !== this.localValue) this.localValue = newValue ?? "";
        }
    },
    methods: {
        onInput() {
            this.$emit("update:modelValue", this.localValue);
        },
        toggleDropdown(value = null) {
            this.open = (value === null)
                ? !this.open
                : value;
            if (this.open) this.highlighted = -1;
        },
        select(item) {
            this.localValue = item;
            this.$emit("update:modelValue", item);
            this.toggleDropdown(false);
        },
        moveSelection(offset) {
            if (!this.open) this.open = true;
            const numItems = this.items.length;
            if (numItems === 0) return;
            this.highlighted = (this.highlighted + offset + numItems) % numItems;
        },
        commitHighlighted() {
            if (this.open && this.highlighted >= 0) {
                this.select(this.items[this.highlighted]);
            } else {
                this.toggleDropdown(false);
            }
        },
        toggleDisabled(value = null) {
            this.disabled = (value === null) ? !this.disabled : value;
        },
        onDocClick(e) {
            const root = this.$refs.root;
            if (!root) return;
            if (!root.contains(e.target)) this.toggleDropdown(false);
        }
    },
    mounted() {
        // close when clicking anywhere else
        document.addEventListener("mousedown", this.onDocClick);
    },
    beforeUnmount() {
        document.removeEventListener("mousedown", this.onDocClick);
    },
};
</script>

<style scoped>
.combo-box {
    width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
}

.list-group {
    border: 1px solid var(--border-color)
}

.list-group-item {
    background-color: var(--input-color);
    cursor: pointer;
}

.list-group-item.active {
    background-color: var(--primary-color);
    color: var(--button-primary-color);
}
</style>
