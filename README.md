<div align="center">

# 🐱 Cat Snake Adventures

### *A Purrfectly Fun Snake Game*

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Pygame](https://img.shields.io/badge/pygame-2.5.2%2B-green.svg)](https://www.pygame.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

**A delightful twist on the classic Snake game, featuring adorable cats, exciting power-ups, and progressively challenging levels!**

[Features](#-features) • [Installation](#-installation) • [How to Play](#-how-to-play) • [Controls](#-controls) • [Development](#-development)

</div>

---

## ✨ Features

### 🎮 Core Gameplay
- **Multiple Levels**: Progress through 11+ unique levels with increasing difficulty
- **Dynamic Backgrounds**: Each level features custom themed backgrounds
- **Save System**: Multiple player profiles with persistent progress
- **High Score Leaderboard**: Track your best performances across all players

### 🐈 Customization
- **Cat Skins**: Choose from multiple adorable cat varieties:
  - Classic Cat (orange tabby)
  - Black Cat (sleek and mysterious)
  - Ginger Cat (fluffy and friendly)
- **Unlockable Content**: Unlock new skins as you progress

### 🍖 Food & Power-ups
- **Fish**: Standard food that grows your cat
- **Mouse**: Quick snacks for bonus points
- **Smoked Salmon**: Premium treats with extra rewards
- **Special Effects**: Mud, slime, zoomies, and skateboard power-ups

### 🎵 Audio & Visual Polish
- **Sound Effects**: Satisfying eating sounds and game audio
- **Custom Graphics**: Hand-crafted pixel art for all game elements
- **Smooth Animations**: Fluid movement and visual feedback
- **Responsive UI**: Intuitive menus and player interfaces

---

## 🚀 Installation

### Prerequisites
- **Python 3.11** or higher
- **pip** package manager

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/Chockers1/cat-snake-adventures.git
   cd cat-snake-adventures
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**
   - **Windows**:
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - **macOS/Linux**:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the game**
   ```bash
   python -m cat_snake_adventures.main
   ```

   Or use the convenience launcher (Windows):
   ```bash
   run_game.bat
   ```

---

## 🎮 How to Play

### Objective
Guide your cat to eat food and grow longer while avoiding:
- 🧱 Walls and boundaries
- 🐍 Your own tail
- ⚠️ Special obstacles in later levels

### Progression
- Start at Level 1 and complete objectives to advance
- Each level introduces new challenges and mechanics
- Collect special items for power-ups and bonus effects
- Build your high score and compete on the leaderboard

### Tips for Success
- 💡 Plan your path ahead to avoid trapping yourself
- 🎯 Aim for high-value food items when safe
- ⚡ Use power-ups strategically
- 🏆 Master each level before attempting speed runs

---

## 🎹 Controls

| Action | Keys |
|--------|------|
| **Move Up** | `↑` or `W` |
| **Move Down** | `↓` or `S` |
| **Move Left** | `←` or `A` |
| **Move Right** | `→` or `D` |
| **Pause Game** | `P` |
| **Quit** | `ESC` |

---

## 🌐 Browser Build (WebAssembly)

Deploy Cat Snake Adventures to the web using [pygbag](https://github.com/pygame-web/pygbag):

1. **Install pygbag**
   ```bash
   pip install pygbag
   ```

2. **Build for web**
   ```bash
   pygbag .
   ```

3. **Deploy to Itch.io**
   - Upload the contents of `build/web/` to [Itch.io](https://itch.io/)
   - Set the project type to **HTML**
   - Enable **"This file will be played in the browser"**

The game runs entirely in the browser with no installation required!

---

## 🛠️ Development

### Project Structure
```
cat-snake-adventures/
├── cat_snake_adventures/       # Main game package
│   ├── main.py                # Entry point
│   ├── game_loop.py           # Core game logic
│   ├── player.py              # Cat/snake mechanics
│   ├── food.py                # Food items and spawning
│   ├── levels.py              # Level definitions
│   ├── skins.py               # Cat skin system
│   ├── ui.py                  # Menu and UI screens
│   ├── save_system.py         # Player profiles & persistence
│   ├── high_scores.py         # Leaderboard system
│   ├── sounds.py              # Audio management
│   └── assets/                # Graphics and audio files
├── requirements.txt           # Python dependencies
├── main.py                    # Alternative entry point
└── README.md                  # This file
```

### Save Files
Player profiles and game progress are stored in `cat_snake_adventures/saves/` as JSON files:
- `<player_name>.json`: Individual player progress, unlocks, and stats
- `leaderboard.json`: High scores across all players

### Adding New Content
- **Levels**: Edit `levels.py` to add new level configurations
- **Skins**: Add new cat sprites to `assets/cats/` and register in `skins.py`
- **Food Types**: Extend `food.py` with new food mechanics
- **Power-ups**: Implement new effects in the game loop

---

## 📋 Requirements

- **Python**: 3.11+
- **pygame**: 2.5.2+
- **pygbag**: (optional, for web builds)

---

## 🤝 Contributing

Contributions are welcome! Whether it's:
- 🐛 Bug fixes
- ✨ New features
- 🎨 Graphics improvements
- 📖 Documentation enhancements

Please feel free to open issues or submit pull requests.

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

## 🎉 Acknowledgments

- Built with [Pygame](https://www.pygame.org/)
- Web deployment powered by [pygbag](https://github.com/pygame-web/pygbag)
- Inspired by the classic Snake game

---

<div align="center">

**Made with 💚 and 🐱**

[⬆ Back to Top](#-cat-snake-adventures)

</div>
