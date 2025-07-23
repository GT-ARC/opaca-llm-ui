import {reactive, ref} from 'vue';
import {marked} from 'marked';
import {shuffleArray} from "./utils.js";
import AudioManager from "./AudioManager.js";
import conf from '../config.js';


export const localizationData = {
    GB: {
        pltConnected: "Connected",
        pltDisconnected: "Disconnected",
        connect: "Connect",
        disconnect: "Disconnect",
        name: "English",
        settings: "Settings",
        method: "Method",
        colorMode: "Color Scheme",
        language: 'Language',
        submit: 'Submit',
        cancel: 'Cancel',
        username: 'Username',
        password: 'Password',
        welcome: 'What can I do for you today? Try one of the sample queries or ask me anything you like!',
        unreachable: 'Please connect to a running OPACA platform.',
        unauthenticated: 'Authentication Required',
        authError: 'Invalid username or password.',
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
        tooltipSidebarInfo: "General Information",
        tooltipSidebarPrompts: "Prompt Library",
        tooltipSidebarAgents: "Agents and Actions",
        tooltipSidebarConfig: "Configuration",
        tooltipSidebarLogs: "Logging",
        tooltipChatbubbleDebug: "Debug",
        tooltipChatbubbleError: "Error",
        tooltipChatbubbleAudioPlay: "Play Audio",
        tooltipChatbubbleAudioStop: "Stop Audio",
        tooltipChatbubbleAudioLoad: "Audio is loading ...",
        tooltipChatbubbleCopy: "Copy",
        tooltipButtonSend: "Submit",
        tooltipButtonStop: "Cancel",
        tooltipButtonRecord: "Dictate",
        tooltipButtonReset: "Reset Chat",
        agentActionDescription: "Description",
        agentActionParameters: "Input Parameters",
        agentActionResult: "Result",
        buttonBackendConfigSave: "Save Config",
        buttonBackendConfigReset: "Reset to Defaults",
        tooltipSidebarFaq: "Help/FAQ",
        audioServerSettings: "Audio",
        rerollQuestions: "More ...",
        regenerate: "Suggest More",
    },

    DE: {
        pltConnected: "Verbunden",
        pltDisconnected: "Nicht verbunden",
        connect: "Verbinden",
        disconnect: "Trennen",
        name: "Deutsch",
        settings: "Einstellungen",
        language: 'Sprache',
        method: "Methode",
        colorMode: "Farbschema",
        submit: 'Senden',
        cancel: 'Abbrechen',
        username: 'Benutzer',
        password: 'Passwort',
        welcome: 'Was kann ich heute für Dich tun? Versuch einen der Beispiel-Queries, oder frag mich alles was Du willst!',
        unreachable: 'Bitte verbinden Sie sich mit einer laufenden OPACA Plattform.',
        unauthenticated: 'Authentifizierung erforderlich',
        authError: 'Benutzer oder Passwort falsch.',
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
        tooltipSidebarInfo: "Generelle Informationen",
        tooltipSidebarPrompts: "Prompt-Bibliothek",
        tooltipSidebarAgents: "Agenten und Aktionen",
        tooltipSidebarConfig: "Konfiguration",
        tooltipSidebarLogs: "Logging",
        tooltipChatbubbleDebug: "Debug",
        tooltipChatbubbleError: "Fehler",
        tooltipChatbubbleAudioPlay: "Audio abspielen",
        tooltipChatbubbleAudioStop: "Audio stoppen",
        tooltipChatbubbleAudioLoad: "Audio lädt ...",
        tooltipChatbubbleCopy: "Kopieren",
        tooltipButtonSend: "Absenden",
        tooltipButtonStop: "Abbrechen",
        tooltipButtonRecord: "Diktieren",
        tooltipButtonReset: "Chat zurücksetzen",
        agentActionDescription: "Beschreibung",
        agentActionParameters: "Parameter",
        agentActionResult: "Ergebnis",
        buttonBackendConfigSave: "Speichern",
        buttonBackendConfigReset: "Zurücksetzen",
        tooltipSidebarFaq: "Hilfe/FAQ",
        audioServerSettings: "Audio",
        rerollQuestions: "Mehr ...",
        regenerate: "Weitere Beispiele",
    },
};


export const sidebarQuestions = reactive({
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
})


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
        "user": " ",
        "assistant": "Working on it",
        "system": "Calling tool",
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
        "user": " ",
        "assistant": "Bearbeiten",
        "system": "Tool-Aufruf",
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

    constructor(selectedLanguage, fallbackLanguage) {
        this._fallbackLanguage = ref(fallbackLanguage)
        this._selectedLanguage = this.isAvailableLanguage(selectedLanguage)
            ? ref(selectedLanguage)
            : ref(fallbackLanguage);

        this._randomSampleQuestions = ref(null);
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

    set randomSampleQuestions(value) {
        this._randomSampleQuestions.value = value;
    }

    get randomSampleQuestions() {
        return this._randomSampleQuestions.value;
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

    getSampleQuestions(textinput, categoryHeader) {
        if (textinput) {
            this.randomSampleQuestions = this.getFilteredSampleQuestions(null, textinput, 3);
        } else if (! this.randomSampleQuestions) {
            this.reloadSampleQuestions(categoryHeader);
        }
        return this.randomSampleQuestions;
    }

    reloadSampleQuestions(categoryHeader = null, numQuestions = 3) {
        this.randomSampleQuestions = this.getFilteredSampleQuestions(categoryHeader, null, numQuestions);
    }

    getFilteredSampleQuestions(categoryHeader = null, textinput = null, numQuestions = 3) {
        // assemble questions from all or selected category into a single array
        let questions = sidebarQuestions[this.language]
            .filter(category => categoryHeader === null || category.header === categoryHeader)
            .flatMap(category => category.questions.map(question => _mapCategoryIcons(question, category)))
            .filter(question => textinput === null || matches(question.question, textinput));

        // if no text input was given -> shuffle and get first k questions
        if (!textinput) {
            shuffleArray(questions);
        }
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

    isAvailableLanguage(langName) {
        if (!langName) return false;
        return this.getAvailableLocales().find(locale => locale.key === langName) !== undefined;
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

function matches(question, textinput) {
    return textinput.toLowerCase().split(/\s+/)
        .every(word => question.toLowerCase().includes(word));
}

// hard-code the most complete language as fallback language
const fallbackLanguage = 'GB';

const localizer = new Localizer(conf.DefaultLanguage, fallbackLanguage);
export default localizer;
