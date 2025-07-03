<template>
<div>
    <div id="options-selector"
         class="accordion">

        <!-- Backend Methods -->
        <OptionsSelectItem
            parent="options-selector"
            name="Methods"
            icon="fa-server"
            :data="Backends"
            :initialSelect="conf.DefaultBackend"
            @select="(_, methodId) => this.$emit('select-method', methodId)"
        />

        <!-- Languages -->
        <OptionsSelectItem
            parent="options-selector"
            name="Languages"
            icon="fa-globe"
            :data="this.getLanguageData()"
            :initialSelect="Localizer.language"
            @select="(_, langId) => this.$emit('select-language', langId)"
        />

        <OptionsSelectItem
            parent="options-selector"
            name="Colors"
            icon="fa-adjust"
            :data="{ 'light': 'Light', 'dark': 'Dark' }"
            :initialSelect="this.getInitialColorMode()"
            @select="(_, modeId) => this.$emit('select-color-mode', modeId)"
        />

        <OptionsSelectItem
            v-if="true"
            parent="options-selector"
            name="Audio"
            :icon="AudioManager.isVoiceServerConnected ? 'fa-microphone' : 'fa-microphone-slash'"
            :show-selected="false"
            :data="this.getAudioData()"
            initialSelect="address"
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
            const isDarkMode = (conf.ColorScheme === "light"
                ? false
                : conf.ColorScheme === "dark"
                    ? true
                    : window.matchMedia('(prefers-color-scheme: dark)').matches);
            return isDarkMode ? 'dark' : 'light';
        },

        getAudioData() {
            const data = {
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