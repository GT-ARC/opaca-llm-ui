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

    <div v-if="this.isLoading">
        <i class="fa fa-circle-notch fa-spin me-1" />
        {{ Localizer.get('sidebarConfigLoading', this.backend) }}
    </div>
    <div v-else-if="!this.backendConfig || Object.keys(this.backendConfig).length === 0">
        {{ Localizer.get('sidebarConfigMissing', this.backend) }}
    </div>
    <div v-else class="flex-row text-start">
        <ConfigParameter
            v-for="(value, name) in backendConfigSchema" :key="name"
            :name="name"
            :config-param="value"
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
import backendClient from "../../utils.js";

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
            backendConfig: {},
            backendConfigSchema: null,
            isLoading: false,
        };
    },
    methods: {
        async fetchBackendConfig() {
            const backend = this.backend;
            this.backendConfig = this.backendConfigSchema = null;
            try {
                const res = await backendClient.getConfig(backend);
                this.backendConfig = res.config_values;
                this.backendConfigSchema = res.config_schema;
            } catch (error) {
                console.error('Error fetching backend config:', error);
            }
        },

        async saveBackendConfig() {
            try {
                await backendClient.updateConfig(this.backend, this.backendConfig);
                this.configChangeSuccess = true
                this.configMessage = Localizer.get('configSaveSuccess');
            } catch (error) {
                if (error.response.status === 400) {
                    console.log("Invalid Configuration Values: ", error.response.data.detail)
                    this.configChangeSuccess = false
                    this.configMessage = Localizer.get('configSaveInvalid', error.response.data.detail);
                } else {
                    console.error('Error saving backend config.');
                    this.configChangeSuccess = false
                    this.configMessage = Localizer.get('configSaveError');
                }
            }
            this.startFadeOut()
        },

        async resetBackendConfig() {
            try {
                const res = await backendClient.resetConfig(this.backend);
                console.log('Reset backend config.');
                this.backendConfig = res.config_values;
                this.backendConfigSchema = res.config_schema;
                this.configChangeSuccess = true
                this.configMessage = Localizer.get('configReset')
            } catch (error) {
                console.error('Error resetting backend config.');
                this.backendConfig = null;
                this.backendConfigSchema = null;
                this.configChangeSuccess = false
                this.configMessage = Localizer.get('configSaveError');
            }
            this.startFadeOut()
        },

        startFadeOut() {
            // Clear previous timeout (if the user saves the config again before fade-out could happen)
            if (this.fadeTimeout) {
                clearTimeout(this.fadeTimeout);
            }

            this.shouldFadeOut = false

            this.fadeTimeout = setTimeout(() => {
                this.shouldFadeOut = true;
            }, 3000);
        },

    },
    async mounted() {
        await this.fetchBackendConfig();
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