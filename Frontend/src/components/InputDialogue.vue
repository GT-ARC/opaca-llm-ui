<template>
    <div v-if="show" class="auth-overlay">
        <div class="p-4 login-container rounded shadow">
            <form @submit.prevent="submitContainerLogin">
                <h5 class="mb-3">{{ title }}</h5>
                <div class="mb-3">{{ message }}</div>

                <div v-for="(type, label) in schema" :key="label">
                    <input v-if="type == 'text' || type == 'password' || type == 'number'"
                        v-model="values[label]"
                        class="form-control mb-2"
                        :type="type"
                        :placeholder="label"
                    />
                    <div v-else-if="type == 'check'">
                        <input class="form-check-input mb-2" type="checkbox" v-model="values[label]" />
                        <label class="form-check-label mx-2"> {{ label }} </label>
                    </div>
                     <select v-else 
                        v-model="values[label]"
                        class="form-select mb-2">
                        <option v-for="(text, val) in type" :key="val" :value="val">{{ text }}</option>
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

        async showDialogue(title, message, errorMsg, schema, callback) {
            this.title = title;
            this.message = message;
            this.errorMsg = errorMsg;
            this.schema = schema;
            this.callback = callback;
            this.values = Object.fromEntries(
                Object.entries(schema).map(([k, v]) => [k, this.getDefault(v)])
            );
            this.show = true;
            await nextTick();
        },

        getDefault(type) {
            switch (type) {
                case "check": return false;
                // the next are null so that the placeholder text is shown...
                case "text": return null;
                case "password": return null;
                case "number": return null;
                // else: options -> select first
                default: return Object.keys(type)[0];
            }
        },

        isDisabled() {
            return Object.values(this.values).indexOf(null) != -1;
        },

        async handleSubmit(okay) {
            this.callback(okay ? this.values : null);
            this.show = false;
            await nextTick();
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
