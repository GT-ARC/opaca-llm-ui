<!-- SidebarQuestions Component -->
<template>
    <div id="sidebar-questions" class="accordion">
        <div v-for="(section, index) in this.getQuestions()"
             :key="index"
             class="accordion-item">
            <div class="accordion-header text-center">
                <button class="accordion-button collapsed text-center" type="button"
                        data-bs-toggle="collapse"
                        :data-bs-target="'#questions-' + index"
                        aria-expanded="false" :aria-controls="'#questions-' + index">
                    <span class="section-icon">{{ section.icon }}</span>
                    <span class="section-title">{{ section.header }}</span>
                </button>
            </div>

            <div :id="'questions-' + index"
                 class="accordion-collapse collapse"
                 data-bs-parent="#sidebar-questions">
                <div class="accordion-body">
                    <div v-for="(q, qIndex) in section.questions"
                         :key="qIndex"
                         class="question-item"
                         @click="$emit('select-question', q.question)">
                        <span class="question-text">{{ q.question }}</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import Localizer from "../Localizer.js";
import {sidebarQuestions} from "../Localizer.js";

export default {
    name: 'SidebarQuestions',
    data() {
        return {
            expandedSection: null
        }
    },
    methods: {
        getQuestions() {
            return sidebarQuestions[Localizer.language];
        },

        toggleSection(index) {
            const questions = this.getQuestions();
            if (this.expandedSection === index) {
                this.expandedSection = null;
                this.$emit('category-selected', null);
            } else {
                this.expandedSection = index;
                this.$emit('category-selected', index in questions ? questions[index].header : "None");
            }
        },

        toggleSectionByHeader(header) {
            const index = this.getQuestions().findIndex(section => section.header === header);
            this.toggleSection(index);
        },

        expandSectionByHeader(header) {
            const questions = this.getQuestions();
            const index = this.getQuestions().findIndex(section => section.header === header);
            if (index != -1 && this.expandedSection !== index) {
                this.expandedSection = index;
                this.$emit('category-selected', index in questions ? questions[index].header : "None");
            }
        }
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
    padding: 0.75rem 1rem;
    margin: 0.25rem 0;
    cursor: pointer;
    color: var(--text-primary-color);
    background-color: var(--background-color);
    border: 1px solid var(--border-color);
    border-radius: var(--bs-border-radius);
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
}
</style> 