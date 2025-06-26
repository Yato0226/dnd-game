import os
import random
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, date
import glob
import subprocess
import sys
import time
import re
from dnd_ai_game.src.ai.rag import RAG

try:
    import ollama
except ImportError:
    ollama = None

SAVE_DIRECTORY = Path("dnd_ai_sessions")
TRANSCRIPT_FILE = SAVE_DIRECTORY / "full_transcript.xml"
game_state = None
model = 'phi3:3.8b-mini-4k-instruct-q4_0' # Default model, can be changed to any Ollama model
RAG_INSTANCE = RAG(SAVE_DIRECTORY)

DEFAULTS = {
    "campaign": "The Unwritten Tale",
    "name": "Adventurer",
    "race": "Human",
    "class": "Explorer",
    "background": "Traveler from distant lands",
    "gender": "not specified",
    "currentLocation": "The Forgotten Inn"
}

def is_ollama_running():
    """Checks if the Ollama process is running."""
    try:
        if sys.platform == "win32":
            command = ["tasklist"]
            process_name = "ollama.exe"
        else: # macOS and Linux
            command = ["pgrep", "-f", "ollama"]
            process_name = "ollama"

        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        if sys.platform == "win32":
            return process_name in result.stdout
        else:
            return result.stdout.strip() != "" # pgrep returns PIDs

    except (subprocess.CalledProcessError, FileNotFoundError):
        # CalledProcessError if pgrep finds nothing, FileNotFoundError if command doesn't exist
        return False
    except Exception as e:
        print(f"An unexpected error occurred while checking for Ollama: {e}")
        return False

def start_ollama():
    """Starts the Ollama application in the background."""
    print("Ollama is not running. Attempting to start it...")
    try:
        if sys.platform == "win32":
            # Use start /b to run in the background without a new console window
            subprocess.Popen(["start", "/b", "ollama", "serve"], shell=True)
        else: # macOS and Linux
            subprocess.Popen(["ollama", "serve"])
            
        print("Ollama started. Please wait a few seconds for it to initialize.")
        time.sleep(5) # Give Ollama time to start up
        return True
    except FileNotFoundError:
        print("\nCRITICAL ERROR: 'ollama' command not found.")
        print("Please ensure Ollama is installed and its location is in your system's PATH.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while starting Ollama: {e}")
        return False

def _parse_xml_node(node):
    data = node.attrib.copy()
    children = list(node)
    text = node.text.strip() if node.text else None

    if not children:
        if text and not data:
            return text
        if text:
            data["#text"] = text
        return data

    for child in children:
        tag = child.tag
        parsed = _parse_xml_node(child)
        if tag in data:
            if not isinstance(data[tag], list):
                data[tag] = [data[tag]]
            data[tag].append(parsed)
        else:
            data[tag] = parsed

    return data

def load_game_state(filepath):
    global game_state
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        game_state = {**root.attrib, **{
            child.tag: _parse_xml_node(child) for child in root
        }}
        if "Memory" not in game_state:
            game_state["Memory"] = {"Fact": []}
        print(f"Game state loaded from {filepath}")
        return True
    except Exception as e:
        print(f"Failed to load {filepath}: {e}")
        game_state = None
        return False

def _convert_dict_to_xml_elements(parent, data):
    if not isinstance(data, dict):
        parent.text = str(data)
        return
    if '#text' in data:
        parent.text = str(data.pop('#text'))

    for key, val in data.items():
        val = val if isinstance(val, list) else [val]
        for item in val:
            child = ET.SubElement(parent, key)
            _convert_dict_to_xml_elements(child, item.copy() if isinstance(item, dict) else item)

def save_game_state(filepath, silent=False):
    global game_state
    if game_state is None:
        if not silent: print("No game state to save.")
        return False

    root_attrs = {k: str(game_state[k]) for k in [
        "id", "date", "gamemaster", "campaignName", "inGameDate", "currentLocation", "lastRecap", "gender", "playerName", "playerRace", "playerClass", "playerBackground", "playerGender", "playerAge", "playerHeight", "playerWeight", "playerAlignment", "playerDeity", "playerBiography", "playerPersonalityTraits", "playerIdeals", "playerBonds", "playerFlaws", "playerSkills", "playerLanguages", "playerEquipment", "playerSpells", "playerInventory", "playerGold", "playerXP", "playerLevel", "playerHitPoints", "playerArmorClass", "playerInitiative", "playerSpeed", "playerProficiencies", "playerSaves", "playerAttacks", "playerFeatures", "playerTraits"
    ] if k in game_state}

    root = ET.Element("Session", attrib=root_attrs)
    for k, v in game_state.items():
        if k in root_attrs:
            continue
        elems = v if isinstance(v, list) else [v]
        for item in elems:
            child = ET.SubElement(root, k)
            _convert_dict_to_xml_elements(child, item.copy() if isinstance(item, dict) else item)

    try:
        ET.indent(root, space="    ")
    except AttributeError:
        pass

    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(filepath, encoding="UTF-8", xml_declaration=True)

    if not silent:
        print(f"Game state saved to {filepath}")
    return True

def _get_next_session_filename():
    SAVE_DIRECTORY.mkdir(exist_ok=True)
    files = glob.glob(str(SAVE_DIRECTORY / "SESS-*.xml"))
    max_id = max((int(f.split('-')[-1].split('.')[0]) for f in files if f.split('-')[-1].split('.')[0].isdigit()), default=0)
    return f"SESS-{max_id + 1:03d}.xml"

def get_latest_save_file():
    SAVE_DIRECTORY.mkdir(exist_ok=True)
    files = sorted(glob.glob(str(SAVE_DIRECTORY / "SESS-*.xml")), key=lambda f: f.lower(), reverse=True)
    return Path(files[0]) if files else None

def extract_minimal_context(xml_string):
    try:
        root = ET.fromstring(xml_string)
        campaign = root.attrib.get("campaignName", "")
        location = root.attrib.get("currentLocation", "")
        recap = root.attrib.get("lastRecap", "")

        log_entries = root.find("Log")
        last_3_logs = []
        if log_entries is not None:
            for entry in log_entries.findall(".//Entry")[-3:]:
                content = entry.findtext("Content")
                if content:
                    last_3_logs.append(content.strip())
        recent_log = "\n".join(last_3_logs)

        return (
            f"Campaign: {campaign}\n"
            f"Location: {location}\n"
            f"Recap: {recap}\n"
            f"Recent Events:\n{recent_log}"
        )
    except Exception as e:
        return f"(Error summarizing XML: {e})"

def summarize_memory_facts():
    memory_facts = game_state.get("Memory", {}).get("Fact", [])
    if not memory_facts:
        return "None yet."
    summary_lines = []
    for fact in memory_facts[-3:]:
        player_input = fact.get('player_input', '[No Input Recorded]')
        ai_response = fact.get('ai_response', '[No Response Recorded]')
        summary_lines.append(f"- Player: {player_input}\n  AI: {ai_response.splitlines()[0]}")
    return "\n".join(summary_lines)

def update_ai_memory(player_input, ai_response):
    if "Memory" not in game_state:
        game_state["Memory"] = {}
    
    if "Fact" not in game_state["Memory"] or not isinstance(game_state["Memory"].get("Fact"), list):
        game_state["Memory"]["Fact"] = []

    new_fact = {
        "timestamp": datetime.now().isoformat(),
        "player_input": player_input,
        "ai_response": str(ai_response if ai_response is not None else "")
    }
    
    game_state["Memory"]["Fact"].append(new_fact)

def get_ai_narrative(player_input_text, current_session_xml_string_context, roll_result, rag_context=""):
    print("\n--- AI Turn ---")
    ai_response_text = None

    if ollama is None:
        print("CRITICAL: 'ollama' library not found. Falling back to manual input.")
        ai_response_text = input("Fallback - GM (manual), enter narrative + choices: ")
        print("--- End AI Turn ---")
        return ai_response_text
        
    try:
        player_name = game_state.get("playerName", DEFAULTS["name"])
        player_gender = game_state.get("playerGender", DEFAULTS["gender"]).lower()
        player_race = game_state.get("playerRace", DEFAULTS["race"])
        player_class = game_state.get("playerClass", DEFAULTS["class"])
        player_background = game_state.get("playerBackground", DEFAULTS["background"])
        player_inventory = ", ".join(game_state.get("playerInventory", [])) or "None"

        pronoun = "they"
        if player_gender == "male":
            pronoun = "he"
        elif player_gender == "female":
            pronoun = "she"

        player_stats = game_state.get("playerStats", {})
        stats_str = ", ".join(f"{k}: {v}" for k, v in player_stats.items())
        player_context = (
            f"Name: {player_name}\n"
            f"Gender: {player_gender.capitalize()}\n"
            f"Race: {player_race}\n"
            f"Class: {player_class}\n"
            f"Background: {player_background}\n"
            f"Pronoun to use for player: {pronoun}\n"
            f"Stats: {stats_str}\n"
            f"Inventory: {player_inventory}"
        )

        context_summary = extract_minimal_context(current_session_xml_string_context)
        memory_summary = summarize_memory_facts()
        
        roll_context = f"The player rolled a d20 and got: {roll_result}.\n"
        if roll_result == 1:
            roll_context += "This is a CRITICAL FAILURE. The action should fail spectacularly, with negative consequences."
        elif roll_result <= 5:
            roll_context += "This is a significant failure. The action fails, and there may be a minor complication."
        elif roll_result <= 10:
            roll_context += "This is a failure. The action does not succeed, but doesn't necessarily make things worse."
        elif roll_result <= 15:
            roll_context += "This is a modest success. The action succeeds, but not perfectly or completely."
        elif roll_result < 20:
            roll_context += "This is a clear success. The action works as intended."
        elif roll_result == 20:
            roll_context += "This is a CRITICAL SUCCESS. The action succeeds spectacularly, with an added bonus or benefit."

        key_npcs = ", ".join(game_state.get("KeyNPCs", [])) or "None"
        key_locations = ", ".join(game_state.get("KeyLocations", [])) or "None"
        key_items = ", ".join(game_state.get("KeyItems", [])) or "None"

        # NEW: Add all session summaries
        all_sessions_summary = summarize_all_sessions()

        # Load AI config/instructions dynamically
        ai_config = load_ai_config()
        prompt_instructions = ai_config.findtext("PromptInstructions", "")
        max_sentences = ai_config.findtext("MaxSentences", "5")
        always_tag = ai_config.findtext("AlwaysTagEntities", "true")
        

        prompt_for_ai = (
            f"== RAG Retrieved Info ==\n{rag_context}\n\n"
            f"{prompt_instructions}\n\n"
            f"== Player Character ==\n{player_context}\n\n"
            f"== Current Memory ==\n{memory_summary}\n\n"
            f"== Current Situation ==\n{context_summary}\n\n"
            f"== Player's Action ==\n{player_input_text}\n\n"
            f"== Dice Roll Result ==\n{roll_context}\n\n"
            f"== Important NPCs ==\n{key_npcs}\n"
            f"== Important Locations ==\n{key_locations}\n"
            f"== Important Items ==\n{key_items}\n\n"
            f"== All Previous Sessions ==\n{all_sessions_summary}\n\n"
            f"== AI Config XML ==\n{ET.tostring(ai_config, encoding='unicode')}\n\n"
            f"== Instructions ==\n"
            f"Before replying, you MUST consider all facts, logs, NPCs, items, locations, and config from all session XMLs and the AI config XML. "
            f"Always limit the output to {max_sentences} sentences maximum, and always end with a numbered list of choices.\n"
            f"{'Always tag new NPCs, locations, and items as [NPC], [LOCATION], or [ITEM].' if always_tag.lower() == 'true' else ''}\n"
            f"Whenever you mention a merchant, shop, or market, tag it as [MERCHANT]. "
            f"If the player receives or spends gold, mention the amount as GOLD: <number>. "
            f"Include opportunities to buy or sell items when appropriate. "
        )

        response = ollama.generate(
            model=model,
            prompt=prompt_for_ai,
            stream=False,
            temperature=1.2  # Add this if supported
        )
        ai_response_text = response.get('response')
        if not ai_response_text:
            raise ValueError("No response received from Ollama.")

    except Exception as e:
        print(f"Error communicating with Ollama: {e}")
        ai_response_text = input("Fallback - GM (manual), enter narrative + choices: ")

    print("--- End AI Turn ---")
    return ai_response_text

def extract_skill_from_ai_output(ai_output):
    match = re.search(r"SKILL:\s*([A-Za-z ]+)", ai_output or "")
    if match:
        return match.group(1).strip()
    return None

def append_to_transcript(player_input, ai_output):
    if not TRANSCRIPT_FILE.exists():
        root = ET.Element("Transcript")
    else:
        tree = ET.parse(TRANSCRIPT_FILE)
        root = tree.getroot()

    turn = ET.SubElement(root, "Turn", attrib={"timestamp": datetime.now().isoformat()})
    ET.SubElement(turn, "Player").text = player_input
    ET.SubElement(turn, "AI").text = str(ai_output if ai_output is not None else "")

    try:
        ET.indent(root, space="    ")
    except Exception:
        pass

    ET.ElementTree(root).write(TRANSCRIPT_FILE, encoding="UTF-8", xml_declaration=True)

def extract_keywords_from_ai_output(ai_output):
    npcs = re.findall(r"\b([\w\s'-]+)\s*\[NPC\]", ai_output)
    locations = re.findall(r"\b([\w\s'-]+)\s*\[LOCATION\]", ai_output)
    items = re.findall(r"\b([\w\s'-]+)\s*\[ITEM\]", ai_output)
    return {
        "KeyNPCs": [npc.strip() for npc in npcs],
        "KeyLocations": [loc.strip() for loc in locations],
        "KeyItems": [item.strip() for item in items]
    }

def extract_skill_from_ai_output(ai_output):
    match = re.search(r"SKILL:\s*([A-Za-z ]+)", ai_output or "")
    if match:
        return match.group(1).strip()
    return None

def load_ai_config():
    config_path = SAVE_DIRECTORY / "ai_config.xml"
    if not config_path.exists():
        root = ET.Element("AIConfig")
        ET.SubElement(root, "PromptInstructions").text = (
            "You are a Dungeons and Dragons game master. Be imaginative, surprising, and vivid in your storytelling. Always consider all facts, logs, NPCs, items, and locations from all session XMLs before responding. Use concise, engaging, and creative storytelling. Always follow the rules and style in this config."
        )
        ET.SubElement(root, "MaxSentences").text = "5"
        ET.SubElement(root, "AlwaysTagEntities").text = "true"
        ET.ElementTree(root).write(config_path, encoding="UTF-8", xml_declaration=True)
    tree = ET.parse(config_path)
    return tree.getroot()

def summarize_all_sessions():
    """Summarize all session XMLs (except ai_config.xml) for AI context."""
    summaries = []
    for xml_file in SAVE_DIRECTORY.glob("*.xml"):
        if xml_file.name == "ai_config.xml":
            continue
        try:
            with open(xml_file, encoding="utf-8") as f:
                xml_str = f.read()
            summary = extract_minimal_context(xml_str)
            summaries.append(f"Session: {xml_file.name}\n{summary}")
        except Exception as e:
            summaries.append(f"Session: {xml_file.name}\n(Error reading: {e})")
    return "\n\n".join(summaries) if summaries else "No previous sessions."

def interactive_chat_loop():
    global game_state

    print("Welcome to the AI D&D Storyteller!")
    
    # Check for ollama library and process
    if ollama is None:
        print("\nWARNING: The 'ollama' library is not installed. The game will run in manual/fallback mode.")
        print("Please install it with 'pip install ollama' to use the AI storyteller.\n")
    else:
        if is_ollama_running():
            print("Ollama is already running.")
        else:
            if not start_ollama():
                # End the game if Ollama can't be started
                return 

    SAVE_DIRECTORY.mkdir(exist_ok=True)
    latest = get_latest_save_file()

    choice = input(f"Type 'new' to start a new game, or 'load' to continue ({latest.name if latest else 'none'}): ").strip().lower()
    if choice == "load" and latest:
        load_game_state(latest)
    else:
        player_name = input("Enter your character's name: ") or DEFAULTS["name"]
        player_race = input("Race: ") or DEFAULTS["race"]
        player_class = input("Class: ") or DEFAULTS["class"]
        player_gender = input("Gender (male/female): ").strip().lower() or DEFAULTS["gender"]
        player_bg = input("Background: ") or DEFAULTS["background"]
        currentLocation = input("Current Location: ") or DEFAULTS["currentLocation"]
        campaign_name = input("Campaign Name: ") or DEFAULTS["campaign"]

        year = random.randint(1490, 1495)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        in_game_date = f"{year:04d}-{month:02d}-{day:02d}"

        game_state = {
            "id": _get_next_session_filename().replace(".xml", ""),
            "date": date.today().isoformat(),
            "gamemaster": "AI Storyteller",
            "campaignName": campaign_name,
            "inGameDate": in_game_date,
            "currentLocation": f"{currentLocation}",
            "lastRecap": f"{player_name} the {player_race} {player_class} arrives at {currentLocation}.",
            "playerName": player_name,
            "playerRace": player_race,
            "playerClass": player_class,
            "playerGender": player_gender,
            "playerBackground": player_bg,
            "Memory": {"Fact": []},
            "Log": {"Entry": []},
            "PlayerCharacters": {"Character": [{"name": player_name, "Race": player_race, "Class": player_class, "Biography": player_bg}]},
            "KeyNPCs": [],
            "KeyLocations": [],
            "KeyItems": [],
            "playerInventory": [],
            "playerHitPoints": 10, 
            "playerArmorClass": 10,
            "playerMaxHitPoints": 10, 
            "playerStats": {
                "Strength": 10,
                "Dexterity": 10,
                "Constitution": 10,
                "Intelligence": 10,
                "Wisdom": 10,
                "Charisma": 10
            },
            "playerSkills": {},  # Will be filled by AI below
            "playerGold": 0,
            "playerXP": 0,
            "playerLevel": 1,
        }

        # --- NEW: Let AI generate starting skills based on character concept ---
        if ollama is not None:
            skill_prompt = (
                f"You are a D&D character builder. "
                f"Given the following character details, generate a JSON object mapping D&D 5e skill names to modifiers (between -1 and +5) "
                f"that would make sense for this character. Only output the JSON object, nothing else.\n"
                f"Name: {player_name}\n"
                f"Race: {player_race}\n"
                f"Class: {player_class}\n"
                f"Gender: {player_gender}\n"
                f"Background: {player_bg}\n"
                f"Example output: {{\"Stealth\": 2, \"Persuasion\": 1, \"Arcana\": 0}}"
            )
            try:
                response = ollama.generate(
                    model= model,
                    prompt=skill_prompt,
                    stream=False
                )
                import json
                skills_json = response.get('response', '{}')
                # Extract JSON from response (in case AI adds text)
                match = re.search(r"\{.*\}", skills_json, re.DOTALL)
                if match:
                    skills_json = match.group(0)
                game_state["playerSkills"] = json.loads(skills_json)
                print("AI-generated starting skills:", game_state["playerSkills"])
            except Exception as e:
                print(f"Could not generate skills with AI: {e}")
                game_state["playerSkills"] = {}
        else:
            print("AI not available, starting with no skills.")
            game_state["playerSkills"] = {}

    def check_level_up():
        """Check if player has enough XP to level up and handle stat increase."""
        xp = game_state.get("playerXP", 0)
        level = game_state.get("playerLevel", 1)
        # Example XP threshold: 100 * current level
        threshold = 100 * level
        while xp >= threshold:
            game_state["playerLevel"] = level + 1
            print(f"\n*** Congratulations! You reached level {level + 1}! ***")
            # Let player choose a stat to increase
            stats = list(game_state["playerStats"].keys())
            print("Choose a stat to increase:")
            for i, stat in enumerate(stats):
                print(f"{i+1}. {stat} (current: {game_state['playerStats'][stat]})")
            choice = input("Enter the number of the stat to increase: ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(stats):
                    chosen_stat = stats[idx]
                    game_state["playerStats"][chosen_stat] += 1
                    print(f"{chosen_stat} increased to {game_state['playerStats'][chosen_stat]}!")
                else:
                    print("Invalid choice. No stat increased.")
            except Exception:
                print("Invalid input. No stat increased.")
            # Heal player to max HP on level up
            game_state["playerHitPoints"] = game_state.get("playerMaxHitPoints", 10)
            print("You are fully healed!")
            # Update for next level
            level = game_state["playerLevel"]
            threshold = 100 * level

    while True:
        print(f"\n== {game_state['campaignName']} / {game_state['currentLocation']} ==")
        print(f"Recap: {game_state['lastRecap']}")
        cmd = input("What do you do? (or type 'save', 'quit'): ").strip()
        print(f"HP: {game_state['playerHitPoints']}/{game_state['playerMaxHitPoints']}")
        print("Stats: " + ", ".join(f"{k}: {v}" for k, v in game_state.get("playerStats", {}).items()))

        if cmd.lower() == "quit":
            subprocess.run(["C:\\Windows\\System32\\taskkill.exe", "/IM", "ollama.exe", "/F"], capture_output=True, text=True)
            break
        elif cmd.lower() == "save":
            save_game_state(SAVE_DIRECTORY / f"{game_state['id']}.xml")
            continue
        elif cmd.lower() == "delete":
            confirm = input("Are you sure you want to delete ALL saved games? Type 'delete' to confirm: ").strip().lower()
            if confirm == "delete":
                files = [f for f in SAVE_DIRECTORY.glob("*.xml") if f.name != "ai_config.xml"]
                for f in files:
                    try:
                        f.unlink()
                    except Exception as e:
                        print(f"Could not delete {f}: {e}")
                print("All XML save files deleted (except ai_config.xml).")
            else:
                print("Delete cancelled.")
            continue
        elif cmd.lower().startswith("take "):
            item = cmd[5:].strip()
            if not item:
                print("Specify an item to take.")
                continue
            # Only allow taking items that have been mentioned by the AI
            if item in game_state.get("KeyItems", []) and item not in game_state["playerInventory"]:
                game_state["playerInventory"].append(item)
                print(f"You take the {item}.")
            elif item in game_state["playerInventory"]:
                print(f"You already have the {item}.")
            else:
                print(f"No such item '{item}' found to take.")
            continue
        elif cmd.lower() in ("inventory", "i"):
            inv = game_state.get("playerInventory", [])
            if inv:
                print("Your inventory:")
                for item in inv:
                    print(f"- {item}")
            else:
                print("Your inventory is empty.")
            continue
        elif cmd.lower().startswith("use "):
            item = cmd[4:].strip()
            if item in game_state.get("playerInventory", []):
                print(f"You attempt to use the {item}...")
                # Pass as player_input_text: "use <item>"
                player_input_text = f"use {item}"
            else:
                print(f"You don't have '{item}' in your inventory.")
                continue
        elif cmd.lower() in ("stats", "stat"):
            stats = game_state.get("playerStats", {})
            print("Your stats:")
            for k, v in stats.items():
                print(f"- {k}: {v}")
            continue
        elif cmd.lower() in ("help", "commands", "?"):
            print("Available commands:")
            print("  save                - Save the game")
            print("  quit                - Quit the game")
            print("  delete              - Delete all saved games")
            print("  take <item>         - Take an item mentioned by the AI")
            print("  inventory, i        - Show your inventory")
            print("  use <item>          - Use an item from your inventory")
            print("  stats, stat         - Show your stats")
            print("  buy <item>          - Buy an item (in shop/market/merchant only)")
            print("  sell <item>         - Sell an item (in shop/market/merchant only)")
            print("  help, commands, ?   - Show this command list")
            print("  <anything else>     - Perform an in-game action")
            continue
        elif cmd.lower().startswith("setstat "):
            # Example: setstat Strength 15
            parts = cmd.split()
            if len(parts) == 3 and parts[1].capitalize() in game_state["playerStats"]:
                stat = parts[1].capitalize()
                try:
                    val = int(parts[2])
                    game_state["playerStats"][stat] = val
                    print(f"{stat} set to {val}.")
                except ValueError:
                    print("Invalid value.")
            else:
                print("Usage: setstat <StatName> <Value>")
            continue
        elif cmd.lower().startswith("buy "):
            item = cmd[4:].strip()
            # Only allow buying in shop/market/merchant context
            allowed = any(
                tag in game_state.get("KeyLocations", []) + game_state.get("KeyNPCs", [])
                for tag in ["Shop", "Market", "Merchant"]
            )
            if not allowed:
                print("You can only buy items when at a shop, market, or with a merchant.")
                continue
            # Example price list (expand as needed)
            price_list = {"Potion": 5, "Sword": 15, "Phoenix Feather": 50}
            if item not in price_list:
                print(f"{item} is not available for sale.")
                continue
            price = price_list[item]
            if game_state["playerGold"] < price:
                print(f"Not enough gold. {item} costs {price} gold, you have {game_state['playerGold']}.")
                continue
            game_state["playerGold"] -= price
            game_state["playerInventory"].append(item)
            print(f"You bought {item} for {price} gold. Gold left: {game_state['playerGold']}")
            continue

        elif cmd.lower().startswith("sell "):
            item = cmd[5:].strip()
            allowed = any(
                tag in game_state.get("KeyLocations", []) + game_state.get("KeyNPCs", [])
                for tag in ["Shop", "Market", "Merchant"]
            )
            if not allowed:
                print("You can only sell items when at a shop, market, or with a merchant.")
                continue
            if item not in game_state["playerInventory"]:
                print(f"You don't have {item} to sell.")
                continue
            price_list = {"Potion": 3, "Sword": 10, "Phoenix Feather": 30}
            price = price_list.get(item, 1)
            game_state["playerGold"] += price
            game_state["playerInventory"].remove(item)
            print(f"You sold {item} for {price} gold. Gold now: {game_state['playerGold']}")
            continue
        else:
            player_input_text = cmd

        roll_result = random.randint(1, 20)
        print("\n--- Action Roll ---")
        print(f"You attempt to '{cmd}'...")
        print(f"You roll a d20 and get... {roll_result}!")
        if roll_result == 1:
            print("Result: Critical Failure!")
        elif roll_result == 20:
            print("Result: Critical Success!")
        print("-------------------")

        temp_path = SAVE_DIRECTORY / "__temp.xml"
        save_game_state(temp_path, silent=True)
        with open(temp_path, encoding='utf-8') as f:
            context_xml = f.read()
        temp_path.unlink()

        # --- FIX: Get relevant info from RAG for the player's command BEFORE calling get_ai_narrative ---
        rag_results = RAG_INSTANCE.retrieve_information(cmd)
        if rag_results:
            rag_context = "Relevant files: " + ", ".join(rag_results)
            rag_snippets = "\n".join(
                f"{fname}: {RAG_INSTANCE.documents[fname][:300]}..." for fname in rag_results
            )
            rag_context += "\n" + rag_snippets
        else:
            rag_context = "No directly relevant files found."

        # --- FIX: Only call get_ai_narrative ONCE, with rag_context ---
        ai_output = get_ai_narrative(cmd, context_xml, roll_result, rag_context=rag_context)
        parse_and_apply_ai_config(ai_output)

        # --- Stat modifier logic: apply relevant stat to skill checks ---
        # This block replaces the previous skill check logic
        skill_name = extract_skill_from_ai_output(ai_output)
        skill_mod = 0
        stat_mod = 0
        if skill_name and skill_name.lower() != "none":
            # If skill is new, add it to playerSkills with default 0
            if skill_name not in game_state["playerSkills"]:
                print(f"New skill detected: '{skill_name}'. Adding to your skills with a +0 modifier.")
                game_state["playerSkills"][skill_name] = 0
            skill_mod = game_state["playerSkills"].get(skill_name, 0)

            # Map skills to stats (D&D 5e standard)
            skill_to_stat = {
                "Acrobatics": "Dexterity",
                "Animal Handling": "Wisdom",
                "Arcana": "Intelligence",
                "Athletics": "Strength",
                "Deception": "Charisma",
                "History": "Intelligence",
                "Insight": "Wisdom",
                "Intimidation": "Charisma",
                "Investigation": "Intelligence",
                "Medicine": "Wisdom",
                "Nature": "Intelligence",
                "Perception": "Wisdom",
                "Performance": "Charisma",
                "Persuasion": "Charisma",
                "Religion": "Intelligence",
                "Sleight of Hand": "Dexterity",
                "Stealth": "Dexterity",
                "Survival": "Wisdom"
            }
            # Default to no stat mod if not found
            stat_name = skill_to_stat.get(skill_name, None)
            if stat_name and stat_name in game_state["playerStats"]:
                stat_score = game_state["playerStats"][stat_name]
                stat_mod = (stat_score - 10) // 2  # D&D 5e modifier
            else:
                stat_mod = 0

            total_roll = roll_result + skill_mod + stat_mod
            print(f"Skill Check: {skill_name} (skill mod {skill_mod}, {stat_name if stat_name else 'No Stat'} mod {stat_mod}), total roll: {total_roll}")
            # Feed the skill roll result back to the AI for narration
            ai_output = get_ai_narrative(cmd, context_xml, total_roll)

        # --- NEW: Extract and store tagged keywords ---
        keywords = extract_keywords_from_ai_output(ai_output or "")
        for k in ["KeyNPCs", "KeyLocations", "KeyItems"]:
            for val in keywords[k]:
                if val and val not in game_state[k]:
                    game_state[k].append(val)

        # --- NEW: Parse DAMAGE and update HP ---
        damage_match = re.search(r"DAMAGE:\s*(\d+)", ai_output or "", re.IGNORECASE)
        damage = int(damage_match.group(1)) if damage_match else 0
        if damage > 0:
            game_state["playerHitPoints"] = max(0, game_state.get("playerHitPoints", 0) - damage)
            print(f"You take {damage} damage! HP: {game_state['playerHitPoints']}/{game_state['playerMaxHitPoints']}")
            if game_state["playerHitPoints"] <= 0:
                # --- SINGLE LIFE UNLESS REVIVAL ITEM/BLESSING ---
                revival_items = ["Blessing of Resurrection", "Scroll of True Revival", "Phoenix Feather"]  # Add more as needed
                found_revival = None
                for item in revival_items:
                    if item in game_state.get("playerInventory", []):
                        found_revival = item
                        break
                if found_revival:
                    print(f"You would have died, but your {found_revival} saves you! The item vanishes in a flash of light.")
                    game_state["playerInventory"].remove(found_revival)
                    game_state["playerHitPoints"] = game_state.get("playerMaxHitPoints", 10) // 2  # Revive at half HP
                else:
                    print("You have died! Game over. (No magic or blessing to revive you.)")
                    save_game_state(SAVE_DIRECTORY / f"{game_state['id']}.xml")
                    break

        # --- NEW: Skill check logic (dynamic skills) ---
        skill_name = extract_skill_from_ai_output(ai_output)
        skill_mod = 0
        if skill_name and skill_name.lower() != "none":
            # If skill is new, add it to playerSkills with default 0
            if skill_name not in game_state["playerSkills"]:
                print(f"New skill detected: '{skill_name}'. Adding to your skills with a +0 modifier.")
                game_state["playerSkills"][skill_name] = 0
            skill_mod = game_state["playerSkills"].get(skill_name, 0)
            skill_roll = roll_result + skill_mod
            print(f"Skill Check: {skill_name} (modifier {skill_mod}), total roll: {skill_roll}")
            # Feed the skill roll result back to the AI for narration
            ai_output = get_ai_narrative(cmd, context_xml, skill_roll)

        update_ai_memory(cmd, ai_output)
        
        append_to_transcript(cmd, ai_output)
        if ai_output:
            game_state["lastRecap"] = ai_output.splitlines()[0]
            
        log_entry_content = f"Player: {cmd} (Rolled {roll_result})\nAI: {ai_output}"
        
        if "Log" not in game_state:
            game_state["Log"] = {}
        if "Entry" not in game_state["Log"] or not isinstance(game_state["Log"].get("Entry"), list):
            game_state["Log"]["Entry"] = []
            
        game_state["Log"]["Entry"].append({
            "timestamp": datetime.now().isoformat(),
            "type": "Turn",
            "Content": log_entry_content
        })

        print(f"\nGM: {ai_output}")
        
        # Save after every action
        save_game_state(SAVE_DIRECTORY / f"{game_state['id']}.xml")

        # Get relevant info from RAG for the player's command
        rag_results = RAG_INSTANCE.retrieve_information(cmd)
        if rag_results:
            rag_context = "Relevant files: " + ", ".join(rag_results)
            # Optionally, include snippets:
            rag_snippets = "\n".join(
                f"{fname}: {RAG_INSTANCE.documents[fname][:300]}..." for fname in rag_results
            )
            rag_context += "\n" + rag_snippets
        else:
            rag_context = "No directly relevant files found."

        # After AI output and before saving, reward XP and check for level up
        # Example: +20 XP per action (customize as needed)
        game_state["playerXP"] = game_state.get("playerXP", 0) + 20
        print(f"You gained 20 XP! Total XP: {game_state['playerXP']}")
        check_level_up()

        save_game_state(SAVE_DIRECTORY / f"{game_state['id']}.xml")

def update_ai_config(key, value):
    """Update a key in ai_config.xml with a new value."""
    config_path = SAVE_DIRECTORY / "ai_config.xml"
    tree = ET.parse(config_path)
    root = tree.getroot()
    elem = root.find(key)
    if elem is None:
        elem = ET.SubElement(root, key)
    elem.text = str(value)
    ET.ElementTree(root).write(config_path, encoding="UTF-8", xml_declaration=True)
    print(f"AI config updated: {key} = {value}")

def parse_and_apply_ai_config(ai_output):
    """Detect and apply CONFIG: Set <Key>=<Value> in AI output."""
    match = re.search(r"CONFIG:\s*Set\s+(\w+)\s*=\s*([^\n\r]+)", ai_output or "", re.IGNORECASE)
    if match:
        key, value = match.group(1), match.group(2).strip()
        update_ai_config(key, value)
        return True
    return False

if __name__ == "__main__":
    interactive_chat_loop()