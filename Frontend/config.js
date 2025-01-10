var config = {

    BackendAddress: import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:3001',

    BackendDefault: import.meta.env.VITE_BACKEND_DEFAULT ?? "opaca/tool-llm-openai",
    Backends: {
        "opaca": {
            name: "OPACA LLM",
            subBackends: {
                "simple-openai": "Simple Prompt",
                "simple-llama": "Simple Prompt (LLAMA)",
                "rest-gpt-openai": "RestGPT",
                "rest-gpt-llama": "RestGPT (LLAMA)",
                "tool-llm-openai": "Tool LLM",
                "tool-llm-llama": "Tool LLM (LLAMA)"
            }
        },
        "itdz-knowledge": "Knowledge Assistant",
        "itdz-data": "Data Analysis",
    },

    BackLink: import.meta.env.VITE_BACKLINK ?? null,

    OpacaRuntimePlatform: import.meta.env.VITE_PLATFORM_BASE_URL ?? 'http://localhost:8000',

    VoiceServerAddress: import.meta.env.VITE_VOICE_SERVER_URL ?? 'http://localhost:7431',

    ShowKeyboard: import.meta.env.VITE_SHOW_KEYBOARD ?? false,

    ShowApiKey: import.meta.env.VITE_SHOW_APIKEY ?? false,

    // if true, attempt to connect to the configured platform on load
    AutoConnect: import.meta.env.VITE_AUTO_CONNECT ?? false,

    languages: {
        GB: 'en-GB',
        DE: 'de-DE'
    },

    // which set of questions is shown within the chat window on startup.
    // possible values: 'general', 'email', 'scheduling', 'smart_office', 'public_services', 'learning', 'random'
    DefaultQuestions: import.meta.env.VITE_DEFAULT_QUESTIONS ?? 'random',

    // which sidebar view is shown by default.
    // possible values: 'connect', 'questions', 'agents', 'config', 'debug'
    DefaultSidebarView: import.meta.env.VITE_DEFAULT_SIDE_OPTION ?? 'agents',

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
            sidebarQuestions: [
                {
                    "id": "general",
                    "header": "General",
                    "icon": "❓",
                    "questions": [
                        {"question": "How can you assist me?"},
                        {"question": "What are 'Large Language Models'?"},
                        {"question": "Tell me something about the 'go-KI' project by GT-ARC."},
                        {"question": "What are the most exciting tech trends for 2025?"}
                    ]
                },
                {
                    "id": "email",
                    "header": "Email Assistant",
                    "icon": "✉️",
                    "questions": [
                        {"question": "Please fetch and summarize my latest e-mails."},
                        {"question": "Draft an out-of-office email explaining that Tolga is my stand-in for the next 2 weeks."},
                        {"question": "Show me all unread emails from last week."}
                    ]
                },
                {
                    "id": "scheduling",
                    "header": "Scheduling Assistant",
                    "icon": "📅",
                    "questions": [
                        {"question": "Schedule a brainstorming session with Tobias."},
                        {"question": "Find a meeting slot with the XAI team next week."},
                        {"question": "Show my calendar for next week."}
                    ]
                },
                {
                    "id": "smart_office",
                    "header": "Smart Office",
                    "icon": "🏢",
                    "questions": [
                        {"question": "Plot the past noise levels in the ZEKI kitchen."},
                        //{"question": "Is the current CO2 level in the conference room above threshold?"}, //Currently not working properly
                        //{"question": "Create a forecast of the temperature in the Coworking Space."}, //Currently not working properly
                        {"question": "Where can I find the espresso cups in the kitchen?"}
                    ]
                },
                {
                    "id": "public_services",
                    "header": "Public Services",
                    "icon": "🏛️",
                    "questions": [
                        {"question": "How can I get an appointment at the Berlin Bürgeramt?"},
                        {"question": "What documents do I need for residence permit?"},
                        {"question": "How can I find the nearest public service office for my address?"}
                    ]
                },
                {
                    "id": "learning",
                    "header": "Learning",
                    "icon": "📚",
                    "questions": [
                        {"question": "Help me learn data science basics."},
                        {"question": "Explain Agile methodology."},
                        {"question": "How to build a simple website?"},
                        {"question": "What is the Fourth Industrial Revolution?"}
                    ]
                }
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
            sidebarQuestions: [
                {
                    "id": "general",
                    "header": "Allgemein",
                    "icon": "❓",
                    "questions": [
                        {"question": "Womit kannst du mir helfen?"},
                        {"question": "Was sind 'Large Language Models'?"},
                        {"question": "Erzähl mir etwas über das 'go-KI' Projekt von GT-ARC."},
                        {"question": "Was sind die spannendsten Tech-Trends für 2025?"}
                    ]
                },
                {
                    "id": "email",
                    "header": "E-Mail Assistent",
                    "icon": "✉️",
                    "questions": [
                        {"question": "Bitte ruf meine letzten E-Mails ab und fasse sie zusammen."},
                        {"question": "Erstelle eine Abwesenheitsmail, in der Tolga als Vertretung für die nächsten 2 Wochen erwähnt wird."},
                        {"question": "Zeige mir alle ungelesenen E-Mails der letzten Woche."}
                    ]
                },
                {
                    "id": "scheduling",
                    "header": "Terminplanung",
                    "icon": "📅",
                    "questions": [
                        {"question": "Plane ein Brainstorming mit Tobias."},
                        {"question": "Finde einen Meetingtermin mit dem XAI-Team nächste Woche."},
                        {"question": "Zeige meinen Kalender für nächste Woche."}
                    ]
                },
                {
                    "id": "smart_office",
                    "header": "Smart Office",
                    "icon": "🏢",
                    "questions": [
                        {"question": "Stelle die Geräuschlevel in der ZEKI-Küche dar."},
                        // {"question": "Ist der aktuelle CO2-Wert im Konferenzraum über dem Grenzwert?"}, //Currently not working properly
                        // {"question": "Erstelle eine Temperaturprognose für den Coworking Space."}, //Currently not working properly
                        {"question": "Wo finde ich die Espressotassen in der Küche?"}
                    ]
                },
                {
                    "id": "public_services",
                    "header": "Öffentlicher Dienst",
                    "icon": "🏛️",
                    "questions": [
                        {"question": "Wie komme ich an einen Termin beim Berliner Bürgeramt?"},
                        {"question": "Welche Dokumente brauche ich für die Aufenthaltserlaubnis?"},
                        {"question": "Wie finde ich das nächstgelegene Bürgeramt für meine Adresse?"}
                    ]
                },
                {
                    "id": "learning",
                    "header": "Lernen",
                    "icon": "📚",
                    "questions": [
                        {"question": "Hilf mir, die Grundlagen der Data Science zu lernen."},
                        {"question": "Erkläre die Agile-Methodik."},
                        {"question": "Wie erstelle ich eine einfache Website?"},
                        {"question": "Was ist die Vierte Industrielle Revolution?"}
                    ]
                }
            ],
            speechRecognition: 'Sprechen' ,
            readLastMessage: 'Vorlesen',
            resetChat: 'Zurücksetzen',
            opacaLocation: 'OPACA URL'
        },
    },
}
export default config = config