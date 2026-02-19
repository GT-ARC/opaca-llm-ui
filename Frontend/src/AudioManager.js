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
            const url = `${conf.VoiceServerUrl}/generate_audio`;
            const payload = { method: 'POST' };
            const params = new URLSearchParams({
                text: this._text,
                voice: audioManager._whisperVoice.value,
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

        this._whisperVoice = ref('alloy');
        this._useWhisperTts = ref(true);
        this._useWhisperStt = ref(true);
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

    get useWhisperTts() {
        return this._useWhisperTts.value !== undefined
            ? this._useWhisperTts.value
            : this._useWhisperTts;
    }

    set useWhisperTts(value) {
        if (this._useWhisperTts.value !== undefined) {
            this._useWhisperTts.value = value;
        } else {
            this._useWhisperTts = value;
        }
    }

    get useWhisperStt() {
        return this._useWhisperStt.value !== undefined
            ? this._useWhisperStt.value
            : this._useWhisperStt;
    }

    set useWhisperStt(value) {
        if (this._useWhisperStt.value !== undefined) {
            this._useWhisperStt.value = value;
        } else {
            this._useWhisperStt = value;
        }
    }

    isBackendConfigured() {
        return !! conf.VoiceServerUrl
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
            const response = await fetch(`${conf.VoiceServerUrl}/info`);
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
        if (!text) return null;
        return await this.isVoiceServerConnected && this.useWhisperTts
            ? new WhisperAudio(text)
            : new WebSpeechAudio(text);
    }

    /**
     * Start speech recognition with web speech API.
     * @param onResult Callback that should expect the successfully recognized text as an argument.
     * @param onError Callback that should expect any error messages.
     */
    async startRecognition(onResult, onError) {
        if (!this.isRecognitionSupported()) return;
        if (this.isVoiceServerConnected && this.useWhisperStt) {
            this.startWhisperRecognition(onResult, onError)
        } else {
            this.startWebSpeechRecognition(onResult, onError)
        }
    }

    async startWhisperRecognition(onResult, onError) {



    }

    async startWebSpeechRecognition(onResult, onError) {
        if (this._recognition) {
            this._recognition.abort();
            this._recognition = null;
        }
        try {
            this._recognition = new (window.webkitSpeechRecognition || window.SpeechRecognition)();
        } catch (error) {
            console.error(`Failed to start web speech recognition: ${error}`);
            return;
        }
        this._recognition.lang = Localizer.getLanguageForTTS();
        this._recognition.onresult = async (event) => {
            const recognizedText = Array.from(event.results).map(r => r[0].transcript).join('\n\n');
            onResult(recognizedText);
        };

        this._recognition.onspeechend = () => {
            console.log('Recognition: Speech ended.');
            this.isLoading = false;
        };

        this._recognition.onnomatch = () => {
            onError('Failed to recognize speech.');
        };

        this._recognition.onerror = (error) => {
            onError(`Failed to recognize speech: ${error}`);
        };

        this._recognition.onend = () => {
            console.log('Recognition ended.');
            this.isLoading = false;
        };

        this.isLoading = true;
        this._recognition.start();
    }

    isRecognitionSupported() {
        return this.isVoiceServerConnected
            || (this.isWebSpeechSupported()
            && this._isGoogleChrome()
            && this._isSecureConnection());
    }

    isWebSpeechSupported() {
        return ('SpeechRecognition' in window) || ('webkitSpeechRecognition' in window);
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


    async setupRecording() {
        try {
            this.audioContext = new AudioContext();

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

            this.mediaRecorder = new MediaRecorder(stream);
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.start(100);
        } catch (error) {
            console.error('Error setting up recording:', error);
        }
    }

    detectSilence() {
        // from Chat-GPT...
        let speaking = false;
        let silenceStart = null;
        const SILENCE_MS = 800; // treat as end‑of‑speech after 0.8 s silence

        audioContext.createScriptProcessor(4096, 1, 1).onaudioprocess = e => {
            const data = e.inputBuffer.getChannelData(0);
            const rms = Math.sqrt(data.reduce((s, x) => s + x*x, 0) / data.length);
            const isSpeech = rms > 0.02; // threshold – tune per environment

            if (isSpeech) {
                speaking = true;
                silenceStart = null;
                // push chunk to Whisper
            } else if (speaking) {
                if (!silenceStart) silenceStart = Date.now();
                else if (Date.now() - silenceStart > SILENCE_MS) {
                    speaking = false;
                    // signal end‑of‑speech → stop recording, send final chunk
                }
            }
        };
    }

    async stopRecording() {
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
            const result = await this.processAudioChunks();
        }
    }

    async processAudioChunks() {
        if (this.audioChunks.length === 0) return '';

        const blob = new Blob(this.audioChunks, { type: 'audio/webm' });
        const audioContext = new AudioContext();
        const audioData = await blob.arrayBuffer();
        const audioBuffer = await audioContext.decodeAudioData(audioData);
        const wavBlob = await this.convertToWav(audioBuffer);
        
        const formData = new FormData();
        formData.append('file', new File([wavBlob], 'audio.wav', { type: 'audio/wav' }));

        try {
            const response = await fetch(`${this.getConfig().VoiceServerUrl}/transcribe?is_final=true&language=${this.language}`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            return result.text || '';
        } catch (error) {
            console.error('Error processing audio:', error);
            throw error;
        } finally {
            audioContext.close();
        }
    }

    convertToWav(audioBuffer) {
        const numOfChannels = audioBuffer.numberOfChannels;
        const length = audioBuffer.length * numOfChannels * 2;
        const buffer = new ArrayBuffer(44 + length);
        const view = new DataView(buffer);
        
        function writeString(view, offset, string) {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        }

        // Write WAV header
        writeString(view, 0, 'RIFF');
        view.setUint32(4, 36 + length, true);
        writeString(view, 8, 'WAVE');
        writeString(view, 12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, numOfChannels, true);
        view.setUint32(24, audioBuffer.sampleRate, true);
        view.setUint32(28, audioBuffer.sampleRate * numOfChannels * 2, true);
        view.setUint16(32, numOfChannels * 2, true);
        view.setUint16(34, 16, true);
        writeString(view, 36, 'data');
        view.setUint32(40, length, true);

        // Write audio data
        const data = new Float32Array(audioBuffer.length * numOfChannels);
        let offset = 44;

        for (let i = 0; i < audioBuffer.numberOfChannels; i++) {
            data.set(audioBuffer.getChannelData(i), i * audioBuffer.length);
        }

        for (let i = 0; i < data.length; i++) {
            const sample = Math.max(-1, Math.min(1, data[i]));
            view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
            offset += 2;
        }

        return new Blob([buffer], { type: 'audio/wav' });
    }

}


const audioManager = new AudioManager();
export default audioManager;