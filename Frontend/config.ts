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

interface Config {
    backendUrl: string;
    method: string;
    backlink: string | null;
    platformUrl: string;
    autoconnect: boolean;
    allowContainerManagement: boolean;
    colorScheme: string;
    selectedCategory: string;
    selectedSidebar: string;
    sidebarCollapsed: boolean;
    language: string;
    audioMethod: string;
    registryUrl: string | null;
};

const baseConfig: Config = {

    // URL to the SAGE backend
    backendUrl: getStringOrDefault("backendUrl", "http://localhost:3001"),

    // The selected prompting method
    method: getStringOrDefault("method", "tool-llm"),

    // Optional "back-link" that redirects the user to a pre-configured site.
    backlink: getMaybeStringOrDefault("backlink", null),

    // URL to the OPACA Runtime platform
    platformUrl: getStringOrDefault("platformUrl", "http://localhost:8000"),

    // If true, attempt to connect to the configured platform on-load
    autoconnect: getBoolOrDefault("autoconnect", false),

    // Whether to allow container management in the SAGE UI; should be deactivated for public no-auth deployment
    allowContainerManagement: getBoolOrDefault("allowContainerManagement", true),

    // The color scheme: light, dark, or system (default)
    colorScheme: getStringOrDefault("colorScheme", "system"),

    // Which set of questions is shown within the chat window.
    // This should be the name of one of the categories, or 'none' (or any other nonexistent value) for none
    selectedCategory: getStringOrDefault("selectedCategory", "none"),

    // Which sidebar view is shown.
    selectedSidebar: getStringOrDefault("selectedSidebar", "questions"),

    // whether the sidebar is showing only the most relevant icons
    sidebarCollapsed: getBoolOrDefault("sidebarCollapsed", true),

    // selected UI language
    language: getStringOrDefault("language", "GB"),

    // audio input/output method to use
    audioMethod: getStringOrDefault("audioMethod", "WHISPER"),

    // OPACA container registry
    registryUrl: getMaybeStringOrDefault("registryUrl", null),
}

function getStringOrDefault(key: string, defaultValue: string): string {
    return getRawValue(key) ?? defaultValue;
}

function getMaybeStringOrDefault(key: string, defaultValue: string | null): string | null {
    return getRawValue(key) ?? defaultValue;
}

function getBoolOrDefault(key: string, defaultValue: boolean): boolean {
    const value = getRawValue(key)
    return value ? value.toLowerCase() === 'true' : defaultValue;
}

function getRawValue(key: string): string | null {
    return getQueryParam(key) ?? Cookie.get(key) ?? getViteEnvVar(key);
}

function getQueryParam(key: string): string | null {
    const params = new URLSearchParams(window.location.search);
    return params.get(key);
}

function getViteEnvVar(key: string): string | null {
    const name = "VITE_" + key.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toUpperCase();
    return import.meta.env[name];
}

// listeners can be used to react to config changes
type Callback = (newValue: any) => void;
const listeners = new Map<string, Callback[]>();

export function addListener(key: string, callback: Callback) {
    const lst = listeners.get(key);
    if (lst) {
        lst.push(callback);
    } else {
        listeners.set(key, [callback]);
    }
}

function triggerListeners(key: string, newValue: any) {
    const lst = listeners.get(key);
    if (lst) {
        for (const callback of lst) {
            callback(newValue);
        }
    }
}

// the proxied config automatically sets cookies and calls any registered listeners whenever a setting is changed
const configHandler = {
    set(target: Config, key: string, value: any) {
        (target as any)[key as keyof Config] = value;
        Cookie.set(key, value);
        triggerListeners(key, value);
        return true;
    }
};
const proxiedConfig = new Proxy<Config>(Object.assign({}, baseConfig), configHandler);

export default proxiedConfig;
