var config = {

    BackendAddress: 'http://localhost:3001',

    BackendDefault: "llama3-rest-gpt",
    Backends: {
        "openai-test": "Simple OpenAI Prompt",
        "llama3-rest-gpt": "LLAMA with RestGPT",
        "gpt-4o-rest-gpt": "GPT-4o with RestGPT",
        "gpt-4o-mini-rest-gpt": "GPT-4o-Mini with RestGPT"
    },

    OpacaRuntimePlatform: 'http://localhost:8000',

    ShowKeyboard: false,

    translations:{
        GB: {
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