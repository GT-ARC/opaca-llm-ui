<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div v-if="!isMobile" class="sidebar-title">
        {{ Localizer.get('tooltipSidebarInfo') }}
    </div>

    <div v-if="this.isLoading">
        <i class="fa fa-circle-notch fa-spin me-1" />
        {{ Localizer.get('platformInfoLoading') }}
    </div>
    <div v-else-if="!isPlatformConnected" class="placeholder-container">
        <img src="../../assets/opaca-llm-sleeping-dog-dark.png" alt="Sleeping-dog" class="placeholder-image" />
        <h5 class="p-4">
            {{ Localizer.get('platformInfoMissing') }}
        </h5>
    </div>
    <div v-else
         v-html="this.howAssistContent"
         class="info-content w-auto"
    />
</div>
</template>

<script>
import conf from "../../../config.js";
import Localizer from "../../Localizer.js";
import {useDevice} from "../../useIsMobile.js";
import backendClient from "../../utils.js";
import {marked} from "marked";

export default {
    name: "SidebarInfo",
    props: {
        isPlatformConnected: Boolean,
    },
    emits: ['update-platform-info'],
    setup() {
        const { isMobile } = useDevice();
        return { conf, Localizer, isMobile };
    },
    data() {
        return {
            howAssistContent: '',
            isLoading: false,
        }
    },
    methods: {
        async showHowCanYouHelpInSidebar() {
            try {
                this.isLoading = true;
                const response = await backendClient.queryNoChat("simple-tools", Localizer.get('platformInfoRequest'), false);
                const answer = response.agent_messages[0].content;
                this.howAssistContent = marked.parse(answer);
            } catch (error) {
                console.error("ERROR " + error);
                this.howAssistContent = Localizer.get('platformInfoFailed', error);
            } finally {
                this.isLoading = false;
            }
        },

    },
    mounted() {},
    watch: {
        isPlatformConnected(newVal) {
            if (newVal) {
                this.showHowCanYouHelpInSidebar();
            }
            this.$emit('update-platform-info', newVal);
        }
    }
}
</script>

<style scoped>
.info-content {
    color: var(--text-primary-color);
}

.placeholder-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 2rem;
    box-sizing: border-box;
    color: var(--text-secondary-light);
}

.placeholder-image {
    width: 180px;
    margin-bottom: 1rem;
    opacity: 0.6;
}

</style>