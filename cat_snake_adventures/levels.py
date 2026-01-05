from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LevelDef:
	index: int
	target_food: int
	speed_cells_per_second: float
	food_spawn_rate: float  # reserved for future
	background_name: str


LEVELS: list[LevelDef] = [
	LevelDef(index=1, target_food=5, speed_cells_per_second=6.0, food_spawn_rate=1.0, background_name="Meadow"),
	LevelDef(index=2, target_food=10, speed_cells_per_second=6.0, food_spawn_rate=1.0, background_name="Meadow"),
	LevelDef(index=3, target_food=15, speed_cells_per_second=7.0, food_spawn_rate=1.0, background_name="Park"),
	LevelDef(index=4, target_food=20, speed_cells_per_second=7.0, food_spawn_rate=1.0, background_name="Park"),
	LevelDef(index=5, target_food=25, speed_cells_per_second=8.0, food_spawn_rate=1.0, background_name="River"),
	LevelDef(index=10, target_food=50, speed_cells_per_second=10.0, food_spawn_rate=1.0, background_name="City"),
]


def get_level(level_index: int) -> LevelDef:
	# Simple: pick the closest defined level at or below index
	candidates = [lvl for lvl in LEVELS if lvl.index <= level_index]
	if not candidates:
		return LEVELS[0]
	return sorted(candidates, key=lambda x: x.index)[-1]
