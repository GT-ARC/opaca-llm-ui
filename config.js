var config = {

    BackendAddress: 'http://localhost:3000',

    OpacaRuntimePlatform: 'http://localhost:8000',

    translations:{
        GB: {
            prompt: 'You suggest web services to fulfil a given purpose. You present the result as pseudo-code, including temporary variables if needed. You know some agents providing different actions that you can use. Do not assume any other services. If those services are not sufficient to solve the problem, just say so. Following is the list of available services described in JSON, which can be called as web services: ',
            language: 'Language',
            welcome: 'Welcome to the OPACA LLM Prototype! How can I help you?',
            defaultQuestion: 'What services do you know?',
            speechRecognition: 'Speech Recognition' ,
            readLastMessage: 'Read last message',
            resetChat: 'Reset Chat',    
            recognitionActive: 'Please speak now',
            opacaLocation: 'OPACA runtime platform location'
        },

        DE: {
            prompt: 'Sie schlagen Webdienste vor, um einen bestimmten Zweck zu erfüllen. Sie präsentieren das Ergebnis als Pseudocode, einschließlich temporärer Variablen, falls erforderlich. Sie kennen einige Agenten, die verschiedene Aktionen bereitstellen, die Sie verwenden können. Übernehmen Sie keine weiteren Leistungen. Wenn diese Dienste zur Lösung des Problems nicht ausreichen, sagen Sie es einfach. Im Folgenden finden Sie die Liste der verfügbaren, in JSON beschriebenen Dienste, die als Webdienste aufgerufen werden können: ',
            language: 'Sprache',
            welcome: 'Willkommen beim OPACA LLM-Prototyp! Wie kann ich Ihnen helfen?',
            defaultQuestion: 'Welche Dienste kennen Sie?',
            speechRecognition: 'Spracherkennung' ,
            readLastMessage: 'Letzte Nachricht vorlesen',
            resetChat: 'neuer Chat',
            recognitionActive: 'Bitte sprechen sie jetzt',
            opacaLocation: 'Standort der OPACA-Laufzeitplattform'
        },
    },
}
export default config = config