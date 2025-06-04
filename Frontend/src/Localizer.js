import {ref} from 'vue';
import {marked} from 'marked';
import {shuffleArray} from "./utils.js";
import AudioManager from "./AudioManager.js";


export const localizationData = {
    GB: {
        name: "English",
        language: 'Language',
        submit: 'Submit',
        welcome: 'Welcome to the OPACA LLM! You can use me to interact with the assistants and services available on the OPACA platform, or ask me general questions. How can I help you today?',
        connected: 'Connected! Available assistants and services:',
        unreachable: 'Please connect to a running OPACA platform.',
        unauthorized: 'Please provide your login credentials to connect to the OPACA platform.',
        none: 'None',
        speechRecognition: 'Speak' ,
        readLastMessage: 'Read Last',
        resetChat: 'Reset',
        opacaLocation: 'OPACA URL',
        inputPlaceholder: 'Send a message ...',
        socketClosed: 'It seems there was a problem in the response generation.',
        socketError: 'An Error occurred in the response generation: %1',
        ttsConnected: 'Connected',
        ttsDisconnected: 'Disconnected',
        ttsRetry: 'Retry Connection',
        ttsServerInfo: '%1 on %2',
        ttsServerUnavailable: 'Audio service not available',
        tooltipSidebarConnection: "Connection",
        tooltipSidebarPrompts: "Prompt Library",
        tooltipSidebarAgents: "Agents & Actions",
        tooltipSidebarConfig: "Configuration",
        tooltipSidebarLogs: "Logging",
        tooltipChatbubbleDebug: "Debug",
        tooltipChatbubbleAudioPlay: "Play Audio",
        tooltipChatbubbleAudioStop: "Stop Audio",
        tooltipChatbubbleAudioLoad: "Audio is loading ...",
    },

    DE: {
        name: "Deutsch",
        language: 'Sprache',
        submit: 'Senden',
        welcome: 'Willkommen beim OPACA LLM! Sie können mich nutzen, um mit den Assistenten und Diensten auf der OPACA-Plattform zu interagieren, oder auch allgemeine Fragen stellen. Wie kann ich Ihnen heute helfen?',
        connected: 'Verbunden! Verfügbare Assistenten und Dienste:',
        unreachable: 'Bitte verbinden Sie sich mit einer laufenden OPACA Plattform.',
        unauthorized: 'Bitte geben Sie Ihre Zugangsdaten an, um sich mit der OPACA Plattform zu verbinden.',
        none: 'Keine',
        speechRecognition: 'Sprechen' ,
        readLastMessage: 'Vorlesen',
        resetChat: 'Zurücksetzen',
        opacaLocation: 'OPACA URL',
        inputPlaceholder: 'Nachricht senden ...',
        socketClosed: 'Es scheint ein Problem bei der Erstellung der Antwort aufgetreten zu sein.',
        socketError: 'Bei der Erstellung der Antwort ist ein Fehler aufgetreten: %1',
        ttsConnected: 'Verbunden',
        ttsDisconnected: 'Nicht verbunden',
        ttsRetry: 'Erneut verbinden',
        ttsServerInfo: '%1 auf %2',
        ttsServerUnavailable: 'Audio-Dienst ist nicht erreichbar',
        tooltipSidebarConnection: "Verbindung",
        tooltipSidebarPrompts: "Prompt-Bibliothek",
        tooltipSidebarAgents: "Agenten & Aktionen",
        tooltipSidebarConfig: "Konfiguration",
        tooltipSidebarLogs: "Logging",
        tooltipChatbubbleDebug: "Debug",
        tooltipChatbubbleAudioPlay: "Audio abspielen",
        tooltipChatbubbleAudioStop: "Audio stoppen",
        tooltipChatbubbleAudioLoad: "Audio lädt ...",
    },
};


export const sidebarQuestions = {
    GB: [
        {
            "id": "taskAutomation",
            "header": "Task Automation",
            "icon": "🤖",
            "questions": [
                {"question": "Please fetch and summarize my latest e-mails.", "icon": "📧"},
                {"question": "Summarize my upcoming meetings for the next 3 days.", "icon": "📅"},
                {"question": "Show the phone numbers of all participants in my next meeting.", "icon": "📞"},
                {"question": "Draft an out-of-office email explaining that Tolga is my stand-in for the next 2 weeks.", "icon": "✉️"},
                {"question": "I need the phone numbers of the people working with LLM from the GoKI project.", "icon": "👥"},
                {"question": "Schedule a brainstorming session with Tobias.", "icon": "🧩"},
                {"question": "Find a meeting slot with the LLM team next week.", "icon": "📆"},
                {"question": "Show my calendar for next week.", "icon": "📅"}
            ]
        },
        {
            "id": "dataAnalysis",
            "header": "Data Analysis",
            "icon": "📊",
            "questions": [
                {"question": "Visualize the current energy mix of Germany in a meaningful way.", "icon": "⚡"},
                {"question": "Retrieve the current noise level in the kitchen and coworking space. Then, plot them in a bar chart for comparison.", "icon": "🔊"},
                {"question": "Create a bar plot comparing the current stock prices of Amazon, Apple, Microsoft and Nvidia.", "icon": "📊"},
                {"question": "Retrieve the current temperature, noise level and humidity of the kitchen and visualize it in a meaningful way.", "icon": "🌤️"},

            ]
        },
        {
            "id": "informationUpskilling",
            "header": "Information & Upskilling",
            "icon": "📚",
            "questions": [
                {"question": "How can you assist me?", "icon": "❓"},
                {"question": "Tell me something about the 'go-KI' project by GT-ARC.", "icon": "🤖"},
                {"question": "What documents do I need for a residence permit?", "icon": "📄"},
                {"question": "Find the nearest public service office to the TU Berlin Campus?", "icon": "🏢"},
                {"question": "How can I get an appointment at the Berlin Bürgeramt?", "icon": "📅"},
                {"question": "What are 'Large Language Models'?", "icon": "🧠"},
                {"question": "What are the most exciting tech trends for 2025?", "icon": "🚀"},
                {"question": "Explain Agile methodology.", "icon": "🔄"},
                {"question": "How to build a simple website?", "icon": "💻"}
            ]
        },
        {
            "id": "smartOffice",
            "header": "Smart Office",
            "icon": "🏢",
            "questions": [
                {"question": "It is too noisy in the kitchen. Could you check if the noise level in the co-working space is lower?", "icon": "🔊"},
                {"question": "Set my desk height to 120cm.", "icon": "⬆️"},
                {"question": "Open the shelf in which I can store a glass.", "icon": "🥃"},
                {"question": "Where can I find the espresso cups in the kitchen?", "icon": "☕"},

            ]
        },
    ],
    DE: [
        {
            "id": "taskAutomation",
            "header": "Task Automation",
            "icon": "🤖",
            "questions": [
                {"question": "Bitte ruf meine letzten E-Mails ab und fasse sie zusammen.", "icon": "📧"},
                {"question": "Fasse mir meine Termine für die nächsten 3 Tage zusammen.", "icon": "📅"},
                {"question": "Zeige mir die Telefonnummern aller Teilnehmer in meinem nächsten Meeting.", "icon": "📞"},
                {"question": "Erstelle eine Abwesenheitsmail, in der Tolga als Vertretung für die nächsten 2 Wochen erwähnt wird.", "icon": "✉️"},
                {"question": "Zeige mir die Telefonnummern aller Personen im GoKI Projekt die am Thema LLM arbeiten.", "icon": "👥"},
                {"question": "Plane ein Brainstorming mit Tobias.", "icon": "🧩"},
                {"question": "Finde einen Meetingtermin mit dem LLM-Team nächste Woche.", "icon": "📆"},
                {"question": "Zeige mir meinen Kalender für die nächste Woche.", "icon": "📅"}
            ]
        },
        {
            "id": "dataAnalysis",
            "header": "Data Analysis",
            "icon": "📊",
            "questions": [
                {"question": "Visualisiere den aktuellen Strommix von Deutschland auf eine sinnvolle Art und Weise.", "icon": "⚡"},
                {"question": "Finde die aktuelle Lautstärke in der Küche und dem Coworking Space. Dann visualisiere die Daten in einem Balkendiagramm für einen Vergleich.", "icon": "🔊"},
                {"question": "Erstelle ein Balkendiagramm der aktuellen Aktienpreise von Amazon, Apple, Microsoft und Nvidia.", "icon": "📊"},
                {"question": "Finde die aktuelle Temperatur, Lautstärke und Luftfeuchtigkeit in der Küche und visualisiere sie auf eine sinnvolle Art und Weise.", "icon": "🌤️"},
            ]
        },
        {
            "id": "informationUpskilling",
            "header": "Information & Upskilling",
            "icon": "📚",
            "questions": [
                {"question": "Womit kannst du mir helfen?", "icon": "❓"},
                {"question": "Erzähl mir etwas über das 'go-KI' Projekt von GT-ARC.", "icon": "🤖"},
                {"question": "Welche Dokumente brauche ich für die Aufenthaltserlaubnis?", "icon": "📄"},
                {"question": "Wie finde ich das nächstgelegene Bürgeramt für meine Adresse?", "icon": "🏢"},
                {"question": "Wie komme ich an einen Termin beim Berliner Bürgeramt?", "icon": "📅"},
                {"question": "Was sind 'Large Language Models'?", "icon": "🧠"},
                {"question": "Was sind die spannendsten Tech-Trends für 2025?", "icon": "🚀"},
                {"question": "Erkläre die Agile-Methodik.", "icon": "🔄"},
                {"question": "Wie erstelle ich eine einfache Website?", "icon": "💻"}
            ]
        },
        {
            "id": "smartOffice",
            "header": "Smart Office",
            "icon": "🏢",
            "questions": [
                {"question": "Es ist zu laut an meinem Platz. Kannst du einen ruhigeren Arbeitsbereich vorschlagen?", "icon": "🔊"},
                {"question": "Stelle die Höhe meines Schreibtisches auf 120cm ein.", "icon": "⬆️"},
                {"question": "Ich möchte mein Wasserglas verstauen. Ich habe es nicht benutzt. Öffne den Küchenschrank, in den ich es zurücklegen kann.", "icon": "🥃"},
                {"question": "Wo finde ich die Espressotassen in der Küche?", "icon": "☕"},
            ]
        },
    ],
}


// Placeholder messages for streaming in different languages
export const loadingMessages = {
    GB: {
        // System
        "preparing": "Initializing the OPACA AI Agents",
        // Multi-Agent System - Orchestration Level
        "Orchestrator": "Creating detailed orchestration plan",
        // Multi-Agent System - Agent Level
        "AgentPlanner": "Planning function calls for task",
        "WorkerAgent": "Executing function calls",
        "AgentEvaluator": "Evaluating task completion",
        // Multi-Agent System - Overall Level
        "OverallEvaluator": "Assessing overall request completion",
        "IterationAdvisor": "Analyzing results and planning next steps",
        // Multi-Agent System - Output Level
        "OutputGenerator": "Generating final response",
        // Tools
        "Tool Generator": "Calling the required tools",
        "Tool Evaluator": "Validating tool calls",
        // Simple
        "user": "",
        "assistant": "",
        "system": "",
    },
    DE: {
        // System
        "preparing": "OPACA KI-Agenten werden initialisiert",
        // Multi-Agent System - Orchestration Level
        "Orchestrator": "Erstelle Plan zur Aufgabenverteilung",
        // Multi-Agent System - Agent Level
        "AgentPlanner": "Plane Funktionsaufrufe für die Aufgabe",
        "WorkerAgent": "Führe Funktionsaufrufe aus",
        "AgentEvaluator": "Bewerte Aufgabenabschluss",
        // Multi-Agent System - Overall Level
        "OverallEvaluator": "Bewerte Gesamtanfrage",
        "IterationAdvisor": "Analysiere Ergebnisse und plane nächste Schritte",
        // Multi-Agent System - Output Level
        "OutputGenerator": "Generiere finale Antwort",
        // Tools
        "Tool Generator": "Aufrufen der benötigten Tools",
        "Tool Evaluator": "Überprüfen der Tool-Ergebnisse",
        // Simple
        "user": "",
        "assistant": "",
        "system": "",
    }
}


export const voiceGenLocalesWhisper = {
    GB: 'english',
    DE: 'german'
};

export const voiceGenLocalesWebSpeech = {
    GB: 'en-US',
    DE: 'de-DE'
};


class Localizer {

    constructor() {
        this._selectedLanguage = ref('GB');
        this._fallbackLanguage = ref('GB');
        this._verifySettings();
    }

    set language(newLang) {
        this._selectedLanguage.value = newLang;
        this._verifySettings();
    }

    get language() {
        return this._selectedLanguage.value;
    }

    set fallbackLanguage(newLang) {
        this._selectedLanguage.value = newLang;
        this._verifySettings();
    }

    get fallbackLanguage() {
        return this._fallbackLanguage.value;
    }

    _verifySettings() {
        if (!localizationData[this.language] || !localizationData[this.fallbackLanguage]) {
            throw Error(`Invalid languages configured in Localizer: ${this.language}, ${this.fallbackLanguage}`);
        }
    }

    /**
     * Allows text formatting as "%1, %2, ..." -> replace % placeholders with arguments.
     * Also does in-line markdown parsing on the text.
     * @param text
     * @param args
     * @returns {string|null}
     */
    formatText(text, ...args) {
        if (!text) return null;
        try {
            text = text.replace(/%(\d+)/g, (match, number) => {
                return typeof args[number - 1] !== 'undefined' ? args[number - 1] : match;
            });
            return marked.parseInline(text);
        } catch (error) {
            console.error('Formatting error:', error);
            return null;
        }
    }

    _getFrom(data, key, args, defaultValue, warningText, errorText) {
        const fallbackText = this.formatText(data?.[this.fallbackLanguage]?.[key], ...args);
        const text = this.formatText(data?.[this.language]?.[key], ...args);
        if (text) {
            return text;
        } else if (fallbackText) {
            console.warn('Localization Warning:', warningText);
            return fallbackText;
        } else {
            console.error('Localization Error:', errorText);
            return defaultValue;
        }
    }

    get(key, ...args) {
        return this._getFrom(localizationData, key, args,
            `[UNKNOWN: ${key}]`,
            `Key "${key}" does not exist for locale "${this.language}", consider adding it."`,
            `Key "${key}" could not be localized!`
        );
    }

    getLoadingMessage(key, ...args) {
        return this._getFrom(loadingMessages, key, args,
            `Loading`,
            `Loading message "${key}" does not exist for locale "${this.language}", consider adding it."`,
            `Loading message "${key}" could not be localized!`
        );
    }

    getSampleQuestions(categoryHeader) {
        const category = sidebarQuestions[this.language]
            ?.find(c => c.header === categoryHeader);

        // if category could not be found, return random sample questions
        if (!category) {
            return this.getRandomSampleQuestions();
        }

        // take first 3 questions and use their individual icons
        return category.questions.slice(0, 3).map(q => ({
            question: q.question,
            icon: q.icon || category.icon // Fallback to category icon if question has no icon
        }));
    }

    getRandomSampleQuestions(numQuestions = 3) {
        let questions = [];

        // assemble questions from all categories into a single array
        sidebarQuestions[this.language]
            .forEach(group => questions = questions
                .concat(group.questions.map(q => _mapCategoryIcons(q, group)))
            );

        shuffleArray(questions);
        return questions.slice(0, numQuestions);
    }

    getAvailableLocales() {
        return Array.from(Object.keys(localizationData))
            .map(locale => { return {key: locale, name: localizationData[locale].name}; });
    }

    getLanguageForTTS() {
        return AudioManager.isVoiceServerConnected
            ? voiceGenLocalesWhisper[this.language]
            : voiceGenLocalesWebSpeech[this.language];
    }
}

/**
 * @private
 * map the category's icon into the (copied) question object,
 * if not icon is defined for the question
 */
function _mapCategoryIcons(question, category) {
    return {
        question: question.question,
        icon: question.icon ?? category.icon
    };
}

const localizer = new Localizer();
export default localizer;
