// Debug color schemes for different modes [dark, light]
export const debugColors = {
    // System
    "preparing": ["#10a37f", "#10a37f"],  // Primary green color for preparation phase
    // Multi-Agent System - Orchestration Level
    "Orchestrator": ["#ff6b6b", "#ff6b6b"],  // Red for orchestration
    // Multi-Agent System - Agent Level
    "AgentPlanner": ["#CD34A9", "#CD34A9"],  // Bright purple for agent planning
    "WorkerAgent": ["#4ecdc4", "#4ecdc4"],   // Turquoise for worker execution
    "AgentEvaluator": ["#45b7d1", "#45b7d1"], // Light blue for agent evaluation
    // Multi-Agent System - Overall Level
    "OverallEvaluator": ["#96ceb4", "#96ceb4"], // Sage green for overall evaluation
    "IterationAdvisor": ["#9d4edd", "#9d4edd"],  // Purple for iteration advisor
    // Multi-Agent System - Output Level
    "OutputGenerator": ["#ffbe0b", "#ffbe0b"],  // Orange for output generation
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
        "preparing": "Initializing the OPACA AI Agents",
        // Multi-Agent System - Orchestration Level
        "Orchestrator": "Creating detailed orchestration plan",
        // Multi-Agent System - Agent Level
        "AgentPlanner": "Planning function calls for task",
        "WorkerAgent": "Executing function calls",
        "AgentEvaluator": "Evaluating task completion",
        // Multi-Agent System - Overall Level
        "OverallEvaluator": "Assessing overall request completion",
        "IterationAdvisor": "Analyzing results and planning next steps",
        // Multi-Agent System - Output Level
        "OutputGenerator": "Generating final response",
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
        "preparing": "OPACA KI-Agenten werden initialisiert",
        // Multi-Agent System - Orchestration Level
        "Orchestrator": "Erstelle Plan zur Aufgabenverteilung",
        // Multi-Agent System - Agent Level
        "AgentPlanner": "Plane Funktionsaufrufe für die Aufgabe",
        "WorkerAgent": "Führe Funktionsaufrufe aus",
        "AgentEvaluator": "Bewerte Aufgabenabschluss",
        // Multi-Agent System - Overall Level
        "OverallEvaluator": "Bewerte Gesamtanfrage",
        "IterationAdvisor": "Analysiere Ergebnisse und plane nächste Schritte",
        // Multi-Agent System - Output Level
        "OutputGenerator": "Generiere finale Antwort",
        // Tools
        "Tool Generator": "Aufrufen der benötigten Tools",
        "Tool Evaluator": "Überprüfen der Tool-Ergebnisse",
        // Simple
        "user": "",
        "assistant": "",
        "system": "",
    }
}