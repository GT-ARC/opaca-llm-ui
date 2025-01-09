"""
FastAPI Server providing HTTP/REST routes for speech-to-text services.
Uses Whisper model for transcription with optimizations for different hardware.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel
import torchaudio
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import io
import os
import numpy as np
from pathlib import Path
import tempfile
import logging

class TTSServer:
    def __init__(self):
        # Set high precision for float32 matmul
        torch.set_float32_matmul_precision("high")

        self.app = FastAPI()
        self.setup_cors()
        self.setup_routes()
        
        # Global variables
        self.model = None
        self.processor = None
        self.pipe = None
        self.device_info = ""
        self.current_transcription = ""

        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def setup_cors(self):
        # Enable CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):
        self.app.on_event("startup")(self.startup_event)
        self.app.get("/device")(self.get_device)
        self.app.post("/transcribe")(self.transcribe_audio)
        self.app.post("/reset")(self.reset_transcription)
        self.app.get("/info")(self.get_info)

    async def startup_event(self):
        # Determine device
        if torch.cuda.is_available():
            device = "cuda"
            self.device_info = f"CUDA GPU: {torch.cuda.get_device_name(0)}"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            device = "mps"
            self.device_info = "Apple Silicon MPS"
        else:
            device = "cpu"
            self.device_info = "CPU"
        
        print(f"Device set to use {device}")
        
        torch_dtype = torch.float16 if device == "cuda" else torch.float32
        model_id = "openai/whisper-large-v3-turbo"
        
        # Load model with optimizations
        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id, 
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
            attn_implementation="sdpa"
        )
        self.model.to(device)
        
        # Enable static cache and compile only for CUDA
        self.model.generation_config.cache_implementation = "static"
        self.model.generation_config.max_new_tokens = 128
        if device == "cuda":
            self.model.forward = torch.compile(self.model.forward, mode="reduce-overhead", fullgraph=True)
        
        # Load processor
        self.processor = AutoProcessor.from_pretrained(model_id)
        
        # Create pipeline with device-specific settings
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=self.model,
            tokenizer=self.processor.tokenizer,
            feature_extractor=self.processor.feature_extractor,
            chunk_length_s=30,  # Process in 30-second chunks
            stride_length_s=5,  # 5-second overlap between chunks
            generate_kwargs={
                "task": "transcribe",
                "language": "german",
                "max_new_tokens": 128,
                "return_timestamps": False
            },
            torch_dtype=torch_dtype,
            device=device,
        )

    async def get_device(self):
        return {"device": self.device_info}

    async def transcribe_audio(
        self,
        file: UploadFile = File(...),
        is_final: bool = Query(False),
        language: str = Query("german", enum=["german", "english"])
    ):
        try:
            # Read the uploaded file
            contents = await file.read()
            audio_data = io.BytesIO(contents)
            
            # Load audio using torchaudio
            waveform, sample_rate = torchaudio.load(audio_data)
            
            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            # Convert to numpy array and prepare input
            audio_array = waveform.squeeze().numpy()
            input_features = {
                "array": audio_array,
                "sampling_rate": sample_rate
            }
            
            # Get transcription
            result = self.pipe(
                input_features,
                batch_size=8,
                generate_kwargs={"task": "transcribe", "language": language}
            )
            
            return {"text": result["text"].strip()}
        except Exception as e:
            self.logger.error(f"Error in transcribe_audio: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def reset_transcription(self):
        self.current_transcription = ""
        return {"status": "reset"}

    async def get_info(self):
        return {
            "device": self.device_info,
            "model": "Whisper Large v3 Turbo",
            "backend": "FastAPI + Transformers"
        }

def create_app():
    server = TTSServer()
    return server.app 