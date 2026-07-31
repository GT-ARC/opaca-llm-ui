<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <div class="sidebar-title">
        {{ Localizer.get('sidebar_playBooks') }}
        <i class="fa fa-plus ms-auto sidebar-title-action"
           :class="{ disabled: isSaving }"
           :aria-disabled="isSaving"
           @click.stop="addPlayBook"
           :title="Localizer.get('playBooks_add')" />
    </div>

    <div v-if="isLoading">
        <i class="fa fa-circle-notch fa-spin me-1" />
        {{ Localizer.get('playBooks_loading') }}
    </div>

    <div v-if="errorMessage" class="sidebar-empty-state">
        {{ errorMessage }}
    </div>

    <div v-if="!isLoading && !errorMessage && playBooks.length === 0"
         class="sidebar-empty-state">
        {{ Localizer.get('playBooks_missing') }}
    </div>

    <AppAccordion
        v-if="!isLoading && playBooks.length > 0"
        id="play-books-accordion"
        class="text-start"
        :items="sortedPlayBooks"
        :get-key="playBook => playBook.id"
    >
        <template #header="{ item: playBook }">
            <i class="fa fa-clipboard-check me-3"
               :class="{ 'play-book-disabled': !playBook.enabled }" />
            <strong class="play-book-name"
                    :class="{ 'play-book-disabled': !playBook.enabled }">
                {{ playBook.name }}
            </strong>

            <span class="play-book-actions section-actions">
                <i class="fa click-icon"
                   :class="playBook.enabled ? 'fa-toggle-on' : 'fa-toggle-off'"
                   @click.stop="togglePlayBook(playBook.id)"
                   :title="Localizer.get(playBook.enabled ? 'playBooks_disable' : 'playBooks_enable')" />
                <i class="fa fa-remove click-icon"
                   @click.stop="deletePlayBook(playBook)"
                   :title="Localizer.get('playBooks_delete')" />
            </span>
        </template>

        <template #body="{ item: playBook }">
            <div class="play-book-body"
                 :class="{ 'play-book-disabled': !playBook.enabled }">
                <div class="play-book-section">
                    <strong>{{ Localizer.get('playBooks_whenToUse') }}</strong>
                    <p>{{ playBook.when_to_use }}</p>
                </div>
                <div class="play-book-section">
                    <strong>{{ Localizer.get('playBooks_whatToDo') }}</strong>
                    <p class="play-book-instructions">{{ playBook.what_to_do }}</p>
                </div>
            </div>
        </template>
    </AppAccordion>

    <InputDialogue ref="input" />
</div>
</template>

<script>
import AppAccordion from "../AppAccordion.vue";
import InputDialogue from "../InputDialogue.vue";
import Localizer from "../../Localizer.js";
import backendClient from "../../utils.js";
import { useDevice } from "../../useIsMobile.js";

export default {
    name: "SidebarPlayBooks",
    components: { AppAccordion, InputDialogue },
    props: {
        sidebarView: String,
    },
    setup() {
        const { isMobile } = useDevice();
        return { Localizer, isMobile };
    },
    data() {
        return {
            playBooks: [],
            isLoading: false,
            isSaving: false,
            errorMessage: "",
        };
    },
    methods: {
        async loadPlayBooks() {
            this.isLoading = true;
            this.errorMessage = "";
            try {
                this.playBooks = await backendClient.getPlayBooks();
            } catch (error) {
                console.error("Failed to load play books", error);
                this.errorMessage = Localizer.get("playBooks_loadFailed");
            } finally {
                this.isLoading = false;
            }
        },

        async addPlayBook() {
            await this.$refs.input.showDialogue(
                Localizer.get("playBooks_add"),
                null,
                null,
                {
                    name: {
                        type: "text",
                        label: Localizer.get("playBooks_name"),
                    },
                    when_to_use: {
                        type: "textarea",
                        label: Localizer.get("playBooks_whenToUse"),
                        rows: 4,
                    },
                    what_to_do: {
                        type: "textarea",
                        label: Localizer.get("playBooks_whatToDo"),
                        rows: 7,
                    },
                },
                async values => {
                    const playBookData = {
                        name: values.name.trim(),
                        when_to_use: values.when_to_use.trim(),
                        what_to_do: values.what_to_do.trim(),
                    };
                    this.isSaving = true;
                    this.errorMessage = "";
                    try {
                        const createdPlayBook = await backendClient.savePlayBook(playBookData);
                        this.playBooks.push(createdPlayBook);
                    } catch (error) {
                        console.error("Failed to save play book", error);
                        this.errorMessage = Localizer.get("playBooks_saveFailed");
                        throw new Error(Localizer.get("playBooks_saveFailed"));
                    } finally {
                        this.isSaving = false;
                    }
                },
            );
        },

        async togglePlayBook(playBookId) {
            if (this.isSaving) return;
            const playBookIndex = this.playBooks.findIndex(playBook => playBook.id === playBookId);
            if (playBookIndex < 0) return;

            const playBook = this.playBooks[playBookIndex];
            const enabled = !playBook.enabled;
            this.isSaving = true;
            this.errorMessage = "";
            try {
                const updatedPlayBook = await backendClient.setPlayBookEnabled(playBook, enabled);
                this.playBooks[playBookIndex] = updatedPlayBook;
            } catch (error) {
                console.error("Failed to update play book", error);
                this.errorMessage = Localizer.get("playBooks_saveFailed");
            } finally {
                this.isSaving = false;
            }
        },

        async deletePlayBook(playBook) {
            if (this.isSaving) return;
            await this.$refs.input.showDialogue(
                Localizer.get("playBooks_delete"),
                Localizer.get("playBooks_delete_confirm", playBook.name),
                null,
                {},
                async () => {
                    this.isSaving = true;
                    this.errorMessage = "";
                    try {
                        await backendClient.deletePlayBook(playBook.id);
                        this.playBooks = this.playBooks.filter(item => item.id !== playBook.id);
                    } catch (error) {
                        console.error("Failed to delete play book", error);
                        this.errorMessage = Localizer.get("playBooks_deleteFailed");
                        throw new Error(Localizer.get("playBooks_deleteFailed"));
                    } finally {
                        this.isSaving = false;
                    }
                },
            );
        },
    },
    computed: {
        sortedPlayBooks() {
            return [...this.playBooks]
                .sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
        },
    },
    watch: {
        sidebarView(newView) {
            if (newView === "playBooks") {
                this.loadPlayBooks();
            }
        },
    },
};
</script>

<style scoped>
.play-book-name {
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.play-book-actions {
    flex: 0 0 auto;
    display: inline-flex;
    align-items: center;
}

.fa-toggle-on {
    color: var(--text-success-color);
}

.fa-toggle-off {
    color: var(--text-secondary-color);
}

.play-book-disabled {
    opacity: 0.5;
}

.play-book-body {
    padding: 0.75rem;
}

.play-book-section + .play-book-section {
    margin-top: 1rem;
}

.play-book-section p {
    margin: 0.25rem 0 0;
    overflow-wrap: anywhere;
}

.play-book-instructions {
    white-space: pre-wrap;
}
</style>
