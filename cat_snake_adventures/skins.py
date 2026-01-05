from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkinDef:
	key: str
	display_name: str
	unlock_text: str


SKINS: list[SkinDef] = [
	SkinDef(key="Classic", display_name="Classic Cat", unlock_text="Default"),
	SkinDef(key="Black", display_name="Black Cat", unlock_text="Reach Level 3"),
	SkinDef(key="Ginger", display_name="Ginger Cat", unlock_text="Reach Level 5"),
	SkinDef(key="Tiger", display_name="Tiger Cat", unlock_text="Reach Level 7"),
	SkinDef(key="Golden", display_name="Golden Cat", unlock_text="Reach Level 10"),
	SkinDef(key="Snow", display_name="Snow Cat", unlock_text="Reach Level 12"),
	SkinDef(key="Leopard", display_name="Leopard Cat", unlock_text="Reach Level 14"),
	SkinDef(key="Kitten", display_name="Kitten Cat", unlock_text="Reach Level 15"),
	SkinDef(key="Dragon", display_name="Dragon Cat", unlock_text="Reach Level 18"),
	SkinDef(key="Space", display_name="Space Cat", unlock_text="Reach Level 20"),
	SkinDef(key="Fisher", display_name="Fisher Cat", unlock_text="Eat 100 fish"),
	SkinDef(key="MouseHunter", display_name="Mouse Hunter", unlock_text="Eat 200 mice"),
	SkinDef(key="Lion", display_name="Lion Cat", unlock_text="Reach Level 25"),
]


LEVEL_UNLOCKS: dict[str, int] = {
	"Black": 3,
	"Ginger": 5,
	"Tiger": 7,
	"Golden": 10,
	"Snow": 12,
	"Leopard": 14,
	"Kitten": 15,
	"Dragon": 18,
	"Space": 20,
	"Lion": 25,
}


def unlock_new_skins(profile) -> list[str]:
	newly_unlocked: list[str] = []

	def unlock(key: str) -> None:
		if key not in profile.unlocked_skins:
			profile.unlocked_skins.append(key)
			newly_unlocked.append(key)

	# Level-based unlocks
	for key, needed_level in LEVEL_UNLOCKS.items():
		if profile.highest_level >= needed_level:
			unlock(key)

	# Food-based unlocks
	if profile.total_fish >= 100:
		unlock("Fisher")
	if profile.total_mice >= 200:
		unlock("MouseHunter")

	# Always ensure default exists
	if "Classic" not in profile.unlocked_skins:
		profile.unlocked_skins.insert(0, "Classic")

	return newly_unlocked


def skin_keys() -> list[str]:
	return [s.key for s in SKINS]


def get_skin_display_name(key: str) -> str:
	for s in SKINS:
		if s.key == key:
			return s.display_name
	return key
