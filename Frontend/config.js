var config = {

    BackendAddress: import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:3001',

    BackendDefault: import.meta.env.VITE_BACKEND_DEFAULT ?? "self-orchestrated",
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

    VoiceServerAddress: import.meta.env.VITE_VOICE_SERVER_URL ?? 'http://localhost:7431',

    ShowKeyboard: import.meta.env.VITE_SHOW_KEYBOARD ?? false,

    ShowApiKey: import.meta.env.VITE_SHOW_APIKEY ?? false,

    // if true, attempt to connect to the configured platform on load
    AutoConnect: false,

    // which set of questions is shown within the chat window on startup.
    DefaultQuestions: 'Task Automation',

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
    config.AutoConnect = (urlParams['autoconnect'] === 'true');
    config.DefaultSidebarView = urlParams['sidebar'] ?? config.DefaultSidebarView;
    config.DefaultQuestions = urlParams['samples'] ?? config.DefaultQuestions;
}

parseQueryParams();

export default config = config;

