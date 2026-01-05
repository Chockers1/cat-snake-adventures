from __future__ import annotations


def toggle_fullscreen(pygame_module) -> None:
	pygame = pygame_module
	try:
		pygame.display.toggle_fullscreen()
	except Exception:
		# Some platforms/drivers may not support toggling; ignore gracefully.
		return
