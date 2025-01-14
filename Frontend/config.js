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
            // Left in for now as a fallback for the sample questions
            sampleQuestions: [
                {"question": "How can you assist me?", "icon": "❓"}, 
                {"question": "Please fetch and summarize my latest e-mails.", "icon": "✉️"}, 
                {"question": "Please find a route from Munich to Berlin.", "icon": "🚗"},
                {"question": "Please find me someone from Go-KI who knows about LLM.", "icon": "🧑"}
            ],
            sidebarQuestions: [
                {
                    "header": "Information & Upskilling",
                    "icon": "📚",
                    "questions": [
                        {"question": "How can you assist me?", "icon": "❓"},
                        {"question": "Tell me something about the 'go-KI' project by GT-ARC.", "icon": "🤖"},
                        {"question": "What documents do I need for a residence permit?", "icon": "📄"},
                        {"question": "How can I find the nearest public service office for my address?", "icon": "🏢"},
                        {"question": "How can I get an appointment at the Berlin Bürgeramt?", "icon": "📅"},
                        {"question": "What are 'Large Language Models'?", "icon": "🧠"},
                        {"question": "What are the most exciting tech trends for 2025?", "icon": "🚀"},
                        {"question": "Explain Agile methodology.", "icon": "🔄"},
                        {"question": "How to build a simple website?", "icon": "💻"}
                    ]
                },
                {
                    "header": "Task Automation",
                    "icon": "🤖",
                    "questions": [
                        {"question": "Where can I find the espresso cups in the kitchen?", "icon": "☕"},
                        {"question": "Please fetch and summarize my latest e-mails.", "icon": "📧"},
                        {"question": "Summarize my upcoming meetings for the next week.", "icon": "📅"},
                        {"question": "Show the phone numbers of all participants in my next meeting.", "icon": "📞"},
                        {"question": "Draft an out-of-office email explaining that Tolga is my stand-in for the next 2 weeks.", "icon": "✉️"},
                        {"question": "I need the phone numbers of the people working with XAI from the GoKI project.", "icon": "👥"},
                        {"question": "Schedule a brainstorming session with Tobias.", "icon": "🧩"},
                        {"question": "Find a meeting slot with the XAI team next week.", "icon": "📆"},
                        {"question": "Show my calendar for next week.", "icon": "📅"}
                    ]
                },
                {
                    "header": "Data Analysis",
                    "icon": "📊",
                    "questions": [
                        {"question": "Plot the past noise levels in the ZEKI kitchen.", "icon": "📈"},
                        {"question": "Illustrate a route from Munich to Berlin with UTF-8 characters.", "icon": "🚗"},
                        {"question": "Create a forecast of the temperature in the Coworking Space.", "icon": "🌤️"},
                        {"question": "Is the current CO2 level in the conference room above threshold?", "icon": "🌡️"},
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
            // Left in for now as a fallback for the sample questions
            sampleQuestions: [
                {"question": "Womit kannst du mir helfen?", "icon": "❓"}, 
                {"question": "Bitte ruf meine letzen E-Mails ab und fasse sie zusammen.", "icon": "✉️"},
                {"question": "Berechne eine Route von München nach Berlin.", "icon": "🚗"},
                {"question": "Finde finde jemanden aus Go-KI der sich mit LLM auskennt.", "icon": "🧑"}
            ],
            sidebarQuestions: [
                {
                    "header": "Information & Upskilling",
                    "icon": "📚",
                    "questions": [
                        {"question": "Womit kannst du mir helfen?", "icon": "❓"},
                        {"question": "Erzähl mir etwas über das 'go-KI' Projekt von GT-ARC.", "icon": "🤖"},
                        {"question": "Welche Dokumente brauche ich für die Aufenthaltserlaubnis?", "icon": "📄"},
                        {"question": "Wie finde ich das nächstgelegene Bürgeramt für meine Adresse?", "icon": "🏢"},
                        {"question": "Wie komme ich an einen Termin beim Berliner Bürgeramt?", "icon": "📅"},
                        {"question": "Was sind 'Large Language Models'?", "icon": "🧠"},
                        {"question": "Was sind die spannendsten Tech-Trends für 2025?", "icon": "🚀"},
                        {"question": "Erkläre die Agile-Methodik.", "icon": "🔄"},
                        {"question": "Wie erstelle ich eine einfache Website?", "icon": "💻"}
                    ]
                },
                {
                    "header": "Task Automation",
                    "icon": "🤖",
                    "questions": [
                        {"question": "Wo finde ich die Espressotassen in der Küche?", "icon": "☕"},
                        {"question": "Bitte ruf meine letzten E-Mails ab und fasse sie zusammen.", "icon": "📧"},
                        {"question": "Fasse mir meine nächsten Termine für die zusammen.", "icon": "📅"},
                        {"question": "Zeige mir die Telefonnummern aller Teilnehmer in meinem nächsten Meeting.", "icon": "📞"},
                        {"question": "Erstelle eine Abwesenheitsmail, in der Tolga als Vertretung für die nächsten 2 Wochen erwähnt wird.", "icon": "✉️"},
                        {"question": "Zeige mir die Telefonnummern aller Personen im GoKI Projekt die an XAI arbeiten.", "icon": "👥"},
                        {"question": "Plane ein Brainstorming mit Tobias.", "icon": "🧩"},
                        {"question": "Finde einen Meetingtermin mit dem XAI-Team nächste Woche.", "icon": "📆"},
                        {"question": "Zeige mir meinen Kalender für die nächste Woche.", "icon": "📅"}
                    ]
                },
                {
                    "header": "Data Analysis",
                    "icon": "📊",
                    "questions": [
                        {"question": "Stelle die Geräuschlevel in der ZEKI-Küche dar.", "icon": "📈"},
                        {"question": "Visualisiere eine Route von München nach Berlin mit UTF-8 Zeichen.", "icon": "🚗"},
                        {"question": "Erstelle eine Temperaturprognose für den Coworking Space.", "icon": "🌤️"},
                        {"question": "Ist der aktuelle CO2-Wert im Konferenzraum über dem Grenzwert?", "icon": "🌡️"},
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