import os
import random
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, date
import glob
import subprocess
import sys
import time

try:
    import ollama
except ImportError:
    ollama = None

SAVE_DIRECTORY = Path("dnd_ai_sessions")
TRANSCRIPT_FILE = SAVE_DIRECTORY / "full_transcript.xml"
game_state = None

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

def get_ai_narrative(player_input_text, current_session_xml_string_context, roll_result):
    print("\n--- AI (Fast Model) Turn ---")
    ai_response_text = None

    if ollama is None:
        print("CRITICAL: 'ollama' library not found. Falling back to manual input.")
        ai_response_text = input("Fallback - GM (manual), enter narrative + choices: ")
        print("--- End AI Turn ---")
        return ai_response_text
        
    try:
        player_name = game_state.get("playerName", DEFAULTS["name"])
        player_gender = game_state.get("playerGender", DEFAULTS["gender"]).lower()

        pronoun = "they"
        if player_gender == "male":
            pronoun = "he"
        elif player_gender == "female":
            pronoun = "she"

        player_context = (
            f"Name: {player_name}\n"
            f"Gender: {player_gender.capitalize()}\n"
            f"Pronoun to use for player: {pronoun}"
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

        prompt_for_ai = (
            f"You are a Dungeons and Dragons game master. You must base the outcome of the player's action on their dice roll.\n\n"
            f"== Player Character ==\n{player_context}\n\n"
            f"== Current Memory ==\n{memory_summary}\n\n"
            f"== Current Situation ==\n{context_summary}\n\n"
            f"== Player's Action ==\n{player_input_text}\n\n"
            f"== Dice Roll Result ==\n{roll_context}\n\n"
            f"== Instructions ==\n"
            f"Based on the player's action and their dice roll, narrate the outcome. "
            f"Tell a story of exactly 3 sentences maximum, then suggest 2–3 numbered choices for the player's next move:\n"
            f"1. ...\n2. ...\n3. ..."
        )

        response = ollama.generate(
            model='phi3:mini',
            prompt=prompt_for_ai,
            stream=False
        )
        ai_response_text = response.get('response')
        if not ai_response_text:
            raise ValueError("No response received from Ollama.")

    except Exception as e:
        print(f"Error communicating with Ollama: {e}")
        ai_response_text = input("Fallback - GM (manual), enter narrative + choices: ")

    print("--- End AI Turn ---")
    return ai_response_text

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
            "PlayerCharacters": {"Character": [{"name": player_name, "Race": player_race, "Class": player_class, "Biography": player_bg}]}
        }

    while True:
        print(f"\n== {game_state['campaignName']} / {game_state['currentLocation']} ==")
        print(f"Recap: {game_state['lastRecap']}")
        cmd = input("What do you do? (or type 'save', 'quit'): ").strip()

        if cmd.lower() == "quit":
            # We don't try to kill the process anymore, as it might be used by other apps.
            # The user can close it manually.
            break
        elif cmd.lower() == "save":
            save_game_state(SAVE_DIRECTORY / f"{game_state['id']}.xml")
            continue

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

        ai_output = get_ai_narrative(cmd, context_xml, roll_result)
        
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
if __name__ == "__main__":
    interactive_chat_loop()