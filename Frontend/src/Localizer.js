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
        tooltipChatbubbleSave: "Save prompt to user library",
        personalQuestionsEmpty: "No personal prompts saved",
        tooltipDeleteQuestion: "Delete Prompt",
        editQuestion: "Edit Prompt",
        addPersonalQuestion: "New Prompt",
        containerLoginMessage: "The following action requires additional credentials: ",
        useWhisperTts: "Whisper TTS",
        useWhisperStt: "Whisper STT",
        whisperVoiceSelectPlaceholder: "Whisper Voice",
        bookmarkHeader: "Bookmarked Prompts",
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
        tooltipChatbubbleSave: "Prompt in Nutzerbibliothek speichern",
        personalQuestionsEmpty: "Keine persönlichen Prompts gespeichert",
        tooltipDeleteQuestion: "Prompt löschen",
        editQuestion: "Prompt bearbeiten",
        addPersonalQuestion: "Neuer Prompt",
        containerLoginMessage: "Die auszuführende Aktion benötigt weitere Zugangsdaten: ",
        useWhisperTts: "Whisper TTS",
        useWhisperStt: "Whisper STT",
        whisperVoiceSelectPlaceholder: "Whisper-Stimme",
        bookmarkHeader: "Favoriten",
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
                {"question": "Fetch my next meeting and prepare me for it by giving me some background information on the topic and get the available phone numbers of the participants!", "icon": "📑"},
                {"question": "Schedule a brainstorming session with Robert.", "icon": "🧠"},
                {"question": "Get my gitlab user id and give me a tabular overview of all open GitLab issues assigned me.", "icon": "📜"},
            ]
        },
        {
            "id": "informationUpskilling",
            "header": "Information & Upskilling",
            "icon": "📚",
            "questions": [
                {"question": "Tell me something about the 'go-KI' project by GT-ARC.", "icon": "🤖"},
                {"question": "What can you tell me about ZEKI?", "icon": "❓"},
                {"question": "What are the most exciting tech trends for 2026 in the domain \"Consumer Electronics\"?", "icon": "🚀"},
                {"question": "Please suggest a curriculum for getting started with computer vision.", "icon": "💻"},
                {"question": "I want to start my master at TU Berlin and focus on AI applications. What program and courses are available?", "icon": "🎓"},
            ]
        },
        {
            "id": "dataAnalysis",
            "header": "Data Analysis",
            "icon": "📊",
            "questions": [
                {"question": "Retrieve the current co2 levels in the kitchen and coworking space. Then, plot them in a bar chart for comparison.", "icon": "☁️"},
                {"question": "Create a bar plot comparing the current stock prices of Siemens, Volkswagen, Deutsche Bank and SAP.", "icon": "📊"},
                {"question": "Get the weather for Berlin for the next three days, show the details and plot a simple temperature graph.", "icon": "🌤️"},
                {"question": "Get my gitlab user id and then plot my user statistics for the last 30 days as a bar plot.", "icon": "📈️"},
            ]
        },
        {
            "id": "smartOffice",
            "header": "Smart Office",
            "icon": "🏢",
            "questions": [
                {"question": "What is the temperature and CO2 level in the conference room?", "icon": "🌡️"},
                {"question": "Where can I find the espresso cups in the kitchen?", "icon": "☕"},
                {"question": "Open the shelf where I can store a glass.", "icon": "🥃"},
                {"question": "Set the light in the Experience Hub to half brightness.", "icon": "💡"},
                {"question": "Guide me to the conference room, please.", "icon": "🧭"},
            ]
        },
        /*
        {
            "id": "mobility",
            "header": "Mobility",
            "icon": "🚗",
            "questions": [
                {"question": "Where is my Tiguan Car?", "icon": "📍"},
                {"question": "Find a route from Ernst-Reuter-Platz, Berlin to Europaplatz, Berlin.", "icon": "🧭"},
                {"question": "Find a parking spot near the current location of my Tiguan car.", "icon": "🅿️"},
                {"question": "What's the current air quality near Ernst-Reuter-Platz, Berlin?", "icon": "🌫️"},
            ]
        },
        */
    ],
    DE: [
        {
            "id": "taskAutomation",
            "header": "Task Automation",
            "icon": "🤖",
            "questions": [
                {"question": "Bitte ruf meine letzten E-Mails ab und fasse sie zusammen.", "icon": "📧"},
                {"question": "Fasse mir meine Termine für die nächsten 3 Tage zusammen.", "icon": "📅"},
                {"question": "Such nach meinem nächsten meeting und bereite mich auf dieses vor, indem du mir Hintergrundinformationen zu dem besprochenen Thema lieferst und die verfügbaren Telefonnummern der Teilnehmer holst.", "icon": "📑"},
                {"question": "Plane ein Brainstorming-Meeting mit Robert.", "icon": "🧠"},
                {"question": "Finde meine GitLab Benutzer id und gib mir dann eine tabellarische Übersicht aller meiner offenen GitLab Issues wieder.", "icon": "📜"},
            ]
        },
        {
            "id": "informationUpskilling",
            "header": "Information & Upskilling",
            "icon": "📚",
            "questions": [
                {"question": "Erzähl mir etwas über das 'go-KI' Projekt von GT-ARC.", "icon": "🤖"},
                {"question": "Was kannst du mir über das ZEKI erzählen?", "icon": "❓"},
                {"question": "Was sind die spannendsten Tech-Trends für 2026 im Bereich \"Consumer Electronics\"?", "icon": "🚀"},
                {"question": "Schlag mir einen Lernplan vor, um mich in Computer Vision einzuarbeiten.", "icon": "💻"},
                {"question": "Ich möchte meinen Master an der TU Berlin anfangen mit dem Schwerpunkt KI Anwendungen. Welche Studiengänge und Kurse sind dazu verfügbar?", "icon": "🎓"},
            ]
        },
        {
            "id": "dataAnalysis",
            "header": "Data Analysis",
            "icon": "📊",
            "questions": [
                {"question": "Finde den aktuellen Co2 Wert in der Küche und dem Coworking Space. Dann visualisiere die Daten in einem Balkendiagramm für einen Vergleich.", "icon": "☁️"},
                {"question": "Erstelle ein Balkendiagramm der aktuellen Aktienpreise von Siemens, Volkswagen, Deutsche Bank und SAP.", "icon": "📊"},
                {"question": "Ruf das Wetter für Berlin in den nächsten drei Tagen ab, zeig die Details und erstelle einen einfachen Graphen der Temperatur.", "icon": "🌤️"},
                {"question": "Finde meine GitLab Benutzer id und stelle dann meine Benutzeraktivitäten für die letzten 30 Tage in einem Balkendiagramm dar.", "icon": "📈️"},
            ]
        },
        {
            "id": "smartOffice",
            "header": "Smart Office",
            "icon": "🏢",
            "questions": [
                {"question": "Wie ist die Temperatur und das CO2-Level im Conference Space?", "icon": "🌡️"},
                {"question": "Wo finde ich die Espressotassen in der Küche?", "icon": "☕"},
                {"question": "Öffne den Küchenschrank, in den die Gläser gehören.", "icon": "🥃"},
                {"question": "Stell die Beleuchtung im Experience Hub auf halbe Helligkeit ein.", "icon": "💡"},
                {"question": "Bitte zeige mir den Weg zum Konferenzraum.", "icon": "🧭"},
            ]
        },
        /*
        {
            "id": "mobility",
            "header": "Mobilität",
            "icon": "🚗",
            "questions": [
                {"question": "Wo ist mein Tiguan Auto?", "icon": "📍"},
                {"question": "Finde eine Route vom Ernst-Reuter-Platz, Berlin zum Europaplatz, Berlin.", "icon": "🧭"},
                {"question": "Finde einen Parkplatz in der Nähe der aktuellen Position meines Tiguan Autos.", "icon": "🅿️"},
                {"question": "Wie ist die aktuelle Luftqualität am Ernst-Reuter-Platz, Berlin?", "icon": "🌫️"},
            ]
        },
        */
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
            .filter(category => categoryHeader === null || categoryHeader === 'none' || category.header === categoryHeader)
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

function matches(question, textinput) {
    return textinput.toLowerCase().split(/\s+/)
        .every(word => question.toLowerCase().includes(word));
}

// hard-code the most complete language as fallback language
const fallbackLanguage = 'GB';

const localizer = new Localizer(conf.DefaultLanguage, fallbackLanguage);
export default localizer;
