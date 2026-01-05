# Cat Snake Adventures

A kid-friendly Snake-style game built with Python + Pygame.

## Setup (Windows)

1. Install Python 3.11+
2. Create and activate a virtualenv (optional)
3. Install dependencies:

```powershell
pip install -r requirements.txt
```

## Run

```powershell
python -m cat_snake_adventures.main
```

## Browser Build (Itch.io) via pygbag

You can package the game to run in a browser (WebAssembly) using `pygbag`.

```powershell
pip install pygbag
pygbag .
```

After building, upload the contents of `build/web/` to Itch.io as an **HTML** game
and enable **This file will be played in the browser**.

## Controls

- Move: Arrow keys or WASD
- Pause: P
- Quit: Esc

## Save Files

Player profiles are stored as JSON in `cat_snake_adventures/saves/`.
