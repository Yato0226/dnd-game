# Dungeons & Dragons AI Game

## Overview
This project is an interactive Dungeons & Dragons game powered by AI. The game allows players to create characters, embark on adventures, and interact with an AI storyteller that generates narratives based on player actions and decisions.

## Project Structure
```
dnd-ai-game
├── src
│   ├── game.py                # Main game logic and interactive loop
│   ├── ai
│   │   ├── __init__.py        # Initializes the AI module
│   │   ├── rag.py             # Implements Retrieval Augmented Generation (RAG)
│   │   └── xml_editor.py      # Allows AI to edit its own XML for dynamic training
│   ├── data
│   │   ├── __init__.py        # Initializes the data module
│   │   └── xml_utils.py       # Utility functions for XML manipulation
│   └── utils
│       └── __init__.py        # Initializes the utils module
├── dnd_ai_sessions             # Directory for XML save files
├── requirements.txt            # Project dependencies
└── README.md                   # Project documentation
```

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```
   cd dnd-ai-game
   ```
3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage
1. Run the game:
   ```
   python src/game.py
   ```
2. Follow the on-screen instructions to create your character and start your adventure.

## Features
- **AI Storytelling**: The AI generates narratives based on player actions, enhancing the storytelling experience.
- **Dynamic Training**: The AI can edit its own XML files for continuous learning and improvement.
- **Retrieval Augmented Generation (RAG)**: The AI can access and retrieve information from XML files, providing contextually relevant responses.

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.