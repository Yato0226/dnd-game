# AI D&D Storyteller

An **interactive, AI-powered Dungeons & Dragons solo adventure game** designed for single players. Immerse yourself in a dynamic narrative where you take on the role of a lone adventurer, and an AI, powered by [Ollama](https://ollama.com/) and the `phi3:mini` model, seamlessly steps into the role of your Dungeon Master. This game brings the classic tabletop experience to your computer, adapting the story and presenting choices based on your character's actions and the luck of the dice.

---

## Features

-   **AI Dungeon Master:** At the core of the experience, **Ollama** leverages the efficient `phi3:mini` model to generate rich, evolving story outcomes and present you with compelling choices, making each playthrough unique.
-   **Dynamic Dice Mechanics:** Every significant action your character takes is resolved with a **d20 roll**, directly influencing the AI's narrative and determining the success or failure of your endeavors.
-   **Robust Session Management:** Never lose your progress. The game allows you to **save and load your game state as XML files**, ensuring you can pick up your adventure right where you left off.
-   **Comprehensive Session Transcript:** All interactions, from your character's actions to the AI's narrative responses, are **logged in a transcript** for easy review, allowing you to retrace your journey and decisions.
-   **Manual Fallback Option:** In cases where Ollama or its Python library might be unavailable, the game gracefully offers a **manual mode**, ensuring you can still engage with the story without AI assistance. This provides flexibility and resilience.

---

## Requirements

-   **Python 3.8 or newer:** Essential for running the game's core logic.
-   **Ollama installed and running:** The backbone for the AI Dungeon Master. Ensure it's installed and the server is active.
-   `ollama` **Python package:** (`pip install ollama`) This Python library facilitates communication between the game and your local Ollama instance.

---

## Setup

Getting started with your adventure is straightforward:

1.  **Install Python dependencies:** Open your terminal or command prompt and run:
    ```sh
    pip install ollama
    ```

2.  **Install and start Ollama:**
    -   Download and install the **Ollama application** from [Ollama’s official website](https://ollama.com/).
    -   Once installed, ensure the Ollama server is running. You can typically start it by typing the following in your command prompt:
        ```sh
        ollama serve
        ```
        Keep this window open while playing the game.

3.  **Run the game:** Navigate to the directory where you've saved `game.py` in your terminal and execute:
    ```sh
    python game.py
    ```

---

## How to Play

Upon launching the game, you'll be greeted with a choice to **start a new adventure or load your latest saved game**.

-   **Character Creation:** If starting fresh, you'll be prompted to **enter your character’s details**, including their name, race, class, and any other attributes relevant to your unique hero.
-   **Interactive Turns:** Each turn, the AI Dungeon Master will describe your current situation. You'll then **type what your character does** (e.g., "search the room for clues", "talk to the innkeeper about local rumors", "attack the goblin").
-   **AI-Driven Outcomes:** The game will automatically **roll a d20** based on your action. The AI will then interpret this roll and your input to narrate the outcome, presenting you with **new choices** for your next move, continuing the unfolding story.
-   **Saving and Exiting:**
    -   To **save your current progress**, simply type `save` at any prompt.
    -   To **exit the game**, type `quit`.

---

## File Structure

- **main.py**: A clean entry point that simply starts the game loop.

- **dnd_ai_game/src/config.py**: Centralizes all constants and default settings for easy modification.

- **dnd_ai_game/src/utils/**: Contains helper modules.
    - **system_utils.py**: Manages OS-level tasks like checking and controlling the Ollama process.
    - **data_manager.py**: Handles all file I/O, including loading/saving XML game states and transcripts.

- **dnd_ai_game/src/ai/**: Contains all AI-related logic.
    - **rag.py**: A placeholder for your Retrieval-Augmented Generation system.
    - **ai_logic.py**: Constructs prompts, interacts with the Ollama API, and parses the AI's responses.

- **dnd_ai_game/src/game/**: Contains the core game mechanics.
    - **game_logic.py**: Manages the main game loop, player commands, character creation, and the overall game_state.

---

## Customizing the AI Model

The game is designed to be flexible regarding the underlying AI model. While `phi3:mini` via Ollama is the default, you can potentially adapt the code to use other local or cloud-based Large Language Models (LLMs).

To switch models or providers, you'll typically need to **modify the `game.py` file**. Look for the section responsible for making API calls to Ollama (e.g., `ollama.chat` or `ollama.generate`).

Here's a general guide:

1.  **Identify the AI Integration Code:** Locate the function or class within `game.py` that handles sending prompts to the AI model and receiving its responses. This will likely involve imports from the `ollama` Python package.
2.  **Replace with Your Desired Model's API:**
    * **For other Ollama models:** Simply change the `model` parameter in the Ollama API call (e.g., from `'phi3:mini'` to `'llama3'`, ensuring you have the new model pulled via `ollama pull llama3`).
    * **For different local LLMs (e.g., through `transformers` library, `llama.cpp` integrations):** You would need to replace the Ollama-specific code with the appropriate library and function calls for your chosen local model. This might involve different setup steps for that specific model.
    * **For cloud-based LLMs (e.g., OpenAI, Anthropic, Google Gemini):** You would replace the Ollama integration with the respective Python SDK calls for that service. This would also require installing their specific Python packages (`pip install openai`, `pip install anthropic`, etc.) and managing API keys.
3.  **Adjust Prompt Formatting:** Different models may respond best to specific prompt formats (e.g., system messages, user messages, conversational turns). You might need to adjust how the game constructs prompts to optimize responses from your new model.

**Note:** This customization requires a basic understanding of Python programming and API interactions. Support for specific alternative models is not built-in and would require manual code changes by the user.

---

## Troubleshooting

Encountering an issue? Here are some common solutions:

-   **Ollama Not Running:** If you receive a message indicating that Ollama isn't active, ensure you've started the Ollama server by running `ollama serve` in a dedicated terminal window.
-   **Missing Python Package:** If the `ollama` Python package is reported as missing, install it using `pip install ollama`.
-   **Playing Without AI:** Should you wish to play the game without the AI Dungeon Master (e.g., for testing or a more traditional text-adventure experience), you can simply proceed in **manual mode** when prompted.

---


## Credits

-   **Powered by [Ollama](https://ollama.com/)** and specifically utilizing the `phi3:mini` model for its generative capabilities.
-   **Created by [Yato]**
