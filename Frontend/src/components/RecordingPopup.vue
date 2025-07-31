<template>
    <div v-if="show" 
         class="recording-popup-overlay fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center"
         @keydown.esc="closePopup" 
         tabindex="0"
         ref="modal">
        <div class="w-full max-w-2xl flex flex-col items-center space-y-8 p-4">
            <div class="w-full bg-zinc-800 backdrop-blur-md rounded-[2rem] p-8 relative">
                <!-- Close Button -->
                <button 
                    @click="closePopup"
                    class="absolute -top-3 -right-3 p-2 rounded-full bg-red-500 hover:bg-red-600 transition-all duration-200 flex items-center justify-center z-50 w-8 h-8 border-0 shadow-lg"
                    aria-label="Close"
                >
                    <i class="fa fa-times text-white text-lg"></i>
                </button>

                <!-- Title Section -->
                <div class="text-center">
                    <h1 class="text-4xl font-bold" style="background: linear-gradient(to right, #60a5fa, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                        Superfast Whisper Voice
                    </h1>
                </div>

                <canvas 
                    id="visualizer" 
                    class="w-full h-32 bg-zinc-900 rounded-[1.5rem] mt-6"
                    width="600"
                    height="128"
                ></canvas>
                
                <div class="flex gap-3 mt-6">
                    <button
                        @click="stopRecording(false)"
                        class="flex-1 py-2 px-4 rounded-[1rem] text-base font-semibold transition-all duration-300 flex items-center justify-center gap-2 stop-recording-btn"
                    >
                        <i class="fa fa-stop text-lg"></i>
                        <span>Stop Recording</span>
                        <span class="text-xs opacity-60">(Shift+Enter)</span>
                    </button>

                    <button
                        @click="stopRecording(true)"
                        class="flex-1 py-2 px-4 rounded-[1rem] text-base font-semibold transition-all duration-300 flex items-center justify-center gap-2 border-0 stop-send-btn"
                    >
                        <i class="fa fa-paper-plane text-lg"></i>
                        <span>Stop & Send</span>
                        <span class="text-xs opacity-60">(Enter)</span>
                    </button>
                </div>

                <div v-if="isProcessing" class="text-center text-zinc-400 mt-4">
                    Processing audio...
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import conf from '../../config.js'

const CHUNK_SIZE = 1920000;
const MAX_PARALLEL_CHUNKS = 3;
const MIN_DECIBELS = -45;

export default {
    name: 'RecordingPopup',
    props: {
        show: Boolean,
        language: String
    },
    data() {
        return {
            mediaRecorder: null,
            audioContext: null,
            analyser: null,
            dataArray: null,
            canvasCtx: null,
            animationFrame: null,
            audioChunks: [],
            isProcessing: false,
            processingChunks: 0,
            animationStartTime: null,
            morphDuration: 300
        }
    },
    watch: {
        async show(newVal) {
            if (newVal) {
                await this.$nextTick();
                this.$refs.modal.focus();
                await this.setupRecording();
                // Add keyboard event listener
                document.addEventListener('keydown', this.handleKeydown);
            } else {
                this.cleanup();
                // Remove keyboard event listener
                document.removeEventListener('keydown', this.handleKeydown);
            }
        }
    },
    methods: {
        getConfig() {
            return conf;
        },

        handleKeydown(e) {
            if (this.show && !this.isProcessing) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    if (e.shiftKey) {
                        this.stopRecording(false);
                    } else {
                        this.stopRecording(true);
                    }
                }
            }
        },

        async stopRecording(shouldSend = false) {
            if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
                this.mediaRecorder.stop();
                this.isProcessing = true;
                this.animationStartTime = null;
                requestAnimationFrame(this.drawProcessingAnimation);

                try {
                    const result = await this.processAudioChunks();
                    this.$emit('transcription-complete', result);
                    if (shouldSend) {
                        this.$emit('send-message', result);
                    }
                } catch (error) {
                    console.error('Error processing audio:', error);
                    this.$emit('error', error);
                } finally {
                    this.isProcessing = false;
                    this.audioChunks = [];
                    this.$emit('update:show', false);
                }
            }
        },

        drawProcessingAnimation(timestamp) {
            if (!this.canvasCtx) return;
            if (!this.animationStartTime) this.animationStartTime = timestamp;
            
            const canvas = this.canvasCtx.canvas;
            const width = canvas.width;
            const height = canvas.height;
            const centerX = width / 2;
            const centerY = height / 2;
            
            // Clear canvas with color scheme aware background
            const isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
            this.canvasCtx.fillStyle = isDarkMode ? 'rgba(24, 24, 27, 1)' : 'rgba(250, 250, 250, 0.8)';
            this.canvasCtx.fillRect(0, 0, width, height);
            
            // Create gradient with color scheme awareness
            const gradient = this.canvasCtx.createLinearGradient(0, 0, width, 0);
            gradient.addColorStop(0, isDarkMode ? '#818cf8' : '#2563eb');
            gradient.addColorStop(1, isDarkMode ? '#c084fc' : '#7c3aed');
            
            const progress = Math.min((timestamp - this.animationStartTime) / this.morphDuration, 1);
            
            this.canvasCtx.strokeStyle = gradient;
            this.canvasCtx.lineWidth = 2;
            
            if (progress < 1) {
                // Draw the shrinking line
                const lineLength = width * (1 - progress);
                const startX = centerX - (lineLength / 2);
                const endX = centerX + (lineLength / 2);
                
                this.canvasCtx.beginPath();
                this.canvasCtx.moveTo(startX, centerY);
                this.canvasCtx.lineTo(endX, centerY);
                this.canvasCtx.stroke();
            } else {
                // Draw loading dots in a wave pattern
                const dotRadius = 3;
                const dotSpacing = 12;
                const time = timestamp / 150;
                
                for (let i = 0; i < 3; i++) {
                    const x = centerX + (i - 1) * dotSpacing;
                    const y = centerY + Math.sin(time + i * 0.5) * 6;
                    
                    this.canvasCtx.beginPath();
                    this.canvasCtx.arc(x, y, dotRadius, 0, 2 * Math.PI);
                    this.canvasCtx.fillStyle = gradient;
                    this.canvasCtx.fill();
                }
            }
            
            // Add glow effect with color scheme awareness
            this.canvasCtx.shadowBlur = 15;
            this.canvasCtx.shadowColor = isDarkMode ? '#818cf8' : '#2563eb';
            
            if (this.isProcessing) {
                requestAnimationFrame(this.drawProcessingAnimation);
            } else {
                this.animationStartTime = null;
            }
        },

        cleanup() {
            if (this.animationFrame) {
                cancelAnimationFrame(this.animationFrame);
                this.animationFrame = null;
            }
            if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
                this.mediaRecorder.stop();
            }
            if (this.audioContext) {
                this.audioContext.close();
            }
            // Stop all microphone tracks
            if (this.mediaRecorder && this.mediaRecorder.stream) {
                this.mediaRecorder.stream.getTracks().forEach(track => {
                    track.stop();
                });
            }
            this.audioChunks = [];
            this.isProcessing = false;
            this.canvasCtx = null;
            this.analyser = null;
            this.dataArray = null;
            this.mediaRecorder = null;
        },

        async setupRecording() {
            try {
                // Wait for the next tick to ensure the canvas is mounted
                await this.$nextTick();
                
                this.audioContext = new AudioContext();
                this.analyser = this.audioContext.createAnalyser();
                this.analyser.fftSize = 4096;
                this.analyser.minDecibels = MIN_DECIBELS;
                this.analyser.maxDecibels = -10;
                this.analyser.smoothingTimeConstant = 0.85;

                const canvas = document.getElementById('visualizer');
                if (!canvas) {
                    throw new Error('Canvas element not found');
                }

                // Get canvas dimensions safely
                const rect = canvas.getBoundingClientRect();
                if (!rect || rect.width === 0) {
                    throw new Error('Invalid canvas dimensions');
                }

                canvas.width = rect.width || 600; // Fallback width if rect.width is 0
                canvas.height = rect.height || 128; // Fallback height if rect.height is 0
                
                this.canvasCtx = canvas.getContext('2d', { alpha: false });
                if (!this.canvasCtx) {
                    throw new Error('Failed to get canvas context');
                }

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

                const source = this.audioContext.createMediaStreamSource(stream);
                source.connect(this.analyser);

                const bufferLength = this.analyser.frequencyBinCount;
                this.dataArray = new Uint8Array(bufferLength);

                this.mediaRecorder = new MediaRecorder(stream);
                this.mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        this.audioChunks.push(event.data);
                    }
                };

                this.mediaRecorder.start(100);
                this.draw();
            } catch (error) {
                console.error('Error setting up recording:', error);
                this.cleanup();
                this.$emit('error', error);
                this.$emit('update:show', false); // Close the popup on error
            }
        },

        draw() {
            if (!this.show || !this.canvasCtx) return;

            this.animationFrame = requestAnimationFrame(this.draw);
            
            try {
                this.analyser.getByteTimeDomainData(this.dataArray);

                const canvas = this.canvasCtx.canvas;
                const width = canvas.width;
                const height = canvas.height;

                // Clear canvas with color scheme aware background
                const isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
                this.canvasCtx.fillStyle = isDarkMode ? 'rgba(24, 24, 27, 1)' : 'rgba(250, 250, 250, 0.8)';
                this.canvasCtx.fillRect(0, 0, width, height);

                // Create gradient
                const gradient = this.canvasCtx.createLinearGradient(0, 0, width, 0);
                gradient.addColorStop(0, isDarkMode ? '#818cf8' : '#2563eb');
                gradient.addColorStop(1, isDarkMode ? '#c084fc' : '#7c3aed');

                this.canvasCtx.lineWidth = 2;
                this.canvasCtx.strokeStyle = gradient;
                this.canvasCtx.beginPath();

                const sliceWidth = width / (this.dataArray.length - 1);
                let x = 0;
                const scale = 1.5;

                for (let i = 0; i < this.dataArray.length; i++) {
                    const v = (this.dataArray[i] / 128.0 - 1) * scale;
                    const y = (height / 2) * (1 + v);

                    if (i === 0) {
                        this.canvasCtx.moveTo(x, y);
                    } else {
                        this.canvasCtx.lineTo(x, y);
                    }

                    x += sliceWidth;
                }

                this.canvasCtx.stroke();
                this.canvasCtx.shadowBlur = 15;
                this.canvasCtx.shadowColor = isDarkMode ? '#818cf8' : '#2563eb';
            } catch (error) {
                console.error('Error drawing to canvas:', error);
                cancelAnimationFrame(this.animationFrame);
            }
        },

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
        },

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
        },

        closePopup() {
            this.cleanup();
            this.$emit('update:show', false);
        }
    },
    mounted() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.show) {
                this.closePopup();
            }
        });
    },
    beforeDestroy() {
        document.removeEventListener('keydown', this.handleKeydown);
        document.removeEventListener('keydown', this.closePopup);
        this.cleanup();
    }
}
</script>

<style scoped>
.recording-popup-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 9999;
    background-color: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
}

#sidebar-content {
    position: relative;
    z-index: 999;
}

.sidebar-menu {
    position: relative;
    z-index: 999;
}

.fixed {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
}

.backdrop-blur-sm {
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
}

/* Base styles */
.bg-zinc-800\/50 {
    background-color: rgba(39, 39, 42, 0.5);
}

.bg-zinc-900\/50 {
    background-color: rgba(24, 24, 27, 0.5);
}

/* Light mode */
@media (prefers-color-scheme: light) {
    .bg-zinc-800\/50 {
        background-color: rgba(242, 242, 242, 0.95) !important;
    }

    .bg-zinc-900\/50 {
        background-color: rgba(255, 255, 255, 0.8) !important;
    }

    .stop-recording-btn {
        background-color: rgba(240, 240, 240, 0.9) !important;
        color: #1f2937 !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
    }

    .stop-recording-btn:hover {
        background-color: rgba(230, 230, 230, 0.9) !important;
    }

    .stop-send-btn {
        background: linear-gradient(to right, #93c5fd, #c4b5fd) !important;
        color: #1f2937 !important;
    }

    .stop-send-btn:hover {
        background: linear-gradient(to right, #60a5fa, #a78bfa) !important;
    }

    .stop-recording-btn i,
    .stop-recording-btn span {
        color: #1f2937 !important;
    }

    .stop-send-btn i,
    .stop-send-btn span {
        color: #1f2937 !important;
    }
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
    .bg-zinc-800\/50 {
        background-color: rgba(39, 39, 42, 0.7) !important;
    }

    .bg-zinc-900\/50 {
        background-color: rgba(24, 24, 27, 0.8) !important;
    }

    .stop-recording-btn {
        background-color: rgba(39, 39, 42, 0.8) !important;
        color: white !important;
        border: 1px solid rgba(63, 63, 70, 0.5) !important;
    }

    .stop-recording-btn:hover {
        background-color: rgba(63, 63, 70, 0.9) !important;
    }

    .stop-send-btn {
        background: linear-gradient(to right, #60a5fa, #a855f7) !important;
        color: white !important;
    }

    .stop-send-btn:hover {
        background: linear-gradient(to right, #3b82f6, #9333ea) !important;
    }

    .stop-recording-btn i,
    .stop-recording-btn span {
        color: white !important;
    }

    .stop-send-btn i,
    .stop-send-btn span {
        color: white !important;
    }

    .text-zinc-400 {
        color: rgba(255, 255, 255, 0.6) !important;
    }
}

.bg-zinc-900\/50 {
    background-color: rgba(245, 245, 245, 0.9);
}

.backdrop-blur-sm {
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
}

.backdrop-blur-md {
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
}

h1[style*="background: linear-gradient"] {
    background: linear-gradient(to right, #60a5fa, #a855f7) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}

button.bg-zinc-900 {
    background-color: rgba(240, 240, 240, 0.9) !important;
    color: #1f2937 !important;
    border-color: rgba(0, 0, 0, 0.1) !important;
}

button.bg-zinc-900:hover {
    background-color: rgba(230, 230, 230, 0.9) !important;
}

button[style*="background: linear-gradient"] {
    background: linear-gradient(to right, #93c5fd, #c4b5fd) !important;
    color: #1f2937 !important;
}

button[style*="background: linear-gradient"]:hover {
    background: linear-gradient(to right, #60a5fa, #a78bfa) !important;
    color: #1f2937 !important;
}

.text-zinc-400 {
    color: rgb(75, 85, 99) !important;
}

.main-recording-interface::before {
    background: linear-gradient(to right, rgba(96, 165, 250, 0.2), rgba(168, 85, 247, 0.2));
}

.flex {
    display: flex;
}

.items-center {
    align-items: center;
}

.justify-center {
    justify-content: center;
}

.z-50 {
    z-index: 50;
}

.space-y-8 > * + * {
    margin-top: 2rem;
}

.space-y-6 > * + * {
    margin-top: 1.5rem;
}

.space-y-4 > * + * {
    margin-top: 1rem;
}

.w-full {
    width: 100%;
}

.max-w-2xl {
    max-width: 42rem;
}

.h-32 {
    height: 8rem;
}

.rounded-2xl {
    border-radius: 1rem;
}

.rounded-3xl {
    border-radius: 1.5rem;
}

.bg-zinc-900\/50 {
    background-color: rgba(24, 24, 27, 0.5);
}

.bg-zinc-800\/50 {
    background-color: rgba(39, 39, 42, 0.5);
}

.bg-rose-500\/90 {
    background-color: rgba(244, 63, 94, 0.9);
}

.hover\:bg-rose-600:hover {
    background-color: rgb(225, 29, 72);
}

.text-zinc-400 {
    color: rgb(161, 161, 170);
}

.text-white {
    color: white;
}

.p-8 {
    padding: 2rem;
}

.p-4 {
    padding: 1rem;
}

.py-4 {
    padding-top: 1rem;
    padding-bottom: 1rem;
}

.px-6 {
    padding-left: 1.5rem;
    padding-right: 1.5rem;
}

.text-lg {
    font-size: 1.125rem;
}

.text-4xl {
    font-size: 2.25rem;
}

.font-semibold {
    font-weight: 600;
}

.font-bold {
    font-weight: 700;
}

.shadow-xl {
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.border {
    border-width: 1px;
}

.border-zinc-700\/50 {
    border-color: rgba(63, 63, 70, 0.5);
}

.transition-all {
    transition-property: all;
    transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
    transition-duration: 300ms;
}

.gap-3 {
    gap: 0.75rem;
}

button {
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.rounded-\[2rem\] {
    border-radius: 2rem;
}

.rounded-\[1\.5rem\] {
    border-radius: 1.5rem;
}

.rounded-\[1\.2rem\] {
    border-radius: 1.2rem;
}

.from-rose-500\/90 {
    --tw-gradient-from: rgba(244, 63, 94, 0.9);
    --tw-gradient-stops: var(--tw-gradient-from), var(--tw-gradient-to, rgba(244, 63, 94, 0));
}

.to-pink-500\/90 {
    --tw-gradient-to: rgba(236, 72, 153, 0.9);
}

.hover\:from-rose-600:hover {
    --tw-gradient-from: rgb(225, 29, 72);
    --tw-gradient-stops: var(--tw-gradient-from), var(--tw-gradient-to, rgb(225, 29, 72, 0));
}

.hover\:to-pink-600:hover {
    --tw-gradient-to: rgb(219, 39, 119);
}

.absolute {
    position: absolute;
}

.-top-16 {
    top: -4rem;
}

.top-2 {
    top: 0.5rem;
}

.right-2 {
    right: 0.5rem;
}

.relative {
    position: relative;
}

button {
    text-shadow: none;
}

.hover\:text-red-400:hover {
    color: rgb(248, 113, 113);
}

.text-red-500 {
    color: rgb(239, 68, 68);
}

.hover\:bg-red-500\/20:hover {
    background-color: rgba(239, 68, 68, 0.2);
}

.from-indigo-500\/90 {
    --tw-gradient-from: rgba(99, 102, 241, 0.9);
    --tw-gradient-stops: var(--tw-gradient-from), var(--tw-gradient-to, rgba(99, 102, 241, 0));
}

.to-purple-500\/90 {
    --tw-gradient-to: rgba(168, 85, 247, 0.9);
}

.hover\:from-indigo-600:hover {
    --tw-gradient-from: rgb(79, 70, 229);
    --tw-gradient-stops: var(--tw-gradient-from), var(--tw-gradient-to, rgb(79, 70, 229, 0));
}

.hover\:to-purple-600:hover {
    --tw-gradient-to: rgb(147, 51, 234);
}

.border-indigo-500\/20 {
    border-color: rgba(99, 102, 241, 0.2);
}

/* Simplified SVG handling */
svg {
    fill: none;
}

svg path[fill] {
    fill: currentColor;
}

svg path[stroke] {
    stroke: currentColor;
    fill: none;
}

/* Remove all the duplicate SVG style rules and keep only these essential ones */

.w-8 {
    width: 2rem;
}

.h-8 {
    height: 2rem;
}

.bg-red-500 {
    background-color: rgb(239, 68, 68);
}

.hover\:bg-red-600:hover {
    background-color: rgb(220, 38, 38);
}

.text-lg {
    font-size: 1.125rem;
    line-height: 1.75rem;
}

/* Override button hover states */
button[style*="background: linear-gradient"]:hover {
    background: linear-gradient(to right, #3b82f6, #9333ea) !important;
}

.border-0 {
    border: 0;
}

.rounded-full {
    border-radius: 9999px;
}

.rounded-\[1rem\] {
    border-radius: 1rem;
}

.rounded-\[1\.5rem\] {
    border-radius: 1.5rem;
}

.rounded-\[2rem\] {
    border-radius: 2rem;
}

/* Override button hover states */
button[style*="background: linear-gradient"]:hover {
    background: linear-gradient(to right, #3b82f6, #9333ea) !important;
}

/* Gradient border fix */
.main-recording-interface {
    position: relative;
    background-clip: padding-box;
    border: 1px solid transparent;
}

.main-recording-interface::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 2rem;
    padding: 1px;
    background: linear-gradient(to right, rgba(96, 165, 250, 0.4), rgba(168, 85, 247, 0.4));
    mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    mask-composite: exclude;
    -webkit-mask-composite: source-out;
    pointer-events: none;
    z-index: -1;
}

/* Base styles */
.bg-black\/70 {
    background-color: rgba(0, 0, 0, 0.7);
}

/* Light mode */
@media (prefers-color-scheme: light) {
    .bg-zinc-800 {
        background-color: rgb(250, 250, 250) !important;
    }

    .bg-zinc-900 {
        background-color: rgb(240, 240, 240) !important;
    }

    .stop-recording-btn {
        background-color: rgb(235, 235, 235) !important;
        color: #1f2937 !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
    }

    .stop-recording-btn:hover {
        background-color: rgb(225, 225, 225) !important;
    }

    .stop-send-btn {
        background: linear-gradient(to right, #93c5fd, #c4b5fd) !important;
        color: #1f2937 !important;
    }

    .stop-send-btn:hover {
        background: linear-gradient(to right, #60a5fa, #a78bfa) !important;
    }

    .stop-recording-btn i,
    .stop-recording-btn span {
        color: #1f2937 !important;
    }

    .stop-send-btn i,
    .stop-send-btn span {
        color: #1f2937 !important;
    }
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
    .bg-zinc-800 {
        background-color: rgb(39, 39, 42) !important;
    }

    .bg-zinc-900 {
        background-color: rgb(24, 24, 27) !important;
    }

    .stop-recording-btn {
        background-color: rgb(24, 24, 27) !important;
        color: white !important;
        border: 1px solid rgba(63, 63, 70, 0.5) !important;
    }

    .stop-recording-btn:hover {
        background-color: rgb(39, 39, 42) !important;
    }

    .stop-send-btn {
        background: linear-gradient(to right, #60a5fa, #a855f7) !important;
        color: white !important;
    }

    .stop-send-btn:hover {
        background: linear-gradient(to right, #3b82f6, #9333ea) !important;
    }

    .stop-recording-btn i,
    .stop-recording-btn span {
        color: white !important;
    }

    .stop-send-btn i,
    .stop-send-btn span {
        color: white !important;
    }

    .text-zinc-400 {
        color: rgba(255, 255, 255, 0.6) !important;
    }
}
</style> 