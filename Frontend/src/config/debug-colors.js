// Debug color schemes for different modes [dark, light]
export const debugColors = {
    // System
    "preparing": ["#10a37f", "#10a37f"],  // Primary green color for preparation phase
    // RestGPT
    "Planner": ["#ff0000", "#9c0000"],
    "Action Selector": ["#ffff00", "#bf6e00"],
    "Caller": ["#5151ff", "#0000b1"],
    "Evaluator": ["#00ff00", "#007300"],
    // Tools
    "Tool Generator": ["#ff0000", "#9c0000"],
    "Tool Generator-Tools": ["#ff0000", "#9c0000"],     // Special class needed for streaming
    "Tool Evaluator": ["#ffff00", "#bf6e00"],
    // Simple
    "user": ["#ffffff", "#000000"],
    "assistant": ["#8888ff", "#434373"],
    "system": ["#ffff88", "#71713d"],
}

// Default colors for unknown agents [dark, light]
export const defaultDebugColors = ["#fff", "#000"];

// Placeholder messages for streaming in different languages
export const debugLoadingMessages = {
    GB: {
        // System
        "preparing": "Initializing the OPACA AI Agent",
        // RestGPT
        "Planner": "Analyzing your request",
        "Action Selector": "Determining best approach",
        "Caller": "Calling the OPACA platform",
        "Evaluator": "Processing results",
        // Tools
        "Tool Generator": "Calling the required tools",
        "Tool Evaluator": "Validating tool calls",
        // Simple
        "user": "",
        "assistant": "",
        "system": "",
    },
    DE: {
        // System
        "preparing": "OPACA KI-Agent wird initialisiert",
        // RestGPT
        "Planner": "Analysiere Ihre Anfrage",
        "Action Selector": "Ermittle beste Vorgehensweise",
        "Caller": "Aufrufen der OPACA-Plattform",
        "Evaluator": "Verarbeite Ergebnisse",
        // Tools
        "Tool Generator": "Aufrufen der benötigten Tools",
        "Tool Evaluator": "Überprüfen der Tool-Ergebnisse",
        // Simple
        "user": "",
        "assistant": "",
        "system": "",
    }
}