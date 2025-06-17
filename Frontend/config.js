var config = {

    BackendAddress: import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:3001',

    BackendDefault: import.meta.env.VITE_BACKEND_DEFAULT ?? "tool-llm",
    Backends: {
        "simple": "Simple Prompt",
        "tool-llm": "Tool LLM",
        "self-orchestrated": "Self-Orchestrated"
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

    ShowKeyboard: import.meta.env.VITE_SHOW_KEYBOARD ?? false,

    ShowApiKey: import.meta.env.VITE_SHOW_APIKEY ?? false,

    // starting color scheme: light, dark, or system (default)
    ColorScheme: import.meta.env.VITE_COLOR_SCHEME ?? 'system',

    // if true, attempt to connect to the configured platform on load
    AutoConnect: import.meta.env.VITE_AUTOCONNECT ?? 'false',

    // which set of questions is shown within the chat window on startup.
    // this should be the name of one of the categories, or "None" (or any other nonexistent value) for none
    DefaultQuestions: 'None',

    // which sidebar view is shown by default.
    // possible values: 'none', 'connect', 'questions', 'agents', 'config', 'debug'
    DefaultSidebarView: 'questions',

    // localizer settings
    fallbackLanguage: import.meta.env.VITE_FALLBACK_LANGUAGE ?? 'GB',
    defaultLanguage: import.meta.env.VITE_DEFAULT_LANGUAGE ?? 'GB',
}


function parseQueryParams() {
    const urlParams = {};
    for (const [key, value] of (new URLSearchParams(window.location.search)).entries()) {
        urlParams[key.toLowerCase()] = value;
    }
    config.AutoConnect = (urlParams['autoconnect'] ?? config.AutoConnect) === 'true';
    config.DefaultSidebarView = urlParams['sidebar'] ?? config.DefaultSidebarView;
    config.DefaultQuestions = urlParams['samples'] ?? config.DefaultQuestions;
    config.ColorScheme = urlParams['colorscheme'] ?? config.ColorScheme;
}

parseQueryParams();

export default config = config;