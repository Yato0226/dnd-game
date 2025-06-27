# Dungeons & Dragons AI Game

## Overview
This project is an interactive Dungeons & Dragons game powered by AI. The game allows players to create characters, embark on adventures, and interact with an AI storyteller that generates narratives based on player actions and decisions.

## Project Structure
```
dnd_ai_game
├── main.py                       # Entry point to start the game
├── README.md                     # Project documentation
├── requirements.txt              # Project dependencies
├── dnd_ai_sessions/              # Directory for XML save files
└── src
    ├── __init__.py
    ├── config.py                 # Central configuration and constants
    ├── ai/
    │   ├── __init__.py
    │   ├── ai_logic.py           # AI prompt construction and response parsing
    │   ├── rag.py                # Retrieval Augmented Generation (RAG) placeholder
    │   └── xml_editor.py         # Tools for AI to edit XML files
    ├── data/
    │   ├── __init__.py
    │   └── xml_utils.py          # XML utility functions
    ├── game/
    │   ├── __init__.py
    │   └── game_logic.py         # Main game loop and mechanics
    └── utils/
        ├── __init__.py
        ├── data_manager.py       # Handles game state and transcript I/O
        └── system_utils.py       # Ollama process management
```

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```
   cd dnd_ai_game
   ```
3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage
1. Run the game:
   ```
   python dnd_ai_game/main.py
   ```
2. Follow the on-screen instructions to create your character and start your adventure.

## Features
- **AI Storytelling**: The AI generates narratives based on player actions, enhancing the storytelling experience.
- **Dynamic Training**: The AI can edit its own XML files for continuous learning and improvement.
- **Retrieval Augmented Generation (RAG)**: The AI can access and retrieve information from XML files, providing contextually relevant responses.
- **Session Management**: Save and load your progress using XML files.
- **Transcript Logging**: All interactions are logged for review.

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.