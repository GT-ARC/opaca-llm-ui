"""
FastAPI Server providing HTTP/REST routes for speech-to-text services.
Uses Whisper model for transcription with optimizations for different hardware.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel
import torchaudio
import torchaudio.transforms as T
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import io
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
from pydub import AudioSegment
from tqdm import tqdm
from openai import OpenAI
import re
from contextlib import asynccontextmanager

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    server = app.state.server
    await server.startup_event()
    yield
    # Shutdown (if needed)

class TTSServer:
    def __init__(self):
        # Set high precision for float32 matmul
        torch.set_float32_matmul_precision("high")

        self.app = FastAPI(lifespan=lifespan)
        self.app.state.server = self  # Store server instance in app state
        self.setup_cors()
        self.setup_routes()
        
        # Global variables
        self.model = None
        self.processor = None
        self.pipe = None
        self.device_info = ""
        self.current_transcription = ""

        # Set up logging with custom configuration
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Filter out unwanted logs
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Create temp directory for audio files
        self.temp_dir = Path(tempfile.gettempdir()) / "tts_audio"
        self.temp_dir.mkdir(exist_ok=True)

    def setup_cors(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):
        self.app.get("/device")(self.get_device)
        self.app.post("/transcribe")(self.transcribe_audio)
        self.app.post("/reset")(self.reset_transcription)
        self.app.get("/info")(self.get_info)
        self.app.post("/generate_audio")(self.generate_audio)

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

    def chunk_text(self, text: str, target_words: int = 60) -> list[tuple[int, str]]:
        """Split text into chunks intelligently, handling both sentences and structured content."""
        
        def count_words(text: str) -> int:
            return len(text.split())
        
        def split_sentences(text: str) -> list[str]:
            # Split on sentence endings (.!?) followed by whitespace or newline
            sentences = re.split(r'(?<=[.!?])\s+', text.strip())
            return [s for s in sentences if s]  # Remove empty strings
        
        def split_blocks(text: str) -> list[str]:
            # Split on multiple newlines (preserves single newlines within blocks)
            blocks = re.split(r'\n\s*\n', text.strip())
            return [b for b in blocks if b]
        
        chunks = []
        chunk_index = 0
        
        # First split into major blocks (handles structured content)
        blocks = split_blocks(text)
        
        for block in blocks:
            current_chunk = []
            current_words = 0
            
            # If block contains bullet points or is structured (contains newlines)
            if '\n' in block:
                # Treat each line as a complete unit
                lines = block.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    line_words = count_words(line)
                    if current_words + line_words > target_words and current_chunk:
                        # Save current chunk and start new one
                        chunks.append((chunk_index, '\n'.join(current_chunk)))
                        chunk_index += 1
                        current_chunk = [line]
                        current_words = line_words
                    else:
                        current_chunk.append(line)
                        current_words += line_words
            else:
                # Regular text block - split into sentences
                sentences = split_sentences(block)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                        
                    sentence_words = count_words(sentence)
                    if current_words + sentence_words > target_words and current_chunk:
                        # Save current chunk and start new one
                        chunks.append((chunk_index, ' '.join(current_chunk)))
                        chunk_index += 1
                        current_chunk = [sentence]
                        current_words = sentence_words
                    else:
                        current_chunk.append(sentence)
                        current_words += sentence_words
            
            # Add remaining chunk if any
            if current_chunk:
                if '\n' in block:
                    chunks.append((chunk_index, '\n'.join(current_chunk)))
                else:
                    chunks.append((chunk_index, ' '.join(current_chunk)))
                chunk_index += 1
        
        return chunks

    def process_chunk_sync(self, chunk_data: tuple[int, str], voice: str) -> tuple[int, Path]:
        """Synchronous version of process_chunk for thread pool."""
        chunk_index, text = chunk_data
        output_path = self.temp_dir / f"chunk_{chunk_index}.mp3"
        
        try:
            response = self.openai_client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return chunk_index, output_path
                
        except Exception as e:
            self.logger.error(f"Error processing chunk {chunk_index}: {str(e)}")
            raise

    async def generate_audio(
        self,
        text: str = Query(..., description="Text to convert to speech"),
        voice: str = Query("alloy", description="Voice to use for TTS"),
    ):
        try:
            chunks = self.chunk_text(text)
            total_chunks = len(chunks)
            
            self.logger.info(f"Processing {total_chunks} chunks in parallel...")
            
            # Process chunks in parallel using thread pool
            chunk_files = []
            with ThreadPoolExecutor(max_workers=24) as executor:
                with tqdm(total=total_chunks, desc="Generating audio", ncols=80) as progress_bar:
                    futures = [
                        executor.submit(self.process_chunk_sync, chunk, voice)
                        for chunk in chunks
                    ]
                    
                    for future in futures:
                        chunk_index, file_path = future.result()
                        chunk_files.append((chunk_index, file_path))
                        progress_bar.update(1)
            
            # Sort chunks by index
            chunk_files.sort(key=lambda x: x[0])
            
            # Merge audio files
            combined = AudioSegment.empty()
            silence = AudioSegment.silent(duration=500)  # 0.5s silence
            
            for i, (_, file_path) in enumerate(chunk_files):
                audio_segment = AudioSegment.from_mp3(file_path)
                combined += audio_segment
                
                # Add silence between chunks (except after the last chunk)
                if i < len(chunk_files) - 1:
                    combined += silence
            
            # Save final audio
            output_path = self.temp_dir / "final_output.mp3"
            combined.export(output_path, format="mp3")
            
            # Read the file and return it
            with open(output_path, "rb") as f:
                audio_data = f.read()
            
            # Cleanup temporary files
            for _, file_path in chunk_files:
                file_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)
            
            self.logger.info("Audio generation completed successfully")
            return Response(
                content=audio_data,
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": "attachment; filename=generated_audio.mp3"
                }
            )

        except Exception as e:
            self.logger.error(f"Error in generate_audio: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

def create_app():
    server = TTSServer()
    return server.app 