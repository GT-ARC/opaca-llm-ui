<template>
<div>
    <div id="options-selector"
         class="accordion">

        <!-- Backend Methods -->
        <OptionsSelectItem
            parent="options-selector"
            elementId="methods"
            :name="Localizer.get('method')"
            icon="fa-server"
            :data="Backends"
            :initialSelect="conf.DefaultBackend"
            @select="(_, methodId) => this.$emit('select-method', methodId)"
        />

        <!-- Languages -->
        <OptionsSelectItem
            parent="options-selector"
            elementId="language"
            :name="Localizer.get('language')"
            icon="fa-globe"
            :data="this.getLanguageData()"
            :initialSelect="Localizer.language"
            @select="(_, langId) => this.$emit('select-language', langId)"
        />

        <OptionsSelectItem
            parent="options-selector"
            elementId="colors"
            :name="Localizer.get('colorMode')"
            icon="fa-adjust"
            :data="{ 'light': 'Light', 'dark': 'Dark' }"
            :initialSelect="this.getInitialColorMode()"
            @select="(_, modeId) => this.$emit('select-color-mode', modeId)"
        />

        <OptionsSelectItem
            v-if="AudioManager.isBackendConfigured()"
            parent="options-selector"
            name="Audio"
            :icon="AudioManager.isVoiceServerConnected ? 'fa-microphone' : 'fa-microphone-slash'"
            :show-selected="false"
            :data="this.getAudioData()"
            initialSelect="connectivity"
            :on-item-click="(item, itemId) => this.handleAudioClick(item, itemId)"
        />


    </div>
</div>
</template>

<script>
import conf, {Backends} from '../../config.js';
import OptionsSelectItem from "./OptionsSelectItem.vue";
import Localizer from "../Localizer.js";
import AudioManager from "../AudioManager.js";

export default {
    name: "OptionsSelect",
    components: {
        OptionsSelectItem,
    },
    props: {},
    data() {
        return {};
    },
    setup() {
        return { conf, Backends, Localizer, AudioManager };
    },
    emits: [
        'select-method',
        'select-language',
        'select-color-mode',
    ],

    methods: {
        getLanguageData() {
            const locales = Localizer.getAvailableLocales()
            const langData = {};
            for (let lang of locales) {
                langData[lang.key] = lang.name;
            }
            return langData;
        },

        getInitialColorMode() {
            if (conf.ColorScheme === 'system') {
                return window.matchMedia('(prefers-color-scheme: dark)').matches
                    ? 'dark' : 'light';
            }
            return conf.ColorScheme;
        },

        getAudioData() {
            const data = {
                'connectivity': AudioManager.isVoiceServerConnected
                    ? Localizer.get('ttsConnected')
                    : Localizer.get('ttsDisconnected'),
                'address': String(conf.VoiceServerUrl),
            };
            if (! AudioManager.isVoiceServerConnected) {
                data['retry'] = Localizer.get('ttsRetry');
            }
            return data;
        },

        handleAudioClick(item, itemId) {
            if (itemId === 'retry') {
                AudioManager.initVoiceServerConnection();
            }
        },
    },
}
</script>

<style scoped>
#options-selector {
    max-width: 800px;
}
</style>