from __future__ import annotations

import math
from pathlib import Path

import pygame


def _make_tone(frequency_hz: float, duration_s: float, volume: float = 0.2) -> pygame.mixer.Sound:
	# Lightweight generated tone (no external assets needed).
	sample_rate = 44100
	n_samples = int(sample_rate * duration_s)
	buf = bytearray()
	for i in range(n_samples):
		t = i / sample_rate
		v = math.sin(2.0 * math.pi * frequency_hz * t)
		sample = int(max(-1.0, min(1.0, v)) * 32767 * volume)
		buf += int(sample).to_bytes(2, byteorder="little", signed=True)
	return pygame.mixer.Sound(buffer=bytes(buf))


class Sounds:
	def __init__(self) -> None:
		# Prefer real kid-friendly assets when present.
		assets_dir = Path(__file__).parent / "assets" / "sounds"
		eat_path = assets_dir / "cat_eating.mp3"
		if eat_path.exists():
			try:
				self.eat = pygame.mixer.Sound(str(eat_path))
			except Exception:
				self.eat = _make_tone(660, 0.06, 0.18)
		else:
			self.eat = _make_tone(660, 0.06, 0.18)
		self.level_up = _make_tone(880, 0.18, 0.20)
		self.unlock = _make_tone(990, 0.10, 0.18)
		self.game_over = _make_tone(220, 0.25, 0.15)
		self.salmon = _make_tone(1320, 0.12, 0.20)
