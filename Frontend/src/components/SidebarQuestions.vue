<!-- SidebarQuestions Component -->
<template>
    <div class="sidebar-questions">
        <div v-for="(section, index) in this.getQuestions()" :key="index" class="question-section">
            <div class="section-header" 
                 @click="toggleSection(index)"
                 :class="{ 'expanded': expandedSection === index }">
                <span class="section-icon">{{ section.icon }}</span>
                <span class="section-title">{{ section.header }}</span>
                <i class="fa fa-chevron-down section-chevron"
                   :class="{ 'rotated': expandedSection === index }"/>
            </div>
            <transition name="slide">
                <div class="section-content" v-if="expandedSection === index">
                    <div v-for="(q, qIndex) in section.questions" 
                         :key="qIndex"
                         class="question-item"
                         @click="$emit('select-question', q.question)">
                        <span class="question-text">{{ q.question }}</span>
                    </div>
                </div>
            </transition>
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
                this.$emit('category-selected', index in questions ? questions[index].header : 'none');
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
                this.$emit('category-selected', index in questions ? questions[index].header : 'none');
            }
        }
    }
}
</script>

<style scoped>
.sidebar-questions {
    width: 100%;
    overflow-y: auto;
    padding: 1rem 0;
}

.question-section {
    margin-bottom: 0.5rem;
}

.section-header {
    display: flex;
    align-items: center;
    padding: 0.75rem 1rem;
    cursor: pointer;
    background-color: var(--surface-light);
    border: 1px solid var(--border-light);
    border-radius: var(--bs-border-radius);
    transition: all 0.2s ease;
    user-select: none;
}

.section-header:hover {
    background-color: var(--background-light);
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}

.section-header.expanded {
    background-color: var(--primary-light);
    color: white;
    border-color: var(--primary-light);
    margin-bottom: 0.5rem;
}

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

.section-chevron {
    transition: transform 0.3s ease;
}

.section-chevron.rotated {
    transform: rotate(180deg);
}

.section-content {
    overflow: hidden;
}

.question-item {
    display: flex;
    align-items: center;
    padding: 0.75rem 1rem;
    margin: 0.25rem 0;
    cursor: pointer;
    background-color: var(--background-light);
    border: 1px solid var(--border-light);
    border-radius: var(--bs-border-radius);
    transition: all 0.2s ease;
}

.question-item:hover {
    background-color: var(--surface-light);
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
    border-color: var(--primary-light);
    color: var(--primary-light);
}

.question-text {
    flex: 1;
    font-size: 0.875rem;
    line-height: 1.4;
}

@media (prefers-color-scheme: dark) {
    .section-header {
        background-color: var(--surface-dark);
        border-color: var(--border-dark);
        color: var(--text-primary-dark);
    }

    .section-header:hover {
        background-color: var(--background-dark);
    }

    .section-header.expanded {
        background-color: var(--primary-dark);
        border-color: var(--primary-dark);
    }

    .question-item {
        background-color: var(--background-dark);
        border-color: var(--border-dark);
        color: var(--text-primary-dark);
    }

    .question-item:hover {
        background-color: var(--surface-dark);
        border-color: var(--primary-dark);
        color: var(--primary-dark);
    }
}
</style> 