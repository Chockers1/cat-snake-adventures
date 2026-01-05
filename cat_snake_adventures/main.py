from __future__ import annotations

import asyncio
import sys

import pygame

from .save_system import SaveSystem
from .ui import MainMenu, CatSelectScreen, HighScoresScreen, HowToPlayScreen
from .game_loop import GameLoop
from .high_scores import build_high_score_rows


async def main() -> int:
	pygame.init()
	try:
		pygame.mixer.init()
	except Exception:
		# Browsers may block audio until first user interaction.
		pass

	is_web = sys.platform == "emscripten"
	flags = 0 if is_web else pygame.RESIZABLE
	screen = pygame.display.set_mode((960, 720), flags)
	pygame.display.set_caption("Cat Snake Adventures")

	save_system = SaveSystem()
	player_profile = await save_system.ensure_player_profile(pygame, screen)

	menu = MainMenu(screen=screen)
	cat_select = CatSelectScreen(screen=screen)
	high_scores = HighScoresScreen(screen=screen)
	how_to_play = HowToPlayScreen(screen=screen)

	while True:
		choice = await menu.run(player_profile)
		if choice == "quit":
			break
		if choice == "change_player":
			picked = await save_system.choose_player_profile(pygame, screen, current=player_profile)
			if picked is not None:
				player_profile = picked
			continue
		if choice == "how_to_play":
			await how_to_play.run()
			continue
		if choice == "high_scores":
			rows = build_high_score_rows(save_system)
			await high_scores.run(rows)
			continue
		if choice == "choose_cat":
			picked = await cat_select.run(player_profile)
			if picked and picked in player_profile.unlocked_skins:
				player_profile.selected_skin = picked
				save_system.save(player_profile)
			continue
		if choice == "play":
			game = GameLoop(screen=screen, save_system=save_system, profile=player_profile)
			await game.run()
			continue

	pygame.quit()
	return 0


if __name__ == "__main__":
	asyncio.run(main())
