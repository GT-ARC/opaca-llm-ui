<template>
<div id="config-display"
     class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div v-if="!isMobile" class="sidebar-title">
        {{ Localizer.get('tooltipSidebarConfig') }}
    </div>

    <div class="py-2">
        <p class="fw-bold">Config for
            <i class="fa fa-server ms-1"/>
            {{ Backends[this.backend] }}
        </p>
        <p>{{ BackendDescriptions[this.backend] }}</p>
    </div>

    <div v-if="!this.backendConfig || Object.keys(this.backendConfig).length === 0">
        No config available.
    </div>

    <div v-else class="flex-row text-start">
        <ConfigParameter v-for="(value, name) in backendConfigSchema"
                         :key="name"
                         :name="name"
                         :value="value"
                         v-model="backendConfig[name]"
        />

        <div class="py-2 text-center">
            <button class="btn btn-primary py-2 w-100" type="button" @click="saveBackendConfig">
                <i class="fa fa-save me-2"/>{{ Localizer.get('buttonBackendConfigSave') }}
            </button>
        </div>
        <div class="py-2 text-center">
            <button class="btn btn-danger py-2 w-100" type="button" @click="resetBackendConfig">
                <i class="fa fa-undo me-2"/>{{ Localizer.get('buttonBackendConfigReset') }}
            </button>
        </div>
        <div v-if="!this.shouldFadeOut"
             class="text-center"
             :class="{ 'text-danger': !this.configChangeSuccess,
                       'text-success': this.configChangeSuccess}">
            {{ this.configMessage }}
        </div>
    </div>
</div>
</template>

<script>
import conf, {Backends, BackendDescriptions} from "../../../config.js";
import Localizer from "../../Localizer.js";
import {useDevice} from "../../useIsMobile.js";
import ConfigParameter from "../ConfigParameter.vue";
import {sendRequest} from "../../utils.js";

export default {
    name: 'SidebarConfig',
    components: {ConfigParameter},
    props: {
        backend: String,
    },
    setup() {
        const {isMobile} = useDevice();
        return {conf, Localizer, Backends, BackendDescriptions, isMobile};
    },
    data() {
        return {
            shouldFadeOut: false,
            configChangeSuccess: false,
            configMessage: '',
            backendConfig: null,
            backendConfigSchema: null,
        };
    },
    methods: {
        async saveBackendConfig() {
            try {
                const url = `${conf.BackendAddress}/${backend}/config`;
                const response = await sendRequest('PUT', url, this.backendConfig);
                if (response.status === 200) {
                    console.log('Saved backend config.');
                    this.configChangeSuccess = true;
                    this.configMessage = "Configuration Changed";
                    this.startFadeOut();
                } else {
                    console.error('Error saving backend config.');
                    this.configChangeSuccess = false;
                    this.configMessage = "Unexpected Error";
                    this.startFadeOut();
                }
            } catch (error) {
                if (error.response.status === 400) {
                    console.log("Invalid Configuration Values: ", error.response.data.detail);
                    this.configChangeSuccess = false;
                    this.configMessage = "Invalid Configuration Values: " + error.response.data.detail;
                    this.startFadeOut();
                }
            }
        },

        async resetBackendConfig() {
            const url = `${conf.BackendAddress}/${this.backend}/config/reset`;
            const response = await sendRequest('POST', url);
            if (response.status === 200) {
                this.backendConfig = response.data.value;
                this.backendConfigSchema = response.data.config_schema;
                this.configChangeSuccess = true
                this.configMessage = "Reset Configuration to default values"
                this.startFadeOut()
                console.log('Reset backend config.');
            } else {
                this.backendConfig = this.backendConfigSchema = null;
                this.configChangeSuccess = false
                this.configMessage = "Unexpected error occurred during configuration reset"
                this.startFadeOut()
                console.error('Error resetting backend config.');
            }
        },

        startFadeOut() {
            // Clear previous timeout (if the user saves the config again before fade-out could happen)
            if (this.fadeTimeout) {
                clearTimeout(this.fadeTimeout);
            }

            this.shouldFadeOut = false

            this.fadeTimeout = setTimeout(() => {
                this.shouldFadeOut = true;
            }, 3000)
        },

        async fetchBackendConfig() {
            this.backendConfig = null;
            this.backendConfigSchema = null;
            try {
                const url = `${conf.BackendAddress}/${this.backend}/config`;
                const response = await sendRequest('GET', url);
                if (response.status === 200) {
                    this.backendConfig = response.data.value;
                    this.backendConfigSchema = response.data.config_schema;
                } else {
                    console.error(`Failed to fetch backend config for backend ${this.getBackend()}`);
                }
            } catch (error) {
                console.error('Error fetching backend config:', error);
            }
        },

    },
    mounted() {
        this.fetchBackendConfig();
    },
    watch: {
        backend() {
            this.fetchBackendConfig();
        },
    }
};
</script>

<style scoped>

</style>