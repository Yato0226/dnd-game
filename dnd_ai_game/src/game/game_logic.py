# dnd_ai_game/src/game/game_logic.py
import random
import re
import json
from datetime import date, datetime
from enum import Enum

from dnd_ai_game.src.config import DEFAULTS, SAVE_DIRECTORY
from dnd_ai_game.src.utils.system_utils import is_ollama_running, start_ollama, stop_ollama
from dnd_ai_game.src.utils.data_manager import (
    load_game_state,
    save_game_state,
    get_latest_save_file,
    _get_next_session_filename,
    append_to_transcript
)
from dnd_ai_game.src.ai.rag import RAG
from dnd_ai_game.src.ai.ai_logic import (
    get_ai_narrative,
    get_ai_event,
    extract_keywords_from_ai_output,
    extract_skill_from_ai_output,
    parse_and_apply_ai_config_command
)

try:
    import ollama
except ImportError:
    ollama = None

class ItemRarity(Enum):
    COMMON = "Common"
    UNCOMMON = "Uncommon"
    RARE = "Rare"
    EPIC = "Epic"
    LEGENDARY = "Legendary"
    UNIQUE = "Unique"
    MYTHIC = "Mythic"
    EXOTIC = "Exotic"
    RELIC = "Relic"
    DIVINE = "Divine"

def initialize_new_game():
    """Guides the user through creating a new character and returns a new game_state."""
    print("\n--- Starting a New Adventure ---")
    player_name = input(f"Enter your character's name [{DEFAULTS['name']}]: ") or DEFAULTS["name"]
    player_race = input(f"Race [{DEFAULTS['race']}]: ") or DEFAULTS["race"]
    player_class = input(f"Class [{DEFAULTS['class']}]: ") or DEFAULTS["class"]
    player_gender = input("Gender (male/female/not specified) [not specified]: ").strip().lower() or DEFAULTS["gender"]
    
    year = random.randint(1490, 1495)
    in_game_date = f"{year:04d}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

    game_state = {
        "id": _get_next_session_filename().replace(".xml", ""),
        "date": date.today().isoformat(),
        "gamemaster": "AI Storyteller",
        "campaignName": DEFAULTS["campaign"],
        "inGameDate": in_game_date,
        "currentLocation": DEFAULTS["currentLocation"],
        "lastRecap": f"{player_name} the {player_race} {player_class} arrives at {DEFAULTS['currentLocation']}.",
        "playerName": player_name,
        "playerRace": player_race,
        "playerClass": player_class,
        "playerGender": player_gender,
        "playerBackground": DEFAULTS["background"],
        "Memory": {"Fact": []},
        "Log": {"Entry": []},
        "KeyNPCs": [], "KeyLocations": [DEFAULTS["currentLocation"]], "KeyItems": [],
        "playerInventory": [], "playerGold": 10, "playerXP": 0, "playerLevel": 1,
        "playerHitPoints": 10, "playerMaxHitPoints": 10, "playerArmorClass": 10,
        "playerStats": {"Strength": 10, "Dexterity": 10, "Constitution": 10, "Intelligence": 10, "Wisdom": 10, "Charisma": 10},
        "playerSkills": {},
        "turn_counter": 0
    }
    return game_state

def update_ai_memory(game_state, player_input, ai_response):
    """Adds the latest turn to the AI's memory within the game state."""
    if "Memory" not in game_state: game_state["Memory"] = {}
    if "Fact" not in game_state["Memory"]: game_state["Memory"]["Fact"] = []
    
    game_state["Memory"]["Fact"].append({
        "timestamp": datetime.now().isoformat(),
        "player_input": player_input,
        "ai_response": str(ai_response or "")
    })

def check_level_up(game_state):
    """Checks for and handles player level-up."""
    xp = int(game_state.get("playerXP", 0))
    level = int(game_state.get("playerLevel", 1))
    threshold = 100 * level
    if xp >= threshold:
        game_state["playerLevel"] = level + 1
        game_state["playerXP"] = xp - threshold # Carry over extra XP
        print(f"\n*** CONGRATULATIONS! You reached level {level + 1}! ***")
        # For simplicity, we'll just add +1 to a random stat and increase HP.
        # This can be expanded to be interactive.
        stat_to_increase = random.choice(list(game_state["playerStats"].keys()))
        game_state["playerStats"][stat_to_increase] += 1
        game_state["playerMaxHitPoints"] += 5
        game_state["playerHitPoints"] = game_state["playerMaxHitPoints"] # Heal on level up
        print(f"Your {stat_to_increase} increased to {game_state['playerStats'][stat_to_increase]}!")
        print(f"Your Max HP increased to {game_state['playerMaxHitPoints']}! You are fully healed.")
        
def process_player_death(game_state):
    """Handles the logic when a player's HP drops to 0 or below."""
    revival_items = ["Phoenix Feather", "Blessing of Resurrection"]
    for item in revival_items:
        if item in game_state.get("playerInventory", []):
            print(f"You would have died, but your {item} saves you! The item vanishes.")
            game_state["playerInventory"].remove(item)
            game_state["playerHitPoints"] = game_state.get("playerMaxHitPoints", 10) // 2
            return False # Player did not die
    print("Your vision fades to black... You have died. Game Over.")
    return True # Player is dead

def create_item(name, rarity=ItemRarity.COMMON, description=""):
    return {
        "name": name,
        "rarity": rarity.value,
        "description": description
    }

def print_inventory(game_state):
    inv = game_state.get('playerInventory', [])
    if not inv:
        print("Inventory: Empty")
    else:
        print("Inventory:")
        for item in inv:
            if isinstance(item, dict):
                print(f"- {item['name']} [{item['rarity']}]")
            else:
                print(f"- {item}")

def interactive_chat_loop():
    """The main game loop."""
    print("Welcome to the AI D&D Storyteller!")
    if ollama and not is_ollama_running():
        if not start_ollama():
            return # Exit if Ollama can't be started

    rag_instance = RAG(SAVE_DIRECTORY)
    
    latest_save = get_latest_save_file()
    choice = input(f"Type 'new' to start a new game, or 'load' to continue ({latest_save.name if latest_save else 'none available'}): ").strip().lower()
    
    if choice == "load" and latest_save:
        game_state = load_game_state(latest_save)
        if not game_state:
            print("Failed to load save. Starting new game.")
            game_state = initialize_new_game()
    else:
        game_state = initialize_new_game()
    
    save_path = SAVE_DIRECTORY / f"{game_state['id']}.xml"

    while True:
        print("\n" + "="*50)
        print(f"Location: {game_state['currentLocation']} | HP: {game_state['playerHitPoints']}/{game_state['playerMaxHitPoints']} | Gold: {game_state['playerGold']} | LVL: {game_state['playerLevel']} ({game_state['playerXP']}/{game_state['playerLevel']*100} XP)")
        print(f"Recap: {game_state.get('lastRecap', 'No recap available.')}")
        print("---")
        cmd = input("What do you do? ('help' for commands) > ").strip()

        if cmd.lower() in ("quit", "exit"):
            if ollama: stop_ollama()
            break
        elif cmd.lower() == "save":
            save_game_state(game_state, save_path)
            continue
        elif cmd.lower() == "help":
            print("\nCommands: save, quit, inventory, stats, <any action>")
            continue
        elif cmd.lower() in ("inventory", "i"):
            print_inventory(game_state)
            continue
        elif cmd.lower() == "stats":
            stats = ", ".join(f"{k}: {v}" for k, v in game_state.get('playerStats', {}).items())
            print(f"Stats: {stats}")
            continue
        elif cmd.lower() == "skills":
            skills = ", ".join(f"{k}: {v}" for k, v in game_state.get('playerSkills', {}).items())
            print(f"Skills: {skills if skills else 'None'}")
            continue

        game_state["turn_counter"] = game_state.get("turn_counter", 0) + 1
        
        # --- Action and AI Turn ---
        roll_result = random.randint(1, 20)
        print(f"\n-> You attempt to '{cmd}'... (d20 roll: {roll_result})")
        
        rag_context = rag_instance.get_context_for_query(cmd)

        # Dynamic world event check (e.g., every 15 turns)
        if game_state["turn_counter"] > 0 and game_state["turn_counter"] % 15 == 0:
            event_text = get_ai_event(game_state, rag_context)
            if event_text:
                print(f"\n[WORLD EVENT]: {event_text}")
                # Log this event
                game_state["Log"]["Entry"].append({
                    "timestamp": datetime.now().isoformat(), "type": "WorldEvent", "Content": event_text
                })

        ai_output = get_ai_narrative(game_state, cmd, roll_result, rag_context)
        print(f"\nGM: {ai_output}")

        # --- Post-AI Processing ---
        update_ai_memory(game_state, cmd, ai_output)
        append_to_transcript(cmd, ai_output)
        parse_and_apply_ai_config_command(ai_output)
        
        # Update game state with keywords and damage from AI response
        keywords = extract_keywords_from_ai_output(ai_output)
        for k, values in keywords.items():
            for v in values:
                if v and v not in game_state[k]:
                    print(f"Discovered new {k[:-1]}: {v}")
                    game_state[k].append(v)
        
        damage_match = re.search(r"DAMAGE:\s*(\d+)", ai_output or "", re.IGNORECASE)
        if damage_match:
            damage = int(damage_match.group(1))
            game_state["playerHitPoints"] -= damage
            print(f"You take {damage} damage!")
            if game_state["playerHitPoints"] <= 0:
                if process_player_death(game_state):
                    save_game_state(game_state, save_path)
                    break # End game

        # Update recap and log
        if ai_output: game_state["lastRecap"] = ai_output.split('\n')[0]
        game_state["Log"]["Entry"].append({
            "timestamp": datetime.now().isoformat(), "type": "Turn",
            "Content": f"Player: {cmd} (Rolled {roll_result})\nAI: {ai_output}"
        })
        
        # Grant XP and check for level up
        game_state["playerXP"] = int(game_state.get("playerXP", 0)) + 20
        check_level_up(game_state)
        
        # Auto-save at the end of the turn
        save_game_state(game_state, save_path)