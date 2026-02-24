import {reactive, ref} from 'vue';
import {shuffleArray} from "./utils.js";
import AudioManager from "./AudioManager.js";
import conf from '../config.js';


export const localizationData = {
    GB: {
        name: "English",
        general_connected: "Connected",
        general_disconnected: "Disconnected",
        general_connect: "Connect",
        general_disconnect: "Disconnect",
        general_okay: 'Okay',
        general_cancel: 'Cancel',
        general_username: 'Username',
        general_password: 'Password',
        settings: "Settings",
        settings_language: 'Language',
        settings_method: "Method",
        settings_colorMode: "Color Scheme",
        settings_audio: "Audio",
        settings_audio_connected: 'Connected',
        settings_audio_disconnected: 'Disconnected',
        settings_audio_retry: 'Retry Connection',
        settings_audio_whisperTts: "Whisper TTS",
        settings_audio_whisperStt: "Whisper STT",
        opacaUnreachable: 'Could not connect to OPACA platform.',
        backendUnreachable: 'SAGE Backend is unreachable. Please check if the backend is running and reload the page.',
        unauthenticated: 'Authentication Required',
        authError: 'Invalid username or password.',
        opacaLocation: 'OPACA URL',
        tooltipSidebarConfig: "Configuration",
        chatarea_welcome: 'What can I do for you today? Try one of the sample queries or ask me anything you like!',
        chatarea_input: 'Send a message ...',
        chatarea_rerollSamples: "More…",
        chatarea_submit: "Submit",
        chatarea_abort: "Cancel",
        chatarea_speak: "Dictate",
        chatbubble_preparing: "Initializing the OPACA AI Agents",
        chatbubble_debug: "Debug",
        chatbubble_tools: "Tool Calls",
        chatbubble_error: "Error",
        chatbubble_audioPlay: "Play Audio",
        chatbubble_audioStop: "Stop Audio",
        chatbubble_audioLoad: "Audio is loading ...",
        chatbubble_copy: "Copy",
        chatbubble_files: "Attached Files",
        buttonConfigSave: "Save Config",
        buttonConfigReset: "Reset to Defaults",
        cookies_text: "This website uses cookies to associate your chat session (message history and settings) with you. This cookie is kept for 30 days after the last interaction, or until manually deleted. The session data is stored in the backend and the messages are sent to the configured LLM. The session data will be deleted from the backend when the cookie expires, or by clicking the Reset button. The cookies and session data are used for the sole purpose of the chat interaction. Without, no continued conversation with the LLM is possible. By using this website, you consent to the above policy.",
        cookies_accept: "Accept",
        sidebar_files: "Uploaded Files",
        sidebar_files_missing: "No files uploaded",
        sidebar_files_upload: "Upload File",
        sidebar_files_uploading: "Uploading…",
        sidebar_files_include: "Include File in conversations?",
        sidebar_files_view: "View File",
        sidebar_files_delete: "Remove File",
        sidebar_files_delete_confirm: "Are you sure that you want to remove and forget the File '%1'?",
        sidebar_files_overflow: "+%1 more…",
        sidebar_files_droparea: "Drop files here to upload",
        sidebarConfigLoading: "Loading config for %1...",
        sidebarConfigMissing: "No config available for %1.",
        sidebar_mcp: "MCP Servers",
        sidebar_mcp_loading: "Loading MCP servers...",
        sidebar_mcp_missing: "No MCP servers available.",
        sidebar_mcp_add: "Add MCP Server",
        configSaveSuccess: "Config saved",
        configSaveInvalid: "Invalid data: %1",
        configSaveError: "An error occurred",
        configReset: "Configuration was reset",
        sidebar_info: "General Information",
        sidebar_info_missing: "It's a little quiet here...",
        sidebar_info_loading: "Querying functionality, please wait...",
        sidebar_info_failed: "There was an error when querying the functionality: %1",
        sidebar_logs: "Logging",
        sidebar_faq: "Help/FAQ",
        sidebar_faq_missing: "Unable to load FAQ.",
        sidebar_chats: "Chats",
        sidebar_chats_new: "New Chat",
        sidebar_chats_edit: "Rename",
        sidebar_chats_delete: "Delete Chat",
        sidebar_chats_delete_confirm: "Are you sure that you want to delete the Chat?",
        sidebar_chats_search: "Search Chats",
        sidebar_chats_deleteAll: "Delete All Chats",
        sidebar_chats_deleteAll_confirm: "Are you sure you want to delete all chats?",
        containerLoginMessage: "The following action requires additional credentials: ",
        sidebar_extensions: "Extensions",
        sidebar_extensions_loading: "Loading available extensions...",
        sidebar_extensions_missing: "No extensions available.",
        sidebar_extensions_refresh: "Refresh",
        sidebar_extensions_expand: "Expand",
        apiKey_missing: "Please provide an API key for this model: ",
        apiKey_invalid: "The entered API key for following model is invalid! Try again: ",
        notification_dismiss: "Dismiss",
        notification_append: "Append to current Chat",
        notification_autoAppend: "Also append future notifications",
        notification_missing: "No notifications",
        sidebar_showStandardTools: "Show Standard Tools",
        sidebar_showAdvancedTools: "Show Advanced Tools",
        sidebar_agents: "Agents and Actions",
        sidebar_agents_loading: "Loading available agents...",
        sidebar_agents_missing: "No agents available.",
        sidebar_agents_search: "Search…",
        sidebar_agents_description: "Description",
        sidebar_agents_parameters: "Input Parameters",
        sidebar_agents_result: "Result",
        sidebar_agents_invoke: "Execute",
        sidebar_questions: "Prompt Library",
        sidebar_questions_addPrompt: "Add New Prompt",
        sidebar_questions_addCategory: "Add New Category",
        sidebar_questions_reset: "Reset Prompts",
        sidebar_questions_reset_confirm: "Are you sure you want to reset the sample question to the default ones?",
        sidebar_questions_editPrompt: "Edit Prompt",
        sidebar_questions_editCategory: "Edit Category",
        sidebar_questions_toggleEditMode: "Edit Prompt Library",
        sidebar_questions_deletePrompt: "Delete Prompt",
        sidebar_questions_deletePrompt_confirm: "Delete prompt \"%1\"?",
        sidebar_questions_deleteCategory: "Delete Category",
        sidebar_questions_deleteCategory_confirm: "Delete category \"%1\"?",
        sidebar_questions_generated: "Auto-Generated Prompts",
        sidebar_questions_regenerate: "Suggest More",
        sidebar_questions_placeholders: "Values for Placeholders",
    },

    DE: {
        name: "Deutsch",
        general_connected: "Verbunden",
        general_disconnected: "Nicht verbunden",
        general_connect: "Verbinden",
        general_disconnect: "Trennen",
        general_okay: 'Okay',
        general_cancel: 'Abbrechen',
        general_username: 'Benutzer',
        general_password: 'Passwort',
        settings: "Einstellungen",
        settings_language: 'Sprache',
        settings_method: "Methode",
        settings_colorMode: "Farbschema",
        settings_audio: "Audio",
        settings_audio_connected: 'Verbunden',
        settings_audio_disconnected: 'Nicht verbunden',
        settings_audio_retry: 'Erneut verbinden',
        settings_audio_whisperTts: "Whisper TTS",
        settings_audio_whisperStt: "Whisper STT",
        opacaUnreachable: 'Verbindung mit OPACA Plattform fehlgeschlagen.',
        backendUnreachable: 'SAGE Backend nicht erreichbar. Bitte überprüfen Sie ob das Backend läuft und laden Sie die Seite neu.',
        unauthenticated: 'Authentifizierung erforderlich',
        authError: 'Benutzer oder Passwort falsch.',
        opacaLocation: 'OPACA URL',
        tooltipSidebarConfig: "Konfiguration",
        chatarea_welcome: 'Was kann ich heute für Dich tun? Versuch einen der Beispiel-Queries, oder frag mich alles was Du willst!',
        chatarea_input: 'Nachricht senden ...',
        chatarea_rerollSamples: "Mehr…",
        chatarea_submit: "Absenden",
        chatarea_abort: "Abbrechen",
        chatarea_speak: "Diktieren",
        chatbubble_preparing: "OPACA KI-Agenten werden initialisiert",
        chatbubble_debug: "Debug",
        chatbubble_tools: "Tool Calls",
        chatbubble_error: "Fehler",
        chatbubble_audioPlay: "Audio abspielen",
        chatbubble_audioStop: "Audio stoppen",
        chatbubble_audioLoad: "Audio lädt ...",
        chatbubble_copy: "Kopieren",
        chatbubble_files: "Angehängte Dateien",
        buttonConfigSave: "Speichern",
        buttonConfigReset: "Zurücksetzen",
        cookies_text: "Diese Website verwendet Cookies, um Ihre Chat-Sitzung (Nachrichtenverlauf und Einstellungen) mit Ihnen zu verknüpfen. Die Cookies werden 30 Tage nach der letzten Interaktion oder bis zur manuellen Löschung gespeichert. Die Sitzungsdaten werden im Backend gespeichert und die Nachrichten werden an das konfigurierte LLM gesendet. Die Sitzungsdaten werden aus dem Backend gelöscht, wenn das Cookie abläuft oder wenn Sie auf die Reset-Schaltfläche klicken. Die Cookies und Sitzungsdaten werden ausschließlich für die Chat-Interaktion verwendet. Ohne sie ist keine fortgesetzte Konversation mit dem LLM möglich. Durch die Nutzung dieser Website stimmen Sie den oben genannten Richtlinien zu.",
        cookies_accept: "Annehmen",
        sidebar_files: "Hochgeladene Dateien",
        sidebar_files_missing: "Keine Dateien hochgeladen",
        sidebar_files_upload: "Datei hochladen",
        sidebar_files_uploading: "Lade hoch…",
        sidebar_files_include: "Datei in Konversationen einbeziehen?",
        sidebar_files_view: "Datei anzeigen",
        sidebar_files_delete: "Datei entfernen",
        sidebar_files_delete_confirm: "Sind Sie sicher, dass Sie die Datei '%1' entfernen und vergessen wollen?",
        sidebar_files_overflow: "+%1 weitere…",
        sidebar_files_droparea: "Dateien hier ablegen um sie hochzuladen",
        sidebarConfigLoading: "Lade Konfiguration für %1...",
        sidebarConfigMissing: "Keine Konfiguration für %1 verfügbar.",
        sidebar_mcp: "MCP Servers",
        sidebar_mcp_loading: "Lade verfügbare MCP-Server...",
        sidebar_mcp_missing: "Keine MCP-Server verfügbar.",
        sidebar_mcp_add: "MCP Server hinzufügen",
        configSaveSuccess: "Konfiguration gespeichert",
        configSaveInvalid: "Fehlerhafte Daten: %1",
        configSaveError: "Es ist ein Fehler aufgretreten",
        configReset: "Konfiguration wurde zurückgesetzt",
        sidebar_info: "Generelle Informationen",
        sidebar_info_missing: "Hier gibt es gerade nichts...",
        sidebar_info_loading: "Frage Funktionalitäten an, bitte warten...",
        sidebar_info_failed: "Es gab einen Fehler bei der Anfrage: %1",
        sidebar_logs: "Logging",
        sidebar_faq: "Hilfe/FAQ",
        sidebar_faq_missing: "FAQ konnte nicht geladen werden.",
        sidebar_chats: "Chats",
        sidebar_chats_new: "Neuer Chat",
        sidebar_chats_edit: "Umbenennen",
        sidebar_chats_delete: "Chat löschen",
        sidebar_chats_delete_confirm: "Sind Sie sicher, dass Sie den Chat löschen wollen?",
        sidebar_chats_search: "Chats Durchsuchen",
        sidebar_chats_deleteAll: "Alle Chats löschen",
        sidebar_chats_deleteAll_confirm: "Sind Sie sicher, dass Sie alle Chats löschen möchten?",
        containerLoginMessage: "Die auszuführende Aktion benötigt weitere Zugangsdaten: ",
        sidebar_extensions: "Erweiterungen",
        sidebar_extensions_loading: "Lade verfügbare Erweiterungen...",
        sidebar_extensions_missing: "Keine Erweiterungen verfügbar.",
        sidebar_extensions_refresh: "Neu laden",
        sidebar_extensions_expand: "Vergrößern",
        apiKey_missing: "Bitte geben Sie für das folgende Model einen API-Key ein: ",
        apiKey_invalid: "Der eingegebene API-Key für das folgende Model ist ungültig! Versuchen Sie es erneut: ",
        notification_dismiss: "Entfernen",
        notification_append: "An den geöffneten Chat heften",
        notification_autoAppend: "Auch künftige Benachrichtigungen anhängen",
        notification_missing: "Keine Benachrichtigungen",
        sidebar_showStandardTools: "Standard-Werkzeuge anzeigen",
        sidebar_showAdvancedTools: "Erweiterte Werkzeuge anzeigen",
        sidebar_agents: "Agenten und Aktionen",
        sidebar_agents_loading: "Lade verfügbare Agenten...",
        sidebar_agents_missing: "Keine Agenten verfügbar.",
        sidebar_agents_search: "Suchen…",
        sidebar_agents_description: "Beschreibung",
        sidebar_agents_parameters: "Parameter",
        sidebar_agents_result: "Ergebnis",
        sidebar_agents_invoke: "Ausführen",
        sidebar_questions: "Prompt-Bibliothek",
        sidebar_questions_addPrompt: "Neuer Prompt",
        sidebar_questions_addCategory: "Neue Kategorie",
        sidebar_questions_reset: "Prompts zurücksetzen",
        sidebar_questions_reset_confirm: "Wirklich auf die Standardeinstellungen zurücksetzen?",
        sidebar_questions_editPrompt: "Prompt bearbeiten",
        sidebar_questions_editCategory: "Kategorie bearbeiten",
        sidebar_questions_toggleEditMode: "Prompt-Bibliothek bearbeiten",
        sidebar_questions_deletePrompt: "Prompt löschen",
        sidebar_questions_deletePrompt_confirm: "Prompt \"%1\" löschen?",
        sidebar_questions_deleteCategory: "Kategorie löschen",
        sidebar_questions_deleteCategory_confirm: "Kategorie \"%1\" löschen?",
        sidebar_questions_generated: "Auto-Generierte Prompts",
        sidebar_questions_regenerate: "Weitere Beispiele",
        sidebar_questions_placeholders: "Werte für Platzhalter",
    },
};


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
        if (!this.getPrompts()) {
            return [];
        }
        // assemble questions from all or selected category into a single array
        let filteredQuestions = this.getPrompts()
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

    /**
     * @returns {Array}
     */
    getPrompts() {
        return this.samplePrompts?.[this.language];
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
