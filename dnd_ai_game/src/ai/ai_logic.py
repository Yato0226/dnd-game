# dnd_ai_game/src/ai/ai_logic.py
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

try:
    import ollama
except ImportError:
    ollama = None

from dnd_ai_game.src.config import MODEL, DEFAULTS
from dnd_ai_game.src.utils.data_manager import (
    extract_minimal_context, 
    summarize_all_sessions, 
    load_ai_config,
    update_ai_config
)

def summarize_memory_facts(game_state):
    """Generates a summary of the most recent memory facts from the game state."""
    memory_facts = game_state.get("Memory", {}).get("Fact", [])
    if not memory_facts:
        return "None yet."
    summary_lines = []
    # Summarize the last 3 facts
    for fact in memory_facts[-3:]:
        player_input = fact.get('player_input', '[No Input Recorded]')
        ai_response = fact.get('ai_response', '[No Response Recorded]')
        ai_response_str = str(ai_response)
        summary_lines.append(f"- Player: {player_input}\n  AI: {ai_response_str.splitlines()[0] if ai_response_str else ''}")
    return "\n".join(summary_lines)

def get_ai_narrative(game_state, player_input_text, roll_result, rag_context=""):
    """Constructs a prompt and gets a narrative response from the AI."""
    print("\n--- AI Turn ---")
    if ollama is None:
        print("CRITICAL: 'ollama' library not found. Cannot generate AI narrative.")
        return "The world remains silent, as the AI storyteller is unavailable."
        
    try:
        player_name = game_state.get("playerName", DEFAULTS["name"])
        player_gender = game_state.get("playerGender", DEFAULTS["gender"]).lower()
        pronoun = "he" if player_gender == "male" else "she" if player_gender == "female" else "they"

        player_context = (
            f"Name: {player_name}\n"
            f"Gender: {game_state.get('playerGender', DEFAULTS['gender']).capitalize()}\n"
            f"Race: {game_state.get('playerRace', DEFAULTS['race'])}\n"
            f"Class: {game_state.get('playerClass', DEFAULTS['class'])}\n"
            f"Background: {game_state.get('playerBackground', DEFAULTS['background'])}\n"
            f"Pronoun to use for player: {pronoun}\n"
            f"Stats: {', '.join(f'{k}: {v}' for k, v in game_state.get('playerStats', {}).items())}\n"
            f"Inventory: {', '.join(game_state.get('playerInventory', [])) or 'None'}"
        )

        # Create a temporary XML string of the current state for context
        from dnd_ai_game.src.utils.data_manager import save_game_state
        from pathlib import Path
        temp_path = Path("__temp_context.xml")
        save_game_state(game_state, temp_path, silent=True)
        with open(temp_path, 'r', encoding='utf-8') as f:
            current_session_xml_string_context = f.read()
        temp_path.unlink()

        context_summary = extract_minimal_context(current_session_xml_string_context)
        memory_summary = summarize_memory_facts(game_state)
        
        roll_context = f"The player rolled a d20 and got: {roll_result}.\n"
        if roll_result == 1: roll_context += "This is a CRITICAL FAILURE. The action should fail spectacularly, with negative consequences."
        elif roll_result <= 5: roll_context += "This is a significant failure. The action fails, and there may be a minor complication."
        elif roll_result <= 10: roll_context += "This is a failure. The action does not succeed, but doesn't necessarily make things worse."
        elif roll_result <= 15: roll_context += "This is a modest success. The action succeeds, but not perfectly or completely."
        elif roll_result < 20: roll_context += "This is a clear success. The action works as intended."
        elif roll_result == 20: roll_context += "This is a CRITICAL SUCCESS. The action succeeds spectacularly, with an added bonus or benefit."

        ai_config = load_ai_config()
        prompt_instructions = ai_config.findtext("PromptInstructions", "")
        max_sentences = ai_config.findtext("MaxSentences", "5")
        
        prompt_for_ai = (
            f"{prompt_instructions}\n\n"
            f"== RAG Retrieved Info ==\n{rag_context}\n\n"
            f"== Player Character ==\n{player_context}\n\n"
            f"== Current Memory ==\n{memory_summary}\n\n"
            f"== Current Situation ==\n{context_summary}\n\n"
            f"== Player's Action ==\n{player_input_text}\n\n"
            f"== Dice Roll Result ==\n{roll_context}\n\n"
            f"== Important Game Elements ==\n"
            f"NPCs: {', '.join(game_state.get('KeyNPCs', [])) or 'None'}\n"
            f"Locations: {', '.join(game_state.get('KeyLocations', [])) or 'None'}\n"
            f"Items: {', '.join(game_state.get('KeyItems', [])) or 'None'}\n\n"
            f"== Summary of All Previous Sessions ==\n{summarize_all_sessions()}\n\n"
            f"== Instructions ==\n"
            f"You MUST consider all provided information. Limit your response to {max_sentences} sentences. "
            f"Always end with a numbered list of 2-3 choices for the player. "
            f"Tag new entities with [NPC], [LOCATION], or [ITEM]. Tag merchants/shops with [MERCHANT]. "
            f"If the player takes damage, state it as DAMAGE: <number>. If a skill is tested, state it as SKILL: <SkillName>."
        )

        # Use ollama.chat for better-structured conversations
        response = ollama.chat(
            model=MODEL,
            messages=[{'role': 'user', 'content': prompt_for_ai}],
        )
        ai_response_text = response['message']['content']

    except Exception as e:
        print(f"Error communicating with Ollama: {e}")
        ai_response_text = f"The AI storyteller stumbles, its words lost to the ether. (Error: {e})"
    
    print("--- End AI Turn ---")
    return ai_response_text

def get_ai_event(game_state, rag_context=""):
    """Generates a dynamic world event using the AI."""
    print("\n--- Generating World Event ---")
    if ollama is None:
        return None
    try:
        from dnd_ai_game.src.utils.data_manager import save_game_state
        from pathlib import Path
        temp_path = Path("__temp_context.xml")
        save_game_state(game_state, temp_path, silent=True)
        with open(temp_path, 'r', encoding='utf-8') as f:
            context_xml = f.read()
        temp_path.unlink()
        
        ai_config = load_ai_config()
        
        prompt = (
            f"As a D&D game master, generate a random, story-relevant world event. "
            f"It should fit the campaign context provided below. Describe the event in 3 sentences or less. "
            f"Do not ask for player input. This event happens in the background.\n\n"
            f"== RAG Retrieved Info ==\n{rag_context}\n\n"
            f"== Current Situation ==\n{extract_minimal_context(context_xml)}\n\n"
            f"== Summary of All Previous Sessions ==\n{summarize_all_sessions()}\n"
        )
        
        response = ollama.chat(
            model=MODEL,
            messages=[{'role': 'user', 'content': prompt}],
        )
        return response['message']['content']
    except Exception as e:
        print(f"Error generating world event: {e}")
        return None

def extract_keywords_from_ai_output(ai_output):
    """Extracts tagged keywords like [NPC], [LOCATION], [ITEM] from AI text."""
    if not ai_output: return {}
    npcs = re.findall(r"([\w\s'-]+)\s*\[NPC\]", ai_output, re.IGNORECASE)
    locations = re.findall(r"([\w\s'-]+)\s*\[LOCATION\]", ai_output, re.IGNORECASE)
    items = re.findall(r"([\w\s'-]+)\s*\[ITEM\]", ai_output, re.IGNORECASE)
    merchants = re.findall(r"([\w\s'-]+)\s*\[MERCHANT\]", ai_output, re.IGNORECASE)
    
    # Add merchants to both NPCs and Locations for broader context
    return {
        "KeyNPCs": [npc.strip() for npc in npcs + merchants],
        "KeyLocations": [loc.strip() for loc in locations + merchants],
        "KeyItems": [item.strip() for item in items]
    }

def extract_skill_from_ai_output(ai_output):
    """Extracts a SKILL: <SkillName> tag from the AI's output."""
    if not ai_output: return None
    match = re.search(r"SKILL:\s*([A-Za-z\s]+)", ai_output, re.IGNORECASE)
    return match.group(1).strip() if match else None

def parse_and_apply_ai_config_command(ai_output):
    """Detects and applies CONFIG: Set <Key>=<Value> in AI output."""
    if not ai_output: return
    match = re.search(r"CONFIG:\s*Set\s+(\w+)\s*=\s*([^\n\r]+)", ai_output, re.IGNORECASE)
    if match:
        key, value = match.group(1), match.group(2).strip()
        update_ai_config(key, value)