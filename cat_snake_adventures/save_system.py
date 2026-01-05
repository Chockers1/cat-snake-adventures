from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .player import PlayerProfile
from .display_utils import toggle_fullscreen


class SaveSystem:
	def __init__(self, saves_dir: Path | None = None) -> None:
		if saves_dir is not None:
			self.saves_dir = saves_dir
		else:
			# In web builds (pygbag/emscripten), the packaged folder isn't reliably writable.
			# Use a temp-like location instead.
			if sys.platform == "emscripten":
				self.saves_dir = Path("/tmp") / "cat_snake_saves"
			else:
				self.saves_dir = Path(__file__).parent / "saves"
		self.saves_dir.mkdir(parents=True, exist_ok=True)

	def _profile_path(self, player_name: str) -> Path:
		# Keep filenames simple for kids.
		safe = "".join(ch for ch in player_name.strip() if ch.isalnum() or ch in (" ", "-", "_"))
		safe = safe.strip() or "Player"
		return self.saves_dir / f"{safe}.json"

	def load(self, player_name: str) -> PlayerProfile | None:
		path = self._profile_path(player_name)
		if not path.exists():
			return None
		data = json.loads(path.read_text(encoding="utf-8"))
		if not isinstance(data, dict):
			return None

		# Forward/backward compatible loads: ignore unknown keys and use defaults for missing keys.
		defaults = PlayerProfile(player_name=str(data.get("player_name", player_name)))
		allowed = set(defaults.__dict__.keys())
		filtered = {k: v for k, v in data.items() if k in allowed}
		profile = PlayerProfile(**{**defaults.__dict__, **filtered})
		profile.ensure_skin_valid()
		return profile

	def save(self, profile: PlayerProfile) -> None:
		path = self._profile_path(profile.player_name)
		path.write_text(json.dumps(asdict(profile), indent=2), encoding="utf-8")

	def list_players(self) -> list[str]:
		players: list[str] = []
		for file in sorted(self.saves_dir.glob("*.json")):
			if file.stem.lower() == "leaderboard":
				continue
			players.append(file.stem)
		return players

	async def ensure_player_profile(self, pygame_module, screen) -> PlayerProfile:
		# Simple, kid-friendly: ask once on first launch.
		players = self.list_players()
		if players:
			# Auto-pick the first profile for now.
			loaded = self.load(players[0])
			if loaded:
				return loaded

		name = await self._prompt_name(pygame_module, screen)
		profile = PlayerProfile(player_name=name)
		self.save(profile)
		return profile

	async def choose_player_profile(self, pygame_module, screen, current: PlayerProfile | None = None) -> PlayerProfile | None:
		pygame = pygame_module
		pygame.display.set_caption("Cat Snake Adventures - Choose Player")

		font_title = pygame.font.SysFont(None, 68)
		font_item = pygame.font.SysFont(None, 52)
		font_hint = pygame.font.SysFont(None, 30)
		clock = pygame.time.Clock()

		bg = (245, 250, 255)
		surface = (255, 255, 255)
		surface_2 = (250, 250, 252)
		text = (25, 30, 45)
		muted = (90, 98, 120)
		primary = (30, 120, 60)
		border = (210, 215, 225)

		players = self.list_players()
		items: list[str] = players + ["+ New Player"]

		# Debug: ensure items list is not empty
		if not items:
			items = ["+ New Player"]

		selected = 0
		if current is not None and current.player_name in players:
			selected = players.index(current.player_name)

		while True:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					return None
				if event.type == pygame.KEYDOWN:
					if event.key == pygame.K_F11:
						toggle_fullscreen(pygame)
						screen = pygame.display.get_surface() or screen
					if event.key == pygame.K_ESCAPE:
						pygame.display.set_caption("Cat Snake Adventures")
						return None
					if event.key in (pygame.K_UP, pygame.K_w):
						selected = (selected - 1) % len(items)
					if event.key in (pygame.K_DOWN, pygame.K_s):
						selected = (selected + 1) % len(items)
					if event.key in (pygame.K_RETURN, pygame.K_SPACE):
						choice = items[selected]
						if choice == "+ New Player":
							name = await self._prompt_name(pygame, screen)
							profile = self.load(name)
							if profile is None:
								profile = PlayerProfile(player_name=name)
								self.save(profile)
							pygame.display.set_caption("Cat Snake Adventures")
							return profile

						profile = self.load(choice)
						if profile is None:
							profile = PlayerProfile(player_name=choice)
							self.save(profile)
						pygame.display.set_caption("Cat Snake Adventures")
						return profile

			w = screen.get_width()
			h = screen.get_height()
			screen.fill(bg)
			title = font_title.render("Choose Player", True, text)
			hint = font_hint.render("Up/Down + Enter • Esc back • F11 fullscreen", True, muted)
			screen.blit(title, ((w - title.get_width()) // 2, 70))
			screen.blit(hint, ((w - hint.get_width()) // 2, 140))

			button_w = min(680, max(460, w - 220))
			button_h = 66
			x = (w - button_w) // 2
			gap = 14
			start_y = 220

			for i, player_name in enumerate(items):
				y = start_y + i * (button_h + gap)
				rect = pygame.Rect(x, y, button_w, button_h)
				is_selected = i == selected
				fill = surface if is_selected else surface_2
				b = primary if is_selected else border
				pygame.draw.rect(screen, fill, rect, border_radius=16)
				pygame.draw.rect(screen, b, rect, width=4 if is_selected else 2, border_radius=16)

				label = font_item.render(player_name, True, primary if is_selected else (25, 30, 45))
				screen.blit(label, (rect.x + 24, rect.y + 14))

			pygame.display.flip()
			clock.tick(60)
			await asyncio.sleep(0)

	async def _prompt_name(self, pygame_module, screen) -> str:
		pygame = pygame_module
		pygame.display.set_caption("Cat Snake Adventures - Player Name")

		font = pygame.font.SysFont(None, 56)
		small = pygame.font.SysFont(None, 34)
		clock = pygame.time.Clock()

		bg = (245, 250, 255)
		surface = (255, 255, 255)
		text = (25, 30, 45)
		muted = (90, 98, 120)
		primary = (30, 120, 60)
		border = (210, 215, 225)

		name = ""
		running = True
		while running:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					running = False
				elif event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						running = False
					elif event.key == pygame.K_F11:
						toggle_fullscreen(pygame)
						screen = pygame.display.get_surface() or screen
					elif event.key == pygame.K_RETURN:
						if name.strip():
							pygame.display.set_caption("Cat Snake Adventures")
							return name.strip()
					elif event.key == pygame.K_BACKSPACE:
						name = name[:-1]
					else:
						ch = event.unicode
						if ch.isprintable() and len(name) < 16:
							name += ch

			w = screen.get_width()
			h = screen.get_height()
			screen.fill(bg)
			title = font.render("What is your name?", True, text)
			prompt = small.render("Type your name, then press Enter (F11 fullscreen)", True, muted)
			screen.blit(title, ((w - title.get_width()) // 2, 120))
			screen.blit(prompt, ((w - prompt.get_width()) // 2, 200))

			box_w = min(640, max(420, w - 240))
			box_h = 84
			box_rect = pygame.Rect((w - box_w) // 2, 300, box_w, box_h)
			pygame.draw.rect(screen, surface, box_rect, border_radius=16)
			pygame.draw.rect(screen, border, box_rect, width=2, border_radius=16)
			box = font.render(name or "_", True, primary)
			screen.blit(box, (box_rect.x + 24, box_rect.y + 18))

			pygame.display.flip()
			clock.tick(60)
			await asyncio.sleep(0)

		pygame.display.set_caption("Cat Snake Adventures")
		return "Player"
