var config = {

    BackendAddress: 'http://localhost:3000',

    OpacaRuntimePlatform: 'http://localhost:8000',

    translations:{
        GB: {
            prompt: 'You suggest web services to fulfil a given purpose. You present the result as pseudo-code, including temporary variables if needed. You know some agents providing different actions that you can use. Do not assume any other services. If those services are not sufficient to solve the problem, just say so. Following is the list of available services described in JSON, which can be called as web services: ',
            language: 'Language',
            welcome: 'Welcome to the OPACA LLM Prototype! How can I help you?',
            speechRecognition: 'Speech Recognition' ,   
            readLastMessage: 'Read last message',
            resetChat: 'Reset Chat',    
            recognitionActive: 'Please speak now',
        },
    },

}
export default config = config