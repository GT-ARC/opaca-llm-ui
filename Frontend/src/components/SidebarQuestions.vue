<!-- SidebarQuestions Component -->
<template>
    <div class="sidebar-questions">
        <div v-for="(section, index) in questions" :key="index" class="question-section">
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
export default {
    name: 'SidebarQuestions',
    props: {
        questions: {
            type: Array,
            required: true
        }
    },
    data() {
        return {
            expandedSection: 0
        }
    },
    watch: {
        questions: {
            immediate: true,
            handler() {
                this.expandedSection = 0;
            }
        }
    },
    methods: {
        toggleSection(index) {
            if (this.expandedSection === index) {
                this.expandedSection = null;
                this.$emit('category-selected', null);
            } else {
                this.expandedSection = index;
                this.$emit('category-selected', this.questions[index].header);
            }
        },
        toggleSectionByHeader(header) {
            const index = this.questions.findIndex(section => section.header === header);
            this.toggleSection(index);
        },
        expandSectionByHeader(header) {
            const index = this.questions.findIndex(section => section.header === header);
            if (this.expandedSection !== index) {
                this.expandedSection = index;
                this.$emit('category-selected', this.questions[index].header);
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

/* Slide animation */
.slide-enter-active,
.slide-leave-active {
    transition: all 0.3s ease;
    max-height: 1000px;
}

.slide-enter-from,
.slide-leave-to {
    opacity: 0;
    max-height: 0;
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