import {ref} from "vue";
import conf from "../config.js";


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

    /**
     * Generate audio from the given text using a local Whisper server.
     * @param text {String}
     * @param voice {String}
     * @returns {Promise<TtsAudio|null>}
     */
    async generateAudio(text, voice = 'alloy') {
        if (!this.canGenerateAudio(text)) return null;
        this.isLoading = true;

        try {
            const url = `${conf.VoiceServerAddress}/generate_audio`;
            const payload = { method: 'POST' };
            const params = new URLSearchParams({
                text: text,
                voice: voice
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

    canGenerateAudio(text) {
        return text && this.isVoiceServerConnected && !this.isLoading;
    }
}


const audioManager = new AudioManager();
export default audioManager;