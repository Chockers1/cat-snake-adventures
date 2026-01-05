"""Pygbag entrypoint.

Pygbag builds the current folder and looks for a top-level `main.py`.
Pygbag requires an asyncio-aware main loop.
"""

from __future__ import annotations

import asyncio

from cat_snake_adventures.main import main


if __name__ == "__main__":
	asyncio.run(main())
