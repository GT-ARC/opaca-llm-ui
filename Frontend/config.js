var config = {

    BackendAddress: import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:3001',

    BackendDefault: import.meta.env.VITE_BACKEND_DEFAULT ?? "self-orchestrated",
    Backends: {
        "simple": "Simple Prompt",
        "rest-gpt": "RestGPT",
        "tool-llm": "Tool LLM",
        "self-orchestrated": "Self-Orchestrated"
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

    languages: {
        GB: 'en-GB',
        DE: 'de-DE'
    },

    // if true, attempt to connect to the configured platform on load
    AutoConnect: false,

    // which set of questions is shown within the chat window on startup.
    DefaultQuestions: 'Task Automation',

    // which sidebar view is shown by default.
    // possible values: 'none', 'connect', 'questions', 'agents', 'config', 'debug'
    DefaultSidebarView: 'questions',


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
            sidebarQuestions: [
                {
                    "header": "Task Automation",
                    "icon": "🤖",
                    "questions": [
                        {"question": "Please fetch and summarize my latest e-mails.", "icon": "📧"},
                        {"question": "Summarize my upcoming meetings for the next 3 days.", "icon": "📅"},
                        {"question": "Show the phone numbers of all participants in my next meeting.", "icon": "📞"},
                        {"question": "Draft an out-of-office email explaining that Tolga is my stand-in for the next 2 weeks.", "icon": "✉️"},
                        {"question": "I need the phone numbers of the people working with LLM from the GoKI project.", "icon": "👥"},
                        {"question": "Schedule a brainstorming session with Tobias.", "icon": "🧩"},
                        {"question": "Find a meeting slot with the LLM team next week.", "icon": "📆"},
                        {"question": "Show my calendar for next week.", "icon": "📅"}
                    ]
                },
                {
                    "header": "Data Analysis",
                    "icon": "📊",
                    "questions": [
                        {"question": "Visualize the current energy mix of Germany in a meaningful way.", "icon": "⚡"},
                        {"question": "Retrieve the current noise level in the kitchen and coworking space. Then, plot them in a bar chart for comparison.", "icon": "🔊"},
                        {"question": "Create a bar plot comparing the current stock prices of Amazon, Apple, Microsoft and Nvidia.", "icon": "📊"},
                        {"question": "Retrieve the current temperature, noise level and humidity of the kitchen and visualize it in a meaningful way.", "icon": "🌤️"},

                    ]
                },
                {
                    "header": "Information & Upskilling",
                    "icon": "📚",
                    "questions": [
                        {"question": "How can you assist me?", "icon": "❓"},
                        {"question": "Tell me something about the 'go-KI' project by GT-ARC.", "icon": "🤖"},
                        {"question": "What documents do I need for a residence permit?", "icon": "📄"},
                        {"question": "Find the nearest public service office to the TU Berlin Campus?", "icon": "🏢"},
                        {"question": "How can I get an appointment at the Berlin Bürgeramt?", "icon": "📅"},
                        {"question": "What are 'Large Language Models'?", "icon": "🧠"},
                        {"question": "What are the most exciting tech trends for 2025?", "icon": "🚀"},
                        {"question": "Explain Agile methodology.", "icon": "🔄"},
                        {"question": "How to build a simple website?", "icon": "💻"}
                    ]
                },
                {
                    "header": "Smart Office",
                    "icon": "🏢",
                    "questions": [
                        {"question": "It is too noisy in the kitchen. Could you check if the noise level in the co-working space is lower?", "icon": "🔊"},
                        {"question": "Set my desk height to 120cm.", "icon": "⬆️"},
                        {"question": "Open the shelf in which I can store a glass.", "icon": "🥃"},
                        {"question": "Where can I find the espresso cups in the kitchen?", "icon": "☕"},

                    ]
                },
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
            sidebarQuestions: [
                {
                    "header": "Task Automation",
                    "icon": "🤖",
                    "questions": [
                        {"question": "Bitte ruf meine letzten E-Mails ab und fasse sie zusammen.", "icon": "📧"},
                        {"question": "Fasse mir meine Termine für die nächsten 3 Tage zusammen.", "icon": "📅"},
                        {"question": "Zeige mir die Telefonnummern aller Teilnehmer in meinem nächsten Meeting.", "icon": "📞"},
                        {"question": "Erstelle eine Abwesenheitsmail, in der Tolga als Vertretung für die nächsten 2 Wochen erwähnt wird.", "icon": "✉️"},
                        {"question": "Zeige mir die Telefonnummern aller Personen im GoKI Projekt die am Thema LLM arbeiten.", "icon": "👥"},
                        {"question": "Plane ein Brainstorming mit Tobias.", "icon": "🧩"},
                        {"question": "Finde einen Meetingtermin mit dem LLM-Team nächste Woche.", "icon": "📆"},
                        {"question": "Zeige mir meinen Kalender für die nächste Woche.", "icon": "📅"}
                    ]
                },
                {
                    "header": "Data Analysis",
                    "icon": "📊",
                    "questions": [
                        {"question": "Visualisiere den aktuellen Strommix von Deutschland auf eine sinnvolle Art und Weise.", "icon": "⚡"},
                        {"question": "Finde die aktuelle Lautstärke in der Küche und dem Coworking Space. Dann visualisiere die Daten in einem Balkendiagramm für einen Vergleich.", "icon": "🔊"},
                        {"question": "Erstelle ein Balkendiagramm der aktuellen Aktienpreise von Amazon, Apple, Microsoft und Nvidia.", "icon": "📊"},
                        {"question": "Finde die aktuelle Temperatur, Lautstärke und Luftfeuchtigkeit in der Küche und visualisiere sie auf eine sinnvolle Art und Weise.", "icon": "🌤️"},
                    ]
                },
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
                    "header": "Smart Office",
                    "icon": "🏢",
                    "questions": [
                        {"question": "Es ist zu laut an meinem Platz. Kannst du einen ruhigeren Arbeitsbereich vorschlagen?", "icon": "🔊"},
                        {"question": "Stelle die Höhe meines Schreibtisches auf 120cm ein.", "icon": "⬆️"},
                        {"question": "Ich möchte mein Wasserglas verstauen. Ich habe es nicht benutzt. Öffne den Küchenschrank, in den ich es zurücklegen kann.", "icon": "🥃"},
                        {"question": "Wo finde ich die Espressotassen in der Küche?", "icon": "☕"},
                    ]
                },
            ],
            speechRecognition: 'Sprechen' ,
            readLastMessage: 'Vorlesen',
            resetChat: 'Zurücksetzen',
            opacaLocation: 'OPACA URL'
        },
    },
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