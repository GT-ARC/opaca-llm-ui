<template>
<div id="options-selector"
    class="accordion">

    <!-- Backend Methods -->
    <OptionsSelectItem
        parent="options-selector"
        name="Backends"
        icon="fa-server"
        :data="Backends"
        initialSelect="tool-llm"
    />

    <!-- Languages -->
    <OptionsSelectItem
        parent="options-selector"
        name="Languages"
        icon="fa-globe"
        :data="Localizer.getAvailableLocales().map(lang => lang.name)"
        :initialSelect="0"
    />

</div>
</template>

<script>
import conf, {Backends} from '../../config.js';
import OptionsSelectItem from "./OptionsSelectItem.vue";
import Localizer from "../Localizer.js";

export default {
    name: "OptionsSelect",
    components: {
        OptionsSelectItem,
    },
    setup() {
        return { conf, Backends, Localizer };
    },
}
</script>

<style scoped>
#options-selector {
    max-width: 600px;
}
</style>