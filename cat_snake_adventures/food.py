from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class FoodType:
	key: str
	display: str
	length_gain: int
	xp_gain: int
	rarity_weight: int


MOUSE = FoodType(key="mouse", display="Mouse", length_gain=1, xp_gain=10, rarity_weight=80)
FISH = FoodType(key="fish", display="Fish", length_gain=2, xp_gain=20, rarity_weight=15)
SALMON = FoodType(key="salmon", display="Smoked Salmon", length_gain=5, xp_gain=50, rarity_weight=5)

ALL_FOODS: list[FoodType] = [MOUSE, FISH, SALMON]


def roll_food(rng: random.Random) -> FoodType:
	# Weighted random, salmon ~5% by default.
	weights = [f.rarity_weight for f in ALL_FOODS]
	return rng.choices(ALL_FOODS, weights=weights, k=1)[0]
