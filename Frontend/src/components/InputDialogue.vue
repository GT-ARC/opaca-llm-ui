<template>
    <div v-if="show" class="input-dialog">
        <div class="p-4 input-container rounded shadow">
            <form @submit.prevent="handleSubmit">
                <h5 class="mb-3">{{ title }}</h5>
                <div class="scroll-container">
                    <div class="mb-3" v-html="message" />

                    <div v-for="(val, key, idx) in schema" :key="key">
                        <input v-if="val.type === 'text' || val.type === 'password' || val.type === 'number'"
                            v-model="values[key]"
                            class="form-control mb-2"
                            :type="val.type"
                            :placeholder="val.label ?? key"
                            v-bind:autofocus="idx === 0"
                        />
                        <textarea v-if="val.type === 'textarea'"
                            v-model="values[key]"
                            class="form-control mb-2"
                            rows="4" 
                            :placeholder="val.label ?? key"
                            v-bind:autofocus="idx === 0"
                        />
                        <div v-if="val.type === 'checkbox'">
                            <input id="cb" class="form-check-input mb-2" type="checkbox" v-model="values[key]" v-bind:autofocus="idx === 0"/>
                            <label for="cb" class="form-check-label mx-2"> {{ val.label ?? key }} </label>
                        </div>
                        <select v-if="val.type === 'select'"
                            v-model="values[key]"
                            v-bind:autofocus="idx === 0"
                            class="form-select mb-2">
                            <option v-for="(v, k) in val.values" :key="k" :value="k">{{ v }}</option>
                        </select>
                    </div>

                    <div v-if="errorMsg !== null" class="text-danger border border-danger rounded p-2 mb-3">
                        {{ errorMsg }}
                    </div>
                </div>

                <div v-if="onOkay !== null" class="d-flex justify-content-end gap-2 mt-2">
                    <button type="button" class="btn btn-secondary w-25" @click="handleSubmit(false)" v-if="!loading">
                        {{ Localizer.get('general_cancel') }}
                    </button>
                    <button type="submit" class="btn btn-primary w-50" @click="handleSubmit(true)" :disabled="!canSubmit()">
                        <span v-if="loading"><i class="fa fa-spin fa-spinner" /></span>
                        <span v-else>{{ Localizer.get('general_okay') }}</span>
                    </button>
                    
                </div>
                <button v-else type="button" class="btn btn-primary w-100 mt-2" @click="show = false">
                    {{ Localizer.get('general_okay') }}
                </button>
            </form>
        </div>
    </div>
</template>

<script>
import {nextTick} from "vue";
import {useDevice} from "../useIsMobile.js";
import Localizer from "../Localizer.js"
import {marked} from "marked";

export default {
    name: 'InputDialogue',
    setup() {
        const { isMobile, screenWidth } = useDevice();
        return { Localizer, isMobile, screenWidth };
    },
    data() {
        return {
            queue: [],
            show: false,
            title: null,
            message: null,
            errorMsg: null,
            schema: null,
            values: null,
            onOkay: null,
            onCancel: null,
            loading: false,
        }
    },
    methods: {

        /**
         * Show input dialogue for asking various values according to given schema. Results are handed to
         * callback functions as dictionary mapping schema-keys to values on "okay", or nothing if "cancel" was pressed
         * 
         * The format for "schema" is as follows
         * 
         * {
         *      key1: {type: str, label: str, default: any, values: dict?},
         *      ...
         * }
         * 
         * Where
         * - key: the internal name of the property, reused in the dict of results
         * - type: one of "text", "textarea", "password", "checkbox", "number", or "select"
         * - label: display label/placeholder, optional (if not present, key is used)
         * - default: default value, optional (default-default is just null)
         * - values: dict (value -> label) for options, only for type 'select'
         * 
         * @param title the title (bold)
         * @param message message below the title, optional; can contain Markdown
         * @param errorMsg error message (e.g. if previous attempt failed), optional)
         * @param schema defines the different values that should be entered in the dialogue (see above)
         * @param onOkay async callback function, should accept dict of values; can raise error
         * @param onCancel async callback function, should accept no parameters (optional); can raise error
         */
        async showDialogue(title, message, errorMsg, schema, onOkay, onCancel=null) {
            this.queue.push({
                title: title,
                message: marked.parse(message ?? ""),
                errorMsg: errorMsg,
                schema: schema,
                onOkay: onOkay,
                onCancel: onCancel ?? (async () => {}),
                values: Object.fromEntries(
                    Object.entries(schema).map(([k, v]) => [k, v.default ?? null]) // yes, '?? null' makes a difference...
                ),
            });
            await this.updateDialogue();
        },

        /**
         * Update dialogue from Queue. This is to ensure that a follow-up dialogue can be shown in the onOkay callback of
         * another dialogue. The problem here is that all those are actually the SAME dialogue and only the content is updated.
         * 
         * - If the last dialogue is still showing (executing its callback), this does nothing.
         * - If the queue is empty, it hides itself.
         * - Otherwise, it updates the content from the queue and sets itself to being visible again.
         *
         * Without the queue, the first dialogue could set itself to hidden and then update the content in the callback, but that
         * would result in a short time of no dialogue being shown. If it sets itself to hidden after the callback is finished, it
         * would update the content and then immediately hide itself. With this queue, the process is: exec callback, queue new
         * content, set self to hidden, update content from queue and set to visible again.
         */
        async updateDialogue() {
            if (this.loading) return;
            if (this.show) return;
            if (this.queue.length === 0) {
                this.show = false;
                return;
            }
            const {title, message, errorMsg, schema, onOkay, onCancel, values} = this.queue.shift();
            this.title = title;
            this.message = message;
            this.errorMsg = errorMsg;
            this.schema = schema;
            this.onOkay = onOkay;
            this.onCancel = onCancel;
            this.values = values;
            this.show = true;
            await nextTick();
        },

        /**
         * Show simplified dialogue, no input values, just one "okay" button
         * 
         * @param title the title (bold)
         * @param message message below the title (optional)
         */
        async showInfo(title, message) {
            await this.showDialogue(title, message, null, {}, null);
        },

        canSubmit() {
            if (this.loading) return false;
            return Object.values(this.values).indexOf(null) === -1;
        },

        async handleSubmit(okay) {
            await nextTick();
            this.loading = true;
            try {
                const callback = okay ? this.onOkay : this.onCancel;
                await callback(this.values);
                this.show = false;
            } catch (error) {
                console.warn(error);
                this.errorMsg = error.message;
                this.show = true;
            } finally {
                this.loading = false;
                await this.updateDialogue();
            }
        },

    },
    mounted() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.show) {
                this.handleSubmit(false);
            }
            if (e.key === 'Enter' && e.ctrlKey && this.show) {
                this.handleSubmit(true);
            }
        });
    },
}
</script>

<style scoped>

.input-container {
    max-width: 400px;
    width: 100%;
    margin: auto;
    background-color: var(--surface-color);
    color: var(--text-primary-color);
}

.scroll-container {
    max-height: 500px;
    overflow-y: auto;
    overflow-x: auto;
}

.input-dialog {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background-color: rgba(0, 0, 0, 0.5); /* Transparent overlay */
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999; /* Should appear above all other items */
}

</style>
