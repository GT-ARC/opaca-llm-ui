<!-- SidebarQuestions Component -->
<template>
<div class="container flex-grow-1 overflow-hidden overflow-y-auto">
    <InputDialogue ref="editDialog" />

    <div class="sidebar-title">
        {{ Localizer.get('sidebar_questions') }}
        <i v-if="!isEditModeActive"
           class="fa fa-plus ms-auto sidebar-title-action"
           :class="{ disabled: !isEditingAllowed }"
           :aria-disabled="!isEditingAllowed"
           @click="this.addNewCategory()"
           :title="Localizer.get('questions_addCategory')" />
        <i v-else
           class="fa fa-sync ms-auto sidebar-title-action"
           :class="{
               'fa-spin': isRegenerating,
               disabled: isRegenerating || !isEditingAllowed,
           }"
           :aria-disabled="isRegenerating || !isEditingAllowed"
           @click="autogenerateSampleQuestions()"
           :title="Localizer.get('questions_regenerate')" />
        <i v-if="isEditModeActive"
           class="fa fa-undo sidebar-title-action sidebar-title-action-danger"
           :class="{ disabled: !isEditingAllowed }"
           :aria-disabled="!isEditingAllowed"
           @click="this.resetPrompts()"
           :title="Localizer.get('questions_reset')" />
        <i class="fa fa-edit sidebar-title-action sidebar-title-action-secondary"
           :class="{ active: isEditModeActive }"
           :aria-pressed="isEditModeActive"
           @click="isEditModeActive = !isEditModeActive"
           :title="Localizer.get('questions_toggleEditMode')" />
    </div>

    <AppAccordion
        id="sidebar-questions"
        :model-value="activeQuestionSection"
        @update:model-value="setActiveQuestionSection"
        :items="visiblePromptSections"
        :get-key="getSectionKey"
        button-class="text-center"
    >
        <template #header="{ item: section }">
            <span class="section-icon">{{ section.icon }}</span>
            <span class="section-title">{{ section.header }}</span>
            <span class="section-actions float-end">
                <i v-if="isEditModeActive && !section.is_default"
                   class="fa fa-edit click-icon"
                   :class="{'disabled': !this.isEditingAllowed || (section.id === this.autogenKey && this.isRegenerating)}"
                   @click.stop.prevent="this.editCategory(section)"
                   :title="Localizer.get('questions_editCategory')"
                />
                <i v-if="isEditModeActive"
                   class="fa fa-remove click-icon"
                   :class="{'disabled': !this.isEditingAllowed || (section.id === this.autogenKey && this.isRegenerating)}"
                   @click.stop.prevent="this.deleteCategory(section, getSectionIndex(section))"
                   :title="Localizer.get('questions_deleteCategory')"
                />
            </span>
        </template>

        <template #body="{ item: section }">
            <!-- category questions -->
            <div v-for="(q, qIndex) in section.questions"
                 :key="qIndex"
                 class="question-item"
                 @click="this.$emit('select-question', q.question)">
                <span class="question-text">
                    <i v-if="section.id === this.autogenKey && isRegenerating"
                       :class="['fa', 'fa-ellipsis', 'fa-beat-fade', 'text-center', 'w-100']"
                    />
                    <span v-else class="mb-auto">{{ q?.question }}</span>
                </span>
                <i v-if="isEditModeActive && !section.is_default && section.id !== this.autogenKey"
                   class="fa fa-edit click-icon"
                   :class="{'disabled': !this.isEditingAllowed}"
                   @click.stop="this.editPrompt(section, q)"
                   :title="Localizer.get('questions_editPrompt')"
                />
                <i v-if="isEditModeActive && section.id !== this.autogenKey"
                   class="fa fa-remove click-icon"
                   :class="{'disabled': !this.isEditingAllowed}"
                   @click.stop="this.deletePrompt(section, q, qIndex)"
                   :title="Localizer.get('questions_deletePrompt')"
                />
            </div>

            <!-- add new prompt button -->
            <div v-if="isEditModeActive && !section.is_default && section.id !== this.autogenKey"
                 class="question-item justify-content-center"
                 :class="{'disabled': !this.isEditingAllowed}"
                 :aria-disabled="!isEditingAllowed"
                 @click.stop="this.addNewPrompt(section)">
                <i class="fa fa-plus me-1" />
                <span>{{ Localizer.get('questions_addPrompt') }}</span>
            </div>
        </template>
    </AppAccordion>

</div>
</template>

<script>
import Localizer from "../../Localizer.js";
import conf from "../../../config.js";
import backendClient from "../../utils.js";
import {nextTick} from "vue";
import {useDevice} from "../../useIsMobile.js";
import AppAccordion from "../AppAccordion.vue";
import InputDialogue from "../InputDialogue.vue";

export default {
    name: 'SidebarQuestions',
    components: { AppAccordion, InputDialogue },
    props: {
        sidebarView: String,
    },
    emits: [
        'select-question',
    ],
    data() {
        return {
            isEditModeActive: false,
            isEditingAllowed: true, // not allowed while save/load calls are in progress
            isRegenerating: false,
            activeQuestionSection: null,
        }
    },
    setup() {
        const {isMobile} = useDevice();
        return { conf, Localizer, isMobile };
    },
    methods: {
        async autogenerateSampleQuestions(numQuestions = 5) {
            this.isRegenerating = true;
            const newQuestions = {
                id: this.autogenKey,
                header: Localizer.get('questions_generated'),
                icon: "🪄",
                visible: true,
                is_default: false,
                questions: (new Array(numQuestions)).map(() => ({
                    question: "__loading__",
                    icon: "",
                }))
            };

            // Push new section or replace old questions with placeholders
            let prevIdx = Localizer.getPrompts()
                .findIndex(obj => obj.id === this.autogenKey)
            let prevQuestions = null
            if (prevIdx === -1) {
                Localizer.getPrompts().push(newQuestions);
                prevIdx = Localizer.getPrompts().length - 1;
            } else {
                newQuestions.header = Localizer.getPrompts()[prevIdx].header;
                newQuestions.icon = Localizer.getPrompts()[prevIdx].icon;
                prevQuestions = Localizer.getPrompts()[prevIdx].questions;
                Localizer.getPrompts()[prevIdx] = newQuestions;
            }

            // Wait for initial push of questions and then show autogenerated questions
            await nextTick();
            this.expandSectionById(this.autogenKey);
            Localizer.reloadSampleQuestions(newQuestions.header);

            // Construct LLM request
            let user_query = `Based on your available tools, I want you to
                generate me exactly ${numQuestions} requests or questions a user could give you. These ${numQuestions} requests or
                questions should directly reference one or more of your available tools. I want you to
                provide me your answer as a JSON file and NOTHING ELSE. Your response should look like this

                {
                   '1': {'question': 'Example request...', 'icon': '🪄'},
                   '2': {'question': 'Example request...', 'icon': '🤖'},
                   '3': ...
                }

                Some of the queries may also contain placeholders, like so: "Get the weather in [city]".
                DO NOT CALL ANY TOOLS for creating those suggestions!
                `;

            if (Localizer.language === 'DE') {
                user_query += "\n\nGenerate all questions in German!";
            }

            // Make sure to not generate any of the previous questions
            if (prevQuestions) {
                user_query += "\n\nPlease DO NOT generate the following questions:\n" +
                    JSON.stringify(prevQuestions);
            }

            try {
                // Let backend generate user questions
                const res = await backendClient.queryNoChat("simple-tools", user_query, 60000);
                const questions = res.content;
                const parsedQuestions = JSON.parse(questions.slice(questions.indexOf('{'), questions.lastIndexOf('}') + 1));
                newQuestions.questions = Object.values(parsedQuestions);

                // Replace autogenerated requests into sidebarQuestions
                Localizer.getPrompts()[prevIdx] = newQuestions;

                // save new prompts
                await backendClient.savePrompts(Localizer.samplePrompts);
            } catch (error) {
                console.log("Failed to auto-generate prompts: " + error);
                Localizer.getPrompts().splice(prevIdx, 1);
            } finally {
                this.isRegenerating = false;
            }

        },

        async loadPrompts() {
            Localizer.samplePrompts = await backendClient.getPrompts();
            Localizer.reloadSampleQuestions();
            this.syncActiveQuestionSection();
        },

        getPromptSections() {
            return Localizer.getPrompts() ?? [];
        },

        getSectionKey(section, index) {
            return section?.id ?? section?.header ?? index;
        },

        getSectionIndex(section) {
            return this.getPromptSections().findIndex((candidate, index) => {
                return candidate === section || this.getSectionKey(candidate, index) === this.getSectionKey(section, index);
            });
        },

        toggleSection(index, show = null) {
            if (index < 0) return;
            const section = this.getPromptSections()[index];
            if (!section) return;
            const key = this.getSectionKey(section, index);

            // show not set -> invert current state
            if (show === null) {
                show = this.activeQuestionSection !== key;
            }

            this.activeQuestionSection = show ? key : null;
            this.updateSelectedCategory(this.activeQuestionSection);
        },

        toggleSectionById(id, show = null) {
            const index = this.getPromptSections()
                .findIndex(section => section.id === id);
            this.toggleSection(index, show);
        },

        expandSectionById(id) {
            this.toggleSectionById(id, true);
        },

        setActiveQuestionSection(key) {
            this.activeQuestionSection = key;
            this.updateSelectedCategory(key);
        },

        updateSelectedCategory(key) {
            const prompts = this.getPromptSections();
            const index = prompts
                .findIndex((section, sectionIndex) => this.getSectionKey(section, sectionIndex) === key);
            conf.selectedCategory = index >= 0
                ? prompts[index].header
                : "none";
        },

        syncActiveQuestionSection() {
            const prompts = this.getPromptSections();
            const index = prompts
                .findIndex(section => section.header === conf.selectedCategory);
            const section = prompts[index];
            this.activeQuestionSection = section ? this.getSectionKey(section, index) : null;
        },

        async resetPrompts() {
            if (!confirm(Localizer.get('questions_reset_confirm'))) return;
            this.isEditingAllowed = false;
            await backendClient.resetPrompts();
            Localizer.samplePrompts = await backendClient.getPrompts();
            Localizer.reloadSampleQuestions();
            this.isEditingAllowed = true;
        },

        addNewPrompt(category) {
            if (!this.isEditingAllowed) return;
            const schema = {
                question: { type: 'textarea', label: 'Prompt', default: "" },
                icon: { type: 'text', label: 'Icon', default: "⭐" },
            };
            this.$refs.editDialog.showDialogue(Localizer.get('questions_addPrompt'), null, null, schema,
                values => this.handleAddPromptOk(values, category));
        },

        editPrompt(category, question) {
            if (!this.isEditingAllowed) return;
            const schema = {
                question: { type: 'textarea', label: 'Prompt', default: question.question, },
                icon: { type: 'text', label: 'Icon', default: question.icon },
            };
            this.$refs.editDialog.showDialogue(Localizer.get('questions_editPrompt'), null, null, schema,
                values => this.handleEditPromptOk(values, category, question));
        },

        async deletePrompt(category, question, index) {
            if (!confirm(Localizer.get('questions_deletePrompt_confirm', question?.question))) return;
            this.isEditingAllowed = false;
            category.questions.splice(index, 1);
            await backendClient.savePrompts(Localizer.samplePrompts);
            this.isEditingAllowed = true;
        },

        addNewCategory() {
            if (!this.isEditingAllowed) return;
            const schema = {
                header: { type: 'text', label: 'Header' },
                icon: { type: 'text', label: 'Icon', default: "⭐" },
            };
            this.$refs.editDialog.showDialogue(Localizer.get('questions_addCategory'), null, null, schema,
                values => this.handleAddCategoryOk(values));
        },

        editCategory(category) {
            if (!this.isEditingAllowed) return;
            const schema = {
                header: { type: 'text', label: 'Header', default: category.header },
                icon: { type: 'text', label: 'Icon', default: category.icon },
            };
            this.$refs.editDialog.showDialogue(Localizer.get('questions_editCategory'), null, null, schema,
                values => this.handleEditCategoryOk(values, category));
        },

        async deleteCategory(category, index) {
            if (!confirm(Localizer.get('questions_deleteCategory_confirm', category.header))) return;
            this.isEditingAllowed = false;
            Localizer.getPrompts().splice(index, 1);
            await backendClient.savePrompts(Localizer.samplePrompts);
            this.isEditingAllowed = true;
        },

        async handleAddPromptOk(values, category) {
            if (!values.question) return;
            this.isEditingAllowed = false;
            category.questions.push({
                question: values.question,
                icon: values.icon?.[0] || "⭐",
            });
            await backendClient.savePrompts(Localizer.samplePrompts);
            Localizer.reloadSampleQuestions();
            this.isEditingAllowed = true;
        },

        async handleEditPromptOk(values, category, question) {
            this.isEditingAllowed = false;
            question.question = values.question;
            await backendClient.savePrompts(Localizer.samplePrompts);
            Localizer.reloadSampleQuestions();
            this.isEditingAllowed = true;
        },

        async handleAddCategoryOk(values) {
            if (!values.header) return;
            this.isEditingAllowed = false;
            const newCategory = {
                id: values.header,
                header: values.header,
                icon: values.icon?.[0] || "⭐",
                visible: true,
                is_default: false,
                questions: [],
            };
            Localizer.getPrompts().push(newCategory);

            // put autogenerated questions at the end
            const autogenIndex = Localizer.getPrompts()
                .findIndex(item => item.id === this.autogenKey);
            if (autogenIndex >= 0) {
                const [autogenCat] = Localizer.getPrompts().splice(autogenIndex, 1);
                Localizer.getPrompts().push(autogenCat);
            }


            await backendClient.savePrompts(Localizer.samplePrompts);
            Localizer.reloadSampleQuestions();
            this.isEditingAllowed = true;
            // The user may have switched sidebars while the category was saving.
            if (this.sidebarView === 'questions') {
                this.isEditModeActive = true;
                await nextTick();
                this.expandSectionById(newCategory.id);
            }
        },

        async handleEditCategoryOk(values, category) {
            this.isEditingAllowed = false;
            category.header = values.header;
            category.icon = values.icon;
            await backendClient.savePrompts(Localizer.samplePrompts);
            Localizer.reloadSampleQuestions();
            this.isEditingAllowed = true;
        },
    },

    computed: {
        visiblePromptSections() {
            return this.getPromptSections().filter(section => section.visible);
        },

        /** ID of the "Auto-Generated Questions" category. */
        autogenKey() {
            return 'autogenerated-questions';
        },
    },

    watch: {
        sidebarView(newView) {
            if (newView !== 'questions') {
                this.isEditModeActive = false;
            }
        },
    },

    async mounted() {
        Localizer.samplePrompts = await backendClient.getPrompts();
        this.syncActiveQuestionSection();
    }
}
</script>

<style scoped>
.section-icon {
    margin-right: 0.75rem;
    font-size: 1.25rem;
    width: 1.5rem;
    text-align: center;
}

.section-title {
    flex: 1;
    font-weight: 500;
}

.question-item {
    display: flex;
    align-items: center;
    padding: 0.75rem 0.25rem 0.75rem 0.75rem;
    cursor: pointer;
    color: var(--text-primary-color);
    background-color: var(--background-color);
    border: 1px solid var(--border-color);
    transition: all 0.2s ease;
}

.question-item:hover {
    background-color: var(--surface-color);
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
    border-color: var(--primary-color);
    color: var(--primary-color);
}

.question-text {
    flex: 1;
    font-size: 0.875rem;
    line-height: 1.4;
    /* Limit to 3 lines and add ellipsis */
    display: -webkit-box;
    -webkit-line-clamp: 3;
    line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: normal;
}

.question-menu-button:hover {
    background-color: var(--input-color);
    color: var(--text-danger-color);
}

.question-item.disabled {
    opacity: 0.5;
    cursor: default;
    transform: none;
    pointer-events: none;
    color: var(--text-primary-color) !important;
    border-color: var(--border-color) !important;
    background-color: var(--background-color) !important;
}
</style>
