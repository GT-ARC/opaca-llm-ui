var config = {

    BackendAddress: import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:3001',

    BackendDefault: import.meta.env.VITE_BACKEND_DEFAULT ?? "rest-gpt-llama3",
    Backends: {
        "simple-openai": "Simple Prompt with GPT",
        "simple-llama": "Simple Prompt with LLAMA",
        "rest-gpt-llama3": "RestGPT with LLAMA",
        "rest-gpt-gpt-4o": "RestGPT with GPT-4o",
        "rest-gpt-gpt-4o-mini": "RestGPT with GPT-4o-Mini",
        "tool-llm-gpt-4o": "Tool LLM with GPT-4o",
        "tool-llm-gpt-4o-mini": "Tool LLM with GPT-4o-Mini",
    },

    OpacaRuntimePlatform: import.meta.env.VITE_PLATFORM_BASE_URL ?? 'http://localhost:8000',

    ShowKeyboard: import.meta.env.VITE_SHOW_KEYBOARD ?? false,

    ShowApiKey: import.meta.env.VITE_SHOW_APIKEY ?? false,

    translations:{
        GB: {
            name: "English",
            language: 'Language',
            submit: 'Submit',
            welcome: 'Welcome to the OPACA LLM! You can use me to interact with the assistants and services available on the OPACA platform, or ask me general questions. How can I help you today?',
            connected: 'Connected! Available assistants and services:',
            unreachable: 'Please connect to a running OPACA platform.',
            unauthorized: 'Please provide your login credentials to connect to the OPACA platform.',
            none: 'None',
            defaultQuestion: 'How can you assist me?',
            sampleQuestions: ["How can you assist me?", "Give me a summary of the agents and actions you provide.", "Call a single random action and give me the result!"],
            speechRecognition: 'Speak' ,
            readLastMessage: 'Read Last',
            resetChat: 'Reset',    
            opacaLocation: 'OPACA URL'
        },

        DE: {
            name: "Deutsch",
            language: 'Sprache',
            submit: 'Senden',
            welcome: 'Willkommen beim OPACA LLM! Sie können mich nutzen, um mit den Assistenten und Diensten auf der OPACA-Plattform zu interagieren, oder auch allgemeine Fragen stellen. Wie kann ich Ihnen heute helfen?',
            connected: 'Verbunden! Verfügbare Assistenten und Dienste:',
            unreachable: 'Bitte verbinden Sie sich mit einer laufenden OPACA Plattform.',
            unauthorized: 'Bitte geben Sie Ihre Zugangsdaten an, um sich mit der OPACA Plattform zu verbinden.',
            none: 'Keine',
            defaultQuestion: 'Womit kannst du mir helfen?',
            sampleQuestions: ["Womit kannst du mir helfen?", "Gib mir eine Zusammenfassung über die Agenten und Aktionen die du kennst.", "Rufe eine einzige, zufällige Aktion auf und gib mir das Ergebnis!"],
            speechRecognition: 'Sprechen' ,
            readLastMessage: 'Vorlesen',
            resetChat: 'Zurücksetzen',
            opacaLocation: 'OPACA URL'
        },
    },
}
export default config = config