# dnd_ai_game/src/utils/data_manager.py
import xml.etree.ElementTree as ET
from pathlib import Path
import glob
from datetime import datetime

# Import constants from the config file
from dnd_ai_game.src.config import SAVE_DIRECTORY, TRANSCRIPT_FILE, AI_CONFIG_FILE

def _parse_xml_node(node):
    """Recursively parses an XML node into a dictionary."""
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
    """Loads a game state from an XML file and returns it as a dictionary."""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        game_state = {**root.attrib, **{
            child.tag: _parse_xml_node(child) for child in root
        }}
        if "Memory" not in game_state:
            game_state["Memory"] = {"Fact": []}
        print(f"Game state loaded from {filepath}")
        return game_state
    except Exception as e:
        print(f"Failed to load {filepath}: {e}")
        return None

def _convert_dict_to_xml_elements(parent, data):
    """Recursively converts a dictionary to XML elements."""
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

def save_game_state(game_state, filepath, silent=False):
    """Saves the provided game_state dictionary to an XML file."""
    if game_state is None:
        if not silent: print("No game state to save.")
        return False

    # Define all possible root attributes to ensure consistent order and presence
    root_attr_keys = [
        "id", "date", "gamemaster", "campaignName", "inGameDate", "currentLocation", 
        "lastRecap", "playerName", "playerRace", "playerClass", "playerBackground", 
        "playerGender", "playerAge", "playerHeight", "playerWeight", "playerAlignment", 
        "playerDeity", "playerBiography", "playerPersonalityTraits", "playerIdeals", 
        "playerBonds", "playerFlaws", "playerSkills", "playerLanguages", "playerEquipment", 
        "playerSpells", "playerInventory", "playerGold", "playerXP", "playerLevel", 
        "playerHitPoints", "playerArmorClass", "playerInitiative", "playerSpeed", 
        "playerProficiencies", "playerSaves", "playerAttacks", "playerFeatures", "playerTraits"
    ]
    root_attrs = {k: str(game_state[k]) for k in root_attr_keys if k in game_state}

    root = ET.Element("Session", attrib=root_attrs)
    for k, v in game_state.items():
        if k in root_attrs:
            continue
        elems = v if isinstance(v, list) else [v]
        for item in elems:
            child = ET.SubElement(root, k)
            _convert_dict_to_xml_elements(child, item.copy() if isinstance(item, dict) else item)

    ET.indent(root, space="    ")
    
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(filepath, encoding="UTF-8", xml_declaration=True)

    if not silent:
        print(f"Game state saved to {filepath}")
    return True

def _get_next_session_filename():
    """Calculates the next session ID and returns the filename."""
    SAVE_DIRECTORY.mkdir(exist_ok=True)
    files = glob.glob(str(SAVE_DIRECTORY / "SESS-*.xml"))
    if not files:
        return "SESS-001.xml"
    max_id = max((int(f.split('-')[-1].split('.')[0]) for f in files if f.split('-')[-1].split('.')[0].isdigit()), default=0)
    return f"SESS-{max_id + 1:03d}.xml"

def get_latest_save_file():
    """Finds and returns the path to the most recent save file."""
    SAVE_DIRECTORY.mkdir(exist_ok=True)
    files = sorted(glob.glob(str(SAVE_DIRECTORY / "SESS-*.xml")), key=lambda f: f.lower(), reverse=True)
    return Path(files[0]) if files else None

def append_to_transcript(player_input, ai_output):
    """Appends the latest turn to the full transcript XML file."""
    if not TRANSCRIPT_FILE.exists():
        root = ET.Element("Transcript")
    else:
        try:
            tree = ET.parse(TRANSCRIPT_FILE)
            root = tree.getroot()
        except ET.ParseError:
            root = ET.Element("Transcript") # Recover from a corrupted file

    turn = ET.SubElement(root, "Turn", attrib={"timestamp": datetime.now().isoformat()})
    ET.SubElement(turn, "Player").text = player_input
    ET.SubElement(turn, "AI").text = str(ai_output if ai_output is not None else "")

    ET.indent(root, space="    ")
    ET.ElementTree(root).write(TRANSCRIPT_FILE, encoding="UTF-8", xml_declaration=True)

def extract_minimal_context(xml_string):
    """Extracts a brief summary from a session XML string for AI context."""
    try:
        root = ET.fromstring(xml_string)
        campaign = root.attrib.get("campaignName", "")
        location = root.attrib.get("currentLocation", "")
        recap = root.attrib.get("lastRecap", "")
        
        log_entries = root.find("Log")
        last_3_logs = []
        if log_entries is not None:
            entries = list(log_entries.findall(".//Entry"))
            for entry in entries[-3:]:
                content = entry.findtext("Content")
                if content:
                    last_3_logs.append(content.strip())
        recent_log = "\n".join(last_3_logs)

        return (
            f"Campaign: {campaign}\nLocation: {location}\n"
            f"Recap: {recap}\nRecent Events:\n{recent_log}"
        )
    except Exception as e:
        return f"(Error summarizing XML: {e})"

def summarize_all_sessions():
    """Summarizes all session XMLs for AI context."""
    summaries = []
    for xml_file in SAVE_DIRECTORY.glob("SESS-*.xml"):
        try:
            with open(xml_file, 'r', encoding="utf-8") as f:
                xml_str = f.read()
            summary = extract_minimal_context(xml_str)
            summaries.append(f"--- Session: {xml_file.name} ---\n{summary}")
        except Exception as e:
            summaries.append(f"--- Session: {xml_file.name} ---\n(Error reading: {e})")
    return "\n\n".join(summaries) if summaries else "No previous sessions."

def load_ai_config():
    """Loads the AI config file, creating it with defaults if it doesn't exist."""
    if not AI_CONFIG_FILE.exists():
        root = ET.Element("AIConfig")
        ET.SubElement(root, "PromptInstructions").text = (
            "You are a Dungeons and Dragons game master. Be imaginative, surprising, and vivid in your storytelling. Always consider all facts, logs, NPCs, items, and locations from all session XMLs before responding. Use concise, engaging, and creative storytelling. Always follow the rules and style in this config."
        )
        ET.SubElement(root, "MaxSentences").text = "5"
        ET.SubElement(root, "AlwaysTagEntities").text = "true"
        ET.indent(root, space="    ")
        ET.ElementTree(root).write(AI_CONFIG_FILE, encoding="UTF-8", xml_declaration=True)
    
    tree = ET.parse(AI_CONFIG_FILE)
    return tree.getroot()

def update_ai_config(key, value):
    """Update a key in ai_config.xml with a new value."""
    tree = ET.parse(AI_CONFIG_FILE)
    root = tree.getroot()
    elem = root.find(key)
    if elem is None:
        elem = ET.SubElement(root, key)
    elem.text = str(value)
    ET.indent(root, space="    ")
    ET.ElementTree(root).write(AI_CONFIG_FILE, encoding="UTF-8", xml_declaration=True)
    print(f"AI config updated: {key} = {value}")
