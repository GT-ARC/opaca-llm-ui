import * as url from "node:url";

var config = {

    BackendAddress: import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:3001',

    BackendDefault: import.meta.env.VITE_BACKEND_DEFAULT ?? "tool-llm",
    Backends: {
        "simple": "Simple Prompt",
        "tool-llm": "Tool LLM",
        "self-orchestrated": "Self-Orchestrated",
	"simple-tools": "Simple Tool Prompt"
    },

    /*
    // reminder, because it's currently not used: define one level of "sub-backends" like this:
    BackendDefault: import.meta.env.VITE_BACKEND_DEFAULT ?? "opaca/self-orchestrated",
    Backends: {
        "opaca": {
            name: "OPACA LLM",
            subBackends: {
                "simple": "Simple Prompt",
                ...
            }
        },
        "itdz-knowledge": "Knowledge Assistant",
        ...
    },
    */

    BackLink: import.meta.env.VITE_BACKLINK ?? null,

    OpacaRuntimePlatform: import.meta.env.VITE_PLATFORM_BASE_URL ?? 'http://localhost:8000',

    VoiceServerAddress: import.meta.env.VITE_VOICE_SERVER_URL ?? null,

    ShowApiKey: parseEnvBool('VITE_SHOW_APIKEY', false),

    // if true, attempt to connect to the configured platform on-load
    AutoConnect: parseEnvBool('VITE_AUTOCONNECT', false),

    // starting color scheme: light, dark, or system (default)
    ColorScheme: import.meta.env.VITE_COLOR_SCHEME ?? 'system',

    // which set of questions is shown within the chat window on startup.
    // this should be the name of one of the categories, or 'none' (or any other nonexistent value) for none
    DefaultQuestions: 'none',

    // which sidebar view is shown by default.
    // possible values: 'none', 'info', 'questions', 'agents', 'config', 'debug'
    DefaultSidebarView: 'questions',

    // default UI language
    DefaultLanguage: import.meta.env.VITE_DEFAULT_LANGUAGE ?? 'GB',
}

/**
 * Parse an environment variable value to a boolean.
 *
 * @param name {String} The variable's name.
 * @param defaultValue {boolean} The default value.
 * @private
 */
function parseEnvBool(name, defaultValue = false) {
    const value = import.meta.env[name];
    return (value?.toLowerCase() === 'true') ?? defaultValue;
}

/**
 * Parse relevant query params and let their values override the default config values.
 */
function parseQueryParams() {
    const urlParams = {};
    for (const [key, value] of (new URLSearchParams(window.location.search)).entries()) {
        urlParams[key.toLowerCase()] = value;
    }

    config.AutoConnect = urlParams['autoconnect'] === 'true' ?? config.AutoConnect;
    config.DefaultSidebarView = urlParams['sidebar'] ?? config.DefaultSidebarView;
    config.DefaultQuestions = urlParams['samples'] ?? config.DefaultQuestions;
    config.DefaultLanguage = urlParams['lang'] ?? config.DefaultLanguage;
    config.ColorScheme = urlParams['colorscheme'] ?? config.ColorScheme;
}

parseQueryParams();

export default config = config;
