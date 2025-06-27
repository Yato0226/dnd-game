# dnd_ai_game/src/config.py
from pathlib import Path
import os

# --- Core Paths ---
SAVE_DIRECTORY = Path("dnd_ai_sessions")
TRANSCRIPT_FILE = SAVE_DIRECTORY / "full_transcript.xml"
AI_CONFIG_FILE = SAVE_DIRECTORY / "ai_config.xml"

# Ensure the save directory exists
os.makedirs(SAVE_DIRECTORY, exist_ok=True)


# --- AI Model ---
# Default model, can be changed to any Ollama model
MODEL = 'gemma3:4b-it-qat'

# --- Game Defaults ---
DEFAULTS = {
    "campaign": "The Unwritten Tale",
    "name": "Adventurer",
    "race": "Human",
    "class": "Explorer",
    "background": "Traveler from distant lands",
    "gender": "not specified",
    "currentLocation": "The Forgotten Inn"
}
