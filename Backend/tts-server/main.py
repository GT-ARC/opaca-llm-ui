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

# Set high precision for float32 matmul
torch.set_float32_matmul_precision("high")

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
model = None
processor = None
pipe = None
device_info = ""
current_transcription = ""

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    global model, processor, pipe, device_info
    
    # Determine device
    if torch.cuda.is_available():
        device = "cuda"
        device_info = f"CUDA GPU: {torch.cuda.get_device_name(0)}"
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = "mps"
        device_info = "Apple Silicon MPS"
    else:
        device = "cpu"
        device_info = "CPU"
    
    print(f"Device set to use {device}")
    
    torch_dtype = torch.float16 if device == "cuda" else torch.float32
    model_id = "openai/whisper-large-v3-turbo"
    
    # Load model with optimizations
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id, 
        torch_dtype=torch_dtype,
        low_cpu_mem_usage=True,
        use_safetensors=True,
        attn_implementation="sdpa"
    )
    model.to(device)
    
    # Enable static cache and compile only for CUDA
    model.generation_config.cache_implementation = "static"
    model.generation_config.max_new_tokens = 128
    if device == "cuda":
        model.forward = torch.compile(model.forward, mode="reduce-overhead", fullgraph=True)
    
    # Load processor
    processor = AutoProcessor.from_pretrained(model_id)
    
    # Create pipeline with device-specific settings
    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
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

@app.get("/device")
async def get_device():
    return {"device": device_info}

@app.post("/transcribe")
async def transcribe_audio(
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
        result = pipe(
            input_features,
            batch_size=8,
            generate_kwargs={"task": "transcribe", "language": language}
        )
        
        return {"text": result["text"].strip()}
    except Exception as e:
        logger.error(f"Error in transcribe_audio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset")
async def reset_transcription():
    global current_transcription
    current_transcription = ""
    return {"status": "reset"}

@app.get("/info")
async def get_info():
    return {
        "device": device_info,
        "model": "Whisper Large v3 Turbo",
        "backend": "FastAPI + Transformers"
    } 