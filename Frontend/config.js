import * as url from "node:url";

// Available "backend methods"
export const Backends = {
    "simple": "Simple Prompt",
    "tool-llm": "Tool LLM",
    "self-orchestrated": "Self-Orchestrated",
    "simple-tools": "Simple Tool Prompt"
};

export const BackendDescriptions = {
    "simple": "Using a simple prompt including the different available actions and querying the LLM in a loop, extracting the actions to call from the LLM's output.",
    "tool-llm": "Two agents using the built-in 'tools' parameter of newer models, providing a good balance of speed/simplicity and functionality.",
    "self-orchestrated": "A two-staged approach, where an orchestrator delegates to several groups of worker agents, each responsible for different OPACA agents.",
    "simple-tools": "A single agent, as in 'Simple', but using the 'tools' parameter.",
};

let config = {

    // URL to the OPACA LLM UI backend
    BackendAddress: import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:3001',

    // The initially selected "backend method"
    DefaultBackend: import.meta.env.VITE_DEFAULT_BACKEND ?? "tool-llm",

    // Optional "back-link" that redirects the user to a pre-configured site.
    BackLink: import.meta.env.VITE_BACKLINK ?? null,

    // URL to the OPACA Runtime platform
    OpacaRuntimePlatform: import.meta.env.VITE_PLATFORM_BASE_URL ?? 'http://localhost:8000',

    // URL to the audio server
    VoiceServerUrl: import.meta.env.VITE_VOICE_SERVER_URL ?? null,

    // If true, attempt to connect to the configured platform on-load
    // the boolean value is parsed later, together with the one passed as query param, if any
    AutoConnect: parseEnvBool('VITE_AUTOCONNECT', false),

    // The initial color scheme: light, dark, or system (default)
    ColorScheme: import.meta.env.VITE_COLOR_SCHEME ?? 'system',

    // Which set of questions is shown within the chat window on startup.
    // This should be the name of one of the categories, or 'none' (or any other nonexistent value) for none
    DefaultQuestions: 'none',

    // Which sidebar view is shown by default.
    // Possible values: 'none', 'info', 'questions', 'agents', 'config', 'debug'
    DefaultSidebarView: 'questions',

    // Default UI language
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
    console.log(name, value);
    return (value?.toLowerCase() === 'true') ?? defaultValue;
}

/**
 * Parse relevant query params and let their values override the default config values.
 * @private
 */
function parseQueryParams() {
    const urlParams = {};
    for (const [key, value] of (new URLSearchParams(window.location.search)).entries()) {
        urlParams[key.toLowerCase()] = value;
    }

    config.AutoConnect = urlParams['autoconnect'] !== undefined
        ? urlParams['autoconnect'] === 'true'
        : config.AutoConnect;
    config.DefaultSidebarView = urlParams['sidebar'] ?? config.DefaultSidebarView;
    config.DefaultQuestions = urlParams['samples'] ?? config.DefaultQuestions;
    config.DefaultLanguage = urlParams['lang'] ?? config.DefaultLanguage;
    config.ColorScheme = urlParams['colorscheme'] ?? config.ColorScheme;
}

parseQueryParams();

export default config;
