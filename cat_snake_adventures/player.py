from __future__ import annotations

from dataclasses import dataclass, field

from .skins import get_skin_display_name


@dataclass
class PlayerProfile:
	player_name: str
	highest_score: int = 0
	highest_level: int = 1
	current_level: int = 1
	total_xp: int = 0
	unlocked_skins: list[str] = field(default_factory=lambda: ["Classic"])
	selected_skin: str = "Classic"
	total_mice: int = 0
	total_fish: int = 0
	total_salmon: int = 0

	def ensure_skin_valid(self) -> None:
		if self.selected_skin not in self.unlocked_skins:
			self.selected_skin = self.unlocked_skins[0] if self.unlocked_skins else "Classic"

	@property
	def selected_skin_display(self) -> str:
		return get_skin_display_name(self.selected_skin)
