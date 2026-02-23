import {ref} from "vue";
import conf from "../config.js";
import Localizer from "./Localizer.js";


const voiceGenLocales = {
    WHISPER: {GB: 'en', DE: 'de'},
    WEBSPEECH: {GB: 'en-US', DE: 'de-DE'},
};

function getLanguageForWhisper() {
    return voiceGenLocales["WHISPER"][Localizer.language];
}

function getLanguageForWebSpeech() {
    return voiceGenLocales["WEBSPEECH"][Localizer.language];
}


/**
 * Provide unified API for TTS/STT using either the browser built-in
 * Web Speech API or a custom Whisper server running locally.
 */
class TtsAudio {

    constructor() {
        this.isPlaying = false;
        this.isLoading = false;
    }

    async setup() {
        throw Error("Not implemented");
    }

    async play() {
        throw Error("Not implemented");
    }

    async stop() {
        throw Error("Not implemented");
    }

    canPlay() {
        throw Error("Not implemented");
    }

    canStop() {
        throw Error("Not implemented");
    }

}

/**
 * Class for handling whisper-generated audio.
 */
class WhisperAudio extends TtsAudio {

    constructor(text) {
        super();
        this._text = text;
        this.audio = null;
    }

    async setup() {
        this.isLoading = true;
        try {
            const url = `${conf.BackendAddress}/whisper/generate`;
            const payload = { method: 'POST' };
            const params = new URLSearchParams({
                text: this._text,
                voice: 'alloy',
            });

            const response = await fetch(`${url}?${params}`, payload);
            if (response.ok) {
                const audioBlob = await response.blob();
                this.audio = this.makeFromBlob(audioBlob);
            } else {
                const errorText = await response.text();
                console.error('Audio API error:', response.status, errorText);
                return null;
            }
        } catch (error) {
            console.error(error);
            alert('Failed to generate audio.');
            return null;
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * @param audioBlob {Blob}
     * @returns {HTMLAudioElement}
     */
    makeFromBlob(audioBlob) {
        if (!audioBlob) return null;
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        audio.onplay = () => this.isPlaying = true;
        audio.onpause = () => this.isPlaying = false;
        audio.onend = () => this.isPlaying = false;
        return audio;
    }

    async play() {
        if (!this.canPlay()) return;
        try {
            if (!this.isPlaying) {
                this.isPlaying = true;
                await this.audio.play();
            } else {
                await this.stop();
            }
        } catch (error) {
            console.error(error);
            this.isPlaying = false;
        }
    }

    async stop() {
        if (!this.audio) return;
        this.audio.pause();
        this.audio.currentTime = 0;
        this.isPlaying = false;
    }

    canPlay() {
        return this.audio !== null && !this.isLoading;
    }

    canStop() {
        return this.audio !== null && !this.isLoading;
    }

}

/**
 * Class for handling WebSpeech-generated audio.
 */
class WebSpeechAudio extends TtsAudio {

    constructor(text) {
        super();
        this._text = text;
        this._synthesis = null;
        this._utterance = null;
    }

    async setup() {
        const utterance = new SpeechSynthesisUtterance(this._text);
        utterance.lang = getLanguageForWebSpeech();

        utterance.onstart = () => {
            this.isLoading = false;
            this.isPlaying = true;
        };
        utterance.onend = () => {
            this.isPlaying = false;
            this.isLoading = false;
        };
        utterance.onerror = (error) => {
            console.error('Failed to play utterance:', error);
            this.isPlaying = false;
            this.isLoading = false;
        };

        this._utterance = utterance;
    }

    async play() {
        if (this.canPlay()) {
            this.isLoading = true;
            this._synthesis = window.speechSynthesis;
            this._synthesis.speak(this._utterance);
        }
    }

    async stop() {
        if (this.canStop()) {
            this._synthesis.pause();
            this._synthesis.cancel();
            this._synthesis = null;
        }
    }

    canPlay() {
        return this._utterance != null && this._utterance.text;
    }

    canStop() {
        return this._utterance != null && this._synthesis !== null
            && this._synthesis.speaking
    }

}

/**
 * Manager class that provides unified public access.
 */
class AudioManager {

    constructor() {
        this._isRecording = ref(false);
        this._isTranscribing = ref(false);
        this.method = "WHISPER";

        // webkit
        this._recognition = null;

        // manual recording for whisper
        this._audioContext = null;
        this._mediaRecorder = null;
    }
    
    get isRecording() {
        return this._isRecording.value;
    }

    set isRecording(value) {
        this._isRecording.value = value;
    }

    get isTranscribing() {
        return this._isTranscribing.value;
    }

    set isTranscribing(value) {
        this._isTranscribing.value = value;
    }

    getAudioMethods() {
        if (this.isWebSpeechSupported()) {
            return { WHISPER: "Whisper", WEBSPEECH: "WebSpeech" };
        } else {
            return { WHISPER: "Whisper" };
        }
    }

    async generateAudio(text) {
        if (!text) return null;
        switch (this.method) {
            case "WHISPER": return new WhisperAudio(text);
            case "WEBSPEECH": return new WebSpeechAudio(text);
        };
    }

    /**
     * Start speech recognition with web speech API.
     * @param onResult Callback that should expect the successfully recognized text as an argument.
     * @param onError Callback that should expect any error messages.
     */
    async startRecognition(onResult, onError) {
        if (!this.isRecognitionSupported()) return;
        switch (this.method) {
            case "WHISPER": this.startWhisperRecognition(onResult, onError); break;
            case "WEBSPEECH": this.startWebSpeechRecognition(onResult, onError); break;
        };
    }

    async stopRecognition() {
        if (!this.isRecognitionSupported()) return;
        switch (this.method) {
            case "WHISPER": this.stopWhisperRecognition(); break;
            case "WEBSPEECH": this.stopWebSpeechRecognition(); break;
        };
    }

    async startWebSpeechRecognition(onResult, onError) {
        if (! this.isWebSpeechSupported()) {
            onError("WebSpeech is not supported in your Browser");
        }
        this.stopWebSpeechRecognition();
        try {
            this._recognition = new (window.webkitSpeechRecognition || window.SpeechRecognition)();
        } catch (error) {
            console.error(`Failed to start web speech recognition: ${error}`);
            return;
        }
        this._recognition.lang = getLanguageForWebSpeech();
        this._recognition.onresult = async (event) => {
            const recognizedText = Array.from(event.results).map(r => r[0].transcript).join('\n\n');
            onResult(recognizedText);
        };

        this._recognition.onnomatch = () => {
            onError('Failed to recognize speech.');
        };

        this._recognition.onerror = (error) => {
            onError(`Failed to recognize speech: ${JSON.stringify(error)}`);
        };

        this._recognition.onend = () => {
            console.log('Recognition ended.');
            this.isRecording = false;
        };

        this.isRecording = true;
        this._recognition.start();
    }

    stopWebSpeechRecognition() {
        if (this._recognition) {
            this._recognition.abort();
            this._recognition = null;
        }
    }

    isRecognitionSupported() {
        return this._isSecureConnection();
    }

    isWebSpeechSupported() {
        return this._isGoogleChrome() && (('SpeechRecognition' in window) || ('webkitSpeechRecognition' in window));
    }

    /**
     * Very hacky check if the user is using the (full) Google Chrome browser.
     * @returns {boolean}
     */
    _isGoogleChrome() {
        return window.chrome !== undefined
            && window.navigator.vendor === "Google Inc."
            && window.navigator.userAgentData !== undefined
            && Array.from(window.navigator.userAgentData?.brands)?.some(b => b?.brand === 'Google Chrome')
            && Array.from(window.navigator.plugins)?.some(plugin => plugin.name === "Chrome PDF Viewer");
    }

    _isSecureConnection() {
        return location.protocol === 'https'
            || location.hostname === 'localhost'
            || location.hostname === '127.0.0.1';
    }

    async startWhisperRecognition(onResult, onError) {
        try {
            this.isRecording = true;
            this._audioContext = new AudioContext();
            
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 44100,
                    sampleSize: 16,
                }
            });

            // set up analyser on the stream for silence detection
            const analyser = this._audioContext.createAnalyser();
            const dataArray = new Float32Array(analyser.fftSize);
            this._audioContext.createMediaStreamSource(stream).connect(analyser);
            const audioChunks = [];
            let lastSound = Date.now()

            this._mediaRecorder = new MediaRecorder(stream);
            this._mediaRecorder.ondataavailable = async (event) => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }

                // detect duration of silence
                analyser.getFloatTimeDomainData(dataArray);
                const rms = Math.sqrt(dataArray.reduce((s, x) => s + x*x, 0) / dataArray.length);
                if (rms > 0.02) {
                    lastSound = Date.now();
                } else if (Date.now() - lastSound > 800) {
                    this.stopWhisperRecognition();
                }
            };

            this._mediaRecorder.onstop = async () => {
                this.isRecording = false;
                this.isTranscribing = true;
                try {
                    const result = await this.processAudioChunks(audioChunks);
                    onResult(result);
                } catch (error) {
                    onError(`Error processing audio: ${error}`);
                }
                this.isTranscribing = false;
            };

            this._mediaRecorder.start(100);
        } catch (error) {
            this.isRecording = false;
            onError(`Error recording audio: ${error}`);
        }
    }

    stopWhisperRecognition() {
        if (this._mediaRecorder) {
            this._mediaRecorder.stop();
            this._mediaRecorder = null;
        }
    }

    async processAudioChunks(audioChunks) {
        if (audioChunks.length === 0) return '';

        const ext = audioChunks[0].type.split("/")[1].split(";")[0].trim();
        const lang = getLanguageForWhisper();

        const formData = new FormData();
        formData.append('file', new File([new Blob(audioChunks)], `audio.${ext}`, { type: `audio/${ext}` }));

        const response = await fetch(`${conf.BackendAddress}/whisper/transcribe/?filetype=${ext}&language=${lang}`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        return result.text || '';
    }
}


const audioManager = new AudioManager();
export default audioManager;