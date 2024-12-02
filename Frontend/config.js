var config = {

    BackendAddress: import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:3001',

    BackendDefault: import.meta.env.VITE_BACKEND_DEFAULT ?? "opaca/tool-llm-gpt",
    Backends: {
        "opaca": {
            name: "OPACA LLM",
            subBackends: {
                "simple-openai": "Simple Prompt",
                "simple-llama": "Simple Prompt (LLAMA)",
                "rest-gpt-llama3": "RestGPT (LLAMA)",
                "rest-gpt-gpt-4o": "RestGPT (4o)",
                "rest-gpt-gpt-4o-mini": "RestGPT (4o-mini)",
                "tool-llm-gpt": "Tool LLM",
                "tool-llm-llama": "Tool LLM (LLAMA)"
            }
        },
        "itdz-knowledge": "Knowledge Assistant",
        "itdz-data": "Data Analysis",
    },

    OpacaRuntimePlatform: import.meta.env.VITE_PLATFORM_BASE_URL ?? 'http://10.42.6.107:8000',

    ShowKeyboard: import.meta.env.VITE_SHOW_KEYBOARD ?? false,

    ShowApiKey: import.meta.env.VITE_SHOW_APIKEY ?? false,

    languages: {
        GB: 'en-GB',
        DE: 'de-DE'
    },

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
            sampleQuestions: [
                {"question": "How can you assist me?", "icon": "❓"}, 
                {"question": "Please fetch and summarize my latest e-mails.", "icon": "✉️"}, 
                {"question": "Please find a route from Munich to Berlin.", "icon": "🚗"},
                {"question": "Please find me someone from Go-KI who knows about LLM.", "icon": "🧑"}
                
            ],
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
            sampleQuestions: [
                {"question": "Womit kannst du mir helfen?", "icon": "❓"}, 
                {"question": "Bitte ruf meine letzen E-Mails ab und fasse sie zusammen.", "icon": "✉️"},
                {"question": "Berechne eine Route von München nach Berlin.", "icon": "🚗"},
                {"question": "Finde finde jemanden aus Go-KI der sich mit LLM auskennt.", "icon": "🧑"}
            ],
            speechRecognition: 'Sprechen' ,
            readLastMessage: 'Vorlesen',
            resetChat: 'Zurücksetzen',
            opacaLocation: 'OPACA URL'
        },
    },
}
export default config = config