"""
Entry point for the TTS server.
"""

import uvicorn
from .tts_server import create_app

def main():
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=7431)

if __name__ == "__main__":
    main() 