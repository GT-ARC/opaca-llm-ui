import {ref} from "vue";
import conf from "../config.js";
import Localizer from "./Localizer.js";


/**
 * Provide unified API for TTS/STT using either the browser built-in
 * Web Speech API or a custom Whisper server running locally.
 */


class TtsAudio {

    constructor(audioBlob) {
        this._isPlaying = ref(false);
        this.audio = this.makeFromBlob(audioBlob);
    }

    get isPlaying() {return this._isPlaying.value;}
    set isPlaying(value) {this._isPlaying.value = value;}

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
        try {
            if (!this.canPlay) return;
            if (!this.isPlaying) {
                await this.audio.play();
            } else {
                this.stop();
            }
        } catch (error) {
            console.error(error);
            this.isPlaying = false;
        }
    }

    stop() {
        if (!this.audio) return;
        this.audio.pause();
        this.audio.currentTime = 0;
    }

    canPlay() {
        return this.audio !== null;
    }

}


class AudioManager {
    constructor() {
        this._isVoiceServerConnected = ref(false);
        this._isLoading = ref(false);
        this._deviceInfo = ref('');

        this.whisperVoice = 'alloy';
        this.synthesis = null;
    }

    get isLoading() {return this._isLoading.value;}
    set isLoading(value) {this._isLoading.value = value;}

    get isVoiceServerConnected() {return this._isVoiceServerConnected.value;}
    set isVoiceServerConnected(value) {this._isVoiceServerConnected.value = value;}

    get deviceInfo() {return this._deviceInfo.value;}
    set deviceInfo(value) {this._deviceInfo.value = value;}

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
            console.error('Error fetching audio server info:', error);
            this.isVoiceServerConnected = false;
        }
    }

    async generateAudio(text) {
        if (this.isVoiceServerConnected) {
            await this.generateWhisperAudio(text);
        } else {
            await this.generateWebSpeechAudio(text);
        }
    }

    /**
     * Generate audio from the given text using a local Whisper server.
     * @param text {String}
     * @returns {Promise<TtsAudio|null>}
     */
    async generateWhisperAudio(text) {
        if (!text) return null;
        if (this.isLoading) return null;
        this.isLoading = true;

        try {
            const url = `${conf.VoiceServerAddress}/generate_audio`;
            const payload = { method: 'POST' };
            const params = new URLSearchParams({
                text: text,
                voice: this.whisperVoice
            });

            const response = await fetch(`${url}?${params}`, payload);
            if (response.ok) {
                const audioBlob = await response.blob();
                return new TtsAudio(audioBlob);
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

    async generateWebSpeechAudio(text) {
        this.abortSpeaking();
        this.synthesis = new (webkitSpeechSynthesis || SpeechSynthesis);
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = Localizer.getLanguageForTTS();

        utterance.onstart = () => {
            console.log("Speaking started.");
        };

        utterance.onend = () => {
            console.log("Speaking ended.");
        };

        utterance.onerror = (error) => {
            console.error(error);
        };

        speechSynthesis.speak(utterance);
    }

    /**
     * Start speech recognition with web speech.
     *
     * @param onResult Callback that should expect the successfully recognized text.
     */
    async startRecognition(onResult) {
        if (!this.isRecognitionSupported()) return;
        this.abortSpeaking();
        const recognition = new (webkitSpeechRecognition || SpeechRecognition)()
        recognition.lang = Localizer.getLanguageForTTS();

        recognition.onresult = async (event) => {
            if (!event.results || event.results.length <= 0) return;
            const recognizedText = event.results[0][0].transcript;
            try {
                onResult(recognizedText);
            } catch (error) {
                console.error(error);
            }
        };

        recognition.onspeechend = () => {
            console.log('Recognition: Speech ended.');
            this.isLoading = false;
        };

        recognition.onnomatch = () => {
            console.error('Failed to recognize speech.');
        };

        recognition.onerror = (error) => {
            console.error('Failed to recognize speech: ', error);
        };

        recognition.onend = () => {
            console.log('Recognition ended.');
            this.isLoading = false;
        };

        recognition.start();
        this.isLoading = true;
    }

    abortSpeaking() {
        if (this.synthesis && this.synthesis.speaking) {
            this.synthesis.cancel();
            this.synthesis = null;
        }
    }

    isRecognitionSupported() {
        return this._isGoogleChrome()
            && this._isWebSpeechSupported()
            && this._isSecureConnection();
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