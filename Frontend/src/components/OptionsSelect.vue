<template>
    <div>
        <AppAccordion
            id="options-selector"
            :items="getCombinedSettingsData()"
            :get-key="setting => setting.elementId"
            variant="compact"
        >
            <template #header="{ item: { data, name, elementId, icon } }">
                <div class="d-flex me-1 p-1 text-start" style="height: 100%">
                    <i class="fa fs-4" :class="[icon]" style="width: 30px" />
                </div>
                <div class="d-flex flex-column">
                    <div>
                        {{ data[this.getSelectedItem(elementId)] }}
                    </div>
                    <div class="text-muted">
                        {{ name }}
                    </div>
                </div>
            </template>

            <template #body="{ item: { data, elementId } }">
                <div v-for="(name, itemId) in data"
                     :key="itemId"
                     class="options-item"
                     @click="this.select(elementId, itemId)">
                    {{ name }}
                    <i class="fa fa-check-circle ms-1" v-if="this.isSelectedItem(elementId, itemId)" />
                </div>
            </template>
        </AppAccordion>
    </div>
</template>

<script>
import conf, {Methods} from '../../config.js';
import Localizer from "../Localizer.js";
import AudioManager from "../AudioManager.js";
import { getCurrentTheme, getColorThemes, setColorTheme } from '../ColorThemes.js';
import AppAccordion from "./AppAccordion.vue";
import ComboBox from "./ComboBox.vue";

export default {
    name: "OptionsSelect",
    components: {AppAccordion, ComboBox},
    data() {
        return {
            selectedItems: {},
        };
    },
    setup() {
        return { };
    },

    methods: {
        getCombinedSettingsData() {
            const res = [
                this.getMethodsData(),
                this.getLanguageData(),
                this.getColorModeData(),
            ]
            if (AudioManager.isRecognitionSupported()) {
                res.push(this.getAudioData());
            }
            return res;
        },

        getMethodsData() {
            return {
                data: Methods,
                name: Localizer.get('settings_method'),
                elementId: 'method',
                icon: 'fa-server',
            }
        },

        getLanguageData() {
            const locales = Localizer.getAvailableLocales()
            const langData = {};
            for (let lang of locales) {
                langData[lang.key] = lang.name;
            }
            return {
                data: langData,
                name: Localizer.get('settings_language'),
                elementId: 'language',
                icon: 'fa-globe',
            }
        },

        getColorModeData() {
            return {
                data: getColorThemes(),
                name: Localizer.get('settings_colorMode'),
                elementId: 'colorMode',
                icon: 'fa-adjust',
            }
        },

        getAudioData() {
            return {
                data: AudioManager.getAudioMethods(),
                name: Localizer.get('settings_audio'),
                elementId: 'audio',
                icon: 'fa-microphone',
            }
        },

        select(key, value) {
            this.selectedItems[key] = value;
            switch (key) {
                case 'method': conf.method = value; break;
                case 'language': this.updateLanguage(value); break;
                case 'colorMode': setColorTheme(value); break;
                case 'audio': conf.audioMethod = value; break;
                default: break;
            }
        },

        updateLanguage(newLanguage) {
            Localizer.language = newLanguage;
            Localizer.reloadSampleQuestions(conf.selectedCategory);
        },

        getSelectedItem(key) {
            return this.selectedItems[key];
        },

        isSelectedItem(key, value) {
            return this.selectedItems[key] === value;
        },
    },

    mounted() {
        this.select('method', conf.method);
        this.select('language', Localizer.language);
        this.select('colorMode', getCurrentTheme());
        this.select('audio', conf.audioMethod);
    }
}
</script>

<style scoped>
#options-selector {
    max-width: 800px;
}

.options-item {
    color: var(--text-primary-color);
    cursor: pointer;
    padding: 0.5rem;
}

.options-item:hover {
    color: var(--primary-color) !important;
    transform: translateY(-1px);
}

.options-item-disabled {
    cursor: default;
}
</style>
