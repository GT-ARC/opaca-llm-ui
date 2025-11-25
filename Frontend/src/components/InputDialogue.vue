<template>
    <div v-if="show" class="auth-overlay">
        <div class="p-4 login-container rounded shadow">
            <form @submit.prevent="submitContainerLogin">
                <h5 class="mb-3">{{ title }}</h5>
                <div class="mb-3">{{ message }}</div>

                <div v-for="(label, type) in schema">
                    <input v-if="type == 'text' || type == 'password'"
                        v-model="values[label]"
                        class="form-control mb-2"
                        :type="type"
                        :placeholder="label"
                    />
                    <!-- TODO boolean, integer, ...-->
                     <select v-else 
                        v-model="values[label]"
                        class="form-select mb-2">
                        <option v-for="(val, text) in type" :value="val">{{ text }}</option>
                    </select>
                </div>

                <div v-if="errorMsg != null" class="text-danger bg-light border border-danger rounded p-2 mb-3">
                    {{ errorMsg }}
                </div>

                <button type="submit" class="btn btn-primary w-100" @click="handleSubmit(true)" :disabled="isDisabled()">
                    <span>{{ Localizer.get('submit') }}</span>
                </button>
                <button type="button" class="btn btn-link mt-2 text-muted d-block mx-auto" @click="handleSubmit(false)">
                    {{ Localizer.get('cancel') }}
                </button>
            </form>
        </div>
    </div>
</template>

<script>
import {nextTick} from "vue";
import conf from '../../config.js';
import {useDevice} from "../useIsMobile.js";
import Localizer from "../Localizer.js"

export default {
    name: 'InputDialogue',
    components: {},
    props: {

    },
    setup() {
        const { isMobile, screenWidth } = useDevice();
        return { conf, Localizer, isMobile, screenWidth };
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

        async showDialogue(title, message, errorMsg, schema, callback) {
            this.title = title;
            this.message = message;
            this.errorMsg = errorMsg;
            this.schema = schema;
            this.callback = callback;

            this.values = Object.fromEntries(
                Object.entries(schema).map(([k, v]) => [k, null]) // TODO derive default?
            );
            console.log("IN SHOW DIALOGUE");
            console.log("VALUES " + JSON.stringify(this.values));
            this.show = true;
            await nextTick();
        },

        isDisabled() {
            return false; // TODO all values set, or all "required" set?
        },

        async handleSubmit(okay) {
            console.log(`IN SUBMIT ${okay} ${JSON.stringify(this.values)}`)
            if (okay) {
                this.callback(true, this.values);
            } else {
                this.callback(false, null);
            }
            this.show = false;
            await nextTick();
        },

    },

    async mounted() {
    }
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

.is-invalid {
    border-color: #dc3545;
    background-color: #f8d7da;
    color: #842029;
}

.is-invalid::placeholder {
    color: #842029
}
</style>
