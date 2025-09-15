import os
from util import BackendTestClient

# SETUP

client = BackendTestClient("http://localhost:3001")
if not client.alive():
    print("Make sure OPACA LLM Backend is running!")
    exit(1)

"""
test-query each model
with and without history
get chats, delete chat, get chat
get history
change config, get config, reset config
"""

def test_connect():
    ip = os.getenv("VITE_PLATFORM_BASE_URL")
    print("IP FROM ENV:", ip)
    res = client.connect(ip)
    assert res == 200, "Failed to connect; OPACA RP not running?"

