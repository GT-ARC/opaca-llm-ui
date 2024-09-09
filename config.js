var config = {

    BackendAddress: import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:3001',

    BackendDefault: import.meta.env.VITE_BACKEND_DEFAULT ?? "rest-gpt-llama3",
    Backends: {
        "simple-openai": "Simple Prompt with GPT",
        "simple-llama": "Simple Prompt with LLAMA",
        "rest-gpt-llama3": "RestGPT with LLAMA",
        "rest-gpt-gpt-4o": "RestGPT with GPT-4o",
        "rest-gpt-gpt-4o-mini": "RestGPT with GPT-4o-Mini"
    },

    OpacaRuntimePlatform: import.meta.env.VITE_PLATFORM_BASE_URL ?? 'http://localhost:8000',

    ShowKeyboard: false,

    translations:{
        GB: {
            name: "English",
            language: 'Language',
            submit: 'Submit',
            welcome: 'Welcome to the OPACA LLM Prototype! How can I help you?',
            defaultQuestion: 'What services do you know?',
            speechRecognition: 'Speak' ,
            readLastMessage: 'Read Last',
            resetChat: 'Reset',    
            opacaLocation: 'OPACA URL'
        },

        DE: {
            name: "Deutsch",
            language: 'Sprache',
            submit: 'Senden',
            welcome: 'Willkommen beim OPACA LLM-Prototyp! Wie kann ich Ihnen helfen?',
            defaultQuestion: 'Welche Dienste kennst du?',
            speechRecognition: 'Sprechen' ,
            readLastMessage: 'Vorlesen',
            resetChat: 'Zurücksetzen',
            opacaLocation: 'OPACA URL'
        },
    },
}
export default config = config