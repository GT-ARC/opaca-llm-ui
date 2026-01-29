import {reactive, ref} from 'vue';
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
        opacaUnreachable: 'Could not connect to OPACA platform.',
        backendUnreachable: 'SAGE Backend is unreachable. Please check if the backend is running and reload the page.',
        unauthenticated: 'Authentication Required',
        authError: 'Invalid username or password.',
        none: 'None',
        speechRecognition: 'Speak' ,
        readLastMessage: 'Read Last',
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
        tooltipSidebarChats: "Chats",
        tooltipSidebarFiles: "Uploaded Files",
        tooltipSidebarPrompts: "Prompt Library",
        tooltipSidebarAgents: "Agents and Actions",
        tooltipSidebarConfig: "Configuration",
        tooltipSidebarLogs: "Logging",
        tooltipSidebarMcp: "MCP Servers",
        tooltipChatbubbleDebug: "Debug",
        tooltipChatbubbleTools: "Tool Calls",
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
        buttonConfigSave: "Save Config",
        buttonConfigReset: "Reset to Defaults",
        tooltipSidebarFaq: "Help/FAQ",
        audioServerSettings: "Audio",
        rerollQuestions: "More…",
        regenerate: "Suggest More",
        platformInfoMissing: "It's a little quiet here...",
        platformInfoLoading: "Querying functionality, please wait...",
        platformInfoFailed: "There was an error when querying the functionality: %1",
        cookiesText: "This website uses cookies to associate your chat session (message history and settings) with you. This cookie is kept for 30 days after the last interaction, or until manually deleted. The session data is stored in the backend and the messages are sent to the configured LLM. The session data will be deleted from the backend when the cookie expires, or by clicking the Reset button. The cookies and session data are used for the sole purpose of the chat interaction. Without, no continued conversation with the LLM is possible. By using this website, you consent to the above policy.",
        cookiesAccept: "Accept",
        tooltipDeleteUploadedFile: "Remove File",
        tooltipSuspendUploadedFile: "Include File in conversations?",
        tooltipViewUploadedFile: "View File",
        tooltipUploadFile: "Upload File",
        tooltipChatbubbleFiles: "Attached Files",
        uploadingFileText: "Uploading…",
        fileOverflow: "+%1 more…",
        sidebarAgentsLoading: "Loading available agents...",
        sidebarAgentsMissing: "No agents available.",
        sidebarConfigLoading: "Loading config for %1...",
        sidebarConfigMissing: "No config available for %1.",
        sidebarMcpLoading: "Loading MCP servers...",
        sidebarMcpMissing: "No MCP servers available.",
        addMcp: "Add MCP Server",
        configSaveSuccess: "Config saved",
        configSaveInvalid: "Invalid data: %1",
        configSaveError: "An error occurred",
        configReset: "Configuration was reset",
        sidebarFaqMissing: "Unable to load FAQ.",
        buttonNewChat: "New Chat",
        tooltipEditChatName: "Edit Name",
        tooltipDeleteChat: "Delete Chat",
        confirmDeleteChat: "Are you sure that you want to delete the Chat?",
        buttonSearchChats: "Search Chats",
        buttonDeleteAllChats: "Delete All Chats",
        confirmDeleteAllChats: "Are you sure you want to delete all chats?",
        dropFiles: "Drop files here to upload",
        sidebarFilesEmpty: "No files uploaded",
        confirmDeleteFile: "Are you sure that you want to remove and forget the File '%1'?",
        searchAgentsPlaceholder: "Search…",
        containerLoginMessage: "The following action requires additional credentials: ",
        useWhisperTts: "Whisper TTS",
        useWhisperStt: "Whisper STT",
        whisperVoiceSelectPlaceholder: "Whisper Voice",
        tooltipSidebarExtensions: "Extensions",
        sidebarExtensionsLoading: "Loading available extensions...",
        sidebarExtensionsMissing: "No extensions available.",
        tooltipExpandExtension: "Expand",
        apiKeyMissing: "Please provide an API key for this model: ",
        apiKeyInvalid: "The entered API key for following model is invalid! Try again: ",
        tooltipAppendNotification: "Append to current Chat",
        tooltipDismissNotification: "Dismiss",
        autoAppendNotification: "Also append future notifications",
        noNotifsAvailable: "No notifications",
        autogenQuestionsTitle: "Auto-Generated Prompts",
        confirmSampleQuestionReset: "Are you sure you want to reset the sample question to the default ones?",
        checkboxDeleteSampleQuestion: "Delete?",
        specifyPlaceholders: "Values for Placeholders",
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
        opacaUnreachable: 'Verbindung mit OPACA Plattform fehlgeschlagen.',
        backendUnreachable: 'SAGE Backend nicht erreichbar. Bitte überprüfen Sie ob das Backend läuft und laden Sie die Seite neu.',
        unauthenticated: 'Authentifizierung erforderlich',
        authError: 'Benutzer oder Passwort falsch.',
        none: 'Keine',
        speechRecognition: 'Sprechen' ,
        readLastMessage: 'Vorlesen',
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
        tooltipSidebarChats: "Chats",
        tooltipSidebarFiles: "Hochgeladene Dateien",
        tooltipSidebarPrompts: "Prompt-Bibliothek",
        tooltipSidebarAgents: "Agenten und Aktionen",
        tooltipSidebarConfig: "Konfiguration",
        tooltipSidebarLogs: "Logging",
        tooltipSidebarMcp: "MCP Servers",
        tooltipChatbubbleDebug: "Debug",
        tooltipChatbubbleTools: "Tool Calls",
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
        buttonConfigSave: "Speichern",
        buttonConfigReset: "Zurücksetzen",
        tooltipSidebarFaq: "Hilfe/FAQ",
        audioServerSettings: "Audio",
        rerollQuestions: "Mehr…",
        regenerate: "Weitere Beispiele",
        platformInfoMissing: "Hier gibt es gerade nichts...",
        platformInfoLoading: "Frage Funktionalitäten an, bitte warten...",
        platformInfoFailed: "Es gab einen Fehler bei der Anfrage: %1",
        cookiesText: "Diese Website verwendet Cookies, um Ihre Chat-Sitzung (Nachrichtenverlauf und Einstellungen) mit Ihnen zu verknüpfen. Die Cookies werden 30 Tage nach der letzten Interaktion oder bis zur manuellen Löschung gespeichert. Die Sitzungsdaten werden im Backend gespeichert und die Nachrichten werden an das konfigurierte LLM gesendet. Die Sitzungsdaten werden aus dem Backend gelöscht, wenn das Cookie abläuft oder wenn Sie auf die Reset-Schaltfläche klicken. Die Cookies und Sitzungsdaten werden ausschließlich für die Chat-Interaktion verwendet. Ohne sie ist keine fortgesetzte Konversation mit dem LLM möglich. Durch die Nutzung dieser Website stimmen Sie den oben genannten Richtlinien zu.",
        cookiesAccept: "Annehmen",
        tooltipDeleteUploadedFile: "Datei entfernen",
        tooltipSuspendUploadedFile: "Datei in Konversationen einbeziehen?",
        tooltipViewUploadedFile: "Datei anzeigen",
        tooltipUploadFile: "Datei hochladen",
        tooltipChatbubbleFiles: "Angehängte Dateien",
        uploadingFileText: "Lade hoch…",
        fileOverflow: "+%1 weitere…",
        sidebarAgentsLoading: "Lade verfügbare Agenten...",
        sidebarAgentsMissing: "Keine Agenten verfügbar.",
        sidebarConfigLoading: "Lade Konfiguration für %1...",
        sidebarConfigMissing: "Keine Konfiguration für %1 verfügbar.",
        sidebarMcpLoading: "Lade verfügbare MCP-Server...",
        sidebarMcpMissing: "Keine MCP-Server verfügbar.",
        addMcp: "MCP Server hinzufügen",
        configSaveSuccess: "Konfiguration gespeichert",
        configSaveInvalid: "Fehlerhafte Daten: %1",
        configSaveError: "Es ist ein Fehler aufgretreten",
        configReset: "Konfiguration wurde zurückgesetzt",
        sidebarFaqMissing: "FAQ konnte nicht geladen werden.",
        buttonNewChat: "Neuer Chat",
        tooltipEditChatName: "Name bearbeiten",
        tooltipDeleteChat: "Chat löschen",
        confirmDeleteChat: "Sind Sie sicher, dass Sie den Chat löschen wollen?",
        buttonSearchChats: "Chats Durchsuchen",
        buttonDeleteAllChats: "Alle Chats löschen",
        confirmDeleteAllChats: "Sind Sie sicher, dass Sie alle Chats löschen möchten?",
        dropFiles: "Dateien hier ablegen um sie hochzuladen",
        sidebarFilesEmpty: "Keine Dateien hochgeladen",
        confirmDeleteFile: "Sind Sie sicher, dass Sie die Datei '%1' entfernen und vergessen wollen?",
        searchAgentsPlaceholder: "Suchen…",
        containerLoginMessage: "Die auszuführende Aktion benötigt weitere Zugangsdaten: ",
        useWhisperTts: "Whisper TTS",
        useWhisperStt: "Whisper STT",
        whisperVoiceSelectPlaceholder: "Whisper-Stimme",
        tooltipSidebarExtensions: "Erweiterungen",
        sidebarExtensionsLoading: "Lade verfügbare Erweiterungen...",
        sidebarExtensionsMissing: "Keine Erweiterungen verfügbar.",
        tooltipExpandExtension: "Vergrößern",
        apiKeyMissing: "Bitte geben Sie für das folgende Model einen API-Key ein: ",
        apiKeyInvalid: "Der eingegebene API-Key für das folgende Model ist ungültig! Versuchen Sie es erneut: ",
        tooltipAppendNotification: "An den geöffneten Chat heften",
        tooltipDismissNotification: "Entfernen",
        autoAppendNotification: "Auch künftige Benachrichtigungen anhängen",
        noNotifsAvailable: "Keine Benachrichtigungen",
        autogenQuestionsTitle: "Auto-Generierte Prompts",
        confirmSampleQuestionReset: "Wirklich auf die Standardeinstellungen zurücksetzen?",
        checkboxDeleteSampleQuestion: "Löschen?",
        specifyPlaceholders: "Werte für Platzhalter",
    },
};


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
        this._samplePrompts = ref(null);
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

    set samplePrompts(value) {
        this._samplePrompts.value = value;
    }

    get samplePrompts() {
        return this._samplePrompts.value;
    }

    _verifySettings() {
        if (!localizationData[this.language] || !localizationData[this.fallbackLanguage]) {
            throw Error(`Invalid languages configured in Localizer: ${this.language}, ${this.fallbackLanguage}`);
        }
    }

    /**
     * Allows text formatting as "%1, %2, ..." -> replace % placeholders with arguments.
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
            return text;
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

    getSampleQuestions(textInput, categoryHeader) {
        if (textInput) {
            this.randomSampleQuestions = this.getFilteredSampleQuestions(null, textInput, 3);
        } else if (! this.randomSampleQuestions) {
            this.reloadSampleQuestions(categoryHeader);
        }
        return this.randomSampleQuestions;
    }

    reloadSampleQuestions(categoryHeader = null, numQuestions = 3) {
        this.randomSampleQuestions = this.getFilteredSampleQuestions(categoryHeader, null, numQuestions);
    }

    getFilteredSampleQuestions(categoryHeader = null, textInput = null, numQuestions = 3) {
        if (!this.samplePrompts) {
            return [];
        }
        // assemble questions from all or selected category into a single array
        let filteredQuestions = this.samplePrompts
            .filter(category => categoryHeader === null || categoryHeader === 'none' || category.header === categoryHeader)
            .flatMap(category => category.questions.map(question => _mapCategoryIcons(question, category)))
            .filter(question => textInput === null || matches(question.question, textInput));

        // if no text input was given -> shuffle and get first k questions
        if (!textInput) {
            shuffleArray(filteredQuestions);
        }
        return filteredQuestions.slice(0, numQuestions);
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

    getLanguageForDate() {
        return voiceGenLocalesWebSpeech[this.language];
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

function matches(question, textInput) {
    return textInput.toLowerCase().split(/\s+/)
        .every(word => question.toLowerCase().includes(word));
}

// hard-code the most complete language as fallback language
const fallbackLanguage = 'GB';

const localizer = new Localizer(conf.DefaultLanguage, fallbackLanguage);
export default localizer;
