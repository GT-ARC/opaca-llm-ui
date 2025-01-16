// Debug color schemes for different modes [dark, light]
export const debugColors = {
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

// Placeholder messages for streaming
export const debugLoadingMessages = {
    // RestGPT
    "Planner": "Planning the next step",
    "Action Selector": "Selecting the best action",
    "Caller": "Calling the OPACA platform",
    "Evaluator": "Evaluating the results",
    // Tools
    "Tool Generator": "Generating the necessary tools",
    "Tool Evaluator": "Evaluating the tools",
    // Simple
    "user": "",
    "assistant": "",
    "system": "",
}