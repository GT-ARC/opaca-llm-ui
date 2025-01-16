"""
FastAPI Server providing HTTP/REST routes for speech-to-text services.
Uses Whisper model for transcription with optimizations for different hardware.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel
import torchaudio
import torchaudio.transforms as T
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import io
import logging

def is_flash_attention_2_installed() -> bool:
    """
    Attempt to import flash-attn. If successful, return True.
    Otherwise return False.
    """
    try:
        import flash_attn  # noqa
        return True
    except ImportError:
        return False

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
            device = "cuda:0"
            self.device_info = f"CUDA GPU: {torch.cuda.get_device_name(0)}"
            torch_dtype = torch.float16
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            device = "mps"
            self.device_info = "Apple Silicon MPS"
            torch_dtype = torch.float32
        else:
            device = "cpu"
            self.device_info = "CPU"
            torch_dtype = torch.float32
        
        print(f"Device set to use {device}")

        model_id = "openai/whisper-large-v3-turbo"
        
        # Decide on the attention implementation
        if device.startswith("cuda") and is_flash_attention_2_installed():
            attn_impl = "flash_attention_2"
            print("Using Flash Attention 2.")
        else:
            attn_impl = "sdpa"
            print("Falling back to SDPA.")
        
        # Load model with proper configuration
        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
            attn_implementation=attn_impl,
        ).to(device)

        # Load processor
        self.processor = AutoProcessor.from_pretrained(model_id)
        
        # Configure generation settings
        self.model.generation_config.cache_implementation = "static"
        self.model.generation_config.max_new_tokens = 256
        self.model.generation_config.max_batch_size = 8  # Avoid batch_size deprecation warning

        # Create pipeline with proper configuration
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=self.model,
            tokenizer=self.processor.tokenizer,
            feature_extractor=self.processor.feature_extractor,
            torch_dtype=torch_dtype,
            device=device,
            chunk_length_s=30,
            stride_length_s=5,
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
            
            # Load audio with torchaudio
            waveform, sample_rate = torchaudio.load(audio_data)
            
            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            # Resample to 16kHz if needed
            if sample_rate != 16000:
                resampler = T.Resample(sample_rate, 16000)
                waveform = resampler(waveform)
                sample_rate = 16000
            
            # Convert to a NumPy array
            audio_array = waveform.squeeze().numpy()

            # Let pipeline handle the chunking and feature extraction
            with sdpa_kernel(SDPBackend.MATH):
                result = self.pipe(
                    {"raw": audio_array, "sampling_rate": 16000},
                    generate_kwargs={
                        "task": "transcribe",
                        "language": language,
                        "return_timestamps": False,
                    }
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