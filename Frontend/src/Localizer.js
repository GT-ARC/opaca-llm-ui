import {reactive, ref} from 'vue';
import {shuffleArray} from "./utils.js";
import AudioManager from "./AudioManager.js";
import conf from '../config.js';

// Some general guidelines on creating Localizer keys
// - use the format "topic_action" or similar
// - use underscore to separate terms and camelcase for words, e.g. "files_createNew"
// - use at least one underscore to make it easier to search for occurrences in code
// - put new keys into their respective "group"
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
        general_authError: 'Invalid username or password.',
        settings_menu: "Settings",
        settings_language: 'Language',
        settings_method: "Method",
        settings_colorMode: "Color Scheme",
        settings_audio: "Audio",
        main_backendUnreachable: 'SAGE Backend is unreachable. Please check if the backend is running and reload the page.',
        main_opacaUrl: 'OPACA URL',
        main_connectHint: "Connect to OPACA Runtime Platform to access Agents and Actions. Authentication may be required.",
        main_opacaUnreachable: 'Could not connect to OPACA platform.',
        sidebar_info: "General Information",
        sidebar_chats: "Chats",
        sidebar_questions: "Prompt Library",
        sidebar_files: "Uploaded Files",
        sidebar_agents: "Agents and Actions",
        sidebar_extensions: "Extensions",
        sidebar_mcp: "MCP Servers",
        sidebar_config: "Configuration",
        sidebar_logs: "Logging",
        sidebar_faq: "Help/FAQ",
        sidebar_showStandardTools: "Show Standard Tools",
        sidebar_showAdvancedTools: "Show Advanced Tools",
        chatarea_welcome: 'What can I do for you today? Try one of the sample queries or ask me anything you like!',
        chatarea_input: 'Send a message ...',
        chatarea_rerollSamples: "More…",
        chatarea_submit: "Submit",
        chatarea_abort: "Cancel",
        chatarea_speak: "Dictate",
        chatarea_speak_stop: "Stop dictating",
        chatbubble_preparing: "Initializing the OPACA AI Agents",
        chatbubble_debug: "Debug",
        chatbubble_tools: "Tool Calls",
        chatbubble_metrics: "Metrics",
        chatbubble_error: "Error",
        chatbubble_audioPlay: "Play Audio",
        chatbubble_audioStop: "Stop Audio",
        chatbubble_audioLoad: "Audio is loading ...",
        chatbubble_copy: "Copy",
        chatbubble_files: "Attached Files",
        config_loading: "Loading config for %1...",
        config_missing: "No config available for %1.",
        config_save: "Save Config",
        config_save_done: "Config saved",
        config_save_invalid: "Invalid data: %1",
        config_save_error: "An error occurred",
        config_reset: "Reset to Defaults",
        config_reset_done: "Configuration was reset",
        cookies_text: "This website uses cookies to associate your chat session (message history and settings) with you. This cookie is kept for 30 days after the last interaction, or until manually deleted. The session data is stored in the backend and the messages are sent to the configured LLM. The session data will be deleted from the backend when the cookie expires, or by clicking the Reset button. The cookies and session data are used for the sole purpose of the chat interaction. Without, no continued conversation with the LLM is possible. By using this website, you consent to the above policy.",
        cookies_accept: "Accept",
        files_missing: "No files uploaded",
        files_upload: "Upload File",
        files_uploading: "Uploading…",
        files_include: "Include File in conversations?",
        files_view: "View File",
        files_rename: "Rename File",
        files_delete: "Remove File",
        files_delete_confirm: "Are you sure that you want to remove and forget the File '%1'?",
        files_overflow: "+%1 more…",
        files_droparea: "Drop files here to upload",
        mcp_loading: "Loading MCP servers...",
        mcp_missing: "No MCP servers available.",
        mcp_add: "Add MCP Server",
        mcp_remove: "Remove MCP Server",
        info_missing: "It's a little quiet here...",
        info_loading: "Querying functionality, please wait...",
        info_failed: "There was an error when querying the functionality: %1",
        faq_missing: "Unable to load FAQ.",
        chats_new: "New Chat",
        chats_edit: "Rename",
        chats_delete: "Delete Chat",
        chats_delete_confirm: "Are you sure that you want to delete the Chat?",
        chats_search: "Search Chats",
        chats_deleteAll: "Delete All Chats",
        chats_deleteAll_confirm: "Are you sure you want to delete all chats?",
        containerLogin_message: "The following action requires additional credentials: ",
        extensions_loading: "Loading available extensions...",
        extensions_missing: "No extensions available.",
        extensions_refresh: "Refresh",
        extensions_expand: "Expand",
        apiKey_missing: "Please provide an API key for this model: ",
        apiKey_invalid: "The entered API key for following model is invalid! Try again: ",
        notification_dismiss: "Dismiss",
        notification_append: "Append to current Chat",
        notification_autoAppend: "Also append future notifications",
        notification_missing: "No notifications",
        agents_loading: "Loading available agents...",
        agents_missing: "No agents available.",
        agents_search: "Search…",
        agents_description: "Description",
        agents_parameters: "Input Parameters",
        agents_result: "Result",
        agents_invoke: "Execute",
        agents_deploy: "Start Container",
        agents_deploy_hint: "Provide either Image Name or full Post-Container JSON",
        agents_undeploy: "Stop Container",
        agents_undeploy_confirm: "Are you sure you want to stop this Agent Container?",
        questions_addPrompt: "Add New Prompt",
        questions_addCategory: "Add New Category",
        questions_reset: "Restore Defaults",
        questions_reset_confirm: "Restore the default prompts?",
        questions_editPrompt: "Edit Prompt",
        questions_editCategory: "Edit Category",
        questions_toggleEditMode: "Edit Prompt Library",
        questions_deletePrompt: "Delete Prompt",
        questions_deletePrompt_confirm: "Delete prompt \"%1\"?",
        questions_deleteCategory: "Delete Category",
        questions_deleteCategory_confirm: "Delete category \"%1\"?",
        questions_generated: "Auto-Generated Prompts",
        questions_regenerate: "Suggest More",
        questions_placeholders: "Values for Placeholders",
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
        general_authError: 'Benutzer oder Passwort falsch.',
        settings_menu: "Einstellungen",
        settings_language: 'Sprache',
        settings_method: "Methode",
        settings_colorMode: "Farbschema",
        settings_audio: "Audio",
        main_backendUnreachable: 'SAGE Backend nicht erreichbar. Bitte überprüfen Sie ob das Backend läuft und laden Sie die Seite neu.',
        main_opacaUrl: 'OPACA URL',
        main_connectHint: "Mit OPACA Runtime Platform verbinden, um auf Agenten und Actions zuzugreifen. Authentisierung kann erforderlich sein.",
        main_opacaUnreachable: 'Verbindung mit OPACA Plattform fehlgeschlagen.',
        sidebar_info: "Generelle Informationen",
        sidebar_chats: "Chats",
        sidebar_questions: "Prompt-Bibliothek",
        sidebar_files: "Hochgeladene Dateien",
        sidebar_agents: "Agenten und Aktionen",
        sidebar_extensions: "Erweiterungen",
        sidebar_mcp: "MCP Servers",
        sidebar_config: "Konfiguration",
        sidebar_logs: "Logging",
        sidebar_faq: "Hilfe/FAQ",
        sidebar_showStandardTools: "Standard-Werkzeuge anzeigen",
        sidebar_showAdvancedTools: "Erweiterte Werkzeuge anzeigen",
        chatarea_welcome: 'Was kann ich heute für Dich tun? Versuch einen der Beispiel-Queries, oder frag mich alles was Du willst!',
        chatarea_input: 'Nachricht senden ...',
        chatarea_rerollSamples: "Mehr…",
        chatarea_submit: "Absenden",
        chatarea_abort: "Abbrechen",
        chatarea_speak: "Diktieren",
        chatarea_speak_stop: "Diktieren beenden",
        chatbubble_preparing: "OPACA KI-Agenten werden initialisiert",
        chatbubble_debug: "Debug",
        chatbubble_tools: "Tool Calls",
        chatbubble_metrics: "Metriken",
        chatbubble_error: "Fehler",
        chatbubble_audioPlay: "Audio abspielen",
        chatbubble_audioStop: "Audio stoppen",
        chatbubble_audioLoad: "Audio lädt ...",
        chatbubble_copy: "Kopieren",
        chatbubble_files: "Angehängte Dateien",
        config_loading: "Lade Konfiguration für %1...",
        config_missing: "Keine Konfiguration für %1 verfügbar.",
        config_save: "Speichern",
        config_save_done: "Konfiguration gespeichert",
        config_save_invalid: "Fehlerhafte Daten: %1",
        config_save_error: "Es ist ein Fehler aufgretreten",
        config_reset: "Zurücksetzen",
        config_reset_done: "Konfiguration wurde zurückgesetzt",
        cookies_text: "Diese Website verwendet Cookies, um Ihre Chat-Sitzung (Nachrichtenverlauf und Einstellungen) mit Ihnen zu verknüpfen. Die Cookies werden 30 Tage nach der letzten Interaktion oder bis zur manuellen Löschung gespeichert. Die Sitzungsdaten werden im Backend gespeichert und die Nachrichten werden an das konfigurierte LLM gesendet. Die Sitzungsdaten werden aus dem Backend gelöscht, wenn das Cookie abläuft oder wenn Sie auf die Reset-Schaltfläche klicken. Die Cookies und Sitzungsdaten werden ausschließlich für die Chat-Interaktion verwendet. Ohne sie ist keine fortgesetzte Konversation mit dem LLM möglich. Durch die Nutzung dieser Website stimmen Sie den oben genannten Richtlinien zu.",
        cookies_accept: "Annehmen",
        files_missing: "Keine Dateien hochgeladen",
        files_upload: "Datei hochladen",
        files_uploading: "Lade hoch…",
        files_include: "Datei in Konversationen einbeziehen?",
        files_view: "Datei anzeigen",
        files_rename: "Datei umbenennen",
        files_delete: "Datei entfernen",
        files_delete_confirm: "Sind Sie sicher, dass Sie die Datei '%1' entfernen und vergessen wollen?",
        files_overflow: "+%1 weitere…",
        files_droparea: "Dateien hier ablegen um sie hochzuladen",
        mcp_loading: "Lade verfügbare MCP-Server...",
        mcp_missing: "Keine MCP-Server verfügbar.",
        mcp_add: "MCP Server hinzufügen",
        mcp_remove: "MCP Server entfernen",
        info_missing: "Hier gibt es gerade nichts...",
        info_loading: "Frage Funktionalitäten an, bitte warten...",
        info_failed: "Es gab einen Fehler bei der Anfrage: %1",
        faq_missing: "FAQ konnte nicht geladen werden.",
        chats_new: "Neuer Chat",
        chats_edit: "Umbenennen",
        chats_delete: "Chat löschen",
        chats_delete_confirm: "Sind Sie sicher, dass Sie den Chat löschen wollen?",
        chats_search: "Chats Durchsuchen",
        chats_deleteAll: "Alle Chats löschen",
        chats_deleteAll_confirm: "Sind Sie sicher, dass Sie alle Chats löschen möchten?",
        containerLogin_message: "Die auszuführende Aktion benötigt weitere Zugangsdaten: ",
        extensions_loading: "Lade verfügbare Erweiterungen...",
        extensions_missing: "Keine Erweiterungen verfügbar.",
        extensions_refresh: "Neu laden",
        extensions_expand: "Vergrößern",
        apiKey_missing: "Bitte geben Sie für das folgende Model einen API-Key ein: ",
        apiKey_invalid: "Der eingegebene API-Key für das folgende Model ist ungültig! Versuchen Sie es erneut: ",
        notification_dismiss: "Entfernen",
        notification_append: "An den geöffneten Chat heften",
        notification_autoAppend: "Auch künftige Benachrichtigungen anhängen",
        notification_missing: "Keine Benachrichtigungen",
        agents_loading: "Lade verfügbare Agenten...",
        agents_missing: "Keine Agenten verfügbar.",
        agents_search: "Suchen…",
        agents_description: "Beschreibung",
        agents_parameters: "Parameter",
        agents_result: "Ergebnis",
        agents_invoke: "Ausführen",
        agents_deploy: "Container starten",
        agents_deploy_hint: "Geben Sie entweder den Image-Namen oder das komplette Post-Container JSON an",
        agents_undeploy: "Container stoppen",
        agents_undeploy_confirm: "Sind Sie sicher, dass Sie den Agent Container stoppen möchten?",
        questions_addPrompt: "Neuer Prompt",
        questions_addCategory: "Neue Kategorie",
        questions_reset: "Wiederherstellen",
        questions_reset_confirm: "Standard-Prompts wiederherstellen?",
        questions_editPrompt: "Prompt bearbeiten",
        questions_editCategory: "Kategorie bearbeiten",
        questions_toggleEditMode: "Prompt-Bibliothek bearbeiten",
        questions_deletePrompt: "Prompt löschen",
        questions_deletePrompt_confirm: "Prompt \"%1\" löschen?",
        questions_deleteCategory: "Kategorie löschen",
        questions_deleteCategory_confirm: "Kategorie \"%1\" löschen?",
        questions_generated: "Auto-Generierte Prompts",
        questions_regenerate: "Weitere Beispiele",
        questions_placeholders: "Werte für Platzhalter",
    },
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
        let filteredQuestions = Object.values(this.getPrompts())
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
