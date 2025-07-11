<template>
<div>
    <div id="options-selector"
         class="accordion">

        <!-- Loop for methods, language and color mode -->
        <div v-for="{ data, name, elementId, icon } in this.getCombinedSettingsData()"
             class="accordion-item m-0">

            <!-- Header -->
            <div class="accordion-header options-header">
                <div class="accordion-button collapsed d-flex p-2 rounded-0"
                     data-bs-toggle="collapse"
                     :data-bs-target="`#selector-${elementId}`">
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
                </div>
            </div>

            <!-- Body -->
            <div :id="`selector-${elementId}`"
                 class="accordion-collapse collapse"
                 data-bs-parent="#options-selector">
                <div class="accordion-body">
                    <div v-for="(name, itemId) in data"
                         :key="itemId"
                         class="options-item"
                         @click="this.select(elementId, itemId)">
                        {{ name }}
                        <i class="fa fa-check-circle ms-1" v-if="this.isSelectedItem(elementId, itemId)" />
                    </div>
                </div>
            </div>

        </div>

        <!-- Audio -->
        <div v-if="AudioManager.isBackendConfigured()"
             class="accordion-item m-0">

            <!-- Header -->
            <div class="accordion-header options-header">
                <div class="accordion-button collapsed d-flex p-2 rounded-0"
                     data-bs-toggle="collapse"
                     data-bs-target="#selector-audio">
                    <div class="d-flex me-1 p-1 text-start" style="height: 100%">
                        <i class="fa fs-4" :class="[AudioManager.isVoiceServerConnected ? 'fa-microphone' : 'fa-microphone-slash']" style="width: 30px" />
                    </div>
                    <div class="d-flex flex-column">
                        <div>
                            {{Localizer.get(AudioManager.isVoiceServerConnected ? 'ttsConnected' : 'ttsDisconnected') }}
                        </div>
                        <div class="text-muted">
                            {{ Localizer.get('audioServerSettings') }}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Body -->
            <div id="selector-audio"
                 class="accordion-collapse collapse"
                 data-bs-parent="#options-selector">
                <div class="accordion-body">
                    <div class="text-muted options-item options-item-disabled">
                        {{ String(conf.VoiceServerUrl) }}
                    </div>
                    <div v-if="! AudioManager.isVoiceServerConnected"
                         class="options-item text-center">
                        <button type="button" class="btn btn-outline-danger w-100"
                                @click="() => AudioManager.initVoiceServerConnection()">
                            <i class="fa fa-refresh"/>
                            {{ Localizer.get('ttsRetry') }}
                        </button>
                    </div>
                </div>
            </div>

        </div>


    </div>
</div>
</template>

<script>
import conf, {Backends} from '../../config.js';
import Localizer from "../Localizer.js";
import AudioManager from "../AudioManager.js";

export default {
    name: "OptionsSelect",
    components: {},
    props: {},
    data() {
        return {
            selectedItems: {}
        };
    },
    setup() {
        return { conf, Backends, Localizer, AudioManager };
    },
    emits: [
        'select'
    ],

    methods: {
        getCombinedSettingsData() {
            return [
                this.getMethodsData(),
                this.getLanguageData(),
                this.getColorModeData(),
            ]
        },

        getMethodsData() {
            return {
                data: Backends,
                name: Localizer.get('method'),
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
                name: Localizer.get('language'),
                elementId: 'language',
                icon: 'fa-globe',
            }
        },

        getColorModeData() {
            return {
                data: { light: 'Light', dark: 'Dark' },
                name: Localizer.get('colorMode'),
                elementId: 'colorMode',
                icon: 'fa-adjust',
            }
        },

        getInitialColorMode() {
            if (conf.ColorScheme === 'system') {
                return window.matchMedia('(prefers-color-scheme: dark)').matches
                    ? 'dark' : 'light';
            }
            return conf.ColorScheme;
        },

        select(key, value) {
            this.selectedItems[key] = value;
            this.$emit('select', key, value);
        },

        getSelectedItem(key) {
            return this.selectedItems[key];
        },

        isSelectedItem(key, value) {
            return this.selectedItems[key] === value;
        },
    },

    mounted() {
        this.select('method', conf.DefaultBackend);
        this.select('language', Localizer.language);
        this.select('colorMode', this.getInitialColorMode());
    }
}
</script>

<style scoped>
#options-selector {
    max-width: 800px;
}

.options-header {
    margin: 0;
    cursor: pointer;
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

.accordion-item {
    min-width: min(300px, 100vw - 6rem);
    max-width: calc(100vw - 6rem);
}

.accordion-button .text-muted {
    transition: color 0.2s ease;
}

.accordion-button:hover .text-muted {
    color: var(--text-primary-color) !important;
}

.accordion-button:not(.collapsed) .text-muted {
    color: var(--text-primary-color) !important;
}

.accordion-header,
.accordion-item,
.accordion-button {
    border-radius: 0 !important;
}
</style>