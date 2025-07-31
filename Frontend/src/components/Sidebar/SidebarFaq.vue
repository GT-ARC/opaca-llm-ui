<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div v-if="!isMobile" class="sidebar-title">
        {{ Localizer.get('tooltipSidebarFaq') }}
    </div>
    <div v-html="this.faqContent"
         class="d-flex flex-column text-start faq-content">
    </div>
</div>
</template>

<script>
import conf from '../../../config.js'
import Localizer from "../../Localizer.js";
import {useDevice} from "../../useIsMobile.js";
import {marked} from "marked";

export default {
    name: "SidebarFaq",
    setup() {
        const {isMobile} = useDevice();
        return { conf, Localizer, isMobile };
    },
    data() {
        return {
            faqContent: '',
        };
    },
    methods: {
        async buildFaqContent() {
            const readmeUrl = '/src/assets/about.md';
            try {
                const response = await fetch(readmeUrl);
                if (response.ok) {
                    const faqRaw = await response.text();
                    this.faqContent = marked.parse(faqRaw);
                } else {
                    console.error('Failed to fetch FAQ content:', response.status, response);
                }
            } catch (error) {
                console.error('Failed to fetch FAQ content:', error);
            }
        },
    },
    mounted() {
        this.buildFaqContent();
    },
};
</script>

<style scoped>
.faq-content {
    color: var(--text-primary-color);
}
</style>