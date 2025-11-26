<template>
    <div v-if="show" class="auth-overlay">
        <div class="p-4 login-container rounded shadow">
            <form @submit.prevent="handleSubmit">
                <h5 class="mb-3">{{ title }}</h5>
                <div class="mb-3">{{ message }}</div>

                <div v-for="(val, key) in schema" :key="key">
                    <input v-if="val.type == 'text' || val.type == 'password' || val.type == 'number'"
                        v-model="values[key]"
                        class="form-control mb-2"
                        :type="val.type"
                        :placeholder="val.label ?? key"
                    />
                    <textarea v-if="val.type == 'textarea'"
                        v-model="values[key]"
                        class="form-control"
                        rows="4" 
                        :placeholder="val.label ?? key"
                    />
                    <div v-if="val.type == 'checkbox'">
                        <input class="form-check-input mb-2" type="checkbox" v-model="values[key]" />
                        <label class="form-check-label mx-2"> {{ val.label ?? key }} </label>
                    </div>
                     <select v-if="val.type == 'select'"
                        v-model="values[key]"
                        class="form-select mb-2">
                        <option v-for="(v, k) in val.values" :key="k" :value="k">{{ v }}</option>
                    </select>
                </div>

                <div v-if="errorMsg != null" class="text-danger bg-light border border-danger rounded p-2 mb-3">
                    {{ errorMsg }}
                </div>

                <div v-if="callback != null">
                    <button type="submit" class="btn btn-primary w-100" @click="handleSubmit(true)" :disabled="isDisabled()">
                        <span>{{ Localizer.get('submit') }}</span>
                    </button>
                    <button type="button" class="btn btn-link mt-2 text-muted d-block mx-auto" @click="handleSubmit(false)">
                        {{ Localizer.get('cancel') }}
                    </button>
                </div>
                <button v-else type="button" class="btn btn-primary w-100" @click="show = false">
                    Okay
                </button>
            </form>
        </div>
    </div>
</template>

<script>
import {nextTick} from "vue";
import {useDevice} from "../useIsMobile.js";
import Localizer from "../Localizer.js"

export default {
    name: 'InputDialogue',
    setup() {
        const { isMobile, screenWidth } = useDevice();
        return { Localizer, isMobile, screenWidth };
    },
    data() {
        return {
            show: false,
            title: null,
            message: null,
            errorMsg: null,
            schema: null,
            values: null,
            callback: null,
        }
    },
    methods: {

        /**
         * Show input dialogue for asking various values according to given schema. Results are handed to
         * callback function as dictionary mapping schema-keys to values, or null if "cancel" was pressed
         * 
         * THe format for "schema" is as follows
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
         * @param message message below the title, optional
         * @param errorMsg error message (e.g. if previous attempt failed), optional
         * @param schema defines the different values that should be entered in the dialogue (see above)
         * @param callback callback function, should accept dict of values or null
         */
        async showDialogue(title, message, errorMsg, schema, callback) {
            this.title = title;
            this.message = message;
            this.errorMsg = errorMsg;
            this.schema = schema;
            this.callback = callback;
            this.values = Object.fromEntries(
                Object.entries(schema).map(([k, v]) => [k, v.default])
            );
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

        isDisabled() {
            return Object.values(this.values).indexOf(null) != -1;
        },

        async handleSubmit(okay) {
            this.show = false;
            await nextTick();
            // callback is called last, so that it can show another dialogue
            this.callback(okay ? this.values : null);
        },

    },
}
</script>

<style scoped>

/* login stuff */
.login-container {
    max-width: 400px;
    width: 100%;
    margin: auto;
    background-color: var(--surface-color);
    color: var(--text-primary-color)
}

.auth-overlay {
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
