import * as url from "node:url";
import Cookie from "js-cookie";

// Available prompting methods
export const Methods = {
    "simple": "Simple Prompt",
    "simple-tools": "Simple Tool Prompt",
    "tool-llm": "Tool LLM",
    "self-orchestrated": "Self-Orchestrated",
};

export const MethodDescriptions = {
    "simple": "Using a simple prompt including the different available actions and querying the LLM in a loop, extracting the actions to call from the LLM's output.",
    "simple-tools": "A single agent, as in 'Simple', but using the 'tools' parameter.",
    "tool-llm": "Three agents using the built-in 'tools' parameter of newer models, providing a good balance of speed/simplicity and functionality.",
    "self-orchestrated": "A two-staged approach, where an orchestrator delegates to several groups of worker agents, each responsible for different OPACA agents.",
};

let baseConfig = {

    // URL to the SAGE backend
    backendUrl: getStringOrDefault("backendUrl", "http://localhost:3001"),

    // The initially selected prompting method
    //DefaultMethod: import.meta.env.VITE_DEFAULT_METHOD ?? "tool-llm",
    method: getStringOrDefault("method", "tool-llm"),

    // Optional "back-link" that redirects the user to a pre-configured site.
    backLink: getStringOrDefault("backLink", null),

    // URL to the OPACA Runtime platform
    platformUrl: getStringOrDefault("platformUrl", "http://localhost:8000"),

    // If true, attempt to connect to the configured platform on-load
    autoConnect: getBoolOrDefault("autoConnect", false),

    // Whether to allow container management in the SAGE UI; should be deactivated for public no-auth deployment
    allowContainerManagement: getBoolOrDefault("allowContainerManagement", true),

    // The initial color scheme: light, dark, or system (default)
    colorScheme: getStringOrDefault("colorScheme", "system"),

    // Which set of questions is shown within the chat window on startup.
    // This should be the name of one of the categories, or 'none' (or any other nonexistent value) for none
    selectedCategory: getStringOrDefault("selectedCategory", "none"),

    // Which sidebar view is shown by default.
    selectedSidebar: getStringOrDefault("selectedSidebar", "questions"),

    // whether the sidebar is showing only the most relevant icons
    sidebarCollapsed: getBoolOrDefault("sidebarCollapsed", true),

    // Default UI language
    //DefaultLanguage: import.meta.env.VITE_DEFAULT_LANGUAGE ?? 'GB',
    language: getStringOrDefault("language", "GB"),

    audioMethod: getStringOrDefault("audioMethod", "WHISPER"),

    registryUrl: getStringOrDefault("registryUrl", null),
}

function getStringOrDefault(key, defaultValue) {
    return getRawValue(key) ?? defaultValue;
}

function getBoolOrDefault(key, defaultValue) {
    const value = getRawValue(key)
    return value ? value.toLowerCase() === 'true' : defaultValue;
}

function getRawValue(key) {
    return getQueryParam(key) ?? Cookie.get(key) ?? getViteEnvVar(key);
}

function getQueryParam(key) {
    const params = new URLSearchParams(window.location.search);
    return params.get(key);
}

function getViteEnvVar(key) {
    const name = "VITE_" + key.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toUpperCase();
    return import.meta.env[name];
}

const cookieSetter = {
    set(target, key, value) {
        target[key] = value;
        Cookie.set(key, value);
        return true;
    }
};

const proxiedConfig = new Proxy(Object.assign({}, baseConfig), cookieSetter);

export default proxiedConfig;
