from __future__ import annotations

import asyncio
import pygame

from .skins import SKINS, LEVEL_UNLOCKS, get_skin_display_name
from .display_utils import toggle_fullscreen


# Simple "modern" palette (kept minimal and consistent).
_BG = (245, 250, 255)
_SURFACE = (255, 255, 255)
_SURFACE_2 = (250, 250, 252)
_TEXT = (25, 30, 45)
_MUTED = (90, 98, 120)
_PRIMARY = (30, 120, 60)
_BORDER = (210, 215, 225)


def _draw_card(surface: pygame.Surface, rect: pygame.Rect, *, fill, border, border_w: int, radius: int) -> None:
	pygame.draw.rect(surface, fill, rect, border_radius=radius)
	pygame.draw.rect(surface, border, rect, width=border_w, border_radius=radius)


class MainMenu:
	def __init__(self, screen: pygame.Surface) -> None:
		self.screen = screen
		self.clock = pygame.time.Clock()
		self.title_font = pygame.font.SysFont(None, 72)
		self.item_font = pygame.font.SysFont(None, 52)
		self.hint_font = pygame.font.SysFont(None, 30)

	async def run(self, profile) -> str:
		selected = 0
		items = ["Play", "Change Player", "Choose Cat", "High Scores", "How to Play", "Quit"]

		running = True
		while running:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					return "quit"
				if event.type == pygame.KEYDOWN:
					if event.key in (pygame.K_ESCAPE,):
						return "quit"
					if event.key == pygame.K_F11:
						toggle_fullscreen(pygame)
						self.screen = pygame.display.get_surface() or self.screen
					if event.key in (pygame.K_UP, pygame.K_w):
						selected = (selected - 1) % len(items)
					if event.key in (pygame.K_DOWN, pygame.K_s):
						selected = (selected + 1) % len(items)
					if event.key in (pygame.K_RETURN, pygame.K_SPACE):
						choice = items[selected].lower()
						if choice == "play":
							return "play"
						if choice == "change player":
							return "change_player"
						if choice == "choose cat":
							return "choose_cat"
						if choice == "high scores":
							return "high_scores"
						if choice == "how to play":
							return "how_to_play"
						return "quit"

			self._draw(profile, items, selected)
			pygame.display.flip()
			self.clock.tick(60)
			await asyncio.sleep(0)

		return "quit"

	def _draw(self, profile, items: list[str], selected_index: int) -> None:
		w = self.screen.get_width()
		h = self.screen.get_height()
		self.screen.fill(_BG)
		title = self.title_font.render("Cat Snake Adventures", True, _TEXT)
		welcome = self.hint_font.render(f"Player: {profile.player_name}", True, _MUTED)
		hint = self.hint_font.render("Up/Down + Enter   (F11 fullscreen)", True, _MUTED)

		title_x = (w - title.get_width()) // 2
		self.screen.blit(title, (title_x, 64))
		self.screen.blit(welcome, (title_x, 134))

		button_w = min(640, max(420, w - 220))
		button_h = 68
		x = (w - button_w) // 2
		gap = 14
		start_y = 220

		for i, text in enumerate(items):
			y = start_y + i * (button_h + gap)
			rect = pygame.Rect(x, y, button_w, button_h)
			selected = i == selected_index
			fill = _SURFACE if selected else _SURFACE_2
			border = _PRIMARY if selected else _BORDER
			_draw_card(self.screen, rect, fill=fill, border=border, border_w=4 if selected else 2, radius=16)

			label = self.item_font.render(text, True, _PRIMARY if selected else _TEXT)
			self.screen.blit(label, (rect.x + 24, rect.y + 14))

		self.screen.blit(hint, (x, h - 44))


class HowToPlayScreen:
	def __init__(self, screen: pygame.Surface) -> None:
		self.screen = screen
		self.clock = pygame.time.Clock()
		self.title_font = pygame.font.SysFont(None, 68)
		self.font = pygame.font.SysFont(None, 36)

	async def run(self) -> None:
		while True:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					return
				if event.type == pygame.KEYDOWN:
					if event.key == pygame.K_F11:
						toggle_fullscreen(pygame)
						self.screen = pygame.display.get_surface() or self.screen
					if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
						return

			w = self.screen.get_width()
			h = self.screen.get_height()
			self.screen.fill(_BG)
			title = self.title_font.render("How to Play", True, _TEXT)
			self.screen.blit(title, ((w - title.get_width()) // 2, 70))

			lines = [
				"Move: Arrow Keys or WASD",
				"Pause: P",
				"Eat food to grow longer!",
				"Don’t crash into walls or your tail.",
				"Smoked Salmon is rare and sparkly!",
				"New cats unlock at higher levels (like Level 3!)",
				"Press Esc to go back.",
			]
			card_w = min(820, max(520, w - 180))
			card_h = min(420, h - 260)
			card = pygame.Rect((w - card_w) // 2, 170, card_w, card_h)
			_draw_card(self.screen, card, fill=_SURFACE, border=_BORDER, border_w=2, radius=18)

			y = card.y + 26
			for line in lines:
				txt = self.font.render(line, True, _TEXT)
				self.screen.blit(txt, (card.x + 28, y))
				y += 48

			pygame.display.flip()
			self.clock.tick(60)
			await asyncio.sleep(0)


class CatSelectScreen:
	def __init__(self, screen: pygame.Surface) -> None:
		self.screen = screen
		self.clock = pygame.time.Clock()
		self.title_font = pygame.font.SysFont(None, 68)
		self.font = pygame.font.SysFont(None, 32)
		self.small = pygame.font.SysFont(None, 28)

	async def run(self, profile) -> str | None:
		# Returns selected skin key, or None if cancelled.
		index = 0
		cols = 4
		while True:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					return None
				if event.type == pygame.KEYDOWN:
					if event.key in (pygame.K_ESCAPE,):
						return None
					if event.key == pygame.K_F11:
						toggle_fullscreen(pygame)
						self.screen = pygame.display.get_surface() or self.screen
					if event.key in (pygame.K_LEFT, pygame.K_a):
						index = max(0, index - 1)
					if event.key in (pygame.K_RIGHT, pygame.K_d):
						index = min(len(SKINS) - 1, index + 1)
					if event.key in (pygame.K_UP, pygame.K_w):
						index = max(0, index - cols)
					if event.key in (pygame.K_DOWN, pygame.K_s):
						index = min(len(SKINS) - 1, index + cols)
					if event.key in (pygame.K_RETURN, pygame.K_SPACE):
						skin = SKINS[index]
						if skin.key in profile.unlocked_skins:
							return skin.key

			self._draw(profile, index)
			pygame.display.flip()
			self.clock.tick(60)
			await asyncio.sleep(0)

	def _truncate(self, font: pygame.font.Font, text: str, max_width: int) -> str:
		if max_width <= 10:
			return ""
		if font.size(text)[0] <= max_width:
			return text
		ell = "…"
		t = text
		while t and font.size(t + ell)[0] > max_width:
			t = t[:-1]
		return (t + ell) if t else ell

	def _draw(self, profile, selected_index: int) -> None:
		w = self.screen.get_width()
		h = self.screen.get_height()
		self.screen.fill(_BG)
		title = self.title_font.render("Choose Cat", True, _TEXT)
		self.screen.blit(title, ((w - title.get_width()) // 2, 60))

		hint = self.small.render("Enter to select • Esc back • F11 fullscreen", True, _MUTED)
		self.screen.blit(hint, ((w - hint.get_width()) // 2, 128))

		cols = 4
		start_x = 70
		start_y = 190
		avail_w = max(200, w - start_x * 2)
		cell_w = avail_w // cols
		cell_h = 112
		pad = 14

		for i, skin in enumerate(SKINS):
			x = start_x + (i % cols) * cell_w
			y = start_y + (i // cols) * cell_h
			rect = pygame.Rect(x, y, cell_w - 16, cell_h - 16)
			is_selected = i == selected_index
			unlocked = skin.key in profile.unlocked_skins
			is_current = skin.key == profile.selected_skin

			bg = _SURFACE if unlocked else (235, 238, 244)
			border = _PRIMARY if (is_selected or is_current) else _BORDER
			_draw_card(self.screen, rect, fill=bg, border=border, border_w=4 if (is_selected or is_current) else 2, radius=14)

			name_text = self._truncate(self.font, get_skin_display_name(skin.key), rect.width - pad * 2)
			name = self.font.render(name_text, True, _TEXT if unlocked else _MUTED)
			self.screen.blit(name, (rect.x + pad, rect.y + 10))

			if unlocked:
				status_text = "Unlocked"
			else:
				if skin.key in LEVEL_UNLOCKS:
					need = LEVEL_UNLOCKS[skin.key]
					status_text = f"Locked: Level {need} (you: {profile.highest_level})"
				elif skin.key == "Fisher":
					status_text = f"Locked: Eat 100 fish ({profile.total_fish}/100)"
				elif skin.key == "MouseHunter":
					status_text = f"Locked: Eat 200 mice ({profile.total_mice}/200)"
				else:
					status_text = f"Locked: {skin.unlock_text}"
			status_text = self._truncate(self.small, status_text, rect.width - pad * 2)
			status = self.small.render(status_text, True, _TEXT if unlocked else _MUTED)
			self.screen.blit(status, (rect.x + pad, rect.y + 52))

		current = self.small.render(f"Current: {get_skin_display_name(profile.selected_skin)}", True, _MUTED)
		self.screen.blit(current, (70, h - 44))


class HighScoresScreen:
	def __init__(self, screen: pygame.Surface) -> None:
		self.screen = screen
		self.clock = pygame.time.Clock()
		self.title_font = pygame.font.SysFont(None, 68)
		self.font = pygame.font.SysFont(None, 40)
		self.small = pygame.font.SysFont(None, 28)

	async def run(self, rows: list[tuple[str, int, int, str]]) -> None:
		def _truncate(font: pygame.font.Font, text: str, max_width: int) -> str:
			if max_width <= 10:
				return ""
			if font.size(text)[0] <= max_width:
				return text
			ell = "…"
			t = text
			while t and font.size(t + ell)[0] > max_width:
				t = t[:-1]
			return (t + ell) if t else ell

		scroll = 0
		while True:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					return
				if event.type == pygame.KEYDOWN:
					if event.key == pygame.K_F11:
						toggle_fullscreen(pygame)
						self.screen = pygame.display.get_surface() or self.screen
					if event.key in (pygame.K_UP, pygame.K_w):
						scroll = max(0, scroll - 1)
					if event.key in (pygame.K_DOWN, pygame.K_s):
						scroll = min(max(0, len(rows) - 1), scroll + 1)
					if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
						return

			w = self.screen.get_width()
			h = self.screen.get_height()
			self.screen.fill(_BG)
			title = self.title_font.render("High Scores", True, _TEXT)
			self.screen.blit(title, ((w - title.get_width()) // 2, 60))
			hint = self.small.render("Esc back • Up/Down scroll • F11 fullscreen", True, _MUTED)
			self.screen.blit(hint, ((w - hint.get_width()) // 2, 128))

			card_w = min(860, max(560, w - 180))
			card_h = min(520, h - 240)
			card = pygame.Rect((w - card_w) // 2, 180, card_w, card_h)
			_draw_card(self.screen, card, fill=_SURFACE, border=_BORDER, border_w=2, radius=18)

			y = card.y + 18
			if not rows:
				empty = self.font.render("No scores yet — play a game!", True, _TEXT)
				self.screen.blit(empty, (card.x + 26, y + 18))
			else:
				# Responsive columns (always fit within the card)
				left = card.x + 26
				right = card.right - 26
				inner_w = max(200, right - left)
				gap = 16

				rank_w = 44
				score_w = 110
				level_w = 80
				name_w = max(160, int(inner_w * 0.32))
				cat_w = max(120, inner_w - (rank_w + name_w + score_w + level_w + gap * 4))

				col_rank = left
				col_name = col_rank + rank_w + gap
				col_score = col_name + name_w + gap
				col_level = col_score + score_w + gap
				col_cat = col_level + level_w + gap

				# Header (align numeric headers to the right edge of their columns)
				rank_h = self.small.render("#", True, _MUTED)
				name_h = self.small.render("Name", True, _MUTED)
				score_h = self.small.render("Score", True, _MUTED)
				level_h = self.small.render("Level", True, _MUTED)
				cat_h = self.small.render("Cat", True, _MUTED)

				self.screen.blit(rank_h, (col_rank, y))
				self.screen.blit(name_h, (col_name, y))
				self.screen.blit(score_h, (col_score + score_w - score_h.get_width(), y))
				self.screen.blit(level_h, (col_level + level_w - level_h.get_width(), y))
				self.screen.blit(cat_h, (col_cat, y))
				y += 40

				# Clip text to the inner card area so nothing can draw outside
				clip_rect = pygame.Rect(card.x + 14, card.y + 12, card.w - 28, card.h - 24)
				prev_clip = self.screen.get_clip()
				self.screen.set_clip(clip_rect)

				visible = 9
				start = max(0, min(scroll, max(0, len(rows) - visible)))
				chunk = rows[start : start + visible]
				for idx, (name, score, level, skin_name) in enumerate(chunk, start=start + 1):
					# Truncate for display based on actual pixel width
					name_col = _truncate(self.font, name, name_w)
					cat_col = _truncate(self.font, skin_name, cat_w)
					
					if idx % 2 == 0:
						row_bg = pygame.Rect(card.x + 14, y - 8, card.w - 28, 46)
						pygame.draw.rect(self.screen, _SURFACE_2, row_bg, border_radius=10)
					
					# Render each column separately (numbers right-aligned)
					rank_t = self.font.render(str(idx), True, _TEXT)
					name_t = self.font.render(name_col, True, _TEXT)
					score_t = self.font.render(str(score), True, _TEXT)
					level_t = self.font.render(str(level), True, _TEXT)
					cat_t = self.font.render(cat_col, True, _TEXT)
					
					self.screen.blit(rank_t, (col_rank, y))
					self.screen.blit(name_t, (col_name, y))
					self.screen.blit(score_t, (col_score + score_w - score_t.get_width(), y))
					self.screen.blit(level_t, (col_level + level_w - level_t.get_width(), y))
					self.screen.blit(cat_t, (col_cat, y))
					
					y += 52

				self.screen.set_clip(prev_clip)

				if len(rows) > visible:
					scroll_hint = self.small.render("Up/Down to scroll", True, _MUTED)
					self.screen.blit(scroll_hint, (card.x + 26, card.bottom + 14))

			pygame.display.flip()
			self.clock.tick(60)
			await asyncio.sleep(0)
