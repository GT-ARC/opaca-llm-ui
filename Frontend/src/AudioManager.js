import {ref} from "vue";
import conf from "../config.js";
import Localizer from "./Localizer.js";


/**
 * Provide unified API for TTS/STT using either the browser built-in
 * Web Speech API or a custom Whisper server running locally.
 */
class TtsAudio {

    constructor() {
        this._isPlaying = ref(false);
        this._isLoading = ref(false);
    }

    get isLoading() {
        return this._isLoading.value !== undefined
            ? this._isLoading.value
            : this._isLoading;
    }

    set isLoading(value) {
        if (this._isLoading.value !== undefined) {
            this._isLoading.value = value;
        } else {
            this._isLoading = value;
        }
    }

    get isPlaying() {
        return this._isPlaying.value !== undefined
            ? this._isPlaying.value
            : this._isPlaying;
    }

    set isPlaying(value) {
        if (this._isPlaying.value !== undefined) {
            this._isPlaying.value = value;
        } else {
            this._isPlaying = value;
        }
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
            const url = `${conf.VoiceServerAddress}/generate_audio`;
            const payload = { method: 'POST' };
            const params = new URLSearchParams({
                text: this._text,
                voice: audioManager.whisperVoice
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
        utterance.lang = Localizer.getLanguageForTTS();

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
        this._isVoiceServerConnected = ref(false);
        this._isLoading = ref(false);
        this._deviceInfo = ref('');
        this._recognition = null;

        this.whisperVoice = 'alloy';
    }

    get isVoiceServerConnected() {
        return this._isVoiceServerConnected.value !== undefined
            ? this._isVoiceServerConnected.value
            : this._isVoiceServerConnected;
    }

    set isVoiceServerConnected(value) {
        if (this._isVoiceServerConnected.value !== undefined) {
            this._isVoiceServerConnected.value = value;
        } else {
            this._isVoiceServerConnected = value;
        }
    }

    get isLoading() {
        return this._isLoading.value !== undefined
            ? this._isLoading.value
            : this._isLoading;
    }

    set isLoading(value) {
        if (this._isLoading.value !== undefined) {
            this._isLoading.value = value;
        } else {
            this._isLoading = value;
        }
    }

    get deviceInfo() {
        return this._deviceInfo.value !== undefined
            ? this._deviceInfo.value
            : this._deviceInfo;
    }

    set deviceInfo(value) {
        if (this._deviceInfo.value !== undefined) {
            this._deviceInfo.value = value;
        } else {
            this._deviceInfo = value;
        }
    }

    isBackendConfigured() {
        return !! conf.VoiceServerAddress
    }

    /**
     * Init connection to local Whisper server.
     * @returns {Promise<void>}
     */
    async initVoiceServerConnection() {
        if (!this.isBackendConfigured()) {
            console.warn('No voice server configured!');
            return;
        }

        try {
            const response = await fetch(`${conf.VoiceServerAddress}/info`);
            if (response.ok) {
                this.deviceInfo = await response.json();
                this.isVoiceServerConnected = true;
            } else {
                this.isVoiceServerConnected = false;
            }
        } catch (error) {
            console.error('Failed to connect to whisper server.');
            this.isVoiceServerConnected = false;
        }
    }

    async generateAudio(text) {
        return await this.isVoiceServerConnected
            ? this.generateWhisperAudio(text)
            : this.generateWebSpeechAudio(text);
    }

    async generateWhisperAudio(text) {
        if (!text) return null;
        return new WhisperAudio(text);
    }

    async generateWebSpeechAudio(text) {
        if (!text) return null;
        return new WebSpeechAudio(text);
    }

    /**
     * Start speech recognition with web speech API.
     * @param onResult Callback that should expect the successfully recognized text as an argument.
     */
    async startWebSpeechRecognition(onResult) {
        if (!this.isRecognitionSupported()) return;
        await this.stopWebSpeechRecognition();
        this._recognition = new (window.webkitSpeechRecognition || window.SpeechRecognition)();
        this._recognition.lang = Localizer.getLanguageForTTS();

        this._recognition.onresult = async (event) => {
            if (!event.results || event.results.length <= 0) return;
            const recognizedText = event.results[0][0].transcript;
            try {
                onResult(recognizedText);
            } catch (error) {
                console.error(error);
            }
        };

        this._recognition.onspeechend = () => {
            console.log('Recognition: Speech ended.');
            this.isLoading = false;
        };

        this._recognition.onnomatch = () => {
            console.error('Failed to recognize speech.');
        };

        this._recognition.onerror = (error) => {
            console.error('Failed to recognize speech: ', error);
        };

        this._recognition.onend = () => {
            console.log('Recognition ended.');
            this.isLoading = false;
        };

        this.isLoading = true;
        this._recognition.start();
    }

    async stopWebSpeechRecognition() {
        if (this._recognition) {
            this._recognition.abort();
            this._recognition = null;
        }
    }

    isRecognitionSupported() {
        return this.isVoiceServerConnected
            || (this._isGoogleChrome()
            && this._isWebSpeechSupported()
            && this._isSecureConnection());
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

    _isWebSpeechSupported() {
        return ('SpeechRecognition' in window) || ('webkitSpeechRecognition' in window);
    }

    _isSecureConnection() {
        return location.protocol === 'https'
            || location.hostname === 'localhost'
            || location.hostname !== '127.0.0.1';
    }

}


const audioManager = new AudioManager();
export default audioManager;