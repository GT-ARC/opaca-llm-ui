<template>
<div id="config-display"
     class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div v-if="!isMobile" class="sidebar-title">
        {{ Localizer.get('tooltipSidebarConfig') }}
    </div>

    <div class="py-2">
        <p class="fw-bold">Config for
            <i class="fa fa-server ms-1"/>
            {{ Methods[this.method] }}
        </p>
        <p>{{ MethodDescriptions[this.method] }}</p>
    </div>

    <div v-if="this.isLoading">
        <i class="fa fa-circle-notch fa-spin me-1" />
        {{ Localizer.get('sidebarConfigLoading', this.method) }}
    </div>
    <div v-else-if="!this.methodConfig || Object.keys(this.methodConfig).length === 0">
        {{ Localizer.get('sidebarConfigMissing', this.method) }}
    </div>
    <div v-else class="flex-row text-start">
        <ConfigParameter
            v-for="(schema, name) in methodConfigSchema" :key="name"
            :name="name"
            :config-param="schema"
            v-model="methodConfig[name]"
        />

        <div class="py-2 text-center">
            <button class="btn btn-primary py-2 w-100" type="button" @click="saveMethodConfig">
                <i class="fa fa-save me-2"/>{{ Localizer.get('buttonConfigSave') }}
            </button>
        </div>
        <div class="py-2 text-center">
            <button class="btn btn-danger py-2 w-100" type="button" @click="resetMethodConfig">
                <i class="fa fa-undo me-2"/>{{ Localizer.get('buttonConfigReset') }}
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
import conf, {Methods, MethodDescriptions} from "../../../config.js";
import Localizer from "../../Localizer.js";
import {useDevice} from "../../useIsMobile.js";
import ConfigParameter from "../ConfigParameter.vue";
import backendClient from "../../utils.js";

export default {
    name: 'SidebarConfig',
    components: {ConfigParameter},
    props: {
        method: String,
    },
    setup() {
        const {isMobile} = useDevice();
        return {conf, Localizer, Methods, MethodDescriptions, isMobile};
    },
    data() {
        return {
            shouldFadeOut: false,
            configChangeSuccess: false,
            configMessage: '',
            methodConfig: {},
            methodConfigSchema: null,
            isLoading: false,
        };
    },
    methods: {
        async fetchMethodConfig() {
            const method = this.method;
            this.methodConfig = this.methodConfigSchema = null;
            try {
                const res = await backendClient.getConfig(method);
                this.methodConfig = res.config_values;
                this.methodConfigSchema = res.config_schema;
            } catch (error) {
                console.error('Error fetching method config:', error);
            }
        },

        async saveMethodConfig() {
            try {
                await backendClient.updateConfig(this.method, this.methodConfig);
                this.configChangeSuccess = true
                this.configMessage = Localizer.get('configSaveSuccess');
                this.startFadeOut()
            } catch (error) {
                if (error.response.status === 422) {
                    console.log("Invalid Configuration Values: ", error.response.data.detail)
                    this.configChangeSuccess = false
                    this.configMessage = Localizer.get('configSaveInvalid', error.response.data.detail);
                } else {
                    console.error('Error saving method config.');
                    this.configChangeSuccess = false
                    this.configMessage = Localizer.get('configSaveError');
                }
            }
        },

        async resetMethodConfig() {
            try {
                const res = await backendClient.resetConfig(this.method);
                console.log('Reset method config.');
                this.methodConfig = res.config_values;
                this.methodConfigSchema = res.config_schema;
                this.configChangeSuccess = true
                this.configMessage = Localizer.get('configReset')
            } catch (error) {
                console.error('Error resetting method config.');
                this.methodConfig = null;
                this.methodConfigSchema = null;
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
    mounted() {
        //this.fetchMethodConfig(); // ... is called in this stage, but moved to App.mounted to fix concurrency issues
    },
    watch: {
        method() {
            this.fetchMethodConfig();
        },
    }
};
</script>

<style scoped>

</style>