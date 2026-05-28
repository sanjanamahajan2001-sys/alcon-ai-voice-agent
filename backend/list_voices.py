import httpx
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ELEVENLABS_API_KEY")

response = httpx.get(
    "https://api.elevenlabs.io/v1/voices",
    headers={"xi-api-key": api_key}
)

if response.status_code == 200:
    print("\n--- AVAILABLE VOICES FOR YOUR ACCOUNT ---")
    for voice in response.json()['voices']:
        if voice['category'] == 'premade':
            print(f"Name: {voice['name']} | ID: {voice['voice_id']}")
    print("------------------------------------------\n")
else:
    print(f"Error: {response.text}")
