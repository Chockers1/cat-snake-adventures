from __future__ import annotations

import math
import random
import sys
import asyncio
from dataclasses import dataclass
from pathlib import Path

import pygame

from .display_utils import toggle_fullscreen
from .food import roll_food
from .leaderboard import add_entry
from .levels import get_level
from .skins import get_skin_display_name, unlock_new_skins
from .sounds import Sounds


@dataclass
class GameState:
	# Tabs are used consistently in this file to match the existing codebase style.
	score: int = 0
	level: int = 1
	xp: int = 0
	xp_to_next: int = 100
	food_eaten_this_level: int = 0
	paused: bool = False
	game_over: bool = False
	leaderboard_saved: bool = False


@dataclass
class Pickup:
	kind: str  # "skateboard" | "zoomies" | "slime" | "mud"
	pos: tuple[float, float]


class GameLoop:
	def __init__(self, screen: pygame.Surface, save_system, profile) -> None:
		# NOTE: This file is intentionally a full overwrite to fix a prior corruption
		# where a duplicate copy of the module was appended mid-line.
		self.screen = screen
		self.save_system = save_system
		self.profile = profile
		self.profile.ensure_skin_valid()

		self.clock = pygame.time.Clock()
		self.font_big = pygame.font.SysFont(None, 64)
		self.font = pygame.font.SysFont(None, 32)

		self.hud_h = 96
		# Keep things big and readable for kids.
		self.target_grid_w = 28
		self.target_grid_h = 20

		# Technique 2: continuous movement + trail following.
		self.segment_ratio = 0.75
		self.sprite_size = 24
		self.segment_distance = 18
		self.play_x = 0
		self.play_y = 0
		self.play_w = 0
		self.play_h = 0
		self._recompute_layout(rescale=False)

		self.rng = random.Random()
		self.sounds = Sounds()

		self._bg_cache: dict[tuple[str, int, int], pygame.Surface] = {}
		self._bg_base: dict[str, pygame.Surface] = {}

		self.food_sprites = self._load_food_sprites()
		self.other_sprites = self._load_other_sprites()
		self._loaded_cat_skin: str | None = None
		self.cat_sprites = self._load_cat_sprites_for_skin(self.profile.selected_skin)
		self._rot_cache: dict[tuple[str, int], pygame.Surface] = {}

		self._time_s = 0.0
		self._speed_boost_until_s = 0.0
		self._zoomies_until_s = 0.0
		self._slow_until_s = 0.0
		self._mud_until_s = 0.0
		self._overlay_text: str | None = None
		self._overlay_until_s = 0.0
		self._slime_target_count = 4
		self._mud_target_count = 1
		self.pickups: list[Pickup] = []

		self.reset_run()

	def _recompute_layout(self, *, rescale: bool) -> None:
		w = self.screen.get_width()
		h = self.screen.get_height()
		usable_h = max(200, h - self.hud_h)

		new_sprite = min(w // self.target_grid_w, usable_h // self.target_grid_h)
		new_sprite = max(20, int(new_sprite))
		sprite_changed = new_sprite != self.sprite_size
		self.sprite_size = new_sprite
		self.segment_distance = max(12, int(self.sprite_size * self.segment_ratio))

		margin = int(self.sprite_size * 1.2)
		avail_w = max(self.sprite_size * 10, w - margin * 2)
		avail_h = max(self.sprite_size * 8, usable_h - margin * 2)

		# Keep the playfield 16:9 so the background fits nicely.
		aspect = 16.0 / 9.0
		play_w = float(avail_w)
		play_h = play_w / aspect
		if play_h > avail_h:
			play_h = float(avail_h)
			play_w = play_h * aspect

		play_w = (int(play_w) // self.segment_distance) * self.segment_distance
		play_h = (int(play_h) // self.segment_distance) * self.segment_distance

		self.play_w = int(play_w)
		self.play_h = int(play_h)
		self.play_x = max(0, (w - self.play_w) // 2)
		self.play_y = self.hud_h + max(0, (usable_h - self.play_h) // 2)

		if rescale and sprite_changed:
			self._bg_cache.clear()
			self.food_sprites = self._load_food_sprites()
			self.other_sprites = self._load_other_sprites()
			self.cat_sprites = self._load_cat_sprites_for_skin(self.profile.selected_skin)
			self._rot_cache.clear()
			# Re-spawn pickups at new scale.
			self._spawn_pickups_for_level()

	def _load_food_sprites(self) -> dict[str, pygame.Surface]:
		sprites: dict[str, pygame.Surface] = {}
		assets = Path(__file__).parent / "assets" / "food"
		mapping = {
			"mouse": assets / "mouse.png",
			"fish": assets / "fish.png",
			"salmon": assets / "smokedsalmon.png",
		}
		for key, path in mapping.items():
			if not path.exists():
				continue
			try:
				img = pygame.image.load(str(path)).convert_alpha()
				size = int(self.sprite_size * 0.92)
				sprites[key] = pygame.transform.smoothscale(img, (size, size))
			except Exception:
				continue
		return sprites

	def _load_other_sprites(self) -> dict[str, pygame.Surface]:
		sprites: dict[str, pygame.Surface] = {}
		assets = Path(__file__).parent / "assets" / "others"
		mapping = {
			"skateboard": assets / "skateboard.png",
			"zoomies": assets / "zoomies.png",
			"slime": assets / "slime.png",
			"mud": assets / "mud.png",
		}
		for key, path in mapping.items():
			if not path.exists():
				continue
			try:
				img = pygame.image.load(str(path)).convert_alpha()
				size = int(self.sprite_size * 0.92)
				sprites[key] = pygame.transform.smoothscale(img, (size, size))
			except Exception:
				continue
		return sprites

	def _load_cat_sprites_for_skin(self, skin_key: str) -> dict[str, pygame.Surface]:
		def _tight_crop_alpha(img: pygame.Surface) -> pygame.Surface:
			# If a sprite has lots of transparent padding, the visible cat can look tiny
			# once scaled. Cropping to the opaque bounds normalizes visual size.
			try:
				mask = pygame.mask.from_surface(img, 1)
				rects = mask.get_bounding_rects()
			except Exception:
				return img
			if not rects:
				return img
			bound = rects[0].copy()
			for r in rects[1:]:
				bound.union_ip(r)
			# Avoid accidental 0-sized subsurfaces
			if bound.w <= 0 or bound.h <= 0:
				return img
			return img.subsurface(bound).copy()

		def _scale_fit_center(img: pygame.Surface, target: int) -> pygame.Surface:
			cw, ch = img.get_width(), img.get_height()
			if cw <= 0 or ch <= 0:
				return pygame.transform.smoothscale(img, (target, target))
			scale = min(target / float(cw), target / float(ch))
			nw = max(1, int(cw * scale))
			nh = max(1, int(ch * scale))
			scaled = pygame.transform.smoothscale(img, (nw, nh))
			out = pygame.Surface((target, target), pygame.SRCALPHA)
			out.blit(scaled, ((target - nw) // 2, (target - nh) // 2))
			return out

		# Sprite packs currently supported.
		if skin_key == "Black":
			folder = "black_cat"
			prefix = "black_cat"
		elif skin_key == "Ginger":
			folder = "ginger_cat"
			prefix = "ginger_cat"
		else:
			folder = "classic_cat"
			prefix = "classic_cat"

		sprites: dict[str, pygame.Surface] = {}
		assets = Path(__file__).parent / "assets" / "cats" / folder
		mapping = {
			"head": assets / f"{prefix}_head.png",
			"body": assets / f"{prefix}_body.png",
			"tail": assets / f"{prefix}_tail.png",
		}
		for key, path in mapping.items():
			if not path.exists():
				continue
			try:
				img = pygame.image.load(str(path)).convert_alpha()
				size = int(self.sprite_size * 0.98)
				if skin_key == "Ginger":
					img = _tight_crop_alpha(img)
					sprites[key] = _scale_fit_center(img, size)
				else:
					sprites[key] = pygame.transform.smoothscale(img, (size, size))
			except Exception:
				continue

		self._loaded_cat_skin = skin_key
		return sprites

	def reset_run(self) -> None:
		self.state = GameState(level=self.profile.current_level)
		self._time_s = 0.0
		self._speed_boost_until_s = 0.0
		self._zoomies_until_s = 0.0
		self._slow_until_s = 0.0
		self._mud_until_s = 0.0
		self._overlay_text = None
		self._overlay_until_s = 0.0
		self.dir = (1, 0)
		self.head_pos = (self.play_w * 0.5, self.play_h * 0.5)
		self.segment_count = 2  # head + tail

		seed_len = (self.segment_count - 1) * self.segment_distance
		hx, hy = self.head_pos
		self.trail: list[tuple[float, float]] = []
		for d in range(int(seed_len), -1, -2):
			self.trail.append((hx - d, hy))

		self.segment_positions = self._segment_positions_from_trail(self.segment_count)
		self.food_pos = self._spawn_food()
		self.food_type = roll_food(self.rng)
		self._rot_cache.clear()
		self._spawn_pickups_for_level()

	def _spawn_pickups_for_level(self) -> None:
		# Level-scaled pickups:
		# - Level 1: fewer slow items.
		# - Each level: add more pickups (with caps so the playfield doesn't get overcrowded).
		lvl = max(1, int(self.state.level))
		self.pickups = []

		# Boost items scale slowly.
		skateboards = min(1 + (lvl - 1) // 5, 3)
		zoomies = min(1 + (lvl - 1) // 6, 3)

		# Slow items scale more aggressively.
		if lvl == 1:
			slimes = 2
			muds = 0
		else:
			slimes = min(3 + (lvl - 2), 10)
			muds = min(1 + (lvl - 2) // 3, 5)

		self._slime_target_count = int(slimes)
		self._mud_target_count = int(muds)
		self._ensure_pickup_count(
			skateboard=int(skateboards),
			zoomies=int(zoomies),
			slime=self._slime_target_count,
			mud=self._mud_target_count,
		)

	def _ensure_pickup_count(self, *, skateboard: int, zoomies: int, slime: int, mud: int) -> None:
		want = {"skateboard": skateboard, "zoomies": zoomies, "slime": slime, "mud": mud}
		have = {"skateboard": 0, "zoomies": 0, "slime": 0, "mud": 0}
		for p in self.pickups:
			have[p.kind] = have.get(p.kind, 0) + 1

		for kind, target in want.items():
			missing = max(0, int(target) - int(have.get(kind, 0)))
			for _ in range(missing):
				pos = self._spawn_pickup_pos(existing=self.pickups)
				self.pickups.append(Pickup(kind=kind, pos=pos))

	def _spawn_pickup_pos(self, *, existing: list[Pickup]) -> tuple[float, float]:
		r = self.sprite_size * 0.60
		for _ in range(350):
			x = self.rng.uniform(r, self.play_w - r)
			y = self.rng.uniform(r, self.play_h - r)

			ok = True
			for sx, sy in getattr(self, "segment_positions", []):
				if math.hypot(x - sx, y - sy) < self.sprite_size * 1.05:
					ok = False
					break
			if not ok:
				continue

			fx, fy = getattr(self, "food_pos", (0.0, 0.0))
			if math.hypot(x - fx, y - fy) < self.sprite_size * 1.10:
				continue

			for p in existing:
				px, py = p.pos
				if math.hypot(x - px, y - py) < self.sprite_size * 1.05:
					ok = False
					break
			if not ok:
				continue

			return (x, y)
		return (self.play_w * 0.75, self.play_h * 0.75)

	def _dir_to_angle(self, dx: int, dy: int) -> int:
		# Assumes sprites face RIGHT by default.
		if (dx, dy) == (1, 0):
			return 0
		if (dx, dy) == (0, 1):
			return -90
		if (dx, dy) == (-1, 0):
			return 180
		if (dx, dy) == (0, -1):
			return 90
		return 0

	def _vector_to_cardinal(self, dx: float, dy: float) -> tuple[int, int]:
		# Movement is axis-aligned; this snaps segment orientation.
		if abs(dx) >= abs(dy):
			return (1, 0) if dx >= 0 else (-1, 0)
		return (0, 1) if dy >= 0 else (0, -1)

	def _rotated(self, key: str, angle: int) -> pygame.Surface | None:
		base = self.cat_sprites.get(key)
		if base is None:
			return None
		cache_key = (key, int(angle))
		cached = self._rot_cache.get(cache_key)
		if cached is not None:
			return cached
		rot = pygame.transform.rotate(base, angle)
		self._rot_cache[cache_key] = rot
		return rot

	def _background_for_level(self, level_index: int) -> pygame.Surface | None:
		# Per-level backgrounds (scaled to the playfield).
		if level_index == 1:
			name = "starting_background.png"
		elif level_index in (2, 3):
			name = "background_l2_l3.png"
		elif level_index in (4, 5, 6):
			name = "background_l4_l6.png"
		elif level_index == 10:
			name = "background_l10.png"
		elif level_index >= 11:
			name = "background_l11a.png"
		else:
			return None
		assets_path = Path(__file__).parent / "assets" / "background" / name
		if not assets_path.exists():
			return None

		key = (name, int(self.play_w), int(self.play_h))
		cached = self._bg_cache.get(key)
		if cached is not None:
			return cached

		base = self._bg_base.get(name)
		if base is None:
			try:
				base = pygame.image.load(str(assets_path)).convert()
			except Exception:
				return None
			self._bg_base[name] = base

		try:
			scaled = pygame.transform.smoothscale(base, (int(self.play_w), int(self.play_h)))
		except Exception:
			return None

		self._bg_cache[key] = scaled
		return scaled

	async def run(self) -> None:
		running = True
		while running:
			dt = self.clock.tick(60) / 1000.0
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					running = False
				elif event.type == pygame.VIDEORESIZE:
					flags = 0 if sys.platform == "emscripten" else pygame.RESIZABLE
					self.screen = pygame.display.set_mode((event.w, event.h), flags)
					self._recompute_layout(rescale=True)
					self.reset_run()
				elif event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						running = False
					elif event.key == pygame.K_F11:
						toggle_fullscreen(pygame)
						self.screen = pygame.display.get_surface() or self.screen
						self._recompute_layout(rescale=True)
						self.reset_run()
					elif event.key == pygame.K_p:
						self.state.paused = not self.state.paused
					else:
						self._handle_direction(event.key)

			if not self.state.paused and not self.state.game_over:
				self._tick(dt)

			self._draw()
			pygame.display.flip()
			await asyncio.sleep(0)

			if self.state.game_over:
				if self._game_over_input():
					self.reset_run()

		self._persist_end()

	def _queue_overlay(self, text: str, *, duration_s: float = 0.9) -> None:
		self._overlay_text = text
		self._overlay_until_s = max(self._overlay_until_s, self._time_s + float(duration_s))

	def _handle_direction(self, key: int) -> None:
		dx, dy = self.dir
		if key in (pygame.K_UP, pygame.K_w):
			nd = (0, -1)
		elif key in (pygame.K_DOWN, pygame.K_s):
			nd = (0, 1)
		elif key in (pygame.K_LEFT, pygame.K_a):
			nd = (-1, 0)
		elif key in (pygame.K_RIGHT, pygame.K_d):
			nd = (1, 0)
		else:
			return

		# Block 180-degree reverse once you have a real body.
		if (nd[0] == -dx and nd[1] == -dy) and self.segment_count >= 3:
			return
		self.dir = nd

	def _tick(self, dt: float) -> None:
		self._time_s += dt
		if self._overlay_text and self._time_s >= self._overlay_until_s:
			self._overlay_text = None
		lvl = get_level(self.state.level)
		cells_per_s = float(lvl.speed_cells_per_second)
		if self._time_s < self._speed_boost_until_s:
			cells_per_s += 5.0
		if self._time_s < self._zoomies_until_s:
			cells_per_s += 8.0
		slow_mult = 1.0
		if self._time_s < self._slow_until_s:
			slow_mult = min(slow_mult, 0.70)
		if self._time_s < self._mud_until_s:
			slow_mult = min(slow_mult, 0.50)
		cells_per_s *= slow_mult
		cells_per_s = max(1.0, cells_per_s)
		speed_px = cells_per_s * float(self.segment_distance)
		move = speed_px * dt
		if move <= 0:
			return

		hx, hy = self.head_pos
		dx, dy = self.dir
		nx = hx + dx * move
		ny = hy + dy * move
		self.head_pos = (nx, ny)
		self.trail.append(self.head_pos)

		self._trim_trail(int((self.segment_count + 6) * self.segment_distance))
		self.segment_positions = self._segment_positions_from_trail(self.segment_count)

		self._check_wall_collision()
		if not self.state.game_over:
			self._check_self_collision()
		if not self.state.game_over:
			self._check_food_collision()
		if not self.state.game_over:
			self._check_pickup_collision()
			# Keep the level's slime/mud count topped up. Skateboard/zoomies do not respawn once collected.
			self._ensure_pickup_count(
				skateboard=self._count_pickups("skateboard"),
				zoomies=self._count_pickups("zoomies"),
				slime=self._slime_target_count,
				mud=self._mud_target_count,
			)

	def _count_pickups(self, kind: str) -> int:
		return sum(1 for p in self.pickups if p.kind == kind)

	def _check_pickup_collision(self) -> None:
		if not self.pickups:
			return
		hx, hy = self.head_pos
		threshold = self.sprite_size * 0.60
		kept: list[Pickup] = []
		picked_skateboard = False
		picked_zoomies = False
		picked_slime = 0
		picked_mud = 0
		for p in self.pickups:
			px, py = p.pos
			if math.hypot(hx - px, hy - py) <= threshold:
				if p.kind == "skateboard":
					self._speed_boost_until_s = max(self._speed_boost_until_s, self._time_s + 10.0)
					picked_skateboard = True
					continue
				if p.kind == "zoomies":
					self._zoomies_until_s = max(self._zoomies_until_s, self._time_s + 6.0)
					picked_zoomies = True
					continue
				if p.kind == "slime":
					self._slow_until_s = max(self._slow_until_s, self._time_s + 4.0)
					picked_slime += 1
					continue
				if p.kind == "mud":
					self._mud_until_s = max(self._mud_until_s, self._time_s + 5.0)
					picked_mud += 1
					continue
			kept.append(p)
		self.pickups = kept
		# Skateboard: only one per level (don't respawn until next level)
		if picked_skateboard:
			pass
		# Zoomies: only one per level (don't respawn until next level)
		if picked_zoomies:
			pass
		# Slime: replace any collected to maintain 4-5 on screen
		# Mud: replace any collected to maintain 1 on screen
		if picked_slime or picked_mud:
			self._ensure_pickup_count(
				skateboard=self._count_pickups("skateboard"),
				zoomies=self._count_pickups("zoomies"),
				slime=self._slime_target_count,
				mud=self._mud_target_count,
			)

	def _trim_trail(self, needed_length_px: int) -> None:
		if len(self.trail) < 3:
			return
		total = 0.0
		for i in range(len(self.trail) - 1, 0, -1):
			x1, y1 = self.trail[i]
			x0, y0 = self.trail[i - 1]
			total += math.hypot(x1 - x0, y1 - y0)
			if total >= needed_length_px:
				cut = max(0, i - 1)
				if cut > 0:
					self.trail = self.trail[cut:]
				return

	def _segment_positions_from_trail(self, count: int) -> list[tuple[float, float]]:
		if not self.trail:
			return []
		positions: list[tuple[float, float]] = []
		targets = [i * self.segment_distance for i in range(count)]
		target_i = 0
		accum = 0.0

		p2x, p2y = self.trail[-1]
		positions.append((p2x, p2y))
		target_i = 1

		for j in range(len(self.trail) - 2, -1, -1):
			p1x, p1y = self.trail[j]
			seg = math.hypot(p2x - p1x, p2y - p1y)
			if seg <= 0.0001:
				p2x, p2y = p1x, p1y
				continue
			while target_i < len(targets) and accum + seg >= targets[target_i]:
				need = targets[target_i] - accum
				t = need / seg
				x = p2x + (p1x - p2x) * t
				y = p2y + (p1y - p2y) * t
				positions.append((x, y))
				target_i += 1
			accum += seg
			p2x, p2y = p1x, p1y
			if target_i >= len(targets):
				break

		# If trail isn't long enough, repeat oldest point.
		last = positions[-1]
		while len(positions) < count:
			positions.append(last)
		return positions

	def _check_wall_collision(self) -> None:
		hx, hy = self.head_pos
		r = self.sprite_size * 0.45
		if hx < r or hx > (self.play_w - r) or hy < r or hy > (self.play_h - r):
			self._set_game_over()

	def _check_self_collision(self) -> None:
		if len(self.segment_positions) < 8:
			return
		hx, hy = self.segment_positions[0]
		threshold = self.segment_distance * 0.65
		for x, y in self.segment_positions[7:]:
			if math.hypot(hx - x, hy - y) < threshold:
				self._set_game_over()
				return

	def _check_food_collision(self) -> None:
		hx, hy = self.head_pos
		fx, fy = self.food_pos
		if math.hypot(hx - fx, hy - fy) <= self.sprite_size * 0.55:
			self._eat_food()

	def _eat_food(self) -> None:
		ft = self.food_type
		self.state.score += ft.xp_gain
		self.state.xp += ft.xp_gain
		self.profile.total_xp += ft.xp_gain
		self.segment_count += ft.length_gain
		self.state.food_eaten_this_level += 1

		# Play the "eat" sound every time.
		self.sounds.eat.play()
		if ft.key == "mouse":
			self.profile.total_mice += 1
		elif ft.key == "fish":
			self.profile.total_fish += 1
		else:
			self.profile.total_salmon += 1
			self.sounds.salmon.play()

		new_skins = unlock_new_skins(self.profile)
		if new_skins:
			self.sounds.unlock.play()
			name = get_skin_display_name(new_skins[0])
			self._queue_overlay(f"Unlocked: {name}!")
			self.save_system.save(self.profile)

		lvl = get_level(self.state.level)
		if self.state.food_eaten_this_level >= lvl.target_food:
			self._celebrate_level_up()
			self.state.level += 1
			self.profile.current_level = self.state.level
			self.state.food_eaten_this_level = 0
			self.profile.highest_level = max(self.profile.highest_level, self.state.level)
			self._spawn_pickups_for_level()

			new_skins = unlock_new_skins(self.profile)
			if new_skins:
				self.sounds.unlock.play()
				name = get_skin_display_name(new_skins[0])
				self._queue_overlay(f"Unlocked: {name}!")
			self.save_system.save(self.profile)

		while self.state.xp >= self.state.xp_to_next:
			self.state.xp -= self.state.xp_to_next
			self.state.xp_to_next = min(400, self.state.xp_to_next + 25)

		self.food_pos = self._spawn_food()
		self.food_type = roll_food(self.rng)
		self.profile.ensure_skin_valid()

	def _spawn_food(self) -> tuple[float, float]:
		r = self.sprite_size * 0.55
		for _ in range(250):
			x = self.rng.uniform(r, self.play_w - r)
			y = self.rng.uniform(r, self.play_h - r)
			ok = True
			for sx, sy in getattr(self, "segment_positions", []):
				if math.hypot(x - sx, y - sy) < self.sprite_size * 0.85:
					ok = False
					break
			if ok:
				return (x, y)
		return (self.play_w * 0.25, self.play_h * 0.25)

	def _celebrate_level_up(self) -> None:
		self.sounds.level_up.play()
		self._queue_overlay(f"Level {self.state.level} complete!")

	def _set_game_over(self) -> None:
		if not self.state.game_over:
			self.state.game_over = True
			self.sounds.game_over.play()
			self._persist_end()

	def _persist_end(self) -> None:
		self.profile.highest_score = max(self.profile.highest_score, self.state.score)
		self.profile.highest_level = max(self.profile.highest_level, self.state.level)
		self.save_system.save(self.profile)

		if self.state.game_over and not self.state.leaderboard_saved:
			add_entry(
				self.save_system.saves_dir,
				player_name=self.profile.player_name,
				score=self.state.score,
				level=self.state.level,
				skin=self.profile.selected_skin_display,
			)
			self.state.leaderboard_saved = True

	def _game_over_input(self) -> bool:
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				return False
			if event.type == pygame.KEYDOWN:
				if event.key == pygame.K_RETURN:
					return True
				if event.key == pygame.K_ESCAPE:
					return False
		return False

	def _draw(self, overlay_text: str | None = None) -> None:
		# Reload cat sprites if the player changed skins in menu.
		if self._loaded_cat_skin != self.profile.selected_skin:
			self.cat_sprites = self._load_cat_sprites_for_skin(self.profile.selected_skin)
			self._rot_cache.clear()

		self.screen.fill((210, 245, 255))
		hud_h = self.hud_h
		pygame.draw.rect(self.screen, (255, 255, 255), pygame.Rect(0, 0, self.screen.get_width(), hud_h))

		label = self.font.render(
			f"Score: {self.state.score}   Level: {self.state.level}   Cat: {self.profile.selected_skin_display}",
			True,
			(30, 30, 30),
		)
		self.screen.blit(label, (18, 14))

		bar_x, bar_y, bar_w, bar_h = 18, 52, 420, 22
		pygame.draw.rect(self.screen, (220, 220, 220), pygame.Rect(bar_x, bar_y, bar_w, bar_h), border_radius=10)
		fill = int(bar_w * (self.state.xp / max(1, self.state.xp_to_next)))
		pygame.draw.rect(self.screen, (60, 180, 90), pygame.Rect(bar_x, bar_y, fill, bar_h), border_radius=10)
		xp_txt = self.font.render(f"XP {self.state.xp}/{self.state.xp_to_next}", True, (30, 30, 30))
		self.screen.blit(xp_txt, (bar_x + bar_w + 12, bar_y - 2))

		origin_x = self.play_x
		origin_y = self.play_y

		bg = self._background_for_level(self.state.level)
		if bg is not None:
			self.screen.blit(bg, (origin_x, origin_y))
		else:
			pygame.draw.rect(
				self.screen,
				(200, 235, 245),
				pygame.Rect(origin_x, origin_y, self.play_w, self.play_h),
				border_radius=18,
			)

		# Pickups
		for p in self.pickups:
			x, y = p.pos
			rect = pygame.Rect(
				origin_x + int(x - self.sprite_size / 2),
				origin_y + int(y - self.sprite_size / 2),
				self.sprite_size,
				self.sprite_size,
			)
			spr = self.other_sprites.get(p.kind)
			if spr is not None:
				dest = spr.get_rect(center=rect.center)
				self.screen.blit(spr, dest)
			else:
				if p.kind == "skateboard":
					color = (70, 170, 90)
				elif p.kind == "zoomies":
					color = (255, 170, 60)
				elif p.kind == "mud":
					color = (145, 110, 75)
				else:
					color = (120, 160, 220)
				pygame.draw.circle(self.screen, color, rect.center, self.sprite_size // 2 - 2)

		use_sprites = {"head", "body", "tail"}.issubset(set(self.cat_sprites.keys()))
		for i, (x, y) in enumerate(self.segment_positions):
			rect = pygame.Rect(
				origin_x + int(x - self.sprite_size / 2),
				origin_y + int(y - self.sprite_size / 2),
				self.sprite_size,
				self.sprite_size,
			)
			center = rect.center

			if use_sprites:
				if i == 0:
					dx, dy = self.dir
					angle = self._dir_to_angle(dx, dy)
					spr = self._rotated("head", angle)
				elif i == len(self.segment_positions) - 1:
					px, py = self.segment_positions[i - 1]
					dx, dy = self._vector_to_cardinal(x - px, y - py)
					angle = self._dir_to_angle(dx, dy)
					spr = self._rotated("tail", angle)
				else:
					px, py = self.segment_positions[i - 1]
					dx, dy = self._vector_to_cardinal(px - x, py - y)
					angle = self._dir_to_angle(dx, dy)
					spr = self._rotated("body", angle)

				if spr is not None:
					dest = spr.get_rect(center=center)
					self.screen.blit(spr, dest)
			else:
				# Fallback boxes.
				color = (255, 170, 60) if i == 0 else (255, 205, 120)
				pygame.draw.rect(self.screen, color, rect, border_radius=8)

		fx, fy = self.food_pos
		food_rect = pygame.Rect(
			origin_x + int(fx - self.sprite_size / 2),
			origin_y + int(fy - self.sprite_size / 2),
			self.sprite_size,
			self.sprite_size,
		)
		sprite = self.food_sprites.get(self.food_type.key)
		if sprite is not None:
			dest = sprite.get_rect(center=food_rect.center)
			self.screen.blit(sprite, dest)
			if self.food_type.key == "salmon":
				pygame.draw.circle(self.screen, (255, 255, 255), (dest.centerx - 6, dest.centery - 8), 2)
				pygame.draw.circle(self.screen, (255, 255, 255), (dest.centerx + 8, dest.centery + 6), 2)
		else:
			pygame.draw.circle(self.screen, (120, 120, 130), food_rect.center, self.sprite_size // 2 - 2)

		if self.state.paused:
			over = self.font_big.render("PAUSED", True, (30, 30, 30))
			self.screen.blit(over, (self.screen.get_width() // 2 - over.get_width() // 2, 330))

		if self.state.game_over:
			msg = self.font_big.render("Game Over", True, (140, 30, 30))
			sub = self.font.render("Press Enter to play again (Esc to quit)", True, (30, 30, 30))
			self.screen.blit(msg, (self.screen.get_width() // 2 - msg.get_width() // 2, 280))
			self.screen.blit(sub, (self.screen.get_width() // 2 - sub.get_width() // 2, 360))

		text = overlay_text or self._overlay_text
		if text:
			msg = self.font_big.render(text, True, (30, 30, 30))
			self.screen.blit(msg, (self.screen.get_width() // 2 - msg.get_width() // 2, 300))
		"""
		NOTE: The remainder of this file previously contained an accidentally appended
		duplicate/corrupted copy of game loop code.
		
		It is intentionally kept inert so imports work and the real implementation above runs.
		
		self.target_grid_h = 20
		# Technique 2: continuous movement + trail following.
		# Body segments follow the head trail at fixed distance.
		self.segment_ratio = 0.75  # segment distance relative to sprite size
		self.sprite_size = 24
		self.segment_distance = 18
		self.play_x = 0
		self.play_y = 0
		self.play_w = 0
		self.play_h = 0
		self._recompute_layout(rescale=False)

		self.rng = random.Random()
		self.sounds = Sounds()
		self.food_sprites = self._load_food_sprites()
		self._loaded_cat_skin: str | None = None
		self.cat_sprites = self._load_cat_sprites_for_skin(self.profile.selected_skin)
		self._rot_cache: dict[tuple[str, int], pygame.Surface] = {}
		self._bg_cache: dict[tuple[str, int, int], pygame.Surface] = {}
		self._bg_base: dict[str, pygame.Surface] = {}
		# Only wired for the two currently supported sprite packs.
		if skin_key == "Black":
			folder = "black_cat"
			prefix = "black_cat"
		else:
			folder = "classic_cat"
			prefix = "classic_cat"

		sprites: dict[str, pygame.Surface] = {}
		assets = Path(__file__).parent / "assets" / "cats" / folder
		mapping = {
			"head": assets / f"{prefix}_head.png",
			"body": assets / f"{prefix}_body.png",
			"tail": assets / f"{prefix}_tail.png",
		}
		for key, path in mapping.items():
			if not path.exists():
				continue
			try:
				img = pygame.image.load(str(path)).convert_alpha()
				size = int(self.sprite_size * 0.98)
				sprites[key] = pygame.transform.smoothscale(img, (size, size))
			except Exception:
				continue

		self._loaded_cat_skin = skin_key
		return sprites

	def _load_classic_cat_sprites(self) -> dict[str, pygame.Surface]:
		# Backwards-compat helper (kept in case other code references it).
		return self._load_cat_sprites_for_skin("Classic")

		self.reset_run()

	def _recompute_layout(self, *, rescale: bool) -> None:
		w = self.screen.get_width()
		h = self.screen.get_height()
		usable_h = max(200, h - self.hud_h)

		new_sprite = min(w // self.target_grid_w, usable_h // self.target_grid_h)
		new_sprite = max(20, int(new_sprite))
		sprite_changed = new_sprite != self.sprite_size
		self.sprite_size = new_sprite
		self.segment_distance = max(12, int(self.sprite_size * self.segment_ratio))

		# Centered playfield with margins, snapped to segment distance.
		margin = int(self.sprite_size * 1.2)
		play_w = max(self.sprite_size * 10, w - margin * 2)
		play_h = max(self.sprite_size * 8, usable_h - margin * 2)
		play_w = (play_w // self.segment_distance) * self.segment_distance
		play_h = (play_h // self.segment_distance) * self.segment_distance

		self.play_w = int(play_w)
		self.play_h = int(play_h)
		self.play_x = max(0, (w - self.play_w) // 2)
		self.play_y = self.hud_h + max(0, (usable_h - self.play_h) // 2)

		if rescale and sprite_changed:
			self.food_sprites = self._load_food_sprites()
			self.cat_sprites = self._load_cat_sprites_for_skin(self.profile.selected_skin)
			self._rot_cache.clear()
			self._bg_cache.clear()

	def _load_food_sprites(self) -> dict[str, pygame.Surface]:
		sprites: dict[str, pygame.Surface] = {}
		assets = Path(__file__).parent / "assets" / "food"
		mapping = {
			"mouse": assets / "mouse.png",
			"fish": assets / "fish.png",
			"salmon": assets / "smokedsalmon.png",
		}
		for key, path in mapping.items():
			if not path.exists():
				continue
			try:
				img = pygame.image.load(str(path)).convert_alpha()
				size = int(self.sprite_size * 0.92)
				sprites[key] = pygame.transform.smoothscale(img, (size, size))
			except Exception:
				continue
		return sprites

	def reset_run(self) -> None:
		self.state = GameState(level=self.profile.current_level)
		# Continuous positions (local playfield coordinates, pixels)
		self.dir = (1, 0)
		self.head_pos = (self.play_w * 0.5, self.play_h * 0.5)
		self.segment_count = 2  # head + tail
		self.pending_growth = 0

		# Trail: list of positions from oldest -> newest.
		# Seed enough history so the tail exists immediately.
		seed_len = (self.segment_count - 1) * self.segment_distance
		hx, hy = self.head_pos
		self.trail: list[tuple[float, float]] = []
		for d in range(int(seed_len), -1, -2):
			self.trail.append((hx - d, hy))

		self.segment_positions = self._segment_positions_from_trail(self.segment_count)
		self.food_pos = self._spawn_food()
		self.food_type = roll_food(self.rng)
		self._accum = 0.0
		self._rot_cache.clear()

	def _load_classic_cat_sprites(self) -> dict[str, pygame.Surface]:
		sprites: dict[str, pygame.Surface] = {}
		assets = Path(__file__).parent / "assets" / "cats" / "classic_cat"
		mapping = {
			"head": assets / "classic_cat_head.png",
			"body": assets / "classic_cat_body.png",
			"tail": assets / "classic_cat_tail.png",
		}
		for key, path in mapping.items():
			if not path.exists():
				continue
			try:
				img = pygame.image.load(str(path)).convert_alpha()
				size = int(self.sprite_size * 0.98)
				sprites[key] = pygame.transform.smoothscale(img, (size, size))
			except Exception:
				continue
		return sprites

	def _dir_to_angle(self, dx: int, dy: int) -> int:
		# Assumes sprites face RIGHT by default.
		if (dx, dy) == (1, 0):
			return 0
		if (dx, dy) == (0, 1):
			return -90
		if (dx, dy) == (-1, 0):
			return 180
		if (dx, dy) == (0, -1):
			return 90
		return 0

	def _rotated(self, key: str, angle: int) -> pygame.Surface | None:
		base = self.cat_sprites.get(key)
		if base is None:
			return None
		cache_key = (key, int(angle))
		cached = self._rot_cache.get(cache_key)
		if cached is not None:
			return cached
		rot = pygame.transform.rotate(base, angle)
		self._rot_cache[cache_key] = rot
		return rot

	def run(self) -> None:
		running = True
		while running:
			dt = self.clock.tick(60) / 1000.0
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					running = False
				elif event.type == pygame.VIDEORESIZE:
					self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
					self._recompute_layout(rescale=True)
					self.reset_run()
				elif event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						running = False
					elif event.key == pygame.K_F11:
						toggle_fullscreen(pygame)
						self.screen = pygame.display.get_surface() or self.screen
						self._recompute_layout(rescale=True)
						self.reset_run()
					elif event.key in (pygame.K_p,):
						self.state.paused = not self.state.paused
					else:
						self._handle_direction(event.key)

			if not self.state.paused and not self.state.game_over:
				self._tick(dt)

			self._draw()
			pygame.display.flip()

			if self.state.game_over:
				# Soft stop: wait for Enter to restart, Esc to quit.
				if self._game_over_input():
					self.reset_run()

		self._persist_end()

	def _handle_direction(self, key: int) -> None:
		# No reversing into yourself
		dx, dy = self.dir
		if key in (pygame.K_UP, pygame.K_w):
			nd = (0, -1)
		elif key in (pygame.K_DOWN, pygame.K_s):
			nd = (0, 1)
		elif key in (pygame.K_LEFT, pygame.K_a):
			nd = (-1, 0)
		elif key in (pygame.K_RIGHT, pygame.K_d):
			nd = (1, 0)
		else:
			return

		# block 180-degree reverse
		if (nd[0] == -dx and nd[1] == -dy) and self.segment_count >= 3:
			return
		self.dir = nd

	def _tick(self, dt: float) -> None:
		lvl = get_level(self.state.level)
		speed_px = float(lvl.speed_cells_per_second) * float(self.segment_distance)
		move = speed_px * dt
		if move <= 0:
			return

		hx, hy = self.head_pos
		dx, dy = self.dir
		nx = hx + dx * move
		ny = hy + dy * move
		self.head_pos = (nx, ny)
		self.trail.append(self.head_pos)

		# Trim trail length to what's needed for current body length
		needed = int((self.segment_count + 4) * self.segment_distance)
		self._trim_trail(needed)
		self.segment_positions = self._segment_positions_from_trail(self.segment_count)

		# Collisions
		self._check_wall_collision()
		if not self.state.game_over:
			self._check_self_collision()
		if not self.state.game_over:
			self._check_food_collision()

	def _trim_trail(self, needed_length_px: int) -> None:
		# Remove oldest points until total length is within budget.
		if len(self.trail) < 3:
			return
		total = 0.0
		for i in range(len(self.trail) - 1, 0, -1):
			x1, y1 = self.trail[i]
			x0, y0 = self.trail[i - 1]
			total += math.hypot(x1 - x0, y1 - y0)
			if total >= needed_length_px:
				# Keep from i-1 onward
				cut = max(0, i - 1)
				if cut > 0:
					self.trail = self.trail[cut:]
				return

	def _segment_positions_from_trail(self, count: int) -> list[tuple[float, float]]:
		if not self.trail:
			return []
		positions: list[tuple[float, float]] = []
		targets = [i * self.segment_distance for i in range(count)]
		target_i = 0
		accum = 0.0

		p2x, p2y = self.trail[-1]
		while target_i < len(targets) and targets[target_i] == 0:
			positions.append((p2x, p2y))
			target_i += 1

		for j in range(len(self.trail) - 2, -1, -1):
			p1x, p1y = self.trail[j]
			seg = math.hypot(p2x - p1x, p2y - p1y)
			if seg <= 0.0001:
				p2x, p2y = p1x, p1y
				continue
			while target_i < len(targets) and accum + seg >= targets[target_i]:
				need = targets[target_i] - accum
				t = need / seg
				x = p2x + (p1x - p2x) * t
				y = p2y + (p1y - p2y) * t
				positions.append((x, y))
				target_i += 1
			accum += seg
			p2x, p2y = p1x, p1y
			if target_i >= len(targets):
				break

		# If trail isn't long enough, repeat oldest point.
		if positions:
			last = positions[-1]
		else:
			last = (self.trail[0][0], self.trail[0][1])
		while len(positions) < count:
			positions.append(last)
		return positions

	def _check_wall_collision(self) -> None:
		hx, hy = self.head_pos
		r = self.sprite_size * 0.45
		if hx < r or hx > (self.play_w - r) or hy < r or hy > (self.play_h - r):
			self._set_game_over()

	def _check_self_collision(self) -> None:
		# Ignore a few near-head segments to prevent false positives on turns.
		if len(self.segment_positions) < 8:
			return
		hx, hy = self.segment_positions[0]
		threshold = self.segment_distance * 0.65
		for x, y in self.segment_positions[7:]:
			if math.hypot(hx - x, hy - y) < threshold:
				self._set_game_over()
				return

	def _check_food_collision(self) -> None:
		hx, hy = self.head_pos
		fx, fy = self.food_pos
		if math.hypot(hx - fx, hy - fy) <= self.sprite_size * 0.55:
			self._eat_food()

	def _eat_food(self) -> None:
		ft = self.food_type
		self.state.score += ft.xp_gain
		self.state.xp += ft.xp_gain
		self.profile.total_xp += ft.xp_gain
		# Grow by adding more segments to the trail-following body.
		self.segment_count += ft.length_gain
		self.state.food_eaten_this_level += 1

		# Play the "eat" sound every time.
		self.sounds.eat.play()

		if ft.key == "mouse":
			self.profile.total_mice += 1
		elif ft.key == "fish":
			self.profile.total_fish += 1
		else:
			self.profile.total_salmon += 1
			self.sounds.salmon.play()

		# Unlock skins immediately after progress changes.
		new_skins = unlock_new_skins(self.profile)
		if new_skins:
			self.sounds.unlock.play()
			name = get_skin_display_name(new_skins[0])
			self._show_overlay(f"Unlocked: {name}!")
			self.save_system.save(self.profile)

		# Level target check
		lvl = get_level(self.state.level)
		if self.state.food_eaten_this_level >= lvl.target_food:
			self._celebrate_level_up()
			self.state.level += 1
			self.profile.current_level = self.state.level
			self.state.food_eaten_this_level = 0
			self.profile.highest_level = max(self.profile.highest_level, self.state.level)

			# Unlock skins that depend on reaching a level.
			new_skins = unlock_new_skins(self.profile)
			if new_skins:
				self.sounds.unlock.play()
				name = get_skin_display_name(new_skins[0])
				self._show_overlay(f"Unlocked: {name}!")
			self.save_system.save(self.profile)

		# XP bar (simple)
		while self.state.xp >= self.state.xp_to_next:
			self.state.xp -= self.state.xp_to_next
			self.state.xp_to_next = min(400, self.state.xp_to_next + 25)

		self.food_pos = self._spawn_food()
		self.food_type = roll_food(self.rng)

		# Keep the current skin valid if it was locked before.
		self.profile.ensure_skin_valid()

	def _celebrate_level_up(self) -> None:
		self.sounds.level_up.play()
		# Simple pause + message (kid-friendly, no stress)
		t = 0.0
		while t < 0.9:
			dt = self.clock.tick(60) / 1000.0
			t += dt
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					return
			self._draw(overlay_text=f"Level {self.state.level} complete!")
			pygame.display.flip()

	def _show_overlay(self, text: str) -> None:
		# Short, non-blocking celebration message.
		elapsed = 0.0
		while elapsed < 0.9:
			dt = self.clock.tick(60) / 1000.0
			elapsed += dt
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					return
			self._draw(overlay_text=text)
			pygame.display.flip()

	def _spawn_food(self) -> tuple[float, float]:
		# Spawn in pixel space, avoiding the body.
		r = self.sprite_size * 0.55
		for _ in range(250):
			x = self.rng.uniform(r, self.play_w - r)
			y = self.rng.uniform(r, self.play_h - r)
			ok = True
			for sx, sy in getattr(self, "segment_positions", []):
				if math.hypot(x - sx, y - sy) < self.sprite_size * 0.85:
					ok = False
					break
			if ok:
				return (x, y)
		return (self.play_w * 0.25, self.play_h * 0.25)

	def _set_game_over(self) -> None:
		if not self.state.game_over:
			self.state.game_over = True
			self.sounds.game_over.play()
			self._persist_end()

	def _persist_end(self) -> None:
		self.profile.highest_score = max(self.profile.highest_score, self.state.score)
		self.profile.highest_level = max(self.profile.highest_level, self.state.level)
		self.save_system.save(self.profile)

		if self.state.game_over and not self.state.leaderboard_saved:
			add_entry(
				self.save_system.saves_dir,
				player_name=self.profile.player_name,
				score=self.state.score,
				level=self.state.level,
				skin=self.profile.selected_skin_display,
			)
			self.state.leaderboard_saved = True

	def _game_over_input(self) -> bool:
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				return False
			if event.type == pygame.KEYDOWN:
				if event.key == pygame.K_RETURN:
					return True
				if event.key == pygame.K_ESCAPE:
					return False
		return False

	def _draw(self, overlay_text: str | None = None) -> None:
		# Background
		self.screen.fill((210, 245, 255))
		hud_h = self.hud_h
		pygame.draw.rect(self.screen, (255, 255, 255), pygame.Rect(0, 0, self.screen.get_width(), hud_h))

		# HUD text
		label = self.font.render(
			f"Score: {self.state.score}   Level: {self.state.level}   Cat: {self.profile.selected_skin_display}",
			True,
			(30, 30, 30),
		)
		self.screen.blit(label, (18, 14))

		# XP bar
		bar_x, bar_y, bar_w, bar_h = 18, 52, 420, 22
		pygame.draw.rect(self.screen, (220, 220, 220), pygame.Rect(bar_x, bar_y, bar_w, bar_h), border_radius=10)
		fill = int(bar_w * (self.state.xp / max(1, self.state.xp_to_next)))
		pygame.draw.rect(self.screen, (60, 180, 90), pygame.Rect(bar_x, bar_y, fill, bar_h), border_radius=10)
		xp_txt = self.font.render(f"XP {self.state.xp}/{self.state.xp_to_next}", True, (30, 30, 30))
		self.screen.blit(xp_txt, (bar_x + bar_w + 12, bar_y - 2))

		# Playfield origin (centered)
		origin_x = self.play_x
		origin_y = self.play_y

		bg = self._background_for_level(self.state.level)
		if bg is not None:
			self.screen.blit(bg, (origin_x, origin_y))
		else:
			pygame.draw.rect(
				self.screen,
				(200, 235, 245),
				pygame.Rect(origin_x, origin_y, self.play_w, self.play_h),
				border_radius=18,
			)
		# For now: Level 1–2 share a background image.
		if level_index not in (1, 2):
			return None

		name = "starting_background.png"
		assets_path = Path(__file__).parent / "assets" / "background" / name
		if not assets_path.exists():
			return None

		key = (name, int(self.play_w), int(self.play_h))
		cached = self._bg_cache.get(key)
		if cached is not None:
			return cached

		base = self._bg_base.get(name)
		if base is None:
			try:
				base = pygame.image.load(str(assets_path)).convert()
			except Exception:
				return None
			self._bg_base[name] = base

		try:
			scaled = pygame.transform.smoothscale(base, (int(self.play_w), int(self.play_h)))
		except Exception:
			return None

		self._bg_cache[key] = scaled
		return scaled

		# Draw cat
		use_classic_sprites = self.profile.selected_skin == "Classic" and {
			"head",
			"body",
			"tail",
		}.issubset(set(self.cat_sprites.keys()))

		if use_classic_sprites:
			for i, (x, y) in enumerate(self.segment_positions):
				rect = pygame.Rect(origin_x + int(x - self.sprite_size / 2), origin_y + int(y - self.sprite_size / 2), self.sprite_size, self.sprite_size)
				center = rect.center

				if i == 0:
					dx, dy = self.dir
					angle = self._dir_to_angle(dx, dy)
					spr = self._rotated("head", angle)
				elif i == len(self.segment_positions) - 1:
					px, py = self.segment_positions[i - 1]
					dx = x - px
					dy = y - py
					angle = self._dir_to_angle(int(math.copysign(1, dx)) if abs(dx) > abs(dy) else 0,
										   int(math.copysign(1, dy)) if abs(dy) > abs(dx) else 0)
					spr = self._rotated("tail", angle)
				else:
					px, py = self.segment_positions[i - 1]
					dx = px - x
					dy = py - y
					angle = self._dir_to_angle(int(math.copysign(1, dx)) if abs(dx) > abs(dy) else 0,
										   int(math.copysign(1, dy)) if abs(dy) > abs(dx) else 0)
					spr = self._rotated("body", angle)

				if spr is not None:
					dest = spr.get_rect(center=center)
					self.screen.blit(spr, dest)
		else:
			for i, (x, y) in enumerate(self.segment_positions):
		if self._loaded_cat_skin != self.profile.selected_skin:
			self.cat_sprites = self._load_cat_sprites_for_skin(self.profile.selected_skin)
			self._rot_cache.clear()
				rect = pygame.Rect(origin_x + int(x - self.sprite_size / 2), origin_y + int(y - self.sprite_size / 2), self.sprite_size, self.sprite_size)
				if i == 0:
					pygame.draw.rect(self.screen, (255, 170, 60), rect, border_radius=6)
					# simple "face"
					eye = pygame.Rect(rect.x + 6, rect.y + 7, 4, 4)
					eye2 = pygame.Rect(rect.x + 14, rect.y + 7, 4, 4)
					pygame.draw.rect(self.screen, (30, 30, 30), eye)
					pygame.draw.rect(self.screen, (30, 30, 30), eye2)
				else:
					pygame.draw.rect(self.screen, (255, 205, 120), rect, border_radius=6)

		# Draw food
		fx, fy = self.food_pos
		food_rect = pygame.Rect(origin_x + int(fx - self.sprite_size / 2), origin_y + int(fy - self.sprite_size / 2), self.sprite_size, self.sprite_size)
		sprite = self.food_sprites.get(self.food_type.key)
		if sprite is not None:
			dest = sprite.get_rect(center=food_rect.center)
			self.screen.blit(sprite, dest)
			if self.food_type.key == "salmon":
				pygame.draw.circle(self.screen, (255, 255, 255), (dest.centerx - 6, dest.centery - 8), 2)
				pygame.draw.circle(self.screen, (255, 255, 255), (dest.centerx + 8, dest.centery + 6), 2)
		else:
			# Fallback shapes if sprites are missing.
			if self.food_type.key == "mouse":
				pygame.draw.circle(self.screen, (120, 120, 130), food_rect.center, self.cell // 2 - 2)
			elif self.food_type.key == "fish":
				pygame.draw.circle(self.screen, (70, 120, 220), food_rect.center, self.cell // 2 - 2)
			else:
				pygame.draw.circle(self.screen, (240, 120, 140), food_rect.center, self.cell // 2 - 2)
				pygame.draw.circle(self.screen, (255, 255, 255), (food_rect.centerx - 4, food_rect.centery - 6), 2)
				pygame.draw.circle(self.screen, (255, 255, 255), (food_rect.centerx + 6, food_rect.centery + 4), 2)

		# Pause / overlays
		if self.state.paused:
			over = self.font_big.render("PAUSED", True, (30, 30, 30))
			self.screen.blit(over, (self.screen.get_width() // 2 - over.get_width() // 2, 330))

		if self.state.game_over:
			msg = self.font_big.render("Game Over", True, (140, 30, 30))
			sub = self.font.render("Press Enter to play again (Esc to quit)", True, (30, 30, 30))
			self.screen.blit(msg, (self.screen.get_width() // 2 - msg.get_width() // 2, 280))
			self.screen.blit(sub, (self.screen.get_width() // 2 - sub.get_width() // 2, 360))

		if overlay_text:
			msg = self.font_big.render(overlay_text, True, (30, 30, 30))
			self.screen.blit(msg, (self.screen.get_width() // 2 - msg.get_width() // 2, 300))
		"""
