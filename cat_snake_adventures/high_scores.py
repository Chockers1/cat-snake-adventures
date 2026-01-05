from __future__ import annotations

from .leaderboard import build_rows, load_entries


def build_high_score_rows(save_system) -> list[tuple[str, int, int, str]]:
	entries = load_entries(save_system.saves_dir)
	return build_rows(entries)
